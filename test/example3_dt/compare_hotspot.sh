#!/usr/bin/env bash

set -euo pipefail

test_dir=$(cd "$(dirname "$0")" && pwd)
repo_dir=$(cd "$test_dir/../.." && pwd)
hotspot_dir=${1:-"$repo_dir/../HotSpot"}
output_dir="$test_dir/outputs/hotspot_comparison"
emulator="$repo_dir/bin/3D-ICE-Emulator"

hotspot_trace="$hotspot_dir/examples/example3/outputs/example.grid.ttrace"
hotspot_steady="$hotspot_dir/examples/example3/outputs/example_layer2.grid.steady"
if [[ ! -f "$hotspot_trace" ]]; then
  echo "HotSpot example3 grid trace not found: $hotspot_trace" >&2
  echo "Run HotSpot examples/example3/run.sh first or pass the HotSpot root directory." >&2
  exit 1
fi

if [[ ! -f "$hotspot_steady" ]]; then
  echo "HotSpot example3 layer-2 steady grid not found: $hotspot_steady" >&2
  echo "Run HotSpot examples/example3/run.sh first." >&2
  exit 1
fi

if [[ ! -f "$test_dir/outputs/fixed/top_tmap.txt" ]]; then
  bash "$test_dir/run.sh"
fi

mkdir -p "$output_dir"
export MPLCONFIGDIR="$test_dir/outputs/.matplotlib"

if [[ ! -x "$emulator" ]]; then
  echo "3D-ICE-Emulator is not built; run 'make' in $repo_dir first" >&2
  exit 1
fi

(cd "$test_dir" && "$emulator" example_steady.stk >"$output_dir/three_dice_steady.log" 2>&1)

python3 "$repo_dir/utils/plot/compare_hotspot_3dice.py" \
  --hotspot-grid-steady "$hotspot_steady" \
  --hotspot-origin upper \
  --three-dice-map "$output_dir/three_dice_layer2.grid.steady" \
  --floorplan "$test_dir/floorplan2.flp" \
  --output "$output_dir/top_layer_steady_comparison"

for comparison in "0.01:t001" "0.02:t002"; do
  time=${comparison%%:*}
  tag=${comparison##*:}

  python3 "$repo_dir/utils/plot/compare_hotspot_3dice.py" \
    --hotspot-grid-trace "$hotspot_trace" \
    --hotspot-layer 2 \
    --hotspot-origin upper \
    --three-dice-map "$test_dir/outputs/fixed/top_tmap.txt" \
    --three-dice-time-source "$test_dir/outputs/fixed/top_temperature.txt" \
    --floorplan "$test_dir/floorplan2.flp" \
    --time "$time" \
    --output "$output_dir/top_layer_${tag}_comparison"
done

for result in \
  "$output_dir/top_layer_t002_comparison.png" \
  "$output_dir/top_layer_t002_comparison.svg" \
  "$output_dir/top_layer_t002_comparison_metrics.json" \
  "$output_dir/top_layer_t001_comparison.png" \
  "$output_dir/top_layer_t001_comparison.svg" \
  "$output_dir/top_layer_t001_comparison_metrics.json" \
  "$output_dir/top_layer_steady_comparison.png" \
  "$output_dir/top_layer_steady_comparison.svg" \
  "$output_dir/top_layer_steady_comparison_metrics.json"; do
  if [[ ! -s "$result" ]]; then
    echo "Expected comparison output was not generated: $result" >&2
    exit 1
  fi
done

if find "$output_dir" -type f \( -name '*.pdf' -o -name '*.tiff' \) -print -quit | grep -q .; then
  echo "Comparison figures must be limited to PNG and SVG" >&2
  exit 1
fi

echo "HotSpot/3D-ICE example3 comparison passed"
