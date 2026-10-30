    // Park a shared-owner read in its snoop wait state, then show three other
    // contexts still refill, update the directory, and return grants.
    reset_bank();
    for (integer i = 0; i < NUM_MSHRS; i++) begin
      ctx_seen[i] = 1'b0;
      ctx_written[i] = 1'b0;
      ctx_addr[i] = 32'h0000_6000 + (i * 64);
      ctx_txn[i] = TXN_ID_WIDTH'(i + 5);
      ctx_src[i] = 1'b0;
    end
    snoop_req_ready = 1'b1;
    send_request(ctx_addr[0], 1'b0, ctx_txn[0], DIR_U, 2'b00, 1'b1);
    for (cycles = 0; cycles < 30; cycles++) begin
      @(posedge clock);
      if (snoop_req_valid && snoop_req_ready) break;
    end
    if (cycles == 30) $fatal(1, "owner snoop did not issue");
    snoop_addr_saved = snoop_req_line_addr;
    snoop_txn_saved = snoop_req_txn_id;
    snoop_target_saved = snoop_target_id;
    if (snoop_addr_saved != ctx_addr[0] || snoop_target_saved != 1'b1 ||
        snoop_req_opcode != SNOOP_READ)
      $fatal(1, "incorrect owner snoop payload");

    // Once the snoop is accepted, a same-line Put from its target must wait;
    // committing its separate snapshot would let this older context restore
    // stale owner/sharer metadata.
    @(negedge clock);
    req_valid = 1'b1;
    req_opcode = REQ_PUTS;
    req_src_id = 1'b1;
    req_txn_id = TXN_ID_WIDTH'(12);
    req_line_addr = ctx_addr[0];
    lookup_dir_state = DIR_S;
    lookup_sharers = 2'b10;
    #1;
    if (req_ready)
      $fatal(1, "same-line Put raced an already accepted snoop snapshot");
    req_valid = 1'b0;

    line_xfer_start_ready = 1'b0;
    for (integer i = 1; i < NUM_MSHRS; i++)
      send_request(ctx_addr[i], 1'b0, ctx_txn[i], DIR_I, 2'b00, 1'b0);
    line_xfer_start_ready = 1'b1;
    collect_xfers(3);
    for (integer i = NUM_MSHRS-1; i >= 1; i--)
      complete_xfer(CTX_W'(i));
    accept_directory_writes(3);
    accept_grants(3);
    if (grant_valid && (grant_line_addr == ctx_addr[0]))
      $fatal(1, "snoop-waiting context incorrectly granted before its response");
    if (dir_write_valid && (dir_write_line_addr == ctx_addr[0]))
      $fatal(1, "snoop-waiting context committed before its response");
    if (protocol_error) $fatal(1, "protocol error while other MSHRs made progress");
    $display("COV_EVENT: id=mshr_bank.snoop_independence checker=PASS old_state=DIR_U requester=0 opcode=GetS_plus_GetS snoop_target=owner1 new_state=mixed data_source=owner_plus_memory beats=8 contexts=4");
    $display("PASS: snoop-blocked Directory context does not block three independent MSHRs");
