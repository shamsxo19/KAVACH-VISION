from flask import Flask, render_template, jsonify
from flask_cors import CORS
import os
import sys
import json
import glob

# Add the root project directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from zenora.pipeline import run_pipeline

app = Flask(__name__)
CORS(app)

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/status")
def status():
    # Keep the basic status for backward compatibility with the frontend
    return jsonify({
        "status": "online",
        "message": "Zenora Integrity Assurance Framework is Active."
    })

from flask import request, Response
from zenora.reports.generator import ReportGenerator

# Global variable to hold the last report for downloading
LAST_REPORT = {}

@app.route("/api/run_pipeline", methods=["GET", "POST"])
def api_run_pipeline():
    """Run the actual prototype pipeline and return the report."""
    global LAST_REPORT
    try:
        # Default to demo paths if not provided
        dataset_path = "demo_data/poisoned_dataset"
        model_path = "demo_data/backdoored_model.pt"
        reference_path = "demo_data/clean_dataset"

        if request.method == "POST" and request.is_json:
            data = request.get_json()
            dataset_path = data.get("dataset_path") or dataset_path
            model_path = data.get("model_path") or model_path
            reference_path = data.get("reference_path") or reference_path
        
        report = run_pipeline(dataset_path, model_path, reference_path)
        LAST_REPORT = report
        return jsonify({"success": True, "report": report})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/report/json")
def download_json_report():
    """Download the JSON assurance report."""
    json_data = ReportGenerator.generate_json_report(LAST_REPORT)
    return Response(
        json_data,
        mimetype="application/json",
        headers={"Content-disposition": "attachment; filename=assurance_report.json"}
    )

@app.route("/api/report/html")
def download_html_report():
    """Download the HTML assurance report."""
    html_data = ReportGenerator.generate_html_report(LAST_REPORT)
    return Response(
        html_data,
        mimetype="text/html",
        headers={"Content-disposition": "attachment; filename=assurance_report.html"}
    )

@app.route("/api/report/pdf")
def download_pdf_report():
    """Download the PDF assurance report."""
    pdf_data = ReportGenerator.generate_pdf_report(LAST_REPORT)
    if pdf_data:
        return Response(
            pdf_data,
            mimetype="application/pdf",
            headers={"Content-disposition": "attachment; filename=assurance_report.pdf"}
        )
    return jsonify({"error": "PDF generation failed. WeasyPrint missing."}), 500

@app.route("/api/logs")
def api_logs():
    """Fetch the latest audit logs."""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        return jsonify({"logs": []})
        
    list_of_files = glob.glob(f"{log_dir}/*.log")
    if not list_of_files:
        return jsonify({"logs": []})
        
    latest_file = max(list_of_files, key=os.path.getctime)
    logs = []
    try:
        with open(latest_file, 'r') as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))
        return jsonify({"latest_file": latest_file, "logs": logs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

from flask import send_from_directory

@app.route('/demo_data/<path:filename>')
def serve_demo_data(filename):
    """Serve the generated dataset images to the frontend dashboard."""
    demo_dir = os.path.abspath(os.path.join(app.root_path, '..', '..', 'demo_data'))
    return send_from_directory(demo_dir, filename)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
