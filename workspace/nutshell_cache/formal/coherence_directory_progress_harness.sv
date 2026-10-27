module CoherenceDirectoryProgressFormal;
  import coherence_protocol_pkg::*;

  (* gclk *) logic formal_timestep;
  logic clock = 1'b0;
  logic [1:0] init_reset_count = 2'b00;
  logic reset;

  logic req_valid;
  logic req_ready;
  logic request_accepted_q = 1'b0;
  logic dir_write_valid;
  logic [31:0] dir_write_line_addr;
  directory_state_t dir_write_state;
  logic [1:0] dir_write_sharers;
  logic dir_write_owner_id;
  logic snoop_req_valid;
  logic snoop_target_id;
  snoop_opcode_t snoop_req_opcode;
  logic [31:0] snoop_req_line_addr;
  logic [TXN_ID_WIDTH-1:0] snoop_req_txn_id;
  logic snoop_rsp_ready;
  logic line_xfer_start_valid;
  line_xfer_kind_t line_xfer_kind;
  logic [31:0] line_xfer_addr;
  logic line_xfer_src_id;
  logic [TXN_ID_WIDTH-1:0] line_xfer_txn_id;
  logic line_xfer_done_ready;
  logic line_xfer_done_valid_q = 1'b0;
  logic line_xfer_done_valid;
  logic grant_valid;
  logic grant_dst_id;
  grant_opcode_t grant_opcode;
  logic grant_has_data;
  logic [31:0] grant_line_addr;
  logic [TXN_ID_WIDTH-1:0] grant_txn_id;
  logic grant_commit_ready;
  logic grant_commit_valid_q = 1'b0;
  logic grant_commit_valid;
  logic snoop_data_to_l2;
  logic protocol_error;
  logic [3:0] protocol_error_code;

  logic xfer_done_seen_q = 1'b0;
  logic grant_seen_q = 1'b0;
  logic commit_seen_q = 1'b0;
  logic [4:0] elapsed_cycles_q = '0;

  always @(posedge formal_timestep)
    clock <= ~clock;

  always_comb begin
    reset = (init_reset_count < 2);
    req_valid = !reset && !request_accepted_q;
    line_xfer_done_valid = line_xfer_done_valid_q && !xfer_done_seen_q;
    grant_commit_valid = grant_commit_valid_q && !commit_seen_q;
  end

  DirectoryController dut (
    .clock(clock), .reset(reset),
    .req_valid(req_valid), .req_ready(req_ready),
    .req_src_id(1'b0), .req_opcode(REQ_GETS),
    .req_line_addr(32'h0000_1000), .req_txn_id(4'd3),
    .lookup_dir_state(DIR_I), .lookup_sharers(2'b00),
    .lookup_owner_id(1'b0),
    .dir_write_valid(dir_write_valid), .dir_write_ready(1'b1),
    .dir_write_line_addr(dir_write_line_addr),
    .dir_write_state(dir_write_state),
    .dir_write_sharers(dir_write_sharers),
    .dir_write_owner_id(dir_write_owner_id),
    .snoop_req_valid(snoop_req_valid), .snoop_req_ready(1'b1),
    .snoop_target_id(snoop_target_id), .snoop_req_opcode(snoop_req_opcode),
    .snoop_req_line_addr(snoop_req_line_addr),
    .snoop_req_txn_id(snoop_req_txn_id),
    .snoop_rsp_valid(1'b0), .snoop_rsp_ready(snoop_rsp_ready),
    .snoop_rsp_src_id(1'b0), .snoop_rsp_opcode(SNOOP_RSP_ACK),
    .snoop_rsp_txn_id(4'd0),
    .line_xfer_start_valid(line_xfer_start_valid),
    .line_xfer_start_ready(1'b1), .line_xfer_kind(line_xfer_kind),
    .line_xfer_addr(line_xfer_addr), .line_xfer_src_id(line_xfer_src_id),
    .line_xfer_txn_id(line_xfer_txn_id),
    .line_xfer_done_valid(line_xfer_done_valid),
    .line_xfer_done_ready(line_xfer_done_ready),
    .line_xfer_done_txn_id(4'd3),
    .grant_valid(grant_valid), .grant_ready(1'b1),
    .grant_dst_id(grant_dst_id), .grant_opcode(grant_opcode),
    .grant_has_data(grant_has_data), .grant_line_addr(grant_line_addr),
    .grant_txn_id(grant_txn_id),
    .grant_commit_valid(grant_commit_valid),
    .grant_commit_ready(grant_commit_ready),
    .grant_commit_txn_id(4'd3), .snoop_data_to_l2(snoop_data_to_l2),
    .protocol_error(protocol_error),
    .protocol_error_code(protocol_error_code)
  );

  always_ff @(posedge clock) begin
    if (reset) begin
      if (init_reset_count < 2)
        init_reset_count <= init_reset_count + 1'b1;
      request_accepted_q <= 1'b0;
      line_xfer_done_valid_q <= 1'b0;
      xfer_done_seen_q <= 1'b0;
      grant_commit_valid_q <= 1'b0;
      grant_seen_q <= 1'b0;
      commit_seen_q <= 1'b0;
      elapsed_cycles_q <= '0;
    end else begin
      elapsed_cycles_q <= elapsed_cycles_q + 1'b1;

      if (req_valid && req_ready)
        request_accepted_q <= 1'b1;

      if (line_xfer_start_valid) begin
        assert (line_xfer_kind == XFER_L2_REFILL);
        assert (line_xfer_addr == 32'h0000_1000);
        assert (line_xfer_txn_id == 4'd3);
        line_xfer_done_valid_q <= 1'b1;
      end
      if (line_xfer_done_valid && line_xfer_done_ready)
        xfer_done_seen_q <= 1'b1;

      if (grant_valid) begin
        assert (grant_opcode == GRANT_DATA_E);
        assert (grant_has_data);
        assert (grant_dst_id == 1'b0);
        assert (grant_line_addr == 32'h0000_1000);
        assert (grant_txn_id == 4'd3);
        assert (dir_write_state == DIR_U);
        assert (dir_write_sharers == 2'b00);
        assert (dir_write_owner_id == 1'b0);
      end
      if (grant_valid)
        grant_seen_q <= 1'b1;
      if (grant_valid && !grant_commit_valid_q)
        grant_commit_valid_q <= 1'b1;
      if (grant_commit_valid && grant_commit_ready)
        commit_seen_q <= 1'b1;

      // With refill start/done, metadata write, grant and commit all ready,
      // the accepted GetS must complete within this explicit bounded window.
      if (elapsed_cycles_q == 5'd8)
        assert (grant_seen_q);
      if (elapsed_cycles_q == 5'd9)
        assert (commit_seen_q);
      assert (!protocol_error);
    end
  end
endmodule
