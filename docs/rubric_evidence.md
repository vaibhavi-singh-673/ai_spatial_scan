# Rubric evidence map

This document maps the submission to the supplied scoring rubric. It separates
implemented evidence from benchmark evidence that still requires real property
captures and laser/tape measurements.

| Weight | Criterion | Current evidence | Status |
|---:|---|---|---|
| 30% | Walk-in cold run | `scripts/run_cold_capture.ps1`, `README.md`, `docs/capture_protocol.md` | READY FOR EXTERNAL CAPTURE |
| 25% | Fix-loop delta | `docs/fix_loop.md`, pose-normalized LiDAR path, regression test | PARTIAL: post-fix measurement unavailable |
| 15% | Verified three-tier accuracy | `src/spatialscan/tiers/`, `tests/`, `benchmarks/manifest.json` | NOT_RUN: real GT required |
| 10% | Compliance matrix | `docs/compliance_matrix.md` | DOCUMENTED |
| 10% | Incumbent comparison | `docs/head_to_head.md`, manifest fields | NOT_RUN: export required |
| 5% | Capture route quality | `docs/capture_protocol.md`, `scripts/run_cold_capture.ps1` | DOCUMENTED |
| 5% | Process evidence | `docs/process_evidence.md`, CI workflow | DOCUMENTED |

No synthetic fixture is used as accuracy evidence. The fixture commands prove
replayability, decoding, schema production, and failure handling only.

Run `python -m spatialscan audit` to generate the current machine-readable
evidence score. The audit currently reports 20 verified points, 25 points under
review, and blocks claims that require real property data.

## Reviewer cold run

From the repository root on Windows PowerShell:

```powershell
.\scripts\run_cold_capture.ps1 `
  -Tier lidar `
  -InputPath fixtures\lidar_sample `
  -OutputDirectory runs\cold_lidar
```

For an accuracy gate, add the measured ground truth path:

```powershell
.\scripts\run_cold_capture.ps1 `
  -Tier lidar `
  -InputPath <capture-folder> `
  -OutputDirectory runs\cold_lidar `
  -GroundTruthPath <ground-truth.json>
```