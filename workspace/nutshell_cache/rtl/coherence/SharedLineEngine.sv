// Shared line transaction FSM. This is a structural extraction of the original
// top-level FSM: state encodings, reset values, priorities, and handshakes match.
module SharedLineEngine #(
  parameter int TXN_ID_WIDTH = coherence_protocol_pkg::TXN_ID_WIDTH,
  parameter int NUM_MSHRS = 4,
  parameter int MSHR_ID_WIDTH = (NUM_MSHRS < 2) ? 1 : $clog2(NUM_MSHRS)
) (
  input logic clock,
  input logic reset,
  input logic mem_r_protocol_bad,
  input logic mem_rd_data_valid,
  input logic mem_rd_data_ready,
  input logic mem_rd_data_error,
  input logic mem_mshr_r_match,
  input logic mem_wr_rsp_valid,
  input logic mem_wr_rsp_ready,
  input logic [TXN_ID_WIDTH-1:0] mem_wr_rsp_txn_id,
  input logic mem_wr_rsp_error,
  input logic dir_xfer_start_valid,
  input logic dir_xfer_start_ready,
  input coherence_protocol_pkg::line_xfer_kind_t dir_xfer_kind,
  input logic [31:0] dir_xfer_addr,
  input logic dir_xfer_src,
  input logic [TXN_ID_WIDTH-1:0] dir_xfer_txn_id,
  input logic [MSHR_ID_WIDTH-1:0] dir_xfer_context_id,
  input logic dir_xfer_done_valid,
  input logic dir_xfer_done_ready,
  input logic dir_grant_valid,
  input logic dir_grant_ready,
  input logic dir_grant_dst,
  input logic dir_grant_has_data,
  input logic [31:0] dir_grant_addr,
  input logic [TXN_ID_WIDTH-1:0] dir_grant_txn_id,
  input logic l2_lookup_hit,
  input logic l2_alloc_victim_valid,
  input logic [31:0] l2_alloc_victim_addr,
  input logic l2_alloc_victim_dirty,
  input coherence_protocol_pkg::directory_state_t l2_alloc_victim_state,
  input logic [1:0] l2_alloc_victim_sharers,
  input logic l2_alloc_victim_owner,
  input logic l2_line_rd_valid,
  input logic l2_line_rd_ready,
  input logic l2_line_rd_hit,
  input logic l2_line_data_valid,
  input logic l2_line_data_ready,
  input logic l2_line_data_last,
  input logic l2_line_wr_valid,
  input logic l2_line_wr_ready,
  input logic [2:0] l2_line_wr_beat_idx,
  input logic l2_line_wr_last,
  input logic l2_entry_invalidate_valid,
  input logic l2_entry_invalidate_ready,
  input logic l2_mark_clean_valid,
  input logic l2_mark_clean_ready,
  input logic l2_dir_write_ready,
  input logic mem_rd_req_valid,
  input logic mem_rd_req_ready,
  input logic mem_wr_req_valid,
  input logic mem_wr_req_ready,
  input logic mem_wr_data_valid,
  input logic mem_wr_data_ready,
  input logic [2:0] mem_wr_data_beat_idx,
  input logic mem_wr_data_last,
  input logic snoop_valid_core [0:1],
  input logic snoop_ready_core [0:1],
  input logic snoop_rsp_has_data_core [0:1],
  input logic [TXN_ID_WIDTH-1:0] snoop_rsp_txn_id_core [0:1],
  input coherence_protocol_pkg::snoop_response_t snoop_rsp_opcode_core [0:1],
  input logic [TXN_ID_WIDTH-1:0] snoop_data_txn_id_core [0:1],
  input logic victim_snoop_data_to_l2,
  input logic victim_snoop_rsp_fire,
  input logic [1:0] victim_targets_after_current,
  input logic victim_owner_retired_before_snoop,
  output logic [4:0] engine_state_q,
  output logic [31:0] engine_addr_q,
  output logic [TXN_ID_WIDTH-1:0] engine_txn_q,
  output logic [MSHR_ID_WIDTH-1:0] engine_context_q,
  output logic engine_src_q,
  output logic [2:0] mem_expected_beat_q,
  output logic [2:0] victim_expected_beat_q,
  output logic [31:0] victim_addr_q,
  output logic [1:0] victim_pending_targets_q,
  output logic victim_snoop_target_q,
  output logic victim_snoop_data_expected_q,
  output logic victim_snoop_data_complete_q,
  output logic victim_dirty_q,
  output logic grant_dst_q,
  output logic [31:0] grant_addr_q,
  output logic [TXN_ID_WIDTH-1:0] grant_txn_q,
  output logic memory_adapter_protocol_error,
  output logic memory_adapter_error
);
  import coherence_protocol_pkg::*;

  localparam logic [4:0] ENGINE_IDLE = 5'd0;
  localparam logic [4:0] ENGINE_VICTIM_READ = 5'd1;
  localparam logic [4:0] ENGINE_VICTIM_WRITE_REQ = 5'd2;
  localparam logic [4:0] ENGINE_VICTIM_WRITE_STREAM = 5'd3;
  localparam logic [4:0] ENGINE_VICTIM_WRITE_WAIT_RSP = 5'd4;
  localparam logic [4:0] ENGINE_VICTIM_MARK_CLEAN = 5'd5;
  localparam logic [4:0] ENGINE_VICTIM_INVALIDATE = 5'd6;
  localparam logic [4:0] ENGINE_PUTM_STREAM = 5'd7;
  localparam logic [4:0] ENGINE_MEM_REQ = 5'd8;
  localparam logic [4:0] ENGINE_XFER_DONE = 5'd9;
  localparam logic [4:0] ENGINE_GRANT_READ = 5'd10;
  localparam logic [4:0] ENGINE_GRANT_STREAM = 5'd11;
  localparam logic [4:0] ENGINE_VICTIM_SNOOP_SEND = 5'd12;
  localparam logic [4:0] ENGINE_VICTIM_SNOOP_WAIT = 5'd13;
  localparam logic [4:0] ENGINE_VICTIM_CLEAR_DIR = 5'd14;
  localparam logic [4:0] ENGINE_ERROR = 5'd15;

  always_ff @(posedge clock) begin
    if (reset) begin
      engine_state_q <= ENGINE_IDLE;
      engine_addr_q <= '0;
      engine_txn_q <= '0;
      engine_context_q <= '0;
      engine_src_q <= 1'b0;
      mem_expected_beat_q <= '0;
      victim_expected_beat_q <= '0;
      victim_addr_q <= '0;
      victim_pending_targets_q <= 2'b00;
      victim_snoop_target_q <= 1'b0;
      victim_snoop_data_expected_q <= 1'b0;
      victim_snoop_data_complete_q <= 1'b0;
      victim_dirty_q <= 1'b0;
      grant_dst_q <= 1'b0;
      grant_addr_q <= '0;
      grant_txn_q <= '0;
      memory_adapter_protocol_error <= 1'b0;
      memory_adapter_error <= 1'b0;
    end else begin
      if (mem_r_protocol_bad) begin
        memory_adapter_protocol_error <= 1'b1;
        engine_state_q <= ENGINE_ERROR;
      end else if (mem_rd_data_valid && mem_rd_data_ready &&
                   mem_mshr_r_match && mem_rd_data_error) begin
        memory_adapter_error <= 1'b1;
        engine_state_q <= ENGINE_ERROR;
      end else if (mem_wr_rsp_valid && mem_wr_rsp_ready &&
                   (engine_state_q != ENGINE_VICTIM_WRITE_WAIT_RSP)) begin
        memory_adapter_protocol_error <= 1'b1;
        engine_state_q <= ENGINE_ERROR;
      end else case (engine_state_q)
        ENGINE_IDLE: begin
          if (dir_xfer_start_valid && dir_xfer_start_ready) begin
            engine_addr_q <= line_align(dir_xfer_addr);
            engine_txn_q <= dir_xfer_txn_id;
            engine_context_q <= dir_xfer_context_id;
            mem_expected_beat_q <= '0;
            if (dir_xfer_kind == XFER_L2_REFILL) begin
              if (l2_lookup_hit)
                engine_state_q <= ENGINE_XFER_DONE;
              else if (l2_alloc_victim_valid) begin
                victim_addr_q <= l2_alloc_victim_addr;
                victim_dirty_q <= l2_alloc_victim_dirty;
                victim_snoop_data_complete_q <= 1'b0;
                if ((l2_alloc_victim_state == DIR_I) &&
                    (l2_alloc_victim_sharers == 2'b00) &&
                    !l2_alloc_victim_owner) begin
                  if (l2_alloc_victim_dirty)
                    engine_state_q <= ENGINE_VICTIM_READ;
                  else
                    engine_state_q <= ENGINE_VICTIM_INVALIDATE;
                end else if ((l2_alloc_victim_state == DIR_S) &&
                             (l2_alloc_victim_sharers != 2'b00) &&
                             !l2_alloc_victim_owner) begin
                  victim_pending_targets_q <= l2_alloc_victim_sharers;
                  victim_snoop_target_q <= !l2_alloc_victim_sharers[0];
                  victim_snoop_data_expected_q <= 1'b0;
                  engine_state_q <= ENGINE_VICTIM_SNOOP_SEND;
                end else if ((l2_alloc_victim_state == DIR_U) &&
                             (l2_alloc_victim_sharers == 2'b00)) begin
                  victim_pending_targets_q <= l2_alloc_victim_owner ?
                                              2'b10 : 2'b01;
                  victim_snoop_target_q <= l2_alloc_victim_owner;
                  victim_snoop_data_expected_q <= 1'b1;
                  victim_snoop_data_complete_q <= 1'b0;
                  victim_dirty_q <= 1'b1;
                  mem_expected_beat_q <= 3'd0;
                  engine_state_q <= ENGINE_VICTIM_SNOOP_SEND;
                end else begin
                  memory_adapter_protocol_error <= 1'b1;
                  engine_state_q <= ENGINE_ERROR;
                end
              end else
                engine_state_q <= ENGINE_MEM_REQ;
            end else if (dir_xfer_kind == XFER_PUTM_TO_L2) begin
              engine_src_q <= dir_xfer_src;
              engine_state_q <= ENGINE_PUTM_STREAM;
            end else begin
              memory_adapter_protocol_error <= 1'b1;
              engine_state_q <= ENGINE_ERROR;
            end
          end else if (dir_grant_valid && dir_grant_ready &&
                       dir_grant_has_data) begin
            grant_dst_q <= dir_grant_dst;
            grant_addr_q <= line_align(dir_grant_addr);
            grant_txn_q <= dir_grant_txn_id;
            if (l2_line_rd_valid && l2_line_rd_ready) begin
              if (l2_line_rd_hit)
                engine_state_q <= ENGINE_GRANT_STREAM;
              else begin
                memory_adapter_protocol_error <= 1'b1;
                engine_state_q <= ENGINE_ERROR;
              end
            end else begin
              engine_state_q <= ENGINE_GRANT_READ;
            end
          end
        end

        ENGINE_VICTIM_READ: begin
          if (l2_line_rd_valid && l2_line_rd_ready) begin
            if (l2_line_rd_hit) begin
              victim_expected_beat_q <= 3'd0;
              engine_state_q <= ENGINE_VICTIM_WRITE_REQ;
            end else begin
              memory_adapter_protocol_error <= 1'b1;
              engine_state_q <= ENGINE_ERROR;
            end
          end
        end

        ENGINE_VICTIM_WRITE_REQ: begin
          if (mem_wr_req_valid && mem_wr_req_ready)
            engine_state_q <= ENGINE_VICTIM_WRITE_STREAM;
        end

        ENGINE_VICTIM_WRITE_STREAM: begin
          if (mem_wr_data_valid && mem_wr_data_ready) begin
            if ((mem_wr_data_beat_idx != victim_expected_beat_q) ||
                (mem_wr_data_last != (mem_wr_data_beat_idx == 3'd7))) begin
              memory_adapter_protocol_error <= 1'b1;
              engine_state_q <= ENGINE_ERROR;
            end else if (mem_wr_data_beat_idx == 3'd7) begin
              engine_state_q <= ENGINE_VICTIM_WRITE_WAIT_RSP;
            end else begin
              victim_expected_beat_q <= victim_expected_beat_q + 1'b1;
            end
          end
        end

        ENGINE_VICTIM_WRITE_WAIT_RSP: begin
          if (mem_wr_rsp_valid && mem_wr_rsp_ready) begin
            if (mem_wr_rsp_txn_id != engine_txn_q) begin
              memory_adapter_protocol_error <= 1'b1;
              engine_state_q <= ENGINE_ERROR;
            end else if (mem_wr_rsp_error) begin
              memory_adapter_error <= 1'b1;
              engine_state_q <= ENGINE_ERROR;
            end else begin
              engine_state_q <= ENGINE_VICTIM_MARK_CLEAN;
            end
          end
        end

        ENGINE_VICTIM_MARK_CLEAN: begin
          if (l2_mark_clean_valid && l2_mark_clean_ready)
            engine_state_q <= ENGINE_VICTIM_INVALIDATE;
        end

        ENGINE_VICTIM_INVALIDATE: begin
          if (l2_entry_invalidate_valid && l2_entry_invalidate_ready)
            engine_state_q <= ENGINE_MEM_REQ;
        end

        ENGINE_VICTIM_SNOOP_SEND: begin
          if (snoop_valid_core[victim_snoop_target_q] &&
              snoop_ready_core[victim_snoop_target_q])
            engine_state_q <= ENGINE_VICTIM_SNOOP_WAIT;
        end

        ENGINE_VICTIM_SNOOP_WAIT: begin
          if (victim_snoop_data_to_l2 && l2_line_wr_valid && l2_line_wr_ready) begin
            if ((l2_line_wr_beat_idx != mem_expected_beat_q) ||
                (l2_line_wr_last != (l2_line_wr_beat_idx == 3'd7)) ||
                (snoop_data_txn_id_core[victim_snoop_target_q] != engine_txn_q)) begin
              memory_adapter_protocol_error <= 1'b1;
              engine_state_q <= ENGINE_ERROR;
            end else if (l2_line_wr_beat_idx == 3'd7) begin
              victim_snoop_data_complete_q <= 1'b1;
              mem_expected_beat_q <= 3'd0;
            end else begin
              mem_expected_beat_q <= mem_expected_beat_q + 1'b1;
            end
          end

          if (victim_snoop_rsp_fire) begin
            if ((snoop_rsp_txn_id_core[victim_snoop_target_q] != engine_txn_q) ||
                (victim_snoop_data_expected_q &&
                 !((snoop_rsp_opcode_core[victim_snoop_target_q] == SNOOP_RSP_DATA &&
                    snoop_rsp_has_data_core[victim_snoop_target_q] &&
                    victim_snoop_data_complete_q) ||
                   victim_owner_retired_before_snoop)) ||
                (!victim_snoop_data_expected_q &&
                 ((snoop_rsp_opcode_core[victim_snoop_target_q] != SNOOP_RSP_INV_ACK) ||
                  snoop_rsp_has_data_core[victim_snoop_target_q]))) begin
              memory_adapter_protocol_error <= 1'b1;
              engine_state_q <= ENGINE_ERROR;
            end else begin
              victim_pending_targets_q <= victim_targets_after_current;
              victim_snoop_data_expected_q <= 1'b0;
              victim_snoop_data_complete_q <= 1'b0;
              if (victim_targets_after_current == 2'b00)
                engine_state_q <= ENGINE_VICTIM_CLEAR_DIR;
              else begin
                victim_snoop_target_q <= !victim_targets_after_current[0];
                engine_state_q <= ENGINE_VICTIM_SNOOP_SEND;
              end
            end
          end
        end

        ENGINE_VICTIM_CLEAR_DIR: begin
          if (l2_dir_write_ready) begin
            if (victim_dirty_q)
              engine_state_q <= ENGINE_VICTIM_READ;
            else
              engine_state_q <= ENGINE_VICTIM_INVALIDATE;
          end
        end

        ENGINE_MEM_REQ: begin
          if (mem_rd_req_valid && mem_rd_req_ready)
            engine_state_q <= ENGINE_IDLE;
        end

        ENGINE_PUTM_STREAM: begin
          if (l2_line_wr_valid && l2_line_wr_ready) begin
            if ((l2_line_wr_beat_idx != mem_expected_beat_q) ||
                (l2_line_wr_last != (l2_line_wr_beat_idx == 3'd7))) begin
              memory_adapter_protocol_error <= 1'b1;
              engine_state_q <= ENGINE_ERROR;
            end else if (l2_line_wr_beat_idx == 3'd7) begin
              engine_state_q <= ENGINE_XFER_DONE;
            end else begin
              mem_expected_beat_q <= mem_expected_beat_q + 1'b1;
            end
          end
        end

        ENGINE_XFER_DONE: begin
          if (dir_xfer_done_valid && dir_xfer_done_ready)
            engine_state_q <= ENGINE_IDLE;
        end

        ENGINE_GRANT_READ: begin
          if (l2_line_rd_valid && l2_line_rd_ready) begin
            if (l2_line_rd_hit)
              engine_state_q <= ENGINE_GRANT_STREAM;
            else begin
              memory_adapter_protocol_error <= 1'b1;
              engine_state_q <= ENGINE_ERROR;
            end
          end
        end

        ENGINE_GRANT_STREAM: begin
          if (l2_line_data_valid && l2_line_data_ready && l2_line_data_last)
            engine_state_q <= ENGINE_IDLE;
        end

        ENGINE_ERROR: engine_state_q <= ENGINE_ERROR;

        default: begin
          memory_adapter_protocol_error <= 1'b1;
          engine_state_q <= ENGINE_ERROR;
        end
      endcase
    end
  end
endmodule
