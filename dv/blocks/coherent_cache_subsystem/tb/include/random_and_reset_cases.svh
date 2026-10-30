    // A repeatable constrained-random phase concentrates traffic on one L2
    // set while varying word offsets, cores, read/write mix, and byte masks.
    inject_periodic_stalls = 1'b1;
    if (!$value$plusargs("seed=%h", random_seed))
      random_seed = 32'h1ACE_B00C;
    random_state = random_seed;
    for (random_index = 0; random_index < 80; random_index = random_index + 1) begin
      random_state = {random_state[30:0],
                      random_state[31] ^ random_state[21] ^
                      random_state[1] ^ random_state[0]};
      random_addr = 32'h0010_0000 + (32'(random_state[7:4]) << 15) +
                    {random_state[10:8], 3'b000};
      random_core = random_state[0];
      case (random_state[4:2])
        3'd0: random_mask = 8'hFF;
        3'd1: random_mask = 8'h0F;
        3'd2: random_mask = 8'hF0;
        3'd3: random_mask = 8'h01;
        3'd4: random_mask = 8'h80;
        default: random_mask = 8'h00;
      endcase
      random_data = {random_state, ~random_state};
      if (random_state[1])
        cpu_access(random_core, random_addr, 1'b1, random_mask,
                   random_data, ignored);
      else
        cpu_access(random_core, random_addr, 1'b0, 8'h00,
                   64'b0, ignored);
    end
    inject_periodic_stalls = 1'b0;
      coverage_mark("random.seeded_data", "mixed", "both", "random", "mixed", "mixed", "mixed", 8);
    $display("PASS: seeded 80-operation coherence/data scoreboard regression seed=%08x",
             random_seed);

    if ((cover_cpu_resp_stall == 0) || (cover_mmio_req_stall == 0) ||
        (cover_mmio_resp_stall == 0) || (cover_mem_rd_req_stall == 0) ||
        (cover_l2_fill_stall == 0) || (cover_mem_wr_req_stall == 0) ||
        (cover_mem_wr_data_stall == 0) ||
        (cover_dir_req_stall == 0))
      $fatal(1, "backpressure coverage hole: cpu_resp=%0d mmio_req=%0d mmio_resp=%0d mem_rd_req=%0d l2_fill=%0d mem_wr_req=%0d mem_wr_data=%0d dir_req=%0d",
             cover_cpu_resp_stall, cover_mmio_req_stall,
             cover_mmio_resp_stall, cover_mem_rd_req_stall, cover_l2_fill_stall,
             cover_mem_wr_req_stall, cover_mem_wr_data_stall,
             cover_dir_req_stall);
    $display("COVER: stalled cpu_resp=%0d mmio_req=%0d mmio_resp=%0d mem_rd_req=%0d l2_fill=%0d mem_wr_req=%0d mem_wr_data=%0d dir_req=%0d",
             cover_cpu_resp_stall, cover_mmio_req_stall,
             cover_mmio_resp_stall, cover_mem_rd_req_stall, cover_l2_fill_stall,
             cover_mem_wr_req_stall, cover_mem_wr_data_stall,
             cover_dir_req_stall);

    if ((l1_controller_protocol_error != 2'b00) ||
        (l1_array_protocol_error != 2'b00) || directory_protocol_error ||
        l2_protocol_error || memory_adapter_protocol_error ||
        memory_adapter_error || mmio_protocol_error || fatal_error)
      $fatal(1, "protocol error(s): ctrl=%b array=%b dir=%b l2=%b mem=%b mmio=%b",
             l1_controller_protocol_error, l1_array_protocol_error,
             directory_protocol_error, l2_protocol_error,
             memory_adapter_protocol_error, mmio_protocol_error);

    // Reset during a blocked refill request cancels the outstanding CPU
    // transaction and its memory-side activity. The external memory model is
    // reset together with the cache subsystem by contract.
    stall_mem_rd_req = 1'b1;
    cpu_issue_only(0, 32'h000F_0000, 1'b0, 8'h00, 64'b0);
    wait (mem_rd_req_valid);
    repeat (3) @(posedge clock);
    @(negedge clock);
    reset = 1'b1;
    reference_clear();
    repeat (3) @(posedge clock);
    if (mem_rd_req_valid || mem_wr_req_valid || mmio_req_valid ||
        cpu_resp_valid[0] || cpu_resp_valid[1])
      $fatal(1, "reset did not cancel a blocked refill transaction");
    @(negedge clock);
    stall_mem_rd_req = 1'b0;
    reset = 1'b0;
    repeat (5) begin
      @(posedge clock);
      if (cpu_resp_valid[0] || cpu_resp_valid[1])
        $fatal(1, "stale CPU response escaped after refill reset");
    end
    expect_word(0, 32'h000F_0000, memory_word(32'h000F_0000, 3'd0));
      coverage_mark("reset.refill", "I", "0", "GetS+Reset", "none", "I", "memory", 0);
    $display("PASS: reset cancels an active refill without a stale response");

    // Hold an MMIO response at the peripheral boundary, then reset before it
    // can complete at the LSU.
    cpu_resp_ready[0] = 1'b0;
    cpu_issue_only(0, 32'h3000_0108, 1'b0, 8'h00, 64'b0);
    wait (mmio_resp_valid);
    if (mmio_resp_ready)
      $fatal(1, "MMIO response should be stalled by the blocked CPU response");
    repeat (2) @(posedge clock);
    @(negedge clock);
    reset = 1'b1;
    reference_clear();
    repeat (3) @(posedge clock);
    @(negedge clock);
    reset = 1'b0;
    cpu_resp_ready[0] = 1'b1;
    repeat (5) begin
      @(posedge clock);
      if (cpu_resp_valid[0] || mmio_resp_ready)
        $fatal(1, "stale MMIO response escaped after reset");
    end
      coverage_mark("reset.mmio", "na", "0", "MMIO+Reset", "none", "na", "MMIO", 0);
    $display("PASS: reset cancels a backpressured MMIO response");

    // Finally assert reset while a valid cache response itself is stalled.
    cpu_resp_ready[0] = 1'b0;
    cpu_issue_only(0, 32'h000F_0000, 1'b0, 8'h00, 64'b0);
    wait (cpu_resp_valid[0]);
    repeat (2) @(posedge clock);
    @(negedge clock);
    reset = 1'b1;
    reference_clear();
    repeat (3) @(posedge clock);
    @(negedge clock);
    reset = 1'b0;
    repeat (5) begin
      @(posedge clock);
      if (cpu_resp_valid[0])
        $fatal(1, "stalled cache response reappeared after reset");
    end
    cpu_resp_ready[0] = 1'b1;
    if ((l1_controller_protocol_error != 2'b00) ||
        (l1_array_protocol_error != 2'b00) || directory_protocol_error ||
        l2_protocol_error || memory_adapter_protocol_error ||
        memory_adapter_error || mmio_protocol_error || fatal_error)
      $fatal(1, "protocol error after reset corner cases");
      coverage_mark("reset.cpu_rsp", "E", "0", "GetS+Reset", "none", "I", "L1", 0);
    $display("PASS: reset cancels a stalled cache response without replay");

    // Reset after an M owner has started returning SnoopData to the L2 path.
    // The reset is asserted between beats; partially transferred data is
    // discarded with the cache and Directory state.
    @(negedge clock);
    reset = 1'b1;
    reference_clear();
    repeat (3) @(posedge clock);
    @(negedge clock);
    reset = 1'b0;
    cpu_access(1, l2_test_addr[0] + 32'd24, 1'b1, 8'hFF,
               l2_dirty_value, ignored);
    cpu_issue_only(0, l2_test_addr[0] + 32'd24,
                   1'b0, 8'h00, 64'b0);
    for (cycles = 0; cycles < 1000; cycles = cycles + 1) begin
      if (dut.snoop_data_valid_core[1])
        break;
      @(posedge clock);
    end
    if (!dut.snoop_data_valid_core[1])
      $fatal(1, "remote GetS never started M-owner SnoopData stream");
    cover_reset_snoop_data = cover_reset_snoop_data + 1;
    @(negedge clock);
    reset = 1'b1;
    reference_clear();
    repeat (3) @(posedge clock);
    if (dut.snoop_data_valid_core[1] || cpu_resp_valid[0] ||
        cpu_resp_valid[1] || mem_rd_req_valid || mem_wr_req_valid ||
        mem_wr_data_valid)
      $fatal(1, "reset did not cancel an active owner SnoopData stream");
    @(negedge clock);
    reset = 1'b0;
    repeat (5) begin
      @(posedge clock);
      if (cpu_resp_valid[0] || cpu_resp_valid[1])
        $fatal(1, "stale CPU response escaped after SnoopData reset");
    end
    expect_reference_word(0, l2_test_addr[0] + 32'd24);
      coverage_mark("reset.snoop_data", "M", "0", "SnoopData+Reset", "1", "I", "L1_owner", 8);
    $display("PASS: reset cancels an active owner SnoopData stream");

    // Rebuild one full congruent L2 set with an M owner in the next victim
    // way. Stall the first external writeback beat, then reset the live
    // transaction and check that no stale memory or CPU response survives.
    @(negedge clock);
    reset = 1'b1;
    reference_clear();
    repeat (3) @(posedge clock);
    @(negedge clock);
    reset = 1'b0;
    stall_mem_wr_data = 1'b1;
    for (l2_line_number = 0; l2_line_number < 6; l2_line_number = l2_line_number + 1)
      expect_reference_word(0, l2_test_addr[l2_line_number] + 32'd24);
    cpu_access(1, l2_test_addr[6] + 32'd24, 1'b1, 8'hFF,
               l2_dirty_value, ignored);
    expect_reference_word(0, l2_test_addr[7] + 32'd24);
    cpu_issue_only(0, l2_test_addr[8] + 32'd24,
                   1'b0, 8'h00, 64'b0);
    for (cycles = 0; cycles < 3000; cycles = cycles + 1) begin
      if (mem_wr_data_valid)
        break;
      @(posedge clock);
    end
    if (!mem_wr_data_valid || mem_wr_data_ready)
      $fatal(1, "test failed to stall an active L2 victim writeback beat");
    repeat (2) @(posedge clock);
    if (!mem_wr_data_valid || mem_wr_data_ready || mem_wr_data_beat_idx != 3'd0)
      $fatal(1, "stalled L2 writeback beat did not remain stable");
    cover_reset_mem_wr_data = cover_reset_mem_wr_data + 1;
    @(negedge clock);
    reset = 1'b1;
    reference_clear();
    repeat (3) @(posedge clock);
    if (mem_wr_req_valid || mem_wr_data_valid || mem_rd_req_valid ||
        cpu_resp_valid[0] || cpu_resp_valid[1])
      $fatal(1, "reset did not cancel the stalled L2 writeback transaction");
    @(negedge clock);
    stall_mem_wr_data = 1'b0;
    reset = 1'b0;
    repeat (5) begin
      @(posedge clock);
      if (mem_wr_req_valid || mem_wr_data_valid ||
          cpu_resp_valid[0] || cpu_resp_valid[1])
        $fatal(1, "stale writeback or CPU response escaped after reset");
    end
    if ((cover_reset_snoop_data == 0) || (cover_reset_mem_wr_data == 0))
      $fatal(1, "reset coverage hole: snoop_data=%0d mem_wr_data=%0d",
             cover_reset_snoop_data, cover_reset_mem_wr_data);
      coverage_mark("reset.l2_writeback", "M", "1", "L2_Writeback+Reset", "1", "I", "backing_memory", 8);
    $display("PASS: reset cancels a stalled dirty L2 writeback beat");
