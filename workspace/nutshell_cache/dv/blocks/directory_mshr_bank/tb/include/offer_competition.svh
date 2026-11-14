    for (integer first = 1; first < NUM_MSHRS; first++) begin : offer_competition
      // Selected context offers first while context0 is still waiting for memory.
      // Completing context0 creates a higher-priority competitor. The
      // pre-existing offer must retain every payload field until acceptance.
      reset_bank();
      for (integer i = 0; i <= first; i++) begin
        ctx_addr[i] = 32'h00d0_2000 + 64*i + 4096*first;
        ctx_src[i] = i[0]; ctx_txn[i] = TXN_ID_WIDTH'(i+5);
        ctx_seen[i] = 0; ctx_written[i] = 0;
        send_request(ctx_addr[i], ctx_src[i], ctx_txn[i], DIR_I, 0, 0);
      end
      line_xfer_start_ready = 1;
      collect_xfers(first+1);
      @(negedge clock); line_xfer_start_ready = 0;
      complete_xfer(CTX_W'(first));
      repeat (3) @(posedge clock);
      if (!dir_write_valid || dir_write_line_addr != ctx_addr[first])
        $fatal(1, "selected context did not establish first write offer");
      complete_xfer(CTX_W'(0));
      repeat (4) begin
        @(posedge clock); #1;
        if (!dir_write_valid || dir_write_line_addr != ctx_addr[first] ||
            dir_write_state != DIR_U || dir_write_sharers != 0 || dir_write_owner_id != ctx_src[first])
          $fatal(1, "later higher-priority context preempted write offer");
      end
      // Accept only selected context metadata; its grant now establishes a locked
      // offer before context0 becomes grant-eligible.
      accept_directory_writes(1);
      repeat (3) @(posedge clock);
      if (!grant_valid || grant_txn_id != ctx_txn[first])
        $fatal(1, "selected context grant did not establish offer");
      accept_directory_writes(1);
      repeat (4) begin
        @(posedge clock); #1;
        if (!grant_valid || grant_line_addr != ctx_addr[first] ||
            grant_txn_id != ctx_txn[first] || grant_dst_id != ctx_src[first] ||
            grant_opcode != GRANT_DATA_E || !grant_has_data)
          $fatal(1, "later higher-priority context preempted grant offer");
      end
      accept_grants(2);
      // Remaining contexts complete after the locked winner and competitor.
      for (integer tail = 1; tail < first; tail++) complete_xfer(CTX_W'(tail));
      if (first > 1) begin
        accept_directory_writes(first-1);
        accept_grants(first-1);
      end
      repeat (3) @(posedge clock);
      if (monitor_active_contexts != 0 || protocol_error)
        $fatal(1, "competing offers did not retire both contexts exactly once");
      $display("PASS: context%0d write/grant offer survives context0 competition and all contexts retire", first);
    end
