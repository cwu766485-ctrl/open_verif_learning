  initial begin : test
    integer beat;
    integer txn;
    line_rd_req_valid = 1'b0;
    line_rd_req_addr = '0;
    line_rd_req_id = '0;
    line_rd_data_ready = 1'b0;
    line_wr_req_valid = 1'b0;
    line_wr_req_addr = '0;
    line_wr_req_id = '0;
    line_wr_data_valid = 1'b0;
    line_wr_data_id = '0;
    line_wr_data_beat = '0;
    line_wr_data = '0;
    line_wr_data_last = 1'b0;
    line_wr_rsp_ready = 1'b0;
    axi_arready = 1'b0;
    axi_rid = '0;
    axi_rdata = '0;
    axi_rresp = 2'b00;
    axi_rlast = 1'b0;
    axi_rvalid = 1'b0;
    axi_awready = 1'b0;
    axi_wready = 1'b0;
    axi_bid = '0;
    axi_bresp = 2'b00;
    axi_bvalid = 1'b0;
    hit_event = '0;
    miss_event = '0;
    snoop_event = '0;
    dirty_writeback_event = 1'b0;
    cache_inflight = '0;
    access_complete_event = '0;
    error_status = '0;
    apb_psel = 1'b0;
    apb_penable = 1'b0;
    apb_pwrite = 1'b0;
    apb_paddr = '0;

    repeat (3) tick();
    @(negedge clock);
    reset = 1'b0;

`include "include/axi_read_cases.svh"

`include "include/axi_write_cases.svh"

`include "include/outstanding_id_cases.svh"

`include "include/apb_csr_cases.svh"

`include "include/invalid_response_cases.svh"
