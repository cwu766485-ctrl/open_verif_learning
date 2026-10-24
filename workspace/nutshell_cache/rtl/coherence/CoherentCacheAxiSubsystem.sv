// System integration variant: retains the custom MESI/Directory/shared-L2
// subsystem, exposes its performance counters through APB3, and connects its
// line-memory ports to an AXI4 64-bit master adapter.
module CoherentCacheAxiSubsystem #(
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

  output logic mmio_req_valid,
  input  logic mmio_req_ready,
  output logic [31:0] mmio_req_addr,
  output logic [2:0] mmio_req_size,
  output logic mmio_req_write,
  output logic [7:0] mmio_req_wmask,
  output logic [63:0] mmio_req_wdata,
  input  logic mmio_resp_valid,
  output logic mmio_resp_ready,
  input  logic [63:0] mmio_resp_rdata,

  // APB3, read-only CSR window. Register offsets are relative to this block.
  input  logic apb_psel,
  input  logic apb_penable,
  input  logic apb_pwrite,
  input  logic [31:0] apb_paddr,
  output logic apb_pready,
  output logic [31:0] apb_prdata,
  output logic apb_pslverr,

  output logic [TXN_ID_WIDTH-1:0] axi_arid,
  output logic [31:0] axi_araddr,
  output logic [7:0] axi_arlen,
  output logic [2:0] axi_arsize,
  output logic [1:0] axi_arburst,
  output logic axi_arlock,
  output logic [3:0] axi_arcache,
  output logic [2:0] axi_arprot,
  output logic axi_arvalid,
  input  logic axi_arready,
  input  logic [TXN_ID_WIDTH-1:0] axi_rid,
  input  logic [63:0] axi_rdata,
  input  logic [1:0] axi_rresp,
  input  logic axi_rlast,
  input  logic axi_rvalid,
  output logic axi_rready,

  output logic [TXN_ID_WIDTH-1:0] axi_awid,
  output logic [31:0] axi_awaddr,
  output logic [7:0] axi_awlen,
  output logic [2:0] axi_awsize,
  output logic [1:0] axi_awburst,
  output logic axi_awlock,
  output logic [3:0] axi_awcache,
  output logic [2:0] axi_awprot,
  output logic axi_awvalid,
  input  logic axi_awready,
  output logic [63:0] axi_wdata,
  output logic [7:0] axi_wstrb,
  output logic axi_wlast,
  output logic axi_wvalid,
  input  logic axi_wready,
  input  logic [TXN_ID_WIDTH-1:0] axi_bid,
  input  logic [1:0] axi_bresp,
  input  logic axi_bvalid,
  output logic axi_bready,

  output logic [1:0] l1_controller_protocol_error,
  output logic [1:0] l1_array_protocol_error,
  output logic directory_protocol_error,
  output logic l2_protocol_error,
  output logic memory_adapter_protocol_error,
  output logic memory_adapter_error,
  output logic axi_adapter_protocol_error,
  output logic mmio_protocol_error,
  output logic fatal_error
);
  logic line_rd_req_valid, line_rd_req_ready;
  logic [31:0] line_rd_req_addr;
  logic [TXN_ID_WIDTH-1:0] line_rd_req_id;
  logic line_rd_data_valid, line_rd_data_ready;
  logic [TXN_ID_WIDTH-1:0] line_rd_data_id;
  logic [2:0] line_rd_data_beat;
  logic [63:0] line_rd_data;
  logic line_rd_data_last, line_rd_data_error;

  logic line_wr_req_valid, line_wr_req_ready;
  logic [31:0] line_wr_req_addr;
  logic [TXN_ID_WIDTH-1:0] line_wr_req_id;
  logic line_wr_data_valid, line_wr_data_ready;
  logic [TXN_ID_WIDTH-1:0] line_wr_data_id;
  logic [2:0] line_wr_data_beat;
  logic [63:0] line_wr_data;
  logic line_wr_data_last;
  logic line_wr_rsp_valid, line_wr_rsp_ready;
  logic [TXN_ID_WIDTH-1:0] line_wr_rsp_id;
  logic line_wr_rsp_error;
  logic core_memory_adapter_protocol_error;
  logic core_memory_adapter_error;
  logic core_fatal_error;
  logic [1:0] perf_hit_event;
  logic [1:0] perf_miss_event;
  logic [1:0] perf_snoop_event;
  logic perf_dirty_writeback_event;
  logic [1:0] perf_inflight;
  logic [1:0] perf_access_complete_event;
  logic [4:0] perf_error_status;
  logic protocol_error_status;

  CoherentCacheSubsystem #(.TXN_ID_WIDTH(TXN_ID_WIDTH)) cache_core (
    .clock(clock), .reset(reset),
    .external_fatal_error(axi_adapter_protocol_error),
    .cpu_req_valid(cpu_req_valid), .cpu_req_ready(cpu_req_ready),
    .cpu_req_addr(cpu_req_addr), .cpu_req_write(cpu_req_write),
    .cpu_req_wmask(cpu_req_wmask), .cpu_req_wdata(cpu_req_wdata),
    .cpu_resp_valid(cpu_resp_valid), .cpu_resp_ready(cpu_resp_ready),
    .cpu_resp_addr(cpu_resp_addr), .cpu_resp_write(cpu_resp_write),
    .cpu_resp_rdata(cpu_resp_rdata), .cpu_resp_txn_id(cpu_resp_txn_id),
    .mmio_req_valid(mmio_req_valid), .mmio_req_ready(mmio_req_ready),
    .mmio_req_addr(mmio_req_addr), .mmio_req_size(mmio_req_size),
    .mmio_req_write(mmio_req_write), .mmio_req_wmask(mmio_req_wmask),
    .mmio_req_wdata(mmio_req_wdata), .mmio_resp_valid(mmio_resp_valid),
    .mmio_resp_ready(mmio_resp_ready), .mmio_resp_rdata(mmio_resp_rdata),
    .mem_rd_req_valid(line_rd_req_valid), .mem_rd_req_ready(line_rd_req_ready),
    .mem_rd_req_addr(line_rd_req_addr), .mem_rd_req_txn_id(line_rd_req_id),
    .mem_rd_data_valid(line_rd_data_valid), .mem_rd_data_ready(line_rd_data_ready),
    .mem_rd_data_txn_id(line_rd_data_id), .mem_rd_data_beat_idx(line_rd_data_beat),
    .mem_rd_data(line_rd_data), .mem_rd_data_last(line_rd_data_last),
    .mem_rd_data_error(line_rd_data_error),
    .mem_wr_req_valid(line_wr_req_valid), .mem_wr_req_ready(line_wr_req_ready),
    .mem_wr_req_addr(line_wr_req_addr), .mem_wr_req_txn_id(line_wr_req_id),
    .mem_wr_data_valid(line_wr_data_valid), .mem_wr_data_ready(line_wr_data_ready),
    .mem_wr_data_txn_id(line_wr_data_id), .mem_wr_data_beat_idx(line_wr_data_beat),
    .mem_wr_data(line_wr_data), .mem_wr_data_last(line_wr_data_last),
    .mem_wr_rsp_valid(line_wr_rsp_valid), .mem_wr_rsp_ready(line_wr_rsp_ready),
    .mem_wr_rsp_txn_id(line_wr_rsp_id), .mem_wr_rsp_error(line_wr_rsp_error),
    .l2_victim_valid(), .l2_victim_addr(), .l2_victim_dir_state(),
    .l2_victim_sharers(), .l2_victim_owner_id(), .l2_victim_dirty(),
    .l1_victim_valid(), .l1_victim_addr(), .l1_victim_state(),
    .l1_controller_protocol_error(l1_controller_protocol_error),
    .l1_array_protocol_error(l1_array_protocol_error),
    .directory_protocol_error(directory_protocol_error),
    .l2_protocol_error(l2_protocol_error),
    .memory_adapter_protocol_error(core_memory_adapter_protocol_error),
    .memory_adapter_error(core_memory_adapter_error), .fatal_error(core_fatal_error),
    .mmio_protocol_error(mmio_protocol_error),
    .perf_hit_event(perf_hit_event), .perf_miss_event(perf_miss_event),
    .perf_snoop_event(perf_snoop_event),
    .perf_dirty_writeback_event(perf_dirty_writeback_event),
    .perf_inflight(perf_inflight),
    .perf_access_complete_event(perf_access_complete_event)
  );

  LineMemoryAxi4Adapter #(.ID_WIDTH(TXN_ID_WIDTH)) memory_adapter (
    .clock(clock), .reset(reset),
    .line_rd_req_valid(line_rd_req_valid), .line_rd_req_ready(line_rd_req_ready),
    .line_rd_req_addr(line_rd_req_addr), .line_rd_req_id(line_rd_req_id),
    .line_rd_data_valid(line_rd_data_valid), .line_rd_data_ready(line_rd_data_ready),
    .line_rd_data_id(line_rd_data_id), .line_rd_data_beat(line_rd_data_beat),
    .line_rd_data(line_rd_data), .line_rd_data_last(line_rd_data_last),
    .line_rd_data_error(line_rd_data_error),
    .line_wr_req_valid(line_wr_req_valid), .line_wr_req_ready(line_wr_req_ready),
    .line_wr_req_addr(line_wr_req_addr), .line_wr_req_id(line_wr_req_id),
    .line_wr_data_valid(line_wr_data_valid), .line_wr_data_ready(line_wr_data_ready),
    .line_wr_data_id(line_wr_data_id), .line_wr_data_beat(line_wr_data_beat),
    .line_wr_data(line_wr_data), .line_wr_data_last(line_wr_data_last),
    .line_wr_rsp_valid(line_wr_rsp_valid), .line_wr_rsp_ready(line_wr_rsp_ready),
    .line_wr_rsp_id(line_wr_rsp_id), .line_wr_rsp_error(line_wr_rsp_error),
    .protocol_error(axi_adapter_protocol_error),
    .axi_arid(axi_arid), .axi_araddr(axi_araddr), .axi_arlen(axi_arlen),
    .axi_arsize(axi_arsize), .axi_arburst(axi_arburst),
    .axi_arlock(axi_arlock), .axi_arcache(axi_arcache),
    .axi_arprot(axi_arprot),
    .axi_arvalid(axi_arvalid), .axi_arready(axi_arready),
    .axi_rid(axi_rid), .axi_rdata(axi_rdata), .axi_rresp(axi_rresp),
    .axi_rlast(axi_rlast), .axi_rvalid(axi_rvalid), .axi_rready(axi_rready),
    .axi_awid(axi_awid), .axi_awaddr(axi_awaddr), .axi_awlen(axi_awlen),
    .axi_awsize(axi_awsize), .axi_awburst(axi_awburst),
    .axi_awlock(axi_awlock), .axi_awcache(axi_awcache),
    .axi_awprot(axi_awprot),
    .axi_awvalid(axi_awvalid), .axi_awready(axi_awready),
    .axi_wdata(axi_wdata), .axi_wstrb(axi_wstrb), .axi_wlast(axi_wlast),
    .axi_wvalid(axi_wvalid), .axi_wready(axi_wready),
    .axi_bid(axi_bid), .axi_bresp(axi_bresp), .axi_bvalid(axi_bvalid),
    .axi_bready(axi_bready)
  );

  always_comb begin
    protocol_error_status = (|l1_controller_protocol_error) ||
      (|l1_array_protocol_error) || directory_protocol_error ||
      l2_protocol_error || core_memory_adapter_protocol_error ||
      axi_adapter_protocol_error || mmio_protocol_error;
    memory_adapter_protocol_error = core_memory_adapter_protocol_error ||
                                    axi_adapter_protocol_error;
    memory_adapter_error = core_memory_adapter_error;
    fatal_error = core_fatal_error;
    perf_error_status = {1'b0, mmio_protocol_error, core_memory_adapter_error,
                         protocol_error_status, fatal_error};
  end

  CachePerformanceCsr performance_csr (
    .clock(clock), .reset(reset),
    .hit_event(perf_hit_event), .miss_event(perf_miss_event),
    .snoop_event(perf_snoop_event),
    .dirty_writeback_event(perf_dirty_writeback_event),
    .cache_inflight(perf_inflight),
    .access_complete_event(perf_access_complete_event),
    .error_status(perf_error_status),
    .apb_psel(apb_psel), .apb_penable(apb_penable),
    .apb_pwrite(apb_pwrite), .apb_paddr(apb_paddr),
    .apb_pready(apb_pready), .apb_prdata(apb_prdata),
    .apb_pslverr(apb_pslverr)
  );
endmodule
