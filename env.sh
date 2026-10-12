#!/usr/bin/env bash
# Source this file to use the project-local Python and the CentOS GCC toolset.
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    echo "Use: source ./env.sh" >&2
    exit 1
fi

_ice_env_root=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
if [[ -f /opt/rh/devtoolset-11/enable ]]; then
    source /opt/rh/devtoolset-11/enable
fi
if [[ ! -f "$_ice_env_root/.venv/bin/activate" ]]; then
    echo "Missing project Python environment: $_ice_env_root/.venv" >&2
    unset _ice_env_root
    return 1
fi
source "$_ice_env_root/.venv/bin/activate"
export PYTHONUTF8=1
# Standalone Python was built with clang; compile local extensions with GCC.
export CC="${CC:-gcc}"
export CXX="${CXX:-g++}"
unset _ice_env_root
