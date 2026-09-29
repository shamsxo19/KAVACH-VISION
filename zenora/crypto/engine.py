import hashlib
import json
import time

class CryptoEngine:
    @staticmethod
    def compute_digest(file_path):
        """Compute SHA-256 digest of a file (simulated)."""
        hasher = hashlib.sha256()
        # In a real scenario, we read the file in chunks.
        # For prototype, we just hash the path and time if file doesn't exist.
        try:
            with open(file_path, 'rb') as f:
                hasher.update(f.read())
        except Exception:
            hasher.update(file_path.encode())
            hasher.update(str(time.time()).encode())
        return hasher.hexdigest()

    @staticmethod
    def sign_record(data, secret_key="ZENORA_SECRET"):
        """Sign a dictionary of data."""
        data_string = json.dumps(data, sort_keys=True) + secret_key
        return hashlib.sha256(data_string.encode()).hexdigest()
