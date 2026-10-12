#!/usr/bin/env bash

set -euo pipefail

test_dir=$(cd "$(dirname "$0")" && pwd)
repo_dir=$(cd "$test_dir/../.." && pwd)
output_root="$test_dir/outputs/standard_bundle"
runner="$repo_dir/utils/thermal/run_steady.py"

# The stack also writes inspection outputs to this directory.
mkdir -p "$test_dir/outputs/hotspot_comparison"

python3 "$runner" \
  --stack "$test_dir/example_steady.stk" \
  --output-dir "$output_root" \
  >"$test_dir/outputs/standard_bundle.log"

python3 "$runner" \
  --stack "$test_dir/example_steady.stk" \
  --output-dir "$output_root" \
  --phase decode \
  >"$test_dir/outputs/standard_bundle_decode.log"

results="$output_root/thermal/results"

for path in \
  "$results/temperature.steady" \
  "$results/temperature_grid.steady" \
  "$results/temperature_steady.tsv" \
  "$results/hotspot_steady.log" \
  "$results/thermal_summary.json" \
  "$results/temperature_decode.steady" \
  "$results/temperature_grid_decode.steady" \
  "$results/temperature_steady_decode.tsv" \
  "$results/hotspot_steady_decode.log" \
  "$results/thermal_summary_decode.json"; do
  if [[ ! -s "$path" ]]; then
    echo "Expected standardized steady output was not generated: $path" >&2
    exit 1
  fi
done

if [[ $(find "$results/heatmaps" -maxdepth 1 -name 'steady_layer_*.png' | wc -l) -ne 8 ]]; then
  echo "Expected four default and four decode heatmaps" >&2
  exit 1
fi

if [[ $(find "$results/heatmaps" -maxdepth 1 -name 'steady_layer_*.svg' | wc -l) -ne 8 ]]; then
  echo "Expected four default and four decode SVG heatmaps" >&2
  exit 1
fi

if find "$results/heatmaps" -type f \( -name '*.pdf' -o -name '*.tiff' \) -print -quit | grep -q .; then
  echo "Steady heatmaps must be limited to PNG and SVG" >&2
  exit 1
fi

python3 - "$results/thermal_summary.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    summary = json.load(handle)

assert summary["simulator"] == "3D-ICE"
assert summary["analysis"] == "steady"
assert summary["grid_rows"] == 64
assert summary["grid_cols"] == 64
assert summary["grid_layer_count"] == 4
assert summary["node_count"] == 23
assert len(summary["heatmaps"]) == 4
PY

echo "3D-ICE standardized steady-result validation passed"
