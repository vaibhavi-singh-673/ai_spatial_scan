# Stock capture protocol — evaluator page

## Hardware matrix

| Tier | Minimum | Preferred | Input |
|---|---|---|---|
| Photos | iPhone 15 | iPhone 15 Pro/Pro Max | 2–8 stills per room |
| Video | iPhone 15 | iPhone 15 Pro/Pro Max | handheld walkthrough clip |
| LiDAR | iPhone 15 Pro/Pro Max | current Pro-class iPhone | depth + poses + intrinsics export |

## Photo tier

1. Use the native iPhone Camera app.
2. Turn on the room lights; do not use portrait mode or panorama.
3. Stand near the doorway and take 2–8 stills that together show every wall.
4. Keep the phone approximately chest height.
5. Overlap adjacent views by roughly one third.
6. Include the floor/wall junction where practical.
7. Do not move furniture.
8. Make one folder per room: `photos/<room_id>/`.
9. Copy the folders unchanged to the pipeline machine.

This tier has no metric scale observation by itself. The pipeline therefore reports a calibration requirement and widened interval until a declared scale source is supplied.

## Video tier

1. Use native Camera, 4K/30 where storage permits.
2. Start at the doorway.
3. Walk slowly, approximately one metre every 2–3 seconds.
4. Keep the phone at chest height and point approximately 20–30 degrees below horizontal so walls and floor are visible.
5. Pause briefly at each corner and opening.
6. Complete one continuous loop where physically safe.
7. Avoid rapid yaw, digital zoom, portrait/cinematic modes, mirrors and very dark corners.
8. Export the original clip; do not transcode.
9. Put it in `video/<room_or_property>.MOV`.

## LiDAR tier

Use a stock LiDAR logging/export application that exports depth frames, confidence, camera intrinsics and poses. Export the original files without recompression. Place them under a single capture folder with:

```text
camera_matrix.csv
odometry.csv
imu.csv
depth/*.png
confidence/*.png
```

## Property walkthrough

For multi-room captures, begin outside/at the main entrance, scan each room completely, pass through each connector only once where possible, and return through a previously seen area to create a loop closure. Keep the same walking speed and avoid occluding the phone with the hand.

## Handoff

Zip one capture folder without modifying filenames. Run:

```bash
python -m spatialscan run --tier <photos|video|lidar> --input <capture> --output runs/result.json --render runs/result.png
```
