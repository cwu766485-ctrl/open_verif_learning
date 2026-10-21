module MesiL1Controller #(
  parameter int TXN_ID_WIDTH = coherence_protocol_pkg::TXN_ID_WIDTH
) (
  input  logic clock,
  input  logic reset,

  // One CPU request may be outstanding. Lookup results are supplied with the
  // request so this control block does not own or duplicate the L1 tag array.
  input  logic cpu_req_valid,
  output logic cpu_req_ready,
  input  logic [31:0] cpu_req_addr,
  input  logic cpu_req_write,
  input  logic cpu_req_hit,
  input  coherence_protocol_pkg::mesi_state_t cpu_req_line_state,
  output logic cpu_resp_valid,
  input  logic cpu_resp_ready,
  output logic [31:0] cpu_resp_addr,
  output logic cpu_resp_write,
  output logic [TXN_ID_WIDTH-1:0] cpu_resp_txn_id,

  // L1 -> Directory request and Directory -> L1 ownership grant.
  output logic dir_req_valid,
  input  logic dir_req_ready,
  output coherence_protocol_pkg::request_opcode_t dir_req_opcode,
  output logic [31:0] dir_req_line_addr,
  output logic [TXN_ID_WIDTH-1:0] dir_req_txn_id,
  input  logic grant_valid,
  output logic grant_ready,
  input  coherence_protocol_pkg::grant_opcode_t grant_opcode,
  input  logic [TXN_ID_WIDTH-1:0] grant_txn_id,

  // Refill beats are forwarded to the L1 data array. The payload source must
  // hold each beat stable while valid is high and ready is low.
  input  logic grant_data_valid,
  output logic grant_data_ready,
  input  logic [TXN_ID_WIDTH-1:0] grant_data_txn_id,
  input  logic [2:0] grant_data_beat_idx,
  input  logic [63:0] grant_data,
  input  logic grant_data_last,
  output logic refill_valid,
  input  logic refill_ready,
  output logic [TXN_ID_WIDTH-1:0] refill_txn_id,
  output logic [2:0] refill_beat_idx,
  output logic [63:0] refill_data,
  output logic refill_last,
  output logic grant_commit_valid,
  input  logic grant_commit_ready,
  output logic [TXN_ID_WIDTH-1:0] grant_commit_txn_id,

  // The snoop path has its own one-entry control slot and remains receptive
  // while the CPU side waits for a grant.
  input  logic snoop_valid,
  output logic snoop_ready,
  input  logic [31:0] snoop_line_addr,
  input  coherence_protocol_pkg::snoop_opcode_t snoop_opcode,
  input  logic [TXN_ID_WIDTH-1:0] snoop_txn_id,
  input  logic snoop_tag_hit,
  input  coherence_protocol_pkg::mesi_state_t snoop_line_state,
  output logic snoop_rsp_valid,
  input  logic snoop_rsp_ready,
  output coherence_protocol_pkg::snoop_response_t snoop_rsp_opcode,
  output logic [TXN_ID_WIDTH-1:0] snoop_rsp_txn_id,
  output logic snoop_rsp_has_data,

  // Snoop line data is requested and returned by the L1 data-array adapter.
  output logic snoop_line_rd_valid,
  input  logic snoop_line_rd_ready,
  output logic [31:0] snoop_line_rd_addr,
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

  // Separate metadata write ports let the eventual array adapter arbitrate
  // CPU-side and snoop-side updates without blocking snoop acceptance.
  output logic cpu_meta_write_valid,
  input  logic cpu_meta_write_ready,
  output logic [31:0] cpu_meta_write_line_addr,
  output coherence_protocol_pkg::mesi_state_t cpu_meta_write_state,
  output logic snoop_meta_write_valid,
  input  logic snoop_meta_write_ready,
  output logic [31:0] snoop_meta_write_line_addr,
  output coherence_protocol_pkg::mesi_state_t snoop_meta_write_state,

  output logic protocol_error
);
  import coherence_protocol_pkg::*;

  typedef enum logic [2:0] {
    CPU_IDLE,
    CPU_SEND_REQ,
    CPU_WAIT_GRANT,
    CPU_REFILL,
    CPU_META_WRITE,
    CPU_RESP,
    CPU_ERROR
  } cpu_state_t;

  typedef enum logic [2:0] {
    SNP_IDLE,
    SNP_SEND_RSP,
    SNP_READ_LINE,
    SNP_SEND_DATA,
    SNP_META_WRITE,
    SNP_ERROR
  } snoop_state_t;

  cpu_state_t cpu_state_q;
  snoop_state_t snoop_state_q;
  logic [TXN_ID_WIDTH-1:0] txn_counter_q;
  logic [TXN_ID_WIDTH-1:0] cpu_txn_q;
  logic [TXN_ID_WIDTH-1:0] snoop_txn_q;
  grant_opcode_t grant_opcode_q;
  logic [31:0] cpu_addr_q;
  logic [31:0] snoop_addr_q;
  logic [31:0] resp_addr_q;
  logic resp_write_q;
  request_opcode_t req_opcode_q;
  mesi_state_t cpu_meta_state_q;
  mesi_state_t snoop_meta_state_q;
  snoop_response_t snoop_rsp_opcode_q;
  logic snoop_rsp_has_data_q;
  logic [2:0] refill_expected_beat_q;
  logic [2:0] snoop_expected_beat_q;
  logic cpu_resp_pending_q;
  logic grant_commit_pending_q;
  logic cpu_meta_pending_q;
  logic snoop_meta_pending_q;
  logic snoop_state_change_q;

  always_comb begin
    cpu_req_ready = (cpu_state_q == CPU_IDLE);
    cpu_resp_valid = (cpu_state_q == CPU_RESP) && cpu_resp_pending_q;
    cpu_resp_addr = resp_addr_q;
    cpu_resp_write = resp_write_q;
    cpu_resp_txn_id = cpu_txn_q;

    dir_req_valid = (cpu_state_q == CPU_SEND_REQ);
    dir_req_opcode = req_opcode_q;
    dir_req_line_addr = line_align(cpu_addr_q);
    dir_req_txn_id = cpu_txn_q;
    grant_ready = (cpu_state_q == CPU_WAIT_GRANT) &&
                  (grant_txn_id == cpu_txn_q);

    grant_data_ready = (cpu_state_q == CPU_REFILL) &&
                       (grant_data_txn_id == cpu_txn_q) && refill_ready;
    refill_valid = (cpu_state_q == CPU_REFILL) && grant_data_valid &&
                   (grant_data_txn_id == cpu_txn_q);
    refill_txn_id = cpu_txn_q;
    refill_beat_idx = grant_data_beat_idx;
    refill_data = grant_data;
    refill_last = grant_data_last;
    grant_commit_valid = (cpu_state_q == CPU_RESP) &&
                         grant_commit_pending_q;
    grant_commit_txn_id = cpu_txn_q;

    snoop_ready = (snoop_state_q == SNP_IDLE);
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

    cpu_meta_write_valid = (cpu_state_q == CPU_META_WRITE) &&
                           cpu_meta_pending_q;
    cpu_meta_write_line_addr = line_align(cpu_addr_q);
    cpu_meta_write_state = cpu_meta_state_q;
    snoop_meta_write_valid = (snoop_state_q == SNP_META_WRITE) &&
                             snoop_meta_pending_q;
    snoop_meta_write_line_addr = snoop_addr_q;
    snoop_meta_write_state = snoop_meta_state_q;
  end

  always_ff @(posedge clock) begin
    if (reset) begin
      cpu_state_q <= CPU_IDLE;
      snoop_state_q <= SNP_IDLE;
      txn_counter_q <= '0;
      cpu_txn_q <= '0;
      snoop_txn_q <= '0;
      grant_opcode_q <= GRANT_DATA_S;
      cpu_addr_q <= '0;
      snoop_addr_q <= '0;
      resp_addr_q <= '0;
      resp_write_q <= 1'b0;
      req_opcode_q <= REQ_GETS;
      cpu_meta_state_q <= MESI_I;
      snoop_meta_state_q <= MESI_I;
      snoop_rsp_opcode_q <= SNOOP_RSP_ACK;
      snoop_rsp_has_data_q <= 1'b0;
      refill_expected_beat_q <= '0;
      snoop_expected_beat_q <= '0;
      cpu_resp_pending_q <= 1'b0;
      grant_commit_pending_q <= 1'b0;
      cpu_meta_pending_q <= 1'b0;
      snoop_meta_pending_q <= 1'b0;
      snoop_state_change_q <= 1'b0;
      protocol_error <= 1'b0;
    end else begin
      case (cpu_state_q)
        CPU_IDLE: begin
          cpu_resp_pending_q <= 1'b0;
          cpu_meta_pending_q <= 1'b0;
          if (cpu_req_valid && cpu_req_ready) begin
            cpu_addr_q <= cpu_req_addr;
            resp_addr_q <= cpu_req_addr;
            resp_write_q <= cpu_req_write;
            cpu_txn_q <= txn_counter_q;
            txn_counter_q <= txn_counter_q + 1'b1;

            if (cpu_req_hit && (cpu_req_line_state == MESI_I)) begin
              protocol_error <= 1'b1;
              cpu_state_q <= CPU_ERROR;
            end else if (cpu_req_hit && !cpu_req_write) begin
              cpu_resp_pending_q <= 1'b1;
              cpu_state_q <= CPU_RESP;
            end else if (cpu_req_hit && cpu_req_write &&
                         (cpu_req_line_state == MESI_M)) begin
              cpu_resp_pending_q <= 1'b1;
              cpu_state_q <= CPU_RESP;
            end else if (cpu_req_hit && cpu_req_write &&
                         (cpu_req_line_state == MESI_E)) begin
              cpu_meta_state_q <= MESI_M;
              cpu_meta_pending_q <= 1'b1;
              cpu_state_q <= CPU_META_WRITE;
            end else if (cpu_req_hit && cpu_req_write &&
                         (cpu_req_line_state == MESI_S)) begin
              req_opcode_q <= REQ_UPGRADE;
              cpu_state_q <= CPU_SEND_REQ;
            end else begin
              req_opcode_q <= cpu_req_write ? REQ_GETM : REQ_GETS;
              cpu_state_q <= CPU_SEND_REQ;
            end
          end
        end

        CPU_SEND_REQ: begin
          if (dir_req_valid && dir_req_ready)
            cpu_state_q <= CPU_WAIT_GRANT;
        end

        CPU_WAIT_GRANT: begin
          if (grant_valid && grant_ready) begin
            if (grant_opcode == GRANT_PUT_ACK) begin
              protocol_error <= 1'b1;
              cpu_state_q <= CPU_ERROR;
            end else if (grant_contains_data(grant_opcode)) begin
              grant_opcode_q <= grant_opcode;
              grant_commit_pending_q <= 1'b1;
              refill_expected_beat_q <= 3'd0;
              cpu_state_q <= CPU_REFILL;
            end else begin
              grant_opcode_q <= grant_opcode;
              cpu_meta_state_q <= grant_to_mesi(grant_opcode);
              cpu_meta_pending_q <= 1'b1;
              grant_commit_pending_q <= 1'b1;
              cpu_state_q <= CPU_META_WRITE;
            end
          end
        end

        CPU_REFILL: begin
          if (grant_data_valid && grant_data_ready) begin
            if ((grant_data_beat_idx != refill_expected_beat_q) ||
                (grant_data_last != (grant_data_beat_idx == 3'd7)))
              protocol_error <= 1'b1;

            if ((grant_data_beat_idx == 3'd7) && grant_data_last) begin
              cpu_meta_state_q <= grant_to_mesi(grant_opcode_q);
              cpu_meta_pending_q <= 1'b1;
              cpu_state_q <= CPU_META_WRITE;
            end else if (grant_data_last ||
                         (grant_data_beat_idx != refill_expected_beat_q) ||
                         (grant_data_beat_idx == 3'd7)) begin
              cpu_state_q <= CPU_ERROR;
            end else begin
              refill_expected_beat_q <= refill_expected_beat_q + 1'b1;
            end
          end
        end

        CPU_META_WRITE: begin
          if (cpu_meta_write_valid && cpu_meta_write_ready) begin
            cpu_meta_pending_q <= 1'b0;
            cpu_resp_pending_q <= 1'b1;
            cpu_state_q <= CPU_RESP;
          end
        end

        CPU_RESP: begin
          if (cpu_resp_valid && cpu_resp_ready)
            cpu_resp_pending_q <= 1'b0;
          if (grant_commit_valid && grant_commit_ready)
            grant_commit_pending_q <= 1'b0;
          if ((!cpu_resp_pending_q || (cpu_resp_valid && cpu_resp_ready)) &&
              (!grant_commit_pending_q ||
               (grant_commit_valid && grant_commit_ready))) begin
            cpu_state_q <= CPU_IDLE;
          end
        end

        CPU_ERROR: cpu_state_q <= CPU_ERROR;

        default: begin
          cpu_state_q <= CPU_IDLE;
          protocol_error <= 1'b1;
        end
      endcase

      case (snoop_state_q)
        SNP_IDLE: begin
          snoop_meta_pending_q <= 1'b0;
          snoop_state_change_q <= 1'b0;
          if (snoop_valid && snoop_ready) begin
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
          if (snoop_line_rd_valid && snoop_line_rd_ready)
            snoop_state_q <= SNP_SEND_DATA;
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
              end else
                snoop_state_q <= SNP_IDLE;
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
