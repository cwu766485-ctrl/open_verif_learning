    // A blocking L1 replacement cannot accept the snoop until its same-line
    // Put is acknowledged. Permit that Put only while the snoop offer remains
    // stalled; after the snoop handshake, the same-line snapshot is locked.
    ctx_addr[0] = 32'h0000_6800;
    ctx_txn[0] = TXN_ID_WIDTH'(6);
    ctx_src[0] = 1'b0;
    snoop_req_ready = 1'b0;
    send_request(ctx_addr[0], ctx_src[0], ctx_txn[0], DIR_U, 2'b00, 1'b1);
    for (cycles = 0; cycles < 30; cycles++) begin
      @(posedge clock);
      if (snoop_req_valid) break;
    end
    if (cycles == 30 || snoop_req_ready)
      $fatal(1, "snoop offer was not held under target backpressure");
    @(negedge clock);
    req_valid = 1'b1;
    req_opcode = REQ_PUTS;
    req_src_id = 1'b1;
    req_txn_id = TXN_ID_WIDTH'(7);
    req_line_addr = ctx_addr[0];
    lookup_dir_state = DIR_S;
    lookup_sharers = 2'b10;
    #1;
    if (!req_ready)
      $fatal(1, "stalled-snoop target Put did not bypass the blocking L1");
    @(posedge clock);
    @(negedge clock);
    req_valid = 1'b0;
    $display("COV_EVENT: id=mshr_bank.stalled_snoop_target_put checker=PASS old_state=DIR_U requester=Core0 opcode=GetS_plus_PutS snoop_target=Core1 new_state=DIR_S data_source=putbypass beats=0 contexts=2");
    reset_bank();
