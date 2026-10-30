  task automatic tick;
    @(posedge clock);
    #1;
  endtask

  task automatic apb_read(input logic [31:0] addr, input logic [31:0] expected);
    @(negedge clock);
    apb_psel = 1'b1;
    apb_penable = 1'b0;
    apb_pwrite = 1'b0;
    apb_paddr = addr;
    #1;
    if (apb_pready)
      $fatal(1, "APB PREADY must remain low during setup phase");
    @(negedge clock);
    apb_penable = 1'b1;
    #1;
    if (!apb_pready || apb_pslverr || (apb_prdata != expected))
      $fatal(1, "APB read %08x returned %08x expected %08x", addr,
             apb_prdata, expected);
    @(negedge clock);
    apb_psel = 1'b0;
    apb_penable = 1'b0;
  endtask

  task automatic submit_read(input integer index);
    @(negedge clock);
    line_rd_req_valid = 1'b1;
    line_rd_req_addr = 32'h0001_0000 + index * 64;
    line_rd_req_id = 4'(index + 1);
    #1;
    if (!line_rd_req_ready)
      $fatal(1, "read queue rejected slot %0d before reaching capacity", index);
    tick();
    @(negedge clock);
    line_rd_req_valid = 1'b0;
  endtask

  task automatic send_interleaved_r(input integer index, input integer beat);
    logic [63:0] expected_data;
    expected_data = 64'h5000 + index * 256 + beat;
    @(negedge clock);
    axi_rid = 4'(index + 1);
    axi_rdata = expected_data;
    axi_rresp = 2'b00;
    axi_rlast = (beat == 7);
    axi_rvalid = 1'b1;
    #1;
    if (!axi_rready || !line_rd_data_valid ||
        line_rd_data_id != 4'(index + 1) ||
        line_rd_data_beat != 3'(beat) || line_rd_data != expected_data ||
        line_rd_data_last != (beat == 7) || line_rd_data_error)
      $fatal(1, "interleaved R beat mismatch id=%0d beat=%0d", index+1, beat);
    tick();
    @(negedge clock);
    axi_rvalid = 1'b0;
  endtask

  task automatic submit_write(input integer index);
    @(negedge clock);
    line_wr_req_valid = 1'b1;
    line_wr_req_addr = 32'h0002_0000 + index * 64;
    line_wr_req_id = 4'(index + 1);
    #1;
    if (!line_wr_req_ready)
      $fatal(1, "write queue rejected slot %0d before reaching capacity", index);
    tick();
    @(negedge clock);
    line_wr_req_valid = 1'b0;
  endtask

  task automatic send_b(input integer index);
    @(negedge clock);
    axi_bid = 4'(index + 1);
    axi_bresp = 2'b00;
    axi_bvalid = 1'b1;
    line_wr_rsp_ready = 1'b1;
    #1;
    if (!line_wr_rsp_valid || line_wr_rsp_error || !axi_bready ||
        line_wr_rsp_id != 4'(index + 1))
      $fatal(1, "out-of-order B response did not route by ID %0d", index+1);
    tick();
    @(negedge clock);
    axi_bvalid = 1'b0;
    line_wr_rsp_ready = 1'b0;
  endtask
