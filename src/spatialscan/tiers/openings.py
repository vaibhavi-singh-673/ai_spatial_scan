"""Geometric opening candidates from wall discontinuities in image linework.

These are review candidates, not confirmed detections or metric measurements.
"""

import cv2


def detect_opening_candidates(lines, width, height):
    vertical, horizontal = [], []
    for x1, y1, x2, y2 in lines:
        dx, dy = abs(int(x2)-int(x1)), abs(int(y2)-int(y1))
        if dy >= max(45, height*.10) and dx <= max(8, dy*.08):
            vertical.append((int((x1+x2)/2), min(y1,y2), max(y1,y2), dy))
        elif dx >= max(35, width*.06) and dy <= max(8, dx*.08):
            horizontal.append((min(x1,x2), max(x1,x2), int((y1+y2)/2)))
    candidates = []
    for i, left in enumerate(vertical):
        for right in vertical[i+1:]:
            gap = abs(right[0]-left[0])
            top, bottom = max(left[1],right[1]), min(left[2],right[2])
            common_height = bottom-top
            if not width*.025 <= gap <= width*.38 or common_height < height*.12:
                continue
            aspect = common_height/max(gap,1)
            if not .65 <= aspect <= 5.5:
                continue
            header = any(x0 <= min(left[0],right[0]) and x1 >= max(left[0],right[0])
                         and abs(y-top) < height*.04 for x0,x1,y in horizontal)
            confidence = min(.82, .35 + .24*header + .18*min(left[3],right[3])/height)
            box = [min(left[0],right[0]), int(top), max(left[0],right[0]), int(bottom)]
            if any(abs(box[0]-item["bbox_px"][0]) < 12 and abs(box[2]-item["bbox_px"][2]) < 12
                   for item in candidates):
                continue
            candidates.append({"type": "door_candidate" if aspect >= 1.7 else "window_candidate",
                "bbox_px": box, "width_px": float(gap), "height_px": float(common_height),
                "confidence": float(confidence), "review_required": True,
                "geometry_checks": {"paired_jambs": True, "header_line": bool(header),
                                    "wall_consistency": "UNVERIFIED"},
                "status": "CANDIDATE_REVIEW_ONLY"})
    return candidates
