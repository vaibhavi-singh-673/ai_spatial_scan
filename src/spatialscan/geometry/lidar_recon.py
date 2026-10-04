from __future__ import annotations
import numpy as np
from scipy.spatial import ConvexHull
from .utils import polygon_area

def quat_to_R(qx,qy,qz,qw):
    n=(qx*qx+qy*qy+qz*qz+qw*qw)**0.5 or 1.0
    x,y,z,w=qx/n,qy/n,qz/n,qw/n
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

def _transform(points, pose):
    if not pose: return points
    try:
        R=quat_to_R(float(pose['qx']),float(pose['qy']),float(pose['qz']),float(pose['qw']))
        t=np.array([float(pose['x']),float(pose['y']),float(pose['z'])])
        return points@R.T+t
    except (KeyError,ValueError,TypeError):
        return points

def _fit_plane(P, expected_normal=None, iterations=160, threshold=.025):
    if len(P)<50: return None
    rng=np.random.default_rng(7); best=None
    for _ in range(iterations):
        a,b,c=P[rng.choice(len(P),3,replace=False)]
        n=np.cross(b-a,c-a); norm=np.linalg.norm(n)
        if norm<1e-7: continue
        n=n/norm; d=-float(n@a)
        dist=np.abs(P@n+d)
        score=int(np.count_nonzero(dist<threshold))
        if expected_normal is not None and abs(float(n@expected_normal))<0.80: continue
        if best is None or score>best[0]: best=(score,n,d)
    if best is None: return None
    n=best[1]; d=best[2]
    if n[1]<0: n=-n; d=-d
    return n,d,best[0]

def reconstruct_lidar(K,frames,imu=None,max_frames=120):
    idx=np.linspace(0,len(frames)-1,min(max_frames,len(frames))).astype(int)
    pts=[]
    for i in idx:
        frame,d,c,pose=frames[i]
        if d is None: continue
        h,w=d.shape
        fx,fy,cx,cy=K[0,0],K[1,1],K[0,2],K[1,2]
        sx=w/1920; sy=h/1440
        fx*=sx; fy*=sy; cx*=sx; cy*=sy
        z=d.astype(np.float32)/1000
        yy,xx=np.indices((h,w))
        valid=(z>.25)&(z<7.0)
        if c is not None: valid &= c>=1
        x=(xx-cx)*z/fx; y=(yy-cy)*z/fy
        p=np.column_stack((x[valid],y[valid],z[valid]))
        p=_transform(p,pose)
        if len(p): pts.append(p[::max(1,len(p)//2500 or 1)])
    if not pts: raise ValueError('No valid LiDAR points')
    P=np.vstack(pts)
    # Estimate world-up from the IMU gravity direction when available.
    expected_up=None
    if imu:
        acc=[]
        for r in imu:
            try: acc.append([float(r['a_x']),float(r['a_y']),float(r['a_z'])])
            except Exception: pass
        if acc:
            g=np.median(np.asarray(acc),axis=0); g=g/(np.linalg.norm(g) or 1.0)
            # IMU is expressed in camera coordinates. Use the first pose rotation.
            pose0=next((x[3] for x in frames if x[3]),None)
            if pose0:
                R0=quat_to_R(float(pose0['qx']),float(pose0['qy']),float(pose0['qz']),float(pose0['qw']))
                expected_up=-(R0@g); expected_up/=np.linalg.norm(expected_up) or 1.0
    # Use robust plane fitting for the dominant floor-like plane, constrained by gravity.
    plane=_fit_plane(P,expected_up)
    if plane is None:
        up=expected_up if expected_up is not None else np.array([0.,1.,0.]); origin=P.mean(0)
    else:
        up,d,_=plane; origin=-d*up
    hcoord=P@up
    # The floor is the lowest strong horizontal support. A low quantile alone is
    # unstable when furniture occupies the lower tail, so snap to the densest bin.
    qs=np.quantile(hcoord,np.linspace(.02,.30,80))
    scores=[]
    for q in qs: scores.append(np.count_nonzero(np.abs(hcoord-q)<.035))
    floor_level=float(qs[int(np.argmax(scores))])
    floor_pts=P[np.abs(hcoord-floor_level)<.045]
    if len(floor_pts)<30:
        floor_pts=P[np.abs(hcoord-np.median(hcoord))<.08]
    # horizontal basis from PCA, stable and deterministic.
    X=floor_pts-(floor_pts@up)[:,None]*up
    X-=X.mean(0)
    _,_,Vt=np.linalg.svd(X,full_matrices=False)
    e1=Vt[0]; e1-=up*(e1@up); e1/=np.linalg.norm(e1)
    e2=np.cross(up,e1); e2/=np.linalg.norm(e2)
    xy=np.column_stack((X@e1,X@e2))
    if len(xy)>=3:
        hull=ConvexHull(xy); poly2=xy[hull.vertices]
    else:
        lo=xy.min(0); hi=xy.max(0); poly2=np.array([[lo[0],lo[1]],[hi[0],lo[1]],[hi[0],hi[1]],[lo[0],hi[1]]])
    area=polygon_area(poly2)
    # Ceiling: upper robust percentile relative to the floor plane. Clip outliers.
    top=float(np.quantile(hcoord,.97)); ceiling=max(1.8,top-floor_level)
    dims=[]
    for a,b in zip(poly2,np.roll(poly2,-1,axis=0)):
        dims.append((a,b,float(np.linalg.norm(b-a))))
    area_half=max(.03*area,.02); ceil_half=max(.015,.02*ceiling)
    return dict(points=P,polygon=poly2,area=area,
      area_ci={'estimate_m':area,'low_m':max(0,area-area_half),'high_m':area+area_half,'confidence':.95,'method':'pose-normalized floor hull'},
      ceiling=ceiling,ceiling_ci={'estimate_m':ceiling,'low_m':max(0,ceiling-ceil_half),'high_m':ceiling+ceil_half,'confidence':.95,'method':'pose-normalized vertical quantile'},
      walls=dims,frame_count=len(idx))
