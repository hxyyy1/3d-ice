# 3D-ICE thermal-map plotting

`plot_temperature_map.py` renders HotSpot-like spatial temperature maps from
3D-ICE output. It overlays the floorplan on the cell-temperature field, marks
the hottest cell, and supports shared-scale comparison panels.

## Required simulation output

Add both module temperatures and a temperature map to the stack output section:

```text
output:
  Tflp(TOP_DIE, "top_temperature.txt", average, slot);
  Tmap(TOP_DIE, "top_tmap.txt", slot);
```

The `Tflp` file supplies the actual timestamps. The `Tmap` file supplies one
cell grid per output instant. Every grid cell is rendered without spatial
aggregation. `--grid-lines auto` draws subtle cell boundaries for grids up to
64×64; use `on` or `off` to override this behavior.

## One thermal map

```bash
python3 utils/plot/plot_temperature_map.py \
  --floorplan test/example3_dt/floorplan2.flp \
  --temperature-map test/example3_dt/outputs/dt/top_tmap.txt \
  --time-source test/example3_dt/outputs/dt/top_temperature.txt \
  --label "Variable dt" \
  --output test/example3_dt/outputs/dt/top_temperature_final
```

The default frame is the last frame. Use `--frame 0` for the first frame.

## Shared-scale comparison

Repeat `--temperature-map`, `--time-source`, and `--label` to create comparison
panels. All panels use one color scale:

```bash
python3 utils/plot/plot_temperature_map.py \
  --floorplan test/example3_dt/floorplan2.flp \
  --temperature-map test/example3_dt/outputs/fixed/top_tmap.txt \
  --time-source test/example3_dt/outputs/fixed/top_temperature.txt \
  --label "Fixed slot" \
  --temperature-map test/example3_dt/outputs/dt/top_tmap.txt \
  --time-source test/example3_dt/outputs/dt/top_temperature.txt \
  --label "Variable dt" \
  --output test/example3_dt/outputs/top_temperature_comparison
```

Static rendering exports PNG and editable SVG only. Useful
options include `--vmin`, `--vmax`, `--cmap`, `--labels auto|all|none`,
and `--grid-lines auto|on|off`. PNG output is fixed at 600 dpi. The default `hot_r` color map matches HotSpot's Python
`grid_thermal_map.py`; pass `--cmap` to override it.

## HotSpot/3D-ICE comparison

`compare_hotspot_3dice.py` aligns a HotSpot grid trace layer with a 3D-ICE
`Tmap` at a common timestamp and exports HotSpot, 3D-ICE, and signed-difference
panels. It also writes a JSON report with all-cell agreement metrics. Run
`python3 utils/plot/compare_hotspot_3dice.py --help` for its input contract.
