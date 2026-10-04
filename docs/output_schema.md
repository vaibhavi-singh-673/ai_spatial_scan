# Output schema

The canonical JSON contains:

- `capture_id`
- `tier`
- `device`
- `rooms[]`
  - polygon
  - floor area + confidence interval
  - ceiling height + confidence interval
  - wall measurements + confidence intervals
  - openings
- `plan`
  - room list
  - adjacency graph
  - stitched footprint
  - drift method and whether loop closure was applied
- `damage[]`
  - class
  - surface
  - metric extent
  - confidence
- `scope[]`
  - surface key
  - action
  - quantity
  - unit
- `diagnostics`

All metric values must carry an interval. Unknown or uncalibrated quantities are not silently converted into narrow intervals.
