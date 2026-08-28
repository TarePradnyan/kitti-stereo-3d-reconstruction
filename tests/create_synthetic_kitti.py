"""Create a small rectified KITTI-shaped fixture for end-to-end smoke tests."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = args.output
    for folder in ("image_2", "image_3", "disp_occ_0", "calib"):
        (root / folder).mkdir(parents=True, exist_ok=True)

    height, width, disparity_px = 160, 320, 24
    rng = np.random.default_rng(7)
    left = rng.integers(0, 256, (height, width, 3), dtype=np.uint8)
    # Add stable structure, then make a right image displaced left by 24 px.
    for column in range(0, width, 32):
        cv2.line(left, (column, 0), (column, height - 1), (255, 255, 255), 1)
    right = np.zeros_like(left)
    right[:, : width - disparity_px] = left[:, disparity_px:]
    pair_id = "000000_10"
    cv2.imwrite(str(root / "image_2" / f"{pair_id}.png"), left)
    cv2.imwrite(str(root / "image_3" / f"{pair_id}.png"), right)
    ground_truth = np.zeros((height, width), dtype=np.uint16)
    ground_truth[:, disparity_px:] = disparity_px * 256
    cv2.imwrite(str(root / "disp_occ_0" / f"{pair_id}.png"), ground_truth)
    (root / "calib" / "000000.txt").write_text(
        "P2: 700 0 160 0 0 700 80 0 0 0 1 0\n"
        "P3: 700 0 160 -378 0 700 80 0 0 0 1 0\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
