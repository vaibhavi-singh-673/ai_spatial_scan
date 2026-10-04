$ErrorActionPreference = "Stop"
python -m spatialscan run --tier lidar --input fixtures/lidar_sample --output runs/lidar_fixture.json --render runs/lidar_fixture.png
