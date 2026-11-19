module MesiL1Controller #(
  parameter int TXN_ID_WIDTH = coherence_protocol_pkg::TXN_ID_WIDTH
) (
  input  logic clock,
  input  logic reset,

  // One shared CPU miss context and one independent shared Snoop engine.
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

  output logic cpu_meta_write_valid,
  input  logic cpu_meta_write_ready,
  output logic [31:0] cpu_meta_write_line_addr,
  output coherence_protocol_pkg::mesi_state_t cpu_meta_write_state,
  output logic snoop_meta_write_valid,
  input  logic snoop_meta_write_ready,
  output logic [31:0] snoop_meta_write_line_addr,
  output coherence_protocol_pkg::mesi_state_t snoop_meta_write_state,

  output logic protocol_error,
  output logic [2:0] monitor_cpu_state,
  output logic [2:0] monitor_snoop_state,
  output logic [31:0] monitor_cpu_active_addr
);
  import coherence_protocol_pkg::*;

  localparam logic [2:0] CPU_IDLE_STATE       = 3'd0;
  localparam logic [2:0] CPU_REFILL_STATE     = 3'd3;
  localparam logic [2:0] CPU_META_WRITE_STATE = 3'd4;
  localparam logic [2:0] CPU_RESP_STATE       = 3'd5;

  logic req_snoop_cpu_ready;
  logic req_snoop_snoop_ready;
  logic cpu_snoop_lock;
  logic snoop_accept;
  logic snoop_idle;
  logic [31:0] snoop_active_addr;
  logic cpu_protocol_error;
  logic snoop_protocol_error;

  MesiL1MissContext #(.TXN_ID_WIDTH(TXN_ID_WIDTH)) cpu_context (
    .clock, .reset,
    .cpu_req_valid, .cpu_req_ready(req_snoop_cpu_ready),
    .cpu_req_addr, .cpu_req_write, .cpu_req_hit, .cpu_req_line_state,
    .cpu_req_txn_id('0),
    .cpu_resp_valid, .cpu_resp_ready, .cpu_resp_addr, .cpu_resp_write,
    .cpu_resp_txn_id,
    .dir_req_valid, .dir_req_ready, .dir_req_opcode, .dir_req_line_addr,
    .dir_req_txn_id, .grant_valid, .grant_ready, .grant_opcode, .grant_txn_id,
    .grant_data_valid, .grant_data_ready, .grant_data_txn_id,
    .grant_data_beat_idx, .grant_data, .grant_data_last,
    .refill_valid, .refill_ready, .refill_txn_id, .refill_beat_idx,
    .refill_data, .refill_last,
    .grant_commit_valid, .grant_commit_ready, .grant_commit_txn_id,
    .cpu_meta_write_valid, .cpu_meta_write_ready, .cpu_meta_write_line_addr,
    .cpu_meta_write_state,
    .protocol_error(cpu_protocol_error), .monitor_cpu_state,
    .monitor_cpu_active_addr
  );

  assign cpu_req_ready = req_snoop_cpu_ready;
  assign snoop_ready = req_snoop_snoop_ready;
  assign cpu_snoop_lock = (monitor_cpu_state == CPU_REFILL_STATE) ||
                          (monitor_cpu_state == CPU_META_WRITE_STATE) ||
                          (monitor_cpu_state == CPU_RESP_STATE);
  assign snoop_accept = snoop_valid && req_snoop_snoop_ready;
  assign protocol_error = cpu_protocol_error || snoop_protocol_error;

  MesiL1SnoopArbiter req_snoop_arbiter (
    .cpu_idle(monitor_cpu_state == CPU_IDLE_STATE),
    .cpu_snoop_lock,
    .cpu_req_addr, .cpu_req_valid,
    .cpu_active_addr(monitor_cpu_active_addr),
    .snoop_idle,
    .snoop_req_addr(snoop_line_addr), .snoop_valid,
    .snoop_active_addr,
    .cpu_req_ready(req_snoop_cpu_ready),
    .snoop_ready(req_snoop_snoop_ready)
  );

  MesiL1SnoopEngine #(.TXN_ID_WIDTH(TXN_ID_WIDTH)) snoop_engine (
    .clock, .reset, .snoop_accept, .snoop_line_addr, .snoop_opcode,
    .snoop_txn_id, .snoop_tag_hit, .snoop_line_state,
    .snoop_idle, .snoop_active_addr,
    .snoop_rsp_valid, .snoop_rsp_ready, .snoop_rsp_opcode,
    .snoop_rsp_txn_id, .snoop_rsp_has_data,
    .snoop_line_rd_valid, .snoop_line_rd_ready, .snoop_line_rd_addr,
    .snoop_line_rd_hit, .snoop_array_data_valid, .snoop_array_data_ready,
    .snoop_array_beat_idx, .snoop_array_data, .snoop_array_last,
    .snoop_data_valid, .snoop_data_ready, .snoop_data_txn_id,
    .snoop_data_beat_idx, .snoop_data, .snoop_data_last,
    .snoop_meta_write_valid, .snoop_meta_write_ready,
    .snoop_meta_write_line_addr, .snoop_meta_write_state,
    .protocol_error(snoop_protocol_error), .monitor_snoop_state
  );
endmodule
