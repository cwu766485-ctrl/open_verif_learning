module MesiL1SnoopEngine #(
  parameter int TXN_ID_WIDTH = coherence_protocol_pkg::TXN_ID_WIDTH
) (
  input  logic clock,
  input  logic reset,
  input  logic snoop_accept,
  input  logic [31:0] snoop_line_addr,
  input  coherence_protocol_pkg::snoop_opcode_t snoop_opcode,
  input  logic [TXN_ID_WIDTH-1:0] snoop_txn_id,
  input  logic snoop_tag_hit,
  input  coherence_protocol_pkg::mesi_state_t snoop_line_state,
  output logic snoop_idle,
  output logic [31:0] snoop_active_addr,
  output logic snoop_rsp_valid,
  input  logic snoop_rsp_ready,
  output coherence_protocol_pkg::snoop_response_t snoop_rsp_opcode,
  output logic [TXN_ID_WIDTH-1:0] snoop_rsp_txn_id,
  output logic snoop_rsp_has_data,
  output logic snoop_line_rd_valid,
  input  logic snoop_line_rd_ready,
  output logic [31:0] snoop_line_rd_addr,
  input  logic snoop_line_rd_hit,
  input  logic snoop_array_data_valid,
  output logic snoop_array_data_ready,
  input  logic [2:0] snoop_array_beat_idx,
  input  logic [63:0] snoop_array_data,
  input  logic snoop_array_last,
  output logic snoop_data_valid,
  input  logic snoop_data_ready,
  output logic [TXN_ID_WIDTH-1:0] snoop_data_txn_id,
  output logic [2:0] snoop_data_beat_idx,
  output logic [63:0] snoop_data,
  output logic snoop_data_last,
  output logic snoop_meta_write_valid,
  input  logic snoop_meta_write_ready,
  output logic [31:0] snoop_meta_write_line_addr,
  output coherence_protocol_pkg::mesi_state_t snoop_meta_write_state,
  output logic protocol_error,
  output logic [2:0] monitor_snoop_state
);
  import coherence_protocol_pkg::*;

  typedef enum logic [2:0] {
    SNP_IDLE,
    SNP_SEND_RSP,
    SNP_READ_LINE,
    SNP_SEND_DATA,
    SNP_META_WRITE,
    SNP_ERROR
  } snoop_state_t;

  snoop_state_t snoop_state_q;
  logic [TXN_ID_WIDTH-1:0] snoop_txn_q;
  logic [31:0] snoop_addr_q;
  mesi_state_t snoop_meta_state_q;
  snoop_response_t snoop_rsp_opcode_q;
  logic snoop_rsp_has_data_q;
  logic [2:0] snoop_expected_beat_q;
  logic snoop_meta_pending_q;
  logic snoop_state_change_q;

  always_comb begin
    snoop_idle = (snoop_state_q == SNP_IDLE);
    snoop_active_addr = snoop_addr_q;
    monitor_snoop_state = snoop_state_q;
    snoop_rsp_valid = (snoop_state_q == SNP_SEND_RSP);
    snoop_rsp_opcode = snoop_rsp_opcode_q;
    snoop_rsp_txn_id = snoop_txn_q;
    snoop_rsp_has_data = snoop_rsp_has_data_q;
    snoop_line_rd_valid = (snoop_state_q == SNP_READ_LINE);
    snoop_line_rd_addr = snoop_addr_q;
    snoop_array_data_ready = (snoop_state_q == SNP_SEND_DATA) &&
                             snoop_data_ready;
    snoop_data_valid = (snoop_state_q == SNP_SEND_DATA) &&
                       snoop_array_data_valid;
    snoop_data_txn_id = snoop_txn_q;
    snoop_data_beat_idx = snoop_array_beat_idx;
    snoop_data = snoop_array_data;
    snoop_data_last = snoop_array_last;
    snoop_meta_write_valid = (snoop_state_q == SNP_META_WRITE) &&
                             snoop_meta_pending_q;
    snoop_meta_write_line_addr = snoop_addr_q;
    snoop_meta_write_state = snoop_meta_state_q;
  end

  always_ff @(posedge clock) begin
    if (reset) begin
      snoop_state_q <= SNP_IDLE;
      snoop_txn_q <= '0;
      snoop_addr_q <= '0;
      snoop_meta_state_q <= MESI_I;
      snoop_rsp_opcode_q <= SNOOP_RSP_ACK;
      snoop_rsp_has_data_q <= 1'b0;
      snoop_expected_beat_q <= '0;
      snoop_meta_pending_q <= 1'b0;
      snoop_state_change_q <= 1'b0;
      protocol_error <= 1'b0;
    end else begin
      case (snoop_state_q)
        SNP_IDLE: begin
          snoop_meta_pending_q <= 1'b0;
          snoop_state_change_q <= 1'b0;
          if (snoop_accept) begin
            snoop_addr_q <= line_align(snoop_line_addr);
            snoop_txn_q <= snoop_txn_id;
            snoop_expected_beat_q <= 3'd0;
            snoop_rsp_has_data_q <= 1'b0;
            snoop_state_change_q <= 1'b0;
            snoop_meta_state_q <= snoop_line_state;

            if (!snoop_tag_hit || (snoop_line_state == MESI_I)) begin
              snoop_rsp_opcode_q <= (snoop_opcode == SNOOP_INVALIDATE) ?
                                    SNOOP_RSP_INV_ACK : SNOOP_RSP_ACK;
              snoop_state_q <= SNP_SEND_RSP;
            end else if (snoop_opcode == SNOOP_READ) begin
              if ((snoop_line_state == MESI_E) ||
                  (snoop_line_state == MESI_M)) begin
                snoop_rsp_opcode_q <= SNOOP_RSP_DATA;
                snoop_rsp_has_data_q <= 1'b1;
                snoop_meta_state_q <= MESI_S;
                snoop_state_change_q <= 1'b1;
                snoop_state_q <= SNP_READ_LINE;
              end else begin
                snoop_rsp_opcode_q <= SNOOP_RSP_ACK;
                snoop_state_q <= SNP_SEND_RSP;
              end
            end else if (snoop_opcode == SNOOP_INVALIDATE) begin
              if ((snoop_line_state == MESI_E) ||
                  (snoop_line_state == MESI_M)) begin
                snoop_rsp_opcode_q <= SNOOP_RSP_DATA;
                snoop_rsp_has_data_q <= 1'b1;
                snoop_state_q <= SNP_READ_LINE;
              end else begin
                snoop_rsp_opcode_q <= SNOOP_RSP_INV_ACK;
                snoop_meta_pending_q <= 1'b1;
                snoop_state_q <= SNP_META_WRITE;
              end
              snoop_meta_state_q <= MESI_I;
              snoop_state_change_q <= 1'b1;
            end else begin
              protocol_error <= 1'b1;
            end
          end
        end

        SNP_SEND_RSP: begin
          if (snoop_rsp_valid && snoop_rsp_ready)
            snoop_state_q <= SNP_IDLE;
        end

        SNP_READ_LINE: begin
          if (snoop_line_rd_valid && snoop_line_rd_ready) begin
            if (snoop_line_rd_hit) begin
              snoop_state_q <= SNP_SEND_DATA;
            end else begin
              // A concurrent metadata commit may remove a line after lookup
              // but before the single-ported array grants its line read.
              snoop_rsp_opcode_q <= (snoop_meta_state_q == MESI_I) ?
                                    SNOOP_RSP_INV_ACK : SNOOP_RSP_ACK;
              snoop_rsp_has_data_q <= 1'b0;
              snoop_state_change_q <= 1'b0;
              snoop_meta_pending_q <= 1'b0;
              snoop_state_q <= SNP_SEND_RSP;
            end
          end
        end

        SNP_SEND_DATA: begin
          if (snoop_data_valid && snoop_data_ready) begin
            if ((snoop_array_beat_idx != snoop_expected_beat_q) ||
                (snoop_array_last != (snoop_array_beat_idx == 3'd7)))
              protocol_error <= 1'b1;

            if ((snoop_array_beat_idx == 3'd7) && snoop_array_last) begin
              if (snoop_state_change_q) begin
                snoop_meta_pending_q <= 1'b1;
                snoop_state_q <= SNP_META_WRITE;
              end else begin
                snoop_state_q <= SNP_IDLE;
              end
            end else if (snoop_array_last ||
                         (snoop_array_beat_idx != snoop_expected_beat_q) ||
                         (snoop_array_beat_idx == 3'd7)) begin
              snoop_state_q <= SNP_ERROR;
            end else begin
              snoop_expected_beat_q <= snoop_expected_beat_q + 1'b1;
            end
          end
        end

        SNP_META_WRITE: begin
          if (snoop_meta_write_valid && snoop_meta_write_ready) begin
            snoop_meta_pending_q <= 1'b0;
            snoop_state_q <= SNP_SEND_RSP;
          end
        end

        SNP_ERROR: snoop_state_q <= SNP_ERROR;

        default: begin
          snoop_state_q <= SNP_IDLE;
          protocol_error <= 1'b1;
        end
      endcase
    end
  end
endmodule
