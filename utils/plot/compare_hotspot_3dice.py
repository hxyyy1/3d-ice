#!/usr/bin/env python3
"""Compare aligned HotSpot and 3D-ICE grid temperature fields."""

from __future__ import annotations

import argparse
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Iterable

if "MPLCONFIGDIR" not in os.environ:
    default_mpl_config = Path.home() / ".config" / "matplotlib"
    writable_target = default_mpl_config if default_mpl_config.exists() else default_mpl_config.parent
    if not os.access(writable_target, os.W_OK):
        fallback_mpl_config = Path(tempfile.gettempdir()) / f"3dice-matplotlib-{os.getuid()}"
        fallback_mpl_config.mkdir(parents=True, exist_ok=True)
        os.environ["MPLCONFIGDIR"] = str(fallback_mpl_config)

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize, TwoSlopeNorm

from plot_temperature_map import (
    draw_floorplan,
    floorplan_extent,
    maximum_location,
    parse_floorplan,
    parse_temperature_maps,
    parse_times,
)


mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 7,
        "axes.linewidth": 0.8,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
    }
)


def parse_hotspot_grid_trace(
    path: Path, layer_index: int, rows: int, columns: int, flip_vertical: bool
) -> tuple[np.ndarray, np.ndarray]:
    values_by_time: dict[float, list[float]] = {}
    current_time: float | None = None
    current_layer: int | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("t ="):
            current_time = float(line.split("=", 1)[1])
            values_by_time.setdefault(current_time, [])
            continue
        if line.startswith("Layer "):
            current_layer = int(line.split()[1].rstrip(":"))
            continue
        if current_time is not None and current_layer == layer_index:
            parts = line.split()
            if len(parts) != 2:
                raise ValueError(f"invalid HotSpot grid row: {raw_line!r}")
            values_by_time[current_time].append(float(parts[1]))

    times = np.asarray(sorted(values_by_time))
    if len(times) == 0:
        raise ValueError(f"no HotSpot layer {layer_index} frames found in {path}")

    frames = []
    expected_cells = rows * columns
    for time in times:
        values = values_by_time[float(time)]
        if len(values) != expected_cells:
            raise ValueError(
                f"HotSpot t={time:g}, layer {layer_index} contains {len(values)} cells; "
                f"expected {expected_cells}"
            )
        frame = np.asarray(values, dtype=float).reshape(rows, columns)
        if flip_vertical:
            frame = np.flipud(frame)
        frames.append(frame)

    data = np.stack(frames)
    if not np.isfinite(data).all():
        raise ValueError("HotSpot grid trace contains non-finite values")
    return times, data


def parse_hotspot_grid_steady(
    path: Path, rows: int, columns: int, flip_vertical: bool
) -> np.ndarray:
    values: list[float] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"invalid HotSpot steady-grid row: {raw_line!r}")
        values.append(float(parts[1]))
    if len(values) != rows * columns:
        raise ValueError(
            f"HotSpot steady grid contains {len(values)} cells; expected {rows * columns}"
        )
    frame = np.asarray(values, dtype=float).reshape(rows, columns)
    if flip_vertical:
        frame = np.flipud(frame)
    if not np.isfinite(frame).all():
        raise ValueError("HotSpot steady grid contains non-finite values")
    return frame


def select_time_index(times: np.ndarray, requested_time: float, source: str) -> int:
    matches = np.flatnonzero(np.isclose(times, requested_time, rtol=1.0e-9, atol=1.0e-12))
    if len(matches) != 1:
        raise ValueError(f"time {requested_time:g} s is not uniquely available in {source}")
    return int(matches[0])


def comparison_metrics(hotspot: np.ndarray, three_dice: np.ndarray) -> dict[str, float | int | str]:
    if hotspot.shape != three_dice.shape:
        raise ValueError(f"grid shapes differ: HotSpot {hotspot.shape}, 3D-ICE {three_dice.shape}")
    difference = three_dice - hotspot
    correlation = float(np.corrcoef(hotspot.ravel(), three_dice.ravel())[0, 1])
    hotspot_range = float(np.ptp(hotspot))
    rmse = float(np.sqrt(np.mean(np.square(difference))))
    return {
        "rows": int(hotspot.shape[0]),
        "columns": int(hotspot.shape[1]),
        "cells_compared": int(hotspot.size),
        "orientation_transform": "HotSpot vertical flip (row 0: top -> physical bottom-origin)",
        "hotspot_min_K": float(np.min(hotspot)),
        "hotspot_max_K": float(np.max(hotspot)),
        "three_dice_min_K": float(np.min(three_dice)),
        "three_dice_max_K": float(np.max(three_dice)),
        "mean_bias_K": float(np.mean(difference)),
        "mae_K": float(np.mean(np.abs(difference))),
        "rmse_K": rmse,
        "nrmse_hotspot_range_percent": 100.0 * rmse / hotspot_range
        if hotspot_range > 0.0
        else 0.0,
        "max_abs_error_K": float(np.max(np.abs(difference))),
        "pearson_r": correlation,
    }


def add_cell_grid(ax: plt.Axes, rows: int, columns: int, width_mm: float, height_mm: float) -> None:
    ax.set_xticks(np.linspace(0.0, width_mm, columns + 1), minor=True)
    ax.set_yticks(np.linspace(0.0, height_mm, rows + 1), minor=True)
    ax.grid(which="minor", color="black", linewidth=0.12, alpha=0.08, zorder=2)
    ax.tick_params(which="minor", bottom=False, left=False)


def draw_temperature_panel(
    ax: plt.Axes,
    frame: np.ndarray,
    title: str,
    blocks,
    width_um: float,
    height_um: float,
    norm: Normalize,
) -> mpl.image.AxesImage:
    width_mm = width_um / 1000.0
    height_mm = height_um / 1000.0
    image = ax.imshow(
        frame,
        origin="lower",
        extent=(0.0, width_mm, 0.0, height_mm),
        interpolation="nearest",
        cmap="hot_r",
        norm=norm,
        aspect="equal",
        rasterized=True,
    )
    add_cell_grid(ax, frame.shape[0], frame.shape[1], width_mm, height_mm)
    draw_floorplan(ax, blocks, width_um, height_um, "auto", font_size=5.0)
    max_x, max_y, max_temp = maximum_location(frame, width_mm, height_mm)
    ax.plot(max_x, max_y, "x", color="#37D5D6", markersize=4.2, markeredgewidth=1.0, zorder=5)
    ax.set_title(f"{title}\n$T_{{max}}$ = {max_temp:.2f} K", fontsize=7.5, pad=3.0)
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_xlim(0.0, width_mm)
    ax.set_ylim(0.0, height_mm)
    return image


def draw_difference_panel(
    ax: plt.Axes,
    difference: np.ndarray,
    blocks,
    width_um: float,
    height_um: float,
    norm: TwoSlopeNorm,
    metrics: dict[str, float | int | str],
) -> mpl.image.AxesImage:
    width_mm = width_um / 1000.0
    height_mm = height_um / 1000.0
    image = ax.imshow(
        difference,
        origin="lower",
        extent=(0.0, width_mm, 0.0, height_mm),
        interpolation="nearest",
        cmap="coolwarm",
        norm=norm,
        aspect="equal",
        rasterized=True,
    )
    add_cell_grid(ax, difference.shape[0], difference.shape[1], width_mm, height_mm)
    draw_floorplan(ax, blocks, width_um, height_um, "none")
    ax.text(
        0.03,
        0.97,
        f"bias = {metrics['mean_bias_K']:+.2f} K\n"
        f"MAE = {metrics['mae_K']:.2f} K\n"
        f"RMSE = {metrics['rmse_K']:.2f} K\n"
        f"r = {metrics['pearson_r']:.3f}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=5.8,
        color="black",
        bbox={"boxstyle": "round,pad=0.22", "facecolor": "white", "alpha": 0.78, "linewidth": 0},
        zorder=6,
    )
    ax.set_title("3D-ICE − HotSpot", fontsize=8.0, pad=4.0)
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_xlim(0.0, width_mm)
    ax.set_ylim(0.0, height_mm)
    return image


def save_figure(fig: plt.Figure, output_prefix: Path) -> list[Path]:
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    png_path = output_prefix.with_suffix(".png")
    svg_path = output_prefix.with_suffix(".svg")
    output_prefix.with_suffix(".pdf").unlink(missing_ok=True)
    output_prefix.with_suffix(".tiff").unlink(missing_ok=True)
    fig.savefig(png_path, dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(svg_path, format="svg", bbox_inches="tight", facecolor="white")
    return [png_path, svg_path]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare aligned HotSpot and 3D-ICE thermal grids.")
    hotspot_input = parser.add_mutually_exclusive_group(required=True)
    hotspot_input.add_argument("--hotspot-grid-trace", type=Path)
    hotspot_input.add_argument("--hotspot-grid-steady", type=Path)
    parser.add_argument("--hotspot-layer", type=int, default=2)
    parser.add_argument("--hotspot-origin", choices=("upper", "lower"), default="upper")
    parser.add_argument("--three-dice-map", required=True, type=Path)
    parser.add_argument("--three-dice-time-source", type=Path)
    parser.add_argument("--floorplan", required=True, type=Path)
    parser.add_argument("--rows", type=int, default=64)
    parser.add_argument("--columns", type=int, default=64)
    parser.add_argument("--time", type=float, help="comparison time; defaults to latest common time")
    parser.add_argument("--output", required=True, type=Path, help="output prefix")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    three_dice_frames = parse_temperature_maps(args.three_dice_map)
    flip_hotspot = args.hotspot_origin == "upper"

    if args.hotspot_grid_steady is not None:
        if len(three_dice_frames) != 1:
            raise ValueError("steady comparison requires one 3D-ICE Tmap frame")
        hotspot = parse_hotspot_grid_steady(
            args.hotspot_grid_steady, args.rows, args.columns, flip_hotspot
        )
        three_dice = three_dice_frames[0]
        comparison_time: float | None = None
        comparison_title = "Top active layer · 64×64 grid · steady state"
        comparison_state = "steady"
    else:
        if args.three_dice_time_source is None:
            raise ValueError("transient comparison requires --three-dice-time-source")
        hotspot_times, hotspot_frames = parse_hotspot_grid_trace(
            args.hotspot_grid_trace,
            args.hotspot_layer,
            args.rows,
            args.columns,
            flip_vertical=flip_hotspot,
        )
        three_dice_times = parse_times(args.three_dice_time_source)
        if len(three_dice_times) != len(three_dice_frames):
            raise ValueError("3D-ICE timestamp and Tmap frame counts differ")
        if args.time is None:
            common_times = [
                time
                for time in hotspot_times
                if np.any(np.isclose(three_dice_times, time, rtol=1.0e-9))
            ]
            if not common_times:
                raise ValueError("HotSpot and 3D-ICE have no common timestamps")
            comparison_time = float(max(common_times))
        else:
            comparison_time = args.time
        hotspot = hotspot_frames[
            select_time_index(hotspot_times, comparison_time, "HotSpot grid trace")
        ]
        three_dice = three_dice_frames[
            select_time_index(three_dice_times, comparison_time, "3D-ICE time source")
        ]
        comparison_title = f"Top active layer · 64×64 grid · t = {comparison_time:.6g} s"
        comparison_state = "transient"

    metrics = comparison_metrics(hotspot, three_dice)
    metrics["comparison_state"] = comparison_state
    metrics["time_s"] = comparison_time
    metrics["hotspot_layer"] = args.hotspot_layer

    blocks = parse_floorplan(args.floorplan)
    width_um, height_um = floorplan_extent(blocks)
    shared_min = float(min(np.min(hotspot), np.min(three_dice)))
    shared_max = float(max(np.max(hotspot), np.max(three_dice)))
    temperature_norm = Normalize(vmin=shared_min, vmax=shared_max)
    difference = three_dice - hotspot
    difference_limit = float(np.max(np.abs(difference)))
    if difference_limit == 0.0:
        difference_limit = 0.5
    difference_norm = TwoSlopeNorm(vmin=-difference_limit, vcenter=0.0, vmax=difference_limit)

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.85), constrained_layout=True)
    hotspot_image = draw_temperature_panel(
        axes[0], hotspot, "HotSpot", blocks, width_um, height_um, temperature_norm
    )
    draw_temperature_panel(
        axes[1], three_dice, "3D-ICE", blocks, width_um, height_um, temperature_norm
    )
    difference_image = draw_difference_panel(
        axes[2], difference, blocks, width_um, height_um, difference_norm, metrics
    )
    for label, axis in zip(("a", "b", "c"), axes):
        axis.text(-0.16, 1.05, label, transform=axis.transAxes, fontweight="bold", fontsize=8.0)

    temperature_bar = fig.colorbar(
        hotspot_image, ax=[axes[0], axes[1]], location="bottom", shrink=0.82, pad=0.02, aspect=35
    )
    temperature_bar.set_label("Temperature (K)")
    difference_bar = fig.colorbar(
        difference_image, ax=axes[2], location="bottom", shrink=0.82, pad=0.02, aspect=18
    )
    difference_bar.set_label("ΔT (K)")
    fig.suptitle(comparison_title, fontsize=9.0)

    outputs = save_figure(fig, args.output)
    plt.close(fig)
    metrics_path = args.output.with_name(args.output.name + "_metrics.json")
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for output in outputs:
        print(output)
    print(metrics_path)
    print(json.dumps(metrics, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
