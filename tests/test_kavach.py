import os
import json
import pytest
from zenora.crypto.engine import CryptoEngine
from zenora.audit.trail import AuditLogger
from zenora.core.inference_provenance import ProvenanceTracker

def test_crypto_engine_signatures():
    data = {"hello": "world", "timestamp": 12345}
    signature = CryptoEngine.sign_record(data)
    assert CryptoEngine.verify_signature(data, signature) == True
    
    # Tamper detection
    tampered = {"hello": "world", "timestamp": 12346}
    assert CryptoEngine.verify_signature(tampered, signature) == False

def test_crypto_engine_digest():
    with open("test_file.txt", "w") as f:
        f.write("KAVACH-VISION")
    digest = CryptoEngine.compute_digest("test_file.txt")
    assert digest is not None
    os.remove("test_file.txt")

def test_audit_chain_valid():
    logger = AuditLogger(log_dir="test_logs", chain_file="test_chain.jsonl")
    if os.path.exists(logger.log_file):
        os.remove(logger.log_file)
        
    logger.append("TEST_EVENT", "SYSTEM", "asset1", {"data": "test1"})
    logger.append("TEST_EVENT", "SYSTEM", "asset2", {"data": "test2"})
    
    res = logger.verify_chain()
    assert res["status"] == "VALID"
    
def test_audit_chain_tampered():
    logger = AuditLogger(log_dir="test_logs", chain_file="test_chain_tamp.jsonl")
    if os.path.exists(logger.log_file):
        os.remove(logger.log_file)
        
    logger.append("TEST_EVENT", "SYSTEM", "asset1", {"data": "test1"})
    
    # Manually tamper the file
    with open(logger.log_file, "r") as f:
        lines = f.readlines()
        
    entry = json.loads(lines[0])
    entry["payload"]["data"] = "TAMPERED"
    
    with open(logger.log_file, "w") as f:
        f.write(json.dumps(entry) + "\n")
        
    res = logger.verify_chain()
    assert res["status"] == "INVALID"
    
def test_provenance_tracker():
    logger = AuditLogger(log_dir="test_logs", chain_file="prov_audit.jsonl")
    tracker = ProvenanceTracker(logger, chain_file="test_prov.jsonl")
    
    if os.path.exists(tracker.chain_file):
        os.remove(tracker.chain_file)
        
    with open("dummy_img.jpg", "w") as f: f.write("img")
    with open("dummy_mod.pt", "w") as f: f.write("mod")
    
    record = tracker.create_provenance_record(
        "dummy_img.jpg", "dummy_mod.pt", {"out": "ok"}
    )
    
    assert record is not None
    assert tracker.verify_provenance_record(record)["valid"] == True
    
    # Tamper output
    record["output_data"] = {"out": "hacked"}
    assert tracker.verify_provenance_record(record)["valid"] == False
    
    os.remove("dummy_img.jpg")
    os.remove("dummy_mod.pt")
