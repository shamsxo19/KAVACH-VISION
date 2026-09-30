import os
import json
import numpy as np
from PIL import Image

class DistributionShiftAnalyzer:
    def __init__(self, audit_logger):
        self.audit_logger = audit_logger

    def _extract_deterministic_features(self, img_path):
        """Extract RGB deterministic color/texture statistical moments."""
        try:
            with Image.open(img_path) as img:
                # Force consistent RGB handling
                img_rgb = img.convert('RGB')
                arr = np.array(img_rgb)
                
                # Mean and std dev across spatial dimensions for each channel
                mean = np.mean(arr, axis=(0,1))
                std = np.std(arr, axis=(0,1))
                return np.concatenate([mean, std]).astype(float)
        except Exception:
            return None

    def _calculate_mahalanobis(self, ref_features, test_features):
        """Calculate average Mahalanobis distance between reference set and test set."""
        if len(ref_features) < 2 or len(test_features) == 0:
            return 0.0
            
        ref_matrix = np.array(ref_features)
        test_matrix = np.array(test_features)
        
        # Calculate reference distribution
        mean_vec = np.mean(ref_matrix, axis=0)
        cov_matrix = np.cov(ref_matrix, rowvar=False) + np.eye(ref_matrix.shape[1]) * 1e-5
        
        try:
            inv_cov = np.linalg.inv(cov_matrix)
            distances = []
            for feat in test_matrix:
                diff = feat - mean_vec
                dist = np.sqrt(np.dot(np.dot(diff, inv_cov), diff))
                distances.append(dist)
                
            return float(np.mean(distances))
        except np.linalg.LinAlgError:
            return 0.0

    def evaluate_shift(self, reference_dataset_path, operational_dataset_path):
        """Quantify distribution shift between a reference (e.g. training) and an operational dataset."""
        print(f"[*] Evaluating distribution shift between {os.path.basename(reference_dataset_path)} and {os.path.basename(operational_dataset_path)}...")
        
        if not os.path.exists(reference_dataset_path):
            return {"status": "error", "error": f"Reference dataset not found: {reference_dataset_path}"}
        if not os.path.exists(operational_dataset_path):
            return {"status": "error", "error": f"Operational dataset not found: {operational_dataset_path}"}

        ref_features = []
        test_features = []
        
        # Load reference
        for root, _, files in os.walk(os.path.join(reference_dataset_path, "images") if os.path.exists(os.path.join(reference_dataset_path, "images")) else reference_dataset_path):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    feat = self._extract_deterministic_features(os.path.join(root, file))
                    if feat is not None:
                        ref_features.append(feat)
                        
        # Load operational
        for root, _, files in os.walk(os.path.join(operational_dataset_path, "images") if os.path.exists(os.path.join(operational_dataset_path, "images")) else operational_dataset_path):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    feat = self._extract_deterministic_features(os.path.join(root, file))
                    if feat is not None:
                        test_features.append(feat)

        shift_distance = self._calculate_mahalanobis(ref_features, test_features)
        
        findings = []
        status = "NORMAL"
        
        # Configurable thresholds
        moderate_threshold = 5.0
        severe_threshold = 15.0
        
        # Calculate normalized risk (0 to 1) based on Sigmoid-like scaling relative to thresholds
        # If distance == 0, risk = 0
        # If distance == severe_threshold, risk is near 1.0
        normalized_risk = min(1.0, float(shift_distance) / (severe_threshold * 1.5))
        
        if shift_distance > severe_threshold:
            status = "STRONG_ANOMALY"
            findings.append({
                "finding_id": "DIST-SHIFT-2",
                "category": "strong_anomaly",
                "severity": "HIGH",
                "confidence": 0.95,
                "asset": "Operational Dataset",
                "evidence": f"Mahalanobis distance ({shift_distance:.2f}) exceeds critical threshold ({severe_threshold}).",
                "reason": "Massive change in color/texture statistics (e.g. day vs night, weather changes, sensor replacement, or targeted perturbations).",
                "limitations": "Uses deterministic color/texture moments instead of semantic deep features.",
                "recommended_disposition": "QUARANTINE"
            })
        elif shift_distance > moderate_threshold:
            status = "DISTRIBUTION_SHIFT"
            findings.append({
                "finding_id": "DIST-SHIFT-1",
                "category": "distribution_shift",
                "severity": "MEDIUM",
                "confidence": 0.85,
                "asset": "Operational Dataset",
                "evidence": f"Mahalanobis distance ({shift_distance:.2f}) exceeds moderate threshold ({moderate_threshold}).",
                "reason": "Moderate drift from training baseline. Often legitimate environmental change (illumination, terrain) but requires monitoring.",
                "limitations": "Uses deterministic color/texture moments.",
                "recommended_disposition": "REVIEW"
            })

        for finding in findings:
            self.audit_logger.append(
                event_type="DISTRIBUTION_SHIFT_FLAG",
                actor="SYSTEM",
                asset_id=os.path.basename(operational_dataset_path),
                payload=finding
            )
            
        return {
            "status": status,
            "raw_distance": float(shift_distance),
            "normalized_risk": float(normalized_risk),
            "threshold": float(moderate_threshold),
            "reference_samples": len(ref_features),
            "test_samples": len(test_features),
            "findings": findings
        }
