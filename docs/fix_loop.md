# Fix loop declaration

## Before run

The first reproducible LiDAR prototype treated camera-frame vertical as world vertical. On the supplied replay this produced an obviously invalid ceiling estimate (the estimator hit its 1.8 m safety floor). This is retained as a development finding, not a benchmark claim.

## Root cause hypothesis

Pose/IMU frame handling was incomplete: depth points were being interpreted in a single camera frame while the phone changes orientation through the capture. The evidence is the large variation in the reconstructed footprint and the implausible vertical extent when the same depth data are accumulated without pose normalization.

## Shipped fix

The current path transforms depth samples through recorded camera poses and uses the IMU gravity direction to constrain floor-plane selection. The code is in `src/spatialscan/geometry/lidar_recon.py`.

## Post-fix

The supplied archive has no laser/tape ceiling measurement, so a pass/fail gate delta cannot honestly be reported yet. The next benchmark run must record the exact before/after values using unchanged raw data.

## Reproducible fixture ablation

The command below records the implementation delta on the unchanged supplied
fixture:

```bash
python -m spatialscan fixloop --input fixtures/lidar_sample --output runs/fixloop_lidar.json
```

Current fixture result:

| Measurement | Before: poses/IMU disabled | After: pose-normalized + IMU | Delta |
|---|---:|---:|---:|
| Floor area (m2) | 6.9023 | 12.5828 | +5.6805 |
| Ceiling (m) | 1.9553 | 7.2079 | +5.2526 |

This is an implementation ablation, not a ground-truth accuracy result. The
large ceiling delta is exactly why laser/tape validation and calibration remain
required before submission.

## Measured before/after run

Run the same LiDAR raw capture with the measured property ground truth to
evaluate both the pose/IMU-disabled baseline and the current implementation:

```bash
python -m spatialscan fixloop --input benchmarks/raw/<capture_id> --ground-truth benchmarks/ground_truth/<property>.json --output benchmarks/results/<capture_id>_fixloop.json
```

The report includes both per-gate evaluations and status changes. A gate can
still be `NOT_RUN` when the ground truth omits required dimensions. This command
does not itself create a physical fix: after changing reconstruction code,
rerun it on the unchanged capture and preserve the before/after artifacts and
code revision. The fixture ablation above must not be presented as real
property improvement.
