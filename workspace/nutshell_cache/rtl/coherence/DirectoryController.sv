module DirectoryController #(
  parameter int TXN_ID_WIDTH = coherence_protocol_pkg::TXN_ID_WIDTH
) (
  input  logic clock,
  input  logic reset,

  // This block serializes one transaction globally. The request arbiter and
  // directory-tag lookup sit in front of it; lookup metadata is sampled when
  // the request handshake occurs.
  input  logic req_valid,
  output logic req_ready,
  input  logic req_src_id,
  input  coherence_protocol_pkg::request_opcode_t req_opcode,
  input  logic [31:0] req_line_addr,
  input  logic [TXN_ID_WIDTH-1:0] req_txn_id,
  input  coherence_protocol_pkg::directory_state_t lookup_dir_state,
  input  logic [1:0] lookup_sharers,
  input  logic lookup_owner_id,

  // Directory metadata array write port. The update commits before the grant
  // header becomes visible to the requester.
  output logic dir_write_valid,
  input  logic dir_write_ready,
  output logic [31:0] dir_write_line_addr,
  output coherence_protocol_pkg::directory_state_t dir_write_state,
  output logic [1:0] dir_write_sharers,
  output logic dir_write_owner_id,

  // Snoop request/response control. SnoopData payload beats use a separate
  // eight-beat line data path. The response handshake occurs only after the
  // owner has sent all beats and committed its local MESI state update.
  output logic snoop_req_valid,
  input  logic snoop_req_ready,
  output logic snoop_target_id,
  output coherence_protocol_pkg::snoop_opcode_t snoop_req_opcode,
  output logic [31:0] snoop_req_line_addr,
  output logic [TXN_ID_WIDTH-1:0] snoop_req_txn_id,
  input  logic snoop_rsp_valid,
  output logic snoop_rsp_ready,
  input  logic snoop_rsp_src_id,
  input  coherence_protocol_pkg::snoop_response_t snoop_rsp_opcode,
  input  logic [TXN_ID_WIDTH-1:0] snoop_rsp_txn_id,

  // Control barriers around the shared L2/line-data engine. XFER_L2_REFILL
  // obtains a line for a GetS/GetM miss; XFER_PUTM_TO_L2 drains a dirty PutM.
  // The adapter reports completion only after all eight beats have transferred.
  output logic line_xfer_start_valid,
  input  logic line_xfer_start_ready,
  output coherence_protocol_pkg::line_xfer_kind_t line_xfer_kind,
  output logic [31:0] line_xfer_addr,
  output logic line_xfer_src_id,
  output logic [TXN_ID_WIDTH-1:0] line_xfer_txn_id,
  input  logic line_xfer_done_valid,
  output logic line_xfer_done_ready,
  input  logic [TXN_ID_WIDTH-1:0] line_xfer_done_txn_id,

  // The Directory remains busy until the requester has accepted all refill
  // beats (if any) and committed its local MESI metadata.
  output logic grant_valid,
  input  logic grant_ready,
  output logic grant_dst_id,
  output coherence_protocol_pkg::grant_opcode_t grant_opcode,
  output logic grant_has_data,
  output logic [31:0] grant_line_addr,
  output logic [TXN_ID_WIDTH-1:0] grant_txn_id,
  input  logic grant_commit_valid,
  output logic grant_commit_ready,
  input  logic [TXN_ID_WIDTH-1:0] grant_commit_txn_id,

  // Owner SnoopData is copied into shared L2 before the directory changes U
  // to S or transfers ownership. This qualifier is held during that snoop.
  output logic snoop_data_to_l2,

  output logic protocol_error
);
  import coherence_protocol_pkg::*;

  typedef enum logic [3:0] {
    DIR_IDLE,
    DIR_START_XFER,
    DIR_WAIT_XFER,
    DIR_SEND_SNOOP,
    DIR_WAIT_SNOOP,
    DIR_COMMIT,
    DIR_SEND_GRANT,
    DIR_WAIT_GRANT_COMMIT,
    DIR_FINISH,
    DIR_ERROR
  } dir_fsm_state_t;

  dir_fsm_state_t state_q;
  dir_fsm_state_t snoop_resume_q;
  request_opcode_t req_opcode_q;
  snoop_opcode_t snoop_opcode_q;
  line_xfer_kind_t line_xfer_kind_q;
  grant_opcode_t grant_opcode_q;
  directory_state_t next_dir_state_q;
  logic [1:0] next_sharers_q;
  logic next_owner_q;
  logic [1:0] pending_targets_q;
  logic current_target_q;
  logic src_id_q;
  logic [31:0] line_addr_q;
  logic [TXN_ID_WIDTH-1:0] txn_id_q;
  logic grant_has_data_q;
  logic snoop_response_must_be_data_q;
  logic [1:0] targets_after_current;
  logic snoop_rsp_matches;

  always_comb begin
    req_ready = (state_q == DIR_IDLE);

    dir_write_valid = (state_q == DIR_COMMIT);
    dir_write_line_addr = line_addr_q;
    dir_write_state = next_dir_state_q;
    dir_write_sharers = next_sharers_q;
    dir_write_owner_id = next_owner_q;

    snoop_req_valid = (state_q == DIR_SEND_SNOOP);
    snoop_target_id = pending_targets_q[0] ? 1'b0 : 1'b1;
    snoop_req_opcode = snoop_opcode_q;
    snoop_req_line_addr = line_addr_q;
    snoop_req_txn_id = txn_id_q;

    snoop_rsp_matches = (snoop_rsp_txn_id == txn_id_q) &&
                        (snoop_rsp_src_id == current_target_q);
    snoop_rsp_ready = (state_q == DIR_WAIT_SNOOP) && snoop_rsp_matches;
    line_xfer_start_valid = (state_q == DIR_START_XFER);
    line_xfer_kind = line_xfer_kind_q;
    line_xfer_addr = line_addr_q;
    line_xfer_src_id = src_id_q;
    line_xfer_txn_id = txn_id_q;
    line_xfer_done_ready = (state_q == DIR_WAIT_XFER) &&
                            (line_xfer_done_txn_id == txn_id_q);

    grant_valid = (state_q == DIR_SEND_GRANT);
    grant_dst_id = src_id_q;
    grant_opcode = grant_opcode_q;
    grant_has_data = grant_has_data_q;
    grant_line_addr = line_addr_q;
    grant_txn_id = txn_id_q;
    grant_commit_ready = (state_q == DIR_WAIT_GRANT_COMMIT) &&
                         (grant_commit_txn_id == txn_id_q);
    snoop_data_to_l2 = snoop_response_must_be_data_q &&
                       ((state_q == DIR_SEND_SNOOP) ||
                        (state_q == DIR_WAIT_SNOOP));

    targets_after_current = pending_targets_q &
                            (current_target_q ? 2'b01 : 2'b10);
  end

  always_ff @(posedge clock) begin : directory_fsm
    logic [1:0] source_mask;
    logic [1:0] target_mask;
    if (reset) begin
      state_q <= DIR_IDLE;
      snoop_resume_q <= DIR_COMMIT;
      req_opcode_q <= REQ_GETS;
      snoop_opcode_q <= SNOOP_READ;
      line_xfer_kind_q <= XFER_L2_REFILL;
      grant_opcode_q <= GRANT_DATA_S;
      next_dir_state_q <= DIR_I;
      next_sharers_q <= 2'b00;
      next_owner_q <= 1'b0;
      pending_targets_q <= 2'b00;
      current_target_q <= 1'b0;
      src_id_q <= 1'b0;
      line_addr_q <= 32'b0;
      txn_id_q <= '0;
      grant_has_data_q <= 1'b0;
      snoop_response_must_be_data_q <= 1'b0;
      protocol_error <= 1'b0;
    end else begin
      case (state_q)
        DIR_IDLE: begin
          if (req_valid && req_ready) begin
            source_mask = core_bit(req_src_id);
            target_mask = 2'b00;
            req_opcode_q <= req_opcode;
            src_id_q <= req_src_id;
            line_addr_q <= line_align(req_line_addr);
            txn_id_q <= req_txn_id;
            pending_targets_q <= 2'b00;
            snoop_response_must_be_data_q <= 1'b0;
            grant_has_data_q <= 1'b0;
            next_dir_state_q <= lookup_dir_state;
            next_sharers_q <= lookup_sharers;
            next_owner_q <= lookup_owner_id;
            snoop_resume_q <= DIR_COMMIT;

            // Reject impossible directory metadata before using it as a data
            // source or issuing a permission grant.
            if (((lookup_dir_state == DIR_I) &&
                 ((lookup_sharers != 2'b00) || lookup_owner_id)) ||
                ((lookup_dir_state == DIR_S) &&
                 ((lookup_sharers == 2'b00) || lookup_owner_id)) ||
                ((lookup_dir_state == DIR_U) && (lookup_sharers != 2'b00))) begin
              protocol_error <= 1'b1;
              state_q <= DIR_ERROR;
            end else begin
              case (req_opcode)
                REQ_GETS: begin
                  grant_has_data_q <= 1'b1;
                  case (lookup_dir_state)
                    DIR_I: begin
                      next_dir_state_q <= DIR_U;
                      next_sharers_q <= 2'b00;
                      next_owner_q <= req_src_id;
                      grant_opcode_q <= GRANT_DATA_E;
                      line_xfer_kind_q <= XFER_L2_REFILL;
                      state_q <= DIR_START_XFER;
                    end
                    DIR_S: begin
                      next_dir_state_q <= DIR_S;
                      next_sharers_q <= lookup_sharers | source_mask;
                      next_owner_q <= 1'b0;
                      grant_opcode_q <= GRANT_DATA_S;
                      line_xfer_kind_q <= XFER_L2_REFILL;
                      state_q <= DIR_START_XFER;
                    end
                    DIR_U: begin
                      // A GetS from the current owner is a recoverable
                      // re-fetch: return the owner's current line and make
                      // that owner Shared.
                      target_mask = core_bit(lookup_owner_id);
                      pending_targets_q <= target_mask;
                      snoop_opcode_q <= SNOOP_READ;
                      next_dir_state_q <= DIR_S;
                      next_sharers_q <= target_mask | source_mask;
                      next_owner_q <= 1'b0;
                      grant_opcode_q <= GRANT_DATA_S;
                      snoop_response_must_be_data_q <= 1'b1;
                      snoop_resume_q <= DIR_COMMIT;
                      state_q <= DIR_SEND_SNOOP;
                    end
                    default: begin
                      protocol_error <= 1'b1;
                      state_q <= DIR_ERROR;
                    end
                  endcase
                end

                REQ_GETM: begin
                  grant_has_data_q <= 1'b1;
                  grant_opcode_q <= GRANT_DATA_M;
                  case (lookup_dir_state)
                    DIR_I: begin
                      next_dir_state_q <= DIR_U;
                      next_sharers_q <= 2'b00;
                      next_owner_q <= req_src_id;
                      line_xfer_kind_q <= XFER_L2_REFILL;
                      state_q <= DIR_START_XFER;
                    end
                    DIR_S: begin
                      target_mask = lookup_sharers & ~source_mask;
                      pending_targets_q <= target_mask;
                      next_dir_state_q <= DIR_U;
                      next_sharers_q <= 2'b00;
                      next_owner_q <= req_src_id;
                      line_xfer_kind_q <= XFER_L2_REFILL;
                      snoop_opcode_q <= SNOOP_INVALIDATE;
                      snoop_response_must_be_data_q <= 1'b0;
                      snoop_resume_q <= DIR_START_XFER;
                      state_q <= (target_mask != 2'b00) ?
                                 DIR_SEND_SNOOP : DIR_START_XFER;
                    end
                    DIR_U: begin
                      if (lookup_owner_id == req_src_id) begin
                        // A requester already recorded as the unique owner
                        // needs no peer invalidation or line refill.
                        grant_has_data_q <= 1'b0;
                        grant_opcode_q <= GRANT_M;
                        next_dir_state_q <= DIR_U;
                        next_sharers_q <= 2'b00;
                        next_owner_q <= req_src_id;
                        state_q <= DIR_COMMIT;
                      end else begin
                        target_mask = core_bit(lookup_owner_id);
                        pending_targets_q <= target_mask;
                        next_dir_state_q <= DIR_U;
                        next_sharers_q <= 2'b00;
                        next_owner_q <= req_src_id;
                        snoop_opcode_q <= SNOOP_INVALIDATE;
                        snoop_response_must_be_data_q <= 1'b1;
                        snoop_resume_q <= DIR_COMMIT;
                        state_q <= DIR_SEND_SNOOP;
                      end
                    end
                    default: begin
                      protocol_error <= 1'b1;
                      state_q <= DIR_ERROR;
                    end
                  endcase
                end

                REQ_UPGRADE: begin
                  grant_opcode_q <= GRANT_M;
                  grant_has_data_q <= 1'b0;
                  case (lookup_dir_state)
                    DIR_S: begin
                      target_mask = lookup_sharers & ~source_mask;
                      pending_targets_q <= target_mask;
                      next_dir_state_q <= DIR_U;
                      next_sharers_q <= 2'b00;
                      next_owner_q <= req_src_id;
                      snoop_opcode_q <= SNOOP_INVALIDATE;
                      snoop_response_must_be_data_q <= 1'b0;
                      snoop_resume_q <= DIR_COMMIT;
                      state_q <= (target_mask != 2'b00) ?
                                 DIR_SEND_SNOOP : DIR_COMMIT;
                    end
                    DIR_U: begin
                      if (lookup_owner_id == req_src_id) begin
                        next_dir_state_q <= DIR_U;
                        next_sharers_q <= 2'b00;
                        next_owner_q <= req_src_id;
                        state_q <= DIR_COMMIT;
                      end else begin
                        // Upgrade from a non-owner while the directory is U
                        // is malformed; recover using the owner's line data.
                        protocol_error <= 1'b1;
                        grant_opcode_q <= GRANT_DATA_M;
                        grant_has_data_q <= 1'b1;
                        target_mask = core_bit(lookup_owner_id);
                        pending_targets_q <= target_mask;
                        next_dir_state_q <= DIR_U;
                        next_sharers_q <= 2'b00;
                        next_owner_q <= req_src_id;
                        snoop_opcode_q <= SNOOP_INVALIDATE;
                        snoop_response_must_be_data_q <= 1'b1;
                        snoop_resume_q <= DIR_COMMIT;
                        state_q <= DIR_SEND_SNOOP;
                      end
                    end
                    DIR_I: begin
                      // Recover an invalid Upgrade as a GetM so stale caller
                      // metadata cannot result in a write without a line.
                      protocol_error <= 1'b1;
                      grant_opcode_q <= GRANT_DATA_M;
                      grant_has_data_q <= 1'b1;
                      next_dir_state_q <= DIR_U;
                      next_sharers_q <= 2'b00;
                      next_owner_q <= req_src_id;
                      line_xfer_kind_q <= XFER_L2_REFILL;
                      state_q <= DIR_START_XFER;
                    end
                    default: begin
                      protocol_error <= 1'b1;
                      state_q <= DIR_ERROR;
                    end
                  endcase
                end

                REQ_PUTS: begin
                  grant_opcode_q <= GRANT_PUT_ACK;
                  if (lookup_dir_state == DIR_S) begin
                    if (!lookup_sharers[req_src_id]) begin
                      protocol_error <= 1'b1;
                      state_q <= DIR_ERROR;
                    end else begin
                      next_sharers_q <= lookup_sharers & ~source_mask;
                      next_dir_state_q <=
                        ((lookup_sharers & ~source_mask) == 0) ? DIR_I : DIR_S;
                      next_owner_q <= 1'b0;
                      state_q <= DIR_COMMIT;
                    end
                  end else if ((lookup_dir_state == DIR_U) &&
                               (lookup_owner_id == req_src_id)) begin
                    // U does not tell us whether the L1 owner is E or M.
                    // Require PutE or PutM so a dirty M line cannot be lost.
                    protocol_error <= 1'b1;
                    state_q <= DIR_ERROR;
                    grant_opcode_q <= GRANT_PUT_ACK;
                  end else if (lookup_dir_state != DIR_I) begin
                    protocol_error <= 1'b1;
                    state_q <= DIR_ERROR;
                  end else begin
                    state_q <= DIR_COMMIT;
                  end
                end

                REQ_PUTE: begin
                  grant_opcode_q <= GRANT_PUT_ACK;
                  if ((lookup_dir_state == DIR_U) &&
                      (lookup_owner_id == req_src_id)) begin
                    next_dir_state_q <= DIR_I;
                    next_sharers_q <= 2'b00;
                    next_owner_q <= 1'b0;
                    state_q <= DIR_COMMIT;
                  end else if (lookup_dir_state == DIR_I) begin
                    state_q <= DIR_COMMIT;
                  end else begin
                    protocol_error <= 1'b1;
                    state_q <= DIR_ERROR;
                  end
                end

                REQ_PUTM: begin
                  grant_opcode_q <= GRANT_PUT_ACK;
                  if ((lookup_dir_state == DIR_U) &&
                      (lookup_owner_id == req_src_id)) begin
                    next_dir_state_q <= DIR_I;
                    next_sharers_q <= 2'b00;
                    next_owner_q <= 1'b0;
                    line_xfer_kind_q <= XFER_PUTM_TO_L2;
                    state_q <= DIR_START_XFER;
                  end else begin
                    protocol_error <= 1'b1;
                    state_q <= DIR_ERROR;
                  end
                end

                default: begin
                  protocol_error <= 1'b1;
                  state_q <= DIR_ERROR;
                end
              endcase
            end
          end
        end

        DIR_START_XFER: begin
          if (line_xfer_start_valid && line_xfer_start_ready)
            state_q <= DIR_WAIT_XFER;
        end

        DIR_WAIT_XFER: begin
          if (line_xfer_done_valid && line_xfer_done_ready)
            state_q <= DIR_COMMIT;
        end

        DIR_SEND_SNOOP: begin
          if (snoop_req_valid && snoop_req_ready) begin
            current_target_q <= snoop_target_id;
            state_q <= DIR_WAIT_SNOOP;
          end
        end

        DIR_WAIT_SNOOP: begin
          if (snoop_rsp_valid && snoop_rsp_ready) begin
            if ((snoop_opcode_q == SNOOP_READ) &&
                (snoop_rsp_opcode != SNOOP_RSP_DATA)) begin
              protocol_error <= 1'b1;
              state_q <= DIR_ERROR;
            end else if ((snoop_opcode_q == SNOOP_INVALIDATE) &&
                         snoop_response_must_be_data_q &&
                         (snoop_rsp_opcode != SNOOP_RSP_DATA)) begin
              protocol_error <= 1'b1;
              state_q <= DIR_ERROR;
            end else if ((snoop_opcode_q == SNOOP_INVALIDATE) &&
                         !snoop_response_must_be_data_q &&
                         (snoop_rsp_opcode != SNOOP_RSP_INV_ACK)) begin
              protocol_error <= 1'b1;
              state_q <= DIR_ERROR;
            end else begin
              pending_targets_q <= targets_after_current;
              state_q <= (targets_after_current != 2'b00) ?
                         DIR_SEND_SNOOP : snoop_resume_q;
            end
          end
        end

        DIR_COMMIT: begin
          if (dir_write_valid && dir_write_ready)
            state_q <= DIR_SEND_GRANT;
        end

        DIR_SEND_GRANT: begin
          if (grant_valid && grant_ready)
            state_q <= DIR_WAIT_GRANT_COMMIT;
        end

        DIR_WAIT_GRANT_COMMIT: begin
          if (grant_commit_valid && grant_commit_ready)
            state_q <= DIR_FINISH;
        end

        DIR_FINISH: state_q <= DIR_IDLE;
        DIR_ERROR: state_q <= DIR_ERROR;

        default: begin
          protocol_error <= 1'b1;
          state_q <= DIR_ERROR;
        end
      endcase
    end
  end
endmodule
