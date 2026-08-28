"""Read KITTI projection matrices and derive stereo intrinsics/baseline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class StereoCalibration:
    """Minimal rectified-stereo calibration needed for depth reconstruction."""

    fx: float
    fy: float
    cx: float
    cy: float
    baseline_m: float
    source: str = "KITTI fallback constants"

    @classmethod
    def fallback(cls) -> "StereoCalibration":
        """Documented KITTI-style fallback for rectified benchmark imagery."""
        return cls(721.5377, 721.5377, 609.5593, 172.8540, 0.54)


def _parse_projection_file(path: Path) -> dict[str, np.ndarray]:
    matrices: dict[str, np.ndarray] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in raw_line:
            continue
        key, values = raw_line.split(":", 1)
        parts = values.split()
        if len(parts) == 12:
            try:
                matrices[key.strip()] = np.asarray(parts, dtype=np.float64).reshape(3, 4)
            except ValueError:
                continue
    return matrices


def read_kitti_calibration(path: Path | None) -> StereoCalibration:
    """Derive rectified intrinsics and baseline from KITTI P2/P3 projections.

    KITTI calibration encodes a camera center as -P[0,3] / P[0,0].
    """
    if path is None or not path.is_file():
        return StereoCalibration.fallback()

    matrices = _parse_projection_file(path)
    left = matrices.get("P2", matrices.get("P_rect_02"))
    right = matrices.get("P3", matrices.get("P_rect_03"))
    if left is None or right is None or left[0, 0] == 0 or right[0, 0] == 0:
        return StereoCalibration.fallback()

    left_center_x = -left[0, 3] / left[0, 0]
    right_center_x = -right[0, 3] / right[0, 0]
    baseline = abs(right_center_x - left_center_x)
    if baseline <= 0:
        return StereoCalibration.fallback()
    return StereoCalibration(
        fx=float(left[0, 0]),
        fy=float(left[1, 1]),
        cx=float(left[0, 2]),
        cy=float(left[1, 2]),
        baseline_m=float(baseline),
        source=str(path),
    )
