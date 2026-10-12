#!/usr/bin/env python3
"""Plot HotSpot-like 3D-ICE thermal maps with floorplan overlays.

The script reads one 3D-ICE floorplan and one or more Tmap/time-output pairs.
Static panels use a shared temperature scale and export PNG plus editable SVG.
"""

from __future__ import annotations

import argparse
import math
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

if "MPLCONFIGDIR" not in os.environ:
    default_mpl_config = Path.home() / ".config" / "matplotlib"
    writable_target = default_mpl_config if default_mpl_config.exists() else default_mpl_config.parent
    if not os.access(writable_target, os.W_OK):
        fallback_mpl_config = Path(tempfile.gettempdir()) / f"3dice-matplotlib-{os.getuid()}"
        fallback_mpl_config.mkdir(parents=True, exist_ok=True)
        os.environ["MPLCONFIGDIR"] = str(fallback_mpl_config)

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize
from matplotlib.patches import Rectangle


mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 8,
        "axes.linewidth": 0.8,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
    }
)


NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
BLOCK_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*$")
POSITION_RE = re.compile(rf"\bposition\s+({NUMBER})\s*,\s*({NUMBER})")
DIMENSION_RE = re.compile(rf"\bdimension\s+({NUMBER})\s*,\s*({NUMBER})")
RECTANGLE_RE = re.compile(
    rf"\brectangle\s*\(\s*({NUMBER})\s*,\s*({NUMBER})\s*,\s*"
    rf"({NUMBER})\s*,\s*({NUMBER})\s*\)"
)


@dataclass
class FloorplanBlock:
    name: str
    rectangles: list[tuple[float, float, float, float]] = field(default_factory=list)
    position: tuple[float, float] | None = None
    dimension: tuple[float, float] | None = None

    def finalize(self) -> None:
        if not self.rectangles and self.position is not None and self.dimension is not None:
            self.rectangles.append((*self.position, *self.dimension))
        if not self.rectangles:
            raise ValueError(f"floorplan block {self.name!r} has no geometry")

    @property
    def area(self) -> float:
        return sum(width * height for _, _, width, height in self.rectangles)

    @property
    def center(self) -> tuple[float, float]:
        weighted_x = 0.0
        weighted_y = 0.0
        total_area = 0.0
        for x, y, width, height in self.rectangles:
            area = width * height
            weighted_x += (x + width / 2.0) * area
            weighted_y += (y + height / 2.0) * area
            total_area += area
        return weighted_x / total_area, weighted_y / total_area


@dataclass
class ThermalCase:
    label: str
    frames: np.ndarray
    times: np.ndarray


def parse_floorplan(path: Path) -> list[FloorplanBlock]:
    blocks: list[FloorplanBlock] = []
    current: FloorplanBlock | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("//", 1)[0].strip()
        if not line:
            continue

        block_match = BLOCK_RE.match(line)
        if block_match:
            if current is not None:
                current.finalize()
                blocks.append(current)
            current = FloorplanBlock(block_match.group(1))
            continue

        if current is None:
            continue

        position_match = POSITION_RE.search(line)
        if position_match:
            current.position = tuple(float(value) for value in position_match.groups())

        dimension_match = DIMENSION_RE.search(line)
        if dimension_match:
            current.dimension = tuple(float(value) for value in dimension_match.groups())

        for rectangle_match in RECTANGLE_RE.finditer(line):
            rectangle = tuple(float(value) for value in rectangle_match.groups())
            if rectangle[2] <= 0.0 or rectangle[3] <= 0.0:
                raise ValueError(f"floorplan block {current.name!r} has non-positive geometry")
            current.rectangles.append(rectangle)

    if current is not None:
        current.finalize()
        blocks.append(current)

    if not blocks:
        raise ValueError(f"no floorplan blocks found in {path}")

    return blocks


def parse_temperature_maps(path: Path) -> np.ndarray:
    frames: list[np.ndarray] = []
    rows: list[list[float]] = []

    def finish_frame() -> None:
        nonlocal rows
        if not rows:
            return
        width = len(rows[0])
        if width == 0 or any(len(row) != width for row in rows):
            raise ValueError(f"ragged temperature map in {path}")
        frames.append(np.asarray(rows, dtype=float))
        rows = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("%"):
            continue
        if not line:
            finish_frame()
            continue
        try:
            rows.append([float(value) for value in line.split()])
        except ValueError as exc:
            raise ValueError(f"invalid numeric row in {path}: {raw_line!r}") from exc

    finish_frame()

    if not frames:
        raise ValueError(f"no temperature frames found in {path}")
    if any(frame.shape != frames[0].shape for frame in frames):
        raise ValueError(f"temperature-map shape changes between frames in {path}")

    data = np.stack(frames)
    if not np.isfinite(data).all():
        raise ValueError(f"non-finite temperature found in {path}")
    return data


def parse_times(path: Path) -> np.ndarray:
    times: list[float] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("%"):
            continue
        try:
            times.append(float(line.split()[0]))
        except (IndexError, ValueError) as exc:
            raise ValueError(f"invalid time row in {path}: {raw_line!r}") from exc
    if not times or not np.isfinite(times).all():
        raise ValueError(f"no finite timestamps found in {path}")
    if any(next_time <= time for time, next_time in zip(times, times[1:])):
        raise ValueError(f"timestamps are not strictly increasing in {path}")
    return np.asarray(times)


def floorplan_extent(blocks: Sequence[FloorplanBlock]) -> tuple[float, float]:
    width = max(x + rectangle_width for block in blocks for x, _, rectangle_width, _ in block.rectangles)
    height = max(y + rectangle_height for block in blocks for _, y, _, rectangle_height in block.rectangles)
    return width, height


def load_cases(
    map_paths: Sequence[Path], time_paths: Sequence[Path], labels: Sequence[str]
) -> list[ThermalCase]:
    if len(map_paths) != len(time_paths):
        raise ValueError("each --temperature-map requires one --time-source")
    if labels and len(labels) != len(map_paths):
        raise ValueError("the number of --label values must match the number of cases")

    cases: list[ThermalCase] = []
    for index, (map_path, time_path) in enumerate(zip(map_paths, time_paths)):
        frames = parse_temperature_maps(map_path)
        times = parse_times(time_path)
        if len(frames) != len(times):
            raise ValueError(
                f"{map_path} contains {len(frames)} frames but {time_path} contains "
                f"{len(times)} timestamps"
            )
        label = labels[index] if labels else map_path.stem
        cases.append(ThermalCase(label=label, frames=frames, times=times))
    return cases


def resolve_frame(case: ThermalCase, requested: int) -> int:
    index = requested if requested >= 0 else len(case.frames) + requested
    if index < 0 or index >= len(case.frames):
        raise ValueError(
            f"frame {requested} is outside case {case.label!r} with {len(case.frames)} frames"
        )
    return index


def label_is_visible(block: FloorplanBlock, chip_area: float, mode: str) -> bool:
    if mode == "none":
        return False
    if mode == "all":
        return True
    return block.area / chip_area >= 0.006


def draw_floorplan(
    ax: plt.Axes,
    blocks: Sequence[FloorplanBlock],
    width_um: float,
    height_um: float,
    label_mode: str,
    font_size: float = 6.0,
) -> None:
    chip_area = width_um * height_um
    for block in blocks:
        for x, y, width, height in block.rectangles:
            ax.add_patch(
                Rectangle(
                    (x / 1000.0, y / 1000.0),
                    width / 1000.0,
                    height / 1000.0,
                    facecolor="none",
                    edgecolor="black",
                    linewidth=0.65,
                    zorder=3,
                )
            )
        if label_is_visible(block, chip_area, label_mode):
            center_x, center_y = block.center
            text = ax.text(
                center_x / 1000.0,
                center_y / 1000.0,
                block.name,
                color="white",
                fontsize=font_size,
                ha="center",
                va="center",
                zorder=4,
                clip_on=True,
            )
            text.set_path_effects(
                [path_effects.Stroke(linewidth=1.4, foreground="black"), path_effects.Normal()]
            )


def maximum_location(frame: np.ndarray, width_mm: float, height_mm: float) -> tuple[float, float, float]:
    row, column = np.unravel_index(np.argmax(frame), frame.shape)
    x = (column + 0.5) * width_mm / frame.shape[1]
    y = (row + 0.5) * height_mm / frame.shape[0]
    return x, y, float(frame[row, column])


def draw_panel(
    ax: plt.Axes,
    frame: np.ndarray,
    time: float,
    label: str,
    blocks: Sequence[FloorplanBlock],
    width_um: float,
    height_um: float,
    norm: Normalize,
    cmap: str,
    label_mode: str,
    grid_line_mode: str,
) -> mpl.image.AxesImage:
    width_mm = width_um / 1000.0
    height_mm = height_um / 1000.0
    image = ax.imshow(
        frame,
        origin="lower",
        extent=(0.0, width_mm, 0.0, height_mm),
        interpolation="nearest",
        cmap=cmap,
        norm=norm,
        aspect="equal",
        rasterized=True,
    )
    draw_floorplan(ax, blocks, width_um, height_um, label_mode)

    show_grid_lines = grid_line_mode == "on" or (
        grid_line_mode == "auto" and max(frame.shape) <= 64
    )
    if show_grid_lines:
        ax.set_xticks(np.linspace(0.0, width_mm, frame.shape[1] + 1), minor=True)
        ax.set_yticks(np.linspace(0.0, height_mm, frame.shape[0] + 1), minor=True)
        ax.grid(which="minor", color="black", linewidth=0.18, alpha=0.12, zorder=2)
        ax.tick_params(which="minor", bottom=False, left=False)

    max_x, max_y, max_temp = maximum_location(frame, width_mm, height_mm)
    ax.plot(max_x, max_y, marker="x", color="#37D5D6", markersize=5.0, markeredgewidth=1.2, zorder=5)
    ax.text(
        0.02,
        0.98,
        f"$T_{{max}}$ = {max_temp:.2f} K",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.0,
        color="white",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": "black", "alpha": 0.55, "linewidth": 0},
        zorder=6,
    )
    ax.text(
        0.98,
        0.02,
        f"{frame.shape[1]}×{frame.shape[0]} cells",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=6.5,
        color="black",
        bbox={"boxstyle": "round,pad=0.18", "facecolor": "white", "alpha": 0.65, "linewidth": 0},
        zorder=6,
    )
    ax.set_title(f"{label} · t = {time:.6g} s", fontsize=9.0, pad=5.0)
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_xlim(0.0, width_mm)
    ax.set_ylim(0.0, height_mm)
    ax.tick_params(direction="out", length=2.5, width=0.7)
    return image


def save_static_figure(fig: plt.Figure, output_prefix: Path) -> list[Path]:
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    png_path = output_prefix.with_suffix(".png")
    svg_path = output_prefix.with_suffix(".svg")
    output_prefix.with_suffix(".pdf").unlink(missing_ok=True)
    output_prefix.with_suffix(".tiff").unlink(missing_ok=True)
    fig.savefig(png_path, dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(svg_path, format="svg", bbox_inches="tight", facecolor="white")
    return [png_path, svg_path]


def plot_static(
    cases: Sequence[ThermalCase],
    frame_indices: Sequence[int],
    blocks: Sequence[FloorplanBlock],
    width_um: float,
    height_um: float,
    vmin: float,
    vmax: float,
    cmap: str,
    label_mode: str,
    grid_line_mode: str,
    title: str | None,
    output_prefix: Path,
) -> list[Path]:
    panel_count = len(cases)
    fig, axes = plt.subplots(
        1,
        panel_count,
        figsize=(3.35 * panel_count + 0.45, 3.15),
        squeeze=False,
        constrained_layout=True,
    )
    norm = Normalize(vmin=vmin, vmax=vmax)
    images = []
    for axis, case, frame_index in zip(axes[0], cases, frame_indices):
        images.append(
            draw_panel(
                axis,
                case.frames[frame_index],
                float(case.times[frame_index]),
                case.label,
                blocks,
                width_um,
                height_um,
                norm,
                cmap,
                label_mode,
                grid_line_mode,
            )
        )

    colorbar = fig.colorbar(images[0], ax=list(axes[0]), location="right", shrink=0.86, pad=0.025)
    colorbar.set_label("Temperature (K)")
    colorbar.ax.tick_params(length=2.5, width=0.7)
    if title:
        fig.suptitle(title, fontsize=10.0)
    return save_static_figure(fig, output_prefix)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render HotSpot-like 3D-ICE temperature maps with floorplan overlays."
    )
    parser.add_argument("--floorplan", required=True, type=Path, help="3D-ICE floorplan file")
    parser.add_argument(
        "--temperature-map",
        required=True,
        action="append",
        type=Path,
        help="3D-ICE Tmap output; repeat for comparison panels",
    )
    parser.add_argument(
        "--time-source",
        required=True,
        action="append",
        type=Path,
        help="time-column output matching each Tmap; repeat for comparison panels",
    )
    parser.add_argument("--label", action="append", default=[], help="panel label; repeat per case")
    parser.add_argument("--output", required=True, type=Path, help="static output prefix")
    parser.add_argument("--frame", type=int, default=-1, help="frame index; negative values count from end")
    parser.add_argument("--vmin", type=float, help="shared lower temperature bound")
    parser.add_argument("--vmax", type=float, help="shared upper temperature bound")
    parser.add_argument(
        "--cmap",
        default="hot_r",
        help="Matplotlib colormap (default: hot_r, matching HotSpot's Python plotter)",
    )
    parser.add_argument(
        "--labels",
        choices=("auto", "all", "none"),
        default="auto",
        help="floorplan block label density",
    )
    parser.add_argument(
        "--grid-lines",
        choices=("auto", "on", "off"),
        default="auto",
        help="cell boundary visibility (auto shows grids up to 64×64)",
    )
    parser.add_argument("--title", help="optional figure-level title")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    blocks = parse_floorplan(args.floorplan)
    width_um, height_um = floorplan_extent(blocks)
    cases = load_cases(args.temperature_map, args.time_source, args.label)
    frame_indices = [resolve_frame(case, args.frame) for case in cases]
    selected_frames = [case.frames[index] for case, index in zip(cases, frame_indices)]

    data_min = min(float(np.min(frame)) for frame in selected_frames)
    data_max = max(float(np.max(frame)) for frame in selected_frames)
    vmin = data_min if args.vmin is None else args.vmin
    vmax = data_max if args.vmax is None else args.vmax
    if not math.isfinite(vmin) or not math.isfinite(vmax) or vmax < vmin:
        raise ValueError("invalid temperature scale")
    if vmax == vmin:
        vmin -= 0.5
        vmax += 0.5

    outputs = plot_static(
        cases,
        frame_indices,
        blocks,
        width_um,
        height_um,
        vmin,
        vmax,
        args.cmap,
        args.labels,
        args.grid_lines,
        args.title,
        args.output,
    )
    plt.close("all")

    for output in outputs:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
