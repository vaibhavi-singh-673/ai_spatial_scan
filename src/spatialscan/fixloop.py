import json
from pathlib import Path

from .io.lidar import load_lidar
from .geometry.lidar_recon import reconstruct_lidar


def run_fix_loop(input_dir, output_path):
    K, frames, imu=load_lidar(input_dir)
    fixed=reconstruct_lidar(K, frames, imu)
    unnormalized=[(frame, depth, confidence, None) for frame, depth, confidence, _ in frames]
    baseline=reconstruct_lidar(K, unnormalized, None)
    report={
        "schema_version": "1.0",
        "input": str(Path(input_dir)),
        "status": "ABLATION_ONLY",
        "ground_truth_status": "NOT_AVAILABLE",
        "before": {
            "method": "single camera frame; poses and IMU disabled",
            "area_m2": baseline["area"],
            "ceiling_m": baseline["ceiling"],
        },
        "after": {
            "method": "pose-normalized points with IMU gravity constraint",
            "area_m2": fixed["area"],
            "ceiling_m": fixed["ceiling"],
        },
        "delta": {
            "area_m2": fixed["area"]-baseline["area"],
            "ceiling_m": fixed["ceiling"]-baseline["ceiling"],
        },
        "interpretation": "This demonstrates a deterministic fix-loop delta. It is not an accuracy result without laser/tape ground truth.",
    }
    destination=Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2))
    return report