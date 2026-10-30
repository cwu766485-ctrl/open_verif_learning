  import coherence_protocol_pkg::*;

  localparam int NUM_MSHRS = 4;
  localparam int CTX_W = 2;

  logic clock = 1'b0;
  logic reset;
  logic req_valid, req_ready, req_src_id;
  request_opcode_t req_opcode;
  logic [31:0] req_line_addr;
  logic [TXN_ID_WIDTH-1:0] req_txn_id;
  directory_state_t lookup_dir_state;
  logic [1:0] lookup_sharers;
  logic lookup_owner_id;
  logic dir_write_valid, dir_write_ready;
  logic [31:0] dir_write_line_addr;
  directory_state_t dir_write_state;
  logic [1:0] dir_write_sharers;
  logic dir_write_owner_id;
  logic snoop_req_valid, snoop_req_ready, snoop_target_id;
  snoop_opcode_t snoop_req_opcode;
  logic [31:0] snoop_req_line_addr;
  logic [TXN_ID_WIDTH-1:0] snoop_req_txn_id;
  logic snoop_rsp_valid, snoop_rsp_ready, snoop_rsp_src_id;
  snoop_response_t snoop_rsp_opcode;
  logic [TXN_ID_WIDTH-1:0] snoop_rsp_txn_id;
  logic line_xfer_start_valid, line_xfer_start_ready;
  line_xfer_kind_t line_xfer_kind;
  logic [31:0] line_xfer_addr;
  logic line_xfer_src_id;
  logic [TXN_ID_WIDTH-1:0] line_xfer_txn_id;
  logic [CTX_W-1:0] line_xfer_context_id;
  logic line_xfer_done_valid, line_xfer_done_ready;
  logic [CTX_W-1:0] line_xfer_done_context_id;
  logic grant_valid, grant_ready, grant_dst_id, grant_has_data;
  grant_opcode_t grant_opcode;
  logic [31:0] grant_line_addr;
  logic [TXN_ID_WIDTH-1:0] grant_txn_id;
  logic grant_commit_valid, grant_commit_src_id, grant_commit_ready;
  logic [TXN_ID_WIDTH-1:0] grant_commit_txn_id;
  logic snoop_data_to_l2, protocol_error;
  logic [3:0] protocol_error_code;
  logic [NUM_MSHRS-1:0] monitor_active_contexts;

  logic [31:0] ctx_addr [0:NUM_MSHRS-1];
  logic [TXN_ID_WIDTH-1:0] ctx_txn [0:NUM_MSHRS-1];
  logic ctx_src [0:NUM_MSHRS-1];
  logic ctx_seen [0:NUM_MSHRS-1];
  logic ctx_written [0:NUM_MSHRS-1];

  always #5 clock = ~clock;

  DirectoryMshrBank #(
    .TXN_ID_WIDTH(TXN_ID_WIDTH), .NUM_MSHRS(NUM_MSHRS), .MSHR_ID_WIDTH(CTX_W)
  ) dut (
    .clock(clock), .reset(reset),
    .req_valid(req_valid), .req_ready(req_ready), .req_src_id(req_src_id),
    .req_opcode(req_opcode), .req_line_addr(req_line_addr), .req_txn_id(req_txn_id),
    .lookup_dir_state(lookup_dir_state), .lookup_sharers(lookup_sharers),
    .lookup_owner_id(lookup_owner_id),
    .dir_write_valid(dir_write_valid), .dir_write_ready(dir_write_ready),
    .dir_write_line_addr(dir_write_line_addr), .dir_write_state(dir_write_state),
    .dir_write_sharers(dir_write_sharers), .dir_write_owner_id(dir_write_owner_id),
    .snoop_req_valid(snoop_req_valid), .snoop_req_ready(snoop_req_ready),
    .snoop_target_id(snoop_target_id), .snoop_req_opcode(snoop_req_opcode),
    .snoop_req_line_addr(snoop_req_line_addr), .snoop_req_txn_id(snoop_req_txn_id),
    .snoop_rsp_valid(snoop_rsp_valid), .snoop_rsp_ready(snoop_rsp_ready),
    .snoop_rsp_src_id(snoop_rsp_src_id), .snoop_rsp_opcode(snoop_rsp_opcode),
    .snoop_rsp_txn_id(snoop_rsp_txn_id),
    .line_xfer_start_valid(line_xfer_start_valid),
    .line_xfer_start_ready(line_xfer_start_ready), .line_xfer_kind(line_xfer_kind),
    .line_xfer_addr(line_xfer_addr), .line_xfer_src_id(line_xfer_src_id),
    .line_xfer_txn_id(line_xfer_txn_id), .line_xfer_context_id(line_xfer_context_id),
    .line_xfer_done_valid(line_xfer_done_valid),
    .line_xfer_done_ready(line_xfer_done_ready),
    .line_xfer_done_context_id(line_xfer_done_context_id),
    .grant_valid(grant_valid), .grant_ready(grant_ready), .grant_dst_id(grant_dst_id),
    .grant_opcode(grant_opcode), .grant_has_data(grant_has_data),
    .grant_line_addr(grant_line_addr), .grant_txn_id(grant_txn_id),
    .grant_commit_valid(grant_commit_valid),
    .grant_commit_src_id(grant_commit_src_id),
    .grant_commit_ready(grant_commit_ready), .grant_commit_txn_id(grant_commit_txn_id),
    .snoop_data_to_l2(snoop_data_to_l2),
    .monitor_active_contexts(monitor_active_contexts),
    .protocol_error(protocol_error),
    .protocol_error_code(protocol_error_code)
  );
