// Packed-port adapter for Picker/Toffee, which cannot export unpacked arrays
// as Python pins. Core 0 occupies the least-significant packed lane.
module CoherentCachePythonWrapper (
  input  logic clock,
  input  logic reset,
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
  output logic [1:0] perf_hit_event,
  output logic [1:0] perf_miss_event,
  output logic perf_l2_refill_hit_event,
  output logic perf_l2_refill_miss_event,
  output logic [1:0] perf_snoop_event,
  output logic perf_dirty_writeback_event,
  output logic [1:0] monitor_snoop_accept_valid,
  output logic [63:0] monitor_snoop_accept_addr,
  output logic [1:0] monitor_snoop_accept_opcode,
  output logic [5:0] monitor_snoop_accept_txn_id,
  output logic monitor_victim_snoop_accept_valid,
  output logic monitor_victim_snoop_accept_core,
  output logic [31:0] monitor_victim_snoop_accept_addr,
  output logic [1:0] monitor_snoop_rsp_valid,
  output logic [1:0] monitor_snoop_rsp_ready,
  output logic [5:0] monitor_snoop_rsp_txn_id,
  output logic [3:0] monitor_snoop_rsp_opcode,
  output logic monitor_dir_snoop_rsp_valid,
  output logic monitor_dir_snoop_rsp_ready,
  output logic [1:0] monitor_dir_snoop_rsp_opcode,
  output logic monitor_dir_snoop_target,
  output logic [2:0] monitor_dir_snoop_txn_id,
  output logic monitor_dir_commit_valid,
  output logic [31:0] monitor_dir_commit_addr,
  output logic [1:0] monitor_dir_commit_state,
  output logic [1:0] monitor_dir_commit_sharers,
  output logic monitor_dir_commit_owner,
  output logic monitor_owner_data_valid,
  output logic monitor_owner_data_core,
  output logic [31:0] monitor_owner_data_addr,
  output logic [2:0] monitor_owner_data_beat_idx,
  output logic [63:0] monitor_owner_data,
  output logic monitor_owner_data_last,
  output logic monitor_dir_lookup_conflict_valid,
  output logic [31:0] monitor_dir_lookup_conflict_incoming_addr,
  output logic [31:0] monitor_dir_lookup_conflict_active_addr,
  output logic monitor_dir_lookup_conflict_is_transfer,
  output logic monitor_dir_transfer_grant_conflict_valid,
  output logic [31:0] monitor_dir_transfer_grant_conflict_lookup_addr,
  output logic [31:0] monitor_dir_transfer_grant_conflict_grant_addr,
  output logic monitor_dir_req_accept_valid,
  output logic [31:0] monitor_dir_req_accept_addr,
  output logic monitor_dir_req_accept_src_id,
  output logic [2:0] monitor_dir_req_accept_opcode,
  output logic [2:0] monitor_dir_req_accept_txn_id,
  output logic monitor_l2_lookup_valid,
  output logic [31:0] monitor_l2_lookup_addr,
  output logic monitor_l2_lookup_hit,
  output logic monitor_dir_grant_accept_valid,
  output logic [31:0] monitor_dir_grant_accept_addr,
  output logic monitor_dir_grant_accept_dst,
  output logic [2:0] monitor_dir_grant_accept_opcode,
  output logic [2:0] monitor_dir_grant_accept_txn_id,
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
  output logic monitor_victim_target,
  output logic [1:0] monitor_snoop_offer_valid,
  output logic [1:0] monitor_snoop_offer_ready,
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

  output logic mem_rd_req_valid,
  input  logic mem_rd_req_ready,
  output logic [31:0] mem_rd_req_addr,
  output logic [2:0] mem_rd_req_txn_id,
  input  logic mem_rd_data_valid,
  output logic mem_rd_data_ready,
  input  logic [2:0] mem_rd_data_txn_id,
  input  logic [2:0] mem_rd_data_beat_idx,
  input  logic [63:0] mem_rd_data,
  input  logic mem_rd_data_last,
  input  logic mem_rd_data_error,

  output logic mem_wr_req_valid,
  input  logic mem_wr_req_ready,
  output logic [31:0] mem_wr_req_addr,
  output logic [2:0] mem_wr_req_txn_id,
  output logic mem_wr_data_valid,
  input  logic mem_wr_data_ready,
  output logic [2:0] mem_wr_data_txn_id,
  output logic [2:0] mem_wr_data_beat_idx,
  output logic [63:0] mem_wr_data,
  output logic mem_wr_data_last,
  input  logic mem_wr_rsp_valid,
  output logic mem_wr_rsp_ready,
  input  logic [2:0] mem_wr_rsp_txn_id,
  input  logic mem_wr_rsp_error,
  output logic protocol_error,
  output logic [11:0] protocol_error_detail
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
  logic monitor_snoop_accept_valid_u [0:1];
  logic [31:0] monitor_snoop_accept_addr_u [0:1];
  coherence_protocol_pkg::snoop_opcode_t monitor_snoop_accept_opcode_u [0:1];
  logic [2:0] monitor_snoop_accept_txn_id_u [0:1];
  logic [2:0] monitor_snoop_rsp_txn_id_u [0:1];
  logic [2:0] monitor_dir_grant_accept_txn_id_u;
  logic [2:0] monitor_dir_req_accept_txn_id_u;
  coherence_protocol_pkg::snoop_response_t monitor_snoop_rsp_opcode_u [0:1];
  coherence_protocol_pkg::request_opcode_t monitor_dir_req_accept_opcode_pkg;

  logic mmio_req_valid;
  logic [31:0] mmio_req_addr;
  logic [2:0] mmio_req_size;
  logic mmio_req_write;
  logic [7:0] mmio_req_wmask;
  logic [63:0] mmio_req_wdata;
  logic mmio_resp_ready;
  logic mmio_protocol_error;
  logic [1:0] l1_controller_protocol_error;
  logic [1:0] l1_array_protocol_error;
  logic directory_protocol_error;
  logic [3:0] directory_protocol_error_code;
  logic l2_protocol_error;
  logic memory_adapter_protocol_error;
  logic memory_adapter_error;
  logic fatal_error;

  always_comb begin
    for (int core = 0; core < 2; core = core + 1) begin
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
      monitor_snoop_accept_valid[core] = monitor_snoop_accept_valid_u[core];
      monitor_snoop_accept_addr[core*32 +: 32] =
        monitor_snoop_accept_addr_u[core];
      monitor_snoop_accept_opcode[core] =
        monitor_snoop_accept_opcode_u[core];
      monitor_snoop_accept_txn_id[core*3 +: 3] =
        monitor_snoop_accept_txn_id_u[core];
      monitor_snoop_rsp_txn_id[core*3 +: 3] = monitor_snoop_rsp_txn_id_u[core];
      monitor_snoop_rsp_opcode[core*2 +: 2] = monitor_snoop_rsp_opcode_u[core];
    end
  end

  assign protocol_error = fatal_error || directory_protocol_error ||
    l2_protocol_error || (|l1_controller_protocol_error) ||
    (|l1_array_protocol_error) || memory_adapter_protocol_error ||
    memory_adapter_error || mmio_protocol_error;
  assign protocol_error_detail = {
    mmio_protocol_error,
    (memory_adapter_protocol_error || memory_adapter_error),
    l1_array_protocol_error,
    l1_controller_protocol_error,
    l2_protocol_error,
    directory_protocol_error,
    directory_protocol_error_code
  };

  CoherentCacheSubsystem #(.TXN_ID_WIDTH(3), .NUM_MSHRS(4)) cache (
    .clock(clock), .reset(reset), .external_fatal_error(1'b0),
    .cpu_req_valid(cpu_req_valid_u), .cpu_req_ready(cpu_req_ready_u),
    .cpu_req_addr(cpu_req_addr_u), .cpu_req_write(cpu_req_write_u),
    .cpu_req_wmask(cpu_req_wmask_u), .cpu_req_wdata(cpu_req_wdata_u),
    .cpu_resp_valid(cpu_resp_valid_u), .cpu_resp_ready(cpu_resp_ready_u),
    .cpu_resp_addr(cpu_resp_addr_u), .cpu_resp_write(cpu_resp_write_u),
    .cpu_resp_rdata(cpu_resp_rdata_u), .cpu_resp_txn_id(cpu_resp_txn_id_u),
    .mmio_req_valid(mmio_req_valid), .mmio_req_ready(1'b1),
    .mmio_req_addr(mmio_req_addr), .mmio_req_size(mmio_req_size),
    .mmio_req_write(mmio_req_write), .mmio_req_wmask(mmio_req_wmask),
    .mmio_req_wdata(mmio_req_wdata), .mmio_resp_valid(1'b0),
    .mmio_resp_ready(mmio_resp_ready), .mmio_resp_rdata(64'b0),
    .mem_rd_req_valid(mem_rd_req_valid), .mem_rd_req_ready(mem_rd_req_ready),
    .mem_rd_req_addr(mem_rd_req_addr), .mem_rd_req_txn_id(mem_rd_req_txn_id),
    .mem_rd_data_valid(mem_rd_data_valid), .mem_rd_data_ready(mem_rd_data_ready),
    .mem_rd_data_txn_id(mem_rd_data_txn_id),
    .mem_rd_data_beat_idx(mem_rd_data_beat_idx), .mem_rd_data(mem_rd_data),
    .mem_rd_data_last(mem_rd_data_last), .mem_rd_data_error(mem_rd_data_error),
    .mem_wr_req_valid(mem_wr_req_valid), .mem_wr_req_ready(mem_wr_req_ready),
    .mem_wr_req_addr(mem_wr_req_addr), .mem_wr_req_txn_id(mem_wr_req_txn_id),
    .mem_wr_data_valid(mem_wr_data_valid), .mem_wr_data_ready(mem_wr_data_ready),
    .mem_wr_data_txn_id(mem_wr_data_txn_id),
    .mem_wr_data_beat_idx(mem_wr_data_beat_idx), .mem_wr_data(mem_wr_data),
    .mem_wr_data_last(mem_wr_data_last), .mem_wr_rsp_valid(mem_wr_rsp_valid),
    .mem_wr_rsp_ready(mem_wr_rsp_ready), .mem_wr_rsp_txn_id(mem_wr_rsp_txn_id),
    .mem_wr_rsp_error(mem_wr_rsp_error),
    .l2_victim_valid(), .l2_victim_addr(), .l2_victim_dir_state(),
    .l2_victim_sharers(), .l2_victim_owner_id(), .l2_victim_dirty(),
    .l1_victim_valid(), .l1_victim_addr(), .l1_victim_state(),
    .l1_controller_protocol_error(l1_controller_protocol_error),
    .l1_array_protocol_error(l1_array_protocol_error),
    .directory_protocol_error(directory_protocol_error),
    .directory_protocol_error_code(directory_protocol_error_code),
    .l2_protocol_error(l2_protocol_error),
    .memory_adapter_protocol_error(memory_adapter_protocol_error),
    .memory_adapter_error(memory_adapter_error), .fatal_error(fatal_error),
    .mmio_protocol_error(mmio_protocol_error),
    .perf_hit_event(perf_hit_event), .perf_miss_event(perf_miss_event),
    .perf_snoop_event(perf_snoop_event),
    .perf_dirty_writeback_event(perf_dirty_writeback_event), .perf_inflight(),
    .perf_access_complete_event(), .metadata_commit_valid(),
    .perf_l2_refill_hit_event(perf_l2_refill_hit_event),
    .perf_l2_refill_miss_event(perf_l2_refill_miss_event),
    .metadata_commit_line_addr(), .metadata_commit_state(),
    .metadata_commit_is_snoop(),
    .monitor_snoop_accept_valid(monitor_snoop_accept_valid_u),
    .monitor_snoop_accept_addr(monitor_snoop_accept_addr_u),
    .monitor_snoop_accept_opcode(monitor_snoop_accept_opcode_u),
    .monitor_snoop_accept_txn_id(monitor_snoop_accept_txn_id_u),
    .monitor_victim_snoop_accept_valid(monitor_victim_snoop_accept_valid),
    .monitor_victim_snoop_accept_core(monitor_victim_snoop_accept_core),
    .monitor_victim_snoop_accept_addr(monitor_victim_snoop_accept_addr),
    .monitor_snoop_rsp_valid(monitor_snoop_rsp_valid),
    .monitor_snoop_rsp_ready(monitor_snoop_rsp_ready),
    .monitor_snoop_rsp_txn_id(monitor_snoop_rsp_txn_id_u),
    .monitor_snoop_rsp_opcode(monitor_snoop_rsp_opcode_u),
    .monitor_dir_snoop_rsp_valid(monitor_dir_snoop_rsp_valid),
    .monitor_dir_snoop_rsp_ready(monitor_dir_snoop_rsp_ready),
    .monitor_dir_snoop_rsp_opcode(monitor_dir_snoop_rsp_opcode),
    .monitor_dir_snoop_target(monitor_dir_snoop_target),
    .monitor_dir_snoop_txn_id(monitor_dir_snoop_txn_id),
    .monitor_dir_commit_valid(monitor_dir_commit_valid),
    .monitor_dir_commit_addr(monitor_dir_commit_addr),
    .monitor_dir_commit_state(monitor_dir_commit_state),
    .monitor_dir_commit_sharers(monitor_dir_commit_sharers),
    .monitor_dir_commit_owner(monitor_dir_commit_owner),
    .monitor_owner_data_valid(monitor_owner_data_valid),
    .monitor_owner_data_core(monitor_owner_data_core),
    .monitor_owner_data_addr(monitor_owner_data_addr),
    .monitor_owner_data_beat_idx(monitor_owner_data_beat_idx),
    .monitor_owner_data(monitor_owner_data),
    .monitor_owner_data_last(monitor_owner_data_last),
    .monitor_dir_lookup_conflict_valid(monitor_dir_lookup_conflict_valid),
    .monitor_dir_lookup_conflict_incoming_addr(
      monitor_dir_lookup_conflict_incoming_addr),
    .monitor_dir_lookup_conflict_active_addr(
      monitor_dir_lookup_conflict_active_addr),
    .monitor_dir_lookup_conflict_is_transfer(
      monitor_dir_lookup_conflict_is_transfer),
    .monitor_dir_transfer_grant_conflict_valid(
      monitor_dir_transfer_grant_conflict_valid),
    .monitor_dir_transfer_grant_conflict_lookup_addr(
      monitor_dir_transfer_grant_conflict_lookup_addr),
    .monitor_dir_transfer_grant_conflict_grant_addr(
      monitor_dir_transfer_grant_conflict_grant_addr),
    .monitor_dir_req_accept_valid(monitor_dir_req_accept_valid),
    .monitor_dir_req_accept_addr(monitor_dir_req_accept_addr),
    .monitor_dir_req_accept_src_id(monitor_dir_req_accept_src_id),
    .monitor_dir_req_accept_opcode(monitor_dir_req_accept_opcode_pkg),
    .monitor_dir_req_accept_txn_id(monitor_dir_req_accept_txn_id_u),
    .monitor_l2_lookup_valid(monitor_l2_lookup_valid),
    .monitor_l2_lookup_addr(monitor_l2_lookup_addr),
    .monitor_l2_lookup_hit(monitor_l2_lookup_hit),
    .monitor_dir_grant_accept_valid(monitor_dir_grant_accept_valid),
    .monitor_dir_grant_accept_addr(monitor_dir_grant_accept_addr),
    .monitor_dir_grant_accept_dst(monitor_dir_grant_accept_dst),
    .monitor_dir_grant_accept_opcode(monitor_dir_grant_accept_opcode),
    .monitor_dir_grant_accept_txn_id(monitor_dir_grant_accept_txn_id_u),
    .monitor_l2_fill_active(monitor_l2_fill_active),
    .monitor_l2_line_wr_valid(monitor_l2_line_wr_valid),
    .monitor_l2_line_wr_ready(monitor_l2_line_wr_ready),
    .monitor_l2_line_wr_addr(monitor_l2_line_wr_addr),
    .monitor_l2_line_wr_beat(monitor_l2_line_wr_beat),
    .monitor_dir_snoop_data_to_l2(monitor_dir_snoop_data_to_l2),
    .monitor_dir_snoop_valid(monitor_dir_snoop_valid),
    .monitor_snoop_set_conflict(monitor_snoop_set_conflict),
    .monitor_engine_state(monitor_engine_state),
    .monitor_engine_addr(monitor_engine_addr),
    .monitor_victim_addr(monitor_victim_addr),
    .monitor_victim_pending_targets(monitor_victim_pending_targets),
    .monitor_victim_target(monitor_victim_target),
    .monitor_snoop_offer_valid(monitor_snoop_offer_valid),
    .monitor_snoop_offer_ready(monitor_snoop_offer_ready),
    .monitor_mem_mshr_valid(monitor_mem_mshr_valid),
    .monitor_directory_active_contexts(monitor_directory_active_contexts),
    .monitor_dir_req_live_valid(monitor_dir_req_live_valid),
    .monitor_dir_req_live_ready(monitor_dir_req_live_ready),
    .monitor_dir_req_live_addr(monitor_dir_req_live_addr),
    .monitor_dir_xfer_live_valid(monitor_dir_xfer_live_valid),
    .monitor_dir_xfer_live_ready(monitor_dir_xfer_live_ready),
    .monitor_cpu_state(monitor_cpu_state),
    .monitor_l1_snoop_state(monitor_l1_snoop_state),
    .monitor_cpu_active_addr(monitor_cpu_active_addr),
    .monitor_l1_replace_state(monitor_l1_replace_state)
  );

  assign monitor_dir_grant_accept_txn_id = monitor_dir_grant_accept_txn_id_u;
  assign monitor_dir_req_accept_txn_id = monitor_dir_req_accept_txn_id_u;

  assign monitor_dir_req_accept_opcode = monitor_dir_req_accept_opcode_pkg;
endmodule
