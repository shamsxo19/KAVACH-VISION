from flask import Flask, render_template, jsonify, request, Response, send_from_directory
from flask_cors import CORS
import os
import sys
import json

# Add the root project directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from zenora.pipeline import run_pipeline
from zenora.audit.trail import AuditLogger
from zenora.core.inference_provenance import ProvenanceTracker
from zenora.reports.generator import ReportGenerator

app = Flask(__name__)
CORS(app)

LAST_REPORT = {}

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/status")
def status():
    return jsonify({
        "status": "online",
        "message": "KAVACH-VISION Integrity Assurance Framework is Active."
    })

@app.route("/api/run_pipeline", methods=["GET", "POST"])
def api_run_pipeline():
    """Run the pipeline with real arguments."""
    global LAST_REPORT
    try:
        # Defaults
        dataset_path = "demo_data/poisoned_dataset"
        model_path = "demo_data/backdoored_model.pt"
        operational_dataset_path = "demo_data/poisoned_dataset"
        reference_model_path = "demo_data/clean_model.pt"
        inference_image_path = "demo_data/poisoned_dataset/images/img_21.jpg"

        if request.method == "POST" and request.is_json:
            data = request.get_json()
            dataset_path = data.get("dataset_path") or dataset_path
            model_path = data.get("model_path") or model_path
            operational_dataset_path = data.get("reference_path") or operational_dataset_path # Map legacy reference_path
        
        report = run_pipeline(
            dataset_path=dataset_path, 
            model_path=model_path, 
            operational_dataset_path=operational_dataset_path,
            reference_model_path=reference_model_path,
            inference_image_path=inference_image_path
        )
        LAST_REPORT = report
        return jsonify({"success": True, "report": report})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/verify/audit")
def verify_audit():
    logger = AuditLogger()
    res = logger.verify_chain()
    return jsonify(res)

@app.route("/api/verify/provenance")
def verify_provenance():
    logger = AuditLogger()
    tracker = ProvenanceTracker(logger)
    res = tracker.verify_provenance_chain()
    return jsonify(res)

@app.route("/api/report/json")
def download_json_report():
    json_data = ReportGenerator.generate_json_report(LAST_REPORT)
    return Response(
        json_data,
        mimetype="application/json",
        headers={"Content-disposition": "attachment; filename=kavach_report.json"}
    )

@app.route("/api/report/html")
def download_html_report():
    html_data = ReportGenerator.generate_html_report(LAST_REPORT)
    return Response(
        html_data,
        mimetype="text/html",
        headers={"Content-disposition": "attachment; filename=kavach_report.html"}
    )

@app.route("/api/report/pdf")
def download_pdf_report():
    pdf_data = ReportGenerator.generate_pdf_report(LAST_REPORT)
    if pdf_data:
        return Response(
            pdf_data,
            mimetype="application/pdf",
            headers={"Content-disposition": "attachment; filename=kavach_report.pdf"}
        )
    return jsonify({"error": "PDF generation failed. WeasyPrint missing."}), 500

@app.route("/api/logs")
def api_logs():
    """Fetch the latest audit logs."""
    logger = AuditLogger()
    logs = logger.get_events(limit=50)
    return jsonify({"latest_file": logger.log_file, "logs": logs})

@app.route('/demo_data/<path:filename>')
def serve_demo_data(filename):
    demo_dir = os.path.abspath(os.path.join(app.root_path, '..', '..', 'demo_data'))
    return send_from_directory(demo_dir, filename)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
