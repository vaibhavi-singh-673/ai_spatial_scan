import json

from spatialscan.report import write_html_report


def test_html_report_contains_quality_summary(tmp_path):
    source = tmp_path / "quality.json"
    target = tmp_path / "report.html"
    source.write_text(json.dumps({
        "tier": "video",
        "input": "fixtures/video",
        "score": 80,
        "readiness": "REVIEW",
        "checks": [{"name": "frames", "status": "PASS", "details": {"count": 3}}],
        "recommendations": ["Add calibration"],
    }))
    write_html_report(source, target)
    content = target.read_text()
    assert "SpatialScan capture report" in content
    assert "Add calibration" in content