import os
import hashlib
from PIL import Image
import imagehash
from zenora.ingest.parsers import DatasetParser

class DataIntegrityChecker:
    def __init__(self, audit_logger):
        self.audit_logger = audit_logger

    def evaluate_dataset(self, dataset_path, format="COCO"):
        """Evaluates a dataset for duplicates, poisoning, and label flipping."""
        print(f"[*] Evaluating training data at {dataset_path} (Format: {format})...")
        findings = []
        
        # 1. Parse Annotations
        labels_map = {}
        if format.upper() == "COCO":
            anno_path = os.path.join(dataset_path, "annotations.json")
            labels_map = DatasetParser.parse_coco(anno_path)
        elif format.upper() == "YOLO":
            labels_map = DatasetParser.parse_yolo(
                os.path.join(dataset_path, "labels"), 
                os.path.join(dataset_path, "images")
            )
            
        # 2. Extract Hashes to find Duplicates & Mislabeled Poisoning
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
        
        for root, _, files in os.walk(images_dir):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    img_path = os.path.join(root, file)
                    total_images += 1
                    try:
                        # Exact Hash (MD5)
                        with open(img_path, "rb") as f:
                            file_hash = hashlib.md5(f.read()).hexdigest()
                            
                        # Perceptual Hash
                        img = Image.open(img_path)
                        p_hash = str(imagehash.average_hash(img))
                        
                        # [CRITICAL] Check Exact Duplicates (deliberate flooding)
                        if file_hash in exact_hashes:
                            duplicates_found += 1
                        else:
                            exact_hashes[file_hash] = file
                            
                        # [HIGH] Check Perceptual Duplicates & Label Flipping
                        if p_hash in phash_map:
                            orig_file = phash_map[p_hash]
                            orig_labels = labels_map.get(orig_file, [])
                            curr_labels = labels_map.get(file, [])
                            
                            if set(orig_labels) != set(curr_labels) and orig_labels and curr_labels:
                                label_flips_found += 1
                                findings.append({
                                    "issue": "Potential Label Flipping / Poisoning",
                                    "evidence": f"Images {file} and {orig_file} are perceptually identical but have conflicting labels.",
                                    "confidence": 0.95,
                                    "severity": "high",
                                    "recommendation": "quarantine_samples"
                                })
                        else:
                            phash_map[p_hash] = file

                        # [MEDIUM] Undersized image check
                        w, h = img.size
                        if w < 64 or h < 64:
                            small_image_count += 1

                    except Exception as e:
                        corrupt_count += 1

        # [CRITICAL] Exact duplicate flooding
        if duplicates_found > 0:
            findings.append({
                "issue": "Near-Duplicate Flooding Detected",
                "evidence": f"Found {duplicates_found} exact or perceptual duplicate images in the dataset.",
                "confidence": 0.99,
                "severity": "critical",
                "recommendation": "deduplicate_dataset"
            })

        # [MEDIUM] High ratio of perceptual near-duplicates
        near_dup_ratio = label_flips_found / max(total_images, 1)
        if near_dup_ratio > 0.03:
            findings.append({
                "issue": "Elevated Near-Duplicate Ratio",
                "evidence": f"{label_flips_found} perceptual near-duplicates found ({near_dup_ratio*100:.1f}% of dataset). Possible data poisoning campaign.",
                "confidence": 0.80,
                "severity": "medium",
                "recommendation": "review_dataset_sources"
            })

        # [LOW] Small/undersized images
        if small_image_count > 0:
            findings.append({
                "issue": "Undersized Image Samples Detected",
                "evidence": f"{small_image_count} images below minimum resolution (64x64). May degrade model generalization.",
                "confidence": 0.72,
                "severity": "low",
                "recommendation": "resize_or_remove_samples"
            })

        # [INFO] Dataset coverage note
        if total_images > 0:
            findings.append({
                "issue": "Dataset Coverage Report",
                "evidence": f"Scanned {total_images} images. Class distribution and augmentation coverage should be verified before training.",
                "confidence": 1.0,
                "severity": "info",
                "recommendation": "review_class_balance"
            })

        # [INFO] Corrupt file report
        if corrupt_count > 0:
            findings.append({
                "issue": "Corrupt or Unreadable Files Found",
                "evidence": f"{corrupt_count} image(s) could not be read and were skipped during evaluation.",
                "confidence": 0.95,
                "severity": "low",
                "recommendation": "remove_corrupt_files"
            })

        # Log all findings to Audit Trail
        for finding in findings:
            self.audit_logger.log_event(
                event_type="DATA_INTEGRITY_FLAG",
                asset_id=dataset_path,
                description=finding["issue"],
                confidence=finding["confidence"],
                recommendation=finding["recommendation"],
                evidence=finding["evidence"]
            )
            
        status = "review_required" if findings else "passed"
        
        return {
            "status": status,
            "findings": findings,
            "dataset": {
                "num_samples": total_images,
                "exact_duplicates": duplicates_found,
                "label_flips": label_flips_found
            }
        }
