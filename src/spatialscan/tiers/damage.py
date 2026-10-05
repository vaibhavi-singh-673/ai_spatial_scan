"""Appearance-anomaly segmentation producing explicitly unverified candidates."""

import cv2
import numpy as np


def _metric_projection(polygon_px, homography):
    if homography is None:
        return None, None
    matrix = np.asarray(homography, dtype=float)
    if matrix.shape != (3, 3) or not np.all(np.isfinite(matrix)):
        return None, None
    points = cv2.perspectiveTransform(np.asarray(polygon_px, dtype=np.float32).reshape(-1, 1, 2),
                                      matrix).reshape(-1, 2)
    if len(points) < 3 or not np.all(np.isfinite(points)):
        return None, None
    x, y = points[:, 0], points[:, 1]
    area = abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))) / 2
    return points.tolist(), area


def detect_damage_candidates(image, surface_regions=None):
    """Segment appearance anomalies, classify by cues, and project only with a surface homography."""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    local = cv2.GaussianBlur(lab, (0,0), 13)
    luminance_delta = cv2.absdiff(lab, local)[:, :, 0]
    chroma_delta = cv2.absdiff(lab[:, :, 1:], local[:, :, 1:]).max(axis=2)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    local_texture = cv2.Laplacian(gray, cv2.CV_32F, ksize=3)
    texture_energy = cv2.GaussianBlur(np.abs(local_texture), (0, 0), 5)
    anomaly = cv2.max(luminance_delta, chroma_delta)
    threshold = max(18, int(np.percentile(anomaly, 98)))
    texture_threshold = float(np.percentile(texture_energy, 92))
    color_mask = cv2.threshold(anomaly, threshold, 255, cv2.THRESH_BINARY)[1]
    texture_mask = cv2.threshold(texture_energy, texture_threshold, 255, cv2.THRESH_BINARY)[1].astype(np.uint8)
    mask = cv2.bitwise_or(color_mask, texture_mask)
    kernel = np.ones((5,5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    regions = surface_regions if isinstance(surface_regions, list) else []
    if regions:
        roi = np.zeros(mask.shape, dtype=np.uint8)
        valid_regions = []
        for region in regions:
            try:
                boundary = np.asarray(region["polygon_px"], dtype=np.int32).reshape(-1, 1, 2)
                if len(boundary) < 3:
                    continue
                cv2.fillPoly(roi, [boundary], 255)
                valid_regions.append((region, boundary))
            except (KeyError, TypeError, ValueError):
                continue
        mask = cv2.bitwise_and(mask, roi)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_area = image.shape[0]*image.shape[1]
    found = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < max(100, image_area*.0004) or area > image_area*.08:
            continue
        x,y,w,h = cv2.boundingRect(contour)
        patch_lab = lab[y:y+h, x:x+w]
        patch_texture = float(texture_energy[y:y+h, x:x+w].mean())
        patch_chroma = float(chroma_delta[y:y+h, x:x+w].mean())
        polygon = cv2.approxPolyDP(contour,max(2,.015*cv2.arcLength(contour,True)),True)
        polygon_px = polygon.reshape(-1,2).tolist()
        moments = cv2.moments(contour)
        center = (moments["m10"]/moments["m00"], moments["m01"]/moments["m00"]) if moments["m00"] else (x+w/2,y+h/2)
        region_match = next(((region, boundary) for region, boundary in valid_regions
                             if cv2.pointPolygonTest(boundary, center, False) >= 0), None) if regions else None
        selected_region = region_match[0] if region_match else None
        homography = selected_region.get("homography_image_to_m") if selected_region else None
        metric_polygon, metric_area = _metric_projection(polygon_px, homography)
        if patch_texture >= texture_threshold and len(polygon_px) >= 5:
            candidate_class = "impact_delamination_candidate"
            cue = "high_local_texture_and_irregular_boundary"
        elif patch_chroma >= threshold:
            candidate_class = "staining_candidate"
            cue = "local_chromatic_anomaly"
        else:
            candidate_class = "surface_anomaly_unclassified"
            cue = "insufficient_class_specific_cues"
        confidence = min(.69, .30 + .20*min(1, area/(image_area*.02))
                         + .10*min(1, patch_chroma/255) + .09*min(1, patch_texture/64))
        found.append({"bbox_px":[x,y,x+w,y+h], "polygon_px":polygon_px,
            "damage_class":candidate_class, "classification_cue":cue,
            "confidence":float(confidence),
            "segmentation_method":"local_color_and_texture_anomaly",
            "surface_polygon_xy_m":metric_polygon, "extent_m2":metric_area,
            "surface_id":selected_region.get("surface_id") if selected_region else None,
            "metric_projection":"CALIBRATED_SURFACE_HOMOGRAPHY" if metric_polygon else
                                "NOT_AVAILABLE_WITHOUT_SURFACE_GEOMETRY",
            "status":"appearance_anomaly_requires_human_review"})
    return sorted(found,key=lambda item:item["confidence"],reverse=True)[:20]
