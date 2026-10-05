# Benchmark report

## Status

**Engineering baseline; physical benchmark evidence is incomplete.** The
manifest now registers three user-supplied LiDAR ZIP archives with depth,
confidence, camera matrix, odometry, and IMU data. Device and scene provenance
are not recorded, so they are classified as raw-capture pipeline replays, not
verified property evidence. Synthetic photo/video fixtures and the small
deterministic LiDAR fixture remain smoke tests. No laser/tape ground truth,
multi-tier property capture, damage annotation, confirmed repeat pair, or
incumbent export is registered. No physical accuracy gate is claimed.

## Fixture replay

The LiDAR pipeline consumes depth frames, confidence maps, camera intrinsics,
odometry, and IMU from `fixtures/lidar_sample/` and the three registered ZIPs.
ZIP replays sample up to 120 frames across each scan. These runs verify decoding
and reconstruction paths only; they have no independent dimensional ground
truth.

## Registered archive replay

The following timings are from the local benchmark run recorded in
`benchmarks/results/benchmark.json`. They include ZIP extraction, capture
readiness checks, and reconstruction, so they are machine-specific pipeline
timings rather than participant walk-in times.

| Archive | Depth frames available | Sampled | Confidence maps in sample | Quality score | Processing time (s) | Accuracy status |
|---|---:|---:|---:|---:|---:|---|
| `single_room.zip` | 1,715 | 120 | 120/120 | 100 | 11.61 | NOT_RUN: no ground truth |
| `single_scan_floor_only.zip` | 5,251 | 120 | 120/120 | 100 | 33.88 | NOT_RUN: no ground truth |
| `single_scan_with_ceiling.zip` | 5,757 | 120 | 70/120 | 90 | 38.84 | NOT_RUN: no ground truth |

The third archive lacks confidence maps for 50 of the 120 evenly sampled depth
frames. Quality scores measure input readiness only; they are not accuracy
scores. The exact archive SHA-256 digests are recorded in
`benchmarks/raw/SHA256SUMS.txt`.

## Gate table

| Gate | Status | Evidence |
|---|---|---|
| Opening width <=2 cm on >=85% | NOT_RUN | opening ground truth not supplied |
| Ceiling <=1.5 cm | NOT_RUN | laser height not supplied |
| Wall length <=8% | NOT_RUN | measured multi-room ground truth not supplied |
| Whole-property floor area <=8% | NOT_RUN | measured property ground truth not supplied |
| Adjacency graph | NOT_RUN | measured property graph not supplied |
| Repeatability | NOT_RUN | paired physical captures not supplied; runner now computes pairwise deltas when registered |
| Incumbent comparison | NOT_RUN | no normalized export and measured ground truth registered |
| Real fix-loop improvement | NOT_RUN | no before/after evaluation against measured property ground truth |
| Cold processing time | NOT_RUN | no reviewer cold-run profile registered |
| Drift accountability | PARTIAL | pose-aware reconstruction path and fixture diagnostic; no ground-truth delta |
| Photo whole-property <=8% | NOT_RUN | physical photo benchmark not supplied |
| Video <=3% | NOT_RUN | physical video benchmark not supplied |
| Incumbent >=70% dimensions | NOT_RUN | incumbent export not supplied |
| Staged damage extent | NOT_RUN | annotated staged-damage capture not supplied |

The evaluator emits per-measurement gate results only when corresponding
ground-truth values exist. A partial measurement set cannot produce an overall
`PASS`. The benchmark runner compares repeat-group pairs and reports per-room
area, height, wall, and opening deltas. It needs explicit protocol tolerances to
mark these comparisons PASS or FAIL; without them it reports REVIEW. No paired
physical captures are registered yet. Incumbent comparison preserves the
vendor export and uses the optional normalized `incumbent_measurements` CSV to
compute errors and the 70% win gate. The real fix-loop command evaluates both
versions on the same LiDAR input when ground truth is supplied.
`run_cold_capture.ps1` records local cold readiness and processing time; this is
not an unassisted physical walk-in. Do not replace pending statuses with
estimated or synthetic values.
