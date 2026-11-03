// Picker/Toffee verification wrapper for the complete product subsystem.
// Only SystemVerilog/Python packing and passive probe wiring live here; the
// product RTL interface and behavior remain unchanged.
module CoherentCacheAxiPythonWrapper (
  input logic clock,
  input logic reset,

  // Core 0 occupies the least-significant packed lane.
  input  logic [1:0] cpu_req_valid,
  output logic [1:0] cpu_req_ready,
  input  logic [63:0] cpu_req_addr,
  input  logic [1:0] cpu_req_write,
  input  logic [15:0] cpu_req_wmask,
  input  logic [127:0] cpu_req_wdata,
  output logic [1:0] cpu_resp_valid,
  input  logic [1:0] cpu_resp_ready,
  output logic [63:0] cpu_resp_addr,
  output logic [1:0] cpu_resp_write,
  output logic [127:0] cpu_resp_rdata,
  output logic [5:0] cpu_resp_txn_id,

  // Existing NutShell MMIO request/response contract.
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

  // Read-only performance/status CSR window.
  input  logic apb_psel,
  input  logic apb_penable,
  input  logic apb_pwrite,
  input  logic [31:0] apb_paddr,
  output logic apb_pready,
  output logic [31:0] apb_prdata,
  output logic apb_pslverr,

  // AXI4 memory slave channels. TXN_ID_WIDTH is fixed at the product default
  // (3) for this wrapper; the adapter still permits four outstanding slots.
  output logic [2:0] axi_arid,
  output logic [31:0] axi_araddr,
  output logic [7:0] axi_arlen,
  output logic [2:0] axi_arsize,
  output logic [1:0] axi_arburst,
  output logic axi_arlock,
  output logic [3:0] axi_arcache,
  output logic [2:0] axi_arprot,
  output logic axi_arvalid,
  input  logic axi_arready,
  input  logic [2:0] axi_rid,
  input  logic [63:0] axi_rdata,
  input  logic [1:0] axi_rresp,
  input  logic axi_rlast,
  input  logic axi_rvalid,
  output logic axi_rready,
  output logic [2:0] axi_awid,
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
  input  logic [2:0] axi_bid,
  input  logic [1:0] axi_bresp,
  input  logic axi_bvalid,
  output logic axi_bready,

  output logic [1:0] monitor_l1_commit_valid,
  output logic [63:0] monitor_l1_commit_addr,
  output logic [3:0] monitor_l1_commit_state,
  output logic [1:0] monitor_l1_commit_is_snoop,
  output logic [1:0] monitor_snoop_accept_valid,
  output logic [63:0] monitor_snoop_accept_addr,
  output logic [3:0] monitor_snoop_accept_opcode,
  output logic [5:0] monitor_snoop_accept_txn_id,
  output logic [1:0] monitor_snoop_rsp_valid,
  output logic [1:0] monitor_snoop_rsp_ready,
  output logic [5:0] monitor_snoop_rsp_txn_id,
  output logic [3:0] monitor_snoop_rsp_opcode,
  output logic monitor_dir_commit_valid,
  output logic [31:0] monitor_dir_commit_addr,
  output logic [1:0] monitor_dir_commit_state,
  output logic [1:0] monitor_dir_commit_sharers,
  output logic monitor_dir_commit_owner,
  output logic monitor_dir_req_accept_valid,
  output logic [31:0] monitor_dir_req_accept_addr,
  output logic monitor_dir_req_accept_src_id,
  output logic [2:0] monitor_dir_req_accept_opcode,
  output logic [2:0] monitor_dir_req_accept_txn_id,
  output logic monitor_dir_grant_accept_valid,
  output logic [31:0] monitor_dir_grant_accept_addr,
  output logic monitor_dir_grant_accept_dst,
  output logic [2:0] monitor_dir_grant_accept_opcode,
  output logic [2:0] monitor_dir_grant_accept_txn_id,
  output logic monitor_owner_data_valid,
  output logic monitor_owner_data_core,
  output logic [31:0] monitor_owner_data_addr,
  output logic [2:0] monitor_owner_data_beat_idx,
  output logic [63:0] monitor_owner_data,
  output logic monitor_owner_data_last,
  output logic monitor_l2_lookup_valid,
  output logic [31:0] monitor_l2_lookup_addr,
  output logic monitor_l2_lookup_hit,
  output logic monitor_l2_fill_active,
  output logic monitor_l2_line_wr_valid,
  output logic monitor_l2_line_wr_ready,
  output logic [31:0] monitor_l2_line_wr_addr,
  output logic [2:0] monitor_l2_line_wr_beat,
  output logic monitor_dir_snoop_data_to_l2,
  output logic monitor_dir_snoop_valid,
  output logic monitor_snoop_set_conflict,
  output logic [4:0] monitor_engine_state,
  output logic [31:0] monitor_engine_addr,
  output logic [31:0] monitor_victim_addr,
  output logic [1:0] monitor_victim_pending_targets,
  output logic [3:0] monitor_mem_mshr_valid,
  output logic [3:0] monitor_directory_active_contexts,
  output logic monitor_dir_req_live_valid,
  output logic monitor_dir_req_live_ready,
  output logic [31:0] monitor_dir_req_live_addr,
  output logic monitor_dir_xfer_live_valid,
  output logic monitor_dir_xfer_live_ready,
  output logic [5:0] monitor_cpu_state,
  output logic [5:0] monitor_l1_snoop_state,
  output logic [63:0] monitor_cpu_active_addr,
  output logic [7:0] monitor_l1_replace_state,
  output logic [1:0] monitor_l2_victim_valid,
  output logic [31:0] monitor_l2_victim_addr,
  output logic [1:0] monitor_l2_victim_dir_state,
  output logic [1:0] monitor_l2_victim_sharers,
  output logic [1:0] monitor_l2_victim_owner_id,
  output logic [1:0] monitor_l2_victim_dirty,
  output logic [1:0] l1_controller_protocol_error,
  output logic [1:0] l1_array_protocol_error,
  output logic directory_protocol_error,
  output logic l2_protocol_error,
  output logic memory_adapter_protocol_error,
  output logic memory_adapter_error,
  output logic axi_adapter_protocol_error,
  output logic mmio_protocol_error,
  output logic fatal_error,
  output logic protocol_error
);
  logic cpu_req_valid_u [0:1];
  logic cpu_req_ready_u [0:1];
  logic [31:0] cpu_req_addr_u [0:1];
  logic cpu_req_write_u [0:1];
  logic [7:0] cpu_req_wmask_u [0:1];
  logic [63:0] cpu_req_wdata_u [0:1];
  logic cpu_resp_valid_u [0:1];
  logic cpu_resp_ready_u [0:1];
  logic [31:0] cpu_resp_addr_u [0:1];
  logic cpu_resp_write_u [0:1];
  logic [63:0] cpu_resp_rdata_u [0:1];
  logic [2:0] cpu_resp_txn_id_u [0:1];

  for (genvar core = 0; core < 2; core++) begin : g_pack_cpu
    always_comb begin
      cpu_req_valid_u[core] = cpu_req_valid[core];
      cpu_req_addr_u[core] = cpu_req_addr[core*32 +: 32];
      cpu_req_write_u[core] = cpu_req_write[core];
      cpu_req_wmask_u[core] = cpu_req_wmask[core*8 +: 8];
      cpu_req_wdata_u[core] = cpu_req_wdata[core*64 +: 64];
      cpu_req_ready[core] = cpu_req_ready_u[core];
      cpu_resp_valid[core] = cpu_resp_valid_u[core];
      cpu_resp_ready_u[core] = cpu_resp_ready[core];
      cpu_resp_addr[core*32 +: 32] = cpu_resp_addr_u[core];
      cpu_resp_write[core] = cpu_resp_write_u[core];
      cpu_resp_rdata[core*64 +: 64] = cpu_resp_rdata_u[core];
      cpu_resp_txn_id[core*3 +: 3] = cpu_resp_txn_id_u[core];
      monitor_l1_commit_valid[core] = dut.cache_core.metadata_commit_valid[core];
      monitor_l1_commit_addr[core*32 +: 32] =
        dut.cache_core.metadata_commit_line_addr[core];
      monitor_l1_commit_state[core*2 +: 2] =
        dut.cache_core.metadata_commit_state[core];
      monitor_l1_commit_is_snoop[core] =
        dut.cache_core.metadata_commit_is_snoop[core];
      monitor_snoop_accept_valid[core] =
        dut.cache_core.monitor_snoop_accept_valid[core];
      monitor_snoop_accept_addr[core*32 +: 32] =
        dut.cache_core.monitor_snoop_accept_addr[core];
      monitor_snoop_accept_opcode[core*2 +: 2] =
        dut.cache_core.monitor_snoop_accept_opcode[core];
      monitor_snoop_accept_txn_id[core*3 +: 3] =
        dut.cache_core.monitor_snoop_accept_txn_id[core];
      monitor_snoop_rsp_valid[core] =
        dut.cache_core.monitor_snoop_rsp_valid[core];
      monitor_snoop_rsp_ready[core] =
        dut.cache_core.monitor_snoop_rsp_ready[core];
      monitor_snoop_rsp_txn_id[core*3 +: 3] =
        dut.cache_core.monitor_snoop_rsp_txn_id[core];
      monitor_snoop_rsp_opcode[core*2 +: 2] =
        dut.cache_core.monitor_snoop_rsp_opcode[core];
    end
  end

  CoherentCacheAxiSubsystem #(
    .TXN_ID_WIDTH(3), .AXI_MAX_OUTSTANDING(4), .NUM_MSHRS(4)
  ) dut (
    .clock(clock), .reset(reset),
    .cpu_req_valid(cpu_req_valid_u), .cpu_req_ready(cpu_req_ready_u),
    .cpu_req_addr(cpu_req_addr_u), .cpu_req_write(cpu_req_write_u),
    .cpu_req_wmask(cpu_req_wmask_u), .cpu_req_wdata(cpu_req_wdata_u),
    .cpu_resp_valid(cpu_resp_valid_u), .cpu_resp_ready(cpu_resp_ready_u),
    .cpu_resp_addr(cpu_resp_addr_u), .cpu_resp_write(cpu_resp_write_u),
    .cpu_resp_rdata(cpu_resp_rdata_u), .cpu_resp_txn_id(cpu_resp_txn_id_u),
    .mmio_req_valid(mmio_req_valid), .mmio_req_ready(mmio_req_ready),
    .mmio_req_addr(mmio_req_addr), .mmio_req_size(mmio_req_size),
    .mmio_req_write(mmio_req_write), .mmio_req_wmask(mmio_req_wmask),
    .mmio_req_wdata(mmio_req_wdata), .mmio_resp_valid(mmio_resp_valid),
    .mmio_resp_ready(mmio_resp_ready), .mmio_resp_rdata(mmio_resp_rdata),
    .apb_psel(apb_psel), .apb_penable(apb_penable),
    .apb_pwrite(apb_pwrite), .apb_paddr(apb_paddr),
    .apb_pready(apb_pready), .apb_prdata(apb_prdata),
    .apb_pslverr(apb_pslverr),
    .axi_arid(axi_arid), .axi_araddr(axi_araddr), .axi_arlen(axi_arlen),
    .axi_arsize(axi_arsize), .axi_arburst(axi_arburst),
    .axi_arlock(axi_arlock), .axi_arcache(axi_arcache),
    .axi_arprot(axi_arprot), .axi_arvalid(axi_arvalid),
    .axi_arready(axi_arready), .axi_rid(axi_rid), .axi_rdata(axi_rdata),
    .axi_rresp(axi_rresp), .axi_rlast(axi_rlast), .axi_rvalid(axi_rvalid),
    .axi_rready(axi_rready), .axi_awid(axi_awid), .axi_awaddr(axi_awaddr),
    .axi_awlen(axi_awlen), .axi_awsize(axi_awsize),
    .axi_awburst(axi_awburst), .axi_awlock(axi_awlock),
    .axi_awcache(axi_awcache), .axi_awprot(axi_awprot),
    .axi_awvalid(axi_awvalid), .axi_awready(axi_awready),
    .axi_wdata(axi_wdata), .axi_wstrb(axi_wstrb), .axi_wlast(axi_wlast),
    .axi_wvalid(axi_wvalid), .axi_wready(axi_wready), .axi_bid(axi_bid),
    .axi_bresp(axi_bresp), .axi_bvalid(axi_bvalid), .axi_bready(axi_bready),
    .l1_controller_protocol_error(l1_controller_protocol_error),
    .l1_array_protocol_error(l1_array_protocol_error),
    .directory_protocol_error(directory_protocol_error),
    .l2_protocol_error(l2_protocol_error),
    .memory_adapter_protocol_error(memory_adapter_protocol_error),
    .memory_adapter_error(memory_adapter_error),
    .axi_adapter_protocol_error(axi_adapter_protocol_error),
    .mmio_protocol_error(mmio_protocol_error), .fatal_error(fatal_error)
  );

  // Passive read-only observations of the existing child monitor ports. These
  // assignments create no new product RTL pins and never drive the DUT.
  assign monitor_dir_commit_valid = dut.cache_core.monitor_dir_commit_valid;
  assign monitor_dir_commit_addr = dut.cache_core.monitor_dir_commit_addr;
  assign monitor_dir_commit_state = dut.cache_core.monitor_dir_commit_state;
  assign monitor_dir_commit_sharers = dut.cache_core.monitor_dir_commit_sharers;
  assign monitor_dir_commit_owner = dut.cache_core.monitor_dir_commit_owner;
  assign monitor_dir_req_accept_valid = dut.cache_core.monitor_dir_req_accept_valid;
  assign monitor_dir_req_accept_addr = dut.cache_core.monitor_dir_req_accept_addr;
  assign monitor_dir_req_accept_src_id = dut.cache_core.monitor_dir_req_accept_src_id;
  assign monitor_dir_req_accept_opcode = dut.cache_core.monitor_dir_req_accept_opcode;
  assign monitor_dir_req_accept_txn_id = dut.cache_core.monitor_dir_req_accept_txn_id;
  assign monitor_dir_grant_accept_valid = dut.cache_core.monitor_dir_grant_accept_valid;
  assign monitor_dir_grant_accept_addr = dut.cache_core.monitor_dir_grant_accept_addr;
  assign monitor_dir_grant_accept_dst = dut.cache_core.monitor_dir_grant_accept_dst;
  assign monitor_dir_grant_accept_opcode = dut.cache_core.monitor_dir_grant_accept_opcode;
  assign monitor_dir_grant_accept_txn_id = dut.cache_core.monitor_dir_grant_accept_txn_id;
  assign monitor_owner_data_valid = dut.cache_core.monitor_owner_data_valid;
  assign monitor_owner_data_core = dut.cache_core.monitor_owner_data_core;
  assign monitor_owner_data_addr = dut.cache_core.monitor_owner_data_addr;
  assign monitor_owner_data_beat_idx = dut.cache_core.monitor_owner_data_beat_idx;
  assign monitor_owner_data = dut.cache_core.monitor_owner_data;
  assign monitor_owner_data_last = dut.cache_core.monitor_owner_data_last;
  assign monitor_l2_lookup_valid = dut.cache_core.monitor_l2_lookup_valid;
  assign monitor_l2_lookup_addr = dut.cache_core.monitor_l2_lookup_addr;
  assign monitor_l2_lookup_hit = dut.cache_core.monitor_l2_lookup_hit;
  assign monitor_l2_fill_active = dut.cache_core.monitor_l2_fill_active;
  assign monitor_l2_line_wr_valid = dut.cache_core.monitor_l2_line_wr_valid;
  assign monitor_l2_line_wr_ready = dut.cache_core.monitor_l2_line_wr_ready;
  assign monitor_l2_line_wr_addr = dut.cache_core.monitor_l2_line_wr_addr;
  assign monitor_l2_line_wr_beat = dut.cache_core.monitor_l2_line_wr_beat;
  assign monitor_dir_snoop_data_to_l2 = dut.cache_core.monitor_dir_snoop_data_to_l2;
  assign monitor_dir_snoop_valid = dut.cache_core.monitor_dir_snoop_valid;
  assign monitor_snoop_set_conflict = dut.cache_core.monitor_snoop_set_conflict;
  assign monitor_engine_state = dut.cache_core.monitor_engine_state;
  assign monitor_engine_addr = dut.cache_core.monitor_engine_addr;
  assign monitor_victim_addr = dut.cache_core.monitor_victim_addr;
  assign monitor_victim_pending_targets = dut.cache_core.monitor_victim_pending_targets;
  assign monitor_mem_mshr_valid = dut.cache_core.monitor_mem_mshr_valid;
  assign monitor_directory_active_contexts =
    dut.cache_core.monitor_directory_active_contexts;
  assign monitor_dir_req_live_valid = dut.cache_core.monitor_dir_req_live_valid;
  assign monitor_dir_req_live_ready = dut.cache_core.monitor_dir_req_live_ready;
  assign monitor_dir_req_live_addr = dut.cache_core.monitor_dir_req_live_addr;
  assign monitor_dir_xfer_live_valid = dut.cache_core.monitor_dir_xfer_live_valid;
  assign monitor_dir_xfer_live_ready = dut.cache_core.monitor_dir_xfer_live_ready;
  assign monitor_cpu_state = dut.cache_core.monitor_cpu_state;
  assign monitor_l1_snoop_state = dut.cache_core.monitor_l1_snoop_state;
  assign monitor_cpu_active_addr = dut.cache_core.monitor_cpu_active_addr;
  assign monitor_l1_replace_state = dut.cache_core.monitor_l1_replace_state;
  assign monitor_l2_victim_valid = dut.cache_core.l2_victim_valid;
  assign monitor_l2_victim_addr = dut.cache_core.l2_victim_addr;
  assign monitor_l2_victim_dir_state = dut.cache_core.l2_victim_dir_state;
  assign monitor_l2_victim_sharers = dut.cache_core.l2_victim_sharers;
  assign monitor_l2_victim_owner_id = dut.cache_core.l2_victim_owner_id;
  assign monitor_l2_victim_dirty = dut.cache_core.l2_victim_dirty;

  always_comb begin
    protocol_error = (|l1_controller_protocol_error) ||
      (|l1_array_protocol_error) || directory_protocol_error ||
      l2_protocol_error || memory_adapter_protocol_error ||
      memory_adapter_error || axi_adapter_protocol_error ||
      mmio_protocol_error || fatal_error;
  end
endmodule
