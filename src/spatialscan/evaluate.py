import json, math

def _rooms(x): return {r['id']:r for r in x.get('rooms',[])}
def _status(ok): return 'PASS' if ok else 'FAIL'
def _rel(a,b): return abs(a-b)/abs(b) if b else None

def evaluate(prediction,gt):
    p=json.load(open(prediction)); g=json.load(open(gt))
    pr=_rooms(p); gr=_rooms(g); gates={}
    common=sorted(set(pr)&set(gr))
    if not common:
        return {'status':'INSUFFICIENT_GROUND_TRUTH','gates':{}}
    # Ceiling gate: <= 1.5 cm per room.
    vals=[]
    for rid in common:
        a=pr[rid]['ceiling_height_m']['value']; b=gr[rid]['ceiling_height_m']['value']
        vals.append(abs(a-b))
    mx=max(vals)
    gates['ceiling_height']={'max_error_m':mx,'status':_status(mx<=.015),'tolerance_m':.015}
    # Floor footprint gate.
    pa=sum(r['floor_area_m2']['value'] for r in pr.values() if r['id'] in gr)
    ga=sum(r['floor_area_m2']['value'] for r in gr.values() if r['id'] in pr)
    err=_rel(pa,ga)
    gates['whole_property_footprint']={'error_fraction':err,'status':_status(err is not None and err<=.08),'tolerance_fraction':.08}
    # Wall lengths, if GT exposes ordered wall measurements.
    pred_w=[]; gt_w=[]
    for rid in common:
        pred_w += [x['value'] for x in pr[rid].get('walls',[])]
        gt_w += [x['value'] for x in gr[rid].get('walls',[])]
    if pred_w and gt_w:
        n=min(len(pred_w),len(gt_w)); errs=[abs(pred_w[i]-gt_w[i]) for i in range(n)]
        gates['wall_length']={'count':n,'max_error_m':max(errs),'mean_error_m':sum(errs)/n,
                              'status':_status(max(errs)<=.08*max(gt_w[:n]))}
    else:
        gates['wall_length']={'status':'NOT_RUN','reason':'ordered wall ground truth not supplied'}
    return {'status':'PASS' if all(v['status']=='PASS' for v in gates.values() if v['status'] in ('PASS','FAIL')) and all(v['status']!='NOT_RUN' for v in gates.values()) else 'FAIL','gates':gates}
