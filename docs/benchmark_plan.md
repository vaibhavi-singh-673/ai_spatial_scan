# Benchmark collection plan

The benchmark must be collected before any accuracy claim is written.

## Property A — multi-room

- 3+ rooms plus one connector/corridor.
- Capture the same property at photo, video and LiDAR tiers.
- Laser/tape every wall, opening, room height and floor footprint.
- Record door/window widths and the exact endpoints used for each measurement.
- Capture one repeat of at least one room at each tier.

## Property B — staged damage

- Furnished room.
- Stage at least two damage classes (for example surface staining + impact/delamination).
- Mark the true damage polygons on a floor/wall elevation sketch and measure extents.
- Record concealed-damage truth only where an inspection rule is justified.

## Repeatability

Capture the same room twice at the same tier without changing furniture. Do not
use the first run to initialize the second run. Give both rows the same
`repeat_group`, tier, room IDs, and ground-truth property; use different
`capture_id` and raw capture paths. The runner compares per-room floor area,
ceiling height, wall lengths, and opening widths for every pair in a group.
Missing/incomplete measurements stay `NOT_RUN`.

Optionally set `repeatability_tolerances` at the manifest top level using the
keys `floor_area_relative`, `ceiling_height_m`, `wall_length_m`, and
`opening_width_m`. Values are maximum allowed pairwise deltas (floor area uses
a relative fraction; the other dimensions use metres). Only populate limits
specified by the challenge rubric or a documented benchmark protocol. Without
a declared tolerance, the runner reports deltas as `REVIEW`, not PASS/FAIL.
The report is `benchmarks/results/benchmark.json` under its `repeatability`
field.

## Head-to-head

Use two rooms from Property A. Run our LiDAR path and the chosen incumbent on the same raw capture session where possible. Preserve the incumbent export unedited.

## Required manifest row

```json
{
  "capture_id":"A_lidar_01",
  "tier":"lidar",
  "device":"iPhone 15 Pro",
  "rooms":["R1","R2","R3","C1"],
  "raw_path":"benchmarks/raw/A_lidar_01",
  "ground_truth_path":"benchmarks/ground_truth/A.json",
  "repeat_group":"R1_lidar_repeat",
  "incumbent_export":"benchmarks/raw/incumbent/A_R1.zip"
}
```
