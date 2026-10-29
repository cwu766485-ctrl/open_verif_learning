// Formal harness for the complete four-context Directory MSHR bank. The
// environment may independently stall every shared output channel. Request
// metadata is constrained to legal MESI directory states at acceptance; all
// response and ready channels remain symbolic.
module CoherenceDirectoryMshrBankFormal(
  input logic reset_after_init,
  input logic req_valid,
  input logic req_src_id,
  input logic [2:0] req_opcode_bits,
  input logic [31:0] req_line_addr,
  input logic [3:0] req_txn_id,
  input logic [1:0] lookup_dir_state_bits,
  input logic [1:0] lookup_sharers,
  input logic lookup_owner_id,
  input logic dir_write_ready,
  input logic snoop_req_ready,
  input logic snoop_rsp_valid,
  input logic snoop_rsp_src_id,
  input logic [1:0] snoop_rsp_opcode_bits,
  input logic [3:0] snoop_rsp_txn_id,
  input logic line_xfer_start_ready,
  input logic line_xfer_done_valid,
  input logic [1:0] line_xfer_done_context_id,
  input logic grant_ready,
  input logic grant_commit_valid,
  input logic grant_commit_src_id,
  input logic [3:0] grant_commit_txn_id
);
  import coherence_protocol_pkg::*;

  localparam int NUM_MSHRS = 4;
  localparam int MSHR_ID_WIDTH = 2;

  (* gclk *) logic formal_timestep;
  logic clock = 1'b0;
  logic reset;
  logic [1:0] init_reset_count = 2'b00;

  request_opcode_t req_opcode;
  directory_state_t lookup_dir_state;
  snoop_response_t snoop_rsp_opcode;
  always_comb begin
    req_opcode = request_opcode_t'(req_opcode_bits);
    lookup_dir_state = directory_state_t'(lookup_dir_state_bits);
    snoop_rsp_opcode = snoop_response_t'(snoop_rsp_opcode_bits);
    reset = (init_reset_count < 2) || reset_after_init;
  end

  logic req_ready;
  logic dir_write_valid;
  logic [31:0] dir_write_line_addr;
  directory_state_t dir_write_state;
  logic [1:0] dir_write_sharers;
  logic dir_write_owner_id;
  logic snoop_req_valid, snoop_target_id;
  snoop_opcode_t snoop_req_opcode;
  logic [31:0] snoop_req_line_addr;
  logic [3:0] snoop_req_txn_id;
  logic snoop_rsp_ready;
  logic line_xfer_start_valid;
  line_xfer_kind_t line_xfer_kind;
  logic [31:0] line_xfer_addr;
  logic line_xfer_src_id;
  logic [3:0] line_xfer_txn_id;
  logic [MSHR_ID_WIDTH-1:0] line_xfer_context_id;
  logic line_xfer_done_ready;
  logic grant_valid, grant_dst_id, grant_has_data;
  grant_opcode_t grant_opcode;
  logic [31:0] grant_line_addr;
  logic [3:0] grant_txn_id;
  logic grant_commit_ready;
  logic snoop_data_to_l2, protocol_error;

  DirectoryMshrBank #(
    .TXN_ID_WIDTH(TXN_ID_WIDTH),
    .NUM_MSHRS(NUM_MSHRS),
    .MSHR_ID_WIDTH(MSHR_ID_WIDTH)
  ) dut (
    .clock(clock), .reset(reset),
    .req_valid(req_valid), .req_ready(req_ready), .req_src_id(req_src_id),
    .req_opcode(req_opcode), .req_line_addr(req_line_addr),
    .req_txn_id(req_txn_id), .lookup_dir_state(lookup_dir_state),
    .lookup_sharers(lookup_sharers), .lookup_owner_id(lookup_owner_id),
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
    .line_xfer_txn_id(line_xfer_txn_id),
    .line_xfer_context_id(line_xfer_context_id),
    .line_xfer_done_valid(line_xfer_done_valid),
    .line_xfer_done_ready(line_xfer_done_ready),
    .line_xfer_done_context_id(line_xfer_done_context_id),
    .grant_valid(grant_valid), .grant_ready(grant_ready),
    .grant_dst_id(grant_dst_id), .grant_opcode(grant_opcode),
    .grant_has_data(grant_has_data), .grant_line_addr(grant_line_addr),
    .grant_txn_id(grant_txn_id), .grant_commit_valid(grant_commit_valid),
    .grant_commit_src_id(grant_commit_src_id),
    .grant_commit_ready(grant_commit_ready),
    .grant_commit_txn_id(grant_commit_txn_id),
    .snoop_data_to_l2(snoop_data_to_l2), .protocol_error(protocol_error)
  );

  logic past_valid = 1'b0;
  request_opcode_t accepted_req_opcode_q [0:NUM_MSHRS-1];
  initial assume (reset);
  always @(posedge formal_timestep)
    clock <= ~clock;

  // Keep the request opcode in the checker model from the public accepted
  // request. The implementation need not retain a redundant opcode register.
  always_ff @(posedge clock) begin : accepted_request_model
    integer slot;
    if (reset) begin
      for (slot = 0; slot < NUM_MSHRS; slot = slot + 1)
        accepted_req_opcode_q[slot] <= REQ_GETS;
    end else if (req_valid && req_ready) begin
      accepted_req_opcode_q[dut.req_sel] <= req_opcode;
    end
  end

  always @(posedge clock) begin : bank_properties
    integer i;
    integer j;
    integer matching_line_contexts;
    integer legal_put_bypass_found;
    past_valid <= 1'b1;
    if (init_reset_count < 2)
      init_reset_count <= init_reset_count + 1'b1;

    // Legal directory metadata is supplied when a request is actually taken.
    if (req_valid && req_ready) begin
      assume (req_opcode <= REQ_PUTM);
      assume (lookup_dir_state != 2'b11);
      assume ((lookup_dir_state != DIR_I) ||
              ((lookup_sharers == 2'b00) && !lookup_owner_id));
      assume ((lookup_dir_state != DIR_S) ||
              ((lookup_sharers != 2'b00) && !lookup_owner_id));
      assume ((lookup_dir_state != DIR_U) || (lookup_sharers == 2'b00));
    end

    if (!reset) begin
      matching_line_contexts = 0;
      legal_put_bypass_found = 0;
      for (i = 0; i < NUM_MSHRS; i = i + 1) begin
        if (dut.active_q[i] &&
            (dut.line_addr_q[i] == line_align(req_line_addr))) begin
          matching_line_contexts = matching_line_contexts + 1;
          if (dut.snoop_valid_ctx[i] && !dut.snoop_ready_ctx[i] &&
              (dut.snoop_target_ctx[i] == req_src_id))
            legal_put_bypass_found = 1;
        end
        for (j = i + 1; j < NUM_MSHRS; j = j + 1) begin
          if (dut.active_q[i] && dut.active_q[j] &&
              (dut.line_addr_q[i] == dut.line_addr_q[j])) begin
            // The sole allowed duplicate is one replacement Put context
            // behind one coherence context that had to let the Put retire
            // before its stalled Snoop could be accepted.
            assert ((accepted_req_opcode_q[i] inside
                      {REQ_PUTS, REQ_PUTE, REQ_PUTM}) !=
                    (accepted_req_opcode_q[j] inside
                      {REQ_PUTS, REQ_PUTE, REQ_PUTM}));
          end
        end
      end
      // Check the bypass at the acceptance edge. Later, the old Snoop may be
      // accepted and the two legal same-line contexts coexist until commit.
      if (req_valid && req_ready && (matching_line_contexts != 0))
        assert (((req_opcode == REQ_PUTS) || (req_opcode == REQ_PUTE) ||
                 (req_opcode == REQ_PUTM)) && legal_put_bypass_found);

      // Four independently arbitrated shared outputs must never grant more
      // than one context in a cycle.
      assert ($onehot0(dut.write_ready_ctx));
      assert ($onehot0(dut.snoop_ready_ctx));
      assert ($onehot0(dut.xfer_ready_ctx));
      assert ($onehot0(dut.grant_ready_ctx));

      // All externally visible payloads must come from the selected live
      // controller context, including source and transaction identity.
      if (dir_write_valid) begin
        assert (dir_write_line_addr == dut.write_addr_ctx[dut.write_sel]);
        assert (dir_write_state == dut.write_state_ctx[dut.write_sel]);
        assert (dir_write_sharers == dut.write_sharers_ctx[dut.write_sel]);
        assert (dir_write_owner_id == dut.write_owner_ctx[dut.write_sel]);
      end
      if (snoop_req_valid) begin
        assert (snoop_req_line_addr == dut.snoop_addr_ctx[dut.snoop_sel]);
        assert (snoop_req_txn_id == dut.snoop_txn_ctx[dut.snoop_sel]);
        assert (snoop_target_id == dut.snoop_target_ctx[dut.snoop_sel]);
      end
      if (line_xfer_start_valid) begin
        assert (line_xfer_context_id == dut.xfer_sel);
        assert (line_xfer_addr == dut.xfer_addr_ctx[dut.xfer_sel]);
        assert (line_xfer_txn_id == dut.xfer_txn_ctx[dut.xfer_sel]);
        assert (line_xfer_src_id == dut.xfer_src_ctx[dut.xfer_sel]);
      end
      if (grant_valid) begin
        assert (grant_line_addr == dut.grant_addr_ctx[dut.grant_sel]);
        assert (grant_txn_id == dut.grant_txn_ctx[dut.grant_sel]);
        assert (grant_dst_id == dut.grant_dst_ctx[dut.grant_sel]);
      end

      // Completion and commit are routed only to the context associated with
      // their captured context ID or (source, transaction ID) pair.
      if (line_xfer_done_ready)
        assert (line_xfer_done_valid &&
                (line_xfer_done_context_id < NUM_MSHRS));
      if (grant_commit_valid && grant_commit_ready) begin
        assert (grant_commit_valid && dut.commit_found);
        assert (dut.active_q[dut.commit_sel]);
        assert (dut.src_id_q[dut.commit_sel] == grant_commit_src_id);
        assert (dut.txn_id_q[dut.commit_sel] == grant_commit_txn_id);
      end
    end

    // Context request fields are captured exactly at acceptance. A commit
    // cannot free a context unless the requester and transaction both match.
    if (past_valid && !reset && !$past(reset)) begin
      if ($past(req_valid && req_ready)) begin
        assert (dut.active_q[$past(dut.req_sel)]);
        assert (dut.line_addr_q[$past(dut.req_sel)] ==
                line_align($past(req_line_addr)));
        assert (dut.src_id_q[$past(dut.req_sel)] == $past(req_src_id));
        assert (dut.txn_id_q[$past(dut.req_sel)] == $past(req_txn_id));
      end

      if ($past(dir_write_valid && !dir_write_ready)) begin
        assert (dir_write_valid);
        assert (dir_write_line_addr == $past(dir_write_line_addr));
        assert (dir_write_state == $past(dir_write_state));
        assert (dir_write_sharers == $past(dir_write_sharers));
        assert (dir_write_owner_id == $past(dir_write_owner_id));
      end
      if ($past(snoop_req_valid && !snoop_req_ready)) begin
        assert (snoop_req_valid);
        assert (snoop_target_id == $past(snoop_target_id));
        assert (snoop_req_opcode == $past(snoop_req_opcode));
        assert (snoop_req_line_addr == $past(snoop_req_line_addr));
        assert (snoop_req_txn_id == $past(snoop_req_txn_id));
      end
      if ($past(line_xfer_start_valid && !line_xfer_start_ready)) begin
        assert (line_xfer_start_valid);
        assert (line_xfer_context_id == $past(line_xfer_context_id));
        assert (line_xfer_addr == $past(line_xfer_addr));
        assert (line_xfer_txn_id == $past(line_xfer_txn_id));
        assert (line_xfer_src_id == $past(line_xfer_src_id));
      end
      if ($past(grant_valid && !grant_ready)) begin
        assert (grant_valid);
        assert (grant_dst_id == $past(grant_dst_id));
        assert (grant_opcode == $past(grant_opcode));
        assert (grant_has_data == $past(grant_has_data));
        assert (grant_line_addr == $past(grant_line_addr));
        assert (grant_txn_id == $past(grant_txn_id));
      end

      if ($past(reset)) begin
        assert (dut.active_q == '0);
        assert (!snoop_req_valid && !line_xfer_start_valid && !grant_valid);
        assert (!snoop_rsp_ready && !grant_commit_ready);
        assert (!dut.snoop_active_q);
        assert (!dut.write_offer_lock_q && !dut.snoop_offer_lock_q &&
                !dut.xfer_offer_lock_q && !dut.grant_offer_lock_q);
      end
    end

    cover (!reset && $countones(dut.active_q) >= 2);
    cover (!reset && $countones(dut.active_q) == NUM_MSHRS);
  end
endmodule
