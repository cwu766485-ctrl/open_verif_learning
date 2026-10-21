// Two P1 MESI controllers wired to their 32 KiB L1 arrays, plus the shared
// request arbiter. The Directory/L2 line engine connects through the exposed
// request, snoop, grant, and eight-beat data channels.
module DualL1MesiCluster #(
  parameter int TXN_ID_WIDTH = coherence_protocol_pkg::TXN_ID_WIDTH
) (
  input logic clock,
  input logic reset,

  input  logic cpu_req_valid [0:1],
  output logic cpu_req_ready [0:1],
  input  logic [31:0] cpu_req_addr [0:1],
  input  logic cpu_req_write [0:1],
  input  logic [7:0] cpu_req_wmask [0:1],
  input  logic [63:0] cpu_req_wdata [0:1],
  output logic cpu_resp_valid [0:1],
  input  logic cpu_resp_ready [0:1],
  output logic [31:0] cpu_resp_addr [0:1],
  output logic cpu_resp_write [0:1],
  output logic [63:0] cpu_resp_rdata [0:1],
  output logic [TXN_ID_WIDTH-1:0] cpu_resp_txn_id [0:1],

  output logic [1:0] dir_req_ready,
  output logic dir_req_valid,
  input  logic dir_req_ready_from_directory,
  output logic dir_req_src_id,
  output coherence_protocol_pkg::request_opcode_t dir_req_opcode,
  output logic [31:0] dir_req_line_addr,
  output logic [TXN_ID_WIDTH-1:0] dir_req_txn_id,

  input  logic grant_valid [0:1],
  output logic grant_ready [0:1],
  input  coherence_protocol_pkg::grant_opcode_t grant_opcode [0:1],
  input  logic [TXN_ID_WIDTH-1:0] grant_txn_id [0:1],
  input  logic grant_data_valid [0:1],
  output logic grant_data_ready [0:1],
  input  logic [TXN_ID_WIDTH-1:0] grant_data_txn_id [0:1],
  input  logic [2:0] grant_data_beat_idx [0:1],
  input  logic [63:0] grant_data [0:1],
  input  logic grant_data_last [0:1],
  output logic grant_commit_valid [0:1],
  input  logic grant_commit_ready [0:1],
  output logic [TXN_ID_WIDTH-1:0] grant_commit_txn_id [0:1],

  input  logic snoop_valid [0:1],
  output logic snoop_ready [0:1],
  input  logic [31:0] snoop_line_addr [0:1],
  input  coherence_protocol_pkg::snoop_opcode_t snoop_opcode [0:1],
  input  logic [TXN_ID_WIDTH-1:0] snoop_txn_id [0:1],
  output logic snoop_rsp_valid [0:1],
  input  logic snoop_rsp_ready [0:1],
  output coherence_protocol_pkg::snoop_response_t snoop_rsp_opcode [0:1],
  output logic [TXN_ID_WIDTH-1:0] snoop_rsp_txn_id [0:1],
  output logic snoop_rsp_has_data [0:1],
  output logic snoop_data_valid [0:1],
  input  logic snoop_data_ready [0:1],
  output logic [TXN_ID_WIDTH-1:0] snoop_data_txn_id [0:1],
  output logic [2:0] snoop_data_beat_idx [0:1],
  output logic [63:0] snoop_data [0:1],
  output logic snoop_data_last [0:1],

  output logic replace_valid [0:1],
  output logic [1:0] replace_way [0:1],
  output coherence_protocol_pkg::mesi_state_t replace_state [0:1],
  output logic [31:0] replace_line_addr [0:1],
  output logic [1:0] controller_protocol_error,
  output logic [1:0] array_protocol_error
);
  import coherence_protocol_pkg::*;

  request_opcode_t controller_req_opcode [0:1];
  logic [31:0] controller_req_addr [0:1];
  logic [TXN_ID_WIDTH-1:0] controller_req_txn_id [0:1];
  logic [1:0] controller_req_valid;
  logic [1:0] controller_req_ready;

  for (genvar core = 0; core < 2; core = core + 1) begin : cores
    logic [31:0] lookup_addr;
    logic ctrl_cpu_req_valid;
    logic ctrl_cpu_req_ready;
    logic request_can_allocate;
    logic lookup_hit;
    logic [1:0] lookup_way;
    mesi_state_t lookup_state;
    logic [63:0] lookup_word;
    logic snoop_lookup_hit;
    mesi_state_t snoop_lookup_state;
    logic [1:0] allocation_way_q;
    logic [7:0] store_wmask_q;
    logic [63:0] store_wdata_q;

    logic ctrl_resp_valid;
    logic ctrl_resp_ready;
    logic [31:0] ctrl_resp_addr;
    logic ctrl_resp_write;
    logic [TXN_ID_WIDTH-1:0] ctrl_resp_txn_id;
    logic refill_valid;
    logic [2:0] refill_beat_idx;
    logic [63:0] refill_data;
    logic refill_last;
    logic cpu_meta_write_valid;
    logic cpu_meta_write_ready;
    logic [31:0] cpu_meta_write_line_addr;
    mesi_state_t cpu_meta_write_state;
    logic snoop_meta_write_valid;
    logic snoop_meta_write_ready;
    logic [31:0] snoop_meta_write_line_addr;
    mesi_state_t snoop_meta_write_state;
    logic snoop_line_rd_valid;
    logic snoop_line_rd_ready;
    logic [31:0] snoop_line_rd_addr;
    logic array_line_data_valid;
    logic array_line_data_ready;
    logic [2:0] array_line_data_beat_idx;
    logic [63:0] array_line_data;
    logic array_line_data_last;
    logic array_refill_ready;
    logic array_store_ready;

    assign lookup_addr = ctrl_resp_valid ? ctrl_resp_addr : cpu_req_addr[core];
    assign request_can_allocate = lookup_hit || !replace_valid[core];
    assign ctrl_cpu_req_valid = cpu_req_valid[core] && request_can_allocate;
    assign cpu_req_ready[core] = ctrl_cpu_req_ready && request_can_allocate;
    assign cpu_resp_valid[core] = ctrl_resp_valid &&
      (!ctrl_resp_write || array_store_ready);
    assign cpu_resp_addr[core] = ctrl_resp_addr;
    assign cpu_resp_write[core] = ctrl_resp_write;
    assign cpu_resp_txn_id[core] = ctrl_resp_txn_id;
    assign cpu_resp_rdata[core] = lookup_word;
    assign ctrl_resp_ready = cpu_resp_ready[core] && cpu_resp_valid[core];

    always_ff @(posedge clock) begin
      if (reset) begin
        allocation_way_q <= '0;
        store_wmask_q <= '0;
        store_wdata_q <= '0;
      end else if (cpu_req_valid[core] && cpu_req_ready[core]) begin
        allocation_way_q <= replace_way[core];
        store_wmask_q <= cpu_req_wmask[core];
        store_wdata_q <= cpu_req_wdata[core];
      end
    end

    MesiL1Controller #(.TXN_ID_WIDTH(TXN_ID_WIDTH)) l1_controller (
      .clock(clock), .reset(reset),
      .cpu_req_valid(ctrl_cpu_req_valid), .cpu_req_ready(ctrl_cpu_req_ready),
      .cpu_req_addr(cpu_req_addr[core]), .cpu_req_write(cpu_req_write[core]),
      .cpu_req_hit(lookup_hit), .cpu_req_line_state(lookup_state),
      .cpu_resp_valid(ctrl_resp_valid), .cpu_resp_ready(ctrl_resp_ready),
      .cpu_resp_addr(ctrl_resp_addr), .cpu_resp_write(ctrl_resp_write),
      .cpu_resp_txn_id(ctrl_resp_txn_id),
      .dir_req_valid(controller_req_valid[core]),
      .dir_req_ready(controller_req_ready[core]),
      .dir_req_opcode(controller_req_opcode[core]),
      .dir_req_line_addr(controller_req_addr[core]),
      .dir_req_txn_id(controller_req_txn_id[core]),
      .grant_valid(grant_valid[core]), .grant_ready(grant_ready[core]),
      .grant_opcode(grant_opcode[core]), .grant_txn_id(grant_txn_id[core]),
      .grant_data_valid(grant_data_valid[core]),
      .grant_data_ready(grant_data_ready[core]),
      .grant_data_txn_id(grant_data_txn_id[core]),
      .grant_data_beat_idx(grant_data_beat_idx[core]),
      .grant_data(grant_data[core]), .grant_data_last(grant_data_last[core]),
      .refill_valid(refill_valid), .refill_ready(array_refill_ready),
      .refill_txn_id(), .refill_beat_idx(refill_beat_idx),
      .refill_data(refill_data), .refill_last(refill_last),
      .grant_commit_valid(grant_commit_valid[core]),
      .grant_commit_ready(grant_commit_ready[core]),
      .grant_commit_txn_id(grant_commit_txn_id[core]),
      .snoop_valid(snoop_valid[core]), .snoop_ready(snoop_ready[core]),
      .snoop_line_addr(snoop_line_addr[core]),
      .snoop_opcode(snoop_opcode[core]), .snoop_txn_id(snoop_txn_id[core]),
      .snoop_tag_hit(snoop_lookup_hit), .snoop_line_state(snoop_lookup_state),
      .snoop_rsp_valid(snoop_rsp_valid[core]),
      .snoop_rsp_ready(snoop_rsp_ready[core]),
      .snoop_rsp_opcode(snoop_rsp_opcode[core]),
      .snoop_rsp_txn_id(snoop_rsp_txn_id[core]),
      .snoop_rsp_has_data(snoop_rsp_has_data[core]),
      .snoop_line_rd_valid(snoop_line_rd_valid),
      .snoop_line_rd_ready(snoop_line_rd_ready),
      .snoop_line_rd_addr(snoop_line_rd_addr),
      .snoop_array_data_valid(array_line_data_valid),
      .snoop_array_data_ready(array_line_data_ready),
      .snoop_array_beat_idx(array_line_data_beat_idx),
      .snoop_array_data(array_line_data), .snoop_array_last(array_line_data_last),
      .snoop_data_valid(snoop_data_valid[core]),
      .snoop_data_ready(snoop_data_ready[core]),
      .snoop_data_txn_id(snoop_data_txn_id[core]),
      .snoop_data_beat_idx(snoop_data_beat_idx[core]),
      .snoop_data(snoop_data[core]), .snoop_data_last(snoop_data_last[core]),
      .cpu_meta_write_valid(cpu_meta_write_valid),
      .cpu_meta_write_ready(cpu_meta_write_ready),
      .cpu_meta_write_line_addr(cpu_meta_write_line_addr),
      .cpu_meta_write_state(cpu_meta_write_state),
      .snoop_meta_write_valid(snoop_meta_write_valid),
      .snoop_meta_write_ready(snoop_meta_write_ready),
      .snoop_meta_write_line_addr(snoop_meta_write_line_addr),
      .snoop_meta_write_state(snoop_meta_write_state),
      .protocol_error(controller_protocol_error[core])
    );

    MesiL1Array #(.SETS(128), .WAYS(4), .TAG_WIDTH(19)) l1_array (
      .clock(clock), .reset(reset),
      .cpu_lookup_addr(lookup_addr), .cpu_lookup_hit(lookup_hit),
      .cpu_lookup_way(lookup_way), .cpu_lookup_state(lookup_state),
      .cpu_lookup_word(lookup_word),
      .snoop_lookup_addr(snoop_line_addr[core]),
      .snoop_lookup_hit(snoop_lookup_hit),
      .snoop_lookup_way(),
      .snoop_lookup_state(snoop_lookup_state),
      .replace_valid(replace_valid[core]), .replace_way(replace_way[core]),
      .replace_state(replace_state[core]),
      .replace_line_addr(replace_line_addr[core]),
      .cpu_meta_write_valid(cpu_meta_write_valid),
      .cpu_meta_write_ready(cpu_meta_write_ready),
      .cpu_meta_write_line_addr(cpu_meta_write_line_addr),
      .cpu_meta_write_state(cpu_meta_write_state),
      .snoop_meta_write_valid(snoop_meta_write_valid),
      .snoop_meta_write_ready(snoop_meta_write_ready),
      .snoop_meta_write_line_addr(snoop_meta_write_line_addr),
      .snoop_meta_write_state(snoop_meta_write_state),
      .refill_valid(refill_valid), .refill_ready(array_refill_ready),
      .refill_line_addr(ctrl_resp_addr), .refill_way(allocation_way_q),
      .refill_beat_idx(refill_beat_idx), .refill_data(refill_data),
      .refill_last(refill_last),
      .cpu_store_valid(cpu_resp_valid[core] && ctrl_resp_write &&
                       cpu_resp_ready[core]),
      .cpu_store_ready(array_store_ready), .cpu_store_addr(ctrl_resp_addr),
      .cpu_store_way(lookup_way), .cpu_store_wmask(store_wmask_q),
      .cpu_store_wdata(store_wdata_q),
      .line_rd_valid(snoop_line_rd_valid),
      .line_rd_ready(snoop_line_rd_ready), .line_rd_addr(snoop_line_rd_addr),
      .line_rd_hit(), .line_data_valid(array_line_data_valid),
      .line_data_ready(array_line_data_ready),
      .line_data_beat_idx(array_line_data_beat_idx),
      .line_data(array_line_data), .line_data_last(array_line_data_last),
      .protocol_error(array_protocol_error[core])
    );
  end

  CoherenceRequestArbiter #(.TXN_ID_WIDTH(TXN_ID_WIDTH)) request_arbiter (
    .clock(clock), .reset(reset),
    .in_valid(controller_req_valid), .in_ready(controller_req_ready),
    .in_opcode(controller_req_opcode), .in_line_addr(controller_req_addr),
    .in_txn_id(controller_req_txn_id), .out_valid(dir_req_valid),
    .out_ready(dir_req_ready_from_directory), .out_src_id(dir_req_src_id),
    .out_opcode(dir_req_opcode), .out_line_addr(dir_req_line_addr),
    .out_txn_id(dir_req_txn_id)
  );

  assign dir_req_ready = controller_req_ready;
endmodule
