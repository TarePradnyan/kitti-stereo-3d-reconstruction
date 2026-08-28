# KITTI Stereo 3D Reconstruction

A compact, evaluation-first stereo reconstruction project built around the KITTI Stereo 2012/2015 training data. It estimates dense disparity with Semi-Global Block Matching (SGBM), turns disparity into a colorized 3D point cloud, and reports disparity error against KITTI ground truth.

The images in KITTI's stereo benchmark are already rectified. This keeps the project focused on the parts that are both technically meaningful and achievable in a weekend: matching, parameter tuning, reprojection, visualization, and benchmarking.

## What it produces

For each KITTI pair the pipeline saves:

- predicted disparity and color visualization;
- absolute-error heatmap against `disp_occ_0` or `disp_noc_0`;
- a colorized `.ply` point cloud;
- pair-level metrics in `metrics.json` and an aggregate benchmark summary;
- optional SGBM grid-search results in `tuning_results.csv`.

## Project layout

```text
stereo_kitti/
  calibration.py       # KITTI projection-matrix parser
  disparity.py         # SGBM + optional WLS refinement
  evaluation.py        # Bad-3, KITTI-style D1, RMSE
  io.py                # image/ground-truth loading and result writers
  reconstruction.py    # dense reprojection and PLY export
run_pipeline.py        # command-line runner
tests/                 # lightweight unit tests (no KITTI download required)
```

## Quick start

Create a virtual environment, activate it, and install the two dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Download the **training** split of [KITTI Stereo 2015](https://www.cvlibs.net/datasets/kitti/eval_scene_flow.php?benchmark=stereo) or Stereo 2012, accept its terms, and arrange the relevant directories like this:

```text
data/kitti/training/
  image_2/000000_10.png
  image_3/000000_10.png
  disp_occ_0/000000_10.png
  calib/000000.txt                 # Stereo 2015
```

`disp_noc_0/` can be used instead of `disp_occ_0/`; `--ground-truth auto` prefers the occluded map when both exist. The calibration reader handles the per-frame `calib/*.txt` layout used by KITTI 2015. If a calibration file is unavailable, the runner uses the documented KITTI defaults (`f=721.5377`, `B=0.54 m`) and records that choice.

Run five pairs:

```powershell
python run_pipeline.py --dataset data/kitti/training --max-pairs 5 --output results/baseline
```

Run a focused tuning sweep first, then inspect `results/tuning/tuning_results.csv` to select settings:

```powershell
python run_pipeline.py --dataset data/kitti/training --ids 000000_10 000001_10 000002_10 --tune --output results/tuning
```

The selected SGBM setting can then be used in a final run, for example:

```powershell
python run_pipeline.py --dataset data/kitti/training --max-pairs 10 --num-disparities 192 --block-size 5 --uniqueness-ratio 10 --output results/final
```

To request WLS refinement (available through `opencv-contrib-python`):

```powershell
python run_pipeline.py --dataset data/kitti/training --max-pairs 5 --use-wls --output results/wls
```

## Metrics

Only valid KITTI ground-truth pixels (`disparity > 0`) are evaluated.

- **Bad-3**: percentage with absolute disparity error greater than 3 px.
- **D1 / Bad-3-or-5%**: percentage where the error is greater than 3 px **and** greater than 5% of ground truth. This is closer to KITTI's published disparity criterion.
- **RMSE**: root mean squared disparity error in pixels.

The aggregate values are computed over all valid ground-truth pixels, not by simply averaging pair percentages. SGBM's left invalid margin and zero/negative predictions are treated as zero disparity, so they correctly contribute error rather than disappearing from the benchmark.

## Sanity checks and tests

Verify that dependencies and pure-Python logic are wired correctly:

```powershell
python -m unittest discover -s tests -v
```

Before reporting results, use a small fixed set of five to ten training pairs, keep the tuning/final pair split explicit, and retain the generated `run_summary.json`. The visualization `rectification_check.png` overlays horizontal scanlines on every first pair; scene structure should line up along each line.

## Resume wording (after you have final numbers)

> Built an evaluation-driven stereo 3D reconstruction pipeline on KITTI using OpenCV SGBM; reprojected calibrated disparity to colorized PLY point clouds and benchmarked performance with Bad-3, KITTI-style D1, RMSE, and error heatmaps across a held-out image set.

Replace “across a held-out image set” with the exact count and add your measured D1/Bad-3 only after completing the final run.
