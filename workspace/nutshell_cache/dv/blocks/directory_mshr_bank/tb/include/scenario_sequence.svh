  initial begin : mshr_stress
    integer cycles;
    logic [31:0] snoop_addr_saved;
    logic [TXN_ID_WIDTH-1:0] snoop_txn_saved;
    logic snoop_target_saved;

    reset = 1'b1;
    req_valid = 1'b0;
    req_src_id = 1'b0;
    req_opcode = REQ_GETS;
    req_line_addr = '0;
    req_txn_id = '0;
    lookup_dir_state = DIR_I;
    lookup_sharers = 2'b00;
    lookup_owner_id = 1'b0;
    dir_write_ready = 1'b0;
    snoop_req_ready = 1'b0;
    snoop_rsp_valid = 1'b0;
    snoop_rsp_src_id = 1'b0;
    snoop_rsp_opcode = SNOOP_RSP_DATA;
    snoop_rsp_txn_id = '0;
    line_xfer_start_ready = 1'b0;
    line_xfer_done_valid = 1'b0;
    line_xfer_done_context_id = '0;
    grant_ready = 1'b0;
    grant_commit_valid = 1'b0;
    grant_commit_src_id = 1'b0;
    grant_commit_txn_id = '0;
    for (integer i = 0; i < NUM_MSHRS; i++) begin
      ctx_addr[i] = 32'h0000_4000 + (i * 64);
      ctx_txn[i] = TXN_ID_WIDTH'(i + 1);
      ctx_src[i] = i[0];
      ctx_seen[i] = 1'b0;
      ctx_written[i] = 1'b0;
    end
    repeat (3) @(posedge clock);
    @(negedge clock);
    reset = 1'b0;

`include "include/context_allocation_and_routing.svh"

`include "include/same_line_put_serialization.svh"

`include "include/snoop_independence.svh"

`include "include/reset_cancellation.svh"
