import json
from pathlib import Path

import cv2
import numpy as np

from ..geometry.utils import ci, polygon_area
from ..geometry.registration import candidate_feature_links, optimize_room_graph
from .scale import estimate_scale


def collect_images(path):
    path = Path(path)
    if path.is_file():
        return [path]
    return sorted(item for item in path.rglob("*")
                  if item.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"})


def collect_video_frames(path, max_frames=120):
    path = Path(path)
    files = [path] if path.is_file() else sorted(
        item for item in path.rglob("*")
        if item.suffix.lower() in {".mp4", ".mov", ".m4v", ".avi"})
    frames = []
    for file in files:
        capture = cv2.VideoCapture(str(file))
        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if total > max_frames:
            selected = set(np.linspace(0, total - 1, max_frames).astype(int))
            index = 0
            while len(frames) < max_frames:
                ok, frame = capture.read()
                if not ok:
                    break
                if index in selected:
                    frames.append(frame)
                index += 1
        else:
            while len(frames) < max_frames:
                ok, frame = capture.read()
                if not ok:
                    break
                frames.append(frame)
        capture.release()
        if len(frames) >= max_frames:
            break
    return frames


def _read_metadata(images, metadata_path=None):
    source = Path(metadata_path) if metadata_path else None
    if source is None:
        for image in images:
            parent = Path(image).parent
            for folder in (parent, *parent.parents[:4]):
                for name in ("spatialscan_capture.json", "capture_metadata.json"):
                    candidate = folder / name
                    if candidate.is_file():
                        source = candidate
                        break
                if source:
                    break
            if source:
                break
    if source and source.is_file():
        try:
            document = json.loads(source.read_text(encoding="utf-8"))
            return source, document if isinstance(document, dict) else {}
        except (OSError, json.JSONDecodeError):
            return source, {}
    return None, {}


def _transform_floor_polygon(metadata, scale):
    points = metadata.get("floor_polygon_px")
    if not points:
        return None, None
    homography = metadata.get("floor_homography_image_to_m")
    if homography is not None:
        matrix = np.asarray(homography, dtype=float)
        if matrix.shape == (3, 3):
            transformed = cv2.perspectiveTransform(
                np.asarray(points, dtype=np.float32).reshape(-1, 1, 2), matrix
            ).reshape(-1, 2)
            return transformed.tolist(), "calibrated_floor_homography"
    if scale is not None and metadata.get("floor_polygon_is_rectified") is True:
        return (np.asarray(points, dtype=float) * scale).tolist(), "rectified_floor_polygon_and_measured_scale"
    return None, None


def _lines(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    raw = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=60,
                          minLineLength=max(30, gray.shape[1] // 10), maxLineGap=15)
    return gray, edges, raw.reshape(-1, 4) if raw is not None else np.empty((0, 4), dtype=int)


def _opening_candidates(lines, width, height):
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
            bar = any(x0 <= min(left[0],right[0]) and x1 >= max(left[0],right[0])
                      and abs(y-top) < height*.04 for x0,x1,y in horizontal)
            confidence = min(.82, .35 + .24*bar + .18*min(left[3],right[3])/height)
            box = [min(left[0],right[0]), int(top), max(left[0],right[0]), int(bottom)]
            if any(abs(box[0]-item["bbox_px"][0]) < 12 and abs(box[2]-item["bbox_px"][2]) < 12
                   for item in candidates):
                continue
            candidates.append({"type": "door_candidate" if aspect >= 1.7 else "window_candidate",
                               "bbox_px": box, "width_px": float(gap),
                               "height_px": float(common_height), "confidence": float(confidence),
                               "review_required": True})
    return candidates


def _appearance_anomalies(image):
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
        mean_l = cv2.cvtColor(image[y:y+h,x:x+w],cv2.COLOR_BGR2LAB)[:,:,0].mean()
        polygon = cv2.approxPolyDP(contour,max(2,.015*cv2.arcLength(contour,True)),True)
        found.append({"bbox_px":[x,y,x+w,y+h],"polygon_px":polygon.reshape(-1,2).tolist(),
                      "damage_class":"staining_candidate" if mean_l < 105 else "impact_delamination_candidate",
                      "confidence":float(min(.69,.35+.25*min(1,area/(image_area*.02)))),
                      "status":"appearance_anomaly_requires_human_review"})
    return sorted(found,key=lambda item:item["confidence"],reverse=True)[:20]


def _measurement(value, unit, kind, room_id, identifier, method, half_width=None):
    if value is None:
        return {"id":identifier,"kind":kind,"room_id":room_id,"value":None,"unit":unit,
                "interval":None,"status":"NOT_ESTIMATED"}
    interval=ci(float(value),float(half_width),method) if half_width is not None else None
    return {"id":identifier,"kind":kind,"room_id":room_id,"value":float(value),"unit":unit,
            "interval":interval,"uncertainty_status":"NOT_QUANTIFIED" if interval is None else "DECLARED"}


def estimate_visual_plan(images, tier, scale_m_per_pixel=None, room_id="room_01",
                         room_name="Room 01", metadata_path=None):
    if not images:
        raise ValueError("No images found")
    decoded = [item if isinstance(item,np.ndarray) else cv2.imread(str(item)) for item in images]
    pairs = [(image,source) for image,source in zip(decoded,images) if image is not None]
    if not pairs:
        raise ValueError("Images could not be decoded")
    imgs = [pair[0] for pair in pairs]
    paths = [pair[1] for pair in pairs if isinstance(pair[1],Path)]
    metadata_file, metadata = _read_metadata(paths,metadata_path)
    scale_info = estimate_scale(paths,scale_m_per_pixel,metadata_file)
    image = imgs[0]
    gray, _, raw_lines = _lines(image)
    height,width = gray.shape
    line_segments = [[int(a),int(b),int(c),int(d)] for a,b,c,d in raw_lines]
    opening_candidates, anomalies = [], []
    for frame,source in pairs:
        frame_gray,_,frame_lines=_lines(frame)
        source_name=Path(source).name if isinstance(source,Path) else "video_frame"
        for candidate in _opening_candidates(frame_lines,frame_gray.shape[1],frame_gray.shape[0]):
            candidate["image"] = source_name
            opening_candidates.append(candidate)
        for anomaly in _appearance_anomalies(frame):
            anomaly["image"] = source_name
            anomalies.append(anomaly)
    opening_candidates = opening_candidates[:100]
    anomalies = anomalies[:100]
    metric_polygon, polygon_method = _transform_floor_polygon(metadata,scale_info["scale_m_per_pixel"])
    area = polygon_area(metric_polygon) if metric_polygon else None
    walls=[]
    if metric_polygon and len(metric_polygon)>=3:
        coordinates=np.asarray(metric_polygon,dtype=float)
        for index,(start,end) in enumerate(zip(coordinates,np.roll(coordinates,-1,axis=0)),1):
            length=float(np.linalg.norm(end-start))
            walls.append(_measurement(length,"m","wall_length",room_id,f"wall_{index}",
                polygon_method or "rectified_floor_boundary_edge",
                metadata.get("wall_length_uncertainty_m")))
    room = {"id":room_id,"name":room_name,"polygon_xy_m":metric_polygon or [],
            "floor_area_m2":_measurement(area,"m2","floor_area",room_id,"floor_area",
                    polygon_method or "NOT_ESTIMATED_NO_RECTIFIED_FLOOR_BOUNDARY",
                    metadata.get("floor_area_uncertainty_m2")),
            "ceiling_height_m":_measurement(metadata.get("ceiling_height_m"),"m","ceiling_height",room_id,
                    "ceiling_height",metadata.get("ceiling_height_source","NOT_ESTIMATED_NO_HEIGHT_REFERENCE"),
                    metadata.get("ceiling_height_uncertainty_m")),
            "walls":walls,"openings":[]}
    for index,candidate in enumerate(opening_candidates,1):
        oid=f"opening_candidate_{index}"
        usable_pixel_scale = (scale_m_per_pixel if scale_m_per_pixel is not None else
                              scale_info["scale_m_per_pixel"] if scale_info["metric_scale_is_global"] else None)
        width_m=candidate["width_px"]*usable_pixel_scale if usable_pixel_scale is not None else None
        scale_uncertainty=scale_info.get("scale_uncertainty_m_per_pixel")
        width_uncertainty=(candidate["width_px"]*scale_uncertainty if width_m is not None
                           and scale_uncertainty is not None else None)
        room["openings"].append({"id":oid,"room_id":room_id,"type":candidate["type"],
            "width":_measurement(width_m,"m","opening_width",room_id,oid,
                 "explicit_uniform_pixel_scale_provisional",width_uncertainty),
            "detected":False,"candidate":True,"confidence":candidate["confidence"],
            "review_required":True,"image_bbox_px":candidate["bbox_px"]})
    damage=[{"id":f"damage_candidate_{i}","room_id":room_id,
             "surface":f"image:{item.get('image','unknown')}","damage_class":item["damage_class"],
             "extent_m2":None,"polygon_xy_m":[],"polygon_px":item["polygon_px"],
             "confidence":item["confidence"],"status":item["status"]}
            for i,item in enumerate(anomalies,1)]
    return {"schema_version":"1.0","capture_id":f"{tier}_capture_{len(imgs)}_frames","tier":tier,
        "device":{"source":"visual capture; device metadata not inferred","images_used":len(imgs),
                  "frame_width_px":width,"frame_height_px":height},
        "rooms":[room],"plan":{"rooms":[room],"adjacency":[],
            "stitched_polygon_xy_m":metric_polygon or [],
            "drift":{"status":"NOT_RUN","method":"No cross-room metric correspondences provided",
                     "loop_closure_applied":False}},
        "damage":damage,"scope":[],"diagnostics":{
            "line_segments":len(line_segments),"input_frames":len(imgs),"scale":scale_info,
            "calibration_status":scale_info["status"],
            "scale_m_per_pixel":scale_info["scale_m_per_pixel"],
            "geometry_status":"METRIC_FLOOR_POLYGON_AVAILABLE" if metric_polygon else "PIXEL_OBSERVATIONS_ONLY",
            "observed_pixel_geometry":{"image_width_px":width,"image_height_px":height,
                "floor_boundary_annotated":bool(metadata.get("floor_polygon_px"))},
            "opening_candidates":opening_candidates,"damage_candidates":anomalies,
            "room_links":metadata.get("room_links",[]),
            "cross_room_consistency":"NOT_RUN_SINGLE_ROOM_RESULT",
            "note":"Intrinsics or a local reference alone do not make a perspective image metric. Floor area and height remain null without rectified geometry or direct measurement.",
            "metadata_path":str(metadata_file) if metadata_file else None}}


def _place_rooms(rooms, graph):
    if graph.get("status") != "PASS":
        return None, rooms
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    placed, polygons = [], []
    for room in rooms:
        pose = graph["poses"].get(room["id"])
        polygon = room.get("polygon_xy_m") or []
        if not pose or len(polygon) < 3:
            placed.append({**room, "global_polygon_xy_m": []})
            continue
        c, s = np.cos(pose["rotation_rad"]), np.sin(pose["rotation_rad"])
        xy = [[c*x-s*y+pose["x_m"],s*x+c*y+pose["y_m"]] for x,y in polygon]
        placed.append({**room, "global_polygon_xy_m": xy})
        shape = Polygon(xy)
        if not shape.is_valid:
            shape = shape.buffer(0)
        if not shape.is_empty:
            polygons.append(shape)
    if not polygons:
        return None, placed
    merged = unary_union(polygons)
    if merged.geom_type == "MultiPolygon":
        merged = max(merged.geoms, key=lambda item:item.area)
    return [[float(x),float(y)] for x,y in list(merged.exterior.coords)[:-1]], placed


def estimate_visual_capture(images, tier, scale_m_per_pixel=None, metadata_path=None, drift_mode="on"):
    if not images:
        raise ValueError("No images found")
    if tier == "photos" and all(isinstance(item,Path) for item in images):
        groups={}
        for image in images:
            groups.setdefault(image.parent.name,[]).append(image)
    else:
        groups={"room_01":images}
    results=[]
    for room_id,room_images in sorted(groups.items()):
        results.append(estimate_visual_plan(room_images,tier,scale_m_per_pixel,room_id,
                                             room_id.replace("_"," ").title(),metadata_path))
    first=results[0]
    rooms=[item["rooms"][0] for item in results]
    first["capture_id"]=f"{tier}_capture_{len(rooms)}_rooms"
    first["rooms"]=rooms
    first["plan"]["rooms"]=rooms
    first["diagnostics"]["rooms_detected"]=len(rooms)
    first["diagnostics"]["input_frames"]=sum(item["diagnostics"]["input_frames"] for item in results)
    first["device"]["rooms_detected"]=len(rooms)
    first["device"]["images_used"]=first["diagnostics"]["input_frames"]
    scales=[item["diagnostics"]["scale_m_per_pixel"] for item in results
            if item["diagnostics"]["scale_m_per_pixel"] is not None]
    if len(scales)>1:
        median=float(np.median(scales))
        spread=float((max(scales)-min(scales))/median) if median else None
        first["diagnostics"]["cross_room_consistency"]={"status":"CONSISTENT" if spread is not None and spread<=.10 else "CONFLICT",
            "relative_scale_spread":spread,"room_scales_m_per_pixel":scales,"scale_propagated":False}
    representative_images = {room_id:room_images[0] for room_id,room_images in groups.items()
                             if room_images and isinstance(room_images[0],Path)}
    candidate_links = candidate_feature_links(representative_images) if len(representative_images)>1 else []
    constraints = first["diagnostics"].get("room_links",[])
    if not isinstance(constraints,list):
        constraints=[]
    drift_off=optimize_room_graph([room["id"] for room in rooms],constraints,use_all_edges=False)
    drift_on=optimize_room_graph([room["id"] for room in rooms],constraints,use_all_edges=True)
    off_footprint,off_rooms=_place_rooms(rooms,drift_off)
    on_footprint,on_rooms=_place_rooms(rooms,drift_on)
    selected=drift_on if drift_mode=="on" else drift_off
    selected_footprint=on_footprint if drift_mode=="on" else off_footprint
    selected_rooms=on_rooms if drift_mode=="on" else off_rooms
    if selected.get("status")=="PASS":
        for room in rooms:
            placed=next((item for item in selected_rooms if item["id"]==room["id"]),None)
            if placed and placed.get("global_polygon_xy_m"):
                room["polygon_xy_m"]=placed["global_polygon_xy_m"]
        first["plan"]["stitched_polygon_xy_m"]=selected_footprint or []
    first["plan"]["adjacency"]=[{"room_a":edge["room_a"],"room_b":edge["room_b"],
        "status":"VERIFIED","source":edge.get("source","manifest_relative_transform")}
        for edge in constraints if edge.get("verified") is True]
    first["plan"]["drift"]={"selected_mode":drift_mode,"selected_graph":selected,
        "drift_off_graph":drift_off,"drift_on_graph":drift_on,
        "drift_ablation":{"off_footprint_xy_m":off_footprint,"on_footprint_xy_m":on_footprint},
        "loop_closure_applied":bool(selected.get("loop_closure_applied",False))}
    first["diagnostics"]["room_correspondence_candidates"]=candidate_links
    first["diagnostics"]["verified_room_constraints"]=len([edge for edge in constraints if edge.get("verified") is True])
    return first
