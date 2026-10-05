# Incumbent comparison record

Use the same raw capture session and same room endpoints for SpatialScan and the
incumbent. Preserve the original incumbent export under `benchmarks/raw/`.

| Room | Dimension | Ground truth | SpatialScan error | Incumbent error | Winner |
|---|---|---:|---:|---:|---|
| R1 | wall 1 | | | | |
| R1 | wall 2 | | | | |
| R1 | opening 1 | | | | |
| R2 | wall 1 | | | | |

Only dimensions present in SpatialScan, measured ground truth, and the
incumbent count toward the 70% gate. Preserve the original app export unchanged.
Because app exports vary, transcribe the relevant exported measurements into a
normalized CSV while retaining the untouched original file:

```csv
room_id,kind,measurement_id,value,unit
R1,wall_length,wall_1,4.12,m
R1,opening_width,door_1,0.91,m
R1,ceiling_height,ceiling_height,2.48,m
```

Use `wall_length`, `opening_width`, `ceiling_height`, or `floor_area` for
`kind`. IDs must match the ground-truth and SpatialScan IDs. Register the
original archive in `incumbent_export` and the normalized file in the optional
manifest field `incumbent_measurements`. The benchmark runner calculates errors
against ground truth, counts SpatialScan wins among shared dimensions, and
reports PASS only at >=70%. No matching dimensions remains `NOT_RUN`.
