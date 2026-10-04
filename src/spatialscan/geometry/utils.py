import numpy as np
def polygon_area(poly):
    p=np.asarray(poly,float)
    return float(abs(np.dot(p[:,0],np.roll(p[:,1],-1))-np.dot(p[:,1],np.roll(p[:,0],-1)))/2)
def ci(v,half,method):
    return {"estimate_m":float(v),"low_m":float(max(0,v-half)),
            "high_m":float(v+half),"confidence":0.95,"method":method}
def percentile_ci(values):
    a=np.asarray(values,float)
    if len(a)<2: return 0.0
    return float(1.96*np.std(a,ddof=1)/np.sqrt(len(a)))
