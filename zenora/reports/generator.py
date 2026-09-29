import json
from datetime import datetime

class ReportGenerator:
    @staticmethod
    def generate_json_report(report_data):
        """Generates a structured JSON assurance report."""
        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "framework": "Zenora Integrity Assurance System",
                "version": "1.0.0"
            },
            "assurance_results": report_data
        }
        return json.dumps(report, indent=4)
        
    @staticmethod
    def generate_html_report(report_data):
        """Generates a standalone HTML assurance report."""
        # Simple HTML template for the report
        html = f"""
        <html>
        <head>
            <title>Zenora Assurance Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; color: #333; }}
                h1, h2, h3 {{ color: #003366; }}
                .finding {{ background: #f9f9f9; border-left: 4px solid #dc2626; padding: 10px; margin-bottom: 10px; }}
                .finding.warning {{ border-left-color: #d97706; }}
                .finding.info {{ border-left-color: #2563eb; }}
            </style>
        </head>
        <body>
            <h1>Zenora Computer Vision Assurance Report</h1>
            <p><strong>Generated At:</strong> {datetime.now().isoformat()}</p>
            <hr>
            
            <h2>1. Data Integrity</h2>
            <p>Status: {report_data.get('dataset_integrity', {}).get('status', 'Unknown')}</p>
        """
        
        # Add Data Findings
        for f in report_data.get('dataset_integrity', {}).get('findings', []):
            html += f"<div class='finding warning'><strong>Issue:</strong> {f.get('issue')}<br><strong>Reason/Evidence:</strong> {f.get('evidence')}<br><strong>Recommendation:</strong> {f.get('recommendation')}</div>"
            
        html += f"""
            <h2>2. Model Integrity</h2>
            <p>Status: {report_data.get('model_integrity', {}).get('status', 'Unknown')}</p>
        """
        
        # Add Model Findings
        for f in report_data.get('model_integrity', {}).get('findings', []):
            html += f"<div class='finding'><strong>Issue:</strong> {f.get('issue')}<br><strong>Reason/Evidence:</strong> {f.get('evidence')}<br><strong>Recommendation:</strong> {f.get('recommendation')}</div>"
            
        html += f"""
            <h2>3. Distribution Shift</h2>
            <p>Status: {report_data.get('distribution_shift', {}).get('status', 'Unknown')}</p>
        """
        
        # Add Shift Findings
        for f in report_data.get('distribution_shift', {}).get('findings', []):
            html += f"<div class='finding warning'><strong>Issue:</strong> {f.get('issue')}<br><strong>Reason/Evidence:</strong> {f.get('evidence')}<br><strong>Recommendation:</strong> {f.get('recommendation')}</div>"
            
        html += f"""
            <h2>4. Inference Provenance (Sample Record)</h2>
            <pre>{json.dumps(report_data.get('sample_provenance_record', {}), indent=4)}</pre>
            
            <hr>
            <p><em>End of Report</em></p>
        </body>
        </html>
        """
        return html
        
    @staticmethod
    def generate_pdf_report(report_data):
        """Generates a PDF assurance report using WeasyPrint."""
        try:
            from weasyprint import HTML
            html_content = ReportGenerator.generate_html_report(report_data)
            pdf_bytes = HTML(string=html_content).write_pdf()
            return pdf_bytes
        except ImportError:
            print("[!] WeasyPrint not installed. Falling back to HTML.")
            return None
