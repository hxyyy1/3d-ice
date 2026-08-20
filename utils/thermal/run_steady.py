#!/usr/bin/env python3
"""Run a 3D-ICE steady analysis and create a standardized result bundle."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shlex
import subprocess
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


def resolve_emulator(explicit: Path | None) -> Path:
    if explicit is not None:
        candidate = explicit.expanduser().resolve()
    else:
        candidate = Path(__file__).resolve().parents[2] / "bin" / "3D-ICE-Emulator"
    if not candidate.is_file() or not os.access(candidate, os.X_OK):
        raise FileNotFoundError(f"3D-ICE-Emulator is not executable: {candidate}")
    return candidate


def phase_suffix(phase: str) -> str:
    return "" if phase == "both" else f"_{phase}"


def result_path(results_dir: Path, stem: str, suffix: str, extension: str) -> Path:
    return results_dir / f"{stem}{suffix}{extension}"


def run_emulator(
    emulator: Path,
    stack: Path,
    results_dir: Path,
    suffix: str,
    log_path: Path,
) -> None:
    command = [
        str(emulator),
        str(stack),
        "--steady-results-dir",
        str(results_dir),
        "--result-suffix",
        suffix,
    ]
    completed = subprocess.run(
        command,
        cwd=stack.parent,
        text=True,
        capture_output=True,
        check=False,
    )
    log_path.write_text(
        "simulator: 3D-ICE\n"
        + "command: "
        + shlex.join(command)
        + f"\nreturncode: {completed.returncode}\n\n[stdout]\n"
        + completed.stdout
        + "\n[stderr]\n"
        + completed.stderr,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"3D-ICE-Emulator exited with status {completed.returncode}; see {log_path}"
        )


def read_steady_nodes(path: Path) -> list[tuple[str, float]]:
    nodes: list[tuple[str, float]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        fields = raw_line.split()
        if not fields:
            continue
        if len(fields) != 2:
            raise ValueError(f"malformed steady node row at {path}:{line_number}")
        temperature = float(fields[1])
        if not math.isfinite(temperature):
            raise ValueError(f"non-finite steady node temperature at {path}:{line_number}")
        nodes.append((fields[0], temperature))
    if not nodes:
        raise ValueError(f"steady node result is empty: {path}")
    return nodes


def read_grid_steady(path: Path) -> dict[int, np.ndarray]:
    layers: dict[int, list[float]] = {}
    current_layer: int | None = None
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("Layer ") and line.endswith(":"):
            current_layer = int(line.split()[1].rstrip(":"))
            if current_layer in layers:
                raise ValueError(f"duplicate grid layer {current_layer} in {path}")
            layers[current_layer] = []
            continue
        if current_layer is None:
            raise ValueError(f"grid value precedes layer header at {path}:{line_number}")
        fields = line.split()
        if len(fields) != 2 or int(fields[0]) != len(layers[current_layer]):
            raise ValueError(f"malformed/non-contiguous grid row at {path}:{line_number}")
        value = float(fields[1])
        if not math.isfinite(value):
            raise ValueError(f"non-finite grid temperature at {path}:{line_number}")
        layers[current_layer].append(value)
    if not layers:
        raise ValueError(f"steady grid result is empty: {path}")
    return {layer: np.asarray(values) for layer, values in layers.items()}


def resolve_grid_shape(
    layers: dict[int, np.ndarray], rows: int | None, columns: int | None
) -> tuple[int, int]:
    cell_counts = {len(values) for values in layers.values()}
    if len(cell_counts) != 1:
        raise ValueError(
            "standard heatmaps require the same cell count in every layer; "
            "non-uniform grids remain available in the raw grid file"
        )
    cell_count = next(iter(cell_counts))
    if (rows is None) != (columns is None):
        raise ValueError("--grid-rows and --grid-cols must be supplied together")
    if rows is None:
        side = math.isqrt(cell_count)
        if side * side != cell_count:
            raise ValueError("cannot infer a square grid; pass --grid-rows and --grid-cols")
        rows = columns = side
    if rows <= 0 or columns <= 0 or rows * columns != cell_count:
        raise ValueError(
            f"grid shape {rows}x{columns} does not match {cell_count} cells per layer"
        )
    return rows, columns


def write_steady_tsv(nodes: list[tuple[str, float]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(("node", "temperature_k", "temperature_c"))
        for node, temperature_k in nodes:
            writer.writerow((node, f"{temperature_k:.12g}", f"{temperature_k - 273.15:.12g}"))


def render_heatmaps(
    layers: dict[int, np.ndarray],
    rows: int,
    columns: int,
    heatmap_dir: Path,
    suffix: str,
) -> list[Path]:
    heatmap_dir.mkdir(parents=True, exist_ok=True)
    all_celsius = np.concatenate([values for _, values in sorted(layers.items())]) - 273.15
    color_min = float(np.min(all_celsius))
    color_max = float(np.max(all_celsius))
    if color_max == color_min:
        color_min -= 0.5
        color_max += 0.5

    outputs: list[Path] = []
    for layer, values in sorted(layers.items()):
        grid = values.reshape(rows, columns) - 273.15
        fig, ax = plt.subplots(figsize=(3.5, 3.1), constrained_layout=True)
        image = ax.imshow(
            grid,
            origin="lower",
            interpolation="nearest",
            cmap="hot_r",
            vmin=color_min,
            vmax=color_max,
            aspect="equal",
            rasterized=True,
        )
        ax.set_title(
            f"Steady temperature — layer {layer}\n"
            f"max {float(np.max(grid)):.2f} °C",
            fontsize=8.0,
        )
        ax.set_xlabel("Grid column")
        ax.set_ylabel("Grid row")
        colorbar = fig.colorbar(image, ax=ax, shrink=0.86, pad=0.03)
        colorbar.set_label("Temperature (°C)")

        output_base = heatmap_dir / f"steady_layer_{layer:02d}{suffix}"
        png_path = Path(f"{output_base}.png")
        svg_path = Path(f"{output_base}.svg")
        Path(f"{output_base}.pdf").unlink(missing_ok=True)
        Path(f"{output_base}.tiff").unlink(missing_ok=True)
        fig.savefig(png_path, dpi=600, bbox_inches="tight", facecolor="white")
        fig.savefig(svg_path, format="svg", bbox_inches="tight", facecolor="white")
        outputs.extend((png_path, svg_path))
        plt.close(fig)
    return outputs


def build_summary(
    *,
    emulator: Path,
    stack: Path,
    phase: str,
    suffix: str,
    nodes: list[tuple[str, float]],
    layers: dict[int, np.ndarray],
    rows: int,
    columns: int,
    heatmaps: list[Path],
) -> dict[str, object]:
    hottest_node, maximum_node_k = max(nodes, key=lambda item: item[1])
    minimum_node, minimum_node_k = min(nodes, key=lambda item: item[1])
    hottest_layer = max(layers, key=lambda layer: float(np.max(layers[layer])))
    hottest_cell = int(np.argmax(layers[hottest_layer]))
    maximum_grid_k = float(layers[hottest_layer][hottest_cell])
    return {
        "simulator": "3D-ICE",
        "emulator": str(emulator),
        "stack_file": str(stack),
        "analysis": "steady",
        "phase": phase,
        "filename_suffix": suffix,
        "grid_rows": rows,
        "grid_cols": columns,
        "grid_layer_count": len(layers),
        "node_count": len(nodes),
        "steady": {
            "hottest_node": hottest_node,
            "maximum_temperature_k": maximum_node_k,
            "maximum_temperature_c": maximum_node_k - 273.15,
            "coolest_node": minimum_node,
            "minimum_temperature_k": minimum_node_k,
            "minimum_temperature_c": minimum_node_k - 273.15,
        },
        "grid": {
            "hottest_layer": hottest_layer,
            "hottest_cell_index": hottest_cell,
            "maximum_temperature_k": maximum_grid_k,
            "maximum_temperature_c": maximum_grid_k - 273.15,
        },
        "temperature_unit": "kelvin in raw files; kelvin and Celsius in TSV/JSON",
        "heatmaps": [str(path) for path in heatmaps if path.suffix == ".png"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run 3D-ICE steady analysis and create OUTPUT_DIR/thermal/results/."
    )
    parser.add_argument("--stack", required=True, type=Path, help="steady .stk input")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("trace_output"),
        help="output root; standardized files are written below thermal/results/",
    )
    parser.add_argument("--emulator", type=Path, help="3D-ICE-Emulator path")
    parser.add_argument("--phase", choices=("both", "prefill", "decode"), default="both")
    parser.add_argument("--grid-rows", type=int)
    parser.add_argument("--grid-cols", type=int)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stack = args.stack.expanduser().resolve()
    if not stack.is_file():
        raise FileNotFoundError(f"stack file does not exist: {stack}")
    emulator = resolve_emulator(args.emulator)
    suffix = phase_suffix(args.phase)
    results_dir = args.output_dir.expanduser().resolve() / "thermal" / "results"
    heatmap_dir = results_dir / "heatmaps"
    results_dir.mkdir(parents=True, exist_ok=True)

    raw_nodes = result_path(results_dir, "temperature", suffix, ".steady")
    raw_grid = result_path(results_dir, "temperature_grid", suffix, ".steady")
    steady_tsv = result_path(results_dir, "temperature_steady", suffix, ".tsv")
    log_path = result_path(results_dir, "hotspot_steady", suffix, ".log")
    summary_path = result_path(results_dir, "thermal_summary", suffix, ".json")

    run_emulator(emulator, stack, results_dir, suffix, log_path)
    nodes = read_steady_nodes(raw_nodes)
    layers = read_grid_steady(raw_grid)
    rows, columns = resolve_grid_shape(layers, args.grid_rows, args.grid_cols)
    write_steady_tsv(nodes, steady_tsv)
    heatmaps = render_heatmaps(
        layers,
        rows,
        columns,
        heatmap_dir,
        suffix,
    )
    summary = build_summary(
        emulator=emulator,
        stack=stack,
        phase=args.phase,
        suffix=suffix,
        nodes=nodes,
        layers=layers,
        rows=rows,
        columns=columns,
        heatmaps=heatmaps,
    )
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    for path in (raw_nodes, raw_grid, steady_tsv, log_path, summary_path, *heatmaps):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
