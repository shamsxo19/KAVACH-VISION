import json
import os
from datetime import datetime
from zenora.crypto.engine import CryptoEngine

class AuditLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, f"audit_{datetime.now().strftime('%Y%m%d')}.log")

    def log_event(self, event_type, asset_id, description, confidence, recommendation, evidence):
        """Log an event with tamper-evident hashing."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "asset": asset_id,
            "description": description,
            "confidence": confidence,
            "recommendation": recommendation,
            "evidence": evidence
        }
        
        # Sign the entry
        signature = CryptoEngine.sign_record(entry)
        entry["signature"] = signature

        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
            
        return entry
