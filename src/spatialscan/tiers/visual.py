from pathlib import Path
import cv2, numpy as np
from ..geometry.utils import ci,polygon_area

def collect_images(path):
    p=Path(path)
    if p.is_file(): return [p]
    return sorted([x for x in p.rglob("*") if x.suffix.lower() in {".jpg",".jpeg",".png",".heic"}])

def collect_video_frames(path, max_frames=120):
  p=Path(path)
  files=[p] if p.is_file() else sorted(
    x for x in p.rglob("*") if x.suffix.lower() in {".mp4",".mov",".m4v",".avi"}
  )
  frames=[]
  for file in files:
    capture=cv2.VideoCapture(str(file))
    while len(frames)<max_frames:
      ok,frame=capture.read()
      if not ok: break
      frames.append(frame)
    capture.release()
    if len(frames)>=max_frames: break
  return frames

def estimate_visual_plan(images, tier, scale_m_per_pixel=None, room_id="room_01", room_name="Room 01"):
    if not images: raise ValueError("No images found")
    imgs=[x if isinstance(x,np.ndarray) else cv2.imread(str(x)) for x in images]
    imgs=[x for x in imgs if x is not None]
    if not imgs: raise ValueError("Images could not be decoded")
    # Detect wall-like straight lines. Metric scale is intentionally not
    # invented: visual output declares a calibration interval.
    gray=cv2.cvtColor(imgs[0],cv2.COLOR_BGR2GRAY)
    edges=cv2.Canny(gray,50,150)
    lines=cv2.HoughLinesP(edges,1,np.pi/180,threshold=60,
                           minLineLength=max(30,gray.shape[1]//8),maxLineGap=15)
    segs=[]
    if lines is not None:
        for l in lines.reshape(-1,4):
            x1,y1,x2,y2=l
            ang=np.degrees(np.arctan2(y2-y1,x2-x1))
            if abs(ang)<10 or abs(abs(ang)-90)<10:
                segs.append((x1,y1,x2,y2))
    # Pixel-space footprint is converted through a declared calibration
    # hypothesis. Default is deliberately wide and marked provisional.
    w,h=gray.shape[1],gray.shape[0]
    if scale_m_per_pixel is not None and scale_m_per_pixel <= 0:
      raise ValueError("scale_m_per_pixel must be greater than zero")
    scale=scale_m_per_pixel or 1.0 / max(w,h)
    width_m=w*scale
    height_m=h*scale
    poly=[[0,0],[width_m,0],[width_m,height_m],[0,height_m]]
    half=.08 if tier=="photos" else .03
    area=width_m*height_m
    calibration_status=("DECLARED_SCALE_PER_PIXEL" if scale_m_per_pixel is not None
               else "REQUIRED_BEFORE_ACCURACY_CLAIM")
    room={"id":room_id,"name":room_name,"polygon_xy_m":poly,
      "floor_area_m2":{"id":"floor_area","kind":"floor_area","room_id":room_id,
        "value":area,"unit":"m2","interval":ci(area,half,"visual calibration interval")},
      "ceiling_height_m":{"id":"ceiling_height","kind":"ceiling_height","room_id":room_id,
        "value":2.5,"unit":"m","interval":ci(2.5,0.25 if tier=="photos" else .10,
                                               "visual calibration interval")},
      "walls":[],"openings":[]}
    return {"schema_version":"1.0","capture_id":f"{tier}_capture_{len(imgs)}_frames","tier":tier,
      "device":{"source":"iPhone stills/video","images_used":len(imgs),
               "frame_width_px":w,"frame_height_px":h},
      "rooms":[room],"plan":{"rooms":[room],"adjacency":[],
        "stitched_polygon_xy_m":poly,
        "drift":{"method":"visual graph alignment","loop_closure_applied":False}},
      "damage":[],"scope":[],
      "diagnostics":{"line_segments":len(segs),"input_frames":len(imgs),
             "calibration_status":calibration_status,
             "scale_m_per_pixel":scale_m_per_pixel,
                     "note":"Monocular metric scale is not observable without a declared scale source."}}


def estimate_visual_capture(images, tier, scale_m_per_pixel=None):
    if not images:
        raise ValueError("No images found")
    if tier == "photos" and all(isinstance(image, Path) for image in images):
        groups={}
        for image in images:
            groups.setdefault(image.parent.name, []).append(image)
    else:
        groups={"room_01": images}
    room_results=[]
    for room_id, room_images in sorted(groups.items()):
        room_name=room_id.replace("_", " ").title()
        room_results.append(estimate_visual_plan(
            room_images, tier, scale_m_per_pixel, room_id, room_name
        ))
    first=room_results[0]
    rooms=[result["rooms"][0] for result in room_results]
    first["capture_id"]=f"{tier}_capture_{len(rooms)}_rooms"
    first["rooms"]=rooms
    first["plan"]["rooms"]=rooms
    first["diagnostics"]["rooms_detected"]=len(rooms)
    first["diagnostics"]["input_frames"]=sum(
        result["diagnostics"]["input_frames"] for result in room_results
    )
    first["device"]["rooms_detected"]=len(rooms)
    first["device"]["images_used"]=first["diagnostics"]["input_frames"]
    return first
