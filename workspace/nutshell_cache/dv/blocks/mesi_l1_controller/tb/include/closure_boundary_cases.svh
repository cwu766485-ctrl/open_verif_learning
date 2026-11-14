    // Local hit paths and malformed lookup/Grant inputs are independently
    // injected at block ports; no FSM manipulation.
    for (integer mode = 0; mode < 4; mode++) begin
      @(negedge clock); reset = 1; repeat (2) tick();
      @(negedge clock); reset = 0;
      cpu_req_valid = 1; cpu_req_hit = 1; cpu_req_addr = 32'h1200_0040;
      cpu_req_write = (mode == 1); cpu_req_line_state = mode == 2 ? MESI_I : MESI_M;
      if (mode == 3) begin cpu_req_hit = 0; cpu_req_write = 0; end
      #1; if (!cpu_req_ready) $fatal(1, "boundary CPU request not ready");
      tick(); @(negedge clock); cpu_req_valid = 0;
      if (mode < 2) begin
        if (!cpu_resp_valid || cpu_resp_addr != 32'h1200_0040 || cpu_resp_write != (mode == 1) ||
            dir_req_valid || protocol_error) $fatal(1, "local hit response incorrect");
        cpu_resp_ready = 1; tick(); @(negedge clock); cpu_resp_ready = 0;
      end else if (mode == 3) begin
        dir_req_ready = 1; tick(); @(negedge clock); dir_req_ready = 0;
        grant_valid = 1; grant_txn_id = dir_req_txn_id; grant_opcode = GRANT_PUT_ACK;
        #1; if (!grant_ready) $fatal(1, "matching unexpected Grant not ready");
        tick(); @(negedge clock); grant_valid = 0;
      end
      if (mode >= 2) begin
        repeat (3) begin
          tick();
          if (!protocol_error || cpu_resp_valid || dir_req_valid || grant_commit_valid)
            $fatal(1, "lookup/Grant fault escaped fail-stop");
        end
      end
    end
    for (integer inv = 0; inv < 2; inv++) begin
      @(negedge clock); reset = 1; repeat (2) tick();
      @(negedge clock); reset = 0;
      snoop_valid = 1; snoop_line_addr = 32'h1200_0080; snoop_tag_hit = 0;
      snoop_line_state = MESI_I; snoop_opcode = inv ? SNOOP_INVALIDATE : SNOOP_READ;
      snoop_txn_id = 6;
      #1; if (!snoop_ready) $fatal(1, "tag-miss Snoop not ready");
      tick(); @(negedge clock); snoop_valid = 0;
      repeat (3) begin
        #1;
        if (!snoop_rsp_valid || snoop_rsp_has_data || snoop_rsp_txn_id != 6 ||
            snoop_rsp_opcode != (inv ? SNOOP_RSP_INV_ACK : SNOOP_RSP_ACK) ||
            snoop_meta_write_valid || snoop_line_rd_valid || protocol_error)
          $fatal(1, "tag-miss Snoop response incorrect");
        tick();
      end
      @(negedge clock); snoop_rsp_ready = 1; tick();
      @(negedge clock); snoop_rsp_ready = 0;
    end
    $display("PASS: local-hit, lookup/Grant faults and absent-line Snoop boundary cases");
