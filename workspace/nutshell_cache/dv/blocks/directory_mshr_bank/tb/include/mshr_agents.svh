  task automatic reset_bank;
    begin
      @(negedge clock);
      reset = 1'b1;
      req_valid = 1'b0;
      snoop_rsp_valid = 1'b0;
      line_xfer_done_valid = 1'b0;
      grant_commit_valid = 1'b0;
      repeat (3) @(posedge clock);
      @(negedge clock);
      reset = 1'b0;
    end
  endtask

  task automatic send_request(
    input logic [31:0] addr,
    input logic src,
    input logic [TXN_ID_WIDTH-1:0] txn,
    input directory_state_t state,
    input logic [1:0] sharers,
    input logic owner
  );
    integer cycles;
    begin
      @(negedge clock);
      req_line_addr = addr;
      req_src_id = src;
      req_txn_id = txn;
      req_opcode = REQ_GETS;
      lookup_dir_state = state;
      lookup_sharers = sharers;
      lookup_owner_id = owner;
      req_valid = 1'b1;
      for (cycles = 0; cycles < 30; cycles++) begin
        @(posedge clock);
        if (req_ready) break;
      end
      if (cycles == 30) $fatal(1, "Directory MSHR request timeout addr=%08x", addr);
      @(negedge clock);
      req_valid = 1'b0;
    end
  endtask

  task automatic collect_xfers(input integer expected_count);
    integer count;
    integer cycles;
    integer idx;
    begin
      count = 0;
      for (cycles = 0; (cycles < 100) && (count < expected_count); cycles++) begin
        @(posedge clock);
        if (line_xfer_start_valid && line_xfer_start_ready) begin
          idx = int'(line_xfer_context_id);
          if ((idx < 0) || (idx >= NUM_MSHRS) || ctx_seen[idx])
            $fatal(1, "invalid/repeated xfer context %0d", idx);
          if (line_xfer_kind != XFER_L2_REFILL)
            $fatal(1, "unexpected xfer kind %0d", line_xfer_kind);
          if (line_xfer_addr !== ctx_addr[idx] || line_xfer_txn_id !== ctx_txn[idx] ||
              line_xfer_src_id !== ctx_src[idx])
            $fatal(1, "xfer payload misrouted ctx=%0d addr=%08x txn=%0d",
                   idx, line_xfer_addr, line_xfer_txn_id);
          ctx_seen[idx] = 1'b1;
          count++;
        end
      end
      if (count != expected_count)
        $fatal(1, "only observed %0d/%0d refill contexts active=%b xfer_valid=%b ready=%b",
               count, expected_count, dut.active_q, dut.xfer_valid_ctx,
               dut.xfer_ready_ctx);
    end
  endtask

  task automatic complete_xfer(input logic [CTX_W-1:0] ctx);
    integer cycles;
    begin
      @(negedge clock);
      line_xfer_done_context_id = ctx;
      line_xfer_done_valid = 1'b1;
      for (cycles = 0; cycles < 30; cycles++) begin
        @(posedge clock);
        if (line_xfer_done_ready) break;
      end
      if (cycles == 30) $fatal(1, "xfer completion timeout ctx=%0d", ctx);
      @(negedge clock);
      line_xfer_done_valid = 1'b0;
    end
  endtask

  task automatic accept_directory_writes(input integer expected_count);
    integer count;
    integer cycles;
    integer idx;
    logic [31:0] held_addr;
    directory_state_t held_state;
    logic [1:0] held_sharers;
    logic held_owner;
    begin
      count = 0;
      dir_write_ready = 1'b0;
      for (count = 0; count < expected_count; count++) begin
        for (cycles = 0; cycles < 100 && !dir_write_valid; cycles++) @(posedge clock);
        if (!dir_write_valid) $fatal(1, "directory write timeout");
        held_addr = dir_write_line_addr;
        held_state = dir_write_state;
        held_sharers = dir_write_sharers;
        held_owner = dir_write_owner_id;
        idx = -1;
        for (integer i = 0; i < NUM_MSHRS; i++)
          if (ctx_addr[i] == held_addr) idx = i;
        if ((idx < 0) || ctx_written[idx] || (held_state != DIR_U) ||
            (held_sharers != 2'b00) || (held_owner != ctx_src[idx]))
          $fatal(1, "bad or duplicate directory update addr=%08x state=%0d", held_addr, held_state);
        repeat (2) begin
          @(posedge clock);
          if (!dir_write_valid || dir_write_line_addr !== held_addr ||
              dir_write_state !== held_state || dir_write_sharers !== held_sharers ||
              dir_write_owner_id !== held_owner)
            $fatal(1, "directory write payload changed under backpressure");
        end
        @(negedge clock);
        dir_write_ready = 1'b1;
        @(posedge clock);
        if (!dir_write_valid) $fatal(1, "directory write vanished before acceptance");
        ctx_written[idx] = 1'b1;
        @(negedge clock);
        dir_write_ready = 1'b0;
      end
    end
  endtask

  task automatic accept_grants(input integer expected_count);
    integer count;
    integer cycles;
    integer idx;
    logic [31:0] saved_addr;
    logic [TXN_ID_WIDTH-1:0] saved_txn;
    logic saved_dst;
    begin
      for (count = 0; count < expected_count; count++) begin
        grant_ready = 1'b0;
        for (cycles = 0; cycles < 100 && !grant_valid; cycles++) @(posedge clock);
        if (!grant_valid) $fatal(1, "grant timeout");
        saved_addr = grant_line_addr;
        saved_txn = grant_txn_id;
        saved_dst = grant_dst_id;
        idx = -1;
        for (integer i = 0; i < NUM_MSHRS; i++)
          if (ctx_addr[i] == saved_addr) idx = i;
        if ((idx < 0) || (ctx_txn[idx] != saved_txn) || (ctx_src[idx] != saved_dst) ||
            !grant_has_data || (grant_opcode != GRANT_DATA_E))
          $fatal(1, "grant misrouted addr=%08x txn=%0d", saved_addr, saved_txn);
        repeat (2) begin
          @(posedge clock);
          if (!grant_valid || grant_line_addr !== saved_addr || grant_txn_id !== saved_txn ||
              grant_dst_id !== saved_dst)
            $fatal(1, "grant changed while backpressured");
        end
        @(negedge clock);
        grant_ready = 1'b1;
        @(posedge clock);
        if (!grant_valid) $fatal(1, "grant vanished before acceptance");
        @(negedge clock);
        grant_ready = 1'b0;
        grant_commit_src_id = saved_dst;
        grant_commit_txn_id = saved_txn;
        grant_commit_valid = 1'b1;
        @(posedge clock);
        if (!grant_commit_ready) $fatal(1, "matching grant commit was not accepted");
        @(negedge clock);
        grant_commit_valid = 1'b0;
      end
    end
  endtask
