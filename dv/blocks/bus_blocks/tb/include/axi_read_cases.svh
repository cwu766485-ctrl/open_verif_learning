    // A line request is buffered while AXI ARREADY stalls. The queued AR
    // payload then remains stable until its address handshake.
    line_rd_req_valid = 1'b1;
    line_rd_req_addr = 32'h0000_1237;
    line_rd_req_id = 4'h5;
    #1;
    if (!line_rd_req_ready || axi_arvalid)
      $fatal(1, "line read request was not captured independently of ARREADY");
    tick();
    @(negedge clock);
    line_rd_req_valid = 1'b0;
    repeat (2) begin
      #1;
      if (!axi_arvalid || axi_araddr != 32'h0000_1200 ||
          axi_arid != 4'h5 || axi_arlen != 8'd7 || axi_arsize != 3'b011 ||
          axi_arburst != 2'b01 || axi_arlock || axi_arcache != 4'b0011 ||
          axi_arprot != 3'b000)
        $fatal(1, "AXI AR fields or backpressure handling are incorrect");
      tick();
    end
    @(negedge clock);
    axi_arready = 1'b1;
    tick();
    @(negedge clock);
    axi_arready = 1'b0;

    // Eight R beats with alternating downstream stalls.
    for (beat = 0; beat < 8; beat = beat + 1) begin
      axi_rid = 4'h5;
      axi_rdata = 64'h1000 + {{32{1'b0}}, beat[31:0]};
      axi_rresp = 2'b00;
      axi_rlast = (beat == 7);
      axi_rvalid = 1'b1;
      line_rd_data_ready = 1'b0;
      #1;
      if (!line_rd_data_valid || line_rd_data_id != 4'h5 ||
          line_rd_data_beat != beat[2:0] ||
          line_rd_data != 64'h1000 + {{32{1'b0}}, beat[31:0]} ||
          line_rd_data_last != (beat == 7) || line_rd_data_error)
        $fatal(1, "AXI R beat translation failed at beat %0d", beat);
      tick();
      @(negedge clock);
      line_rd_data_ready = 1'b1;
      tick();
      @(negedge clock);
      axi_rvalid = 1'b0;
      line_rd_data_ready = 1'b0;
    end

    // An AXI error terminates the line response and drains trailing R beats.
    line_rd_req_valid = 1'b1;
    line_rd_req_addr = 32'h0000_4560;
    line_rd_req_id = 4'h6;
    axi_arready = 1'b0;
    tick();
    @(negedge clock);
    line_rd_req_valid = 1'b0;
    axi_arready = 1'b1;
    tick();
    @(negedge clock);
    axi_arready = 1'b0;
    axi_rid = 4'h6;
    axi_rdata = 64'hbad0;
    axi_rresp = 2'b10;
    axi_rlast = 1'b0;
    axi_rvalid = 1'b1;
    line_rd_data_ready = 1'b1;
    #1;
    if (!line_rd_data_valid || !line_rd_data_error || !line_rd_data_last ||
        !axi_rready)
      $fatal(1, "AXI read error was not surfaced as a terminal line error");
    tick();
    @(negedge clock);
    axi_rresp = 2'b00;
    axi_rlast = 1'b1;
    axi_rvalid = 1'b1;
    #1;
    if (line_rd_data_valid || !axi_rready)
      $fatal(1, "trailing AXI error-response beats were not drained");
    tick();
    @(negedge clock);
    axi_rvalid = 1'b0;
    if (adapter_protocol_error)
      $fatal(1, "valid AXI error response incorrectly raised protocol_error");
