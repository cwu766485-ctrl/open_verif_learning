// Four independent Directory transaction contexts with arbitration for the
// single-ported L2 metadata/data controls and the two per-core snoop engines.
// Different cache lines can remain active at once; same-line requests are
// held off until the earlier grant commits.
module DirectoryMshrBank #(
  parameter int TXN_ID_WIDTH = coherence_protocol_pkg::TXN_ID_WIDTH,
  parameter int NUM_MSHRS = 4,
  parameter int L2_SET_INDEX_WIDTH = 9,
  parameter int MSHR_ID_WIDTH = (NUM_MSHRS < 2) ? 1 : $clog2(NUM_MSHRS)
) (
  input logic clock,
  input logic reset,
  input logic req_valid,
  output logic req_ready,
  input logic req_src_id,
  input coherence_protocol_pkg::request_opcode_t req_opcode,
  input logic [31:0] req_line_addr,
  input logic [TXN_ID_WIDTH-1:0] req_txn_id,
  input coherence_protocol_pkg::directory_state_t lookup_dir_state,
  input logic [1:0] lookup_sharers,
  input logic lookup_owner_id,

  output logic dir_write_valid,
  input logic dir_write_ready,
  output logic [31:0] dir_write_line_addr,
  output coherence_protocol_pkg::directory_state_t dir_write_state,
  output logic [1:0] dir_write_sharers,
  output logic dir_write_owner_id,

  output logic snoop_req_valid,
  input logic snoop_req_ready,
  output logic snoop_target_id,
  output coherence_protocol_pkg::snoop_opcode_t snoop_req_opcode,
  output logic [31:0] snoop_req_line_addr,
  output logic [TXN_ID_WIDTH-1:0] snoop_req_txn_id,
  input logic snoop_rsp_valid,
  output logic snoop_rsp_ready,
  input logic snoop_rsp_src_id,
  input coherence_protocol_pkg::snoop_response_t snoop_rsp_opcode,
  input logic [TXN_ID_WIDTH-1:0] snoop_rsp_txn_id,

  output logic line_xfer_start_valid,
  input logic line_xfer_start_ready,
  output coherence_protocol_pkg::line_xfer_kind_t line_xfer_kind,
  output logic [31:0] line_xfer_addr,
  output logic line_xfer_src_id,
  output logic [TXN_ID_WIDTH-1:0] line_xfer_txn_id,
  output logic [MSHR_ID_WIDTH-1:0] line_xfer_context_id,
  input logic line_xfer_done_valid,
  output logic line_xfer_done_ready,
  input logic [MSHR_ID_WIDTH-1:0] line_xfer_done_context_id,

  output logic grant_valid,
  input logic grant_ready,
  output logic grant_dst_id,
  output coherence_protocol_pkg::grant_opcode_t grant_opcode,
  output logic grant_has_data,
  output logic [31:0] grant_line_addr,
  output logic [TXN_ID_WIDTH-1:0] grant_txn_id,
  input logic grant_commit_valid,
  input logic grant_commit_src_id,
  output logic grant_commit_ready,
  input logic [TXN_ID_WIDTH-1:0] grant_commit_txn_id,

  output logic snoop_data_to_l2,
  output logic protocol_error,
  output logic [3:0] protocol_error_code,
  output logic [NUM_MSHRS-1:0] monitor_active_contexts
);
  import coherence_protocol_pkg::*;

  logic [NUM_MSHRS-1:0] active_q;
  logic [31:0] line_addr_q [0:NUM_MSHRS-1];
  logic src_id_q [0:NUM_MSHRS-1];
  logic [TXN_ID_WIDTH-1:0] txn_id_q [0:NUM_MSHRS-1];

  logic [NUM_MSHRS-1:0] req_ready_ctx, req_valid_ctx;
  logic [NUM_MSHRS-1:0] write_valid_ctx, write_ready_ctx;
  logic [31:0] write_addr_ctx [0:NUM_MSHRS-1];
  directory_state_t write_state_ctx [0:NUM_MSHRS-1];
  logic [1:0] write_sharers_ctx [0:NUM_MSHRS-1];
  logic write_owner_ctx [0:NUM_MSHRS-1];
  logic [NUM_MSHRS-1:0] snoop_valid_ctx, snoop_ready_ctx;
  logic snoop_target_ctx [0:NUM_MSHRS-1];
  snoop_opcode_t snoop_opcode_ctx [0:NUM_MSHRS-1];
  logic [31:0] snoop_addr_ctx [0:NUM_MSHRS-1];
  logic [TXN_ID_WIDTH-1:0] snoop_txn_ctx [0:NUM_MSHRS-1];
  logic [NUM_MSHRS-1:0] snoop_rsp_ready_ctx;
  logic [NUM_MSHRS-1:0] xfer_valid_ctx, xfer_ready_ctx;
  line_xfer_kind_t xfer_kind_ctx [0:NUM_MSHRS-1];
  logic [31:0] xfer_addr_ctx [0:NUM_MSHRS-1];
  logic xfer_src_ctx [0:NUM_MSHRS-1];
  logic [TXN_ID_WIDTH-1:0] xfer_txn_ctx [0:NUM_MSHRS-1];
  logic [NUM_MSHRS-1:0] xfer_done_ready_ctx;
  logic [NUM_MSHRS-1:0] grant_valid_ctx, grant_ready_ctx;
  logic grant_dst_ctx [0:NUM_MSHRS-1];
  grant_opcode_t grant_opcode_ctx [0:NUM_MSHRS-1];
  logic grant_has_data_ctx [0:NUM_MSHRS-1];
  logic [31:0] grant_addr_ctx [0:NUM_MSHRS-1];
  logic [TXN_ID_WIDTH-1:0] grant_txn_ctx [0:NUM_MSHRS-1];
  logic [NUM_MSHRS-1:0] grant_commit_ready_ctx;
  logic [NUM_MSHRS-1:0] snoop_data_ctx, error_ctx;
  logic [3:0] error_code_ctx [0:NUM_MSHRS-1];

  logic [MSHR_ID_WIDTH-1:0] write_rr_q, snoop_rr_q, xfer_rr_q, grant_rr_q;
  logic write_offer_lock_q, snoop_offer_lock_q, xfer_offer_lock_q, grant_offer_lock_q;
  logic [MSHR_ID_WIDTH-1:0] write_offer_idx_q, snoop_offer_idx_q;
  logic [MSHR_ID_WIDTH-1:0] xfer_offer_idx_q, grant_offer_idx_q;
  logic snoop_active_q;
  logic [MSHR_ID_WIDTH-1:0] snoop_active_idx_q;
  logic [MSHR_ID_WIDTH-1:0] write_sel, snoop_sel, xfer_sel, grant_sel;
  logic write_found, snoop_found, xfer_found, grant_found;
  logic req_found, duplicate_line;
  logic put_snoop_bypass;
  logic same_line_put_conflict;
  logic same_line_active;
  logic active_set_conflict;
  logic [MSHR_ID_WIDTH-1:0] req_sel;
  logic commit_found;
  logic [MSHR_ID_WIDTH-1:0] commit_sel;
  logic [NUM_MSHRS-1:0] done_valid_ctx;
  logic [NUM_MSHRS-1:0] commit_match_ctx;

  // Request allocation is independent of the output-channel arbiters. Keep
  // req_ready_ctx out of the request-valid path to avoid a false ready/valid
  // combinational cycle through the request arbiter.
  always_comb begin : choose_request_context
    integer i;
    integer first_free;
    req_found = 1'b0;
    duplicate_line = 1'b0;
    put_snoop_bypass = 1'b0;
    same_line_put_conflict = 1'b0;
    same_line_active = 1'b0;
    active_set_conflict = 1'b0;
    req_sel = '0;
    first_free = -1;
    for (i = 0; i < NUM_MSHRS; i = i + 1) begin
      if (!active_q[i] && first_free < 0) first_free = i;
      if (active_q[i]) begin
        if (line_addr_q[i] == line_align(req_line_addr)) begin
          same_line_active = 1'b1;
          if (req_opcode == REQ_GETS || req_opcode == REQ_GETM ||
              req_opcode == REQ_UPGRADE) begin
            duplicate_line = 1'b1;
          end else if (req_opcode == REQ_PUTS || req_opcode == REQ_PUTE ||
                       req_opcode == REQ_PUTM) begin
            // Normally serialize same-line Put with ownership requests too:
            // otherwise their snapshots can commit out of order (for example
            // a GetS retaining a departing sharer after PutS cleared it).
            // The sole bypass is the deadlock escape while this context's
            // snoop offer is stalled at that Put source. A blocking L1
            // replacement cannot accept the snoop until the Put receives its
            // Ack. Once the snoop is accepted, serialize same-line Puts so an
            // older directory snapshot cannot overwrite the Put's commit.
            if (snoop_valid_ctx[i] && !snoop_ready_ctx[i] &&
                (snoop_target_ctx[i] == req_src_id))
              put_snoop_bypass = 1'b1;
            else
              same_line_put_conflict = 1'b1;
          end
        end
        // A live L2 victim is selected from the refill's set. Serialize new
        // ownership requests while a context can still hold a set snapshot.
        // Put transactions must bypass this guard: an L1 can be waiting for
        // its victim PutAck before it is able to service the active context's
        // snoop, so blocking Put here would create a Directory/L1 deadlock.
        if ((req_opcode == REQ_GETS || req_opcode == REQ_GETM ||
             req_opcode == REQ_UPGRADE) &&
            line_addr_q[i][6 +: L2_SET_INDEX_WIDTH] ==
            req_line_addr[6 +: L2_SET_INDEX_WIDTH])
          active_set_conflict = 1'b1;
      end
    end
    if ((req_opcode == REQ_PUTS || req_opcode == REQ_PUTE ||
         req_opcode == REQ_PUTM) &&
        same_line_active && (same_line_put_conflict || !put_snoop_bypass))
      duplicate_line = 1'b1;
    if (first_free >= 0) begin
      req_sel = MSHR_ID_WIDTH'(first_free);
      req_found = !duplicate_line && !active_set_conflict;
    end
    req_ready = req_found && req_ready_ctx[req_sel];
  end

  always_comb begin : route_request_context
    req_valid_ctx = '0;
    if (req_valid && req_found) req_valid_ctx[req_sel] = 1'b1;
  end

  always_comb begin : choose_output_contexts
    integer i;
    integer idx;
    integer selected;
    selected = -1;
    for (i = 0; i < NUM_MSHRS; i = i + 1) begin
      idx = (int'(write_rr_q) + i) % NUM_MSHRS;
      if ((selected < 0) && write_valid_ctx[idx]) selected = idx;
    end
    write_found = (selected >= 0);
    write_sel = write_offer_lock_q ? write_offer_idx_q :
                (write_found ? MSHR_ID_WIDTH'(selected) : '0);

    selected = -1;
    for (i = 0; i < NUM_MSHRS; i = i + 1) begin
      idx = (int'(snoop_rr_q) + i) % NUM_MSHRS;
      if ((selected < 0) && snoop_valid_ctx[idx]) selected = idx;
    end
    snoop_found = (selected >= 0);
    snoop_sel = snoop_active_q ? snoop_active_idx_q :
                snoop_offer_lock_q ? snoop_offer_idx_q :
                (snoop_found ? MSHR_ID_WIDTH'(selected) : '0);

    selected = -1;
    for (i = 0; i < NUM_MSHRS; i = i + 1) begin
      idx = (int'(xfer_rr_q) + i) % NUM_MSHRS;
      if ((selected < 0) && xfer_valid_ctx[idx]) selected = idx;
    end
    xfer_found = (selected >= 0);
    xfer_sel = xfer_offer_lock_q ? xfer_offer_idx_q :
               (xfer_found ? MSHR_ID_WIDTH'(selected) : '0);

    selected = -1;
    for (i = 0; i < NUM_MSHRS; i = i + 1) begin
      idx = (int'(grant_rr_q) + i) % NUM_MSHRS;
      if ((selected < 0) && grant_valid_ctx[idx]) selected = idx;
    end
    grant_found = (selected >= 0);
    grant_sel = grant_offer_lock_q ? grant_offer_idx_q :
                (grant_found ? MSHR_ID_WIDTH'(selected) : '0);

    commit_match_ctx = '0;
    done_valid_ctx = '0;
    if (int'(line_xfer_done_context_id) < NUM_MSHRS)
      done_valid_ctx[line_xfer_done_context_id] = line_xfer_done_valid;
    for (i = 0; i < NUM_MSHRS; i = i + 1) begin
      commit_match_ctx[i] = active_q[i] &&
        (src_id_q[i] == grant_commit_src_id) &&
        (txn_id_q[i] == grant_commit_txn_id);
    end
    selected = -1;
    for (i = 0; i < NUM_MSHRS; i = i + 1)
      if ((selected < 0) && commit_match_ctx[i]) selected = i;
    commit_found = (selected >= 0);
    commit_sel = (selected >= 0) ? MSHR_ID_WIDTH'(selected) : '0;
  end

  always_comb begin : route_channel_payloads
    dir_write_valid = write_found && write_valid_ctx[write_sel];
    dir_write_line_addr = write_addr_ctx[write_sel];
    dir_write_state = write_state_ctx[write_sel];
    dir_write_sharers = write_sharers_ctx[write_sel];
    dir_write_owner_id = write_owner_ctx[write_sel];
    snoop_req_valid = !snoop_active_q && snoop_found && snoop_valid_ctx[snoop_sel];
    snoop_target_id = snoop_target_ctx[snoop_sel];
    snoop_req_opcode = snoop_opcode_ctx[snoop_sel];
    snoop_req_line_addr = snoop_addr_ctx[snoop_sel];
    snoop_req_txn_id = snoop_txn_ctx[snoop_sel];
    snoop_rsp_ready = snoop_active_q &&
                      snoop_rsp_ready_ctx[snoop_active_idx_q];

    line_xfer_start_valid = xfer_found && xfer_valid_ctx[xfer_sel];
    line_xfer_kind = xfer_kind_ctx[xfer_sel];
    line_xfer_addr = xfer_addr_ctx[xfer_sel];
    line_xfer_src_id = xfer_src_ctx[xfer_sel];
    line_xfer_txn_id = xfer_txn_ctx[xfer_sel];
    line_xfer_context_id = xfer_sel;
    line_xfer_done_ready = 1'b0;
    if (line_xfer_done_valid &&
        (int'(line_xfer_done_context_id) < NUM_MSHRS))
      line_xfer_done_ready = xfer_done_ready_ctx[line_xfer_done_context_id];

    grant_valid = grant_found && grant_valid_ctx[grant_sel];
    grant_dst_id = grant_dst_ctx[grant_sel];
    grant_opcode = grant_opcode_ctx[grant_sel];
    grant_has_data = grant_has_data_ctx[grant_sel];
    grant_line_addr = grant_addr_ctx[grant_sel];
    grant_txn_id = grant_txn_ctx[grant_sel];
    grant_commit_ready = commit_found &&
                         grant_commit_ready_ctx[commit_sel];

    snoop_data_to_l2 = snoop_data_ctx[snoop_sel];
    protocol_error = |error_ctx;
    protocol_error_code = 4'd0;
    for (integer i = 0; i < NUM_MSHRS; i = i + 1)
      if (error_ctx[i] && protocol_error_code == 4'd0)
        protocol_error_code = error_code_ctx[i];
  end

  assign monitor_active_contexts = active_q;

  always_comb begin : route_channel_readies
    write_ready_ctx = '0;
    if (dir_write_valid) write_ready_ctx[write_sel] = dir_write_ready;

    snoop_ready_ctx = '0;
    if (snoop_req_valid) snoop_ready_ctx[snoop_sel] = snoop_req_ready;

    xfer_ready_ctx = '0;
    if (line_xfer_start_valid)
      xfer_ready_ctx[xfer_sel] = line_xfer_start_ready;

    grant_ready_ctx = '0;
    if (grant_valid) grant_ready_ctx[grant_sel] = grant_ready;
  end

  always_ff @(posedge clock) begin : arbitration_state
    if (reset) begin
      active_q <= '0;
      write_rr_q <= '0;
      snoop_rr_q <= '0;
      xfer_rr_q <= '0;
      grant_rr_q <= '0;
      write_offer_lock_q <= 1'b0;
      snoop_offer_lock_q <= 1'b0;
      xfer_offer_lock_q <= 1'b0;
      grant_offer_lock_q <= 1'b0;
      write_offer_idx_q <= '0;
      snoop_offer_idx_q <= '0;
      xfer_offer_idx_q <= '0;
      grant_offer_idx_q <= '0;
      snoop_active_q <= 1'b0;
      snoop_active_idx_q <= '0;
      for (integer i = 0; i < NUM_MSHRS; i = i + 1) begin
        line_addr_q[i] <= '0;
        src_id_q[i] <= 1'b0;
        txn_id_q[i] <= '0;
      end
    end else begin
      if (req_valid && req_ready) begin
        active_q[req_sel] <= 1'b1;
        line_addr_q[req_sel] <= line_align(req_line_addr);
        src_id_q[req_sel] <= req_src_id;
        txn_id_q[req_sel] <= req_txn_id;
      end
      if (grant_commit_valid && grant_commit_ready)
        active_q[commit_sel] <= 1'b0;

      if (dir_write_valid && !dir_write_ready && !write_offer_lock_q) begin
        write_offer_lock_q <= 1'b1;
        write_offer_idx_q <= write_sel;
      end else if (dir_write_valid && dir_write_ready) begin
        write_offer_lock_q <= 1'b0;
        write_rr_q <= (write_sel == MSHR_ID_WIDTH'(NUM_MSHRS-1)) ? '0 :
                      write_sel + 1'b1;
      end

      if (snoop_req_valid && !snoop_req_ready && !snoop_offer_lock_q) begin
        snoop_offer_lock_q <= 1'b1;
        snoop_offer_idx_q <= snoop_sel;
      end else if (snoop_req_valid && snoop_req_ready) begin
        snoop_offer_lock_q <= 1'b0;
        snoop_active_q <= 1'b1;
        snoop_active_idx_q <= snoop_sel;
      end
      if (snoop_active_q && snoop_rsp_valid && snoop_rsp_ready) begin
        snoop_active_q <= 1'b0;
        snoop_rr_q <= (snoop_active_idx_q == MSHR_ID_WIDTH'(NUM_MSHRS-1)) ?
                      '0 : snoop_active_idx_q + 1'b1;
      end

      if (line_xfer_start_valid && !line_xfer_start_ready &&
          !xfer_offer_lock_q) begin
        xfer_offer_lock_q <= 1'b1;
        xfer_offer_idx_q <= xfer_sel;
      end else if (line_xfer_start_valid && line_xfer_start_ready) begin
        xfer_offer_lock_q <= 1'b0;
        xfer_rr_q <= (xfer_sel == MSHR_ID_WIDTH'(NUM_MSHRS-1)) ? '0 :
                     xfer_sel + 1'b1;
      end

      if (grant_valid && !grant_ready && !grant_offer_lock_q) begin
        grant_offer_lock_q <= 1'b1;
        grant_offer_idx_q <= grant_sel;
      end else if (grant_valid && grant_ready) begin
        grant_offer_lock_q <= 1'b0;
        grant_rr_q <= (grant_sel == MSHR_ID_WIDTH'(NUM_MSHRS-1)) ? '0 :
                      grant_sel + 1'b1;
      end
    end
  end

  for (genvar c = 0; c < NUM_MSHRS; c = c + 1) begin : contexts
    DirectoryController #(.TXN_ID_WIDTH(TXN_ID_WIDTH)) context_i (
      .clock(clock), .reset(reset),
      .req_valid(req_valid_ctx[c]), .req_ready(req_ready_ctx[c]),
      .req_src_id(req_src_id), .req_opcode(req_opcode),
      .req_line_addr(req_line_addr), .req_txn_id(req_txn_id),
      .lookup_dir_state(lookup_dir_state), .lookup_sharers(lookup_sharers),
      .lookup_owner_id(lookup_owner_id),
      .dir_write_valid(write_valid_ctx[c]), .dir_write_ready(write_ready_ctx[c]),
      .dir_write_line_addr(write_addr_ctx[c]), .dir_write_state(write_state_ctx[c]),
      .dir_write_sharers(write_sharers_ctx[c]), .dir_write_owner_id(write_owner_ctx[c]),
      .snoop_req_valid(snoop_valid_ctx[c]), .snoop_req_ready(snoop_ready_ctx[c]),
      .snoop_target_id(snoop_target_ctx[c]), .snoop_req_opcode(snoop_opcode_ctx[c]),
      .snoop_req_line_addr(snoop_addr_ctx[c]), .snoop_req_txn_id(snoop_txn_ctx[c]),
      .snoop_rsp_valid(snoop_active_q && (snoop_active_idx_q == MSHR_ID_WIDTH'(c)) &&
                       snoop_rsp_valid),
      .snoop_rsp_ready(snoop_rsp_ready_ctx[c]),
      .snoop_rsp_src_id(snoop_rsp_src_id), .snoop_rsp_opcode(snoop_rsp_opcode),
      .snoop_rsp_txn_id(snoop_rsp_txn_id),
      .line_xfer_start_valid(xfer_valid_ctx[c]),
      .line_xfer_start_ready(xfer_ready_ctx[c]), .line_xfer_kind(xfer_kind_ctx[c]),
      .line_xfer_addr(xfer_addr_ctx[c]), .line_xfer_src_id(xfer_src_ctx[c]),
      .line_xfer_txn_id(xfer_txn_ctx[c]),
      .line_xfer_done_valid(done_valid_ctx[c]),
      .line_xfer_done_ready(xfer_done_ready_ctx[c]),
      .line_xfer_done_txn_id(txn_id_q[c]),
      .grant_valid(grant_valid_ctx[c]), .grant_ready(grant_ready_ctx[c]),
      .grant_dst_id(grant_dst_ctx[c]), .grant_opcode(grant_opcode_ctx[c]),
      .grant_has_data(grant_has_data_ctx[c]), .grant_line_addr(grant_addr_ctx[c]),
      .grant_txn_id(grant_txn_ctx[c]),
      .grant_commit_valid(grant_commit_valid && commit_found &&
                          (commit_sel == MSHR_ID_WIDTH'(c))),
      .grant_commit_ready(grant_commit_ready_ctx[c]),
      .grant_commit_txn_id(grant_commit_txn_id),
      .snoop_data_to_l2(snoop_data_ctx[c]), .protocol_error(error_ctx[c]),
      .protocol_error_code(error_code_ctx[c])
    );
  end

endmodule
