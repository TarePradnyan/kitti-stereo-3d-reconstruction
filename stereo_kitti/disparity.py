"""OpenCV Semi-Global Block Matching with optional WLS refinement."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SGBMConfig:
    num_disparities: int = 192
    block_size: int = 5
    uniqueness_ratio: int = 10
    speckle_window_size: int = 100
    speckle_range: int = 2
    disp12_max_diff: int = 1
    use_wls: bool = False
    wls_lambda: float = 8000.0
    wls_sigma_color: float = 1.5

    def __post_init__(self) -> None:
        if self.num_disparities <= 0 or self.num_disparities % 16:
            raise ValueError("num_disparities must be a positive multiple of 16")
        if self.block_size < 3 or self.block_size % 2 == 0:
            raise ValueError("block_size must be an odd integer >= 3")


def _opencv():
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError(
            "OpenCV is required. Install dependencies with: pip install -r requirements.txt"
        ) from exc
    return cv2


def _matcher(cv2, config: SGBMConfig):
    channels = 1
    return cv2.StereoSGBM_create(
        minDisparity=0,
        numDisparities=config.num_disparities,
        blockSize=config.block_size,
        P1=8 * channels * config.block_size**2,
        P2=32 * channels * config.block_size**2,
        disp12MaxDiff=config.disp12_max_diff,
        uniquenessRatio=config.uniqueness_ratio,
        speckleWindowSize=config.speckle_window_size,
        speckleRange=config.speckle_range,
        preFilterCap=63,
        mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY,
    )


def estimate_disparity(left_bgr: np.ndarray, right_bgr: np.ndarray, config: SGBMConfig) -> np.ndarray:
    """Return a left-view disparity map in pixel units as float32."""
    cv2 = _opencv()
    if left_bgr.shape[:2] != right_bgr.shape[:2]:
        raise ValueError("left and right image sizes must match")
    left_gray = cv2.cvtColor(left_bgr, cv2.COLOR_BGR2GRAY)
    right_gray = cv2.cvtColor(right_bgr, cv2.COLOR_BGR2GRAY)
    left_matcher = _matcher(cv2, config)
    left_raw = left_matcher.compute(left_gray, right_gray)

    if config.use_wls:
        if not hasattr(cv2, "ximgproc"):
            raise RuntimeError("WLS needs opencv-contrib-python (cv2.ximgproc is unavailable)")
        right_matcher = cv2.ximgproc.createRightMatcher(left_matcher)
        right_raw = right_matcher.compute(right_gray, left_gray)
        wls = cv2.ximgproc.createDisparityWLSFilter(left_matcher)
        wls.setLambda(config.wls_lambda)
        wls.setSigmaColor(config.wls_sigma_color)
        disparity = wls.filter(left_raw, left_bgr, disparity_map_right=right_raw)
    else:
        disparity = left_raw
    return disparity.astype(np.float32) / 16.0
