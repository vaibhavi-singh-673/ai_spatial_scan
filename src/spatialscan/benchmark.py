import json
from time import perf_counter
from itertools import combinations
from pathlib import Path
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from zipfile import BadZipFile, ZipFile

from .evaluate import evaluate
from .incumbent import compare_incumbent
from .quality import assess_capture
from .tiers.lidar import run as lidar_run
from .tiers.visual import collect_images, collect_video_frames, estimate_visual_capture


REQUIRED_FIELDS = {
    "capture_id", "tier", "device", "rooms", "raw_path",
    "ground_truth_path", "repeat_group", "incumbent_export",
}


def _run_capture(row):
    tier=row["tier"]
    input_path=Path(row["raw_path"])
    if tier == "lidar":
        prediction=lidar_run(input_path, row["capture_id"])
    elif tier == "video":
        prediction=estimate_visual_capture(collect_video_frames(input_path), tier, row.get("scale_m_per_pixel"))
    elif tier == "photos":
        prediction=estimate_visual_capture(collect_images(input_path), tier, row.get("scale_m_per_pixel"))
    else:
        raise ValueError(f"Unsupported tier: {tier}")
    return prediction


def _resolve_manifest_path(value, manifest_file):
    """Resolve paths in the manifest, supporting project-root and relative paths.

    Benchmark manifests normally live in ``benchmarks/`` and use paths relative
    to the repository root (for example ``benchmarks/raw/capture_01``). For
    portable temporary manifests, paths relative to the manifest directory are
    accepted as a fallback.
    """
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    if manifest_file.parent.name == "benchmarks":
        return (manifest_file.parent.parent / path).resolve()
    project_relative = (manifest_file.parent.parent / path).resolve()
    return project_relative if project_relative.exists() else (manifest_file.parent / path).resolve()


@contextmanager
def _capture_directory(path):
    """Yield a capture folder, safely unpacking supported LiDAR ZIP archives."""
    path = Path(path)
    if path.is_dir():
        yield path
        return
    if not path.is_file() or path.suffix.lower() != ".zip":
        raise ValueError(f"Capture must be a folder or LiDAR ZIP archive: {path}")
    with TemporaryDirectory(prefix="spatialscan-capture-") as temporary:
        destination = Path(temporary).resolve()
        try:
            with ZipFile(path) as archive:
                for entry in archive.infolist():
                    target = (destination / entry.filename).resolve()
                    if not target.is_relative_to(destination):
                        raise ValueError(f"Unsafe archive member path: {entry.filename}")
                archive.extractall(destination)
        except BadZipFile as error:
            raise ValueError(f"Invalid ZIP archive: {path}") from error
        metadata = [file.parent for file in destination.rglob("camera_matrix.csv")
                    if (file.parent / "odometry.csv").is_file()
                    and (file.parent / "imu.csv").is_file()]
        if len(metadata) != 1:
            raise ValueError("ZIP must contain exactly one LiDAR folder with camera_matrix.csv, odometry.csv, and imu.csv")
        yield metadata[0]


def _repeat_values(prediction, room_id):
    room = next((item for item in prediction.get("rooms", []) if item.get("id") == room_id), None)
    if room is None:
        return None
    return {
        "floor_area_m2": room.get("floor_area_m2", {}).get("value"),
        "ceiling_height_m": room.get("ceiling_height_m", {}).get("value"),
        "wall_lengths_m": [item.get("value") for item in room.get("walls", [])],
        "opening_widths_m": {
            item.get("id", str(index)): item.get("width", {}).get("value")
            for index, item in enumerate(room.get("openings", []))
        },
    }


def _compare_repeat_pair(first, second, tolerances):
    if first["tier"] != second["tier"]:
        return {"status": "NOT_RUN", "reason": "repeat pair tiers differ"}
    left, right = first["prediction"], second["prediction"]
    left_rooms = {room.get("id") for room in left.get("rooms", [])}
    right_rooms = {room.get("id") for room in right.get("rooms", [])}
    room_ids = sorted((left_rooms & right_rooms) - {None})
    if not room_ids or left_rooms != right_rooms:
        return {"status": "NOT_RUN", "reason": "repeat pair room coverage differs or is empty"}

    samples = {"floor_area_relative": [], "ceiling_height_m": [],
               "wall_length_m": [], "opening_width_m": []}
    complete = {name: True for name in samples}
    for room_id in room_ids:
        a, b = _repeat_values(left, room_id), _repeat_values(right, room_id)
        av, bv = a["floor_area_m2"], b["floor_area_m2"]
        if av is not None and bv is not None and max(abs(av), abs(bv)) > 0:
            samples["floor_area_relative"].append(abs(av-bv) / max(abs(av), abs(bv)))
        av, bv = a["ceiling_height_m"], b["ceiling_height_m"]
        if av is not None and bv is not None:
            samples["ceiling_height_m"].append(abs(av-bv))
        if len(a["wall_lengths_m"]) == len(b["wall_lengths_m"]):
            samples["wall_length_m"].extend(abs(x-y) for x, y in zip(a["wall_lengths_m"], b["wall_lengths_m"])
                                             if x is not None and y is not None)
            complete["wall_length_m"] &= all(x is not None and y is not None
                                               for x, y in zip(a["wall_lengths_m"], b["wall_lengths_m"]))
        else:
            complete["wall_length_m"] = False
        if a["opening_widths_m"].keys() == b["opening_widths_m"].keys():
            samples["opening_width_m"].extend(abs(a["opening_widths_m"][key] - b["opening_widths_m"][key])
                                                for key in a["opening_widths_m"]
                                                if a["opening_widths_m"][key] is not None
                                                and b["opening_widths_m"][key] is not None)
            complete["opening_width_m"] &= all(a["opening_widths_m"][key] is not None
                                                 and b["opening_widths_m"][key] is not None
                                                 for key in a["opening_widths_m"])
        else:
            complete["opening_width_m"] = False

    metrics = {}
    for name, values in samples.items():
        if not values or not complete[name]:
            metrics[name] = {"status": "NOT_RUN", "reason": "measurements missing or incomplete"}
            continue
        tolerance = tolerances.get(name)
        maximum = max(values)
        metrics[name] = {"status": "PASS" if maximum <= tolerance else "FAIL" if tolerance is not None else "REVIEW",
                         "max_delta": maximum, "measurement_count": len(values), "tolerance": tolerance}
    states = [item["status"] for item in metrics.values()]
    status = "NOT_RUN" if all(value == "NOT_RUN" for value in states) else (
        "FAIL" if "FAIL" in states else "REVIEW" if "REVIEW" in states or "NOT_RUN" in states else "PASS")
    return {"status": status, "capture_ids": [first["capture_id"], second["capture_id"]],
            "room_ids": room_ids, "metrics": metrics}


def _repeatability_report(captures, tolerances):
    groups = {}
    for capture in captures:
        group = capture.get("repeat_group")
        if group and capture.get("prediction") is not None:
            groups.setdefault(group, []).append(capture)
    report = {}
    for group, members in groups.items():
        report[group] = {
            "pairs": [_compare_repeat_pair(a, b, tolerances) for a, b in combinations(members, 2)]
        }
        states = [pair["status"] for pair in report[group]["pairs"]]
        report[group]["status"] = "FAIL" if "FAIL" in states else "PASS" if states and all(
            state == "PASS" for state in states) else "REVIEW" if states else "NOT_RUN"
    return report


def run_benchmark(manifest_path, output_path=None):
    manifest_file=Path(manifest_path)
    manifest=json.loads(manifest_file.read_text())
    rows=manifest.get("captures", [])
    results=[]
    repeat_captures=[]
    for row in rows:
        missing=sorted(REQUIRED_FIELDS-set(row))
        result={"capture_id": row.get("capture_id"), "tier": row.get("tier"),
            "quality": None, "evaluation": None}
        if missing:
            result.update({"status": "INVALID", "missing_fields": missing})
            results.append(result)
            continue
        raw_path=_resolve_manifest_path(row["raw_path"], manifest_file)
        if not raw_path.exists():
            result.update({"status": "NOT_RUN", "reason": "raw capture not present", "raw_path": str(raw_path)})
            results.append(result)
            continue
        try:
            started = perf_counter()
            with _capture_directory(raw_path) as capture_dir:
                quality=assess_capture(capture_dir, row["tier"], row.get("scale_m_per_pixel"))
                quality["input"] = str(raw_path)
                prediction=_run_capture({**row, "raw_path": capture_dir})
            processing_seconds = perf_counter() - started
            repeat_captures.append({**row, "prediction": prediction})
            ground_truth=(_resolve_manifest_path(row["ground_truth_path"], manifest_file)
                          if row.get("ground_truth_path") else None)
            prediction_file=manifest_file.parent / "results" / f"{row['capture_id']}_prediction.json"
            prediction_file.parent.mkdir(parents=True, exist_ok=True)
            prediction_file.write_text(json.dumps(prediction, indent=2), encoding="utf-8")
            evaluation=None
            if ground_truth and ground_truth.exists():
                evaluation=evaluate(prediction_file, ground_truth)
            incumbent=(_resolve_manifest_path(row["incumbent_export"], manifest_file)
                       if row.get("incumbent_export") else None)
            comparison = None
            normalized_export = row.get("incumbent_measurements")
            if ground_truth and ground_truth.exists() and incumbent and incumbent.exists() and normalized_export:
                normalized_path = _resolve_manifest_path(normalized_export, manifest_file)
                if normalized_path.exists():
                    comparison = compare_incumbent(
                        prediction, json.loads(ground_truth.read_text(encoding="utf-8")), normalized_path
                    )
            result.update({
                "status": "PASS" if evaluation and evaluation["status"] == "PASS" else "NOT_RUN" if evaluation is None else "FAIL",
                "quality": quality,
                "pipeline_status": "COMPLETED",
                "prediction_path": str(prediction_file),
                "processing_seconds": processing_seconds,
                "performance_evidence": "local_recorded_capture_processing_only",
                "evaluation": evaluation,
                "ground_truth": str(ground_truth) if ground_truth else None,
                "ground_truth_status": "AVAILABLE" if ground_truth and ground_truth.exists() else "NOT_RUN",
                "incumbent_export": str(incumbent) if incumbent else None,
                "incumbent_status": "AVAILABLE" if incumbent and incumbent.exists() else "NOT_RUN",
                "incumbent_comparison": comparison or {"status": "NOT_RUN", "reason":
                    "add an incumbent_measurements CSV and measured ground truth"},
                "evidence_class": "measured" if ground_truth and ground_truth.exists()
                    else row.get("evidence_class", "pipeline_smoke_only"),
            })
        except (OSError, ValueError, KeyError) as error:
            result.update({"status": "ERROR", "reason": str(error)})
        results.append(result)
    tolerances = manifest.get("repeatability_tolerances", {})
    report={"schema_version": "1.0", "manifest": str(manifest_file), "captures": results,
            "repeatability": _repeatability_report(repeat_captures, tolerances),
            "repeatability_tolerances": tolerances}
    if output_path:
        destination=Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2))
    return report
