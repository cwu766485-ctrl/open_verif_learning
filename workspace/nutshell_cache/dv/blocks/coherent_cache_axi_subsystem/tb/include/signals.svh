  localparam int TXN_ID_WIDTH = coherence_protocol_pkg::TXN_ID_WIDTH;
  localparam int MODEL_SLOTS = 4;
  localparam int MEMORY_LINES = 64;

  logic clock = 1'b0;
  logic reset = 1'b1;

  logic cpu_req_valid [0:1];
  logic cpu_req_ready [0:1];
  logic [31:0] cpu_req_addr [0:1];
  logic cpu_req_write [0:1];
  logic [7:0] cpu_req_wmask [0:1];
  logic [63:0] cpu_req_wdata [0:1];
  logic cpu_resp_valid [0:1];
  logic cpu_resp_ready [0:1];
  logic [31:0] cpu_resp_addr [0:1];
  logic cpu_resp_write [0:1];
  logic [63:0] cpu_resp_rdata [0:1];
  logic [TXN_ID_WIDTH-1:0] cpu_resp_txn_id [0:1];

  logic mmio_req_valid, mmio_req_ready;
  logic [31:0] mmio_req_addr;
  logic [2:0] mmio_req_size;
  logic mmio_req_write;
  logic [7:0] mmio_req_wmask;
  logic [63:0] mmio_req_wdata;
  logic mmio_resp_valid, mmio_resp_ready;
  logic [63:0] mmio_resp_rdata;

  logic apb_psel, apb_penable, apb_pwrite;
  logic [31:0] apb_paddr;
  logic apb_pready;
  logic [31:0] apb_prdata;
  logic apb_pslverr;

  logic [TXN_ID_WIDTH-1:0] axi_arid;
  logic [31:0] axi_araddr;
  logic [7:0] axi_arlen;
  logic [2:0] axi_arsize;
  logic [1:0] axi_arburst;
  logic axi_arlock;
  logic [3:0] axi_arcache;
  logic [2:0] axi_arprot;
  logic axi_arvalid, axi_arready;
  logic [TXN_ID_WIDTH-1:0] axi_rid;
  logic [63:0] axi_rdata;
  logic [1:0] axi_rresp;
  logic axi_rlast, axi_rvalid, axi_rready;

  logic [TXN_ID_WIDTH-1:0] axi_awid;
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
  logic [TXN_ID_WIDTH-1:0] axi_bid;
  logic [1:0] axi_bresp;
  logic axi_bvalid, axi_bready;

  logic [1:0] l1_controller_protocol_error;
  logic [1:0] l1_array_protocol_error;
  logic directory_protocol_error, l2_protocol_error;
  logic memory_adapter_protocol_error, memory_adapter_error;
  logic axi_adapter_protocol_error, mmio_protocol_error, fatal_error;

  CoherentCacheAxiSubsystem dut (.*);

  always #5 clock = ~clock;
