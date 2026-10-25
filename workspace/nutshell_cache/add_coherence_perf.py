#!/usr/bin/env python3
"""Add an isolated performance mode to the existing CoherentCacheSubsystem_tb.sv.

Usage from workspace/nutshell_cache:
    python3 /path/to/add_coherence_perf.py
    make coherence_build
    reports/coherence/obj_dir/VCoherentCacheSubsystem_tb +perf_only

Makes a backup; refuses if expected source anchors are missing. The inserted
SystemVerilog is compiled by the regular coherence build before use.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil

ANCHOR_MON = "  always #5 clock = ~clock;"
ANCHOR_TASK = "  initial begin\n    logic [63:0] ignored;"
ANCHOR_BOOT = "    reset = 1'b0;\n\n    line_addr = 32'h0000_1000;"
MARK = "// === COHERENCE PERF ADDON (generated) ==="

MONITOR = r'''  // === COHERENCE PERF ADDON (generated) ===
  longint unsigned perf_start_cycle [0:1];
  longint unsigned perf_completed [0:1];
  longint unsigned perf_latency_sum [0:1];
  longint unsigned perf_mem_reads;
  longint unsigned perf_mem_writes;
  longint unsigned perf_directory_reqs;
  longint unsigned perf_snoops;
  longint unsigned perf_req_ready_stall_cycles;

  // CPU request timestamp to response timestamp, measured at handshakes.
  // At most one CPU request is outstanding per core in this RTL.
  always_ff @(posedge clock) begin : coherence_perf_counters
    if (reset) begin
      for (int c = 0; c < 2; c++) begin
        perf_start_cycle[c] <= 0;
        perf_completed[c] <= 0;
        perf_latency_sum[c] <= 0;
      end
      perf_mem_reads <= 0;
      perf_mem_writes <= 0;
      perf_directory_reqs <= 0;
      perf_snoops <= 0;
      perf_req_ready_stall_cycles <= 0;
    end else begin
      for (int c = 0; c < 2; c++) begin
        if (cpu_req_valid[c] && cpu_req_ready[c])
          perf_start_cycle[c] <= 64'(cycle_count);
        if (cpu_resp_valid[c] && cpu_resp_ready[c]) begin
          perf_completed[c] <= perf_completed[c] + 1;
          perf_latency_sum[c] <= perf_latency_sum[c] +
                                 (64'(cycle_count) - perf_start_cycle[c]);
        end
      end
      if (mem_rd_req_valid && mem_rd_req_ready)
        perf_mem_reads <= perf_mem_reads + 1;
      if (mem_wr_req_valid && mem_wr_req_ready)
        perf_mem_writes <= perf_mem_writes + 1;
      if (dut.cluster_dir_req_valid && dut.dir_req_ready)
        perf_directory_reqs <= perf_directory_reqs + 1;
      perf_snoops <= perf_snoops +
          ((dut.snoop_valid_core[0] && dut.snoop_ready_core[0]) ? 1 : 0) +
          ((dut.snoop_valid_core[1] && dut.snoop_ready_core[1]) ? 1 : 0);
      perf_req_ready_stall_cycles <= perf_req_ready_stall_cycles +
          ((cpu_req_valid[0] && !cpu_req_ready[0]) ? 1 : 0) +
          ((cpu_req_valid[1] && !cpu_req_ready[1]) ? 1 : 0);
    end
  end
'''

TASKS = r'''  // Isolated benchmark mode using the EXISTING memory model and
  // scoreboard-checked cpu_access/cpu_pair_access transaction drivers.
  longint unsigned perf_cyc0;
  longint unsigned perf_done0 [0:1];
  longint unsigned perf_lat0 [0:1];
  longint unsigned perf_mrd0, perf_mwr0, perf_dir0, perf_snp0;
  longint unsigned perf_req_stall0;

  task automatic perf_begin;
    @(negedge clock);
    perf_cyc0 = 64'(cycle_count);
    for (int c = 0; c < 2; c++) begin
      perf_done0[c] = perf_completed[c];
      perf_lat0[c] = perf_latency_sum[c];
    end
    perf_mrd0 = perf_mem_reads;
    perf_mwr0 = perf_mem_writes;
    perf_dir0 = perf_directory_reqs;
    perf_snp0 = perf_snoops;
    perf_req_stall0 = perf_req_ready_stall_cycles;
  endtask

  task automatic perf_end(input string name);
    longint unsigned count, latency, window_cycles;
    @(negedge clock);
    count = (perf_completed[0] - perf_done0[0]) +
            (perf_completed[1] - perf_done0[1]);
    latency = (perf_latency_sum[0] - perf_lat0[0]) +
              (perf_latency_sum[1] - perf_lat0[1]);
    window_cycles = 64'(cycle_count) - perf_cyc0;
    if (count == 0) $fatal(1, "benchmark phase %s had no responses", name);
    $display("COHERENCE_PERF,name=%s,ops=%0d,window_cycles=%0d,cycles_per_op=%0f,mean_req_to_resp_cycles=%0f,request_ready_stall_cycles=%0d,mem_read_lines=%0d,mem_write_lines=%0d,dir_requests=%0d,snoops=%0d",
             name, count, window_cycles,
             real'(window_cycles) / real'(count),
             real'(latency) / real'(count),
             perf_req_ready_stall_cycles - perf_req_stall0,
             perf_mem_reads - perf_mrd0, perf_mem_writes - perf_mwr0,
             perf_directory_reqs - perf_dir0, perf_snoops - perf_snp0);
  endtask

  task automatic run_coherence_perf;
    logic [63:0] rdata0, rdata1;
    logic last_source;
    begin
      $display("COHERENCE_PERF_START,clock_period_ns=10,stall_mode=off");
      // Warm local hits. No coherence requests should be needed in phase.
      cpu_access(0, 32'h0010_1000, 1'b0, 8'h00, '0, rdata0);
      perf_begin();
      for (int i = 0; i < 64; i++)
        cpu_access(0, 32'h0010_1000, 1'b0, 8'h00, '0, rdata0);
      perf_end("warm_l1_local_reads");

      // True cold reads: every address belongs to a different cache line.
      perf_begin();
      for (int i = 0; i < 32; i++)
        cpu_access(0, 32'h0011_0000 + 64*i, 1'b0, 8'h00, '0, rdata0);
      perf_end("cold_l1_l2_memory_reads");

      // Set up modified lines on Core0; measure only remote GetS on Core1.
      for (int i = 0; i < 16; i++)
        cpu_access(0, 32'h0012_0000 + 64*i, 1'b1, 8'hFF,
                   64'hABCD_1234_0000_0000 + 64'(i), rdata0);
      perf_begin();
      for (int i = 0; i < 16; i++)
        cpu_access(1, 32'h0012_0000 + 64*i, 1'b0, 8'h00, '0, rdata1);
      perf_end("remote_GetS_from_M_owner");

      // Every line is now shared; Core1 upgrades to M and invalidates Core0.
      perf_begin();
      for (int i = 0; i < 16; i++)
        cpu_access(1, 32'h0012_0000 + 64*i, 1'b1, 8'hFF,
                   64'hDEAD_BEEF_0000_0000 + 64'(i), rdata1);
      perf_end("shared_to_modified_upgrade");

      // Two independent hot lines, issued at the same time by both agents.
      cpu_access(0, 32'h0013_0000, 1'b0, 8'h00, '0, rdata0);
      cpu_access(1, 32'h0013_2000, 1'b0, 8'h00, '0, rdata1);
      perf_begin();
      for (int i = 0; i < 32; i++)
        cpu_pair_access(32'h0013_0000, 1'b0, 8'h00, '0,
                        32'h0013_2000, 1'b0, 8'h00, '0,
                        rdata0, rdata1, last_source);
      perf_end("dual_core_independent_hot_reads");

      // Force >8 tags into one L2 set; this stresses inclusive eviction.
      // L2 stride = 512 sets * 64 bytes = 32768 bytes.
      perf_begin();
      for (int i = 0; i < 9; i++)
        cpu_access(0, 32'h0020_0000 + (i*32768), 1'b1, 8'hFF,
                   64'h2026_0000_0000_0000 + 64'(i), rdata0);
      perf_end("nine_line_same_l2_set_dirty_conflicts");
      $display("COHERENCE_PERF_END");
    end
  endtask

'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tb", type=Path,
                    default=Path("tests/subsystem/rtl/CoherentCacheSubsystem_tb.sv"))
    args = ap.parse_args()
    tb = args.tb
    s = tb.read_text(encoding="utf-8")
    if MARK in s:
        print("Perf addon already present; no changes made.")
        return
    for anchor in (ANCHOR_MON, ANCHOR_TASK, ANCHOR_BOOT):
        if s.count(anchor) != 1:
            raise SystemExit(f"Expected exactly one anchor ({anchor[:50]!r}), got {s.count(anchor)}. File not changed.")
    backup = tb.with_suffix(tb.suffix + ".before_perf.bak")
    if backup.exists():
        raise SystemExit(f"Backup already exists: {backup}. File not changed.")
    shutil.copy2(tb, backup)
    s = s.replace(ANCHOR_MON, MONITOR + "\n" + ANCHOR_MON)
    s = s.replace(ANCHOR_TASK, TASKS + ANCHOR_TASK)
    s = s.replace(
        ANCHOR_BOOT,
        "    reset = 1'b0;\n\n"
        "    if ($test$plusargs(\"perf_only\")) begin\n"
        "      run_coherence_perf();\n"
        "      $finish;\n"
        "    end\n\n"
        "    line_addr = 32'h0000_1000;"
    )
    tb.write_text(s, encoding="utf-8")
    print(f"Patched: {tb}\nBackup:  {backup}\nRun: make coherence_build && reports/coherence/obj_dir/VCoherentCacheSubsystem_tb +perf_only")


if __name__ == "__main__":
    main()
