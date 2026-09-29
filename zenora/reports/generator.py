import json
from datetime import datetime

class ReportGenerator:
    @staticmethod
    def generate_json_report(report_data):
        report = {
            "metadata": {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "framework": "KAVACH-VISION Integrity Assurance System",
                "version": "2.0.0",
                "reproducibility": "Fully deterministic offline execution",
            },
            "coverage_matrix": {
                "implemented": [
                    "COCO ingestion", "YOLO ingestion", "Exact duplicates (SHA-256)", 
                    "Near duplicates (Hamming)", "Label inconsistency", "Contributor risk", 
                    "OOD screening (Statistical)", "Model digest", "Model substitution comparison", 
                    "Model fingerprint", "Trigger sensitivity screening (Simulated patch)", 
                    "Distribution shift (Mahalanobis)", "Provenance tracking (Ed25519)", 
                    "Replay detection", "Audit-chain verification"
                ],
                "not_implemented": [
                    "Full Neural Cleanse", "Formal adversarial robustness certification", 
                    "Hardware-level compromise", "Secure boot/TPM verification"
                ]
            },
            "assurance_results": report_data
        }
        return json.dumps(report, indent=4)
        
    @staticmethod
    def generate_html_report(report_data):
        html = f"""
        <html>
        <head>
            <title>KAVACH-VISION Assurance Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; color: #333; }}
                h1, h2, h3, h4 {{ color: #0f172a; }}
                .finding {{ background: #f8fafc; border-left: 4px solid #cbd5e1; padding: 10px; margin-bottom: 10px; }}
                .finding.critical {{ border-left-color: #ef4444; background: #fef2f2; }}
                .finding.high {{ border-left-color: #f97316; background: #fff7ed; }}
                .finding.medium {{ border-left-color: #eab308; background: #fefce8; }}
                .finding.low {{ border-left-color: #3b82f6; background: #eff6ff; }}
            </style>
        </head>
        <body>
            <h1>KAVACH-VISION Executive Assurance Report</h1>
            <p><strong>Generated At:</strong> {datetime.utcnow().isoformat()}Z</p>
            <hr>
            
            <h2>1. Executive Summary & Risk Evaluation</h2>
            <p><strong>Overall Status:</strong> {report_data.get('risk_evaluation', {}).get('status', 'Unknown')}</p>
            <p><strong>Risk Score:</strong> {report_data.get('risk_evaluation', {}).get('risk_score', '0')}</p>
            
            <h2>2. Consolidated Findings</h2>
        """
        
        for f in report_data.get('risk_evaluation', {}).get('findings', []):
            sev_class = f.get('severity', 'info').lower()
            html += f"<div class='finding {sev_class}'>"
            html += f"<strong>[{f.get('severity').upper()}] {f.get('category').upper()}: {f.get('issue')}</strong><br>"
            html += f"<strong>Asset:</strong> {f.get('affected_asset')}<br>"
            html += f"<strong>Evidence:</strong> {f.get('evidence')}<br>"
            html += f"<strong>Confidence:</strong> {f.get('confidence')}<br>"
            html += f"<strong>Disposition:</strong> {f.get('recommended_disposition')}<br>"
            html += "</div>"
            
        html += f"""
            <h2>3. Coverage Matrix & Limitations</h2>
            <h4>Supported Capabilities</h4>
            <ul>
                <li>Dataset Parsing (COCO/YOLO)</li>
                <li>Exact/Near Duplicate Detection (SHA-256 / Hamming)</li>
                <li>Label Inconsistency & Contributor Risk Analysis</li>
                <li>Offline OOD Statistical Screening</li>
                <li>Model Identity, Reference Comparison, & Fingerprinting</li>
                <li>Trigger Sensitivity Screening</li>
                <li>Distribution Shift (Mahalanobis)</li>
                <li>Cryptographic Provenance & Audit Chains (Ed25519)</li>
            </ul>
            <h4>Unsupported / Out of Scope</h4>
            <ul>
                <li>Full Neural Cleanse Backdoor Reversal</li>
                <li>Formal Adversarial Robustness Certification</li>
                <li>Hardware-level Compromise / TPM Verification</li>
            </ul>
            
            <hr>
            <p><em>End of KAVACH-VISION Report. Cryptographic Audit Chain Available.</em></p>
        </body>
        </html>
        """
        return html
        
    @staticmethod
    def generate_pdf_report(report_data):
        try:
            from weasyprint import HTML
            html_content = ReportGenerator.generate_html_report(report_data)
            pdf_bytes = HTML(string=html_content).write_pdf()
            return pdf_bytes
        except ImportError:
            return None
