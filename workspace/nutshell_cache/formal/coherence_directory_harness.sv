module CoherenceDirectoryFormal(
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
  input logic [3:0] line_xfer_done_txn_id,
  input logic grant_ready,
  input logic grant_commit_valid,
  input logic [3:0] grant_commit_txn_id
);
  import coherence_protocol_pkg::*;

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
  logic [TXN_ID_WIDTH-1:0] snoop_req_txn_id;
  logic snoop_rsp_ready;
  logic line_xfer_start_valid;
  line_xfer_kind_t line_xfer_kind;
  logic [31:0] line_xfer_addr;
  logic line_xfer_src_id;
  logic [TXN_ID_WIDTH-1:0] line_xfer_txn_id;
  logic line_xfer_done_ready;
  logic grant_valid, grant_dst_id, grant_has_data;
  grant_opcode_t grant_opcode;
  logic [31:0] grant_line_addr;
  logic [TXN_ID_WIDTH-1:0] grant_txn_id;
  logic grant_commit_ready;
  logic snoop_data_to_l2, protocol_error;
  logic [3:0] protocol_error_code;

  logic past_valid = 1'b0;
  logic reset_seen_q = 1'b0;
  logic protocol_error_seen_q = 1'b0;
  request_opcode_t accepted_req_opcode_q;

  logic dir_write_stall_q = 1'b0;
  logic [31:0] dir_write_addr_hold_q;
  directory_state_t dir_write_state_hold_q;
  logic [1:0] dir_write_sharers_hold_q;
  logic dir_write_owner_hold_q;

  logic snoop_stall_q = 1'b0;
  logic snoop_target_hold_q;
  snoop_opcode_t snoop_opcode_hold_q;
  logic [31:0] snoop_addr_hold_q;
  logic [TXN_ID_WIDTH-1:0] snoop_txn_hold_q;
  logic snoop_data_to_l2_hold_q;

  logic xfer_stall_q = 1'b0;
  line_xfer_kind_t xfer_kind_hold_q;
  logic [31:0] xfer_addr_hold_q;
  logic [TXN_ID_WIDTH-1:0] xfer_txn_hold_q;

  logic grant_stall_q = 1'b0;
  grant_opcode_t grant_opcode_hold_q;
  logic [31:0] grant_addr_hold_q;
  logic [TXN_ID_WIDTH-1:0] grant_txn_hold_q;
  logic grant_has_data_hold_q;

  always_comb reset = (init_reset_count < 2) || reset_after_init;

  always_comb begin
    if (req_valid && req_ready) begin
      assume (req_opcode <= REQ_PUTM);
      assume (lookup_dir_state != 2'b11);
      assume ((lookup_dir_state != DIR_I) ||
              ((lookup_sharers == 2'b00) && !lookup_owner_id));
      assume ((lookup_dir_state != DIR_S) ||
              ((lookup_sharers != 2'b00) && !lookup_owner_id));
      assume ((lookup_dir_state != DIR_U) ||
              (lookup_sharers == 2'b00));
    end
  end

  always @(posedge formal_timestep)
    clock <= ~clock;

  DirectoryController dut (.*);

  always @(posedge clock) begin
    past_valid <= 1'b1;
    if (init_reset_count < 2)
      init_reset_count <= init_reset_count + 1'b1;
    if (reset)
      reset_seen_q <= 1'b1;
    else if (reset_seen_q)
      reset_seen_q <= 1'b0;

    if (reset) begin
      protocol_error_seen_q <= 1'b0;
      accepted_req_opcode_q <= REQ_GETS;
      dir_write_stall_q <= 1'b0;
      snoop_stall_q <= 1'b0;
      xfer_stall_q <= 1'b0;
      grant_stall_q <= 1'b0;
    end else begin
      if (req_valid && req_ready)
        accepted_req_opcode_q <= req_opcode;
      if (protocol_error_seen_q)
        assert (protocol_error);
      protocol_error_seen_q <= protocol_error;

      if (dir_write_stall_q) begin
        assert (dir_write_valid);
        assert (dir_write_line_addr == dir_write_addr_hold_q);
        assert (dir_write_state == dir_write_state_hold_q);
        assert (dir_write_sharers == dir_write_sharers_hold_q);
        assert (dir_write_owner_id == dir_write_owner_hold_q);
        if (dir_write_valid && dir_write_ready)
          dir_write_stall_q <= 1'b0;
      end else if (dir_write_valid && !dir_write_ready) begin
        dir_write_stall_q <= 1'b1;
        dir_write_addr_hold_q <= dir_write_line_addr;
        dir_write_state_hold_q <= dir_write_state;
        dir_write_sharers_hold_q <= dir_write_sharers;
        dir_write_owner_hold_q <= dir_write_owner_id;
      end

      if (snoop_stall_q) begin
        assert (snoop_req_valid);
        assert (snoop_target_id == snoop_target_hold_q);
        assert (snoop_req_opcode == snoop_opcode_hold_q);
        assert (snoop_req_line_addr == snoop_addr_hold_q);
        assert (snoop_req_txn_id == snoop_txn_hold_q);
        assert (snoop_data_to_l2 == snoop_data_to_l2_hold_q);
        if (snoop_req_valid && snoop_req_ready)
          snoop_stall_q <= 1'b0;
      end else if (snoop_req_valid && !snoop_req_ready) begin
        snoop_stall_q <= 1'b1;
        snoop_target_hold_q <= snoop_target_id;
        snoop_opcode_hold_q <= snoop_req_opcode;
        snoop_addr_hold_q <= snoop_req_line_addr;
        snoop_txn_hold_q <= snoop_req_txn_id;
        snoop_data_to_l2_hold_q <= snoop_data_to_l2;
      end

      if (xfer_stall_q) begin
        assert (line_xfer_start_valid);
        assert (line_xfer_kind == xfer_kind_hold_q);
        assert (line_xfer_addr == xfer_addr_hold_q);
        assert (line_xfer_txn_id == xfer_txn_hold_q);
        if (line_xfer_start_valid && line_xfer_start_ready)
          xfer_stall_q <= 1'b0;
      end else if (line_xfer_start_valid && !line_xfer_start_ready) begin
        xfer_stall_q <= 1'b1;
        xfer_kind_hold_q <= line_xfer_kind;
        xfer_addr_hold_q <= line_xfer_addr;
        xfer_txn_hold_q <= line_xfer_txn_id;
      end

      if (grant_stall_q) begin
        assert (grant_valid);
        assert (grant_opcode == grant_opcode_hold_q);
        assert (grant_line_addr == grant_addr_hold_q);
        assert (grant_txn_id == grant_txn_hold_q);
        assert (grant_has_data == grant_has_data_hold_q);
        if (grant_valid && grant_ready)
          grant_stall_q <= 1'b0;
      end else if (grant_valid && !grant_ready) begin
        grant_stall_q <= 1'b1;
        grant_opcode_hold_q <= grant_opcode;
        grant_addr_hold_q <= grant_line_addr;
        grant_txn_hold_q <= grant_txn_id;
        grant_has_data_hold_q <= grant_has_data;
      end
    end

    if (past_valid && reset_seen_q)
      assert (req_ready && !dir_write_valid && !snoop_req_valid &&
              !grant_valid && !line_xfer_start_valid);

    if (past_valid && !reset) begin
      assert (!grant_valid || (grant_line_addr[5:0] == 6'b0));
      assert (!snoop_req_valid || (snoop_req_line_addr[5:0] == 6'b0));
      assert (!dir_write_valid || (dir_write_line_addr[5:0] == 6'b0));
      assert (!grant_commit_ready ||
              (grant_commit_txn_id == grant_txn_id));
      assert (!line_xfer_done_ready ||
              (line_xfer_done_txn_id == line_xfer_txn_id));
      assert (!snoop_rsp_ready ||
              ((snoop_rsp_txn_id == snoop_req_txn_id) &&
               (snoop_rsp_src_id == snoop_target_id)));

      if (dir_write_valid) begin
        assert ((dir_write_state != DIR_I) ||
                ((dir_write_sharers == 2'b00) && !dir_write_owner_id));
        assert ((dir_write_state != DIR_S) ||
                ((dir_write_sharers != 2'b00) && !dir_write_owner_id));
        assert ((dir_write_state != DIR_U) ||
                (dir_write_sharers == 2'b00));
      end

      // Grants are legal only after the Directory's snoop/refill sequence has
      // completed, and their permission must agree with the committed owner /
      // sharer metadata. This checks the safety contract at the grant boundary.
      if (grant_valid) begin
        assert (dut.pending_targets_q == 2'b00);
        assert (grant_dst_id == dut.src_id_q);
        assert (grant_line_addr == dut.line_addr_q);
        assert (grant_txn_id == dut.txn_id_q);
        assert (grant_has_data == grant_contains_data(grant_opcode));
        case (accepted_req_opcode_q)
          REQ_GETS: begin
            assert ((grant_opcode == GRANT_DATA_S) ||
                    (grant_opcode == GRANT_DATA_E));
            if (grant_opcode == GRANT_DATA_S) begin
              assert (dir_write_state == DIR_S);
              assert (dir_write_sharers[dut.src_id_q]);
              assert (!dir_write_owner_id);
            end else begin
              assert (dir_write_state == DIR_U);
              assert (dir_write_owner_id == dut.src_id_q);
              assert (dir_write_sharers == 2'b00);
            end
          end
          REQ_GETM, REQ_UPGRADE: begin
            assert ((grant_opcode == GRANT_DATA_M) ||
                    (grant_opcode == GRANT_M));
            assert (dir_write_state == DIR_U);
            assert (dir_write_owner_id == dut.src_id_q);
            assert (dir_write_sharers == 2'b00);
          end
          REQ_PUTS, REQ_PUTE, REQ_PUTM:
            assert (grant_opcode == GRANT_PUT_ACK);
          default: assert (1'b0);
        endcase
      end
    end
  end
endmodule
