import os
import json
import hashlib
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

class CryptoEngine:
    """Provides genuine cryptographic primitives for KAVACH-VISION."""
    
    KEY_DIR = os.path.expanduser("~/.kavach/keys")
    PRIVATE_KEY_PATH = os.path.join(KEY_DIR, "kavach_ed25519.pem")
    PUBLIC_KEY_PATH = os.path.join(KEY_DIR, "kavach_ed25519.pub")

    @classmethod
    def _ensure_keys(cls):
        """Ensures that an Ed25519 keypair exists, generating one if not."""
        if not os.path.exists(cls.KEY_DIR):
            os.makedirs(cls.KEY_DIR, exist_ok=True)
            
        if not os.path.exists(cls.PRIVATE_KEY_PATH) or not os.path.exists(cls.PUBLIC_KEY_PATH):
            private_key = ed25519.Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            
            with open(cls.PRIVATE_KEY_PATH, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
                
            with open(cls.PUBLIC_KEY_PATH, "wb") as f:
                f.write(public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))

    @classmethod
    def _get_private_key(cls):
        cls._ensure_keys()
        with open(cls.PRIVATE_KEY_PATH, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)

    @classmethod
    def get_public_key(cls):
        cls._ensure_keys()
        with open(cls.PUBLIC_KEY_PATH, "rb") as f:
            return serialization.load_pem_public_key(f.read())

    @classmethod
    def get_public_key_fingerprint(cls):
        public_key = cls.get_public_key()
        pub_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return hashlib.sha256(pub_bytes).hexdigest()[:16]

    @staticmethod
    def compute_digest(file_path):
        """Compute strict SHA-256 digest of a file. Returns error if not found."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Cannot compute digest: {file_path} not found.")
            
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
        
    @staticmethod
    def hash_string(data_str: str) -> str:
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

    @classmethod
    def sign_record(cls, data: dict) -> str:
        """Sign a dictionary of data using Ed25519."""
        private_key = cls._get_private_key()
        # Ensure deterministic JSON serialization
        canonical_data = json.dumps(data, sort_keys=True, separators=(',', ':'))
        signature = private_key.sign(canonical_data.encode('utf-8'))
        return signature.hex()

    @classmethod
    def verify_signature(cls, data: dict, signature_hex: str) -> bool:
        """Verify an Ed25519 signature for a dictionary."""
        public_key = cls.get_public_key()
        canonical_data = json.dumps(data, sort_keys=True, separators=(',', ':'))
        try:
            public_key.verify(bytes.fromhex(signature_hex), canonical_data.encode('utf-8'))
            return True
        except InvalidSignature:
            return False
        except Exception:
            return False
