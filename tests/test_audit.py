from spatialscan.audit import audit_submission


def test_audit_reports_missing_external_evidence():
    report = audit_submission(".")
    assert report["status"] == "READY_FOR_COLLECTION"
    assert report["evidence_score"] < 50
    names = {item["name"]: item for item in report["rubric"]}
    assert names["walk_in"]["status"] == "BLOCKED"
    assert names["incumbent"]["status"] == "BLOCKED"