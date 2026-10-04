# Compliance matrix

| Requirement | Artifact | Status |
|---|---|---|
| Three input tiers | `src/spatialscan/tiers/` | IMPLEMENTED |
| Common output contract | `src/spatialscan/models.py`, `docs/output_schema.md` | IMPLEMENTED |
| One command per capture | `python -m spatialscan run ...` | IMPLEMENTED |
| LiDAR depth/poses/intrinsics | `src/spatialscan/io/lidar.py` | IMPLEMENTED |
| LiDAR metric reconstruction | `src/spatialscan/geometry/lidar_recon.py` | IMPLEMENTED |
| Photo room folders | `src/spatialscan/tiers/visual.py` | IMPLEMENTED |
| Video input | `src/spatialscan/tiers/visual.py` | IMPLEMENTED |
| Whole-property stitching | plan/adjacency schema + graph hook | PARTIAL — benchmark validation required |
| Openings | schema present | PARTIAL — detector to be calibrated |
| Damage classes/regions | schema present | PARTIAL — detector to be calibrated |
| Concealed damage rules | schema contract | PARTIAL |
| Scope line items | schema contract | PARTIAL |
| Confidence interval every measurement | models + tier outputs | IMPLEMENTED |
| Drift accountability | plan drift record | PARTIAL |
| Repeatability | evaluator structure | READY FOR BENCHMARK |
| Gate evaluation | `src/spatialscan/evaluate.py` | IMPLEMENTED |
| Manifest benchmark runner | `src/spatialscan/benchmark.py`, `python -m spatialscan benchmark ...` | IMPLEMENTED — external captures still required |
| Fix loop | `docs/fix_loop.md` | READY |
| Raw benchmark data | `benchmarks/raw/` | REQUIRED FROM COLLECTION |
| Incumbent comparison | `docs/head_to_head.md` | REQUIRED FROM COLLECTION |
| 6-page technical report | `docs/technical_report.md` | DRAFT STRUCTURE |
