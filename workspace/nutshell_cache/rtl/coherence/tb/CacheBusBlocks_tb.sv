module CacheBusBlocks_tb;
  logic clock;
  logic reset = 1'b1;
  initial begin
    clock = 1'b0;
    forever #5 clock = ~clock;
  end

  logic line_rd_req_valid, line_rd_req_ready;
  logic [31:0] line_rd_req_addr;
  logic [3:0] line_rd_req_id;
  logic line_rd_data_valid, line_rd_data_ready;
  logic [3:0] line_rd_data_id;
  logic [2:0] line_rd_data_beat;
  logic [63:0] line_rd_data;
  logic line_rd_data_last, line_rd_data_error;
  logic line_wr_req_valid, line_wr_req_ready;
  logic [31:0] line_wr_req_addr;
  logic [3:0] line_wr_req_id;
  logic line_wr_data_valid, line_wr_data_ready;
  logic [3:0] line_wr_data_id;
  logic [2:0] line_wr_data_beat;
  logic [63:0] line_wr_data;
  logic line_wr_data_last;
  logic line_wr_rsp_valid, line_wr_rsp_ready;
  logic [3:0] line_wr_rsp_id;
  logic line_wr_rsp_error, adapter_protocol_error;

  logic [3:0] axi_arid;
  logic [31:0] axi_araddr;
  logic [7:0] axi_arlen;
  logic [2:0] axi_arsize;
  logic [1:0] axi_arburst;
  logic axi_arlock;
  logic [3:0] axi_arcache;
  logic [2:0] axi_arprot;
  logic axi_arvalid, axi_arready;
  logic [3:0] axi_rid;
  logic [63:0] axi_rdata;
  logic [1:0] axi_rresp;
  logic axi_rlast, axi_rvalid, axi_rready;
  logic [3:0] axi_awid;
  logic [31:0] axi_awaddr;
  logic [7:0] axi_awlen;
  logic [2:0] axi_awsize;
  logic [1:0] axi_awburst;
  logic axi_awlock;
  logic [3:0] axi_awcache;
  logic [2:0] axi_awprot;
  logic axi_awvalid, axi_awready;
  logic [63:0] axi_wdata;
  logic [7:0] axi_wstrb;
  logic axi_wlast, axi_wvalid, axi_wready;
  logic [3:0] axi_bid;
  logic [1:0] axi_bresp;
  logic axi_bvalid, axi_bready;

  logic [1:0] hit_event, miss_event, snoop_event;
  logic dirty_writeback_event;
  logic [1:0] cache_inflight, access_complete_event;
  logic [4:0] error_status;
  logic apb_psel, apb_penable, apb_pwrite;
  logic [31:0] apb_paddr, apb_prdata;
  logic apb_pready, apb_pslverr;

  LineMemoryAxi4Adapter #(.ID_WIDTH(4)) adapter (.*,
    .protocol_error(adapter_protocol_error));
  CachePerformanceCsr csr (.*,
    .apb_psel(apb_psel), .apb_penable(apb_penable),
    .apb_pwrite(apb_pwrite), .apb_paddr(apb_paddr),
    .apb_pready(apb_pready), .apb_prdata(apb_prdata),
    .apb_pslverr(apb_pslverr));

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

  initial begin : test
    integer beat;
    integer txn;
    line_rd_req_valid = 1'b0;
    line_rd_req_addr = '0;
    line_rd_req_id = '0;
    line_rd_data_ready = 1'b0;
    line_wr_req_valid = 1'b0;
    line_wr_req_addr = '0;
    line_wr_req_id = '0;
    line_wr_data_valid = 1'b0;
    line_wr_data_id = '0;
    line_wr_data_beat = '0;
    line_wr_data = '0;
    line_wr_data_last = 1'b0;
    line_wr_rsp_ready = 1'b0;
    axi_arready = 1'b0;
    axi_rid = '0;
    axi_rdata = '0;
    axi_rresp = 2'b00;
    axi_rlast = 1'b0;
    axi_rvalid = 1'b0;
    axi_awready = 1'b0;
    axi_wready = 1'b0;
    axi_bid = '0;
    axi_bresp = 2'b00;
    axi_bvalid = 1'b0;
    hit_event = '0;
    miss_event = '0;
    snoop_event = '0;
    dirty_writeback_event = 1'b0;
    cache_inflight = '0;
    access_complete_event = '0;
    error_status = '0;
    apb_psel = 1'b0;
    apb_penable = 1'b0;
    apb_pwrite = 1'b0;
    apb_paddr = '0;

    repeat (3) tick();
    @(negedge clock);
    reset = 1'b0;

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

    // Exercise the APB counters and status mapping.
    hit_event = 2'b01;
    miss_event = 2'b10;
    snoop_event = 2'b11;
    dirty_writeback_event = 1'b1;
    cache_inflight = 2'b01;
    tick();
    @(negedge clock);
    hit_event = '0;
    miss_event = '0;
    snoop_event = '0;
    dirty_writeback_event = 1'b0;
    cache_inflight = '0;
    access_complete_event = 2'b01;
    error_status = 5'b0_1101;
    tick();
    @(negedge clock);
    access_complete_event = '0;
    repeat (2) tick();
    apb_read(32'h00, 32'd1);
    apb_read(32'h04, 32'd1);
    apb_read(32'h08, 32'd2);
    apb_read(32'h0c, 32'd1);
    apb_read(32'h10, 32'h0000_000d);
    apb_read(32'h14, 32'd1);
    apb_read(32'h18, 32'd1);

    @(negedge clock);
    apb_psel = 1'b1;
    apb_penable = 1'b0;
    apb_pwrite = 1'b1;
    apb_paddr = 32'h00;
    @(negedge clock);
    apb_penable = 1'b1;
    #1;
    if (!apb_pready || !apb_pslverr)
      $fatal(1, "APB writes must be rejected by the read-only CSR block");
    @(negedge clock);
    apb_psel = 1'b0;
    apb_penable = 1'b0;
    apb_pwrite = 1'b0;

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
endmodule
