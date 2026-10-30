    // Exercise external request/response stalls while the CPU response is
    // also blocked. The memory model inserts read-data bubbles during this
    // phase and keeps each beat stable until the DUT accepts it.
    inject_periodic_stalls = 1'b1;
    stall_mem_rd_req = 1'b1;
    cpu_resp_ready[0] = 1'b0;
    cpu_issue_only(0, 32'h0000_9000, 1'b0, 8'h00, 64'b0);
    for (cycles = 0; cycles < 100; cycles = cycles + 1) begin
      if (mem_rd_req_valid)
        break;
      @(posedge clock);
    end
    if (!mem_rd_req_valid)
      $fatal(1, "stalled memory read request was never presented");
    repeat (4) @(posedge clock);
    @(negedge clock);
    force dut.l2_array.line_wr_ready = 1'b0;
    stall_mem_rd_req = 1'b0;
    wait (dut.mem_mshr_full_q[0]);
    wait (dut.mem_fill_writer_active_q);
    #1;
    if (!dut.mem_mshr_full_q[0] || !dut.mem_fill_writer_active_q ||
        dut.l2_line_wr_ready || (dut.mem_fill_writer_beat_q != 3'd0))
      $fatal(1, "MSHR did not decouple AXI refill from a stalled L2 fill port: full=%b writer=%b ready=%b beat=%0d",
             dut.mem_mshr_full_q[0], dut.mem_fill_writer_active_q,
             dut.l2_line_wr_ready, dut.mem_fill_writer_beat_q);
    repeat (3) @(posedge clock);
    if (!dut.mem_fill_writer_active_q ||
        (dut.mem_fill_writer_beat_q != 3'd0) || cpu_resp_valid[0])
      $fatal(1, "stalled L2 fill did not hold its buffered line and block CPU completion");
    // Some simulator versions retain a forced value on optimized array ports;
    // explicitly restore READY for portable behavior.
    force dut.l2_array.line_wr_ready = 1'b1;
      coverage_mark("backpressure.mem_refill", "I", "0", "GetS", "none", "E", "memory", 8);
    $display("PASS: refill MSHR absorbs the memory line while the L2 fill port is stalled");
    for (cycles = 0; cycles < 1000; cycles = cycles + 1) begin
      if (cpu_resp_valid[0])
        break;
      @(posedge clock);
    end
    if (!cpu_resp_valid[0])
      $fatal(1, "CPU response did not arrive after memory request stall release");
    repeat (4) @(posedge clock);
    @(negedge clock);
    cpu_resp_ready[0] = 1'b1;
    cpu_response_only(0, 32'h0000_9000, 1'b0, 8'h00, 64'b0, stalled_data);
    // Give the response tracker a full ready cycle before starting the next
    // independent transaction and changing the backpressure pattern.
    @(posedge clock);
    @(negedge clock);
      coverage_mark("backpressure.independent_channels", "mixed", "both", "GetS+GetM", "none", "mixed", "memory", 8);
    $display("PASS: memory request/refill and CPU response survive independent stalls");

    stall_mmio_req = 1'b1;
    cpu_resp_ready[0] = 1'b0;
    cpu_issue_only(0, 32'h3000_0100, 1'b0, 8'h00, 64'b0);
    for (cycles = 0; cycles < 100; cycles = cycles + 1) begin
      if (mmio_req_valid)
        break;
      @(posedge clock);
    end
    if (!mmio_req_valid)
      $fatal(1, "stalled MMIO request was never presented");
    repeat (4) @(posedge clock);
    @(negedge clock);
    stall_mmio_req = 1'b0;
    for (cycles = 0; cycles < 1000; cycles = cycles + 1) begin
      if (mmio_resp_valid)
        break;
      @(posedge clock);
    end
    if (!mmio_resp_valid)
      $fatal(1, "MMIO response did not arrive after request stall release");
    repeat (4) @(posedge clock);
    @(negedge clock);
    cpu_resp_ready[0] = 1'b1;
    cpu_response_only(0, 32'h3000_0100, 1'b0, 8'h00, 64'b0, stalled_data);
    inject_periodic_stalls = 1'b0;
      coverage_mark("backpressure.mmio", "na", "0", "MMIO", "none", "na", "MMIO", 0);
    $display("PASS: MMIO request and response payloads remain stable under backpressure");

    expect_word(0, word_addr, initial_word);
    expect_protocol_state(MESI_E, MESI_I, DIR_U, 2'b00, 1'b0);
      coverage_mark("mesi.gets_cold_refill", "I", "0", "GetS", "none", "E", "memory", 8);
    $display("PASS: Core0 GetS refill from backing memory");
