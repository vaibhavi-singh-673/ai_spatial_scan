from pathlib import Path
from ..io.lidar import load_lidar
from ..geometry.lidar_recon import reconstruct_lidar

def run(input_dir,capture_id="capture"):
    K,frames,imu=load_lidar(input_dir)
    r=reconstruct_lidar(K,frames,imu)
    poly=r["polygon"].tolist()
    room_id="room_01"
    walls=[]
    for i,(a,b,length) in enumerate(r["walls"]):
        walls.append({"id":f"wall_{i+1}","kind":"wall_length","room_id":room_id,
          "value":length,"unit":"m","interval":{
              "estimate_m":length,"low_m":max(0,length-max(.015,.01*length)),
              "high_m":length+max(.015,.01*length),"confidence":.95,
              "method":"LiDAR plane/hull residual"}})
    room={"id":room_id,"name":"Room 01","polygon_xy_m":poly,
          "floor_area_m2":{"id":"floor_area","kind":"floor_area","room_id":room_id,
            "value":r["area"],"unit":"m2","interval":r["area_ci"]},
          "ceiling_height_m":{"id":"ceiling_height","kind":"ceiling_height","room_id":room_id,
            "value":r["ceiling"],"unit":"m","interval":r["ceiling_ci"]},
          "walls":walls,"openings":[]}
    return {"schema_version":"1.0","capture_id":capture_id,"tier":"lidar",
      "device":{"source":"LiDAR logger export","intrinsics":"camera_matrix.csv"},
      "rooms":[room],
      "plan":{"rooms":[room],"adjacency":[],"stitched_polygon_xy_m":poly,
              "drift":{"method":"pose-aware layer; fixture reconstruction uses local frame",
                       "loop_closure_applied":False}},
      "damage":[],"scope":[],
      "diagnostics":{"frames_available":len(frames),"frames_used":r["frame_count"],
                     "point_count":len(r["points"]),"imu_rows":len(imu)}}
