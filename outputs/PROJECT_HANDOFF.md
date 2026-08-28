# KITTI Stereo Reconstruction — Start Here

The project is built and verified locally. Its implementation is in the workspace root; this handoff gives you the shortest route to a real KITTI result.

## 1. Add the KITTI training data

Download the KITTI Stereo 2015 (or 2012) **training** split from the official KITTI site and point the commands below at its `training` folder. The folder must contain `image_2`, `image_3`, a `disp_occ_0` or `disp_noc_0` directory, and preferably `calib/`.

## 2. Run a baseline on five pairs

```powershell
.\.venv\Scripts\python.exe run_pipeline.py --dataset <path-to-kitti-training> --max-pairs 5 --output results/baseline
```

Review `results/baseline/run_summary.json`, each pair's disparity visualization, error heatmap, and `point_cloud.ply`.

## 3. Tune, then evaluate cleanly

Use a fixed subset of 3–5 pairs for tuning:

```powershell
.\.venv\Scripts\python.exe run_pipeline.py --dataset <path-to-kitti-training> --ids 000000_10 000001_10 000002_10 --tune --output results/tuning
```

Choose the top row in `tuning_results.csv`, then run a **different** fixed 5–10 pair set with those parameters. Report only that final run's aggregated `bad3_pct`, `d1_pct`, and `rmse_px` from `run_summary.json`.

## Delivered capabilities

- OpenCV SGBM with exposed matching/noise parameters and optional WLS filtering
- Correct KITTI 16-bit disparity decoding and P2/P3 baseline derivation
- Bad-3, KITTI-style D1, RMSE, MAE, and per-pair error heatmaps
- Dense left-camera 3D reprojection and colorized PLY export
- Rectification scanline check, configuration search, reproducible JSON/CSV reports

## Verification completed

- Five unit tests: calibration parsing, metric aggregation, invalid-prediction handling, reprojection/PLY export, and SGBM parameter validation
- End-to-end run on a generated rectified KITTI-shaped fixture, including a WLS run and the complete tuning workflow

Use the exact results from your real KITTI hold-out set in your resume—not the generated smoke-test figures.
