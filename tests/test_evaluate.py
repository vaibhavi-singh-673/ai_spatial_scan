import json
from spatialscan.evaluate import evaluate

def test_evaluate_ceiling(tmp_path):
    gt={'rooms':[{'id':'r','floor_area_m2':{'value':10},'ceiling_height_m':{'value':2.5},'walls':[]}]} 
    pr={'rooms':[{'id':'r','floor_area_m2':{'value':10.2},'ceiling_height_m':{'value':2.505},'walls':[]}]} 
    a=tmp_path/'p.json'; b=tmp_path/'g.json'; a.write_text(json.dumps(pr)); b.write_text(json.dumps(gt))
    out=evaluate(a,b)
    assert out['gates']['ceiling_height']['status']=='PASS'
