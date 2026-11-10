    begin : offer_competition
      // Context1 offers first while context0 is still waiting for memory.
      // Completing context0 creates a higher-priority competitor. The
      // pre-existing offer must retain every payload field until acceptance.
      reset_bank();
      for (integer i = 0; i < 2; i++) begin
        ctx_addr[i] = 32'h00d0_2000 + 64*i;
        ctx_src[i] = i[0]; ctx_txn[i] = TXN_ID_WIDTH'(i+5);
        ctx_seen[i] = 0; ctx_written[i] = 0;
        send_request(ctx_addr[i], ctx_src[i], ctx_txn[i], DIR_I, 0, 0);
      end
      line_xfer_start_ready = 1;
      collect_xfers(2);
      @(negedge clock); line_xfer_start_ready = 0;
      complete_xfer(CTX_W'(1));
      repeat (3) @(posedge clock);
      if (!dir_write_valid || dir_write_line_addr != ctx_addr[1])
        $fatal(1, "context1 did not establish first write offer");
      complete_xfer(CTX_W'(0));
      repeat (4) begin
        @(posedge clock); #1;
        if (!dir_write_valid || dir_write_line_addr != ctx_addr[1] ||
            dir_write_state != DIR_U || dir_write_sharers != 0 || dir_write_owner_id != 1)
          $fatal(1, "later higher-priority context preempted write offer");
      end
      // Accept only context1 metadata; its grant now establishes a locked
      // offer before context0 becomes grant-eligible.
      accept_directory_writes(1);
      repeat (3) @(posedge clock);
      if (!grant_valid || grant_txn_id != ctx_txn[1])
        $fatal(1, "context1 grant did not establish offer");
      accept_directory_writes(1);
      repeat (4) begin
        @(posedge clock); #1;
        if (!grant_valid || grant_line_addr != ctx_addr[1] ||
            grant_txn_id != ctx_txn[1] || grant_dst_id != 1 ||
            grant_opcode != GRANT_DATA_E || !grant_has_data)
          $fatal(1, "later higher-priority context preempted grant offer");
      end
      accept_grants(2);
      repeat (3) @(posedge clock);
      if (monitor_active_contexts != 0 || protocol_error)
        $fatal(1, "competing offers did not retire both contexts exactly once");
      $display("PASS: write/grant offers remain stable under later higher-priority context competition");
    end
