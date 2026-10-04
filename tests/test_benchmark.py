import json

from spatialscan.benchmark import run_benchmark


def test_benchmark_marks_missing_capture_not_run(tmp_path):
    manifest=tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "version": 1,
        "captures": [{
            "capture_id": "missing",
            "tier": "lidar",
            "device": "test",
            "rooms": ["R1"],
            "raw_path": "raw/missing",
            "ground_truth_path": "gt.json",
            "repeat_group": "repeat",
            "incumbent_export": "incumbent.zip",
        }],
    }))
    report=run_benchmark(manifest)
    assert report["captures"][0]["status"] == "NOT_RUN"


def test_benchmark_runs_fixture_without_ground_truth(tmp_path):
    manifest=tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "version": 1,
        "captures": [{
            "capture_id": "fixture",
            "tier": "lidar",
            "device": "test",
            "rooms": ["R1"],
            "raw_path": "../../fixtures/lidar_sample",
            "ground_truth_path": "missing.json",
            "repeat_group": "repeat",
            "incumbent_export": "incumbent.zip",
        }],
    }))
    report=run_benchmark(manifest)
    assert report["captures"][0]["status"] == "NOT_RUN"
    assert report["captures"][0]["evaluation"] is None