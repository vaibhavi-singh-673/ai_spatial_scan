"""Metric room-pose graph optimization from explicit relative constraints."""
import numpy as np
from scipy.optimize import least_squares


def _relative(pose_a, pose_b):
    ax, ay, at = pose_a
    bx, by, bt = pose_b
    dx, dy = bx-ax, by-ay
    c, s = np.cos(at), np.sin(at)
    return np.array([c*dx+s*dy, -s*dx+c*dy, bt-at])


def _wrap(angle):
    return (angle + np.pi) % (2*np.pi) - np.pi


def optimize_room_graph(room_ids, constraints, use_all_edges=True):
    """Optimize SE(2) room poses from measured/verified room-to-room links.

    Each constraint defines room_b relative to room_a in room_a coordinates.
    Tentative feature matches are excluded unless `verified` is true.
    """
    room_ids = list(dict.fromkeys(room_ids))
    if not room_ids:
        return {"status": "NOT_RUN", "reason": "no rooms"}
    index = {room_id: position for position, room_id in enumerate(room_ids)}
    edges = []
    for edge in constraints:
        if edge.get("verified") is not True or edge.get("room_a") not in index or edge.get("room_b") not in index \
                or edge.get("room_a") == edge.get("room_b"):
            continue
        try:
            values = [float(edge[key]) for key in ("dx_m", "dy_m", "rotation_rad")]
            weight = float(edge.get("weight", 1.0))
        except (KeyError, TypeError, ValueError):
            continue
        if not np.all(np.isfinite(values)) or not np.isfinite(weight) or weight <= 0:
            continue
        edges.append({**edge, "dx_m":values[0], "dy_m":values[1],
                      "rotation_rad":values[2], "weight":weight})
    if not edges:
        return {"status": "NOT_RUN", "reason": "no verified relative room transforms"}
    # Use the same deterministic spanning tree as the uncorrected baseline;
    # non-tree constraints become held-out loop-closure measurements.
    tree, seen = [], {room_ids[0]}
    pending = list(edges)
    changed = True
    while changed:
        changed = False
        for edge in pending[:]:
            a, b = edge["room_a"], edge["room_b"]
            if (a in seen) != (b in seen):
                tree.append(edge)
                seen.update((a,b))
                pending.remove(edge)
                changed = True
    closure_edges = [edge for edge in edges if edge not in tree]
    if not use_all_edges:
        edges = tree
    if not edges:
        return {"status": "NOT_RUN", "reason": "verified links do not connect an anchored room"}
    connected = {room_ids[0]}
    changed = True
    while changed:
        changed = False
        for edge in edges:
            if (edge["room_a"] in connected) != (edge["room_b"] in connected):
                connected.update((edge["room_a"],edge["room_b"]))
                changed = True
    if len(connected) != len(room_ids):
        return {"status":"NOT_RUN","reason":"relative transforms do not connect every room",
                "connected_rooms":sorted(connected),"unconnected_rooms":sorted(set(room_ids)-connected)}

    def residual(flat):
        poses = np.zeros((len(room_ids), 3), dtype=float)
        poses[1:] = np.asarray(flat).reshape(-1, 3)
        values = []
        for edge in edges:
            observed = np.array([edge["dx_m"], edge["dy_m"], edge["rotation_rad"]], dtype=float)
            error = _relative(poses[index[edge["room_a"]]], poses[index[edge["room_b"]]]) - observed
            error[2] = _wrap(error[2])
            weight = float(edge.get("weight", 1.0))
            values.extend(error * np.sqrt(max(weight, 1e-6)))
        return np.asarray(values)

    initial = np.zeros(max(0, (len(room_ids)-1)*3), dtype=float)
    solution = least_squares(residual, initial, loss="huber", f_scale=.05)
    poses = np.zeros((len(room_ids), 3), dtype=float)
    if len(room_ids) > 1:
        poses[1:] = solution.x.reshape(-1, 3)
    poses[:,2] = np.vectorize(_wrap)(poses[:,2])
    residuals = residual(solution.x).reshape(-1,3)
    closure_residuals = []
    for edge in closure_edges:
        observed = np.array([edge["dx_m"], edge["dy_m"], edge["rotation_rad"]])
        error = _relative(poses[index[edge["room_a"]]], poses[index[edge["room_b"]]]) - observed
        error[2] = _wrap(error[2])
        closure_residuals.append(float(np.linalg.norm(error[:2])))
    closure_error = float(np.mean(closure_residuals)) if closure_residuals else None
    return {"status":"PASS" if solution.success else "REVIEW",
            "poses":{room_id:{"x_m":float(poses[i,0]),"y_m":float(poses[i,1]),
                              "rotation_rad":float(poses[i,2])}
                     for i,room_id in enumerate(room_ids)},
            "constraints_used":len(edges),"constraint_residuals":{
                f"{edge['room_a']}->{edge['room_b']}":{
                    "translation_m":float(np.linalg.norm(residuals[i,:2])),
                    "rotation_rad":float(abs(residuals[i,2]))}
                for i,edge in enumerate(edges)},
            "closure_edge_count":len(closure_edges),"closure_error_m":closure_error,
            "closure_error_status":"MEASURED_HELD_OUT_CONSTRAINTS" if closure_edges else "NOT_RUN_NO_CLOSURE_EDGES",
            "loop_closure_applied":bool(use_all_edges and closure_edges),
            "optimizer":"scipy.least_squares_huber","success":bool(solution.success)}


def candidate_feature_links(room_images, minimum_inliers=10):
    """List tentative ORB room-image matches for inspection; never auto-connect."""
    import cv2
    rooms = sorted(room_images)
    orb = cv2.ORB_create(nfeatures=1800)
    descriptors = {}
    for room_id in rooms:
        image = cv2.imread(str(room_images[room_id]))
        if image is not None:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            keypoints, desc = orb.detectAndCompute(gray, None)
            if desc is not None:
                descriptors[room_id] = (keypoints, desc)
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    candidates = []
    for i, room_a in enumerate(rooms):
        if room_a not in descriptors:
            continue
        for room_b in rooms[i+1:]:
            if room_b not in descriptors:
                continue
            kp_a, desc_a = descriptors[room_a]
            kp_b, desc_b = descriptors[room_b]
            pairs = matcher.knnMatch(desc_a, desc_b, k=2)
            good = [first for pair in pairs if len(pair) == 2
                    for first, second in [pair] if first.distance < .72*second.distance]
            if len(good) < minimum_inliers:
                continue
            points_a = np.float32([kp_a[item.queryIdx].pt for item in good])
            points_b = np.float32([kp_b[item.trainIdx].pt for item in good])
            _, mask = cv2.estimateAffinePartial2D(points_a, points_b, method=cv2.RANSAC,
                                                 ransacReprojThreshold=3.0)
            inliers = int(mask.sum()) if mask is not None else 0
            if inliers >= minimum_inliers:
                candidates.append({"room_a":room_a,"room_b":room_b,"matches":len(good),
                                   "inliers":inliers,"inlier_fraction":inliers/len(good),
                                   "status":"CANDIDATE_REVIEW_ONLY",
                                   "used_for_registration":False,
                                   "reason":"Image overlap is not proof of physical adjacency or metric alignment"})
    return candidates
