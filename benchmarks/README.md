# Benchmark data policy

`fixtures/` is the deterministic smoke-test dataset. Its synthetic photos and
videos and supplied LiDAR replay validate input handling and output contracts;
they are not physical measurements and must never be reported as accuracy
evidence.

Author-collected evaluation data belongs under `benchmarks/raw/` (ignored by
Git because captures may be large or private). Keep each capture unmodified and
record its device, tier, room IDs, capture conditions, repeated-capture group,
independent laser/tape ground truth, and original incumbent export in
`manifest.json`. Ground-truth JSON belongs under `benchmarks/ground_truth/`.
Keep a copy of the manifest with the submitted package so another person can
reproduce the run.

The three ZIP archives currently in `raw/` contain LiDAR depth/confidence
images, camera intrinsics, odometry, and IMU. They are registered as
`raw_capture_unverified` pipeline inputs. Their device, room identity, capture
protocol, independent measurements, repeat relationship, and incumbent output
were not included. Their filenames are preserved as hints, not treated as
verified scene labels. The runner extracts one archive at a time to a temporary
folder, samples up to 120 frames evenly across the scan, and removes the
temporary extraction after processing. Predictions and run metrics are saved
under `benchmarks/results/`; frame coverage in the quality report describes the
sampled frames and also records the total available count.

Manifest paths are relative to the repository root. A row can use `null` for
ground truth, repeat group, or incumbent export until that evidence exists.
`scale_m_per_pixel` is
optional for photo/video rows and must only contain a measured calibration.
Missing captures and measurements remain `NOT_RUN`; no fixture, guessed value,
or app screenshot counts as a substitute. The runner reports pipeline smoke
results separately from evaluated results.

Start with `manifest.template.json`, then run from the project root:

```bash
python -m spatialscan benchmark --manifest benchmarks/manifest.json --output benchmarks/results/benchmark.json
python -m spatialscan audit --root . --output benchmarks/results/submission_audit.json
```

Capture procedure and measurement endpoints are documented in
`../docs/benchmark_plan.md` and `../docs/capture_protocol.md`.
