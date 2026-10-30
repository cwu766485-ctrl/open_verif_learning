    // A response with the wrong AXI ID is both surfaced as a line error and
    // latched as an adapter protocol failure.
    @(negedge clock);
    line_rd_req_valid = 1'b1;
    line_rd_req_addr = 32'h0000_a000;
    line_rd_req_id = 4'h7;
    axi_arready = 1'b0;
    tick();
    @(negedge clock);
    line_rd_req_valid = 1'b0;
    axi_arready = 1'b1;
    tick();
    @(negedge clock);
    axi_arready = 1'b0;
    axi_rid = 4'h8;
    axi_rresp = 2'b00;
    axi_rlast = 1'b1;
    axi_rvalid = 1'b1;
    line_rd_data_ready = 1'b1;
    #1;
    if (line_rd_data_valid || !axi_rready)
      $fatal(1, "unknown AXI RID was not drained independently of line data");
    tick();
    @(negedge clock);
    axi_rvalid = 1'b0;
    line_rd_data_ready = 1'b0;
    if (!adapter_protocol_error)
      $fatal(1, "AXI RID mismatch did not set adapter protocol_error");

    $display("PASS: AXI4 burst adapter and APB performance CSR");
    $finish;
  end
