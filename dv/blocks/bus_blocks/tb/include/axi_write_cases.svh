    // AW is buffered independently; line data is gathered by ID before the
    // AXI4 W burst is emitted in AW order.
    line_wr_req_valid = 1'b1;
    line_wr_req_addr = 32'h0000_8007;
    line_wr_req_id = 4'h3;
    axi_awready = 1'b0;
    #1;
    if (!line_wr_req_ready || axi_awvalid)
      $fatal(1, "line write request was not captured independently of AWREADY");
    tick();
    @(negedge clock);
    line_wr_req_valid = 1'b0;
    repeat (2) begin
      #1;
      if (!axi_awvalid || axi_awaddr != 32'h0000_8000 ||
          axi_awid != 4'h3 || axi_awlen != 8'd7 || axi_awsize != 3'b011 ||
          axi_awburst != 2'b01 || axi_awlock || axi_awcache != 4'b0011 ||
          axi_awprot != 3'b000)
        $fatal(1, "AXI AW fields or backpressure handling are incorrect");
      tick();
    end
    @(negedge clock);
    axi_awready = 1'b1;
    tick();
    @(negedge clock);
    axi_awready = 1'b0;
    for (beat = 0; beat < 8; beat = beat + 1) begin
      line_wr_data_valid = 1'b1;
      line_wr_data_id = 4'h3;
      line_wr_data_beat = beat[2:0];
      line_wr_data = 64'h2000 + {{32{1'b0}}, beat[31:0]};
      line_wr_data_last = (beat == 7);
      axi_wready = 1'b0;
      #1;
      if (!line_wr_data_ready || axi_wvalid)
        $fatal(1, "line write data buffering failed at beat %0d", beat);
      tick();
      @(negedge clock);
      line_wr_data_valid = 1'b0;
    end
    for (beat = 0; beat < 8; beat = beat + 1) begin
      axi_wready = 1'b0;
      #1;
      if (!axi_wvalid || axi_wdata != 64'h2000 + {{32{1'b0}}, beat[31:0]} ||
          axi_wstrb != 8'hff || axi_wlast != (beat == 7))
        $fatal(1, "AXI W beat translation failed at beat %0d", beat);
      tick();
      @(negedge clock);
      axi_wready = 1'b1;
      tick();
      @(negedge clock);
    end
    axi_wready = 1'b0;
    axi_bid = 4'h3;
    axi_bresp = 2'b00;
    axi_bvalid = 1'b1;
    line_wr_rsp_ready = 1'b0;
    #1;
    if (!line_wr_rsp_valid || line_wr_rsp_error || axi_bready ||
        line_wr_rsp_id != 4'h3)
      $fatal(1, "AXI B response was not held under line-side backpressure");
    tick();
    @(negedge clock);
    line_wr_rsp_ready = 1'b1;
    #1;
    if (!axi_bready)
      $fatal(1, "AXI BREADY did not follow the line response receiver");
    tick();
    @(negedge clock);
    axi_bvalid = 1'b0;
    line_wr_rsp_ready = 1'b0;

    // A legal AXI SLVERR is a memory error, not an adapter protocol error.
    @(negedge clock);
    line_wr_req_valid = 1'b1;
    line_wr_req_addr = 32'h0000_9000;
    line_wr_req_id = 4'h4;
    axi_awready = 1'b0;
    tick();
    @(negedge clock);
    line_wr_req_valid = 1'b0;
    axi_awready = 1'b1;
    tick();
    @(negedge clock);
    axi_awready = 1'b0;
    for (beat = 0; beat < 8; beat = beat + 1) begin
      line_wr_data_valid = 1'b1;
      line_wr_data_id = 4'h4;
      line_wr_data_beat = beat[2:0];
      line_wr_data = 64'h3000 + {{32{1'b0}}, beat[31:0]};
      line_wr_data_last = (beat == 7);
      tick();
      @(negedge clock);
      line_wr_data_valid = 1'b0;
    end
    axi_wready = 1'b1;
    for (beat = 0; beat < 8; beat = beat + 1) begin
      tick();
      @(negedge clock);
    end
    axi_wready = 1'b0;
    axi_bid = 4'h4;
    axi_bresp = 2'b10;
    axi_bvalid = 1'b1;
    line_wr_rsp_ready = 1'b1;
    #1;
    if (!line_wr_rsp_valid || !line_wr_rsp_error || !axi_bready)
      $fatal(1, "AXI B error response was not propagated to the line interface");
    tick();
    @(negedge clock);
    axi_bvalid = 1'b0;
    line_wr_rsp_ready = 1'b0;
    if (adapter_protocol_error)
      $fatal(1, "legal AXI SLVERR incorrectly raised protocol_error");
