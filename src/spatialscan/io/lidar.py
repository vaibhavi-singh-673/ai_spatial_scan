from pathlib import Path
import csv, cv2, numpy as np

def read_matrix(path):
    return np.loadtxt(path, delimiter=",")

def read_odometry(path):
    rows=[]
    with open(path,newline="") as f:
        for raw in csv.DictReader(f):
            r={str(key).strip(): (value.strip() if isinstance(value,str) else value)
               for key,value in raw.items() if key is not None}
            if r.get("frame") not in (None, ""):
                rows.append(r)
    return rows

def load_lidar(folder, max_frames=None):
    folder=Path(folder)
    K=read_matrix(folder/"camera_matrix.csv")
    odom=read_odometry(folder/"odometry.csv")
    frames=[]
    depth_paths=sorted((folder/"depth").glob("*.png"))
    if max_frames and len(depth_paths)>max_frames:
        indices=np.linspace(0,len(depth_paths)-1,max_frames).astype(int)
        depth_paths=[depth_paths[index] for index in indices]
    for p in depth_paths:
        conf=folder/"confidence"/p.name
        d=cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
        c=cv2.imread(str(conf), cv2.IMREAD_GRAYSCALE) if conf.exists() else None
        frame=int(p.stem)
        match=next((r for r in odom if int(r["frame"])==frame),None)
        frames.append((frame,d,c,match))
    imu=[]
    ip=folder/"imu.csv"
    if ip.exists():
        with open(ip,newline="") as f:
            for r in csv.DictReader(f):
                try: imu.append(r)
                except Exception: pass
    return K,frames,imu

def depth_to_points(depth_mm,K,confidence=None,min_mm=250,max_mm=7000):
    h,w=depth_mm.shape
    fx,fy,cx,cy=K[0,0],K[1,1],K[0,2],K[1,2]
    # Intrinsics supplied for the RGB stream may be larger than depth raster.
    sx=w/1920.0; sy=h/1440.0
    fx*=sx; fy*=sy; cx*=sx; cy*=sy
    z=depth_mm.astype(np.float32)/1000.0
    yy,xx=np.indices((h,w))
    valid=np.isfinite(z)&(z*1000>=min_mm)&(z*1000<=max_mm)
    if confidence is not None:
        valid &= confidence>=1
    x=(xx-cx)*z/fx
    y=(yy-cy)*z/fy
    return np.column_stack((x[valid],y[valid],z[valid]))
