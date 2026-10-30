    // Reset all four allocated contexts while their refill starts are stalled.
    reset_bank();
    for (integer i = 0; i < NUM_MSHRS; i++) begin
      ctx_seen[i] = 1'b0;
      ctx_written[i] = 1'b0;
      ctx_addr[i] = 32'h0000_7000 + (i * 64);
      ctx_txn[i] = TXN_ID_WIDTH'(i + 9);
      ctx_src[i] = i[0];
      send_request(ctx_addr[i], ctx_src[i], ctx_txn[i], DIR_I, 2'b00, 1'b0);
    end
    @(negedge clock);
    req_valid = 1'b1;
    req_line_addr = 32'h0000_8000;
    lookup_dir_state = DIR_I;
    #1;
    if (req_ready) $fatal(1, "expected four live contexts before reset");
    req_valid = 1'b0;
    reset_bank();
    if (line_xfer_start_valid || dir_write_valid || grant_valid || snoop_req_valid ||
        protocol_error)
      $fatal(1, "outputs or error state survived reset cancellation");
    $display("COV_EVENT: id=mshr_bank.reset_cancel checker=PASS old_state=mixed requester=multiple opcode=GetS_plus_Reset snoop_target=none new_state=I data_source=none beats=0 contexts=4");
    $display("PASS: reset cancels four simultaneously active Directory contexts");
    $display("PASS: Directory MSHR bank directed stress completed");
    $finish;
  end
