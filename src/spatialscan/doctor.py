import importlib
import importlib.util
import json
import platform
import sys
import tempfile
from pathlib import Path


DEPENDENCIES = {
    "numpy": "numpy",
    "opencv": "cv2",
    "pillow": "PIL",
    "scipy": "scipy",
    "shapely": "shapely",
    "matplotlib": "matplotlib",
    "pydantic": "pydantic",
    "pyyaml": "yaml",
}


def _check(name, ready, details):
    return {"name": name, "status": "READY" if ready else "BLOCKED", "details": details}


def run_doctor(output_dir="runs/doctor", output_json=None):
    project_root = Path(__file__).resolve().parents[2]
    dependencies = {name: importlib.util.find_spec(module) is not None
                    for name, module in DEPENDENCIES.items()}
    checks = [
        _check("python", sys.version_info >= (3, 11),
               {"version": platform.python_version(), "required": ">=3.11"}),
        _check("dependencies", all(dependencies.values()), dependencies),
    ]

    cv2_ready = dependencies["opencv"]
    still_ready = False
    video_ready = False
    photo_fixture_ready = False
    decoder_error = None
    if cv2_ready:
        try:
            cv2 = importlib.import_module("cv2")
            import numpy as np
            sample = np.zeros((16, 16, 3), dtype=np.uint8)
            encoded, payload = cv2.imencode(".png", sample)
            decoded = cv2.imdecode(payload, cv2.IMREAD_COLOR) if encoded else None
            still_ready = decoded is not None and decoded.shape[:2] == (16, 16)
            photos = sorted(path for path in (project_root / "fixtures" / "photo").rglob("*")
                            if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"})
            photo_decoded = None
            for path in photos:
                photo_decoded = cv2.imread(str(path))
                if photo_decoded is not None:
                    break
            photo_fixture_ready = photo_decoded is not None
            videos = sorted((project_root / "fixtures" / "video").rglob("*.mp4"))
            if videos:
                capture = cv2.VideoCapture(str(videos[0]))
                video_ok, frame = capture.read()
                capture.release()
                video_ready = bool(video_ok and frame is not None)
        except Exception as error:
            decoder_error = str(error)
        checks.append(_check("opencv_still_decoder", still_ready,
                             {"version": getattr(locals().get("cv2"), "__version__", None),
                              "encode_decode": still_ready, "error": decoder_error}))
        checks.append(_check("opencv_video_decoder", video_ready,
                             {"fixture": str(videos[0]) if "videos" in locals() and videos else None,
                              "first_frame_decoded": video_ready, "error": decoder_error}))
    else:
        checks.extend([
            _check("opencv_still_decoder", False, {"reason": "opencv dependency unavailable"}),
            _check("opencv_video_decoder", False, {"reason": "opencv dependency unavailable"}),
        ])

    config_path = project_root / "configs" / "default.yaml"
    config_ready = False
    config_error = None
    if dependencies["pyyaml"] and config_path.is_file():
        try:
            import yaml
            config_ready = isinstance(yaml.safe_load(config_path.read_text(encoding="utf-8")), dict)
        except (OSError, yaml.YAMLError) as error:
            config_error = str(error)
    checks.append(_check("configuration", config_ready,
                         {"path": str(config_path), "valid_yaml": config_ready, "error": config_error}))

    lidar_root = project_root / "fixtures" / "lidar_sample"
    lidar_metadata_present = all((lidar_root / name).is_file()
                                 for name in ("camera_matrix.csv", "odometry.csv", "imu.csv"))
    lidar_ready = False
    lidar_details = {"fixture_metadata_present": lidar_metadata_present, "decoded_depth_frames": 0,
                     "imu_samples": 0}
    if lidar_metadata_present and cv2_ready:
        try:
            from .io.lidar import load_lidar
            matrix, frames, imu = load_lidar(lidar_root, max_frames=8)
            decoded_depth = sum(depth is not None for _, depth, _, _ in frames)
            lidar_ready = matrix.shape == (3, 3) and decoded_depth > 0 and bool(imu)
            lidar_details.update({"decoded_depth_frames": decoded_depth,
                                  "sampled_depth_frames": len(frames), "imu_samples": len(imu),
                                  "camera_matrix_shape": list(matrix.shape)})
        except Exception as error:
            lidar_details["error"] = str(error)
    lidar_details["fixture_metadata_present"] = lidar_metadata_present
    lidar_details["frame_sampling_limit"] = 8
    checks.append(_check("lidar_tier", lidar_ready,
                         lidar_details))
    checks.append(_check("photo_tier", still_ready and photo_fixture_ready,
                         {"still_decoder_ready": still_ready,
                          "photo_fixture_decoded": photo_fixture_ready}))
    checks.append(_check("video_tier", video_ready,
                         {"video_decoder_ready": video_ready}))

    model_dir = project_root / "models"
    model_files = [path.name for path in model_dir.glob("*") if path.is_file()
                   and path.suffix.lower() in {".onnx", ".pt", ".pth", ".tflite"}]
    # The present geometry/OpenCV pipeline does not require learned weights.
    checks.append(_check("models", True,
                         {"required": False, "available": model_files,
                          "note": "Current pipeline is model-free; geometric CV paths are used."}))

    output_path = Path(output_dir).expanduser().resolve()
    output_ready = False
    output_error = None
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=output_path, prefix=".spatialscan-doctor-", delete=True):
            output_ready = True
    except OSError as error:
        output_error = str(error)
    checks.append(_check("output", output_ready,
                         {"path": str(output_path), "writable": output_ready, "error": output_error}))

    report_ready = False
    report_details = {"matplotlib_available": dependencies["matplotlib"]}
    if output_ready and dependencies["matplotlib"]:
        try:
            from .render import render_plan
            from .report import write_html_report
            with tempfile.TemporaryDirectory(dir=output_path, prefix=".spatialscan-report-check-") as temp:
                temporary = Path(temp)
                source = temporary / "sample.json"
                source.write_text(json.dumps({"tier":"doctor","rooms":[{
                    "id":"check","name":"check","polygon_xy_m":[[0,0],[1,0],[1,1],[0,1]]}]}),
                    encoding="utf-8")
                render_plan(json.loads(source.read_text(encoding="utf-8")),temporary/"check.png")
                write_html_report(source,temporary/"check.html")
                report_ready = (temporary/"check.png").is_file() and (temporary/"check.html").is_file()
            report_details["png_and_html_write"] = report_ready
        except Exception as error:
            report_details["error"] = str(error)
    checks.append(_check("report", report_ready, report_details))
    blocked = [item["name"] for item in checks if item["status"] == "BLOCKED"]
    report = {"schema_version": "1.0", "status": "READY" if not blocked else "BLOCKED",
              "python": platform.python_version(), "checks": checks,
              "blocked": blocked, "tiers": {"PHOTO": "READY" if still_ready and photo_fixture_ready else "BLOCKED",
              "VIDEO": "READY" if video_ready else "BLOCKED",
              "LIDAR": "READY" if lidar_ready and cv2_ready else "BLOCKED",
              "OUTPUT": "READY" if output_ready else "BLOCKED",
              "REPORT": "READY" if report_ready else "BLOCKED"}}
    if output_json:
        destination = Path(output_json).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
