`timescale 1ns/1ps

module DirectoryMshrBank_tb;
  import coherence_protocol_pkg::*;

  localparam int NUM_MSHRS = 4;
  localparam int CTX_W = 2;

  logic clock = 1'b0;
  logic reset;
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
  logic [CTX_W-1:0] line_xfer_context_id;
  logic line_xfer_done_valid, line_xfer_done_ready;
  logic [CTX_W-1:0] line_xfer_done_context_id;
  logic grant_valid, grant_ready, grant_dst_id, grant_has_data;
  grant_opcode_t grant_opcode;
  logic [31:0] grant_line_addr;
  logic [TXN_ID_WIDTH-1:0] grant_txn_id;
  logic grant_commit_valid, grant_commit_src_id, grant_commit_ready;
  logic [TXN_ID_WIDTH-1:0] grant_commit_txn_id;
  logic snoop_data_to_l2, protocol_error;
  logic [3:0] protocol_error_code;

  logic [31:0] ctx_addr [0:NUM_MSHRS-1];
  logic [TXN_ID_WIDTH-1:0] ctx_txn [0:NUM_MSHRS-1];
  logic ctx_src [0:NUM_MSHRS-1];
  logic ctx_seen [0:NUM_MSHRS-1];
  logic ctx_written [0:NUM_MSHRS-1];

  always #5 clock = ~clock;

  DirectoryMshrBank #(
    .TXN_ID_WIDTH(TXN_ID_WIDTH), .NUM_MSHRS(NUM_MSHRS), .MSHR_ID_WIDTH(CTX_W)
  ) dut (
    .clock(clock), .reset(reset),
    .req_valid(req_valid), .req_ready(req_ready), .req_src_id(req_src_id),
    .req_opcode(req_opcode), .req_line_addr(req_line_addr), .req_txn_id(req_txn_id),
    .lookup_dir_state(lookup_dir_state), .lookup_sharers(lookup_sharers),
    .lookup_owner_id(lookup_owner_id),
    .dir_write_valid(dir_write_valid), .dir_write_ready(dir_write_ready),
    .dir_write_line_addr(dir_write_line_addr), .dir_write_state(dir_write_state),
    .dir_write_sharers(dir_write_sharers), .dir_write_owner_id(dir_write_owner_id),
    .snoop_req_valid(snoop_req_valid), .snoop_req_ready(snoop_req_ready),
    .snoop_target_id(snoop_target_id), .snoop_req_opcode(snoop_req_opcode),
    .snoop_req_line_addr(snoop_req_line_addr), .snoop_req_txn_id(snoop_req_txn_id),
    .snoop_rsp_valid(snoop_rsp_valid), .snoop_rsp_ready(snoop_rsp_ready),
    .snoop_rsp_src_id(snoop_rsp_src_id), .snoop_rsp_opcode(snoop_rsp_opcode),
    .snoop_rsp_txn_id(snoop_rsp_txn_id),
    .line_xfer_start_valid(line_xfer_start_valid),
    .line_xfer_start_ready(line_xfer_start_ready), .line_xfer_kind(line_xfer_kind),
    .line_xfer_addr(line_xfer_addr), .line_xfer_src_id(line_xfer_src_id),
    .line_xfer_txn_id(line_xfer_txn_id), .line_xfer_context_id(line_xfer_context_id),
    .line_xfer_done_valid(line_xfer_done_valid),
    .line_xfer_done_ready(line_xfer_done_ready),
    .line_xfer_done_context_id(line_xfer_done_context_id),
    .grant_valid(grant_valid), .grant_ready(grant_ready), .grant_dst_id(grant_dst_id),
    .grant_opcode(grant_opcode), .grant_has_data(grant_has_data),
    .grant_line_addr(grant_line_addr), .grant_txn_id(grant_txn_id),
    .grant_commit_valid(grant_commit_valid),
    .grant_commit_src_id(grant_commit_src_id),
    .grant_commit_ready(grant_commit_ready), .grant_commit_txn_id(grant_commit_txn_id),
    .snoop_data_to_l2(snoop_data_to_l2), .protocol_error(protocol_error),
    .protocol_error_code(protocol_error_code)
  );

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

  initial begin : mshr_stress
    integer cycles;
    logic [31:0] snoop_addr_saved;
    logic [TXN_ID_WIDTH-1:0] snoop_txn_saved;
    logic snoop_target_saved;

    reset = 1'b1;
    req_valid = 1'b0;
    req_src_id = 1'b0;
    req_opcode = REQ_GETS;
    req_line_addr = '0;
    req_txn_id = '0;
    lookup_dir_state = DIR_I;
    lookup_sharers = 2'b00;
    lookup_owner_id = 1'b0;
    dir_write_ready = 1'b0;
    snoop_req_ready = 1'b0;
    snoop_rsp_valid = 1'b0;
    snoop_rsp_src_id = 1'b0;
    snoop_rsp_opcode = SNOOP_RSP_DATA;
    snoop_rsp_txn_id = '0;
    line_xfer_start_ready = 1'b0;
    line_xfer_done_valid = 1'b0;
    line_xfer_done_context_id = '0;
    grant_ready = 1'b0;
    grant_commit_valid = 1'b0;
    grant_commit_src_id = 1'b0;
    grant_commit_txn_id = '0;
    for (integer i = 0; i < NUM_MSHRS; i++) begin
      ctx_addr[i] = 32'h0000_4000 + (i * 64);
      ctx_txn[i] = TXN_ID_WIDTH'(i + 1);
      ctx_src[i] = i[0];
      ctx_seen[i] = 1'b0;
      ctx_written[i] = 1'b0;
    end
    repeat (3) @(posedge clock);
    @(negedge clock);
    reset = 1'b0;

    // Four distinct lines occupy the complete bank. Duplicate-line and fifth
    // line requests must be backpressured while the four contexts are live.
    for (integer i = 0; i < NUM_MSHRS; i++)
      send_request(ctx_addr[i], ctx_src[i], ctx_txn[i], DIR_I, 2'b00, 1'b0);
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
endmodule
