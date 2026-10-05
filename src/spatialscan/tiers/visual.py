import json
from pathlib import Path

import cv2
import numpy as np

from ..geometry.utils import ci, polygon_area
from ..geometry.registration import candidate_feature_links, optimize_room_graph
from .scale import estimate_scale
from .openings import detect_opening_candidates
from .damage import detect_damage_candidates


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
        for candidate in detect_opening_candidates(frame_lines,frame_gray.shape[1],frame_gray.shape[0]):
            candidate["image"] = source_name
            opening_candidates.append(candidate)
        surface_mappings = metadata.get("damage_surface_regions", {})
        if isinstance(surface_mappings, list):
            surface_regions = surface_mappings
        elif isinstance(surface_mappings, dict):
            surface_regions = surface_mappings.get(source_name, surface_mappings.get("default", []))
        else:
            surface_regions = []
        for anomaly in detect_damage_candidates(frame, surface_regions):
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
        image_name = candidate.get("image")
        wall_mappings = metadata.get("wall_homographies_image_to_m", {})
        if not isinstance(wall_mappings, dict):
            wall_mappings = {}
        wall_homography = wall_mappings.get(image_name, wall_mappings.get("default"))
        width_m, measurement_method = None, "NOT_ESTIMATED_NO_WALL_PLANE_CALIBRATION"
        if wall_homography is not None:
            matrix = np.asarray(wall_homography, dtype=float)
            if matrix.shape == (3,3) and np.all(np.isfinite(matrix)):
                x0, y0, x1, y1 = candidate["bbox_px"]
                points = cv2.perspectiveTransform(np.asarray(
                    [[[x0, (y0+y1)/2], [x1, (y0+y1)/2]]], dtype=np.float32), matrix)[0]
                projected_width = float(np.linalg.norm(points[1]-points[0]))
                if np.all(np.isfinite(points)) and projected_width > 0:
                    width_m = projected_width
                    measurement_method = "calibrated_wall_homography"
        elif (metadata.get("opening_geometry_is_rectified") is True and
              scale_info["scale_m_per_pixel"] is not None):
            width_m = candidate["width_px"] * scale_info["scale_m_per_pixel"]
            measurement_method = "rectified_opening_plane_and_measured_scale"
        width_uncertainty = metadata.get("opening_width_uncertainty_m") if width_m is not None else None
        room["openings"].append({"id":oid,"room_id":room_id,"type":candidate["type"],
            "width":_measurement(width_m,"m","opening_width",room_id,oid,
                 measurement_method,width_uncertainty),
            "detected":False,"candidate":True,"confidence":candidate["confidence"],
            "review_required":True,"image_bbox_px":candidate["bbox_px"],
            "metric_projection":"CALIBRATED_WALL_PLANE" if width_m is not None else "PIXEL_CANDIDATE_ONLY"})
    damage=[{"id":f"damage_candidate_{i}","room_id":room_id,
             "surface":item.get("surface_id") or f"image:{item.get('image','unknown')}",
             "damage_class":item["damage_class"],
             "extent_m2":item.get("extent_m2"),"polygon_xy_m":item.get("surface_polygon_xy_m") or [],
             "polygon_px":item["polygon_px"],
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
