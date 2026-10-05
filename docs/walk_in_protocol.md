# Cold reproduction and walk-in evidence

The project can record a cold local run, but a scripted replay is not a live
walk-in test. A walk-in result requires a participant who did not build the
system, a physical property, and the target capture device.

## Cold local run

From a fresh environment, have a reviewer follow the README setup and run:

```powershell
.\scripts\run_cold_capture.ps1 -Tier lidar -InputPath <capture-folder> -OutputDirectory runs\walk_in
```

This writes `cold_run.json`, quality, prediction, and optional evaluation
artifacts. It records setup-independent readiness time, processing time, input
size, Python version, and timestamp. Its evidence class is explicitly
`COLD_REPRODUCTION_ONLY`; it does not measure participant task time or physical
accuracy.

## Physical walk-in study record

For each participant, save a record with:

- participant role (for example, estimator unfamiliar with the codebase)
- device model, operating system, capture app and version
- property/session ID and capture tier
- start/end timestamps and active assistance provided
- capture completion, successful export, cold pipeline completion, and blockers
- original capture and generated output paths
- independent ground-truth and evaluation artifact paths, when available

Do not include participant names or other unnecessary personal data. Run at
least one unassisted session before claiming the workflow is reproducible by a
new operator. Keep that study record separate from fixture timing and do not
infer physical accuracy from successful execution.
