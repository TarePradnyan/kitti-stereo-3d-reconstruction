"""KITTI-style disparity evaluation with aggregate-safe accounting."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class DisparityMetrics:
    valid_pixels: int
    bad3_pixels: int
    d1_pixels: int
    squared_error_sum: float
    absolute_error_sum: float

    @property
    def bad3_pct(self) -> float:
        return 100.0 * self.bad3_pixels / self.valid_pixels if self.valid_pixels else float("nan")

    @property
    def d1_pct(self) -> float:
        return 100.0 * self.d1_pixels / self.valid_pixels if self.valid_pixels else float("nan")

    @property
    def rmse_px(self) -> float:
        return float(np.sqrt(self.squared_error_sum / self.valid_pixels)) if self.valid_pixels else float("nan")

    @property
    def mae_px(self) -> float:
        return self.absolute_error_sum / self.valid_pixels if self.valid_pixels else float("nan")

    def report(self) -> dict[str, float | int]:
        result = asdict(self)
        result.update(
            bad3_pct=round(self.bad3_pct, 4),
            d1_pct=round(self.d1_pct, 4),
            rmse_px=round(self.rmse_px, 4),
            mae_px=round(self.mae_px, 4),
        )
        return result


def evaluate_disparity(predicted: np.ndarray, ground_truth: np.ndarray) -> tuple[DisparityMetrics, np.ndarray]:
    """Evaluate prediction and return metrics plus absolute-error map.

    KITTI PNG ground truth uses zero for invalid pixels. A non-positive or
    non-finite SGBM result is treated as zero disparity, so an invalid estimate
    is counted as an error at every valid ground-truth pixel.
    """
    if predicted.shape != ground_truth.shape:
        raise ValueError("predicted and ground-truth disparity maps must match")
    predicted = predicted.astype(np.float32, copy=False)
    ground_truth = ground_truth.astype(np.float32, copy=False)
    valid = ground_truth > 0
    safe_prediction = np.where(np.isfinite(predicted) & (predicted > 0), predicted, 0.0)
    error = np.abs(safe_prediction - ground_truth)
    errors = error[valid]
    gt = ground_truth[valid]
    metrics = DisparityMetrics(
        valid_pixels=int(errors.size),
        bad3_pixels=int(np.count_nonzero(errors > 3.0)),
        d1_pixels=int(np.count_nonzero((errors > 3.0) & (errors / gt > 0.05))),
        squared_error_sum=float(np.sum(errors**2, dtype=np.float64)),
        absolute_error_sum=float(np.sum(errors, dtype=np.float64)),
    )
    return metrics, error


def aggregate_metrics(metrics: list[DisparityMetrics]) -> DisparityMetrics:
    """Aggregate raw counts/sums, weighting every valid pixel equally."""
    return DisparityMetrics(
        valid_pixels=sum(item.valid_pixels for item in metrics),
        bad3_pixels=sum(item.bad3_pixels for item in metrics),
        d1_pixels=sum(item.d1_pixels for item in metrics),
        squared_error_sum=sum(item.squared_error_sum for item in metrics),
        absolute_error_sum=sum(item.absolute_error_sum for item in metrics),
    )
