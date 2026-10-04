# Benchmark report

## Status

**Submission package status: engineering baseline / benchmark data collection incomplete.**

The supplied LiDAR archive is preserved under `benchmarks/raw/` and is replayable. It does not contain laser/tape ground truth, photo/video tiers, damage annotations, or incumbent-app exports, so those gates are intentionally not claimed.

## LiDAR replay

The pipeline consumes the archive's depth frames, confidence maps, camera matrix, odometry and IMU. A deterministic subset fixture is also included for fast CI tests.

## Gate table

| Gate | Status | Evidence |
|---|---|---|
| Opening width <=2 cm on >=85% | NOT_RUN | opening ground truth not supplied |
| Ceiling <=1.5 cm | NOT_RUN | laser height not supplied |
| Repeatability | NOT_RUN | repeat capture not supplied |
| Drift accountability | PARTIAL | pose-aware reconstruction path + explicit diagnostic |
| Photo whole-property <=8% | NOT_RUN | photo benchmark not supplied |
| Video <=3% | NOT_RUN | video benchmark not supplied |
| Incumbent >=70% dimensions | NOT_RUN | incumbent export not supplied |

Do not replace these statuses with estimated or synthetic values.
