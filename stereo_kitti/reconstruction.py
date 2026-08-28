"""Back-project rectified disparity to a compact color point cloud."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .calibration import StereoCalibration


def reproject_to_points(
    disparity: np.ndarray,
    left_bgr: np.ndarray,
    calibration: StereoCalibration,
    max_depth_m: float = 80.0,
    stride: int = 2,
) -> tuple[np.ndarray, np.ndarray]:
    """Return Nx3 XYZ points and Nx3 RGB colors in the left-camera frame."""
    if disparity.shape != left_bgr.shape[:2]:
        raise ValueError("disparity and left image must have the same height/width")
    if stride < 1:
        raise ValueError("stride must be >= 1")
    rows, cols = np.indices(disparity.shape)
    valid = np.isfinite(disparity) & (disparity > 0)
    depth = np.zeros_like(disparity, dtype=np.float32)
    depth[valid] = calibration.fx * calibration.baseline_m / disparity[valid]
    valid &= (depth > 0) & (depth <= max_depth_m)
    valid &= (rows % stride == 0) & (cols % stride == 0)
    z = depth[valid]
    x = (cols[valid] - calibration.cx) * z / calibration.fx
    y = (rows[valid] - calibration.cy) * z / calibration.fy
    points = np.column_stack((x, y, z)).astype(np.float32)
    colors = left_bgr[valid][:, ::-1].astype(np.uint8)
    return points, colors


def write_ply(path: Path, points: np.ndarray, colors_rgb: np.ndarray) -> None:
    """Write an ASCII XYZRGB PLY that MeshLab and Open3D can open."""
    if points.shape != (len(points), 3) or colors_rgb.shape != (len(points), 3):
        raise ValueError("points and colors must each have shape (N, 3)")
    path.parent.mkdir(parents=True, exist_ok=True)
    header = "\n".join(
        [
            "ply",
            "format ascii 1.0",
            f"element vertex {len(points)}",
            "property float x",
            "property float y",
            "property float z",
            "property uchar red",
            "property uchar green",
            "property uchar blue",
            "end_header",
        ]
    )
    with path.open("w", encoding="ascii", newline="\n") as file:
        file.write(header + "\n")
        for point, color in zip(points, colors_rgb):
            file.write(
                f"{point[0]:.5f} {point[1]:.5f} {point[2]:.5f} "
                f"{int(color[0])} {int(color[1])} {int(color[2])}\n"
            )
