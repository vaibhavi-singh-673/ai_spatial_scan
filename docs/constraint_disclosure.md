# Constraint and dependency disclosure

## Capture and infrastructure

- The intended route is handheld consumer capture using the stock Camera app
  for photos/video and a stock LiDAR export app for LiDAR.
- Runtime processing is local. The CLI does not call SpatialScan-owned
  infrastructure, hosted inference, or a remote database.
- OpenCV, NumPy, SciPy, Shapely, Pillow, Matplotlib, Pydantic, and PyYAML are
  installed from the pinned requirement ranges in `pyproject.toml`.

## Models, datasets, and APIs

- No pretrained model, private dataset, or external inference API is used by
  the current implementation.
- The visual tier uses OpenCV edge/Hough-line heuristics.
- The LiDAR tier uses deterministic geometry, plane fitting, and pose/IMU
  normalization.
- `models/` intentionally contains documentation only. Future weights must be
  fetched by a separately reviewed script or mounted volume, with source,
  version, license, checksum, and loader recorded before use.

## Known adversarial conditions

Mirrors, glass, wet-look surfaces, low light, clutter, occlusion, and fast
camera motion are not silently treated as solved. They are included in the
capture matrix at `docs/adversarial_capture_matrix.md` and must be represented
in benchmark evidence before accuracy claims include them.