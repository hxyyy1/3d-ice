# Example 3 variable-dt validation

This test adapts HotSpot's `tests/example3_dt` inputs to 3D-ICE.

- `floorplan1.flp` is the bottom die with `Unit1`, `Unit2`, and `Unit3`.
- `floorplan2.flp` is the top EV6-like die with 18 floorplan elements.
- Dimensions were converted from metres in HotSpot to micrometres in 3D-ICE.
- The 16 mm × 16 mm dies use 250 µm cells, matching HotSpot's 64×64 grid.
- `example.fixed.ptrace` uses the stack's fixed `slot = 0.01 s` for both rows.
- `example.ptrace` uses `dt = 0.005 s` and `dt = 0.015 s`, so its timestamps
  are `0.005 s` and `0.020 s` and each row performs one thermal solve.

The trace columns are already in 3D-ICE power order: the three bottom-die
elements first, followed by the 18 top-die elements.

Build 3D-ICE and run the test from any directory:

```bash
make
bash test/example3_dt/run.sh
```

or through the test Makefile:

```bash
make -C test example3dttest
```

Successful validation prints:

```text
3D-ICE example3 variable-dt validation passed
```

Generated files are written below `test/example3_dt/outputs/`. The script
checks the fixed timestamps (`0.010`, `0.020`), variable timestamps (`0.005`,
`0.020`), natural EOF termination, and that both temperature outputs change
when the non-uniform durations are used.

The example also writes per-cell `Tmap` data and creates HotSpot-like plots:

- `outputs/top_temperature_comparison.{png,svg}` compares the fixed and
  variable-dt top-die fields at `t = 0.020 s` using one shared color scale.
- `outputs/dt/top_temperature_final.{png,svg}` is the final variable-dt
  top-die map.

The plots combine the grid temperature field with floorplan boundaries, block
labels, a temperature scale, and the maximum-temperature location. Their
default `hot_r` palette matches HotSpot's Python thermal-map configuration.

## Compare with HotSpot example3

If the HotSpot repository is next to this repository and its `example3` output
has been generated, run:

```bash
make -C test hotspotcompare
```

Alternatively, pass the HotSpot root directory explicitly:

```bash
bash test/example3_dt/compare_hotspot.sh /path/to/HotSpot
```

This compares all 4096 cells of HotSpot layer 2 with the 3D-ICE top active
layer at steady state, `t = 0.01 s`, and `t = 0.02 s`. HotSpot row 0 is vertically flipped to the physical
bottom-origin convention used by 3D-ICE; no interpolation, filtering, or
downsampling is performed. Outputs include a three-panel temperature/difference
figure and a JSON file containing bias, MAE, RMSE, maximum error, and Pearson
correlation.

The replicated model aligns the 64×64 geometry, silicon/TIM layers, material
properties, power trace, 318.15 K initial/ambient temperature, and total
convection conductance. HotSpot's additional dynamic spreader/sink package
layers are not represented by the standard 3D-ICE heat-sink boundary, so local
hotspot temperatures are not expected to be numerically identical.

For the checked outputs, all 4096 cells are included:

| State | Pearson r | Mean bias (3D-ICE − HotSpot) | RMSE |
|---|---:|---:|---:|
| transient, 0.01 s | 0.995 | +0.05 K | 0.96 K |
| transient, 0.02 s | 0.983 | +0.45 K | 1.78 K |
| steady state | 0.873 | −19.00 K | 19.50 K |

Thus the short-time transient spatial pattern is highly consistent, while the
steady-state fields are not numerically equivalent under the simplified
3D-ICE heat-sink boundary. The JSON reports retain the unrounded metrics.
