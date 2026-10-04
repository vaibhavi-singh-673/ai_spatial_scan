# Technical report — six-page submission structure

## 1. Architecture
Describe the shared representation and the three tier adapters.

## 2. Tier design and device matrix
State hardware, capture protocol, calibration source and expected interval widths.

## 3. Drift handling
Document odometry preprocessing, loop closure, pose graph/plane anchors and the ablation with correction disabled.

## 4. Error budget
Separate sensor noise, pose error, segmentation/plane fit, scale calibration and rendering discretization.

## 5. Calibration analysis
Report coverage and empirical error by tier. Do not report a nominal interval without coverage testing.

## 6. Fix loop and known failure modes
Include the exact failing gate, evidence, prediction, shipped fix and after result. Cover mirrors, glass, wet-look surfaces, low light, occlusion and clutter.
