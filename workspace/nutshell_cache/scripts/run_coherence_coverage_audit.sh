#!/usr/bin/env bash
set -euo pipefail

jobs="${1:-2}"
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
source scripts/env.sh

coverage_flags=(--coverage-line --coverage-branch --coverage-toggle --coverage-fsm)
out_root="reports/coherence/block_coverage"
mkdir -p "$out_root"

run_top() {
  local name="$1"
  local top="$2"
  local filelist="$3"
  local mdir="$out_root/${name}_obj"
  local build_log="$out_root/${name}_build.log"
  local run_log="$out_root/${name}_run.log"
  local dat="$out_root/${name}.dat"

  rm -rf "$mdir"
  rm -f "$dat"
  mkdir -p "$mdir"
  echo "=== Coverage audit: ${name} (${top}) ==="
  if ! (cd rtl && verilator --binary --timing --assert "${coverage_flags[@]}" \
      -j "$jobs" -CFLAGS -O0 -Wall -Wno-fatal -Wno-BLKSEQ \
      --unroll-count 10000 --top-module "$top" --Mdir "../$mdir" \
      -f "$filelist") >"$build_log" 2>&1; then
    tail -n 100 "$build_log"
    return 1
  fi
  if [[ "$name" == coherent_cache_axi_subsystem ]]; then
    # Match the normal AXI regression's fixed seed set. The testbench requires
    # measured overlapping refills; its default seed does not guarantee that.
    for seed in 6699 24301 12648430 195936478 219540062; do
      local seed_dat="$out_root/${name}_seed_${seed}.dat"
      if ! ("$mdir/V$top" "+seed=$seed" "+verilator+coverage+file+$seed_dat") \
          >"$out_root/${name}_seed_${seed}_run.log" 2>&1; then
        cat "$out_root/${name}_seed_${seed}_run.log"
        return 1
      fi
    done
    verilator_coverage --write "$dat" "$out_root"/${name}_seed_*.dat
    cat "$out_root"/${name}_seed_*_run.log >"$run_log"
  else
    if ! ("$mdir/V$top" "+verilator+coverage+file+$dat") >"$run_log" 2>&1; then
      cat "$run_log"
      return 1
    fi
  fi
  verilator_coverage --report summary,hier "$dat" >"$out_root/${name}_summary.txt"
  verilator_coverage --filter-type line --write-info "$out_root/${name}_line.info" "$dat"
  echo "PASS: ${name}; raw=$dat; summary=$out_root/${name}_summary.txt"
}

run_top coherent_cache_axi_subsystem CoherentCacheAxiSubsystem_tb \
  ../dv/blocks/coherent_cache_axi_subsystem/filelist.f
run_top directory_controller DirectoryController_tb \
  ../dv/blocks/directory_controller/filelist.f
run_top directory_mshr_bank DirectoryMshrBank_tb \
  ../dv/blocks/directory_mshr_bank/filelist.f
run_top shared_line_engine SharedLineEngine_tb \
  ../dv/blocks/shared_line_engine/filelist.f
run_top mesi_l1_controller MesiL1Controller_tb \
  ../dv/blocks/mesi_l1_controller/filelist.f
run_top shared_l2_directory_array SharedL2DirectoryArray_tb \
  ../dv/blocks/shared_l2_directory_array/filelist.f
run_top bus_blocks CacheBusBlocks_tb \
  ../dv/blocks/bus_blocks/filelist.f

echo "Independent coverage datasets are intentionally not merged: each top has a different elaboration and testcase set."
