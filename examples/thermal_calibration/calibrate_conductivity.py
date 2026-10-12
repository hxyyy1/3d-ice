#!/usr/bin/env python3
"""Reproduce and audit the memory-package thermal-property calibration.

Conductivity calculations use W m^-1 K^-1.  Volumetric heat capacities use
MJ m^-3 K^-1.  Values written to 3D-ICE stack files are divided by 1e6 for
conductivity and multiplied by 1e-12 for volumetric heat capacity because the
solver geometry is in um.

The only non-standard dependencies are NumPy and SciPy.  They are used for the
finite-volume homogenization of the package-plane die/EMC maps; the remaining
mixture and resistance calculations are analytic.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve


ROOT = Path(__file__).resolve().parents[2]

# Nominal material properties at the model reference temperature (about 320 K).
K_SI = 130.0
K_CU = 390.0
K_EMC = 0.88
K_BT = 0.34
K_DAF = 0.30
K_AIR = 0.0275
K_SAC = 58.0
K_NI = 90.0
K_PI = 0.20
K_NCF = 0.20

# Volumetric heat capacities in MJ m^-3 K^-1 at about 320 K.  Active/source
# layer heat capacities are intentionally excluded from this calibration.
CV_SI = 1.71
CV_CU = 3.45
CV_EMC = 1.52
CV_BT = 1.60
CV_DAF = 1.50
CV_AIR = 0.00111
CV_SAC = 1.71
CV_NI = 4.00
CV_PI = 1.50
CV_NCF = 1.37
CV_W = 2.58
CV_SIO2 = 1.606


def harmonic_layer(thicknesses: list[float], conductivities: list[float]) -> float:
    """One-dimensional series conductivity for layers of the same area."""
    return sum(thicknesses) / sum(t / k for t, k in zip(thicknesses, conductivities))


def maxwell_cylinders(k_matrix: float, k_inclusion: float, fraction: float) -> float:
    """Transverse Maxwell solution for dilute aligned cylindrical inclusions."""
    numerator = k_inclusion + k_matrix + fraction * (k_inclusion - k_matrix)
    denominator = k_inclusion + k_matrix - fraction * (k_inclusion - k_matrix)
    return k_matrix * numerator / denominator


def volume_average(fraction: float, inclusion: float, matrix: float) -> float:
    """Volume-conserving heat-capacity mixture for local thermal equilibrium."""
    return fraction * inclusion + (1.0 - fraction) * matrix


def laminate_substrate(
    total_um: float,
    copper_layers: int,
    copper_um: float,
    trace_coverage: float,
    k_dielectric: float = K_BT,
) -> tuple[float, float, float]:
    """Return (kx, ky, kz) for a copper/dielectric package substrate.

    Patterned metal lamina are first homogenized through their plan area.  The
    lamina then conduct in parallel in-plane and in series through-plane, as in
    the design-based BGA methodology of Johnson et al. (ITHERM 1998).
    """
    metal_total = copper_layers * copper_um
    if metal_total >= total_um:
        raise ValueError("Copper thickness must be smaller than total substrate thickness")
    k_patterned_metal = trace_coverage * K_CU + (1.0 - trace_coverage) * k_dielectric
    k_xy = (
        (total_um - metal_total) * k_dielectric + metal_total * k_patterned_metal
    ) / total_um
    k_z = total_um / (
        (total_um - metal_total) / k_dielectric + metal_total / k_patterned_metal
    )
    return k_xy, k_xy, k_z


def bga_standoff(
    package_area_mm2: float,
    ball_count: int,
    ball_diameter_mm: float,
    height_mm: float,
    spreading_resistance_area: float = 3.0e-4,
) -> tuple[float, float, float]:
    """Equivalent BGA layer including unresolved pad/constriction resistance.

    The bulk vertical term is the solder/air area-parallel upper bound.  A
    calibrated area-specific spreading/contact resistance is then added in
    series.  The in-plane value is air, following Johnson et al. for an
    unencapsulated ball array.
    """
    f_ball = ball_count * math.pi * (ball_diameter_mm / 2.0) ** 2 / package_area_mm2
    k_bulk_z = f_ball * K_SAC + (1.0 - f_ball) * K_AIR
    height_m = height_mm * 1.0e-3
    k_z = height_m / (height_m / k_bulk_z + spreading_resistance_area)
    return K_AIR, K_AIR, k_z


def flip_chip_bond() -> tuple[float, float, float]:
    """GDDR Cu-pillar/Ni/SAC/PI/underfill equivalent for a 48 um layer."""
    pitch_um = 57.0
    diameter_um = 25.0
    f_bump = math.pi * (diameter_um / 2.0) ** 2 / pitch_um**2

    # Outside the PI opening: 43 um underfill plus 5 um PI in series.
    k_matrix = harmonic_layer([43.0, 5.0], [K_EMC, K_PI])
    # Inside the opening: Cu pillar, Ni barrier, SAC cap and a short Cu/Al pad
    # closure for the 5 um PI opening.
    k_column = harmonic_layer([30.0, 3.0, 10.0, 5.0], [K_CU, K_NI, K_SAC, K_CU])
    k_bulk_z = f_bump * k_column + (1.0 - f_bump) * k_matrix

    # Contact resistance per actual bump area inferred from the IBM 50 um-pitch
    # microbump measurement after subtracting its bulk solder/underfill term.
    r_contact_bump = 1.30e-6  # m2 K W^-1 on actual bump area
    thickness_m = 48.0e-6
    k_z = thickness_m / (thickness_m / k_bulk_z + r_contact_bump / f_bump)
    k_xy = maxwell_cylinders(k_matrix, k_column, f_bump)
    return k_xy, k_xy, k_z


def tsv_silicon(f_tsv: float) -> tuple[float, float, float]:
    """Continuous Cu cylinders in Si: Maxwell transverse, parallel axial."""
    k_xy = maxwell_cylinders(K_SI, K_CU, f_tsv)
    k_z = f_tsv * K_CU + (1.0 - f_tsv) * K_SI
    return k_xy, k_xy, k_z


def finite_volume_effective(
    length_x: float,
    length_y: float,
    cells_x: int,
    cells_y: int,
    rectangles: list[tuple[float, float, float, float]],
    k_matrix: float,
    k_rectangle: float,
    axis: str,
) -> float:
    """Solve div(k grad(T))=0 for one package-plane conductivity component.

    Unit temperatures are imposed on the two faces normal to ``axis`` and the
    other pair of faces is adiabatic.  Harmonic face conductivities preserve
    flux across material discontinuities.  Rectangles use the same cell grids
    as the corresponding 3D-ICE models.
    """
    dx = length_x / cells_x
    dy = length_y / cells_y
    x_centres = (np.arange(cells_x) + 0.5) * dx
    y_centres = (np.arange(cells_y) + 0.5) * dy
    conductivity = np.full((cells_y, cells_x), k_matrix, dtype=float)
    for x, y, width, height in rectangles:
        mask = (
            (y_centres[:, None] >= y)
            & (y_centres[:, None] < y + height)
            & (x_centres[None, :] >= x)
            & (x_centres[None, :] < x + width)
        )
        conductivity[mask] = k_rectangle

    count = cells_x * cells_y
    matrix = lil_matrix((count, count))
    rhs = np.zeros(count)

    def node(row: int, col: int) -> int:
        return row * cells_x + col

    for row in range(cells_y):
        for col in range(cells_x):
            centre = node(row, col)
            neighbours = (
                (row, col - 1, dy, dx),
                (row, col + 1, dy, dx),
                (row - 1, col, dx, dy),
                (row + 1, col, dx, dy),
            )
            for other_row, other_col, face_area, distance in neighbours:
                if 0 <= other_row < cells_y and 0 <= other_col < cells_x:
                    k_here = conductivity[row, col]
                    k_other = conductivity[other_row, other_col]
                    k_face = 2.0 * k_here * k_other / (k_here + k_other)
                    conductance = k_face * face_area / distance
                    matrix[centre, centre] += conductance
                    matrix[centre, node(other_row, other_col)] -= conductance

            if axis == "x" and col in (0, cells_x - 1):
                conductance = conductivity[row, col] * dy / (dx / 2.0)
                matrix[centre, centre] += conductance
                if col == cells_x - 1:
                    rhs[centre] += conductance
            elif axis == "y" and row in (0, cells_y - 1):
                conductance = conductivity[row, col] * dx / (dy / 2.0)
                matrix[centre, centre] += conductance
                if row == cells_y - 1:
                    rhs[centre] += conductance

    temperature = spsolve(matrix.tocsr(), rhs).reshape((cells_y, cells_x))
    if axis == "x":
        heat = sum(
            conductivity[row, -1] * dy / (dx / 2.0) * (1.0 - temperature[row, -1])
            for row in range(cells_y)
        )
        return heat * length_x / length_y
    heat = sum(
        conductivity[-1, col] * dx / (dy / 2.0) * (1.0 - temperature[-1, col])
        for col in range(cells_x)
    )
    return heat * length_y / length_x


def mapped_layer(
    length_x: float,
    length_y: float,
    cells_x: int,
    cells_y: int,
    rectangles: list[tuple[float, float, float, float]],
    k_rectangle: float = K_SI,
) -> tuple[float, float, float]:
    area_fraction = sum(width * height for _, _, width, height in rectangles) / (
        length_x * length_y
    )
    k_x = finite_volume_effective(
        length_x, length_y, cells_x, cells_y, rectangles, K_EMC, k_rectangle, "x"
    )
    k_y = finite_volume_effective(
        length_x, length_y, cells_x, cells_y, rectangles, K_EMC, k_rectangle, "y"
    )
    k_z = area_fraction * k_rectangle + (1.0 - area_fraction) * K_EMC
    return k_x, k_y, k_z


def calculate() -> dict[str, tuple[float, float, float]]:
    results: dict[str, tuple[float, float, float]] = {}

    results["GDDR6_ACTIVE"] = mapped_layer(
        12.0,
        14.0,
        48,
        56,
        [(1.885, 2.25, 8.23, 4.50), (1.885, 7.25, 8.23, 4.50)],
    )
    results["GDDR7_ACTIVE"] = mapped_layer(
        12.0,
        14.0,
        48,
        56,
        [(2.75, 0.40, 6.50, 6.40), (2.75, 7.00, 6.50, 6.40)],
    )
    results["LPDDR5X_ACTIVE"] = mapped_layer(
        14.0,
        12.4,
        56,
        62,
        [(0.50, 3.40, 6.50, 5.60), (7.00, 3.40, 6.50, 5.60)],
    )
    results["LPDDR6_ACTIVE"] = mapped_layer(
        14.0,
        12.4,
        56,
        62,
        [(0.75, 2.60, 6.25, 7.00), (7.00, 2.60, 6.25, 7.00)],
    )
    results["HBM_ACTIVE"] = mapped_layer(
        11.0, 11.0, 44, 44, [(0.25, 0.25, 10.50, 10.50)]
    )

    results["GDDR_FC_BOND"] = flip_chip_bond()
    results["GDDR6_SUBSTRATE"] = laminate_substrate(280.0, 4, 12.0, 25.0 / 55.0)
    results["GDDR7_SUBSTRATE"] = laminate_substrate(262.0, 6, 12.0, 25.0 / 55.0)
    results["LPDDR_SUBSTRATE"] = laminate_substrate(100.0, 2, 12.0, 0.35)
    results["GDDR6_BGA"] = bga_standoff(12.0 * 14.0, 180, 0.47, 0.34)
    results["GDDR7_BGA"] = bga_standoff(12.0 * 14.0, 266, 0.47, 0.30)
    results["LPDDR5X_BGA"] = bga_standoff(14.0 * 12.4, 496, 0.27, 0.20)
    results["LPDDR6_BGA"] = bga_standoff(14.0 * 12.4, 518, 0.27, 0.20)

    f_tsv = math.pi * 2.5**2 / 55.0**2
    results["HBM3E_TSV_SI"] = tsv_silicon(f_tsv)
    results["HBM4_TSV_SI"] = tsv_silicon(2.0 * f_tsv)
    results["HBM3E_BOND"] = (
        maxwell_cylinders(K_NCF, K_SAC, 0.20),
        maxwell_cylinders(K_NCF, K_SAC, 0.20),
        1.225,
    )
    results["HBM4_BOND"] = (
        maxwell_cylinders(K_EMC, K_SAC, 0.20),
        maxwell_cylinders(K_EMC, K_SAC, 0.20),
        1.225,
    )

    # HBF: map Sandisk BiCS8's 218 layers to a 40 nm W/SiO2 pair pitch.
    array_um = 218.0 * 0.040
    k_array_xy = 0.5 * 40.0 + 0.5 * 1.4
    k_array_z = harmonic_layer([20.0, 20.0], [40.0, 1.4])
    silicon_um = 33.0 - array_um
    k_nand_xy = (silicon_um * K_SI + array_um * k_array_xy) / 33.0
    k_nand_z = harmonic_layer([silicon_um, array_um], [K_SI, k_array_z])
    results["HBF_NAND_CORE"] = (k_nand_xy, k_nand_xy, k_nand_z)
    results["HBF_TSV_NAND"] = (
        maxwell_cylinders(k_nand_xy, K_CU, 2.0 * f_tsv),
        maxwell_cylinders(k_nand_xy, K_CU, 2.0 * f_tsv),
        2.0 * f_tsv * K_CU + (1.0 - 2.0 * f_tsv) * k_nand_z,
    )
    results["HBF_TSV_SI"] = results["HBM4_TSV_SI"]
    results["HBF_BOND"] = (
        maxwell_cylinders(K_EMC, K_SAC, 0.20),
        maxwell_cylinders(K_EMC, K_SAC, 0.20),
        10.0 / (15.0 / 1.225),
    )
    return results


def calculate_heat_capacities() -> dict[str, float]:
    """Return non-active volumetric heat capacities in MJ m^-3 K^-1."""
    results: dict[str, float] = {
        "SILICON": CV_SI,
        "EMC": CV_EMC,
        "DAF": CV_DAF,
    }

    # Patterned-Cu substrates: only the Cu-covered part of each metal lamina is
    # counted as copper volume; the remaining metal-lamina area is BT matrix.
    for name, total_um, layers, copper_um, coverage in (
        ("GDDR6_SUBSTRATE", 280.0, 4, 12.0, 25.0 / 55.0),
        ("GDDR7_SUBSTRATE", 262.0, 6, 12.0, 25.0 / 55.0),
        ("LPDDR_SUBSTRATE", 100.0, 2, 12.0, 0.35),
    ):
        f_cu = layers * copper_um * coverage / total_um
        results[name] = volume_average(f_cu, CV_CU, CV_BT)

    # GDDR 48 um Cu-pillar/Ni/SAC/PI/underfill layer.
    f_bump = math.pi * (25.0 / 2.0) ** 2 / 57.0**2
    cv_matrix = (43.0 * CV_EMC + 5.0 * CV_PI) / 48.0
    cv_column = (
        30.0 * CV_CU + 3.0 * CV_NI + 10.0 * CV_SAC + 5.0 * CV_CU
    ) / 48.0
    results["GDDR_FC_BOND"] = volume_average(f_bump, cv_column, cv_matrix)

    # Unencapsulated BGA arrays: solder-ball volume fraction is approximated by
    # the projected area fraction used by the collapsed standoff model.
    for name, package_area, count, diameter in (
        ("GDDR6_BGA", 12.0 * 14.0, 180, 0.47),
        ("GDDR7_BGA", 12.0 * 14.0, 266, 0.47),
        ("LPDDR5X_BGA", 14.0 * 12.4, 496, 0.27),
        ("LPDDR6_BGA", 14.0 * 12.4, 518, 0.27),
    ):
        f_ball = count * math.pi * (diameter / 2.0) ** 2 / package_area
        results[name] = volume_average(f_ball, CV_SAC, CV_AIR)

    f_tsv = math.pi * 2.5**2 / 55.0**2
    results["HBM3E_TSV_SI"] = volume_average(f_tsv, CV_CU, CV_SI)
    results["HBM4_TSV_SI"] = volume_average(2.0 * f_tsv, CV_CU, CV_SI)
    results["HBM3E_BOND"] = volume_average(0.20, CV_SAC, CV_NCF)
    results["HBM4_BOND"] = volume_average(0.20, CV_SAC, CV_EMC)

    # HBF passive NAND core: 24.28 um Si backing plus an 8.72 um 218-layer
    # W/SiO2 array.  Word-line and ILD occupy equal thickness in the proxy RUC.
    array_um = 218.0 * 0.040
    silicon_um = 33.0 - array_um
    cv_array = 0.5 * CV_W + 0.5 * CV_SIO2
    cv_nand = (silicon_um * CV_SI + array_um * cv_array) / 33.0
    results["HBF_NAND_CORE"] = cv_nand
    results["HBF_TSV_NAND"] = volume_average(2.0 * f_tsv, CV_CU, cv_nand)
    results["HBF_TSV_SI"] = results["HBM4_TSV_SI"]
    results["HBF_BOND"] = results["HBM4_BOND"]
    return results


MODEL_EXPECTATIONS = {
    "examples/gddr/gddr6_1pkg/model.stk": {
        "SILICON": (K_SI,) * 3,
        "EMC": (K_EMC,) * 3,
        "ACTIVE_LAYER_EQ": "GDDR6_ACTIVE",
        "FC_BUMP_UF_EQ": "GDDR_FC_BOND",
        "PACKAGE_SUBSTRATE_EQ": "GDDR6_SUBSTRATE",
        "BGA_SOLDER_AIR_EQ": "GDDR6_BGA",
    },
    "examples/gddr/gddr7_1pkg/model.stk": {
        "SILICON": (K_SI,) * 3,
        "EMC": (K_EMC,) * 3,
        "ACTIVE_LAYER_EQ": "GDDR7_ACTIVE",
        "FC_BUMP_UF_EQ": "GDDR_FC_BOND",
        "PACKAGE_SUBSTRATE_EQ": "GDDR7_SUBSTRATE",
        "BGA_SOLDER_AIR_EQ": "GDDR7_BGA",
    },
    "examples/lpddr/lpddr5x_1pkg/model.stk": {
        "SILICON": (K_SI,) * 3,
        "EMC": (K_EMC,) * 3,
        "ACTIVE_LAYER_EQ": "LPDDR5X_ACTIVE",
        "DAF": (K_DAF,) * 3,
        "PACKAGE_SUBSTRATE_EQ": "LPDDR_SUBSTRATE",
        "BGA_SOLDER_AIR_EQ": "LPDDR5X_BGA",
    },
    "examples/lpddr/lpddr6_1pkg/model.stk": {
        "SILICON": (K_SI,) * 3,
        "EMC": (K_EMC,) * 3,
        "ACTIVE_LAYER_EQ": "LPDDR6_ACTIVE",
        "DAF": (K_DAF,) * 3,
        "PACKAGE_SUBSTRATE_EQ": "LPDDR_SUBSTRATE",
        "BGA_SOLDER_AIR_EQ": "LPDDR6_BGA",
    },
    "examples/hbm/hbm3e_8h/model.stk": {
        "SILICON": (K_SI,) * 3,
        "TSV_SI_HBM3E_EQ": "HBM3E_TSV_SI",
        "EMC": (K_EMC,) * 3,
        "ACTIVE_LAYER_EQ": "HBM_ACTIVE",
        "NCF_BUMP_EQ": "HBM3E_BOND",
    },
    "examples/hbm/hbm4_12h/model.stk": {
        "SILICON": (K_SI,) * 3,
        "TSV_SI_HBM4_EQ": "HBM4_TSV_SI",
        "EMC": (K_EMC,) * 3,
        "ACTIVE_LAYER_EQ": "HBM_ACTIVE",
        "ADV_MR_MUF_BUMP_EQ": "HBM4_BOND",
    },
    "examples/hbf/hbf_384gb_16h/model.stk": {
        "SILICON": (K_SI,) * 3,
        "NAND_CORE_EQ": "HBF_NAND_CORE",
        "TSV_NAND_HBF_EQ": "HBF_TSV_NAND",
        "TSV_SI_HBF_EQ": "HBF_TSV_SI",
        "EMC": (K_EMC,) * 3,
        "CMOS_ACTIVE_LAYER_EQ": "HBM_ACTIVE",
        "MICROBUMP_MUF_EQ": "HBF_BOND",
    },
}


# Active/source materials are deliberately absent: the user requested that
# active-layer modeling remain unchanged in this calibration pass.
HEAT_CAPACITY_EXPECTATIONS = {
    "examples/gddr/gddr6_1pkg/model.stk": {
        "SILICON": "SILICON",
        "EMC": "EMC",
        "FC_BUMP_UF_EQ": "GDDR_FC_BOND",
        "PACKAGE_SUBSTRATE_EQ": "GDDR6_SUBSTRATE",
        "BGA_SOLDER_AIR_EQ": "GDDR6_BGA",
    },
    "examples/gddr/gddr7_1pkg/model.stk": {
        "SILICON": "SILICON",
        "EMC": "EMC",
        "FC_BUMP_UF_EQ": "GDDR_FC_BOND",
        "PACKAGE_SUBSTRATE_EQ": "GDDR7_SUBSTRATE",
        "BGA_SOLDER_AIR_EQ": "GDDR7_BGA",
    },
    "examples/lpddr/lpddr5x_1pkg/model.stk": {
        "SILICON": "SILICON",
        "EMC": "EMC",
        "DAF": "DAF",
        "PACKAGE_SUBSTRATE_EQ": "LPDDR_SUBSTRATE",
        "BGA_SOLDER_AIR_EQ": "LPDDR5X_BGA",
    },
    "examples/lpddr/lpddr6_1pkg/model.stk": {
        "SILICON": "SILICON",
        "EMC": "EMC",
        "DAF": "DAF",
        "PACKAGE_SUBSTRATE_EQ": "LPDDR_SUBSTRATE",
        "BGA_SOLDER_AIR_EQ": "LPDDR6_BGA",
    },
    "examples/hbm/hbm3e_8h/model.stk": {
        "SILICON": "SILICON",
        "TSV_SI_HBM3E_EQ": "HBM3E_TSV_SI",
        "EMC": "EMC",
        "NCF_BUMP_EQ": "HBM3E_BOND",
    },
    "examples/hbm/hbm4_12h/model.stk": {
        "SILICON": "SILICON",
        "TSV_SI_HBM4_EQ": "HBM4_TSV_SI",
        "EMC": "EMC",
        "ADV_MR_MUF_BUMP_EQ": "HBM4_BOND",
    },
    "examples/hbf/hbf_384gb_16h/model.stk": {
        "SILICON": "SILICON",
        "NAND_CORE_EQ": "HBF_NAND_CORE",
        "TSV_NAND_HBF_EQ": "HBF_TSV_NAND",
        "TSV_SI_HBF_EQ": "HBF_TSV_SI",
        "EMC": "EMC",
        "MICROBUMP_MUF_EQ": "HBF_BOND",
    },
}


def parse_stk_conductivities(path: Path) -> dict[str, tuple[float, float, float]]:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"material\s+(\w+)\s*:\s*.*?thermal\s+conductivity\s+([^;]+);",
        re.DOTALL,
    )
    parsed = {}
    for name, values_text in pattern.findall(text):
        values = tuple(float(value.strip()) * 1.0e6 for value in values_text.split(","))
        if len(values) == 1:
            values = values * 3
        parsed[name] = values
    return parsed


def parse_stk_heat_capacities(path: Path) -> dict[str, float]:
    """Read 3D-ICE J um^-3 K^-1 values and return MJ m^-3 K^-1."""
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"material\s+(\w+)\s*:\s*.*?volumetric\s+heat\s+capacity\s+([^;]+);",
        re.DOTALL,
    )
    return {name: float(value.strip()) * 1.0e12 for name, value in pattern.findall(text)}


def check_models(
    results: dict[str, tuple[float, float, float]], heat_capacities: dict[str, float]
) -> None:
    failures = []
    for relative_path, expected_materials in MODEL_EXPECTATIONS.items():
        actual = parse_stk_conductivities(ROOT / relative_path)
        for material, expected_or_key in expected_materials.items():
            expected = (
                results[expected_or_key]
                if isinstance(expected_or_key, str)
                else expected_or_key
            )
            if material not in actual:
                failures.append(f"{relative_path}: missing material {material}")
                continue
            for axis, (observed, target) in enumerate(zip(actual[material], expected)):
                if not math.isclose(observed, target, rel_tol=5.0e-6, abs_tol=5.0e-5):
                    failures.append(
                        f"{relative_path}:{material}[{axis}]={observed:.8g}, "
                        f"expected {target:.8g} W/(m K)"
                    )
    for relative_path, expected_materials in HEAT_CAPACITY_EXPECTATIONS.items():
        actual = parse_stk_heat_capacities(ROOT / relative_path)
        for material, expected_key in expected_materials.items():
            target = heat_capacities[expected_key]
            if material not in actual:
                failures.append(f"{relative_path}: missing heat capacity for {material}")
                continue
            observed = actual[material]
            if not math.isclose(observed, target, rel_tol=5.0e-6, abs_tol=5.0e-5):
                failures.append(
                    f"{relative_path}:{material}.Cv={observed:.8g}, "
                    f"expected {target:.8g} MJ/(m3 K)"
                )
    if failures:
        raise SystemExit("\n".join(failures))
    print(
        f"PASS: {len(MODEL_EXPECTATIONS)} model files match conductivity and "
        "non-active heat-capacity calibration."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="audit the checked-in .stk values")
    args = parser.parse_args()
    results = calculate()
    heat_capacities = calculate_heat_capacities()
    payload = {
        "conductivity_W_mK": {
            key: [round(value, 8) for value in values] for key, values in results.items()
        },
        "volumetric_heat_capacity_MJ_m3K": {
            key: round(value, 8) for key, value in heat_capacities.items()
        },
    }
    print(json.dumps(payload, indent=2))
    if args.check:
        check_models(results, heat_capacities)


if __name__ == "__main__":
    main()
