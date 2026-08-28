"""Dataset discovery, KITTI PNG decoding, and OpenCV visual outputs."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def _opencv():
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV is required. Install dependencies with: pip install -r requirements.txt") from exc
    return cv2


def discover_pair_ids(dataset: Path, requested_ids: list[str] | None, max_pairs: int | None) -> list[str]:
    left_dir = dataset / "image_2"
    right_dir = dataset / "image_3"
    if not left_dir.is_dir() or not right_dir.is_dir():
        raise FileNotFoundError("Dataset must contain image_2/ and image_3/ directories")
    available = sorted(path.stem for path in left_dir.glob("*.png") if (right_dir / path.name).is_file())
    selected = requested_ids if requested_ids else available
    missing = sorted(set(selected) - set(available))
    if missing:
        raise FileNotFoundError(f"No complete left/right pair for: {', '.join(missing)}")
    if not selected:
        raise FileNotFoundError("No .png stereo pairs were found")
    return selected[:max_pairs] if max_pairs else selected


def read_pair(dataset: Path, pair_id: str) -> tuple[np.ndarray, np.ndarray]:
    cv2 = _opencv()
    left = cv2.imread(str(dataset / "image_2" / f"{pair_id}.png"), cv2.IMREAD_COLOR)
    right = cv2.imread(str(dataset / "image_3" / f"{pair_id}.png"), cv2.IMREAD_COLOR)
    if left is None or right is None:
        raise FileNotFoundError(f"Could not load stereo pair {pair_id}")
    return left, right


def ground_truth_path(dataset: Path, pair_id: str, preference: str) -> Path | None:
    folders = [f"disp_{preference}_0"] if preference != "auto" else ["disp_occ_0", "disp_noc_0"]
    for folder in folders:
        path = dataset / folder / f"{pair_id}.png"
        if path.is_file():
            return path
    return None


def read_kitti_disparity(path: Path) -> np.ndarray:
    """KITTI disparity PNGs store pixel disparity as unsigned-16 / 256."""
    cv2 = _opencv()
    raw = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if raw is None:
        raise FileNotFoundError(f"Could not load ground truth: {path}")
    if raw.dtype != np.uint16:
        raise ValueError(f"Expected 16-bit KITTI disparity PNG, got {raw.dtype} at {path}")
    return raw.astype(np.float32) / 256.0


def save_disparity_visualization(path: Path, disparity: np.ndarray) -> None:
    cv2 = _opencv()
    valid = disparity[np.isfinite(disparity) & (disparity > 0)]
    display = np.zeros_like(disparity, dtype=np.uint8)
    if valid.size:
        upper = float(np.percentile(valid, 99))
        display = np.clip(disparity * 255.0 / max(upper, 1.0), 0, 255).astype(np.uint8)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), cv2.applyColorMap(display, cv2.COLORMAP_TURBO))


def save_error_visualization(path: Path, error: np.ndarray, ground_truth: np.ndarray, cap_px: float = 12.0) -> None:
    cv2 = _opencv()
    normalized = np.clip(error * 255.0 / cap_px, 0, 255).astype(np.uint8)
    color = cv2.applyColorMap(normalized, cv2.COLORMAP_INFERNO)
    color[ground_truth <= 0] = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), color)


def save_rectification_check(path: Path, left_bgr: np.ndarray, right_bgr: np.ndarray, spacing: int = 40) -> None:
    cv2 = _opencv()
    composite = np.concatenate((left_bgr, right_bgr), axis=1)
    for row in range(0, composite.shape[0], spacing):
        cv2.line(composite, (0, row), (composite.shape[1] - 1, row), (0, 255, 0), 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), composite)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
