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

After running the validation sweep, record the best row from
`results/tuning_validation/tuning_results.csv` here. Then run the selected
parameters once on the held-out five-scene set and record those metrics below.

| Stage | IDs | Parameters | D1 | Bad-3 | RMSE (px) |
|---|---|---|---:|---:|---:|
| Best validation configuration | `000000_10`–`000002_10` | Pending | Pending | Pending | Pending |
| Held-out final evaluation | `000005_10`–`000009_10` | Pending | Pending | Pending | Pending |

## References

- [KITTI Stereo 2015 benchmark and metric definition](https://www.cvlibs.net/datasets/kitti/eval_scene_flow.php?benchmark=stereo)
- [OpenCV StereoSGBM API reference](https://docs.opencv.org/4.12.0/d2/d85/classcv_1_1StereoSGBM.html)
