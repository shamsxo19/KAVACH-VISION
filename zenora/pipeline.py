import time
import os
from zenora.audit.trail import AuditLogger
from zenora.core.data_integrity import DataIntegrityChecker
from zenora.core.model_integrity import ModelIntegrityAssessor
from zenora.core.inference_provenance import ProvenanceTracker
from zenora.core.distribution_shift import DistributionShiftAnalyzer
from zenora.core.risk import RiskEngine

def run_pipeline(
    dataset_path, 
    model_path, 
    operational_dataset_path=None, 
    reference_model_path=None,
    inference_image_path=None,
    preproc_config=None,
    infer_config=None
):
    logger = AuditLogger()
    print("[*] Initializing KAVACH-VISION Assurance Pipeline...")
    
    # 1. Training-Data Integrity
    data_checker = DataIntegrityChecker(logger)
    data_report = data_checker.evaluate_dataset(dataset_path)
    
    # 2. Model Integrity
    model_assessor = ModelIntegrityAssessor(logger)
    model_report = model_assessor.evaluate_model(model_path, reference_path=reference_model_path)
    
    # 3. Distribution Shift
    shift_report = {"status": "NOT_ASSESSED", "findings": []}
    if operational_dataset_path and os.path.exists(operational_dataset_path):
        shift_detector = DistributionShiftAnalyzer(logger)
        shift_report = shift_detector.evaluate_shift(dataset_path, operational_dataset_path)
    
    # 4. Inference Provenance
    prov_record = None
    if inference_image_path and os.path.exists(inference_image_path):
        provenance_tracker = ProvenanceTracker(logger)
        # In a real pipeline, we would run actual inference here. We simulate the prediction dict.
        dummy_output = {"class": "tank", "confidence": 0.98, "bbox": [10, 20, 100, 200]}
        prov_record = provenance_tracker.create_provenance_record(
            image_path=inference_image_path, 
            model_path=model_path,
            output_data=dummy_output,
            preproc_config=preproc_config,
            infer_config=infer_config
        )
    
    # 5. Risk Engine
    all_findings = []
    all_findings.extend(data_report.get("findings", []))
    all_findings.extend(model_report.get("findings", []))
    all_findings.extend(shift_report.get("findings", []))
    
    risk_engine = RiskEngine(logger)
    risk_report = risk_engine.evaluate(all_findings)
    
    # 6. Analyst-Facing Assurance
    final_report = {
        "dataset_integrity": data_report,
        "model_integrity": model_report,
        "distribution_shift": shift_report,
        "sample_provenance_record": prov_record,
        "risk_evaluation": risk_report
    }
    
    return final_report
