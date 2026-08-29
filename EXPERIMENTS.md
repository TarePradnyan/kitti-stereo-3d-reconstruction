# Experimental Log

This log records the decisions, hypotheses, and measured results for the
KITTI Stereo 2015 SGBM baseline. It deliberately distinguishes exploratory
runs from final held-out evaluation.

## Reproducibility snapshot

- **Dataset:** KITTI Stereo 2015 / Scene Flow training split.
- **Images evaluated:** `image_2` / `image_3` rectified pairs with IDs ending
  in `_10`.
- **Ground truth:** `disp_occ_0`, decoded from KITTI's 16-bit PNG format by
  dividing by 256.
- **Method:** OpenCV `StereoSGBM` in `STEREO_SGBM_MODE_SGBM_3WAY` mode.
- **OpenCV environment:** 4.11.0 (local development environment).
- **Default configuration:** `numDisparities=192`, `blockSize=5`,
  `uniquenessRatio=10`, `speckleWindowSize=100`, `speckleRange=2`.

## Metric definitions

All metrics use valid (`> 0`) KITTI ground-truth pixels. An invalid SGBM
prediction is counted as zero disparity rather than silently excluded.

- **Bad-3:** fraction of pixels with absolute disparity error above 3 px.
- **D1:** fraction with error above 3 px **and** above 5% of the ground-truth
  disparity. This follows the KITTI-style outlier definition.
- **RMSE:** square root of mean squared disparity error, in pixels.

Lower is better for all three metrics.

## Exploratory sanity run

| Date | Pair | Configuration | D1 | Bad-3 | RMSE (px) | Purpose |
|---|---|---|---:|---:|---:|---|
| 2026-08-28 | `000000_10` | default | 22.1107% | 22.1130% | 15.1552 | Verify end-to-end loading, disparity, evaluation, visualization, and PLY export. |

Qualitative inspection found aligned horizontal scanlines, lower disparity at
the distant road/horizon, and high error concentrated at vehicle boundaries,
reflections, thin structures, and low-texture regions. These are expected
failure modes for local stereo matching.

## Baseline protocol correction

The first `--max-pairs 5` exploratory command selected both `_10` and `_11`
frames. Because this project evaluates `disp_occ_0`, only `_10` frames have
the selected ground truth; the run processed five images but evaluated three.
The experiment was corrected by specifying five explicit `_10` IDs. This
avoids mixing unevaluated images into a reported five-pair baseline.

## Measured five-pair baseline

| Evaluation IDs | Configuration | D1 | Bad-3 | RMSE (px) | Status |
|---|---|---:|---:|---:|---|
| `000000_10`–`000004_10` | default | 27.5163% | 27.5952% | 20.2486 | Baseline / exploratory. Do not present as held-out final performance. |

The higher error relative to the one-pair sanity run shows why a single image
is not representative: the five scenes contain a broader mix of occlusion,
lighting, texture, and object-boundary difficulty.

## Parameter-tuning plan

### Split

- **Validation set for parameter selection:** `000000_10`, `000001_10`,
  `000002_10`.
- **Held-out final set:** `000005_10` through `000009_10`.

The final set must not influence parameter selection. This is a small,
reproducible held-out protocol within the KITTI training split; it is not an
official KITTI test-server submission.

### Hypotheses

| Variable | Values | Hypothesis |
|---|---|---|
| `numDisparities` | 128, 160, 192 | Too small can truncate high-disparity foreground matches; too large increases search ambiguity and the invalid left border. |
| `blockSize` | 5, 7, 9 | Larger windows reduce noise in textured regions but can blur object boundaries and thin structures. |
| `uniquenessRatio` | 5, 10, 15 | A higher threshold rejects more ambiguous matches, which may improve reliability but reduce usable disparity density. |

For all candidates, `P1` and `P2` remain coupled to `blockSize` using the
OpenCV-recommended formulas `8 * channels * blockSize^2` and
`32 * channels * blockSize^2`, respectively.

## Results to complete

The 27-configuration validation sweep selected the following setting by lowest
D1. The result is **validation-only** and must not be presented as the final
score because the configuration was selected using these same images.

| Stage | IDs | Parameters | D1 | Bad-3 | RMSE (px) |
|---|---|---|---:|---:|---:|
| Best validation configuration | `000000_10`–`000002_10` | `numDisparities=128`, `blockSize=9`, `uniquenessRatio=5` | 17.9321% | 17.9385% | 13.2916 |
| Held-out final evaluation | `000005_10`–`000009_10` | `numDisparities=128`, `blockSize=9`, `uniquenessRatio=5` | 16.2764% | 16.6643% | 16.3709 |

## Final held-out analysis

The locked configuration was evaluated once on five image IDs that were not
used for parameter selection. All five had valid `disp_occ_0` ground truth,
for a total of 511,434 evaluated pixels.

| Pair ID | D1 | Bad-3 | RMSE (px) |
|---|---:|---:|---:|
| `000005_10` | 23.1024% | 23.4576% | 22.7122 |
| `000006_10` | 28.5944% | 30.0765% | 24.0277 |
| `000007_10` | 12.5089% | 12.5117% | 11.4864 |
| `000008_10` | 6.4673% | 6.4673% | 5.2319 |
| `000009_10` | 10.0816% | 10.0826% | 8.9249 |
| **Aggregate (pixel-weighted)** | **16.2764%** | **16.6643%** | **16.3709** |

The spread across scenes is substantial (D1 from 6.47% to 28.59%), which
reinforces that a single stereo image is not representative. The aggregate is
computed from raw error counts across all valid pixels, rather than averaging
the five percentages. These results are a small held-out evaluation within the
KITTI training split and are not an official KITTI leaderboard submission.

### Qualitative error analysis

The error heatmaps were inspected for the hardest and easiest held-out scenes.
In these heatmaps, yellow/white denotes high absolute disparity error; dark
purple denotes lower error; black can also denote pixels for which KITTI does
not provide valid ground truth.

| Pair | Observation | Interpretation |
|---|---|---|
| `000006_10` (D1 28.59%) | Broad bright regions cover the close foreground vehicle, with additional bright contours around parked vehicles and scene boundaries. | Large foreground disparity, reflective/low-texture vehicle surfaces, occlusion, and sharp depth discontinuities make local correspondence unreliable. |
| `000008_10` (D1 6.47%) | Most valid scene regions remain dark, while brighter errors are largely confined to vehicle outlines and highlights. | SGBM matches the dominant surfaces reliably when texture and correspondence are clearer; boundary/reflectance errors remain. |

This comparison supports the quantitative result: the method's dominant
failure mode is not uniform error across an image, but difficult local
correspondence at reflective regions, occlusions, and depth discontinuities.

## 3D reconstruction verification

Calibration for `000005_10` was added from KITTI's `calib_cam_to_cam` archive.
The pipeline read the pair's projection matrices from `calib/000005.txt` and
derived `fx=721.5377 px` and a `0.532725 m` stereo baseline before exporting
the colorized PLY. Visual inspection of the PLY shows a coherent road plane and
building facade, with sparse/noisy points around nearby vehicles and occlusion
boundaries. This is consistent with the corresponding disparity limitations.

## References

- [KITTI Stereo 2015 benchmark and metric definition](https://www.cvlibs.net/datasets/kitti/eval_scene_flow.php?benchmark=stereo)
- [OpenCV StereoSGBM API reference](https://docs.opencv.org/4.12.0/d2/d85/classcv_1_1StereoSGBM.html)
