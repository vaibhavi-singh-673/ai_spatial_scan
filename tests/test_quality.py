import json

from spatialscan.quality import assess_capture


def test_quality_assesses_all_fixture_tiers():
    lidar = assess_capture("fixtures/lidar_sample", "lidar")
    photos = assess_capture("fixtures/photo", "photos")
    video = assess_capture("fixtures/video", "video")

    assert lidar["readiness"] == "READY_WITH_CAVEATS"
    assert photos["readiness"] == "REVIEW"
    assert video["readiness"] == "REVIEW"
    assert all(result["checks"] for result in (lidar, photos, video))


def test_quality_accepts_declared_visual_calibration():
    result = assess_capture("fixtures/video", "video", 0.01)
    checks = {check["name"]: check for check in result["checks"]}
    assert result["readiness"] == "READY_WITH_CAVEATS"
    assert checks["metric_calibration_declared"]["status"] == "PASS"


def test_quality_output_is_json_serializable(tmp_path):
    result = assess_capture("fixtures/lidar_sample", "lidar")
    output = tmp_path / "quality.json"
    output.write_text(json.dumps(result, indent=2))
    assert json.loads(output.read_text())["tier"] == "lidar"