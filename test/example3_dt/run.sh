#!/usr/bin/env bash

set -euo pipefail

test_dir=$(cd "$(dirname "$0")" && pwd)
repo_dir=$(cd "$test_dir/../.." && pwd)
server="$repo_dir/bin/3D-ICE-Server"
plotter="$repo_dir/utils/plot/plot_temperature_map.py"
output_dir="$test_dir/outputs"

if [[ ! -x "$server" ]]; then
  echo "3D-ICE-Server is not built; run 'make' in $repo_dir first" >&2
  exit 1
fi

mkdir -p "$output_dir/fixed" "$output_dir/dt"

cd "$test_dir"

echo "[1/4] Running fixed-slot 3D-ICE simulation..."
"$server" example.stk \
  --power-trace example.fixed.ptrace \
  --output-dir "$output_dir/fixed" \
  2>&1 | tee "$output_dir/fixed/run.log"

echo "[2/4] Running variable-dt 3D-ICE simulation..."
"$server" example.stk \
  --power-trace example.ptrace \
  --output-dir "$output_dir/dt" \
  2>&1 | tee "$output_dir/dt/run.log"

echo "[3/4] Validating timestamps and module temperatures..."
fixed_times=$(awk '!/^%/ && NF {print $1}' \
  "$output_dir/fixed/bottom_temperature.txt")
dt_times=$(awk '!/^%/ && NF {print $1}' \
  "$output_dir/dt/bottom_temperature.txt")

if [[ "$fixed_times" != $'0.010\n0.020' ]]; then
  echo "Unexpected fixed-trace timestamps:" >&2
  echo "$fixed_times" >&2
  exit 1
fi

if [[ "$dt_times" != $'0.005\n0.020' ]]; then
  echo "Unexpected variable-dt timestamps:" >&2
  echo "$dt_times" >&2
  exit 1
fi

for file in bottom_temperature.txt top_temperature.txt; do
  fixed_final=$(awk '!/^%/ && NF {
    line=""; for (i=2; i<=NF; i++) line=line sprintf("%.6f ", $i)
  } END {print line}' "$output_dir/fixed/$file")
  dt_final=$(awk '!/^%/ && NF {
    line=""; for (i=2; i<=NF; i++) line=line sprintf("%.6f ", $i)
  } END {print line}' "$output_dir/dt/$file")

  if [[ "$fixed_final" == "$dt_final" ]]; then
    echo "Expected final fixed and variable-dt temperatures to differ for $file" >&2
    exit 1
  fi
done

grep -q 'End of power trace after 2 slots' "$output_dir/fixed/run.log"
grep -q 'End of power trace after 2 slots' "$output_dir/dt/run.log"

export MPLCONFIGDIR="$output_dir/.matplotlib"
mkdir -p "$MPLCONFIGDIR"

echo "[4/4] Rendering and validating fixed/variable grid heatmaps..."
python3 "$plotter" \
  --floorplan floorplan2.flp \
  --temperature-map "$output_dir/fixed/top_tmap.txt" \
  --time-source "$output_dir/fixed/top_temperature.txt" \
  --label "Fixed slot" \
  --temperature-map "$output_dir/dt/top_tmap.txt" \
  --time-source "$output_dir/dt/top_temperature.txt" \
  --label "Variable dt" \
  --output "$output_dir/top_temperature_comparison" \
  --title "Top-die temperature at the final trace time"

python3 "$plotter" \
  --floorplan floorplan2.flp \
  --temperature-map "$output_dir/dt/top_tmap.txt" \
  --time-source "$output_dir/dt/top_temperature.txt" \
  --label "Variable dt" \
  --output "$output_dir/dt/top_temperature_final"

rm -f "$output_dir/dt/top_temperature.gif"

for figure in \
  "$output_dir/top_temperature_comparison.png" \
  "$output_dir/top_temperature_comparison.svg" \
  "$output_dir/dt/top_temperature_final.png" \
  "$output_dir/dt/top_temperature_final.svg"; do
  if [[ ! -s "$figure" ]]; then
    echo "Expected plot was not generated: $figure" >&2
    exit 1
  fi
done

for stale_figure in \
  "$output_dir/top_temperature_comparison.pdf" \
  "$output_dir/top_temperature_comparison.tiff" \
  "$output_dir/dt/top_temperature_final.pdf" \
  "$output_dir/dt/top_temperature_final.tiff"; do
  if [[ -e "$stale_figure" ]]; then
    echo "Unexpected stale plotting output: $stale_figure" >&2
    exit 1
  fi
done

echo "3D-ICE example3 variable-dt validation passed"
echo "Results: $output_dir"
