// One independently tracked CPU miss transaction. Snoop arbitration and the
// shared Snoop engine live outside this block so multiple contexts can share
// one per-L1 snoop path.
module MesiL1MissContext #(
  parameter int TXN_ID_WIDTH = coherence_protocol_pkg::TXN_ID_WIDTH,
  parameter bit EXTERNAL_TXN_ID = 1'b0
) (
  input  logic clock,
  input  logic reset,

  input  logic cpu_req_valid,
  input  logic cpu_req_ready,
  input  logic [31:0] cpu_req_addr,
  input  logic cpu_req_write,
  input  logic cpu_req_hit,
  input  coherence_protocol_pkg::mesi_state_t cpu_req_line_state,
  input  logic [TXN_ID_WIDTH-1:0] cpu_req_txn_id,
  output logic cpu_resp_valid,
  input  logic cpu_resp_ready,
  output logic [31:0] cpu_resp_addr,
  output logic cpu_resp_write,
  output logic [TXN_ID_WIDTH-1:0] cpu_resp_txn_id,

  output logic dir_req_valid,
  input  logic dir_req_ready,
  output coherence_protocol_pkg::request_opcode_t dir_req_opcode,
  output logic [31:0] dir_req_line_addr,
  output logic [TXN_ID_WIDTH-1:0] dir_req_txn_id,
  input  logic grant_valid,
  output logic grant_ready,
  input  coherence_protocol_pkg::grant_opcode_t grant_opcode,
  input  logic [TXN_ID_WIDTH-1:0] grant_txn_id,

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

  output logic cpu_meta_write_valid,
  input  logic cpu_meta_write_ready,
  output logic [31:0] cpu_meta_write_line_addr,
  output coherence_protocol_pkg::mesi_state_t cpu_meta_write_state,

  output logic protocol_error,
  output logic [2:0] monitor_cpu_state,
  output logic [31:0] monitor_cpu_active_addr
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

  cpu_state_t cpu_state_q;
  logic [TXN_ID_WIDTH-1:0] txn_counter_q;
  logic [TXN_ID_WIDTH-1:0] cpu_txn_q;
  grant_opcode_t grant_opcode_q;
  logic [31:0] cpu_addr_q;
  logic [31:0] resp_addr_q;
  logic resp_write_q;
  logic cpu_protocol_error_q;
  request_opcode_t req_opcode_q;
  mesi_state_t cpu_meta_state_q;
  logic [2:0] refill_expected_beat_q;
  logic cpu_resp_pending_q;
  logic grant_commit_pending_q;
  logic cpu_meta_pending_q;

  always_comb begin
    monitor_cpu_state = cpu_state_q;
    monitor_cpu_active_addr = cpu_addr_q;
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

    cpu_meta_write_valid = (cpu_state_q == CPU_META_WRITE) &&
                           cpu_meta_pending_q;
    cpu_meta_write_line_addr = line_align(cpu_addr_q);
    cpu_meta_write_state = cpu_meta_state_q;
    protocol_error = cpu_protocol_error_q;
  end

  always_ff @(posedge clock) begin
    if (reset) begin
      cpu_state_q <= CPU_IDLE;
      txn_counter_q <= '0;
      cpu_txn_q <= '0;
      grant_opcode_q <= GRANT_DATA_S;
      cpu_addr_q <= '0;
      resp_addr_q <= '0;
      resp_write_q <= 1'b0;
      req_opcode_q <= REQ_GETS;
      cpu_meta_state_q <= MESI_I;
      refill_expected_beat_q <= '0;
      cpu_resp_pending_q <= 1'b0;
      grant_commit_pending_q <= 1'b0;
      cpu_meta_pending_q <= 1'b0;
      cpu_protocol_error_q <= 1'b0;
    end else begin
      case (cpu_state_q)
        CPU_IDLE: begin
          cpu_resp_pending_q <= 1'b0;
          cpu_meta_pending_q <= 1'b0;
          if (cpu_req_valid && cpu_req_ready) begin
            cpu_addr_q <= cpu_req_addr;
            resp_addr_q <= cpu_req_addr;
            resp_write_q <= cpu_req_write;
            if (EXTERNAL_TXN_ID) begin
              cpu_txn_q <= cpu_req_txn_id;
            end else begin
              cpu_txn_q <= txn_counter_q;
              txn_counter_q <= txn_counter_q + 1'b1;
            end

            if (cpu_req_hit && (cpu_req_line_state == MESI_I)) begin
              cpu_protocol_error_q <= 1'b1;
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
              cpu_protocol_error_q <= 1'b1;
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
              cpu_protocol_error_q <= 1'b1;

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
          cpu_protocol_error_q <= 1'b1;
        end
      endcase
    end
  end
endmodule
