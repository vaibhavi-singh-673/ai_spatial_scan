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


def _drift_ablation(predicted, truth):
    """Compare both registration modes against an explicitly measured footprint."""
    drift = predicted.get("plan", {}).get("drift", {})
    ablation = drift.get("drift_ablation", {})
    gt_polygon = truth.get("plan", {}).get("stitched_polygon_xy_m")
    if not gt_polygon:
        return {"status":"NOT_RUN", "reason":"ground-truth stitched_polygon_xy_m is missing"}
    try:
        from shapely.geometry import Polygon
        target = Polygon(gt_polygon)
        if target.is_empty or not target.is_valid or target.area <= 0:
            return {"status":"NOT_RUN", "reason":"ground-truth footprint is invalid or has zero area"}
        target = target.buffer(0)
    except (ImportError, TypeError, ValueError):
        return {"status":"NOT_RUN", "reason":"valid polygon comparison requires Shapely and metric coordinates"}

    def mode(label, key, graph_key):
        polygon = ablation.get(key)
        graph = drift.get(graph_key, {})
        if not polygon or graph.get("status") != "PASS":
            return {"status":"NOT_RUN", "reason":"metric footprint or connected verified registration is unavailable",
                    "footprint_error_fraction":None, "closure_error_m":None}
        try:
            measured = Polygon(polygon)
            if not measured.is_valid:
                measured = measured.buffer(0)
            error = float(measured.symmetric_difference(target).area / target.area)
        except (TypeError, ValueError):
            return {"status":"NOT_RUN", "reason":"predicted footprint is invalid",
                    "footprint_error_fraction":None, "closure_error_m":None}
        return {"label":label, "status":"MEASURED", "footprint_error_fraction":error,
                "footprint_error_definition":"symmetric_difference_area / ground_truth_area",
                "closure_error_m":graph.get("closure_error_m"),
                "closure_status":graph.get("closure_error_status", "NOT_RUN")}

    without = mode("WITHOUT CORRECTION", "off_footprint_xy_m", "drift_off_graph")
    with_correction = mode("WITH CORRECTION", "on_footprint_xy_m", "drift_on_graph")
    def improvement(before, after, field):
        a, b = before.get(field), after.get(field)
        return (100.0 * (a-b)/a) if isinstance(a,(int,float)) and isinstance(b,(int,float)) and a > 0 else None
    footprint_improvement = improvement(without, with_correction, "footprint_error_fraction")
    closure_improvement = improvement(without, with_correction, "closure_error_m")
    any_measured = without["status"] == "MEASURED" or with_correction["status"] == "MEASURED"
    return {"status":"MEASURED" if any_measured else "NOT_RUN",
            "WITHOUT CORRECTION":without, "WITH CORRECTION":with_correction,
            "IMPROVEMENT": {"footprint_error_percent":footprint_improvement,
                            "closure_error_percent":closure_improvement,
                            "definition":"100 * (without - with) / without; positive means improvement"}}


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
    missed_openings = []
    matched_predictions = set()
    detected_predictions = []
    for rid in common:
        pred_openings = pr[rid].get("openings", [])
        gt_openings = gr[rid].get("openings", [])
        for index, expected in enumerate(gt_openings):
            actual = next((item for item in pred_openings
                           if item.get("detected", True) and not item.get("candidate", False)
                           and expected.get("id") and item.get("id") == expected.get("id")), None)
            if actual is None and index < len(pred_openings) and not expected.get("id"):
                candidate = pred_openings[index]
                actual = candidate if candidate.get("detected", True) and not candidate.get("candidate", False) else None
            if actual is None:
                opening_errors.append(None)
                missed_openings.append({"room_id": rid, "opening_id": expected.get("id", f"opening_{index+1}")})
                continue
            matched_predictions.add(id(actual))
            actual_width = _value(actual.get("width"))
            truth_width = _value(expected.get("width"))
            if actual_width is not None and truth_width is not None:
                opening_errors.append(abs(actual_width - truth_width))
            else:
                opening_errors.append(None)
        # Extra predicted openings count as false positives.
        detected_count = sum(item.get("detected", True) and not item.get("candidate", False)
                             for item in pred_openings)
        detected_predictions.extend((rid,item) for item in pred_openings
                                    if item.get("detected", True) and not item.get("candidate", False))
        opening_errors.extend(None for _ in range(max(0, detected_count - len(gt_openings))))
    if opening_errors:
        passing = sum(error is not None and error <= .02 for error in opening_errors)
        fraction = passing / len(opening_errors)
        gates["opening_width"] = {"count": len(opening_errors), "within_2_cm": passing,
                                  "fraction_within_tolerance": fraction, "status": _status(fraction >= .85),
                                  "tolerance_m": .02, "required_fraction": .85,
                                  "missed_openings": missed_openings,
                                  "phantom_openings": [{"room_id":rid,"opening_id":item.get("id")}
                                      for rid,item in detected_predictions if id(item) not in matched_predictions],
                                  "unverified_candidates": sum(bool(item.get("candidate")) for rid in common
                                      for item in pr[rid].get("openings",[]))}
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
    drift_ablation = _drift_ablation(predicted, truth)
    gates["drift_ablation"] = drift_ablation
    states = [gate.get("status", "NOT_RUN") for gate in gates.values()]
    overall = "FAIL" if "FAIL" in states else "PASS" if states and all(s == "PASS" for s in states) else "NOT_RUN"
    return {"status": overall, "matched_rooms": common, "gates": gates}
