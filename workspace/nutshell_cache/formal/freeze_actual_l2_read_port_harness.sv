// Actual production-default SharedL2DirectoryArray + SharedLineEngine.
// Main routing equations retained explicitly; no L2 busy recurrence model.
module FreezeActualL2ReadPortFormal(
  input logic clock,
  input logic mem_r_protocol_bad,
  input logic mem_rd_data_valid,
  input logic mem_rd_data_ready,
  input logic mem_rd_data_error,
  input logic mem_mshr_r_match,
  input logic mem_wr_rsp_valid,
  input logic mem_wr_rsp_ready,
  input logic [3:0] mem_wr_rsp_txn_id,
  input logic mem_wr_rsp_error,
  input logic dir_xfer_start_valid,
  input logic dir_xfer_start_ready,
  input coherence_protocol_pkg::line_xfer_kind_t dir_xfer_kind,
  input logic [31:0] dir_xfer_addr,
  input logic dir_xfer_src,
  input logic [3:0] dir_xfer_txn_id,
  input logic [1:0] dir_xfer_context_id,
  input logic dir_xfer_done_valid,
  input logic dir_xfer_done_ready,
  input logic dir_grant_valid,
  input logic dir_grant_dst,
  input logic dir_grant_has_data,
  input logic [31:0] dir_grant_addr,
  input logic [3:0] dir_grant_txn_id,
  input logic l2_lookup_hit,
  input logic l2_alloc_victim_valid,
  input logic [31:0] l2_alloc_victim_addr,
  input logic l2_alloc_victim_dirty,
  input coherence_protocol_pkg::directory_state_t l2_alloc_victim_state,
  input logic [1:0] l2_alloc_victim_sharers,
  input logic l2_alloc_victim_owner,
  input logic l2_line_wr_valid,
  input logic l2_line_wr_ready,
  input logic [2:0] l2_line_wr_beat_idx,
  input logic l2_line_wr_last,
  input logic l2_entry_invalidate_valid,
  input logic l2_entry_invalidate_ready,
  input logic l2_mark_clean_valid,
  input logic l2_mark_clean_ready,
  input logic l2_dir_write_ready,
  input logic mem_rd_req_valid,
  input logic mem_rd_req_ready,
  input logic mem_wr_req_valid,
  input logic mem_wr_req_ready,
  input logic mem_wr_data_ready,
  input logic snoop_valid_core [0:1],
  input logic snoop_ready_core [0:1],
  input logic snoop_rsp_has_data_core [0:1],
  input logic [3:0] snoop_rsp_txn_id_core [0:1],
  input coherence_protocol_pkg::snoop_response_t snoop_rsp_opcode_core [0:1],
  input logic [3:0] snoop_data_txn_id_core [0:1],
  input logic victim_snoop_data_to_l2,
  input logic victim_snoop_rsp_fire,
  input logic [1:0] victim_targets_after_current,
  input logic victim_owner_retired_before_snoop,
  input logic reset_later,
  input logic grant_ready_sink,
  input logic stream_ready,
  input logic [31:0] array_lookup_addr,
  input logic array_dir_write_valid,
  input logic [31:0] array_dir_write_line_addr,
  input coherence_protocol_pkg::directory_state_t array_dir_write_state,
  input logic [1:0] array_dir_write_sharers,
  input logic array_dir_write_owner_id,
  input logic [31:0] array_alloc_addr,
  input logic array_entry_invalidate_valid,
  input logic [31:0] array_entry_invalidate_line_addr,
  input logic array_mark_clean_valid,
  input logic [31:0] array_mark_clean_line_addr,
  input logic array_line_wr_valid,
  input logic [31:0] array_line_wr_addr,
  input logic array_line_wr_dirty,
  input logic [2:0] array_line_wr_beat_idx,
  input logic [63:0] array_line_wr_data,
  input logic array_line_wr_last,
  input logic [31:0] array_line_rd_addr
);
  import coherence_protocol_pkg::*;
  localparam TXN_ID_WIDTH=4, NUM_MSHRS=4, MSHR_ID_WIDTH=2;
  logic reset;
  logic mem_wr_data_valid, mem_wr_data_last;
  logic [2:0] mem_wr_data_beat_idx;
  logic dir_grant_ready;
  logic l2_line_rd_valid;
  logic l2_line_rd_ready;
  logic l2_line_data_valid;
  logic l2_line_data_ready;
  logic l2_line_data_last;
  logic [4:0] engine_state_q;
  logic [31:0] engine_addr_q;
  logic [TXN_ID_WIDTH-1:0] engine_txn_q;
  logic [MSHR_ID_WIDTH-1:0] engine_context_q;
  logic engine_src_q;
  logic [2:0] mem_expected_beat_q;
  logic [2:0] victim_expected_beat_q;
  logic [31:0] victim_addr_q;
  logic [1:0] victim_pending_targets_q;
  logic victim_snoop_target_q;
  logic victim_snoop_data_expected_q;
  logic victim_snoop_data_complete_q;
  logic victim_dirty_q;
  logic grant_dst_q;
  logic [31:0] grant_addr_q;
  logic [TXN_ID_WIDTH-1:0] grant_txn_q;
  logic memory_adapter_protocol_error;
  logic memory_adapter_error;
  logic [1:0] init_count=0;
  logic busy;
  logic [2:0] beat;
  logic l2_line_rd_hit;
  assign mem_wr_data_valid = !reset && engine_state_q==3 && busy;
  assign mem_wr_data_beat_idx = beat;
  assign mem_wr_data_last = beat==7;
  assign reset = init_count<2 || reset_later;
  assign dir_grant_ready = grant_ready_sink &&
    (!dir_grant_has_data || (engine_state_q==0 && !dir_xfer_start_valid));
  assign l2_line_rd_valid = engine_state_q==10 || engine_state_q==1 ||
    (engine_state_q==0 && dir_grant_valid && dir_grant_ready && dir_grant_has_data);



  assign l2_line_data_ready = (engine_state_q==11 || engine_state_q==3) && (engine_state_q==3 ? mem_wr_data_ready : stream_ready);
  logic array_lookup_hit;
  logic [3-1:0] array_lookup_way;
  coherence_protocol_pkg::directory_state_t array_lookup_dir_state;
  logic [1:0] array_lookup_sharers;
  logic array_lookup_owner_id;
  logic array_dir_write_ready;
  logic array_alloc_victim_valid;
  logic [3-1:0] array_alloc_way;
  logic [31:0] array_alloc_victim_addr;
  coherence_protocol_pkg::directory_state_t array_alloc_victim_dir_state;
  logic [1:0] array_alloc_victim_sharers;
  logic array_alloc_victim_owner_id;
  logic array_alloc_victim_dirty;
  logic array_entry_invalidate_ready;
  logic array_mark_clean_ready;
  logic array_line_wr_ready;
  logic [63:0] array_line_data;
  logic array_protocol_error;
  assign busy = l2_line_data_valid;
  SharedL2DirectoryArray array_dut (
    .clock(clock),
    .reset(reset),
    .lookup_addr(array_lookup_addr),
    .lookup_hit(array_lookup_hit),
    .lookup_way(array_lookup_way),
    .lookup_dir_state(array_lookup_dir_state),
    .lookup_sharers(array_lookup_sharers),
    .lookup_owner_id(array_lookup_owner_id),
    .dir_write_valid(array_dir_write_valid),
    .dir_write_ready(array_dir_write_ready),
    .dir_write_line_addr(array_dir_write_line_addr),
    .dir_write_state(array_dir_write_state),
    .dir_write_sharers(array_dir_write_sharers),
    .dir_write_owner_id(array_dir_write_owner_id),
    .alloc_addr(array_alloc_addr),
    .alloc_victim_valid(array_alloc_victim_valid),
    .alloc_way(array_alloc_way),
    .alloc_victim_addr(array_alloc_victim_addr),
    .alloc_victim_dir_state(array_alloc_victim_dir_state),
    .alloc_victim_sharers(array_alloc_victim_sharers),
    .alloc_victim_owner_id(array_alloc_victim_owner_id),
    .alloc_victim_dirty(array_alloc_victim_dirty),
    .entry_invalidate_valid(array_entry_invalidate_valid),
    .entry_invalidate_ready(array_entry_invalidate_ready),
    .entry_invalidate_line_addr(array_entry_invalidate_line_addr),
    .mark_clean_valid(array_mark_clean_valid),
    .mark_clean_ready(array_mark_clean_ready),
    .mark_clean_line_addr(array_mark_clean_line_addr),
    .line_wr_valid(array_line_wr_valid),
    .line_wr_ready(array_line_wr_ready),
    .line_wr_addr(array_line_wr_addr),
    .line_wr_dirty(array_line_wr_dirty),
    .line_wr_beat_idx(array_line_wr_beat_idx),
    .line_wr_data(array_line_wr_data),
    .line_wr_last(array_line_wr_last),
    .line_rd_valid(l2_line_rd_valid),
    .line_rd_ready(l2_line_rd_ready),
    .line_rd_addr(array_line_rd_addr),
    .line_rd_hit(l2_line_rd_hit),
    .line_data_valid(l2_line_data_valid),
    .line_data_ready(l2_line_data_ready),
    .line_data_beat_idx(beat),
    .line_data(array_line_data),
    .line_data_last(l2_line_data_last),
    .protocol_error(array_protocol_error)
  );
  // All non-routing environment inputs are symbolic, including malformed
  // responses. No assumptions exclude protocol errors or reset_after_init.
  SharedLineEngine dut (
    .clock(clock),
    .reset(reset),
    .mem_r_protocol_bad(mem_r_protocol_bad),
    .mem_rd_data_valid(mem_rd_data_valid),
    .mem_rd_data_ready(mem_rd_data_ready),
    .mem_rd_data_error(mem_rd_data_error),
    .mem_mshr_r_match(mem_mshr_r_match),
    .mem_wr_rsp_valid(mem_wr_rsp_valid),
    .mem_wr_rsp_ready(mem_wr_rsp_ready),
    .mem_wr_rsp_txn_id(mem_wr_rsp_txn_id),
    .mem_wr_rsp_error(mem_wr_rsp_error),
    .dir_xfer_start_valid(dir_xfer_start_valid),
    .dir_xfer_start_ready(dir_xfer_start_ready),
    .dir_xfer_kind(dir_xfer_kind),
    .dir_xfer_addr(dir_xfer_addr),
    .dir_xfer_src(dir_xfer_src),
    .dir_xfer_txn_id(dir_xfer_txn_id),
    .dir_xfer_context_id(dir_xfer_context_id),
    .dir_xfer_done_valid(dir_xfer_done_valid),
    .dir_xfer_done_ready(dir_xfer_done_ready),
    .dir_grant_valid(dir_grant_valid),
    .dir_grant_ready(dir_grant_ready),
    .dir_grant_dst(dir_grant_dst),
    .dir_grant_has_data(dir_grant_has_data),
    .dir_grant_addr(dir_grant_addr),
    .dir_grant_txn_id(dir_grant_txn_id),
    .l2_lookup_hit(l2_lookup_hit),
    .l2_alloc_victim_valid(l2_alloc_victim_valid),
    .l2_alloc_victim_addr(l2_alloc_victim_addr),
    .l2_alloc_victim_dirty(l2_alloc_victim_dirty),
    .l2_alloc_victim_state(l2_alloc_victim_state),
    .l2_alloc_victim_sharers(l2_alloc_victim_sharers),
    .l2_alloc_victim_owner(l2_alloc_victim_owner),
    .l2_line_rd_valid(l2_line_rd_valid),
    .l2_line_rd_ready(l2_line_rd_ready),
    .l2_line_rd_hit(l2_line_rd_hit),
    .l2_line_data_valid(l2_line_data_valid),
    .l2_line_data_ready(l2_line_data_ready),
    .l2_line_data_last(l2_line_data_last),
    .l2_line_wr_valid(l2_line_wr_valid),
    .l2_line_wr_ready(l2_line_wr_ready),
    .l2_line_wr_beat_idx(l2_line_wr_beat_idx),
    .l2_line_wr_last(l2_line_wr_last),
    .l2_entry_invalidate_valid(l2_entry_invalidate_valid),
    .l2_entry_invalidate_ready(l2_entry_invalidate_ready),
    .l2_mark_clean_valid(l2_mark_clean_valid),
    .l2_mark_clean_ready(l2_mark_clean_ready),
    .l2_dir_write_ready(l2_dir_write_ready),
    .mem_rd_req_valid(mem_rd_req_valid),
    .mem_rd_req_ready(mem_rd_req_ready),
    .mem_wr_req_valid(mem_wr_req_valid),
    .mem_wr_req_ready(mem_wr_req_ready),
    .mem_wr_data_valid(mem_wr_data_valid),
    .mem_wr_data_ready(mem_wr_data_ready),
    .mem_wr_data_beat_idx(mem_wr_data_beat_idx),
    .mem_wr_data_last(mem_wr_data_last),
    .snoop_valid_core(snoop_valid_core),
    .snoop_ready_core(snoop_ready_core),
    .snoop_rsp_has_data_core(snoop_rsp_has_data_core),
    .snoop_rsp_txn_id_core(snoop_rsp_txn_id_core),
    .snoop_rsp_opcode_core(snoop_rsp_opcode_core),
    .snoop_data_txn_id_core(snoop_data_txn_id_core),
    .victim_snoop_data_to_l2(victim_snoop_data_to_l2),
    .victim_snoop_rsp_fire(victim_snoop_rsp_fire),
    .victim_targets_after_current(victim_targets_after_current),
    .victim_owner_retired_before_snoop(victim_owner_retired_before_snoop),
    .engine_state_q(engine_state_q),
    .engine_addr_q(engine_addr_q),
    .engine_txn_q(engine_txn_q),
    .engine_context_q(engine_context_q),
    .engine_src_q(engine_src_q),
    .mem_expected_beat_q(mem_expected_beat_q),
    .victim_expected_beat_q(victim_expected_beat_q),
    .victim_addr_q(victim_addr_q),
    .victim_pending_targets_q(victim_pending_targets_q),
    .victim_snoop_target_q(victim_snoop_target_q),
    .victim_snoop_data_expected_q(victim_snoop_data_expected_q),
    .victim_snoop_data_complete_q(victim_snoop_data_complete_q),
    .victim_dirty_q(victim_dirty_q),
    .grant_dst_q(grant_dst_q),
    .grant_addr_q(grant_addr_q),
    .grant_txn_q(grant_txn_q),
    .memory_adapter_protocol_error(memory_adapter_protocol_error),
    .memory_adapter_error(memory_adapter_error));
  // Busy ownership and beat agreement are asserted induction lemmas, never
  // assumptions. ENGINE_ERROR may retain busy until reset; it is fail-stop.
  always @(posedge clock) begin
    if(init_count<2) init_count<=init_count+1'b1;
    if(init_count>=2 && !reset) begin
      assert(engine_state_q<=15);
      assert(!busy || engine_state_q==2 || engine_state_q==3 || engine_state_q==11 || engine_state_q==15);
      assert(engine_state_q!=3 || beat==victim_expected_beat_q);
      assert(engine_state_q!=2 || (beat==0 && victim_expected_beat_q==0));
      assert(engine_state_q!=10);
      assert(!(engine_state_q==0 && busy));
      assert(!(dir_grant_valid && dir_grant_ready && dir_grant_has_data && busy));
    end
  end
endmodule
