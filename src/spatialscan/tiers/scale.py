"""Evidence-aware scale calibration for visual captures.

Camera intrinsics alone constrain viewing geometry but cannot recover absolute
monocular scale. This module only returns a metric scale when an explicit
measured calibration or a configured known-size reference is present.
"""
import json
from pathlib import Path

import cv2
import numpy as np


METADATA_NAMES = ("spatialscan_capture.json", "capture_metadata.json")


def _metadata_for(images, metadata_path=None):
    if metadata_path:
        candidate = Path(metadata_path)
        if candidate.is_file():
            try:
                value = json.loads(candidate.read_text(encoding="utf-8"))
                return candidate, value if isinstance(value, dict) else {}
            except (OSError, json.JSONDecodeError):
                return candidate, {}
    checked = set()
    for image in images:
        parent = Path(image).parent
        for folder in (parent, *parent.parents[:4]):
            for name in METADATA_NAMES:
                candidate = folder / name
                if candidate in checked:
                    continue
                checked.add(candidate)
                if candidate.is_file():
                    try:
                        value = json.loads(candidate.read_text(encoding="utf-8"))
                        if isinstance(value, dict):
                            return candidate, value
                    except (OSError, json.JSONDecodeError):
                        continue
    return None, {}


def _qr_scale(images, marker_size_m, marker_uncertainty_m=0.0):
    if not marker_size_m or marker_size_m <= 0:
        return []
    detector = cv2.QRCodeDetector()
    scales = []
    for image in images:
        if not isinstance(image, Path):
            continue
        frame = cv2.imread(str(image))
        if frame is None:
            continue
        ok, points = detector.detect(frame)
        if not ok or points is None:
            continue
        corners = np.asarray(points, dtype=float).reshape(-1, 4, 2)
        for quad in corners:
            edges = np.linalg.norm(quad - np.roll(quad, -1, axis=0), axis=1)
            px = float(np.median(edges))
            if px > 2:
                scales.append({"scale_m_per_pixel": float(marker_size_m) / px,
                               "source": "recognized_qr_known_size", "image": image.name,
                               "reference_pixels": px, "reference_length_m": float(marker_size_m),
                               "scale_uncertainty_m_per_pixel": (float(marker_size_m) / px) * np.sqrt(
                                   (float(marker_uncertainty_m) / float(marker_size_m))**2 + (1.0 / px)**2),
                               "plane_rectified": False})
    return scales


def estimate_scale(images, declared_scale_m_per_pixel=None, metadata_path=None):
    metadata_path, metadata = _metadata_for(images, metadata_path)
    sensor = metadata.get("sensor", {}) if isinstance(metadata.get("sensor", {}), dict) else {}
    candidates = []
    if declared_scale_m_per_pixel is not None:
        if declared_scale_m_per_pixel <= 0:
            raise ValueError("scale_m_per_pixel must be greater than zero")
        candidates.append({"scale_m_per_pixel": float(declared_scale_m_per_pixel),
                           "source": "explicit_cli_calibration", "plane_rectified": False})

    try:
        metadata_scale = float(metadata.get("metric_scale_m_per_pixel"))
    except (TypeError, ValueError):
        metadata_scale = None
    if metadata_scale and metadata_scale > 0:
        candidates.append({"scale_m_per_pixel": metadata_scale,
                           "source": "capture_metadata_calibration",
                           "scale_uncertainty_m_per_pixel": metadata.get("metric_scale_uncertainty_m_per_pixel"),
                           "plane_rectified": bool(metadata.get("metric_scale_plane_rectified", False))})

    explicit_sensor_scale = sensor.get("calibrated_scale_m_per_pixel")
    try:
        explicit_sensor_scale = float(explicit_sensor_scale)
    except (TypeError, ValueError):
        explicit_sensor_scale = None
    if explicit_sensor_scale and explicit_sensor_scale > 0:
        candidates.append({"scale_m_per_pixel": explicit_sensor_scale,
                           "source": "sensor_calibration_metadata",
                           "scale_uncertainty_m_per_pixel": sensor.get("calibrated_scale_uncertainty_m_per_pixel"),
                           "plane_rectified": bool(sensor.get("plane_rectified"))})

    try:
        marker_size = float(metadata.get("qr_marker_size_m"))
    except (TypeError, ValueError):
        marker_size = None
    try:
        marker_uncertainty = float(metadata.get("qr_marker_uncertainty_m", 0.0))
    except (TypeError, ValueError):
        marker_uncertainty = 0.0
    candidates.extend(_qr_scale(images, marker_size, marker_uncertainty))

    references = metadata.get("scale_references", [])
    if not isinstance(references, list):
        references = []
    repeated = []
    for reference in references:
        try:
            px = float(reference["pixel_length_px"])
            real_m = float(reference["length_m"])
            if px <= 0 or real_m <= 0:
                continue
            candidate = {"scale_m_per_pixel": real_m / px,
                         "source": reference.get("source", "measured_geometric_reference"),
                         "reference_kind": reference.get("kind", "unspecified"),
                         "reference_pixels": px, "reference_length_m": real_m,
                         "scale_uncertainty_m_per_pixel": (
                             (real_m/px) * np.sqrt((float(reference.get("length_uncertainty_m", 0))/real_m)**2
                               +(float(reference.get("pixel_uncertainty_px", 1))/px)**2)),
                         "plane_rectified": bool(reference.get("plane_rectified", False))}
            candidates.append(candidate)
            if reference.get("kind") in {"door", "window", "wall", "repeated_architectural_dimension"}:
                repeated.append(candidate["scale_m_per_pixel"])
        except (KeyError, TypeError, ValueError):
            continue

    # Sensor focal length and image dimensions provide intrinsics/FOV, not scale.
    sensor_description = {key: sensor.get(key) for key in
                          ("camera_model", "focal_length_mm", "sensor_width_mm", "intrinsics")
                          if sensor.get(key) is not None}
    selected = None
    status = "SCALE_UNRESOLVED"
    conflicts = []
    if candidates:
        values = np.asarray([item["scale_m_per_pixel"] for item in candidates], dtype=float)
        median = float(np.median(values))
        relative_deviation = np.abs(values - median) / max(median, 1e-12)
        if len(values) > 1 and float(np.max(relative_deviation)) > 0.15 and declared_scale_m_per_pixel is None:
            conflicts = [float(value) for value in values]
            status = "SCALE_REFERENCE_CONFLICT"
        else:
            selected = candidates[0] if declared_scale_m_per_pixel is not None else {
                "scale_m_per_pixel": median,
                "source": "+".join(sorted({item["source"] for item in candidates})),
                "plane_rectified": all(item["plane_rectified"] for item in candidates),
                "scale_uncertainty_m_per_pixel": (
                    max(item["scale_uncertainty_m_per_pixel"] for item in candidates)
                    if all(item.get("scale_uncertainty_m_per_pixel") is not None for item in candidates) else None),
            }
            status = "METRIC_SCALE_AVAILABLE_WITH_PLANE_LIMITS"
    elif sensor_description:
        status = "SENSOR_METADATA_ONLY_NO_ABSOLUTE_SCALE"

    return {
        "scale_m_per_pixel": selected["scale_m_per_pixel"] if selected else None,
        "scale_uncertainty_m_per_pixel": selected.get("scale_uncertainty_m_per_pixel") if selected else None,
        "source": selected["source"] if selected else None,
        "plane_rectified": selected["plane_rectified"] if selected else False,
        "status": status,
        "candidates": candidates,
        "conflicts": conflicts,
        "repeated_architectural_reference_count": len(repeated),
        "sensor_metadata": sensor_description,
        "metadata_path": str(metadata_path) if metadata_path else None,
        "metric_scale_is_global": bool(selected and selected["plane_rectified"]),
        "cross_room_consistency": "CHECK_ONLY; room scale is never propagated without a local reference",
    }
