# Process evidence

The repository keeps implementation, fixture replay, and benchmark collection
separate so a reviewer can audit what is actually measured.

## Reproducible checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\check_submission.py
.\.venv\Scripts\python.exe -m spatialscan quality --tier lidar --input fixtures\lidar_sample --output runs\quality_lidar.json
.\.venv\Scripts\python.exe -m spatialscan report --input runs\quality_lidar.json --output runs\quality_lidar.html
```

The same checks run in `.github/workflows/ci.yml` on push and pull request.

## Change record

Use the repository's Git history to audit changes. Keep capture collection,
reconstruction, calibration, fix-loop, and reporting changes in separate
commits. Do not claim a benchmark result from a fixture-only change.