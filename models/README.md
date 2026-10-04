# Model artifacts

This directory is reserved for optional downloaded or locally trained model
weights. No model file is included because the current implementation uses
deterministic geometry and OpenCV heuristics; adding an arbitrary binary here
would not improve the pipeline.

Model weights are ignored by `.gitignore`. Keep a small manifest here when a
future model is introduced, including its filename, source, version, checksum,
and the code path that loads it.