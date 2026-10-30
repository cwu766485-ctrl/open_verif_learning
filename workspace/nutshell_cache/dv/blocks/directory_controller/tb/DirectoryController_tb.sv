module DirectoryController_tb;
  import coherence_protocol_pkg::*;

  logic clock = 0;
  logic reset = 1;
  always #5 clock = ~clock;

  logic req_valid, req_ready, req_src_id;
  request_opcode_t req_opcode;
  logic [31:0] req_line_addr;
  logic [TXN_ID_WIDTH-1:0] req_txn_id;
  directory_state_t lookup_dir_state;
  logic [1:0] lookup_sharers;
  logic lookup_owner_id;
  logic dir_write_valid, dir_write_ready;
  logic [31:0] dir_write_line_addr;
  directory_state_t dir_write_state;
  logic [1:0] dir_write_sharers;
  logic dir_write_owner_id;
  logic snoop_req_valid, snoop_req_ready, snoop_target_id;
  snoop_opcode_t snoop_req_opcode;
  logic [31:0] snoop_req_line_addr;
  logic [TXN_ID_WIDTH-1:0] snoop_req_txn_id;
  logic snoop_rsp_valid, snoop_rsp_ready, snoop_rsp_src_id;
  snoop_response_t snoop_rsp_opcode;
  logic [TXN_ID_WIDTH-1:0] snoop_rsp_txn_id;
  logic line_xfer_start_valid, line_xfer_start_ready;
  line_xfer_kind_t line_xfer_kind;
  logic [31:0] line_xfer_addr;
  logic line_xfer_src_id;
  logic [TXN_ID_WIDTH-1:0] line_xfer_txn_id;
  logic line_xfer_done_valid, line_xfer_done_ready;
  logic [TXN_ID_WIDTH-1:0] line_xfer_done_txn_id;
  logic grant_valid, grant_ready, grant_dst_id, grant_has_data;
  grant_opcode_t grant_opcode;
  logic [31:0] grant_line_addr;
  logic [TXN_ID_WIDTH-1:0] grant_txn_id;
  logic grant_commit_valid, grant_commit_ready;
  logic [TXN_ID_WIDTH-1:0] grant_commit_txn_id;
  logic snoop_data_to_l2, protocol_error;
  logic [3:0] protocol_error_code;

  DirectoryController dut (.*);

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

  initial begin
    req_valid = 0; req_src_id = 0; req_opcode = REQ_GETS;
    req_line_addr = 0; req_txn_id = 0;
    lookup_dir_state = DIR_I; lookup_sharers = 0; lookup_owner_id = 0;
    dir_write_ready = 0; snoop_req_ready = 0; snoop_rsp_valid = 0;
    snoop_rsp_src_id = 0; snoop_rsp_opcode = SNOOP_RSP_ACK;
    snoop_rsp_txn_id = 0; line_xfer_start_ready = 0;
    line_xfer_done_valid = 0; line_xfer_done_txn_id = 0;
    grant_ready = 0; grant_commit_valid = 0; grant_commit_txn_id = 0;
    repeat (3) tick();
    @(negedge clock); reset = 0;

    // GetS on an invalid line fetches from L2, installs U ownership, then
    // completes the requester grant/commit handshake.
    issue_req(0, REQ_GETS, 32'h3000_0018, 4'h1, DIR_I, 0, 0);
    finish_xfer(4'h1, 32'h3000_0000, XFER_L2_REFILL);
    finish_commit(DIR_U, 2'b00, 0);
    finish_grant(4'h1, GRANT_DATA_E, 1, 0);

    // A remote GetS snoops the U owner for current data, then commits S with
    // both cores recorded as sharers.
    issue_req(1, REQ_GETS, 32'h3000_0008, 4'h2, DIR_U, 0, 0);
    finish_snoop(0, SNOOP_READ, 4'h2, SNOOP_RSP_DATA, 1);
    finish_commit(DIR_S, 2'b11, 0);
    finish_grant(4'h2, GRANT_DATA_S, 1, 1);

    // Upgrade from one of two sharers invalidates the other copy before
    // granting M without another data refill.
    issue_req(0, REQ_UPGRADE, 32'h3000_0030, 4'h3, DIR_S, 2'b11, 0);
    finish_snoop(1, SNOOP_INVALIDATE, 4'h3, SNOOP_RSP_INV_ACK, 0);
    finish_commit(DIR_U, 2'b00, 0);
    finish_grant(4'h3, GRANT_M, 0, 0);

    // GetM from I fetches data and installs M ownership.
    issue_req(1, REQ_GETM, 32'h3000_0010, 4'h4, DIR_I, 0, 0);
    finish_xfer(4'h4, 32'h3000_0000, XFER_L2_REFILL);
    finish_commit(DIR_U, 2'b00, 1);
    finish_grant(4'h4, GRANT_DATA_M, 1, 1);

    // Remote GetM invalidates the current U owner and requires its latest data.
    issue_req(0, REQ_GETM, 32'h3000_0020, 4'h5, DIR_U, 0, 1);
    finish_snoop(1, SNOOP_INVALIDATE, 4'h5, SNOOP_RSP_DATA, 1);
    finish_commit(DIR_U, 2'b00, 0);
    finish_grant(4'h5, GRANT_DATA_M, 1, 0);

    // GetM from S invalidates the peer, refills the line, and then grants M.
    issue_req(0, REQ_GETM, 32'h3000_0038, 4'h6, DIR_S, 2'b11, 0);
    finish_snoop(1, SNOOP_INVALIDATE, 4'h6, SNOOP_RSP_INV_ACK, 0);
    finish_xfer(4'h6, 32'h3000_0000, XFER_L2_REFILL);
    finish_commit(DIR_U, 2'b00, 0);
    finish_grant(4'h6, GRANT_DATA_M, 1, 0);

    // PutS removes only the caller; PutE releases a clean U owner; PutM
    // explicitly drains dirty data before returning PutAck.
    issue_req(0, REQ_PUTS, 32'h3000_0010, 4'h7, DIR_S, 2'b11, 0);
    finish_commit(DIR_S, 2'b10, 0);
    finish_grant(4'h7, GRANT_PUT_ACK, 0, 0);

    issue_req(1, REQ_PUTE, 32'h3000_0018, 4'h8, DIR_U, 0, 1);
    finish_commit(DIR_I, 2'b00, 0);
    finish_grant(4'h8, GRANT_PUT_ACK, 0, 1);

    issue_req(0, REQ_PUTM, 32'h3000_0020, 4'hA, DIR_U, 0, 0);
    finish_xfer(4'hA, 32'h3000_0000, XFER_PUTM_TO_L2);
    finish_commit(DIR_I, 2'b00, 0);
    finish_grant(4'hA, GRANT_PUT_ACK, 0, 0);

    if (protocol_error) $fatal(1, "unexpected Directory protocol_error");

    // Reset in a blocked L2 refill request clears the active Directory txn.
    @(negedge clock); reset = 1; repeat (2) tick();
    @(negedge clock); reset = 0;
    issue_req(0, REQ_GETS, 32'h3000_0008, 4'hB, DIR_I, 0, 0);
    if (!line_xfer_start_valid) $fatal(1, "reset test missed xfer start state");
    repeat (2) tick();
    if (!line_xfer_start_valid || line_xfer_start_ready)
      $fatal(1, "blocked xfer request did not remain pending");
    @(negedge clock); reset = 1; tick();
    @(negedge clock); reset = 0; #1;
    if (!req_ready || line_xfer_start_valid || dir_write_valid ||
        grant_valid || protocol_error)
      $fatal(1, "reset left stale Directory transaction outputs");

    // A second MSHR may accept a different source/opcode while this context
    // waits for its owner Snoop. Recovery must use this context's latched
    // GetM/core0 fields, not the shared live request payload (Put/GetS/core1).
    issue_req(0, REQ_GETM, 32'h3000_0020, 4'hC, DIR_U, 0, 1);
    if (!snoop_req_valid || snoop_target_id != 1'b1 ||
        snoop_req_opcode != SNOOP_INVALIDATE || snoop_req_txn_id != 4'hC)
      $fatal(1, "concurrent-context replay missed owner Snoop");
    snoop_req_ready = 1;
    tick();
    @(negedge clock);
    snoop_req_ready = 0;
    req_src_id = 1;
    req_opcode = REQ_GETS;
    req_line_addr = 32'h5000_0040;
    req_txn_id = 4'hD;
    snoop_rsp_valid = 1;
    snoop_rsp_src_id = 1;
    snoop_rsp_txn_id = 4'hC;
    snoop_rsp_opcode = SNOOP_RSP_INV_ACK;
    #1;
    if (!snoop_rsp_ready) $fatal(1, "owner-missing Snoop response was not accepted");
    tick();
    @(negedge clock);
    snoop_rsp_valid = 0;
    if (!line_xfer_start_valid || line_xfer_kind != XFER_L2_REFILL ||
        line_xfer_addr != 32'h3000_0000 || line_xfer_txn_id != 4'hC ||
        line_xfer_src_id != 1'b0)
      $fatal(1, "GetM recovery used the competing context payload");
    finish_xfer(4'hC, 32'h3000_0000, XFER_L2_REFILL);
    finish_commit(DIR_U, 2'b00, 1'b0);
    finish_grant(4'hC, GRANT_DATA_M, 1, 0);
    if (protocol_error) $fatal(1, "context-payload recovery raised protocol error");

    // If an owner disappears while a blocking replacement commits Put, a
    // GetS-only ACK retries from the current L2 copy and grants E to requester.
    @(negedge clock); reset = 1; repeat (2) tick();
    @(negedge clock); reset = 0;
    issue_req(1, REQ_GETS, 32'h3000_0008, 4'h9, DIR_U, 0, 0);
    snoop_req_ready = 1; tick(); @(negedge clock); snoop_req_ready = 0;
    snoop_rsp_valid = 1; snoop_rsp_src_id = 0;
    snoop_rsp_txn_id = 4'h9; snoop_rsp_opcode = SNOOP_RSP_ACK;
    #1; if (!snoop_rsp_ready) $fatal(1, "matching malformed Snoop response not accepted");
    tick(); @(negedge clock); snoop_rsp_valid = 0;
    if (!line_xfer_start_valid || line_xfer_kind != XFER_L2_REFILL ||
        line_xfer_addr != 32'h3000_0000 || line_xfer_txn_id != 4'h9 ||
        line_xfer_src_id != 1'b1)
      $fatal(1, "GetS owner-miss recovery transfer mismatch");
    finish_xfer(4'h9, 32'h3000_0000, XFER_L2_REFILL);
    finish_commit(DIR_U, 2'b00, 1'b1);
    finish_grant(4'h9, GRANT_DATA_E, 1, 1);
    if (protocol_error) $fatal(1, "GetS owner-miss recovery raised protocol error");
    $display("PASS DirectoryController_tb");
    $finish;
  end
endmodule
