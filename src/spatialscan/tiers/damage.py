"""Appearance-anomaly segmentation producing explicitly unverified candidates."""

import cv2
import numpy as np


def detect_damage_candidates(image):
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    local = cv2.GaussianBlur(lab, (0,0), 13)
    delta = cv2.absdiff(lab, local)[:,:,0]
    threshold = max(18, int(np.percentile(delta, 98)))
    mask = cv2.threshold(delta, threshold, 255, cv2.THRESH_BINARY)[1]
    kernel = np.ones((5,5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_area = image.shape[0]*image.shape[1]
    found = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < max(100, image_area*.0004) or area > image_area*.08:
            continue
        x,y,w,h = cv2.boundingRect(contour)
        patch_lab = cv2.cvtColor(image[y:y+h,x:x+w],cv2.COLOR_BGR2LAB)
        mean_l = float(patch_lab[:,:,0].mean())
        polygon = cv2.approxPolyDP(contour,max(2,.015*cv2.arcLength(contour,True)),True)
        found.append({"bbox_px":[x,y,x+w,y+h], "polygon_px":polygon.reshape(-1,2).tolist(),
            "damage_class":"staining_candidate" if mean_l < 105 else "impact_delamination_candidate",
            "confidence":float(min(.69,.35+.25*min(1,area/(image_area*.02)))),
            "segmentation_method":"local_L_channel_appearance_anomaly",
            "metric_projection":"NOT_AVAILABLE_WITHOUT_SURFACE_GEOMETRY",
            "status":"appearance_anomaly_requires_human_review"})
    return sorted(found,key=lambda item:item["confidence"],reverse=True)[:20]
