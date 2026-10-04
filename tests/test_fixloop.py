import json

from spatialscan.fixloop import run_fix_loop


def test_fixloop_writes_before_after_ablation(tmp_path):
    output=tmp_path / "fixloop.json"
    report=run_fix_loop("fixtures/lidar_sample", output)
    assert report["status"] == "ABLATION_ONLY"
    assert report["ground_truth_status"] == "NOT_AVAILABLE"
    assert "area_m2" in report["delta"]
    assert json.loads(output.read_text())["after"]["method"].startswith("pose")