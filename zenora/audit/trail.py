import json
import os
import copy
from datetime import datetime
from zenora.crypto.engine import CryptoEngine

class AuditLogger:
    def __init__(self, log_dir="logs", chain_file="audit_chain.jsonl"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, chain_file)

    def _get_last_entry(self):
        if not os.path.exists(self.log_file):
            return None
        last_line = None
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last_line = line.strip()
        if last_line:
            try:
                return json.loads(last_line)
            except json.JSONDecodeError:
                return None
        return None

    def _calculate_entry_hash(self, entry_dict):
        """Calculate deterministic hash of the entry content"""
        # Create a copy without signature and current_hash
        content = {k: v for k, v in entry_dict.items() if k not in ["current_hash", "signature"]}
        canonical_str = json.dumps(content, sort_keys=True, separators=(',', ':'))
        return CryptoEngine.hash_string(canonical_str)

    def append(self, event_type, actor, asset_id, payload):
        """Append an event to the cryptographically linked chain."""
        last_entry = self._get_last_entry()
        
        sequence = 0
        previous_hash = "GENESIS"
        if last_entry:
            sequence = last_entry.get("sequence", -1) + 1
            previous_hash = last_entry.get("current_hash", "UNKNOWN")

        entry = {
            "sequence": sequence,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": event_type,
            "actor": actor,
            "asset": asset_id,
            "payload": payload,
            "previous_hash": previous_hash
        }
        
        # 1. Compute current hash based on content and previous hash
        entry["current_hash"] = self._calculate_entry_hash(entry)
        
        # 2. Sign the content using Ed25519
        signable_content = {k: v for k, v in entry.items() if k != "signature"}
        entry["signature"] = CryptoEngine.sign_record(signable_content)

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
            
        return entry

    def log_event(self, event_type, asset_id, description, confidence, recommendation, evidence):
        """Legacy wrapper for old calls, mapping to new chain."""
        payload = {
            "description": description,
            "confidence": confidence,
            "recommendation": recommendation,
            "evidence": evidence
        }
        return self.append(event_type=event_type, actor="KAVACH_SYSTEM", asset_id=asset_id, payload=payload)

    def verify_chain(self):
        """Verify the integrity of the audit chain."""
        if not os.path.exists(self.log_file):
            return {"status": "VALID", "message": "Chain is empty.", "entries": 0}
            
        entries = []
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        entries.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        return {"status": "INVALID", "message": "Corrupted JSON format detected in file.", "failed_at": len(entries)}
        
        if not entries:
            return {"status": "VALID", "message": "Chain is empty.", "entries": 0}
            
        expected_prev_hash = "GENESIS"
        expected_seq = 0
        
        for idx, entry in enumerate(entries):
            # Check Sequence
            if entry.get("sequence") != expected_seq:
                return {"status": "INVALID", "message": f"Sequence out of order. Expected {expected_seq}, got {entry.get('sequence')}", "failed_at": idx}
                
            # Check Previous Hash Link
            if entry.get("previous_hash") != expected_prev_hash:
                return {"status": "INVALID", "message": f"Broken hash link at sequence {expected_seq}.", "failed_at": idx}
                
            # Check Current Hash Calculation
            calculated_hash = self._calculate_entry_hash(entry)
            if entry.get("current_hash") != calculated_hash:
                return {"status": "INVALID", "message": f"Modified entry detected. Hash mismatch at sequence {expected_seq}.", "failed_at": idx}
                
            # Check Ed25519 Signature
            signable_content = {k: v for k, v in entry.items() if k != "signature"}
            signature = entry.get("signature", "")
            if not CryptoEngine.verify_signature(signable_content, signature):
                return {"status": "INVALID", "message": f"Invalid signature at sequence {expected_seq}.", "failed_at": idx}
                
            expected_seq += 1
            expected_prev_hash = calculated_hash
            
        return {"status": "VALID", "message": "Chain is completely valid.", "entries": len(entries)}

    def get_events(self, limit=100, reverse=True):
        if not os.path.exists(self.log_file):
            return []
        entries = []
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line.strip()))
        if reverse:
            entries.reverse()
        return entries[:limit]
        
    def export(self, filepath):
        if not os.path.exists(self.log_file):
            return False
        with open(self.log_file, "r", encoding="utf-8") as f:
            data = [json.loads(line) for line in f if line.strip()]
        with open(filepath, "w", encoding="utf-8") as out:
            json.dump(data, out, indent=2)
        return True
