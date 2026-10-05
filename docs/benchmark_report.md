# Benchmark report

## Status

**Engineering baseline; physical benchmark collection is incomplete.** The
repository contains synthetic photo/video fixtures and a deterministic LiDAR
sensor-format fixture for smoke testing. No physical multi-tier property
capture, laser/tape ground truth, measured damage annotations, repeat-capture
pair, or incumbent-app export is currently registered in
`benchmarks/manifest.json`. No physical accuracy gate is claimed.

## Fixture replay

The LiDAR pipeline consumes depth frames, confidence maps, camera intrinsics,
odometry, and IMU from `fixtures/lidar_sample/`. This verifies the local data
path only. The fixture has no independent dimensional ground truth.

## Gate table

| Gate | Status | Evidence |
|---|---|---|
| Opening width <=2 cm on >=85% | NOT_RUN | opening ground truth not supplied |
| Ceiling <=1.5 cm | NOT_RUN | laser height not supplied |
| Wall length <=8% | NOT_RUN | measured multi-room ground truth not supplied |
| Whole-property floor area <=8% | NOT_RUN | measured property ground truth not supplied |
| Adjacency graph | NOT_RUN | measured property graph not supplied |
| Repeatability | NOT_RUN | paired physical captures not supplied |
| Drift accountability | PARTIAL | pose-aware reconstruction path and fixture diagnostic; no ground-truth delta |
| Photo whole-property <=8% | NOT_RUN | physical photo benchmark not supplied |
| Video <=3% | NOT_RUN | physical video benchmark not supplied |
| Incumbent >=70% dimensions | NOT_RUN | incumbent export not supplied |
| Staged damage extent | NOT_RUN | annotated staged-damage capture not supplied |

The evaluator emits per-measurement gate results only when corresponding
ground-truth values exist. A partial measurement set cannot produce an overall
`PASS`. Repeatability and incumbent comparison require paired captures/exports
and remain outside the current single-capture evaluator. Do not replace these
statuses with estimated or synthetic values.
