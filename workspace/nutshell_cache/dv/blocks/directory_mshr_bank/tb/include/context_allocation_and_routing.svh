    // Four distinct lines occupy the complete bank. Duplicate-line and fifth
    // line requests must be backpressured while the four contexts are live.
    for (integer i = 0; i < NUM_MSHRS; i++)
      send_request(ctx_addr[i], ctx_src[i], ctx_txn[i], DIR_I, 2'b00, 1'b0);
    if (monitor_active_contexts !== {NUM_MSHRS{1'b1}})
      $fatal(1, "active-context monitor mismatch after allocation: %b",
             monitor_active_contexts);
    @(negedge clock);
    req_valid = 1'b1;
    req_opcode = REQ_GETS;
    req_src_id = 1'b0;
    req_txn_id = 4'hd;
    req_line_addr = ctx_addr[0];
    lookup_dir_state = DIR_I;
    #1;
    if (req_ready) $fatal(1, "duplicate line was not suppressed");
    req_line_addr = 32'h0000_5000;
    #1;
    if (req_ready) $fatal(1, "full four-context bank accepted a fifth request");
    req_valid = 1'b0;
    $display("COV_EVENT: id=mshr_bank.duplicate_suppression checker=PASS old_state=I requester=multiple opcode=GetS_duplicate snoop_target=none new_state=I data_source=none beats=0 contexts=4");

    line_xfer_start_ready = 1'b1;
    collect_xfers(NUM_MSHRS);
    // Complete fills in reverse context order to exercise independent context
    // routing rather than a FIFO-only completion assumption.
    for (integer i = NUM_MSHRS-1; i >= 0; i--)
      complete_xfer(CTX_W'(i));
    accept_directory_writes(NUM_MSHRS);
    accept_grants(NUM_MSHRS);
    if (protocol_error) $fatal(1, "protocol error during four-context test");
    $display("COV_EVENT: id=mshr_bank.four_contexts checker=PASS old_state=I requester=multiple opcode=GetS snoop_target=none new_state=DIR_U data_source=L2_refill beats=8 contexts=4");
    $display("PASS: Directory MSHR bank routes four distinct contexts and out-of-order fills");

    // Different lines in one L2 set must not retain simultaneous directory
    // snapshots: a miss can reclaim any way in the set while a prior grant is
    // still pending. The second request is accepted after the first commits.
    reset_bank();
    ctx_addr[0] = 32'h0000_9000;
    ctx_addr[1] = 32'h0001_1000; // same [14:6] L2 set as 0x9000
    ctx_txn[0] = TXN_ID_WIDTH'(1);
    ctx_txn[1] = TXN_ID_WIDTH'(2);
    ctx_src[0] = 1'b0;
    ctx_src[1] = 1'b1;
    ctx_seen[0] = 1'b0;
    ctx_written[0] = 1'b0;
    line_xfer_start_ready = 1'b0;
    send_request(ctx_addr[0], ctx_src[0], ctx_txn[0], DIR_I, 2'b00, 1'b0);
    @(negedge clock);
    req_valid = 1'b1;
    req_src_id = ctx_src[1];
    req_txn_id = ctx_txn[1];
    req_line_addr = ctx_addr[0];
    lookup_dir_state = DIR_I;
    #1;
    if (req_ready) $fatal(1, "same-line ownership request was not serialized");
    req_opcode = REQ_PUTS;
    req_src_id = 1'b1;
    #1;
    if (req_ready)
      $fatal(1, "same-line Put raced an ownership snapshot without a snoop dependency");
    $display("COV_EVENT: id=mshr_bank.same_line_put_serialization checker=PASS old_state=DIR_I requester=Core1 opcode=PutS snoop_target=none new_state=I data_source=none beats=0 contexts=1");
    req_opcode = REQ_GETS;
    req_src_id = ctx_src[1];
    req_line_addr = ctx_addr[1];
    #1;
    if (req_ready) $fatal(1, "same-L2-set Directory context was not serialized");
    req_opcode = REQ_PUTS;
    req_src_id = 1'b1;
    req_line_addr = ctx_addr[1];
    lookup_dir_state = DIR_S;
    lookup_sharers = 2'b10;
    #1;
    if (!req_ready)
      $fatal(1, "same-set Put was blocked behind an active ownership transaction");
    $display("COV_EVENT: id=mshr_bank.same_set_put_bypass checker=PASS old_state=DIR_S requester=Core1 opcode=PutS snoop_target=none new_state=DIR_I data_source=none beats=0 contexts=1");
    req_valid = 1'b0;
    line_xfer_start_ready = 1'b1;
    collect_xfers(1);
    complete_xfer(CTX_W'(0));
    accept_directory_writes(1);
    accept_grants(1);
    send_request(ctx_addr[1], ctx_src[1], ctx_txn[1], DIR_I, 2'b00, 1'b0);
    $display("COV_EVENT: id=mshr_bank.same_set_serialization checker=PASS old_state=I requester=multiple opcode=GetS_same_set snoop_target=none new_state=DIR_U data_source=L2_refill beats=8 contexts=1");
    if (protocol_error || protocol_error_code != 0)
      $fatal(1, "protocol error during same-set serialization test code=%0d",
             protocol_error_code);
    reset_bank();
