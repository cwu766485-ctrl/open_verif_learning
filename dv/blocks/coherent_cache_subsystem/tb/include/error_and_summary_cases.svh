    // A terminal backing-memory read error must fail-stop without returning
    // fabricated data. The external memory sends only beat 0/error/last.
    @(negedge clock);
    reset = 1'b1;
    reference_clear();
    inject_next_mem_rd_error = 1'b0;
    inject_next_mem_wr_error = 1'b0;
    repeat (3) @(posedge clock);
    @(negedge clock);
    reset = 1'b0;
    inject_next_mem_rd_error = 1'b1;
    cpu_issue_only(0, 32'h0020_0000, 1'b0, 8'h00, 64'b0);
    for (cycles = 0; cycles < 1000; cycles = cycles + 1) begin
      if (fatal_error)
        break;
      @(posedge clock);
    end
    if (!fatal_error || !memory_adapter_error || memory_adapter_protocol_error ||
        cpu_resp_valid[0] || cpu_resp_valid[1] || memory_active_q)
      $fatal(1, "terminal read error did not enter clean fail-stop handling");
    @(negedge clock);
    cpu_req_valid[1] = 1'b1;
    cpu_req_addr[1] = 32'h0020_0080;
    #1;
    if (cpu_req_ready[1])
      $fatal(1, "fatal_error did not block a new CPU request");
    cpu_req_valid[1] = 1'b0;
      coverage_mark("error.mem_read", "I", "0", "GetS+MemError", "none", "I", "memory_error", 1);
    $display("PASS: terminal memory read error suppresses success and blocks new requests");

    // After a system reset, force a dirty live L2 victim and return a failed
    // write response. The victim must remain valid and dirty because beat 7
    // alone is not a write commit.
    @(negedge clock);
    reset = 1'b1;
    reference_clear();
    inject_next_mem_rd_error = 1'b0;
    inject_next_mem_wr_error = 1'b0;
    repeat (3) @(posedge clock);
    @(negedge clock);
    reset = 1'b0;
    for (l2_line_number = 0; l2_line_number < 6; l2_line_number = l2_line_number + 1)
      expect_reference_word(0, l2_test_addr[l2_line_number] + 32'd24);
    cpu_access(1, l2_test_addr[6] + 32'd24, 1'b1, 8'hFF,
               l2_dirty_value, ignored);
    expect_reference_word(0, l2_test_addr[7] + 32'd24);
    inject_next_mem_wr_error = 1'b1;
    cpu_issue_only(0, l2_test_addr[8] + 32'd24,
                   1'b0, 8'h00, 64'b0);
    for (cycles = 0; cycles < 4000; cycles = cycles + 1) begin
      if (fatal_error)
        break;
      @(posedge clock);
    end
    failed_victim_found = 1'b0;
    failed_victim_dirty = 1'b0;
    for (integer way = 0; way < 8; way = way + 1) begin
      if (dut.l2_array.valid_array[dut.victim_addr_q[14:6]][way] &&
          dut.l2_array.tag_array[dut.victim_addr_q[14:6]][way] ==
            dut.victim_addr_q[31:15]) begin
        failed_victim_found = 1'b1;
        failed_victim_dirty = dut.l2_array.dirty_array[dut.victim_addr_q[14:6]][way];
      end
    end
    if (!fatal_error || !memory_adapter_error || memory_adapter_protocol_error ||
        cpu_resp_valid[0] || cpu_resp_valid[1] || !failed_victim_found ||
        !failed_victim_dirty || mem_wr_rsp_valid)
      $fatal(1, "failed write response check: fatal=%b mem_err=%b mem_proto=%b cpu_resp=%b%b victim_found=%b dirty=%b victim_addr=%08x rsp_valid=%b rsp_err=%b engine=%0d",
             fatal_error, memory_adapter_error, memory_adapter_protocol_error,
             cpu_resp_valid[0], cpu_resp_valid[1], failed_victim_found,
             failed_victim_dirty, dut.victim_addr_q, mem_wr_rsp_valid,
             memory_write_response_error_q, dut.engine_state_q);
      coverage_mark("error.mem_write", "M", "0", "L2_Writeback+MemError", "none", "M", "backing_memory", 8);
    $display("PASS: failed write response preserves the valid dirty L2 victim");

    if (performance_events_seen != 5'b11111)
      $fatal(1, "performance event coverage incomplete: %05b", performance_events_seen);
    if ((metadata_commit_count == 0) || (metadata_snoop_commit_count == 0))
      $fatal(1, "metadata commit monitor was not exercised: commits=%0d snoops=%0d",
             metadata_commit_count, metadata_snoop_commit_count);
    if ((benchmark_model_accept_hit_count != benchmark_rtl_hit_count) ||
        (benchmark_model_accept_miss_count != benchmark_rtl_miss_count))
      $fatal(1, "accepted hit/miss classification differs from RTL: model=%0d/%0d RTL=%0d/%0d; completed=%0d/%0d",
             benchmark_model_accept_hit_count,
             benchmark_model_accept_miss_count,
             benchmark_rtl_hit_count, benchmark_rtl_miss_count,
             benchmark_read_hit_count + benchmark_write_hit_count,
             benchmark_upgrade_count + benchmark_l1_miss_count);
    $display("PASS: hit/miss/snoop/writeback and completed-access performance events observed");
    $display("BENCH: l1_hit_count=%0d l1_hit_avg_cycles=%0d l1_miss_count=%0d l1_miss_avg_cycles=%0d read_hit_count=%0d read_hit_avg_cycles=%0d write_hit_count=%0d write_hit_avg_cycles=%0d upgrade_count=%0d upgrade_avg_cycles=%0d l1_cold_miss_count=%0d l1_cold_miss_avg_cycles=%0d cpu_req_ready_stall_cycles=%0d snoop_count=%0d snoop_avg_cycles=%0d",
             benchmark_read_hit_count + benchmark_write_hit_count,
             ((benchmark_read_hit_count + benchmark_write_hit_count) == 0) ? 0 :
               (benchmark_read_hit_cycles + benchmark_write_hit_cycles) /
                 (benchmark_read_hit_count + benchmark_write_hit_count),
             benchmark_l1_miss_count + benchmark_upgrade_count,
             ((benchmark_l1_miss_count + benchmark_upgrade_count) == 0) ? 0 :
               (benchmark_l1_miss_cycles + benchmark_upgrade_cycles) /
                 (benchmark_l1_miss_count + benchmark_upgrade_count),
             benchmark_read_hit_count,
             (benchmark_read_hit_count == 0) ? 0 : benchmark_read_hit_cycles / benchmark_read_hit_count,
             benchmark_write_hit_count,
             (benchmark_write_hit_count == 0) ? 0 : benchmark_write_hit_cycles / benchmark_write_hit_count,
             benchmark_upgrade_count,
             (benchmark_upgrade_count == 0) ? 0 : benchmark_upgrade_cycles / benchmark_upgrade_count,
             benchmark_l1_miss_count,
             (benchmark_l1_miss_count == 0) ? 0 : benchmark_l1_miss_cycles / benchmark_l1_miss_count,
             benchmark_request_ready_stall_cycles,
             benchmark_snoop_count,
             (benchmark_snoop_count == 0) ? 0 : benchmark_snoop_cycles / benchmark_snoop_count);
    $display("PASS: dual-L1 MESI directed, backpressure, reset, concurrency, and random regression");
    $finish;
  end
