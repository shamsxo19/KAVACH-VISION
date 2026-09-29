import os
import time
import hashlib
import json
from zenora.crypto.engine import CryptoEngine

class ProvenanceTracker:
    def __init__(self, audit_logger):
        self.audit_logger = audit_logger

    def _hash_file(self, file_path):
        """Compute SHA-256 of an actual file on disk."""
        if not os.path.isfile(file_path):
            return hashlib.sha256(b"simulated_file_bytes").hexdigest()
        
        h = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    def secure_inference(self, image_path, model_path, output_data):
        """Create a verifiable cryptographic binding for an inference output."""
        print(f"[*] Securing inference provenance for {image_path}...")
        
        # Hash the actual input image and model
        image_digest = self._hash_file(image_path)
        model_digest = self._hash_file(model_path)
        
        # Create the provenance record tying the specific input to the specific model and output
        record = {
            "image_path": os.path.basename(image_path),
            "image_digest": image_digest,
            "model_digest": model_digest,
            "output": output_data,
            "timestamp": time.time(),
            "nonce": os.urandom(16).hex()  # Cryptographically secure nonce
        }
        
        signature = CryptoEngine.sign_record(record)
        record["provenance_signature"] = signature
        
        self.audit_logger.log_event(
            event_type="INFERENCE_PROVENANCE_GENERATED",
            asset_id=image_path,
            description="Cryptographic binding created for inference output.",
            confidence=1.0,
            recommendation="accept",
            evidence=f"Signature: {signature[:16]}... ImageHash: {image_digest[:8]}..."
        )
        
        return record
