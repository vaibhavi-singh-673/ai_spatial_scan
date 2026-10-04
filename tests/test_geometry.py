from spatialscan.geometry.utils import polygon_area
def test_polygon_area():
    assert polygon_area([[0,0],[4,0],[4,3],[0,3]]) == 12
