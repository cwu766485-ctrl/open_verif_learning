  // Force the top-level master READY low only after a response is presented.
  // The source must keep VALID/ID/data/beat/last stable for five cycles and
  // then drain normally when READY is released.
  initial begin : axi_response_backpressure_injection
    logic do_r_stall;
    logic do_b_stall;
    logic [TXN_ID_WIDTH-1:0] held_id;
    logic [63:0] held_data;
    logic held_last;
    logic [1:0] held_resp;
    do_r_stall = $test$plusargs("stall_r") || $test$plusargs("stall_rb");
    do_b_stall = $test$plusargs("stall_b") || $test$plusargs("stall_rb");
    wait (!reset);
    if (do_r_stall) begin
      wait (axi_rvalid);
      held_id = axi_rid;
      held_data = axi_rdata;
      held_last = axi_rlast;
      held_resp = axi_rresp;
      force dut.cache_core.mem_rd_data_ready = 1'b0;
      repeat (5) begin
        @(posedge clock); #1;
        if (!axi_rvalid || axi_rready || axi_rid != held_id ||
            axi_rdata != held_data || axi_rresp != held_resp ||
            axi_rlast != held_last)
          $fatal(1, "AXI R response changed during forced backpressure");
        forced_r_stall_cycles = forced_r_stall_cycles + 1;
      end
      release dut.cache_core.mem_rd_data_ready;
    end
    if (do_b_stall) begin
      wait (axi_bvalid);
      held_id = axi_bid;
      held_resp = axi_bresp;
      force dut.cache_core.mem_wr_rsp_ready = 1'b0;
      repeat (5) begin
        @(posedge clock); #1;
        if (!axi_bvalid || axi_bready || axi_bid != held_id ||
            axi_bresp != held_resp)
          $fatal(1, "AXI B response changed during forced backpressure");
        forced_b_stall_cycles = forced_b_stall_cycles + 1;
      end
      release dut.cache_core.mem_wr_rsp_ready;
    end
  end
