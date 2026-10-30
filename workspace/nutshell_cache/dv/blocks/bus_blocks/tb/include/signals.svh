  logic clock;
  logic reset = 1'b1;
  initial begin
    clock = 1'b0;
    forever #5 clock = ~clock;
  end

  logic line_rd_req_valid, line_rd_req_ready;
  logic [31:0] line_rd_req_addr;
  logic [3:0] line_rd_req_id;
  logic line_rd_data_valid, line_rd_data_ready;
  logic [3:0] line_rd_data_id;
  logic [2:0] line_rd_data_beat;
  logic [63:0] line_rd_data;
  logic line_rd_data_last, line_rd_data_error;
  logic line_wr_req_valid, line_wr_req_ready;
  logic [31:0] line_wr_req_addr;
  logic [3:0] line_wr_req_id;
  logic line_wr_data_valid, line_wr_data_ready;
  logic [3:0] line_wr_data_id;
  logic [2:0] line_wr_data_beat;
  logic [63:0] line_wr_data;
  logic line_wr_data_last;
  logic line_wr_rsp_valid, line_wr_rsp_ready;
  logic [3:0] line_wr_rsp_id;
  logic line_wr_rsp_error, adapter_protocol_error;

  logic [3:0] axi_arid;
  logic [31:0] axi_araddr;
  logic [7:0] axi_arlen;
  logic [2:0] axi_arsize;
  logic [1:0] axi_arburst;
  logic axi_arlock;
  logic [3:0] axi_arcache;
  logic [2:0] axi_arprot;
  logic axi_arvalid, axi_arready;
  logic [3:0] axi_rid;
  logic [63:0] axi_rdata;
  logic [1:0] axi_rresp;
  logic axi_rlast, axi_rvalid, axi_rready;
  logic [3:0] axi_awid;
  logic [31:0] axi_awaddr;
  logic [7:0] axi_awlen;
  logic [2:0] axi_awsize;
  logic [1:0] axi_awburst;
  logic axi_awlock;
  logic [3:0] axi_awcache;
  logic [2:0] axi_awprot;
  logic axi_awvalid, axi_awready;
  logic [63:0] axi_wdata;
  logic [7:0] axi_wstrb;
  logic axi_wlast, axi_wvalid, axi_wready;
  logic [3:0] axi_bid;
  logic [1:0] axi_bresp;
  logic axi_bvalid, axi_bready;

  logic [1:0] hit_event, miss_event, snoop_event;
  logic dirty_writeback_event;
  logic [1:0] cache_inflight, access_complete_event;
  logic [4:0] error_status;
  logic apb_psel, apb_penable, apb_pwrite;
  logic [31:0] apb_paddr, apb_prdata;
  logic apb_pready, apb_pslverr;

  LineMemoryAxi4Adapter #(.ID_WIDTH(4)) adapter (.*,
    .protocol_error(adapter_protocol_error));
  CachePerformanceCsr csr (.*,
    .apb_psel(apb_psel), .apb_penable(apb_penable),
    .apb_pwrite(apb_pwrite), .apb_paddr(apb_paddr),
    .apb_pready(apb_pready), .apb_prdata(apb_prdata),
    .apb_pslverr(apb_pslverr));
