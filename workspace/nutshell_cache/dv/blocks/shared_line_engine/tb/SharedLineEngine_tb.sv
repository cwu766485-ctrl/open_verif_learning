`timescale 1ns/1ps
module SharedLineEngine_tb;
  import coherence_protocol_pkg::*;

  localparam logic [4:0] ENGINE_IDLE = 5'd0;
  localparam logic [4:0] ENGINE_VICTIM_READ = 5'd1;
  localparam logic [4:0] ENGINE_VICTIM_WRITE_REQ = 5'd2;
  localparam logic [4:0] ENGINE_VICTIM_WRITE_STREAM = 5'd3;
  localparam logic [4:0] ENGINE_VICTIM_WRITE_WAIT_RSP = 5'd4;
  localparam logic [4:0] ENGINE_VICTIM_MARK_CLEAN = 5'd5;
  localparam logic [4:0] ENGINE_VICTIM_INVALIDATE = 5'd6;
  localparam logic [4:0] ENGINE_MEM_REQ = 5'd8;
  localparam logic [4:0] ENGINE_GRANT_READ = 5'd10;
  localparam logic [4:0] ENGINE_GRANT_STREAM = 5'd11;
  localparam logic [4:0] ENGINE_VICTIM_SNOOP_SEND = 5'd12;
  localparam logic [4:0] ENGINE_VICTIM_SNOOP_WAIT = 5'd13;
  localparam logic [4:0] ENGINE_VICTIM_CLEAR_DIR = 5'd14;
  localparam logic [4:0] ENGINE_PUTM_STREAM = 5'd7;
  localparam logic [4:0] ENGINE_XFER_DONE = 5'd9;
  localparam logic [4:0] ENGINE_ERROR = 5'd15;

  logic clock = 1'b0;
  logic reset;
  logic mem_r_protocol_bad, mem_rd_data_valid, mem_rd_data_ready;
  logic mem_rd_data_error, mem_mshr_r_match;
  logic mem_wr_rsp_valid, mem_wr_rsp_ready;
  logic [TXN_ID_WIDTH-1:0] mem_wr_rsp_txn_id;
  logic mem_wr_rsp_error;
  logic dir_xfer_start_valid, dir_xfer_start_ready;
  line_xfer_kind_t dir_xfer_kind;
  logic [31:0] dir_xfer_addr;
  logic dir_xfer_src;
  logic [TXN_ID_WIDTH-1:0] dir_xfer_txn_id;
  logic [1:0] dir_xfer_context_id;
  logic dir_xfer_done_valid, dir_xfer_done_ready;
  logic dir_grant_valid, dir_grant_ready, dir_grant_dst, dir_grant_has_data;
  logic [31:0] dir_grant_addr;
  logic [TXN_ID_WIDTH-1:0] dir_grant_txn_id;
  logic l2_lookup_hit, l2_alloc_victim_valid, l2_alloc_victim_dirty;
  logic [31:0] l2_alloc_victim_addr;
  directory_state_t l2_alloc_victim_state;
  logic [1:0] l2_alloc_victim_sharers;
  logic l2_alloc_victim_owner;
  logic l2_line_rd_valid, l2_line_rd_ready, l2_line_rd_hit;
  logic l2_line_data_valid, l2_line_data_ready, l2_line_data_last;
  logic l2_line_wr_valid, l2_line_wr_ready;
  logic [2:0] l2_line_wr_beat_idx;
  logic l2_line_wr_last;
  logic l2_entry_invalidate_valid, l2_entry_invalidate_ready;
  logic l2_mark_clean_valid, l2_mark_clean_ready, l2_dir_write_ready;
  logic mem_rd_req_valid, mem_rd_req_ready;
  logic mem_wr_req_valid, mem_wr_req_ready;
  logic mem_wr_data_valid, mem_wr_data_ready;
  logic [2:0] mem_wr_data_beat_idx;
  logic mem_wr_data_last;
  logic snoop_valid_core [0:1];
  logic snoop_ready_core [0:1];
  logic snoop_rsp_has_data_core [0:1];
  logic [TXN_ID_WIDTH-1:0] snoop_rsp_txn_id_core [0:1];
  snoop_response_t snoop_rsp_opcode_core [0:1];
  logic [TXN_ID_WIDTH-1:0] snoop_data_txn_id_core [0:1];
  logic victim_snoop_data_to_l2, victim_snoop_rsp_fire;
  logic [1:0] victim_targets_after_current;
  logic victim_owner_retired_before_snoop;

  logic [4:0] engine_state_q;
  logic [31:0] engine_addr_q;
  logic [TXN_ID_WIDTH-1:0] engine_txn_q;
  logic [1:0] engine_context_q;
  logic engine_src_q;
  logic [2:0] mem_expected_beat_q, victim_expected_beat_q;
  logic [31:0] victim_addr_q;
  logic [1:0] victim_pending_targets_q;
  logic victim_snoop_target_q, victim_snoop_data_expected_q;
  logic victim_snoop_data_complete_q, victim_dirty_q, grant_dst_q;
  logic [31:0] grant_addr_q;
  logic [TXN_ID_WIDTH-1:0] grant_txn_q;
  logic memory_adapter_protocol_error, memory_adapter_error;

  always #5 clock = ~clock;

  SharedLineEngine #(.TXN_ID_WIDTH(TXN_ID_WIDTH), .NUM_MSHRS(4)) dut (
    .clock, .reset,
    .mem_r_protocol_bad, .mem_rd_data_valid, .mem_rd_data_ready,
    .mem_rd_data_error, .mem_mshr_r_match,
    .mem_wr_rsp_valid, .mem_wr_rsp_ready, .mem_wr_rsp_txn_id,
    .mem_wr_rsp_error,
    .dir_xfer_start_valid, .dir_xfer_start_ready, .dir_xfer_kind,
    .dir_xfer_addr, .dir_xfer_src, .dir_xfer_txn_id, .dir_xfer_context_id,
    .dir_xfer_done_valid, .dir_xfer_done_ready,
    .dir_grant_valid, .dir_grant_ready, .dir_grant_dst,
    .dir_grant_has_data, .dir_grant_addr, .dir_grant_txn_id,
    .l2_lookup_hit, .l2_alloc_victim_valid, .l2_alloc_victim_addr,
    .l2_alloc_victim_dirty, .l2_alloc_victim_state,
    .l2_alloc_victim_sharers, .l2_alloc_victim_owner,
    .l2_line_rd_valid, .l2_line_rd_ready, .l2_line_rd_hit,
    .l2_line_data_valid, .l2_line_data_ready, .l2_line_data_last,
    .l2_line_wr_valid, .l2_line_wr_ready, .l2_line_wr_beat_idx,
    .l2_line_wr_last, .l2_entry_invalidate_valid,
    .l2_entry_invalidate_ready, .l2_mark_clean_valid,
    .l2_mark_clean_ready, .l2_dir_write_ready,
    .mem_rd_req_valid, .mem_rd_req_ready, .mem_wr_req_valid,
    .mem_wr_req_ready, .mem_wr_data_valid, .mem_wr_data_ready,
    .mem_wr_data_beat_idx, .mem_wr_data_last,
    .snoop_valid_core, .snoop_ready_core, .snoop_rsp_has_data_core,
    .snoop_rsp_txn_id_core, .snoop_rsp_opcode_core,
    .snoop_data_txn_id_core, .victim_snoop_data_to_l2,
    .victim_snoop_rsp_fire, .victim_targets_after_current,
    .victim_owner_retired_before_snoop,
    .engine_state_q, .engine_addr_q, .engine_txn_q, .engine_context_q,
    .engine_src_q, .mem_expected_beat_q, .victim_expected_beat_q,
    .victim_addr_q, .victim_pending_targets_q, .victim_snoop_target_q,
    .victim_snoop_data_expected_q, .victim_snoop_data_complete_q,
    .victim_dirty_q, .grant_dst_q, .grant_addr_q, .grant_txn_q,
    .memory_adapter_protocol_error, .memory_adapter_error
  );

  `include "include/engine_test_tasks.svh"
  `include "include/engine_grant_cases.svh"
  `include "include/engine_xfer_cases.svh"
  `include "include/engine_clean_victim_case.svh"
  `include "include/engine_dirty_owner_case.svh"
  `include "include/engine_fault_cases.svh"

  initial begin
    initialize_inputs();
    reset_dut();
    test_grant_read_backpressure();
    reset_dut();
    test_grant_immediate_l2_hit();
    reset_dut();
    test_grant_immediate_l2_miss_fault();
    reset_dut();
    test_grant_read_miss_fault();
    reset_dut();
    test_refill_hit_and_cold_miss();
    reset_dut();
    test_putm_stream();
    reset_dut();
    test_putm_malformed_beat();
    reset_dut();
    test_clean_invalid_victim();
    reset_dut();
    test_clean_shared_victim_reclaim();
    reset_dut();
    test_dirty_owner_victim_writeback();
    reset_dut();
    test_memory_protocol_faults();
    test_dirty_writeback_faults();
    $display("PASS: SharedLineEngine grant, victim reclaim/writeback and fault cases");
    $finish;
  end
endmodule
