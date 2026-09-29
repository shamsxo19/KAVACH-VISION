import time
from zenora.audit.trail import AuditLogger
from zenora.core.data_integrity import DataIntegrityChecker
from zenora.core.model_integrity import ModelIntegrityAssessor
from zenora.core.inference_provenance import ProvenanceTracker
from zenora.core.distribution_shift import DistributionShiftDetector

def run_pipeline(dataset_path, model_path, inference_batch_path):
    logger = AuditLogger()
    print("[*] Initializing Zenora Assurance Pipeline...")
    time.sleep(1.0) # Simulating startup
    
    # 1. Training-Data Integrity
    time.sleep(1.5) # Simulating heavy CV scanning
    data_checker = DataIntegrityChecker(logger)
    data_report = data_checker.evaluate_dataset(dataset_path)
    
    # 2. Model Integrity
    model_assessor = ModelIntegrityAssessor(logger)
    model_report = model_assessor.evaluate_model(model_path)
    
    # 3. Distribution Shift
    shift_detector = DistributionShiftDetector(logger)
    shift_report = shift_detector.detect_shift(inference_batch_path, "reference_dist.json")
    
    # 4. Inference Provenance
    provenance_tracker = ProvenanceTracker(logger)
    prov_record = provenance_tracker.secure_inference(
        image_path="img_001.jpg", 
        model_path=model_path,
        output_data={"class": "person", "confidence": 0.99}
    )
    
    # 5. Analyst-Facing Assurance
    final_report = {
        "dataset_integrity": data_report,
        "model_integrity": model_report,
        "distribution_shift": shift_report,
        "sample_provenance_record": prov_record
    }
    
    return final_report
