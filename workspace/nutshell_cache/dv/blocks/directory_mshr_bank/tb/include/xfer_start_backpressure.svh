  begin : xfer_start_backpressure_case
    integer xfer_cycles;
    logic [31:0] held_addr;
    logic [TXN_ID_WIDTH-1:0] held_txn;
    logic [CTX_W-1:0] held_context;
    logic held_src;
    line_xfer_kind_t held_kind;

    reset_bank();
    ctx_addr[0] = 32'h0000_7400;
    ctx_txn[0] = TXN_ID_WIDTH'(9);
    ctx_src[0] = 1'b1;
    ctx_written[0] = 1'b0;
    line_xfer_start_ready = 1'b0;
    send_request(ctx_addr[0], ctx_src[0], ctx_txn[0], DIR_I, 2'b00, 1'b0);

    for (xfer_cycles = 0; xfer_cycles < 30; xfer_cycles++) begin
      @(posedge clock);
      if (line_xfer_start_valid) break;
    end
    if (xfer_cycles == 30) $fatal(1, "refill start was not presented");
    held_addr = line_xfer_addr;
    held_txn = line_xfer_txn_id;
    held_context = line_xfer_context_id;
    held_src = line_xfer_src_id;
    held_kind = line_xfer_kind;

    repeat (5) begin
      @(posedge clock);
      #1;
      if (!line_xfer_start_valid || line_xfer_start_ready ||
          line_xfer_addr !== held_addr || line_xfer_txn_id !== held_txn ||
          line_xfer_context_id !== held_context || line_xfer_src_id !== held_src ||
          line_xfer_kind !== held_kind)
        $fatal(1, "refill start payload changed during five-cycle backpressure");
    end

    @(negedge clock);
    line_xfer_start_ready = 1'b1;
    @(posedge clock);
    if (!line_xfer_start_valid || line_xfer_addr !== held_addr ||
        line_xfer_txn_id !== held_txn || line_xfer_context_id !== held_context ||
        line_xfer_src_id !== held_src || line_xfer_kind !== held_kind)
      $fatal(1, "refill start payload changed on acceptance");
    @(negedge clock);
    line_xfer_start_ready = 1'b0;

    complete_xfer(held_context);
    accept_directory_writes(1);
    accept_grants(1);
    if (protocol_error || protocol_error_code != 0)
      $fatal(1, "legal refill backpressure raised protocol error code=%0d",
             protocol_error_code);
    $display("PASS: refill-start address/ID/context/source remain stable through five stalled cycles and complete once");
  end
