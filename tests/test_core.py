from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from stereo_kitti.calibration import read_kitti_calibration
from stereo_kitti.disparity import SGBMConfig
from stereo_kitti.evaluation import aggregate_metrics, evaluate_disparity
from stereo_kitti.reconstruction import reproject_to_points, write_ply


class CorePipelineTests(unittest.TestCase):
    def test_kitti_error_metrics(self) -> None:
        ground_truth = np.array([[10.0, 10.0, 0.0], [20.0, 20.0, 20.0]], dtype=np.float32)
        predicted = np.array([[10.0, 14.0, 12.0], [22.0, 25.0, -1.0]], dtype=np.float32)
        metrics, error = evaluate_disparity(predicted, ground_truth)
        self.assertEqual(metrics.valid_pixels, 5)
        self.assertEqual(metrics.bad3_pixels, 3)
        self.assertEqual(metrics.d1_pixels, 3)
        self.assertAlmostEqual(metrics.rmse_px, np.sqrt((0 + 16 + 4 + 25 + 400) / 5))
        self.assertEqual(error.shape, ground_truth.shape)

    def test_aggregate_uses_pixel_weights(self) -> None:
        one, _ = evaluate_disparity(np.array([[0.0, 14.0]]), np.array([[0.0, 10.0]]))
        two, _ = evaluate_disparity(np.array([[10.0] * 10]), np.array([[10.0] * 10]))
        aggregate = aggregate_metrics([one, two])
        self.assertAlmostEqual(aggregate.bad3_pct, 100 / 11)

    def test_projection_baseline_parser(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "calib.txt"
            path.write_text(
                "P2: 700 0 600 0 0 700 180 0 0 0 1 0\n"
                "P3: 700 0 600 -378 0 700 180 0 0 0 1 0\n",
                encoding="utf-8",
            )
            calibration = read_kitti_calibration(path)
        self.assertAlmostEqual(calibration.baseline_m, 0.54)
        self.assertEqual(calibration.fx, 700)

    def test_reprojection_and_ply(self) -> None:
        calibration = read_kitti_calibration(None)
        disparity = np.full((2, 2), 10.0, dtype=np.float32)
        image = np.zeros((2, 2, 3), dtype=np.uint8)
        image[:, :, 2] = 255  # BGR red
        points, colors = reproject_to_points(disparity, image, calibration, stride=1)
        self.assertEqual(points.shape, (4, 3))
        self.assertTrue(np.all(colors == [255, 0, 0]))
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "cloud.ply"
            write_ply(target, points, colors)
            self.assertIn("element vertex 4", target.read_text(encoding="ascii"))

    def test_sgbm_validation(self) -> None:
        with self.assertRaises(ValueError):
            SGBMConfig(num_disparities=100)
        with self.assertRaises(ValueError):
            SGBMConfig(block_size=4)


if __name__ == "__main__":
    unittest.main()
