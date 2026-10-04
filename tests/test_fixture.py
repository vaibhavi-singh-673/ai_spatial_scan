from pathlib import Path
from spatialscan.io.lidar import load_lidar
def test_lidar_fixture_loads():
    K,frames,imu=load_lidar("fixtures/lidar_sample")
    assert K.shape==(3,3)
    assert len(frames)>0
    assert len(imu)>0
    assert all(frame[3] is not None for frame in frames)
