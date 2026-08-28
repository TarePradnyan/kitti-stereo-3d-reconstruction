"""Run and optionally tune an evaluation-first KITTI stereo pipeline."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

from stereo_kitti.calibration import read_kitti_calibration
from stereo_kitti.disparity import SGBMConfig, estimate_disparity
from stereo_kitti.evaluation import aggregate_metrics, evaluate_disparity
from stereo_kitti.io import (
    discover_pair_ids,
    ground_truth_path,
    read_kitti_disparity,
    read_pair,
    save_disparity_visualization,
    save_error_visualization,
    save_rectification_check,
    write_json,
)
from stereo_kitti.reconstruction import reproject_to_points, write_ply


def calibration_path(dataset: Path, pair_id: str) -> Path | None:
    candidates = [
        dataset / "calib" / f"{pair_id}.txt",  # KITTI 2012-style naming
        dataset / "calib" / f"{pair_id.split('_')[0]}.txt",  # KITTI 2015-style naming
        dataset / "calib_cam_to_cam.txt",  # KITTI raw data layout
    ]
    return next((path for path in candidates if path.is_file()), None)


def process_pairs(args: argparse.Namespace, config: SGBMConfig, save_artifacts: bool) -> dict:
    dataset = Path(args.dataset)
    output = Path(args.output)
    ids = discover_pair_ids(dataset, args.ids, args.max_pairs)
    all_metrics = []
    pair_reports = []
    started = perf_counter()

    for index, pair_id in enumerate(ids):
        left, right = read_pair(dataset, pair_id)
        if index == 0 and save_artifacts:
            save_rectification_check(output / "rectification_check.png", left, right)
        disparity = estimate_disparity(left, right, config)
        gt_path = ground_truth_path(dataset, pair_id, args.ground_truth)
        report: dict = {"pair_id": pair_id}

        if save_artifacts:
            pair_dir = output / "pairs" / pair_id
            save_disparity_visualization(pair_dir / "disparity_color.png", disparity)
            calibration = read_kitti_calibration(calibration_path(dataset, pair_id))
            points, colors = reproject_to_points(disparity, left, calibration, args.max_depth, args.point_stride)
            write_ply(pair_dir / "point_cloud.ply", points, colors)
            report["point_count"] = len(points)
            report["calibration"] = asdict(calibration)

        if gt_path is not None:
            metrics, error = evaluate_disparity(disparity, read_kitti_disparity(gt_path))
            all_metrics.append(metrics)
            report["metrics"] = metrics.report()
            if save_artifacts:
                save_error_visualization(output / "pairs" / pair_id / "error_heatmap.png", error, read_kitti_disparity(gt_path))
        else:
            report["metrics"] = None
            report["ground_truth"] = "not found"
        pair_reports.append(report)

    aggregate = aggregate_metrics(all_metrics).report() if all_metrics else None
    summary = {
        "dataset": str(dataset),
        "pair_count": len(ids),
        "evaluated_pair_count": len(all_metrics),
        "config": asdict(config),
        "aggregate_metrics": aggregate,
        "elapsed_seconds": round(perf_counter() - started, 3),
        "pairs": pair_reports,
    }
    if save_artifacts:
        write_json(output / "run_summary.json", summary)
    return summary


def tune(args: argparse.Namespace) -> None:
    if args.ground_truth == "none":
        raise ValueError("--tune requires KITTI ground truth; use occ, noc, or auto")
    rows = []
    for num_disparities in (128, 160, 192):
        for block_size in (5, 7, 9):
            for uniqueness_ratio in (5, 10, 15):
                config = SGBMConfig(
                    num_disparities=num_disparities,
                    block_size=block_size,
                    uniqueness_ratio=uniqueness_ratio,
                    speckle_window_size=args.speckle_window_size,
                    speckle_range=args.speckle_range,
                    use_wls=args.use_wls,
                )
                summary = process_pairs(args, config, save_artifacts=False)
                metrics = summary["aggregate_metrics"]
                if metrics:
                    rows.append({**asdict(config), **metrics})
    rows.sort(key=lambda row: (row["d1_pct"], row["rmse_px"]))
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / "tuning_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["status"])
        writer.writeheader()
        writer.writerows(rows)
    write_json(output / "tuning_summary.json", {"tested_configs": len(rows), "best": rows[0] if rows else None})
    if not rows:
        raise RuntimeError("No ground truth maps were found for the selected pairs")
    best = rows[0]
    print(f"Best D1: {best['d1_pct']}% | Bad-3: {best['bad3_pct']}% | RMSE: {best['rmse_px']} px")
    print(f"Saved tuning table: {output / 'tuning_results.csv'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, help="KITTI training directory containing image_2 and image_3")
    parser.add_argument("--output", default="results/run", help="Directory for generated artifacts")
    parser.add_argument("--ids", nargs="*", help="Explicit pair IDs, e.g. 000000_10 000001_10")
    parser.add_argument("--max-pairs", type=int, default=None, help="Process only the first N selected pairs")
    parser.add_argument("--ground-truth", choices=("auto", "occ", "noc", "none"), default="auto")
    parser.add_argument("--num-disparities", type=int, default=192)
    parser.add_argument("--block-size", type=int, default=5)
    parser.add_argument("--uniqueness-ratio", type=int, default=10)
    parser.add_argument("--speckle-window-size", type=int, default=100)
    parser.add_argument("--speckle-range", type=int, default=2)
    parser.add_argument("--use-wls", action="store_true")
    parser.add_argument("--max-depth", type=float, default=80.0)
    parser.add_argument("--point-stride", type=int, default=2)
    parser.add_argument("--tune", action="store_true", help="Evaluate a compact 27-configuration SGBM grid")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.max_pairs is not None and args.max_pairs < 1:
        raise ValueError("--max-pairs must be >= 1")
    if args.tune:
        tune(args)
        return
    config = SGBMConfig(
        num_disparities=args.num_disparities,
        block_size=args.block_size,
        uniqueness_ratio=args.uniqueness_ratio,
        speckle_window_size=args.speckle_window_size,
        speckle_range=args.speckle_range,
        use_wls=args.use_wls,
    )
    summary = process_pairs(args, config, save_artifacts=True)
    if summary["aggregate_metrics"]:
        metrics = summary["aggregate_metrics"]
        print(f"D1: {metrics['d1_pct']}% | Bad-3: {metrics['bad3_pct']}% | RMSE: {metrics['rmse_px']} px")
    print(f"Saved run summary: {Path(args.output) / 'run_summary.json'}")


if __name__ == "__main__":
    main()
