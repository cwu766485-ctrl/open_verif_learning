    // Queue four reads while AR is blocked. The R channel then interleaves
    // four distinct IDs and the adapter routes each beat to the right line.
    axi_arready = 1'b0;
    for (txn = 0; txn < 4; txn = txn + 1)
      submit_read(txn);
    @(negedge clock);
    line_rd_req_valid = 1'b1;
    line_rd_req_addr = 32'h0001_1000;
    line_rd_req_id = 4'hf;
    #1;
    if (line_rd_req_ready)
      $fatal(1, "read adapter accepted more than four outstanding requests");
    line_rd_req_valid = 1'b0;
    if (!axi_arvalid || axi_arid != 4'h1 || axi_araddr != 32'h0001_0000)
      $fatal(1, "queued AR head was not held under backpressure");
    axi_arready = 1'b1;
    for (txn = 0; txn < 4; txn = txn + 1) begin
      #1;
      if (!axi_arvalid || axi_arid != 4'(txn + 1) ||
          axi_araddr != (32'h0001_0000 + txn * 64))
        $fatal(1, "queued AR order mismatch at entry %0d", txn);
      tick();
      @(negedge clock);
    end
    axi_arready = 1'b0;
    line_rd_data_ready = 1'b1;
    for (beat = 0; beat < 8; beat = beat + 1)
      for (txn = 0; txn < 4; txn = txn + 1)
        send_interleaved_r(txn, beat);

    // Four writes can be accepted and filled concurrently. AW addresses are
    // emitted in order, W bursts stay in that order, and B responses may
    // return in a different order because their IDs identify each request.
    axi_awready = 1'b0;
    axi_wready = 1'b0;
    for (txn = 0; txn < 4; txn = txn + 1)
      submit_write(txn);
    @(negedge clock);
    line_wr_req_valid = 1'b1;
    line_wr_req_addr = 32'h0002_1000;
    line_wr_req_id = 4'hf;
    #1;
    if (line_wr_req_ready)
      $fatal(1, "write adapter accepted more than four outstanding requests");
    line_wr_req_valid = 1'b0;
    for (beat = 0; beat < 8; beat = beat + 1) begin
      for (txn = 0; txn < 4; txn = txn + 1) begin
        line_wr_data_valid = 1'b1;
        line_wr_data_id = 4'(txn + 1);
        line_wr_data_beat = 3'(beat);
        line_wr_data = 64'h6000 + txn * 256 + beat;
        line_wr_data_last = (beat == 7);
        #1;
        if (!line_wr_data_ready || axi_wvalid)
          $fatal(1, "write-data gather failed id=%0d beat=%0d", txn+1, beat);
        tick();
        @(negedge clock);
        line_wr_data_valid = 1'b0;
      end
    end
    if (axi_wvalid)
      $fatal(1, "AXI W data issued before AW acceptance");
    axi_awready = 1'b1;
    for (txn = 0; txn < 4; txn = txn + 1) begin
      #1;
      if (!axi_awvalid || axi_awid != 4'(txn + 1) ||
          axi_awaddr != (32'h0002_0000 + txn * 64))
        $fatal(1, "queued AW order mismatch at entry %0d", txn);
      tick();
      @(negedge clock);
    end
    axi_awready = 1'b0;
    axi_wready = 1'b1;
    for (txn = 0; txn < 4; txn = txn + 1) begin
      for (beat = 0; beat < 8; beat = beat + 1) begin
        #1;
        if (!axi_wvalid || axi_wdata != (64'h6000 + txn * 256 + beat) ||
            axi_wlast != (beat == 7))
          $fatal(1, "serialized AXI W order mismatch txn=%0d beat=%0d", txn, beat);
        tick();
        @(negedge clock);
      end
    end
    axi_wready = 1'b0;
    send_b(3);
    send_b(1);
    send_b(0);
    send_b(2);
    if (adapter_protocol_error)
      $fatal(1, "legal four-outstanding traffic raised adapter protocol_error");
