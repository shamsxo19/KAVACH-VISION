import os
import hashlib
from PIL import Image
import imagehash
import json
import numpy as np
from zenora.crypto.engine import CryptoEngine
from zenora.ingest.parsers import DatasetParser

class DataIntegrityChecker:
    def __init__(self, audit_logger):
        self.audit_logger = audit_logger

    def _calculate_hamming_distance(self, hash1, hash2):
        """Calculate Hamming distance between two hex hashes"""
        try:
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            return h1 - h2
        except Exception:
            return 999

    def _extract_offline_ood_features(self, img_path):
        """Deterministic, offline, statistical feature extraction for OOD screening.
        Using a simplified statistical representation (color moments) instead of full deep features
        to guarantee completely offline, reproducible execution without external model dependencies.
        """
        try:
            with Image.open(img_path) as img:
                img_rgb = img.convert('RGB')
                arr = np.array(img_rgb)
                # Compute Color Moments: Mean, Std, Skewness per channel
                mean = np.mean(arr, axis=(0,1))
                std = np.std(arr, axis=(0,1))
                # Fallback simple proxy for skewness/distribution
                p90 = np.percentile(arr, 90, axis=(0,1))
                p10 = np.percentile(arr, 10, axis=(0,1))
                return np.concatenate([mean, std, p90 - p10]).astype(float)
        except Exception:
            return None

    def evaluate_dataset(self, dataset_path, format="COCO", hamming_threshold=4):
        """Evaluates a dataset for duplicates, poisoning, and label flipping."""
        print(f"[*] Evaluating training data at {dataset_path} (Format: {format})...")
        findings = []
        
        # 1. Parse Annotations
        labels_map = {}
        if format.upper() == "COCO":
            anno_path = os.path.join(dataset_path, "annotations.json")
            if os.path.exists(anno_path):
                labels_map = DatasetParser.parse_coco(anno_path)
        elif format.upper() == "YOLO":
            labels_dir = os.path.join(dataset_path, "labels")
            imgs_dir = os.path.join(dataset_path, "images")
            if os.path.exists(labels_dir) and os.path.exists(imgs_dir):
                labels_map = DatasetParser.parse_yolo(labels_dir, imgs_dir)
            
        images_dir = os.path.join(dataset_path, "images") if format.upper() == "YOLO" else dataset_path
        if not os.path.exists(images_dir):
            return {"status": "error", "error": f"Directory not found: {images_dir}"}
            
        exact_hashes = {}
        phash_map = {}
        
        duplicates_found = 0
        label_flips_found = 0
        small_image_count = 0
        corrupt_count = 0
        total_images = 0
        
        # Tracking contributors if we simulate metadata
        metadata_path = os.path.join(dataset_path, "metadata.json")
        metadata = {}
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                
        contributor_risk = {}
        features_list = []
        file_list = []
        
        for root, _, files in os.walk(images_dir):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    img_path = os.path.join(root, file)
                    total_images += 1
                    file_list.append(file)
                    file_meta = metadata.get(file, {})
                    contributor = file_meta.get("contributor", "unknown")
                    
                    if contributor not in contributor_risk:
                        contributor_risk[contributor] = {"total": 0, "exact_dup": 0, "near_dup": 0, "label_conflict": 0, "corrupt": 0, "ood": 0}
                    contributor_risk[contributor]["total"] += 1
                    
                    try:
                        # Exact Hash (SHA-256)
                        file_hash = CryptoEngine.compute_digest(img_path)
                            
                        # Perceptual Hash
                        img = Image.open(img_path)
                        p_hash = str(imagehash.average_hash(img))
                        
                        # Offline OOD feature extraction
                        features = self._extract_offline_ood_features(img_path)
                        if features is not None:
                            features_list.append(features)
                        
                        # [CRITICAL] Check Exact Duplicates
                        if file_hash in exact_hashes:
                            duplicates_found += 1
                            contributor_risk[contributor]["exact_dup"] += 1
                        else:
                            exact_hashes[file_hash] = file
                            
                        # [HIGH] Check Perceptual Duplicates & Label Flipping with Hamming Distance
                        is_near_dup = False
                        for prev_hash, prev_file in phash_map.items():
                            dist = self._calculate_hamming_distance(p_hash, prev_hash)
                            if dist <= hamming_threshold:
                                is_near_dup = True
                                contributor_risk[contributor]["near_dup"] += 1
                                
                                orig_labels = labels_map.get(prev_file, [])
                                curr_labels = labels_map.get(file, [])
                                
                                if set(orig_labels) != set(curr_labels) and orig_labels and curr_labels:
                                    label_flips_found += 1
                                    contributor_risk[contributor]["label_conflict"] += 1
                                    findings.append({
                                        "finding_id": f"DATA-LBL-{label_flips_found}",
                                        "category": "label_inconsistency",
                                        "issue": "Potential Label Flipping / Poisoning",
                                        "evidence": f"Images {file} and {prev_file} are perceptually similar (Hamming={dist}) but have conflicting labels: {curr_labels} vs {orig_labels}. Source: {contributor}",
                                        "confidence": 0.95,
                                        "severity": "high",
                                        "affected_asset": file,
                                        "recommendation": "QUARANTINE"
                                    })
                                break
                                
                        if not is_near_dup:
                            phash_map[p_hash] = file

                        # [LOW] Undersized image check
                        w, h = img.size
                        if w < 64 or h < 64:
                            small_image_count += 1

                    except Exception as e:
                        corrupt_count += 1
                        contributor_risk[contributor]["corrupt"] += 1

        # OOD Screening (Isolation Forest approximation / distance from mean)
        ood_count = 0
        if len(features_list) > 10:
            feature_matrix = np.array(features_list)
            mean_vec = np.mean(feature_matrix, axis=0)
            cov_matrix = np.cov(feature_matrix, rowvar=False) + np.eye(feature_matrix.shape[1]) * 1e-5
            try:
                inv_cov = np.linalg.inv(cov_matrix)
                for idx, feat in enumerate(features_list):
                    diff = feat - mean_vec
                    mahalanobis = np.sqrt(np.dot(np.dot(diff, inv_cov), diff))
                    if mahalanobis > 10.0:  # Threshold for statistical anomaly
                        ood_count += 1
                        fname = file_list[idx]
                        c = metadata.get(fname, {}).get("contributor", "unknown")
                        if c in contributor_risk:
                            contributor_risk[c]["ood"] += 1
            except np.linalg.LinAlgError:
                pass
                
        if ood_count > 0:
            findings.append({
                "finding_id": "DATA-OOD-1",
                "category": "ood_screening",
                "issue": "Offline Statistical OOD Samples Detected",
                "evidence": f"Found {ood_count} images exhibiting severe statistical anomalies (Color moments Mahalanobis distance > 10). Note: This is a statistical heuristic, not guaranteed semantic OOD detection.",
                "confidence": 0.75,
                "severity": "medium",
                "affected_asset": "Dataset",
                "recommendation": "REVIEW"
            })

        # Aggregated findings
        if duplicates_found > 0:
            findings.append({
                "finding_id": "DATA-DUP-1",
                "category": "exact_duplicates",
                "issue": "Near-Duplicate Flooding Detected",
                "evidence": f"Found {duplicates_found} exact SHA-256 duplicate images in the dataset.",
                "confidence": 1.0,
                "severity": "critical",
                "affected_asset": "Dataset",
                "recommendation": "REVIEW"
            })

        near_dup_ratio = label_flips_found / max(total_images, 1)
        if near_dup_ratio > 0.03:
            findings.append({
                "finding_id": "DATA-NDUP-1",
                "category": "near_duplicates",
                "issue": "Elevated Near-Duplicate Ratio",
                "evidence": f"{label_flips_found} perceptual near-duplicates found ({near_dup_ratio*100:.1f}%). Possible data poisoning campaign.",
                "confidence": 0.80,
                "severity": "medium",
                "affected_asset": "Dataset",
                "recommendation": "REVIEW"
            })

        if corrupt_count > 0:
            findings.append({
                "finding_id": "DATA-COR-1",
                "category": "corrupt_files",
                "issue": "Corrupt or Unreadable Files Found",
                "evidence": f"{corrupt_count} image(s) could not be read and were skipped.",
                "confidence": 1.0,
                "severity": "high",
                "affected_asset": "Dataset",
                "recommendation": "QUARANTINE"
            })
            
        # Evaluate Contributor Risk
        for contributor, stats in contributor_risk.items():
            if contributor != "unknown" and stats["total"] > 0:
                bad_ratio = (stats["exact_dup"] + stats["label_conflict"] + stats["corrupt"]) / stats["total"]
                if bad_ratio > 0.2:
                    findings.append({
                        "finding_id": f"DATA-RISK-{contributor}",
                        "category": "contributor_risk",
                        "issue": f"High Risk Contributor: {contributor}",
                        "evidence": f"Contributor {contributor} submitted {stats['total']} samples with {stats['label_conflict']} label conflicts, {stats['exact_dup']} duplicates, and {stats['corrupt']} corruptions.",
                        "confidence": 0.90,
                        "severity": "critical",
                        "affected_asset": "Dataset",
                        "recommendation": "QUARANTINE"
                    })

        # Log to New Audit Chain
        for finding in findings:
            self.audit_logger.append(
                event_type="DATA_INTEGRITY_FLAG",
                actor="SYSTEM",
                asset_id=dataset_path,
                payload=finding
            )
            
        status = "review_required" if findings else "passed"
        
        return {
            "status": status,
            "findings": findings,
            "dataset": {
                "num_samples": total_images,
                "exact_duplicates": duplicates_found,
                "label_flips": label_flips_found,
                "ood_detected": ood_count
            },
            "contributor_risk_available": len(contributor_risk) > 1 or "unknown" not in contributor_risk
        }
