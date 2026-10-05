import json
import copy
import tempfile
from pathlib import Path

from .io.lidar import load_lidar
from .geometry.lidar_recon import reconstruct_lidar
from .tiers.lidar import run as lidar_run
from .evaluate import evaluate


def run_fix_loop(input_dir, output_path, ground_truth_path=None):
    K, frames, imu=load_lidar(input_dir,max_frames=120)
    fixed=reconstruct_lidar(K, frames, imu)
    unnormalized=[(frame, depth, confidence, None) for frame, depth, confidence, _ in frames]
    baseline=reconstruct_lidar(K, unnormalized, None)
    after_prediction = lidar_run(input_dir, "after_fix")
    # Build a comparable baseline prediction from the exact same raw frames,
    # with the pose/IMU correction disabled in the reconstruction call above.
    before_prediction = copy.deepcopy(after_prediction)
    before_room = before_prediction["rooms"][0]
    before_room["floor_area_m2"]["value"] = baseline["area"]
    before_room["ceiling_height_m"]["value"] = baseline["ceiling"]
    wall_template = before_room["walls"][0] if before_room["walls"] else None
    before_room["walls"] = []
    for index, baseline_wall in enumerate(baseline["walls"], start=1):
        wall = copy.deepcopy(wall_template) if wall_template else {
            "kind": "wall_length", "room_id": before_room["id"], "unit": "m"
        }
        wall.update({"id": f"wall_{index}", "value": baseline_wall[2]})
        before_room["walls"].append(wall)
    before_room["polygon_xy_m"] = baseline["polygon"].tolist()
    before_prediction["plan"]["stitched_polygon_xy_m"] = baseline["polygon"].tolist()
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
    if ground_truth_path:
        truth_path = Path(ground_truth_path)
        if not truth_path.exists():
            raise FileNotFoundError(f"Ground truth not found: {truth_path}")
        truth = json.loads(truth_path.read_text(encoding="utf-8"))
        truth_rooms = truth.get("rooms", [])
        if len(truth_rooms) == 1:
            truth_room_id = truth_rooms[0].get("id")
            for prediction in (before_prediction, after_prediction):
                if len(prediction.get("rooms", [])) == 1 and truth_room_id:
                    prediction["rooms"][0]["id"] = truth_room_id
                    prediction["plan"]["rooms"][0]["id"] = truth_room_id
        with tempfile.TemporaryDirectory(prefix="spatialscan-fixloop-") as temp_dir:
            before_path = Path(temp_dir) / "before.json"
            after_path = Path(temp_dir) / "after.json"
            before_path.write_text(json.dumps(before_prediction), encoding="utf-8")
            after_path.write_text(json.dumps(after_prediction), encoding="utf-8")
            before_eval = evaluate(before_path, truth_path)
            after_eval = evaluate(after_path, truth_path)
        before_gates = before_eval.get("gates", {})
        after_gates = after_eval.get("gates", {})
        gate_delta = {}
        for name in sorted(set(before_gates) | set(after_gates)):
            before_gate, after_gate = before_gates.get(name, {}), after_gates.get(name, {})
            numeric_fields = {key for key, value in before_gate.items()
                              if isinstance(value, (int, float)) and not isinstance(value, bool)
                              and isinstance(after_gate.get(key), (int, float))}
            gate_delta[name] = {
                "before": before_gate.get("status", "NOT_RUN"),
                "after": after_gate.get("status", "NOT_RUN"),
                "numeric_delta_after_minus_before": {
                    key: after_gate[key] - before_gate[key] for key in sorted(numeric_fields)
                },
            }
        report.update({"status": "MEASURED_FIX_LOOP", "ground_truth_status": "AVAILABLE",
                       "before_evaluation": before_eval, "after_evaluation": after_eval,
                       "gate_delta": gate_delta})
        report["interpretation"] = (
            "Before and after predictions were evaluated against the supplied ground truth on identical raw data."
        )
    destination=Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2))
    return report
