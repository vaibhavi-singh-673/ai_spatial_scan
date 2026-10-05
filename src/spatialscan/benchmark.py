import json
from pathlib import Path

from .evaluate import evaluate
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


def run_benchmark(manifest_path, output_path=None):
    manifest_file=Path(manifest_path)
    manifest=json.loads(manifest_file.read_text())
    rows=manifest.get("captures", [])
    results=[]
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
            quality=assess_capture(raw_path, row["tier"], row.get("scale_m_per_pixel"))
            prediction=_run_capture({**row, "raw_path": raw_path})
            ground_truth=_resolve_manifest_path(row["ground_truth_path"], manifest_file)
            evaluation=None
            if ground_truth.exists():
                prediction_file=manifest_file.parent / "results" / f"{row['capture_id']}_prediction.json"
                prediction_file.parent.mkdir(parents=True, exist_ok=True)
                prediction_file.write_text(json.dumps(prediction, indent=2))
                evaluation=evaluate(prediction_file, ground_truth)
            incumbent=_resolve_manifest_path(row["incumbent_export"], manifest_file)
            result.update({
                "status": "PASS" if evaluation and evaluation["status"] == "PASS" else "NOT_RUN" if evaluation is None else "FAIL",
                "quality": quality,
                "evaluation": evaluation,
                "ground_truth": str(ground_truth),
                "ground_truth_status": "AVAILABLE" if ground_truth.exists() else "NOT_RUN",
                "incumbent_export": str(incumbent),
                "incumbent_status": "AVAILABLE" if incumbent.exists() else "NOT_RUN",
                "evidence_class": "measured" if ground_truth.exists() else "pipeline_smoke_only",
            })
        except (OSError, ValueError, KeyError) as error:
            result.update({"status": "ERROR", "reason": str(error)})
        results.append(result)
    report={"schema_version": "1.0", "manifest": str(manifest_file), "captures": results}
    if output_path:
        destination=Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2))
    return report
