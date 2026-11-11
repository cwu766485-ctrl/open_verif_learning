module FinalContextReachabilityFormal(
input logic  clock ,
input logic  external_fatal_error ,
input logic  cpu_req_valid [0:1],
input logic [31:0] cpu_req_addr [0:1],
input logic  cpu_req_write [0:1],
input logic [7:0] cpu_req_wmask [0:1],
input logic [63:0] cpu_req_wdata [0:1],
input logic  cpu_resp_ready [0:1],
input logic  mmio_req_ready ,
input logic  mmio_resp_valid ,
input logic [63:0] mmio_resp_rdata ,
input logic  mem_rd_req_ready ,
input logic  mem_rd_data_valid ,
input logic [4-1:0] mem_rd_data_txn_id ,
input logic [2:0] mem_rd_data_beat_idx ,
input logic [63:0] mem_rd_data ,
input logic  mem_rd_data_last ,
input logic  mem_rd_data_error ,
input logic  mem_wr_req_ready ,
input logic  mem_wr_data_ready ,
input logic  mem_wr_rsp_valid ,
input logic [4-1:0] mem_wr_rsp_txn_id ,
input logic  mem_wr_rsp_error ,
input logic reset_later
);
logic  cpu_req_ready [0:1];
logic  cpu_resp_valid [0:1];
logic [31:0] cpu_resp_addr [0:1];
logic  cpu_resp_write [0:1];
logic [63:0] cpu_resp_rdata [0:1];
logic [4-1:0] cpu_resp_txn_id [0:1];
logic  mmio_req_valid ;
logic [31:0] mmio_req_addr ;
logic [2:0] mmio_req_size ;
logic  mmio_req_write ;
logic [7:0] mmio_req_wmask ;
logic [63:0] mmio_req_wdata ;
logic  mmio_resp_ready ;
logic  mem_rd_req_valid ;
logic [31:0] mem_rd_req_addr ;
logic [4-1:0] mem_rd_req_txn_id ;
logic  mem_rd_data_ready ;
logic  mem_wr_req_valid ;
logic [31:0] mem_wr_req_addr ;
logic [4-1:0] mem_wr_req_txn_id ;
logic  mem_wr_data_valid ;
logic [4-1:0] mem_wr_data_txn_id ;
logic [2:0] mem_wr_data_beat_idx ;
logic [63:0] mem_wr_data ;
logic  mem_wr_data_last ;
logic  mem_wr_rsp_ready ;
logic  l2_victim_valid ;
logic [31:0] l2_victim_addr ;
coherence_protocol_pkg::directory_state_t  l2_victim_dir_state ;
logic [1:0] l2_victim_sharers ;
logic  l2_victim_owner_id ;
logic  l2_victim_dirty ;
logic [1:0] l1_victim_valid ;
logic [31:0] l1_victim_addr [0:1];
coherence_protocol_pkg::mesi_state_t  l1_victim_state [0:1];
logic [1:0] l1_controller_protocol_error ;
logic [1:0] l1_array_protocol_error ;
logic  directory_protocol_error ;
logic [3:0] directory_protocol_error_code ;
logic  l2_protocol_error ;
logic  memory_adapter_protocol_error ;
logic  memory_adapter_error ;
logic  fatal_error ;
logic  mmio_protocol_error ;
logic [1:0] perf_hit_event ;
logic [1:0] perf_miss_event ;
logic [1:0] perf_snoop_event ;
logic  perf_dirty_writeback_event ;
logic [1:0] perf_inflight ;
logic [1:0] perf_access_complete_event ;
logic  perf_l2_refill_hit_event ;
logic  perf_l2_refill_miss_event ;
logic  metadata_commit_valid [0:1];
logic [31:0] metadata_commit_line_addr [0:1];
coherence_protocol_pkg::mesi_state_t  metadata_commit_state [0:1];
logic  metadata_commit_is_snoop [0:1];
logic  monitor_snoop_accept_valid [0:1];
logic [31:0] monitor_snoop_accept_addr [0:1];
coherence_protocol_pkg::snoop_opcode_t  monitor_snoop_accept_opcode [0:1];
logic [4-1:0] monitor_snoop_accept_txn_id [0:1];
logic  monitor_victim_snoop_accept_valid ;
logic  monitor_victim_snoop_accept_core ;
logic [31:0] monitor_victim_snoop_accept_addr ;
logic [1:0] monitor_snoop_rsp_valid ;
logic [1:0] monitor_snoop_rsp_ready ;
logic [4-1:0] monitor_snoop_rsp_txn_id [0:1];
coherence_protocol_pkg::snoop_response_t  monitor_snoop_rsp_opcode [0:1];
logic  monitor_dir_snoop_target ;
logic [4-1:0] monitor_dir_snoop_txn_id ;
logic  monitor_dir_snoop_rsp_valid ;
logic  monitor_dir_snoop_rsp_ready ;
coherence_protocol_pkg::snoop_response_t  monitor_dir_snoop_rsp_opcode ;
logic  monitor_dir_commit_valid ;
logic [31:0] monitor_dir_commit_addr ;
logic [1:0] monitor_dir_commit_state ;
logic [1:0] monitor_dir_commit_sharers ;
logic  monitor_dir_commit_owner ;
logic  monitor_owner_data_valid ;
logic  monitor_owner_data_core ;
logic [31:0] monitor_owner_data_addr ;
logic [2:0] monitor_owner_data_beat_idx ;
logic [63:0] monitor_owner_data ;
logic  monitor_owner_data_last ;
logic  monitor_dir_lookup_conflict_valid ;
logic [31:0] monitor_dir_lookup_conflict_incoming_addr ;
logic [31:0] monitor_dir_lookup_conflict_active_addr ;
logic  monitor_dir_lookup_conflict_is_transfer ;
logic  monitor_dir_transfer_grant_conflict_valid ;
logic [31:0] monitor_dir_transfer_grant_conflict_lookup_addr ;
logic [31:0] monitor_dir_transfer_grant_conflict_grant_addr ;
logic  monitor_dir_req_accept_valid ;
logic [31:0] monitor_dir_req_accept_addr ;
logic  monitor_dir_req_accept_src_id ;
coherence_protocol_pkg::request_opcode_t  monitor_dir_req_accept_opcode ;
logic [4-1:0] monitor_dir_req_accept_txn_id ;
logic  monitor_l2_lookup_valid ;
logic [31:0] monitor_l2_lookup_addr ;
logic  monitor_l2_lookup_hit ;
logic  monitor_dir_grant_accept_valid ;
logic [31:0] monitor_dir_grant_accept_addr ;
logic  monitor_dir_grant_accept_dst ;
coherence_protocol_pkg::grant_opcode_t  monitor_dir_grant_accept_opcode ;
logic [4-1:0] monitor_dir_grant_accept_txn_id ;
logic  monitor_l2_fill_active ;
logic  monitor_l2_line_wr_valid ;
logic  monitor_l2_line_wr_ready ;
logic [31:0] monitor_l2_line_wr_addr ;
logic [2:0] monitor_l2_line_wr_beat ;
logic  monitor_dir_snoop_data_to_l2 ;
logic  monitor_dir_snoop_valid ;
logic  monitor_snoop_set_conflict ;
logic [4:0] monitor_engine_state ;
logic [31:0] monitor_engine_addr ;
logic [31:0] monitor_victim_addr ;
logic [1:0] monitor_victim_pending_targets ;
logic  monitor_victim_target ;
logic [1:0] monitor_snoop_offer_valid ;
logic [1:0] monitor_snoop_offer_ready ;
logic [4-1:0] monitor_mem_mshr_valid ;
logic [4-1:0] monitor_directory_active_contexts ;
logic  monitor_dir_req_live_valid ;
logic  monitor_dir_req_live_ready ;
logic [31:0] monitor_dir_req_live_addr ;
logic  monitor_dir_xfer_live_valid ;
logic  monitor_dir_xfer_live_ready ;
logic [5:0] monitor_cpu_state ;
logic [5:0] monitor_l1_snoop_state ;
logic [63:0] monitor_cpu_active_addr ;
logic [7:0] monitor_l1_replace_state ;
logic reset;logic [1:0] init_count=0;
assign reset=init_count<2 || reset_later;
CoherentCacheSubsystem dut(.*);
always @(posedge clock) begin
 if(init_count<2)init_count<=init_count+1'b1;
 if(init_count>=2 && !reset) begin
  cover(dut.directory_controller.monitor_active_contexts[2]);
  cover(dut.directory_controller.monitor_active_contexts[3]);
 end
end
endmodule
