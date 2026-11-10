  // Observe actual integrated resource occupancy and protocol producers. These
  // assertions check every sampled cycle; observed peaks are not upper proofs.
  integer freeze_peak_contexts = 0;
  integer freeze_context2_cycles = 0, freeze_context3_cycles = 0;
  integer freeze_read_checks = 0, freeze_write_checks = 0;
  logic freeze_past_reset = 1;
  always @(posedge clock) begin : freeze_protocol_observer
    integer active_count;
    if (!reset) begin
      active_count = $countones(dut.monitor_directory_active_contexts);
      if (active_count > freeze_peak_contexts) begin
        freeze_peak_contexts = active_count;
        $display("FREEZE_CONTEXT_PEAK: active=%b count=%0d", dut.monitor_directory_active_contexts, active_count);
      end
      if (dut.monitor_directory_active_contexts[2]) freeze_context2_cycles++;
      if (dut.monitor_directory_active_contexts[3]) freeze_context3_cycles++;
      if (dut.dir_grant_valid && dut.dir_grant_ready && dut.dir_grant_has_data) begin
        freeze_read_checks++;
        if (!dut.l2_line_rd_valid || !dut.l2_line_rd_ready)
          $fatal(1,"integrated data grant accepted without available L2 read port");
      end
      if (mem_wr_data_valid && mem_wr_data_ready) begin
        freeze_write_checks++;
        if (mem_wr_data_txn_id != dut.engine_txn_q ||
            mem_wr_data_beat_idx != dut.victim_expected_beat_q ||
            mem_wr_data_last != (mem_wr_data_beat_idx==7))
          $fatal(1,"internal writeback producer ID/beat/last mismatch");
      end
      if (freeze_past_reset && (dut.monitor_directory_active_contexts != 0 ||
          dut.dir_grant_commit_valid || mem_wr_data_valid || cpu_resp_valid[0] || cpu_resp_valid[1]))
        $fatal(1,"old transaction survived synchronous reset");
    end
    freeze_past_reset <= reset;
  end
  final begin
    $display("FREEZE_OBSERVATIONS: peak=%0d ctx2_cycles=%0d ctx3_cycles=%0d grant_read_checks=%0d write_producer_checks=%0d",freeze_peak_contexts,freeze_context2_cycles,freeze_context3_cycles,freeze_read_checks,freeze_write_checks);
  end
