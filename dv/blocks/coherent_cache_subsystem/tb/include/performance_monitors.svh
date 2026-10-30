  always @(posedge clock) begin
    if (!reset) begin
      for (integer core = 0; core < 2; core = core + 1) begin
        if (metadata_commit_valid[core]) begin
          metadata_commit_count <= metadata_commit_count + 1;
          if (metadata_commit_line_addr[core][5:0] != 6'b0)
            $fatal(1, "metadata commit address is not line aligned: %08x",
                   metadata_commit_line_addr[core]);
          case (metadata_commit_state[core])
            MESI_I, MESI_S, MESI_E, MESI_M: begin end
            default: $fatal(1, "invalid committed MESI state for core %0d", core);
          endcase
          if (metadata_commit_is_snoop[core])
            metadata_snoop_commit_count <= metadata_snoop_commit_count + 1;
        end
      end
    end
  end
  logic [4:0] performance_events_seen = 5'b0;

  always_ff @(posedge clock) begin
    if (|perf_hit_event) performance_events_seen[0] <= 1'b1;
    if (|perf_miss_event) performance_events_seen[1] <= 1'b1;
    if (|perf_snoop_event) performance_events_seen[2] <= 1'b1;
    if (perf_dirty_writeback_event) performance_events_seen[3] <= 1'b1;
    if (|perf_access_complete_event) performance_events_seen[4] <= 1'b1;
  end

  logic [3:0] memory_active_q;
  logic memory_read_valid_held_q;
  integer memory_read_hold_slot_q;
  integer memory_read_pick_q;
  logic [2:0] memory_beat_q [0:3];
  logic [31:0] memory_line_addr_q [0:3];
  logic [TXN_ID_WIDTH-1:0] memory_txn_q [0:3];
  logic memory_error_q [0:3];
  integer memory_response_slot;
  integer memory_free_slot;
  integer memory_read_candidate;
  logic memory_write_response_pending_q;
  logic [TXN_ID_WIDTH-1:0] memory_write_response_txn_q;
  logic memory_write_response_error_q;
  logic inject_next_mem_rd_error;
  logic inject_next_mem_wr_error;
  logic memory_slot_valid [0:127];
  logic [31:0] memory_slot_addr [0:127];
  logic [63:0] backing_store [0:127][0:7];
  logic [63:0] staged_write_data_q [0:7];
  logic [6:0] memory_write_slot_q;
  logic [TXN_ID_WIDTH-1:0] memory_write_txn_q;
  logic [31:0] memory_write_addr_q;
  logic [31:0] mmio_saved_addr_q;
  logic [63:0] mmio_saved_data_q;
  logic mmio_saved_valid_q;
  logic mmio_response_valid_q;
  logic [63:0] mmio_response_data_q;
  integer mmio_response_delay_q;
  logic stall_mem_rd_req;
  logic stall_mem_wr_req;
  logic stall_mem_wr_data;
  logic stall_mmio_req;
  logic inject_periodic_stalls;
  integer cycle_count;
  integer memory_write_expected_beat_q;
  localparam int DATA_MODEL_ENTRIES = 256;
  logic [31:0] reference_addr [0:DATA_MODEL_ENTRIES-1];
  logic [63:0] reference_data [0:DATA_MODEL_ENTRIES-1];
  logic reference_valid [0:DATA_MODEL_ENTRIES-1];
  integer reference_entries;
  localparam int STATE_MODEL_ENTRIES = 256;
  logic state_model_valid [0:STATE_MODEL_ENTRIES-1];
  logic [31:0] state_model_line [0:STATE_MODEL_ENTRIES-1];
  mesi_state_t state_model_mesi [0:STATE_MODEL_ENTRIES-1][0:1];
  integer state_model_entries_used = 0;
  logic benchmark_accept_pending [0:1];
  logic benchmark_accept_write [0:1];
  mesi_state_t benchmark_accept_state [0:1];
  integer benchmark_accept_cycle [0:1];
  integer benchmark_read_hit_count = 0;
  integer benchmark_read_hit_cycles = 0;
  integer benchmark_write_hit_count = 0;
  integer benchmark_write_hit_cycles = 0;
  integer benchmark_upgrade_count = 0;
  integer benchmark_upgrade_cycles = 0;
  integer benchmark_l1_miss_count = 0;
  integer benchmark_l1_miss_cycles = 0;
  integer benchmark_request_ready_stall_cycles = 0;
  integer benchmark_model_accept_hit_count = 0;
  integer benchmark_model_accept_miss_count = 0;
  integer benchmark_rtl_hit_count = 0;
  integer benchmark_rtl_miss_count = 0;
  integer benchmark_snoop_count = 0;
  integer benchmark_snoop_cycles = 0;
  logic [1:0] stalled_cpu_req_q;
  logic [1:0] stalled_cpu_resp_q;
  logic [31:0] cpu_req_addr_hold_q [0:1];
  logic [31:0] cpu_resp_addr_hold_q [0:1];
  logic cpu_req_write_hold_q [0:1];
  logic cpu_resp_write_hold_q [0:1];
  logic [7:0] cpu_req_wmask_hold_q [0:1];
  logic [63:0] cpu_req_wdata_hold_q [0:1];
  logic [63:0] cpu_resp_rdata_hold_q [0:1];
  logic [TXN_ID_WIDTH-1:0] cpu_resp_txn_hold_q [0:1];
  logic stalled_mmio_req_q;
  logic stalled_mmio_resp_q;
  logic [31:0] mmio_addr_hold_q;
  logic [2:0] mmio_size_hold_q;
  logic mmio_write_hold_q;
  logic [7:0] mmio_wmask_hold_q;
  logic [63:0] mmio_wdata_hold_q;
  logic [63:0] mmio_resp_data_hold_q;
  logic stalled_mem_rd_req_q;
  logic stalled_mem_rd_data_q;
  logic stalled_mem_wr_req_q;
  logic stalled_mem_wr_data_q;
  logic [31:0] mem_rd_addr_hold_q;
  logic [TXN_ID_WIDTH-1:0] mem_rd_txn_hold_q;
  logic [TXN_ID_WIDTH-1:0] mem_rd_data_txn_hold_q;
  logic [2:0] mem_rd_data_beat_hold_q;
  logic [63:0] mem_rd_data_hold_q;
  logic mem_rd_data_last_hold_q;
  logic mem_rd_data_error_hold_q;
  logic [31:0] mem_wr_addr_hold_q;
  logic [TXN_ID_WIDTH-1:0] mem_wr_txn_hold_q;
  logic [TXN_ID_WIDTH-1:0] mem_wr_data_txn_hold_q;
  logic [2:0] mem_wr_data_beat_hold_q;
  logic [63:0] mem_wr_data_hold_q;
  logic mem_wr_data_last_hold_q;
  logic stalled_dir_req_q;
  logic dir_req_src_hold_q;
  request_opcode_t dir_req_opcode_hold_q;
  logic [31:0] dir_req_addr_hold_q;
  logic [TXN_ID_WIDTH-1:0] dir_req_txn_hold_q;
  logic stalled_snoop_q;
  logic snoop_target_hold_q;
  snoop_opcode_t snoop_opcode_hold_q;
  logic [31:0] snoop_addr_hold_q;
  logic [TXN_ID_WIDTH-1:0] snoop_txn_hold_q;
  logic stalled_grant_q;
  logic grant_dst_hold_q;
  grant_opcode_t grant_opcode_hold_q;
  logic [31:0] grant_addr_hold_q;
  logic [TXN_ID_WIDTH-1:0] grant_txn_hold_q;
  logic stalled_l2_data_q;
  logic [2:0] l2_data_beat_hold_q;
  logic [63:0] l2_data_hold_q;
  logic l2_data_last_hold_q;
  logic stalled_l2_write_q;
  logic [31:0] l2_write_addr_hold_q;
  logic [2:0] l2_write_beat_hold_q;
  logic [63:0] l2_write_data_hold_q;
  logic l2_write_last_hold_q;
  integer cover_cpu_resp_stall = 0;
  integer cover_mmio_req_stall = 0;
  integer cover_mmio_resp_stall = 0;
  integer cover_mem_rd_req_stall = 0;
  integer cover_l2_fill_stall = 0;
  integer cover_mem_wr_req_stall = 0;
  integer cover_mem_wr_data_stall = 0;
  integer cover_dir_req_stall = 0;
  integer cover_reset_snoop_data = 0;
  integer cover_reset_mem_wr_data = 0;
  integer mmio_request_count;
  integer memory_read_count;
  logic saw_l2_live_victim_q;
  logic [31:0] observed_l2_live_victim_q;
  logic saw_l2_shared_victim_q;
  logic [31:0] observed_l2_shared_victim_q;
  logic [1:0] observed_l2_shared_sharers_q;

  always #5 clock = ~clock;
