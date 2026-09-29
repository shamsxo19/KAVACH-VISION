import argparse
import sys
import json
import os
from zenora.pipeline import run_pipeline
from zenora.audit.trail import AuditLogger
from zenora.core.inference_provenance import ProvenanceTracker
from zenora.core.data_integrity import DataIntegrityChecker
from zenora.core.model_integrity import ModelIntegrityAssessor
from zenora.core.distribution_shift import DistributionShiftAnalyzer
from zenora.demo.generators import generate_better_dataset, generate_dummy_model

def main():
    parser = argparse.ArgumentParser(description="KAVACH-VISION: Trustworthy Computer Vision Integrity Assurance")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run-pipeline
    p_run = subparsers.add_parser('run-pipeline', help="Run full pipeline")
    p_run.add_argument('--dataset', required=True)
    p_run.add_argument('--model', required=True)
    p_run.add_argument('--operational-dataset')
    p_run.add_argument('--reference-model')
    p_run.add_argument('--inference-image')

    # verify-audit
    p_audit = subparsers.add_parser('verify-audit', help="Verify cryptographically linked audit chain")

    # verify-provenance
    p_prov = subparsers.add_parser('verify-provenance', help="Verify inference provenance chain")

    # scan-data
    p_data = subparsers.add_parser('scan-data', help="Scan dataset integrity")
    p_data.add_argument('--dataset', required=True)

    # scan-model
    p_model = subparsers.add_parser('scan-model', help="Scan model integrity")
    p_model.add_argument('--model', required=True)
    p_model.add_argument('--reference-model')

    # scan-shift
    p_shift = subparsers.add_parser('scan-shift', help="Scan distribution shift")
    p_shift.add_argument('--reference-dataset', required=True)
    p_shift.add_argument('--operational-dataset', required=True)

    # generate-demo
    p_demo = subparsers.add_parser('generate-demo', help="Generate deterministic attack scenarios")
    p_demo.add_argument('--outdir', default='demo_data')

    args = parser.parse_args()

    print("=" * 60)
    print(" KAVACH-VISION - Computer Vision Integrity Assurance Framework ")
    print("=" * 60)

    if args.command == 'run-pipeline':
        report = run_pipeline(args.dataset, args.model, args.operational_dataset, args.reference_model, args.inference_image)
        print(json.dumps(report, indent=4))
        
    elif args.command == 'verify-audit':
        logger = AuditLogger()
        res = logger.verify_chain()
        print(json.dumps(res, indent=4))

    elif args.command == 'verify-provenance':
        logger = AuditLogger()
        tracker = ProvenanceTracker(logger)
        res = tracker.verify_provenance_chain()
        print(json.dumps(res, indent=4))

    elif args.command == 'scan-data':
        logger = AuditLogger()
        checker = DataIntegrityChecker(logger)
        res = checker.evaluate_dataset(args.dataset)
        print(json.dumps(res, indent=4))

    elif args.command == 'scan-model':
        logger = AuditLogger()
        assessor = ModelIntegrityAssessor(logger)
        res = assessor.evaluate_model(args.model, args.reference_model)
        print(json.dumps(res, indent=4))

    elif args.command == 'scan-shift':
        logger = AuditLogger()
        analyzer = DistributionShiftAnalyzer(logger)
        res = analyzer.evaluate_shift(args.reference_dataset, args.operational_dataset)
        print(json.dumps(res, indent=4))

    elif args.command == 'generate-demo':
        os.makedirs(args.outdir, exist_ok=True)
        generate_better_dataset(f"{args.outdir}/clean_dataset", 50, False)
        generate_dummy_model(f"{args.outdir}/clean_model.pt", False)
        generate_better_dataset(f"{args.outdir}/poisoned_dataset", 50, True)
        generate_dummy_model(f"{args.outdir}/backdoored_model.pt", True)
        print(f"Generated demo artifacts in {args.outdir}")

if __name__ == "__main__":
    main()
