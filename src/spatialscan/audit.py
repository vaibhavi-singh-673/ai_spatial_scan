import json
from pathlib import Path


def _item(name, weight, status, evidence, next_step):
    return {
        "name": name,
        "weight": weight,
        "status": status,
        "evidence": evidence,
        "next_step": next_step,
    }


def audit_submission(root):
    root = Path(root)
    manifest_path = root / "benchmarks" / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"captures": []}
    captures = manifest.get("captures", [])
    tiers = {row.get("tier") for row in captures}
    real_rows = []
    gt_rows = []
    incumbent_rows = []
    condition_tags = set()
    repeat_groups = {}
    fixloop_report = (root / "runs" / "fixloop_lidar.json").exists()

    for row in captures:
        raw = (root / row.get("raw_path", "")).resolve()
        ground_truth = (root / row.get("ground_truth_path", "")).resolve()
        incumbent = (root / row.get("incumbent_export", "")).resolve()
        if raw.exists():
            real_rows.append(row)
        if ground_truth.exists():
            gt_rows.append(row)
        if incumbent.exists():
            incumbent_rows.append(row)
        condition_tags.update(row.get("conditions", []))
        repeat = row.get("repeat_group")
        if repeat:
            repeat_groups.setdefault(repeat, []).append(row)

    repeated = any(len(rows) >= 2 for rows in repeat_groups.values())
    adversarial = {"mirrors", "glass", "wet-look", "low-light", "clutter"}
    items = [
        _item("walk_in", 30, "PASS" if real_rows and gt_rows else "BLOCKED",
              f"{len(real_rows)} real capture rows, {len(gt_rows)} ground-truth rows",
              "Add a real capture and laser/tape ground truth to benchmarks/"),
        _item(
            "fix_loop", 25,
            "REVIEW" if (root / "docs/fix_loop.md").exists() else "BLOCKED",
            "Measured fixture ablation exists; laser/tape accuracy delta is absent"
            if fixloop_report else "Fix-loop declaration exists; measured delta is absent",
            "Add laser/tape ground truth and record before/after gate values"
            if fixloop_report else "Record before/after gate values on identical raw data",
        ),
        _item("three_tier_accuracy", 15,
              "PASS" if {"photos", "video", "lidar"} <= tiers and len(gt_rows) >= 3 else "BLOCKED",
              f"Manifest tiers: {sorted(tiers)}; evaluated rows: {len(gt_rows)}",
              "Add measured photo, video, and LiDAR rows with ground truth"),
        _item("compliance", 10,
              "PASS" if (root / "docs/compliance_matrix.md").exists() else "BLOCKED",
              "Compliance matrix and source artifacts present",
              "Keep partial items explicitly labeled"),
        _item("incumbent", 10, "PASS" if incumbent_rows else "BLOCKED",
              f"{len(incumbent_rows)} incumbent exports found",
              "Preserve a magicplan or Polycam export for shared rooms"),
        _item("capture_route", 5,
              "PASS" if (root / "docs/capture_protocol.md").exists()
              and (root / "scripts/run_cold_capture.ps1").exists() else "BLOCKED",
              "Capture protocol and cold-run script present",
              "Have a non-engineer follow the route and record install time"),
        _item("process", 5,
              "PASS" if (root / ".github/workflows/ci.yml").exists()
              and (root / "tests").exists() else "BLOCKED",
              "CI workflow and test suite present",
              "Keep benchmark changes auditable in Git history"),
    ]
    condition_status = "PASS" if adversarial <= condition_tags else "BLOCKED"
    items.append(_item(
        "difficult_conditions", 0, condition_status,
        f"Tagged conditions: {sorted(condition_tags)}",
        "Collect mirrors, glass, wet-look, low-light, and clutter cases",
    ))
    earned = sum(item["weight"] for item in items if item["status"] == "PASS")
    review = sum(item["weight"] for item in items if item["status"] == "REVIEW")
    return {
        "schema_version": "1.0",
        "status": "READY_FOR_COLLECTION" if earned < 50 else "PARTIALLY_EVIDENCED",
        "evidence_score": earned,
        "review_weight": review,
        "rubric": items,
        "repeat_groups": {key: len(value) for key, value in repeat_groups.items()},
        "repeatability_ready": repeated,
        "recommendation": "Collect real benchmark evidence before claiming accuracy or selection readiness.",
    }
