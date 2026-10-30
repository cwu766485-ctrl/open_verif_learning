  task automatic tick;
    @(posedge clock); #1;
  endtask

  task automatic issue_req(input logic src, input request_opcode_t op,
                           input logic [31:0] addr,
                           input logic [TXN_ID_WIDTH-1:0] txn,
                           input directory_state_t state,
                           input logic [1:0] sharers,
                           input logic owner);
    @(negedge clock);
    req_valid = 1; req_src_id = src; req_opcode = op;
    req_line_addr = addr; req_txn_id = txn;
    lookup_dir_state = state; lookup_sharers = sharers;
    lookup_owner_id = owner; #1;
    if (!req_ready) $fatal(1, "Directory request not ready");
    tick(); @(negedge clock); req_valid = 0;
  endtask

  task automatic finish_xfer(input logic [TXN_ID_WIDTH-1:0] txn,
                             input logic [31:0] addr,
                             input line_xfer_kind_t kind);
    if (!line_xfer_start_valid || line_xfer_kind != kind ||
        line_xfer_addr != addr || line_xfer_txn_id != txn)
      $fatal(1, "L2 refill transfer header mismatch");
    repeat (2) begin tick(); #1;
      if (!line_xfer_start_valid || line_xfer_kind != kind ||
          line_xfer_addr != addr || line_xfer_txn_id != txn)
        $fatal(1, "line transfer request changed under backpressure");
    end
    @(negedge clock);
    line_xfer_start_ready = 1; tick(); @(negedge clock);
    line_xfer_start_ready = 0; line_xfer_done_valid = 1;
    line_xfer_done_txn_id = txn; #1;
    if (!line_xfer_done_ready) $fatal(1, "matching line transfer completion rejected");
    tick(); @(negedge clock); line_xfer_done_valid = 0;
  endtask

  task automatic finish_snoop(input logic target, input snoop_opcode_t op,
                              input logic [TXN_ID_WIDTH-1:0] txn,
                              input snoop_response_t response,
                              input logic data_expected);
    if (!snoop_req_valid || snoop_target_id != target ||
        snoop_req_opcode != op || snoop_req_txn_id != txn ||
        snoop_req_line_addr != 32'h3000_0000 ||
        snoop_data_to_l2 != data_expected)
      $fatal(1, "Snoop request fields mismatch");
    repeat (2) begin tick(); #1;
      if (!snoop_req_valid || snoop_target_id != target ||
          snoop_req_opcode != op || snoop_req_txn_id != txn)
        $fatal(1, "Snoop request changed under backpressure");
    end
    @(negedge clock);
    snoop_req_ready = 1; tick(); @(negedge clock); snoop_req_ready = 0;
    snoop_rsp_valid = 1; snoop_rsp_src_id = target;
    snoop_rsp_txn_id = txn; snoop_rsp_opcode = response; #1;
    if (!snoop_rsp_ready) $fatal(1, "matching Snoop response not accepted");
    snoop_rsp_txn_id = txn ^ 4'h1; #1;
    if (snoop_rsp_ready) $fatal(1, "wrong-ID Snoop response was accepted");
    repeat (2) tick();
    @(negedge clock); snoop_rsp_txn_id = txn; #1;
    if (!snoop_rsp_ready) $fatal(1, "matching Snoop response was lost after stall");
    tick(); @(negedge clock); snoop_rsp_valid = 0;
  endtask

  task automatic finish_commit(input directory_state_t state,
                               input logic [1:0] sharers,
                               input logic owner);
    if (!dir_write_valid || dir_write_line_addr != 32'h3000_0000 ||
        dir_write_state != state || dir_write_sharers != sharers ||
        dir_write_owner_id != owner)
      $fatal(1, "directory metadata commit mismatch: addr=%08x state=%0d sharers=%b owner=%b expected=%08x/%0d/%b/%b",
             dir_write_line_addr, dir_write_state, dir_write_sharers,
             dir_write_owner_id, 32'h3000_0000, state, sharers, owner);
    repeat (2) begin tick(); #1;
      if (!dir_write_valid || dir_write_state != state ||
          dir_write_sharers != sharers || dir_write_owner_id != owner)
        $fatal(1, "directory metadata changed under backpressure");
    end
    @(negedge clock);
    dir_write_ready = 1; tick(); @(negedge clock); dir_write_ready = 0;
  endtask

  task automatic finish_grant(input logic [TXN_ID_WIDTH-1:0] txn,
                              input grant_opcode_t op,
                              input logic has_data,
                              input logic dst);
    if (!grant_valid || grant_dst_id != dst || grant_opcode != op ||
        grant_has_data != has_data || grant_line_addr != 32'h3000_0000 ||
        grant_txn_id != txn)
      $fatal(1, "grant header mismatch");
    repeat (2) begin tick(); #1;
      if (!grant_valid || grant_opcode != op || grant_txn_id != txn ||
          grant_dst_id != dst || grant_has_data != has_data)
        $fatal(1, "grant header changed under backpressure");
    end
    @(negedge clock);
    grant_ready = 1; tick(); @(negedge clock); grant_ready = 0;
    grant_commit_valid = 1; grant_commit_txn_id = txn ^ 4'h1; #1;
    if (grant_commit_ready) $fatal(1, "wrong-ID grant commit was accepted");
    repeat (2) tick();
    @(negedge clock); grant_commit_txn_id = txn; #1;
    if (!grant_commit_ready) $fatal(1, "matching grant commit not accepted");
    tick(); @(negedge clock); grant_commit_valid = 0;
    tick();
  endtask
