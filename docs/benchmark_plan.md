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

Capture the same room twice at the same tier without changing furniture. Do not use the first run to initialize the second run.

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
