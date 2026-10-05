import json


def _rooms(document):
    return {room["id"]: room for room in document.get("rooms", []) if room.get("id")}


def _status(passed):
    return "PASS" if passed else "FAIL"


def _not_run(reason):
    return {"status": "NOT_RUN", "reason": reason}


def _value(item):
    return item.get("value") if isinstance(item, dict) else None


def _adjacency(document):
    plan = document.get("plan", {})
    edges = plan.get("adjacency", document.get("adjacency", []))
    return {tuple(sorted((edge.get("room_a"), edge.get("room_b")))) for edge in edges
            if edge.get("room_a") and edge.get("room_b")}


def evaluate(prediction, gt):
    with open(prediction, encoding="utf-8") as source:
        predicted = json.load(source)
    with open(gt, encoding="utf-8") as source:
        truth = json.load(source)
    pr, gr = _rooms(predicted), _rooms(truth)
    gates = {}
    common = sorted(set(pr) & set(gr))
    if not common:
        return {"status": "INSUFFICIENT_GROUND_TRUTH", "gates": {
            "room_match": _not_run("prediction and ground truth have no matching room ids")}}

    ceiling_errors = []
    for rid in common:
        actual = _value(pr[rid].get("ceiling_height_m"))
        expected = _value(gr[rid].get("ceiling_height_m"))
        if actual is not None and expected is not None:
            ceiling_errors.append(abs(actual - expected))
    if ceiling_errors and len(ceiling_errors) == len(common):
        maximum = max(ceiling_errors)
        gates["ceiling_height"] = {"max_error_m": maximum, "status": _status(maximum <= .015), "tolerance_m": .015,
                                   "measured_rooms": len(ceiling_errors)}
    else:
        gates["ceiling_height"] = _not_run("ceiling measurements missing")

    predicted_area = sum(_value(pr[rid].get("floor_area_m2")) or 0 for rid in common)
    ground_area = sum(_value(gr[rid].get("floor_area_m2")) or 0 for rid in common)
    if set(pr) != set(gr):
        gates["whole_property_footprint"] = _not_run("prediction and ground truth room sets differ")
    elif ground_area > 0 and all(_value(pr[rid].get("floor_area_m2")) is not None and
                               _value(gr[rid].get("floor_area_m2")) is not None for rid in common):
        error = abs(predicted_area - ground_area) / ground_area
        area_tolerance = .03 if predicted.get("tier") == "video" else .08
        gates["whole_property_footprint"] = {"error_fraction": error, "status": _status(error <= area_tolerance),
                                             "tolerance_fraction": area_tolerance}
    else:
        gates["whole_property_footprint"] = _not_run("floor-area measurements missing or non-positive")

    wall_errors = []
    walls_complete = True
    for rid in common:
        pred_walls = pr[rid].get("walls", [])
        gt_walls = gr[rid].get("walls", [])
        if len(pred_walls) != len(gt_walls):
            walls_complete = False
        for index, (actual, expected) in enumerate(zip(pred_walls, gt_walls)):
            a, b = _value(actual), _value(expected)
            if a is not None and b is not None:
                wall_errors.append({"room_id": rid, "index": index, "error_m": abs(a-b), "truth_m": b})
            else:
                walls_complete = False
    if wall_errors and walls_complete and set(pr) == set(gr):
        passing = sum(row["error_m"] <= .08 * row["truth_m"] for row in wall_errors)
        gates["wall_length"] = {"count": len(wall_errors), "within_8_percent": passing,
                                "max_error_m": max(row["error_m"] for row in wall_errors),
                                "status": _status(passing == len(wall_errors)), "tolerance_fraction": .08}
    else:
        gates["wall_length"] = _not_run("ordered wall measurements missing or incomplete")

    opening_errors = []
    for rid in common:
        pred_openings = pr[rid].get("openings", [])
        gt_openings = gr[rid].get("openings", [])
        for index, expected in enumerate(gt_openings):
            actual = next((item for item in pred_openings
                           if expected.get("id") and item.get("id") == expected.get("id")), None)
            if actual is None and index < len(pred_openings) and not expected.get("id"):
                actual = pred_openings[index]
            if actual is None:
                opening_errors.append(float("inf"))
                continue
            actual_width = _value(actual.get("width"))
            truth_width = _value(expected.get("width"))
            if actual_width is not None and truth_width is not None:
                opening_errors.append(abs(actual_width - truth_width))
            else:
                opening_errors.append(float("inf"))
        # Extra predicted openings count as false positives.
        opening_errors.extend(float("inf") for _ in range(max(0, len(pred_openings) - len(gt_openings))))
    if opening_errors:
        passing = sum(error <= .02 for error in opening_errors)
        fraction = passing / len(opening_errors)
        gates["opening_width"] = {"count": len(opening_errors), "within_2_cm": passing,
                                  "fraction_within_tolerance": fraction, "status": _status(fraction >= .85),
                                  "tolerance_m": .02, "required_fraction": .85}
    else:
        gates["opening_width"] = _not_run("matched opening width measurements missing")

    pred_edges, gt_edges = _adjacency(predicted), _adjacency(truth)
    if gt_edges:
        gates["adjacency"] = {"expected_edges": len(gt_edges), "predicted_edges": len(pred_edges),
                              "missing": [list(edge) for edge in sorted(gt_edges - pred_edges)],
                              "unexpected": [list(edge) for edge in sorted(pred_edges - gt_edges)],
                              "status": _status(pred_edges == gt_edges)}
    else:
        gates["adjacency"] = _not_run("ground-truth adjacency edges missing")

    states = [gate["status"] for gate in gates.values()]
    overall = "FAIL" if "FAIL" in states else "PASS" if states and all(s == "PASS" for s in states) else "NOT_RUN"
    return {"status": overall, "matched_rooms": common, "gates": gates}
