import os
import time
import json
import uuid
from datetime import datetime
from zenora.crypto.engine import CryptoEngine

class ProvenanceTracker:
    def __init__(self, audit_logger, chain_file="provenance_chain.jsonl"):
        self.audit_logger = audit_logger
        self.chain_file = os.path.join(audit_logger.log_dir, chain_file)
        self._seen_nonces = set()

    def _get_last_entry(self):
        if not os.path.exists(self.chain_file):
            return None
        last_line = None
        with open(self.chain_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last_line = line.strip()
        if last_line:
            try:
                return json.loads(last_line)
            except json.JSONDecodeError:
                return None
        return None
        
    def _calculate_record_hash(self, record):
        content = {k: v for k, v in record.items() if k not in ["record_hash", "signature"]}
        canonical_str = json.dumps(content, sort_keys=True, separators=(',', ':'))
        return CryptoEngine.hash_string(canonical_str)

    def create_provenance_record(self, image_path, model_path, output_data, preproc_config=None, infer_config=None):
        """Create a verifiable cryptographic binding for an inference output."""
        print(f"[*] Securing inference provenance for {os.path.basename(image_path)}...")
        
        # Hash the actual input image and model. Strict!
        image_digest = CryptoEngine.compute_digest(image_path)
        model_digest = CryptoEngine.compute_digest(model_path)
        
        preproc_config = preproc_config or {"resize": [224, 224], "normalize": True}
        infer_config = infer_config or {"batch_size": 1, "precision": "fp32"}
        
        preproc_hash = CryptoEngine.hash_string(json.dumps(preproc_config, sort_keys=True))
        infer_hash = CryptoEngine.hash_string(json.dumps(infer_config, sort_keys=True))
        output_hash = CryptoEngine.hash_string(json.dumps(output_data, sort_keys=True))
        
        last_entry = self._get_last_entry()
        sequence = 0
        previous_hash = "GENESIS"
        if last_entry:
            sequence = last_entry.get("sequence", -1) + 1
            previous_hash = last_entry.get("record_hash", "UNKNOWN")
            
        nonce = uuid.uuid4().hex
        
        # Format mapping based on extension
        model_format = "PyTorch" if model_path.endswith((".pt", ".pth")) else "ONNX" if model_path.endswith(".onnx") else "Unknown"

        record = {
            "sequence": sequence,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "nonce": nonce,
            "image_path": os.path.basename(image_path),
            "input_hash": image_digest,
            "model_id": os.path.basename(model_path),
            "model_hash": model_digest,
            "model_format": model_format,
            "preproc_config": preproc_config,
            "preproc_hash": preproc_hash,
            "infer_config": infer_config,
            "infer_hash": infer_hash,
            "output_data": output_data,
            "output_hash": output_hash,
            "previous_hash": previous_hash
        }
        
        record_hash = self._calculate_record_hash(record)
        record["record_hash"] = record_hash
        
        signable_content = {k: v for k, v in record.items() if k != "signature"}
        signature = CryptoEngine.sign_record(signable_content)
        record["signature"] = signature
        
        with open(self.chain_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
            
        self.audit_logger.append(
            event_type="INFERENCE_PROVENANCE_GENERATED",
            actor="SYSTEM",
            asset_id=os.path.basename(image_path),
            payload={"record_hash": record_hash, "signature_prefix": signature[:16]}
        )
        
        return record

    def verify_provenance_record(self, record):
        """Verify an individual provenance record for internal consistency and signature."""
        # Check Signature
        signable_content = {k: v for k, v in record.items() if k != "signature"}
        signature = record.get("signature", "")
        if not CryptoEngine.verify_signature(signable_content, signature):
            return {"valid": False, "reason": "Invalid digital signature"}
            
        # Check Record Hash
        calc_hash = self._calculate_record_hash(record)
        if calc_hash != record.get("record_hash"):
            return {"valid": False, "reason": "Record hash mismatch (Data Tampering)"}
            
        # Check internal hashes
        if CryptoEngine.hash_string(json.dumps(record.get("preproc_config"), sort_keys=True)) != record.get("preproc_hash"):
            return {"valid": False, "reason": "Preprocessing config hash mismatch"}
            
        if CryptoEngine.hash_string(json.dumps(record.get("infer_config"), sort_keys=True)) != record.get("infer_hash"):
            return {"valid": False, "reason": "Inference config hash mismatch"}
            
        if CryptoEngine.hash_string(json.dumps(record.get("output_data"), sort_keys=True)) != record.get("output_hash"):
            return {"valid": False, "reason": "Output data hash mismatch (Output Tampering)"}
            
        return {"valid": True, "reason": "Record is internally consistent and cryptographically secure"}

    def verify_provenance_chain(self):
        """Verify the entire provenance chain for replay attacks and broken links."""
        if not os.path.exists(self.chain_file):
            return {"status": "VALID", "message": "Provenance chain is empty.", "entries": 0}
            
        entries = []
        with open(self.chain_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        entries.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        return {"status": "INVALID", "message": "Corrupted JSON format detected in provenance file."}
                        
        if not entries:
            return {"status": "VALID", "message": "Chain is empty.", "entries": 0}
            
        expected_prev_hash = "GENESIS"
        expected_seq = 0
        seen_nonces = set()
        
        for idx, entry in enumerate(entries):
            # Verify individual record
            single_check = self.verify_provenance_record(entry)
            if not single_check["valid"]:
                return {"status": "INVALID", "message": f"Sequence {expected_seq}: {single_check['reason']}", "failed_at": idx}
                
            # Sequence
            if entry.get("sequence") != expected_seq:
                return {"status": "INVALID", "message": f"Sequence out of order. Expected {expected_seq}, got {entry.get('sequence')}", "failed_at": idx}
                
            # Hash Link
            if entry.get("previous_hash") != expected_prev_hash:
                return {"status": "INVALID", "message": f"Broken provenance hash link at sequence {expected_seq}.", "failed_at": idx}
                
            # Replay Detection (Nonce reuse)
            nonce = entry.get("nonce")
            if nonce in seen_nonces:
                return {"status": "INVALID", "message": f"Replay Attack Detected: Nonce {nonce} reused at sequence {expected_seq}.", "failed_at": idx}
            seen_nonces.add(nonce)
                
            expected_seq += 1
            expected_prev_hash = entry.get("record_hash")
            
        return {"status": "VALID", "message": "Provenance chain is completely valid.", "entries": len(entries)}
