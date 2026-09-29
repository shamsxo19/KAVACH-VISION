class RiskEngine:
    """Central Risk & Governance Engine for KAVACH-VISION."""
    def __init__(self, audit_logger):
        self.audit_logger = audit_logger

    def evaluate(self, all_findings):
        """Evaluate findings and determine disposition based on severity/confidence rules."""
        evaluated_findings = []
        overall_risk_score = 0
        
        # Severity weights
        weights = {"critical": 100, "high": 50, "medium": 10, "low": 2, "info": 0}

        for finding in all_findings:
            sev = finding.get("severity", "info").lower()
            conf = finding.get("confidence", 0.0)
            
            # Decide Disposition
            disposition = "ACCEPT"
            if sev == "critical":
                disposition = "QUARANTINE" if conf > 0.8 else "REVIEW"
            elif sev == "high":
                disposition = "QUARANTINE" if conf > 0.9 else "REVIEW"
            elif sev == "medium":
                disposition = "REVIEW" if conf > 0.7 else "ACCEPT"
            elif sev == "low":
                disposition = "ACCEPT"
                
            finding["recommended_disposition"] = disposition
            
            # Keep original fields but ensure disposition is prominent
            evaluated_findings.append(finding)
            
            # Aggregate score
            overall_risk_score += (weights.get(sev, 0) * conf)

        # Global Status
        if overall_risk_score > 100:
            status = "CRITICAL_RISK"
        elif overall_risk_score > 50:
            status = "HIGH_RISK"
        elif overall_risk_score > 10:
            status = "MODERATE_RISK"
        else:
            status = "ACCEPTABLE"

        return {
            "status": status,
            "risk_score": float(overall_risk_score),
            "findings": evaluated_findings
        }
