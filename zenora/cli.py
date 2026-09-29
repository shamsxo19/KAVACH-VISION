import argparse
import sys
import json
from zenora.pipeline import run_pipeline

def main():
    parser = argparse.ArgumentParser(description="Zenora: Trustworthy Computer Vision Integrity Assurance")
    parser.add_argument('--dataset', type=str, required=True, help="Path to the dataset")
    parser.add_argument('--model', type=str, required=True, help="Path to the model")
    parser.add_argument('--inference-batch', type=str, required=False, default="demo_batch", help="Path to inference batch")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print(" ZENORA - Computer Vision Integrity Assurance Framework ")
    print("=" * 60)
    
    report = run_pipeline(args.dataset, args.model, args.inference_batch)
    
    print("\n" + "=" * 60)
    print(" FINAL ASSURANCE REPORT ")
    print("=" * 60)
    print(json.dumps(report, indent=4))
    print("=" * 60)
    print("[+] Evaluation complete. Audit trail updated.")

if __name__ == "__main__":
    main()
