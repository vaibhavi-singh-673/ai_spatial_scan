import csv


def _truth_dimensions(document):
    dimensions = {}
    for room in document.get("rooms", []):
        rid = room.get("id")
        if not rid:
            continue
        for kind in ("floor_area", "ceiling_height"):
            item = room.get("floor_area_m2" if kind == "floor_area" else "ceiling_height_m")
            if isinstance(item, dict) and item.get("value") is not None:
                dimensions[(rid, kind, item.get("id", kind))] = float(item["value"])
        for kind in ("wall_length", "opening_width"):
            items = room.get("walls" if kind == "wall_length" else "openings", [])
            for index, item in enumerate(items):
                value = item.get("value") if kind == "wall_length" else item.get("width", {}).get("value")
                if value is not None:
                    dimensions[(rid, kind, item.get("id", f"{kind}_{index + 1}"))] = float(value)
    return dimensions


def _prediction_dimensions(document):
    dimensions = {}
    for room in document.get("rooms", []):
        rid = room.get("id")
        if not rid:
            continue
        for kind in ("floor_area", "ceiling_height"):
            item = room.get("floor_area_m2" if kind == "floor_area" else "ceiling_height_m")
            if isinstance(item, dict) and item.get("value") is not None:
                dimensions[(rid, kind, item.get("id", kind))] = float(item["value"])
        for kind in ("wall_length", "opening_width"):
            items = room.get("walls" if kind == "wall_length" else "openings", [])
            for index, item in enumerate(items):
                value = item.get("value") if kind == "wall_length" else item.get("width", {}).get("value")
                if value is not None:
                    dimensions[(rid, kind, item.get("id", f"{kind}_{index + 1}"))] = float(value)
    return dimensions


def _incumbent_dimensions(path):
    dimensions = {}
    with open(path, newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(source):
            key = (row["room_id"], row["kind"], row["measurement_id"])
            dimensions[key] = float(row["value"])
    return dimensions


def compare_incumbent(prediction, ground_truth, incumbent_csv):
    """Compare shared dimensions from two systems against measured truth.

    CSV columns: room_id,kind,measurement_id,value,unit. The original vendor
    export is preserved separately; this normalized CSV makes comparison
    deterministic without guessing vendor-specific export formats.
    """
    truth = _truth_dimensions(ground_truth)
    ours = _prediction_dimensions(prediction)
    incumbent = _incumbent_dimensions(incumbent_csv)
    rows = []
    for key in sorted(set(truth) & set(ours) & set(incumbent)):
        true_value = truth[key]
        our_error = abs(ours[key] - true_value)
        incumbent_error = abs(incumbent[key] - true_value)
        rows.append({"room_id": key[0], "kind": key[1], "measurement_id": key[2],
                     "ground_truth": true_value, "spatialscan": ours[key], "incumbent": incumbent[key],
                     "spatialscan_error": our_error, "incumbent_error": incumbent_error,
                     "winner": "tie" if our_error == incumbent_error else
                               "spatialscan" if our_error < incumbent_error else "incumbent"})
    if not rows:
        return {"status": "NOT_RUN", "reason": "no dimensions shared by prediction, ground truth, and incumbent CSV",
                "dimensions": []}
    wins = sum(row["winner"] == "spatialscan" for row in rows)
    win_fraction = wins / len(rows)
    return {"status": "PASS" if win_fraction >= .70 else "FAIL", "shared_dimensions": len(rows),
            "spatialscan_wins": wins, "ties": sum(row["winner"] == "tie" for row in rows),
            "win_fraction": win_fraction, "required_fraction": .70, "dimensions": rows}
