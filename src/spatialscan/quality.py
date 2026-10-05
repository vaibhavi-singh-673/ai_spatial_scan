from pathlib import Path

import cv2

from .io.lidar import load_lidar
from .tiers.visual import collect_images, collect_video_frames


VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".avi"}


def _check(name, passed, weight, details, blocking=False):
    return {
        "name": name,
        "status": "PASS" if passed else "FAIL",
        "weight": weight,
        "details": details,
        "blocking": blocking,
    }


def _visual_quality(folder, tier, scale_m_per_pixel=None):
    root = Path(folder)
    if tier == "video":
        files = sorted(
            path for path in root.rglob("*") if path.suffix.lower() in VIDEO_SUFFIXES
        ) if root.is_dir() else [root]
        frames = collect_video_frames(root)
        checks = [
            _check("video_file_found", bool(files), 20,
                   {"files": [str(path.relative_to(root)) for path in files]} , True),
            _check("frames_decoded", bool(frames), 35,
                   {"decoded_frames": len(frames)}, True),
            _check("minimum_frame_count", len(frames) >= 3, 15,
                   {"decoded_frames": len(frames), "minimum": 3}),
        ]
        sample = frames[0] if frames else None
    else:
        images = collect_images(root)
        decoded = [cv2.imread(str(path)) for path in images]
        decoded = [image for image in decoded if image is not None]
        checks = [
            _check("image_found", bool(images), 20,
                   {"files": [str(path.relative_to(root)) for path in images]}, True),
            _check("images_decoded", bool(decoded), 35,
                   {"decoded_images": len(decoded)}, True),
            _check("room_view_count", 2 <= len(decoded) <= 8, 15,
                   {"decoded_images": len(decoded), "recommended_range": [2, 8]}),
        ]
        sample = decoded[0] if decoded else None

    checks.append(_check(
        "usable_resolution",
        sample is not None and sample.shape[1] >= 640 and sample.shape[0] >= 480,
        10,
        {"width": int(sample.shape[1]), "height": int(sample.shape[0])} if sample is not None else {},
    ))
    checks.append(_check(
        "metric_calibration_declared",
        scale_m_per_pixel is not None and scale_m_per_pixel > 0,
        20,
        {"scale_m_per_pixel": scale_m_per_pixel} if scale_m_per_pixel else
        {"reason": "Monocular scale requires a measured reference or calibration source"},
    ))
    return checks


def _lidar_quality(folder):
    root = Path(folder)
    required = ["camera_matrix.csv", "odometry.csv", "imu.csv"]
    missing = [name for name in required if not (root / name).exists()]
    checks = [_check("required_metadata", not missing, 25, {"missing": missing}, True)]
    if missing:
        return checks
    try:
        depth_paths = sorted((root / "depth").glob("*.png"))
        sampled_total = min(len(depth_paths), 120)
        K, frames, imu = load_lidar(root, max_frames=120)
        depth_frames = sum(frame[1] is not None for frame in frames)
        confidence_frames = sum(frame[2] is not None for frame in frames)
        pose_frames = sum(frame[3] is not None for frame in frames)
        checks.extend([
            _check("camera_matrix", K.shape == (3, 3), 20, {"shape": list(K.shape)}, True),
            _check("depth_frames_decoded", depth_frames > 0, 25,
                   {"decoded_sample": depth_frames, "sampled_total": sampled_total,
                    "available_total": len(depth_paths), "sampling_limit": 120}, True),
            _check("confidence_coverage", confidence_frames == depth_frames, 10,
                   {"with_confidence": confidence_frames, "sampled_depth_frames": depth_frames}),
            _check("pose_coverage", pose_frames == depth_frames, 10,
                   {"with_pose": pose_frames, "sampled_depth_frames": depth_frames}),
            _check("imu_samples", len(imu) > 0, 10, {"samples": len(imu)}),
        ])
    except (OSError, ValueError, TypeError) as error:
        checks.append(_check("lidar_decodes", False, 50, {"error": str(error)}, True))
    return checks


def assess_capture(folder, tier, scale_m_per_pixel=None):
    if tier not in {"photos", "video", "lidar"}:
        raise ValueError(f"Unsupported tier: {tier}")
    checks = (_lidar_quality(folder) if tier == "lidar"
              else _visual_quality(folder, tier, scale_m_per_pixel))
    total_weight = sum(check["weight"] for check in checks)
    earned_weight = sum(check["weight"] for check in checks if check["status"] == "PASS")
    score = round(100 * earned_weight / total_weight) if total_weight else 0
    blocking_failures = [check["name"] for check in checks if check["blocking"] and check["status"] == "FAIL"]
    calibration_missing = any(
        check["name"] == "metric_calibration_declared" and check["status"] == "FAIL"
        for check in checks
    )
    if blocking_failures:
        readiness = "BLOCKED"
    elif calibration_missing:
        readiness = "REVIEW"
    elif score >= 80:
        readiness = "READY_WITH_CAVEATS"
    else:
        readiness = "REVIEW"
    recommendations = []
    if tier in {"photos", "video"} and calibration_missing:
        recommendations.append("Add a measured scale reference before making metric accuracy claims.")
    for check in checks:
        if check["status"] == "FAIL" and check["name"] != "metric_calibration_declared":
            recommendations.append(f"Fix {check['name']}: {check['details']}.")
    return {
        "schema_version": "1.0",
        "tier": tier,
        "input": str(Path(folder)),
        "readiness": readiness,
        "score": score,
        "checks": checks,
        "recommendations": recommendations,
    }
