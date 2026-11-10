module CoherenceDirectoryFormal(
  input logic clock,
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

  always_comb reset = (init_reset_count < 2) || reset_after_init;

  // No protocol-input assumptions: malformed opcode, metadata, IDs and
  // response timing remain unconstrained. Only the initial reset is modeled.


  DirectoryController dut (.*);

  // Reachability claim is limited to FSM encodings. Full protocol safety
  // remains in the existing bounded harness and the directed fault tests.
  always @(posedge clock) begin
    past_valid <= 1'b1;
    if (init_reset_count < 2) init_reset_count <= init_reset_count + 1'b1;
    if (past_valid && init_reset_count >= 2) begin
      assert (dut.state_q <= 4'd9);
      assert (dut.snoop_resume_q <= 4'd9);
    end
  end
`ifdef TRANSACTION_PROPERTIES
  DirectoryTransactionProperties transaction_properties (
    .clock, .reset,
    .req_fire(req_valid && req_ready),
    .write_fire(dir_write_valid && dir_write_ready),
    .grant_fire(grant_valid && grant_ready),
    .commit_fire(grant_commit_valid && grant_commit_ready),
    .state(dut.state_q), .write_valid(dir_write_valid),
    .write_state(dir_write_state), .write_sharers(dir_write_sharers),
    .write_owner(dir_write_owner_id), .req_ready,
    .snoop_valid(snoop_req_valid), .xfer_valid(line_xfer_start_valid),
    .grant_valid, .snoop_ready(snoop_rsp_ready),
    .xfer_done_ready(line_xfer_done_ready), .commit_ready(grant_commit_ready),
    .error(protocol_error)
  );
`endif
endmodule
