# Standardized steady thermal results

`run_steady.py` runs a steady 3D-ICE stack and creates a HotSpot-style result
bundle below `OUTPUT_DIR/thermal/results/`. File content is generated from
3D-ICE and is not presented as HotSpot data.

```bash
python3 utils/thermal/run_steady.py \
  --stack test/example3_dt/example_steady.stk \
  --output-dir trace_output
```

Default outputs:

```text
trace_output/thermal/results/
├── temperature.steady
├── temperature_grid.steady
├── temperature_steady.tsv
├── hotspot_steady.log
├── thermal_summary.json
└── heatmaps/
    ├── steady_layer_*.png
    └── steady_layer_*.svg
```

The compatibility log filename remains `hotspot_steady.log`, but its first line
and summary identify the simulator as 3D-ICE. `temperature.steady` contains
floorplan-element temperatures for powered layers and one average-temperature
node for passive layers. `temperature_grid.steady` contains every physical
layer and every thermal cell.

Use `--phase prefill` or `--phase decode` to insert a suffix before each file
extension. Use `--grid-rows` and `--grid-cols` for a non-square uniform grid.
Each steady heatmap is exported as PNG and editable SVG; PDF and TIFF are not
generated.
