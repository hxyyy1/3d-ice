# 3D-ICE

[![3D-ICE](https://www.epfl.ch/labs/esl/wp-content/uploads/2018/12/3d_ice.bmp)](https://esl.epfl.ch/3d-ice)


3D-ICE stands for 3D Interlayer Cooling Emulator. It is a Linux-based Thermal Emulator Library written in C, which can perform transient thermal analyses of vertically stacked 3D integrated circuits with inter-tier Microchannel Liquid Cooling. The latest version, namely 3D-ICE 4.0, adds support for heterogeneous and anisotropic floorplans (including GDS layouts), customizable non-uniform thermal modeling, different heat sink models, and parallel acceleration.

To get more information about 3D-ICE, and how to use and install it, please refer to the [3D-ICE_User_Guide](doc/3D-ICE-User_Guide.pdf) in the doc folder. It helps you get started with 3D-ICE and serves as a quick reference later on. Click [here](https://www.epfl.ch/labs/esl/research/open-source-tools/3d-ice/3d-ice-documentation/) if you want to know more about the modeling theory aspects of 3D-ICE.

## Local environment on CentOS 7

A project-local Python environment is installed in `.venv`, backed by the
standalone Python in `.local/python`. Enable it and the installed GCC 11 toolset
in each new Bash terminal:

```bash
source ./env.sh
python3 --version
gcc --version
```

The Python packages are listed in `requirements.txt`. The versions validated on
this host are recorded in `requirements-centos7.lock`. To restore the packages
after creating and activating a Python 3.11 virtual environment, use compatible
binary wheels and build `gdspy` with GCC:

```bash
python3 -m pip install --only-binary=:all: -c requirements-centos7.lock \
  numpy matplotlib shapely rtree wheel setuptools
python3 -m pip install --no-build-isolation -c requirements-centos7.lock gdspy
```

The local environment directories are ignored by Git and are not included in a clone.

After moving compiled artifacts from another machine, rebuild them on this host
to match its glibc. With the local SuperLU sources already extracted:

```bash
make -B -C superlu_mt-4.0.0/SRC
make -B -C flex
make -B -C bison
make -B -C sources
make -C lib
make -B -C bin
make -C test example3dttest steadyresultstest
```

OpenBLAS development headers and libraries must be installed. `makefile.def`
recognizes the CentOS `/usr/include/openblas` header directory; custom locations
can be supplied with `OPENBLAS_CFLAGS` and `OPENBLAS_LIBS` make variables.
These core examples do not require OpenModelica or the optional FMI/Python
heat-sink loaders. The top-level `make test` also builds those optional plugins.

## Power traces with variable slot durations

The traditional power trace format still uses the fixed `slot` duration from
the stack file. A trace can optionally provide a header, but its columns must
remain in 3D-ICE floorplan order (bottom die to top die):

```text
Core0 Cache0
10.0  3.0
12.0  4.2
```

To give each power row a different duration, make `dt` the first header field
and add the duration in seconds as the first value of every data row:

```text
dt     Core0 Cache0
0.005  10.0  3.0
0.015  12.0  4.2
```

Every `dt` must be finite and greater than zero. When `dt` is present, each
trace row is solved exactly once with `dt` used directly as that transient
step. If `dt` changes, 3D-ICE rebuilds and factorizes the time-dependent system
matrix before the solve; adjacent rows with the same `dt` reuse the existing
factorization. Trace headers are informational and must contain exactly one
label per floorplan element.

When `dt` is absent, the original fixed `step`/`slot` path is used unchanged:
each power row remains active for `slot / step` solver steps.

The stack file still requires the existing transient `step`/`slot` declaration
for configuration compatibility, but those values no longer subdivide rows in
a `dt` trace. Changing `dt` is currently unsupported with a pluggable heat-sink
model because its external state is initialized with a fixed step duration.

A finite trace can be run directly; reaching end-of-file ends the simulation:

```bash
bin/3D-ICE-Server model.stk --power-trace power.ptrace
```

To place every relative path from the stack `output:` section below one
directory, use `--output-dir`:

```bash
bin/3D-ICE-Server model.stk \
  --power-trace power.ptrace \
  --output-dir results/run-01
```

The directory and any required subdirectories are created automatically.
Relative output paths preserve their structure below this directory; absolute
paths in the stack file remain unchanged. Without `--output-dir`, output path
handling is identical to the original behavior. Socket mode accepts the same
option after the port number.

Variable-duration traces are also supported by `3D-ICE-Client` when used with
an updated `3D-ICE-Server`:

```bash
bin/3D-ICE-Client 127.0.0.1 10000 power.ptrace
```

`--follow` and the optional all-minus-one sentinel mode remain available for
streaming traces. Headerless numeric traces remain backward compatible.

A complete two-die fixed-versus-variable trace example adapted from HotSpot is
available in [`test/example3_dt`](test/example3_dt/README.md). Run it with:

```bash
make -C test example3dttest
```

To compare the replicated 64×64 top active layer against a sibling HotSpot
`example3` result at the same timestamp, run:

```bash
make -C test hotspotcompare
```

This exports aligned HotSpot, 3D-ICE, and signed-difference panels plus a JSON
report containing all-cell bias, MAE, RMSE, maximum error, and correlation.

## Standardized steady-result bundle

Run a steady stack and create a HotSpot-style output bundle below
`OUTPUT_DIR/thermal/results/`:

```bash
python3 utils/thermal/run_steady.py \
  --stack test/example3_dt/example_steady.stk \
  --output-dir trace_output
```

The bundle contains `temperature.steady`, `temperature_grid.steady`,
`temperature_steady.tsv`, `hotspot_steady.log`, `thermal_summary.json`, and
`heatmaps/steady_layer_*.{png,svg}`. Raw files contain 3D-ICE results; the compatibility
log name does not imply that HotSpot was executed. `--phase prefill|decode`
adds the corresponding filename suffix.

The example automatically generates HotSpot-like thermal maps. The reusable
Python plotter accepts one result or multiple comparison panels and exports
PNG and editable SVG files:

```bash
python3 utils/plot/plot_temperature_map.py \
  --floorplan test/example3_dt/floorplan2.flp \
  --temperature-map test/example3_dt/outputs/dt/top_tmap.txt \
  --time-source test/example3_dt/outputs/dt/top_temperature.txt \
  --label "Variable dt" \
  --output test/example3_dt/outputs/dt/top_temperature_final
```

We are constantly looking for your feedback and comments in our strive to improve 3D-ICE. Please send your emails to 3d-ice@listes.epfl.ch. You must subscribe to this mailing list in order to be able to communicate with us and also receive notifications about new releases and updates on new patches, bugs, etc. Notifications will be kept as limited and as brief as possible and THERE WILL BE NO SPAMMING of your mailbox. In addition, this mailing list will serve as a forum where you can interact with other users of 3D-ICE.

## Citation
> ***IMPORTANT INFORMATION:*** Any usage of 3D-ICE for research, commercial or other purposes should be properly acknowledged in the resulting products or publications. Specifically, publications 1, 2, 3, and 4 below should be appropriately cited.

1. K. Zhu, D. Huang, L. Costero and D. Atienza, 3D-ICE 4.0: Accurate and efficient thermal modeling for 2.5D/3D heterogeneous chiplet systems, 2026 Design, Automation and Test in Europe Conference (DATE), Verona, Italy, 2026.

2. F. Terraneo, A. Leva, W. Fornaciari, M. Zapater, D. Atienza, 3D-ICE 3.0: efficient nonlinear MPSoC thermal simulation with pluggable heat sink models, Transactions on Computer-Aided Design of Integrated Circuits and Systems Volume 40 pp. 1-14, 2021-04-19

3. A. Sridhar, A. Vincenzi, D. Atienza and T. Brunschwiler, 3D-ICE: A Compact Thermal Model for Early-Stage Design of Liquid-Cooled ICs, IEEE Transactions on Computers, vol. 63, no. 10, pp. 2576-2589, Oct. 2014, doi: 10.1109/TC.2013.127

4. A. Sridhar, A. Vincenzi, M. Ruggiero, T. Brunschwiler and D. Atienza, 3D-ICE: Fast compact transient thermal modeling for 3D ICs with inter-tier liquid cooling, 2010 IEEE/ACM International Conference on Computer-Aided Design (ICCAD), San Jose, CA, 2010, pp. 463-470, doi: 10.1109/ICCAD.2010.5653749

## License and copyright                         
                                                                             
3D-ICE is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License or any later version.                                  
                                       
3D-ICE is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.                                                       
                                                                             
You should have received a copy of the GNU General Public License along with 3D-ICE. If not, see <http://www.gnu.org/licenses/>.               
                                                                             
                             Copyright (C) 2021                             
    Embedded Systems Laboratory - Ecole Polytechnique Federale de Lausanne   
                             All Rights Reserved.                            
                                                                             
    Authors:    Arvind Sridhar              Alessandro Vincenzi                   
                Giseong Bak                 Martino Ruggiero                      
                Thomas Brunschwiler         Eder Zulian                           
                Federico Terraneo           Darong Huang                          
                Kai Zhu                     Luis Costero               
                Marina Zapater              David Atienza                                                     
                                                                             
    For any comment, suggestion or request  about 3D-ICE, please  register and 
    write to the mailing list (see http://listes.epfl.ch/doc.cgi?liste=3d-ice) 
    Any usage  of 3D-ICE  for research,  commercial or other  purposes must be 
    properly acknowledged in the resulting products or publications.           
                                                                                
    EPFL-STI-IEL-ESL                     Mail : 3d-ice@listes.epfl.ch          
    Batiment ELG, ELG 130                       (SUBSCRIPTION IS NECESSARY)    
    Station 11                                                                 
    1015 Lausanne, Switzerland           Url  : https://esl.epfl.ch/3d-ice      
    

 


## Release history:
    November 19, 2025   Version 4.0
    January  13, 2022   Version 3.1
    February 10, 2021   Version 3.0
    June 1, 2019        Version 2.2.8
    October 25, 2018    Version 2.2.7
    August 2, 2016      Version 2.2.6
    March 25, 2013      Varsion 2.2.5
    February 5, 2013    Version 2.2.4
    September 20, 2012  Version 2.2.3
    August 13, 2012     Version 2.2.2
    July 31, 2012       Version 2.2.1
    July 24, 2012       Version 2.2
    March 23, 2012      Version 2.1
    December 7, 2011    Version 2.0
    July 11, 2011       Version 1.0.3
    June 6, 2011        Version 1.0.2
    October 7, 2010     Version 1.0.1
    September 28, 2010  Version 1.0

## Matrix ownership and variable-step cleanup

`system_matrix_build` allocates A, permutation arrays, and statistics. The
first `pdgstrf` call allocates L/U; their SCP/NCP Stores own those arrays.
Destroying or replacing factors uses `Destroy_SuperNode_SCP` and
`Destroy_CompCol_NCP`. A and its permuted wrapper share data and continue
using their distinct wrapper-only destruction paths. Failed construction
resets the matrix; destruction is safe before factorization and on retry.
The timestep, power trace, temperature vector, thermal coefficients, ordering
policy, and numerical solver are unchanged.

The bundled dependency also needs
`patches/superlu_mt-4.0.0-empty-ordering-cleanup.patch`, applied by
`install-superlumt.sh`. It releases the ordering column pointers for an empty
adjacency graph (e.g. a diagonal matrix). For an existing unpatched checkout,
apply the patch from inside `superlu_mt-4.0.0`, rebuild `SRC`, then relink the
3D-ICE binaries. Do not add a second free of `map_in_sup`: `ParallelFinalize`
already frees that map.

Run the allocator-accounting regression (single thread, with allocation
failure injection, singular-factor cleanup/retry, and refact=YES coverage):

```bash
source ./env.sh
make -C test matrixcleanuptest
```

`test/ThermalCleanupRegression.c` can be linked separately against baseline
and repaired libraries. It writes every cell temperature as native doubles
at each slot boundary for exact comparison. Arguments are
`stack output.bin fixed|variable|steady steps [power.ptrace]`; set
`ICE_TEST_THREADS` to override its default single solver thread. Transient stacks
without embedded power values require the last argument. Steady mode should
use one step. Output locations must be explicitly chosen under Thermal's
`llm_activity_trace/thermal analysis/` for this project's experiments.

The 2026-10-11 repair evidence and original binaries are retained in
`../Thermal/llm_activity_trace/thermal analysis/superlu_cleanup_20261011/`.

## Full-grid steady temperature initialization

The local Emulator supports `--temperature-state-file PATH` for steady
analysis. The local-trace Server supports `--initial-temperature-file PATH`
to restore that full native temperature vector after mesh construction and
before its first transient step. This includes passive solid and fluid cells;
the coolant inlet remains an independent boundary condition.

The versioned text format preserves native double temperatures with 17
significant digits and checks cell count, geometry/order signature, contiguous
indices, finite positive Kelvin values, truncation and trailing data. Loading
does not replace the buffer aliased by SuperLU and does not silently fall back
to a scalar temperature. Both programs advertise this interface using
`--temperature-state-version` (`3DICE_TEMPERATURE_STATE_V1`). This is a
temperature initial condition, not a checkpoint of time, power queues or
external heat-sink plugin state. Socket mode and reset commands retain their
existing scalar semantics.

Validation and the focused patch are recorded in the sibling Thermal project:
`llm_activity_trace/thermal analysis/full_grid_initialization_20261011/README.md`.
