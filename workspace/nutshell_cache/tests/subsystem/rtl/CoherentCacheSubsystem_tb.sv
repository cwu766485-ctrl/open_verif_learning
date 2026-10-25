`timescale 1ns/1ps

module CoherentCacheSubsystem_tb;
  import coherence_protocol_pkg::*;
  localparam int MODEL_SLOTS = 4;

  logic clock = 1'b0;
  logic reset;

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

  logic mmio_req_valid;
  logic mmio_req_ready;
  logic [31:0] mmio_req_addr;
  logic [2:0] mmio_req_size;
  logic mmio_req_write;
  logic [7:0] mmio_req_wmask;
  logic [63:0] mmio_req_wdata;
  logic mmio_resp_valid;
  logic mmio_resp_ready;
  logic [63:0] mmio_resp_rdata;
  logic mmio_protocol_error;

  logic mem_rd_req_valid;
  logic mem_rd_req_ready;
  logic [31:0] mem_rd_req_addr;
  logic [TXN_ID_WIDTH-1:0] mem_rd_req_txn_id;
  logic mem_rd_data_valid;
  logic mem_rd_data_ready;
  logic [TXN_ID_WIDTH-1:0] mem_rd_data_txn_id;
  logic [2:0] mem_rd_data_beat_idx;
  logic [63:0] mem_rd_data;
  logic mem_rd_data_last;
  logic mem_rd_data_error;

  logic mem_wr_req_valid;
  logic mem_wr_req_ready;
  logic [31:0] mem_wr_req_addr;
  logic [TXN_ID_WIDTH-1:0] mem_wr_req_txn_id;
  logic mem_wr_data_valid;
  logic mem_wr_data_ready;
  logic [TXN_ID_WIDTH-1:0] mem_wr_data_txn_id;
  logic [2:0] mem_wr_data_beat_idx;
  logic [63:0] mem_wr_data;
  logic mem_wr_data_last;
  logic mem_wr_rsp_valid;
  logic mem_wr_rsp_ready;
  logic [TXN_ID_WIDTH-1:0] mem_wr_rsp_txn_id;
  logic mem_wr_rsp_error;

  logic l2_victim_valid;
  logic [31:0] l2_victim_addr;
  directory_state_t l2_victim_dir_state;
  logic [1:0] l2_victim_sharers;
  logic l2_victim_owner_id;
  logic l2_victim_dirty;
  logic [1:0] l1_victim_valid;
  logic [31:0] l1_victim_addr [0:1];
  mesi_state_t l1_victim_state [0:1];
  logic [1:0] l1_controller_protocol_error;
  logic [1:0] l1_array_protocol_error;
  logic directory_protocol_error;
  logic l2_protocol_error;
  logic memory_adapter_protocol_error;
  logic memory_adapter_error;
  logic fatal_error;
  logic [1:0] perf_hit_event;
  logic [1:0] perf_miss_event;
  logic [1:0] perf_snoop_event;
  logic perf_dirty_writeback_event;
  logic [1:0] perf_inflight;
  logic [1:0] perf_access_complete_event;
  logic metadata_commit_valid [0:1];
  logic [31:0] metadata_commit_line_addr [0:1];
  mesi_state_t metadata_commit_state [0:1];
  logic metadata_commit_is_snoop [0:1];
  logic monitor_snoop_accept_valid [0:1];
  logic [31:0] monitor_snoop_accept_addr [0:1];
  snoop_opcode_t monitor_snoop_accept_opcode [0:1];
  logic [TXN_ID_WIDTH-1:0] monitor_snoop_accept_txn_id [0:1];
  integer metadata_commit_count = 0;
  integer metadata_snoop_commit_count = 0;

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

  // Ready/valid protocol assertions. These deliberately check the integrated
  // subsystem boundary and both CPU response channels under actual stalls.
  always_ff @(posedge clock) begin : ready_valid_assertions
    if (reset) begin
      stalled_cpu_req_q <= '0;
      stalled_cpu_resp_q <= '0;
      stalled_mmio_req_q <= 1'b0;
      stalled_mmio_resp_q <= 1'b0;
      stalled_mem_rd_req_q <= 1'b0;
      stalled_mem_rd_data_q <= 1'b0;
      stalled_mem_wr_req_q <= 1'b0;
      stalled_mem_wr_data_q <= 1'b0;
      stalled_dir_req_q <= 1'b0;
      stalled_snoop_q <= 1'b0;
      stalled_grant_q <= 1'b0;
      stalled_l2_data_q <= 1'b0;
      stalled_l2_write_q <= 1'b0;
      for (integer core = 0; core < 2; core = core + 1) begin
        cpu_req_addr_hold_q[core] <= '0;
        cpu_req_write_hold_q[core] <= 1'b0;
        cpu_req_wmask_hold_q[core] <= '0;
        cpu_req_wdata_hold_q[core] <= '0;
        cpu_resp_addr_hold_q[core] <= '0;
        cpu_resp_write_hold_q[core] <= 1'b0;
        cpu_resp_rdata_hold_q[core] <= '0;
        cpu_resp_txn_hold_q[core] <= '0;
      end
      mmio_addr_hold_q <= '0;
      mmio_size_hold_q <= '0;
      mmio_write_hold_q <= 1'b0;
      mmio_wmask_hold_q <= '0;
      mmio_wdata_hold_q <= '0;
      mmio_resp_data_hold_q <= '0;
      mem_rd_addr_hold_q <= '0;
      mem_rd_txn_hold_q <= '0;
      mem_rd_data_txn_hold_q <= '0;
      mem_rd_data_beat_hold_q <= '0;
      mem_rd_data_hold_q <= '0;
      mem_rd_data_last_hold_q <= 1'b0;
      mem_rd_data_error_hold_q <= 1'b0;
      mem_wr_addr_hold_q <= '0;
      mem_wr_txn_hold_q <= '0;
      mem_wr_data_txn_hold_q <= '0;
      mem_wr_data_beat_hold_q <= '0;
      mem_wr_data_hold_q <= '0;
      mem_wr_data_last_hold_q <= 1'b0;
      dir_req_src_hold_q <= 1'b0;
      dir_req_opcode_hold_q <= REQ_GETS;
      dir_req_addr_hold_q <= '0;
      dir_req_txn_hold_q <= '0;
      snoop_target_hold_q <= 1'b0;
      snoop_opcode_hold_q <= SNOOP_READ;
      snoop_addr_hold_q <= '0;
      snoop_txn_hold_q <= '0;
      grant_dst_hold_q <= 1'b0;
      grant_opcode_hold_q <= GRANT_DATA_S;
      grant_addr_hold_q <= '0;
      grant_txn_hold_q <= '0;
      l2_data_beat_hold_q <= '0;
      l2_data_hold_q <= '0;
      l2_data_last_hold_q <= 1'b0;
      l2_write_addr_hold_q <= '0;
      l2_write_beat_hold_q <= '0;
      l2_write_data_hold_q <= '0;
      l2_write_last_hold_q <= 1'b0;
    end else begin
      for (integer core = 0; core < 2; core = core + 1) begin
        if (stalled_cpu_req_q[core])
          assert (cpu_req_ready[core] || (cpu_req_valid[core] &&
                  cpu_req_addr[core] == cpu_req_addr_hold_q[core] &&
                  cpu_req_write[core] == cpu_req_write_hold_q[core] &&
                  cpu_req_wmask[core] == cpu_req_wmask_hold_q[core] &&
                  cpu_req_wdata[core] == cpu_req_wdata_hold_q[core]))
            else $fatal(1, "CPU%0d request changed while stalled", core);
        if (stalled_cpu_resp_q[core])
          assert (cpu_resp_ready[core] || (cpu_resp_valid[core] &&
                  cpu_resp_addr[core] == cpu_resp_addr_hold_q[core] &&
                  cpu_resp_write[core] == cpu_resp_write_hold_q[core] &&
                  cpu_resp_rdata[core] == cpu_resp_rdata_hold_q[core] &&
                  cpu_resp_txn_id[core] == cpu_resp_txn_hold_q[core]))
            else $fatal(1, "CPU%0d response changed while stalled: valid=%b/%b addr=%08x/%08x write=%b/%b data=%016x/%016x txn=%0h/%0h",
                        core, cpu_resp_valid[core], stalled_cpu_resp_q[core],
                        cpu_resp_addr[core], cpu_resp_addr_hold_q[core],
                        cpu_resp_write[core], cpu_resp_write_hold_q[core],
                        cpu_resp_rdata[core], cpu_resp_rdata_hold_q[core],
                        cpu_resp_txn_id[core], cpu_resp_txn_hold_q[core]);
        stalled_cpu_req_q[core] <= cpu_req_valid[core] && !cpu_req_ready[core];
        cpu_req_addr_hold_q[core] <= cpu_req_addr[core];
        cpu_req_write_hold_q[core] <= cpu_req_write[core];
        cpu_req_wmask_hold_q[core] <= cpu_req_wmask[core];
        cpu_req_wdata_hold_q[core] <= cpu_req_wdata[core];
        stalled_cpu_resp_q[core] <= cpu_resp_valid[core] && !cpu_resp_ready[core];
        cpu_resp_addr_hold_q[core] <= cpu_resp_addr[core];
        cpu_resp_write_hold_q[core] <= cpu_resp_write[core];
        cpu_resp_rdata_hold_q[core] <= cpu_resp_rdata[core];
        cpu_resp_txn_hold_q[core] <= cpu_resp_txn_id[core];
      end

      if (stalled_mmio_req_q)
        assert (mmio_req_ready || (mmio_req_valid && mmio_req_addr == mmio_addr_hold_q &&
                mmio_req_size == mmio_size_hold_q &&
                mmio_req_write == mmio_write_hold_q &&
                mmio_req_wmask == mmio_wmask_hold_q &&
                mmio_req_wdata == mmio_wdata_hold_q))
          else $fatal(1, "MMIO request changed while stalled");
      if (stalled_mmio_resp_q)
        assert (mmio_resp_ready ||
                (mmio_resp_valid && mmio_resp_rdata == mmio_resp_data_hold_q))
          else $fatal(1, "MMIO response changed while stalled");
      stalled_mmio_req_q <= mmio_req_valid && !mmio_req_ready;
      mmio_addr_hold_q <= mmio_req_addr;
      mmio_size_hold_q <= mmio_req_size;
      mmio_write_hold_q <= mmio_req_write;
      mmio_wmask_hold_q <= mmio_req_wmask;
      mmio_wdata_hold_q <= mmio_req_wdata;
      stalled_mmio_resp_q <= mmio_resp_valid && !mmio_resp_ready;
      mmio_resp_data_hold_q <= mmio_resp_rdata;

      if (stalled_dir_req_q)
        assert (dut.dir_req_ready || (dut.cluster_dir_req_valid &&
                dut.cluster_dir_req_src_id == dir_req_src_hold_q &&
                dut.cluster_dir_req_opcode == dir_req_opcode_hold_q &&
                dut.cluster_dir_req_addr == dir_req_addr_hold_q &&
                dut.cluster_dir_req_txn_id == dir_req_txn_hold_q))
          else $fatal(1, "arbiter request changed while Directory was stalled");
      if (stalled_snoop_q)
        assert (dut.dir_snoop_ready || (dut.dir_snoop_valid && dut.dir_snoop_target == snoop_target_hold_q &&
                dut.dir_snoop_opcode == snoop_opcode_hold_q &&
                dut.dir_snoop_addr == snoop_addr_hold_q &&
                dut.dir_snoop_txn_id == snoop_txn_hold_q))
          else $fatal(1, "Directory snoop changed while L1 was stalled");
      if (stalled_grant_q)
        assert (dut.dir_grant_ready || (dut.dir_grant_valid && dut.dir_grant_dst == grant_dst_hold_q &&
                dut.dir_grant_opcode == grant_opcode_hold_q &&
                dut.dir_grant_addr == grant_addr_hold_q &&
                dut.dir_grant_txn_id == grant_txn_hold_q))
          else $fatal(1, "Directory grant changed while L1 was stalled");
      if (stalled_l2_data_q)
        assert (dut.l2_line_data_ready || (dut.l2_line_data_valid &&
                dut.l2_line_data_beat_idx == l2_data_beat_hold_q &&
                dut.l2_line_data == l2_data_hold_q &&
                dut.l2_line_data_last == l2_data_last_hold_q))
          else $fatal(1, "L2 line data changed while destination was stalled");
      if (stalled_l2_write_q)
        assert (dut.l2_line_wr_ready || (dut.l2_line_wr_valid && dut.l2_line_wr_addr == l2_write_addr_hold_q &&
                dut.l2_line_wr_beat_idx == l2_write_beat_hold_q &&
                dut.l2_line_wr_data == l2_write_data_hold_q &&
                dut.l2_line_wr_last == l2_write_last_hold_q))
          else $fatal(1, "L2 line write changed while array was stalled");
      stalled_dir_req_q <= dut.cluster_dir_req_valid && !dut.dir_req_ready;
      dir_req_src_hold_q <= dut.cluster_dir_req_src_id;
      dir_req_opcode_hold_q <= dut.cluster_dir_req_opcode;
      dir_req_addr_hold_q <= dut.cluster_dir_req_addr;
      dir_req_txn_hold_q <= dut.cluster_dir_req_txn_id;
      stalled_snoop_q <= dut.dir_snoop_valid && !dut.dir_snoop_ready;
      snoop_target_hold_q <= dut.dir_snoop_target;
      snoop_opcode_hold_q <= dut.dir_snoop_opcode;
      snoop_addr_hold_q <= dut.dir_snoop_addr;
      snoop_txn_hold_q <= dut.dir_snoop_txn_id;
      stalled_grant_q <= dut.dir_grant_valid && !dut.dir_grant_ready;
      grant_dst_hold_q <= dut.dir_grant_dst;
      grant_opcode_hold_q <= dut.dir_grant_opcode;
      grant_addr_hold_q <= dut.dir_grant_addr;
      grant_txn_hold_q <= dut.dir_grant_txn_id;
      stalled_l2_data_q <= dut.l2_line_data_valid && !dut.l2_line_data_ready;
      l2_data_beat_hold_q <= dut.l2_line_data_beat_idx;
      l2_data_hold_q <= dut.l2_line_data;
      l2_data_last_hold_q <= dut.l2_line_data_last;
      stalled_l2_write_q <= dut.l2_line_wr_valid && !dut.l2_line_wr_ready;
      l2_write_addr_hold_q <= dut.l2_line_wr_addr;
      l2_write_beat_hold_q <= dut.l2_line_wr_beat_idx;
      l2_write_data_hold_q <= dut.l2_line_wr_data;
      l2_write_last_hold_q <= dut.l2_line_wr_last;

      if (cpu_resp_valid[0] && !cpu_resp_ready[0])
        cover_cpu_resp_stall <= cover_cpu_resp_stall + 1;
      if (mmio_req_valid && !mmio_req_ready)
        cover_mmio_req_stall <= cover_mmio_req_stall + 1;
      if (mmio_resp_valid && !mmio_resp_ready)
        cover_mmio_resp_stall <= cover_mmio_resp_stall + 1;
      if (mem_rd_req_valid && !mem_rd_req_ready)
        cover_mem_rd_req_stall <= cover_mem_rd_req_stall + 1;
      if (dut.mem_fill_writer_active_q && !dut.l2_line_wr_ready)
        cover_l2_fill_stall <= cover_l2_fill_stall + 1;
      if (mem_wr_req_valid && !mem_wr_req_ready)
        cover_mem_wr_req_stall <= cover_mem_wr_req_stall + 1;
      if (mem_wr_data_valid && !mem_wr_data_ready)
        cover_mem_wr_data_stall <= cover_mem_wr_data_stall + 1;
      if (dut.cluster_dir_req_valid && !dut.dir_req_ready)
        cover_dir_req_stall <= cover_dir_req_stall + 1;

      if (stalled_mem_rd_req_q)
        assert (mem_rd_req_ready ||
                (mem_rd_req_valid && mem_rd_req_addr == mem_rd_addr_hold_q &&
                 mem_rd_req_txn_id == mem_rd_txn_hold_q))
          else $fatal(1, "memory read request changed while stalled");
      if (stalled_mem_rd_data_q)
        assert (mem_rd_data_ready ||
                (mem_rd_data_valid && mem_rd_data_txn_id == mem_rd_data_txn_hold_q &&
                 mem_rd_data_beat_idx == mem_rd_data_beat_hold_q &&
                 mem_rd_data == mem_rd_data_hold_q &&
                 mem_rd_data_last == mem_rd_data_last_hold_q &&
                 mem_rd_data_error == mem_rd_data_error_hold_q))
          else $fatal(1, "memory read beat changed while stalled");
      if (stalled_mem_wr_req_q)
        assert (mem_wr_req_ready ||
                (mem_wr_req_valid && mem_wr_req_addr == mem_wr_addr_hold_q &&
                 mem_wr_req_txn_id == mem_wr_txn_hold_q))
          else $fatal(1, "memory write request changed while stalled");
      if (stalled_mem_wr_data_q)
        assert (mem_wr_data_ready ||
                (mem_wr_data_valid && mem_wr_data_txn_id == mem_wr_data_txn_hold_q &&
                 mem_wr_data_beat_idx == mem_wr_data_beat_hold_q &&
                 mem_wr_data == mem_wr_data_hold_q &&
                 mem_wr_data_last == mem_wr_data_last_hold_q))
          else $fatal(1, "memory write beat changed while stalled");
      stalled_mem_rd_req_q <= mem_rd_req_valid && !mem_rd_req_ready;
      mem_rd_addr_hold_q <= mem_rd_req_addr;
      mem_rd_txn_hold_q <= mem_rd_req_txn_id;
      stalled_mem_rd_data_q <= mem_rd_data_valid && !mem_rd_data_ready;
      mem_rd_data_txn_hold_q <= mem_rd_data_txn_id;
      mem_rd_data_beat_hold_q <= mem_rd_data_beat_idx;
      mem_rd_data_hold_q <= mem_rd_data;
      mem_rd_data_last_hold_q <= mem_rd_data_last;
      mem_rd_data_error_hold_q <= mem_rd_data_error;
      stalled_mem_wr_req_q <= mem_wr_req_valid && !mem_wr_req_ready;
      mem_wr_addr_hold_q <= mem_wr_req_addr;
      mem_wr_txn_hold_q <= mem_wr_req_txn_id;
      stalled_mem_wr_data_q <= mem_wr_data_valid && !mem_wr_data_ready;
      mem_wr_data_txn_hold_q <= mem_wr_data_txn_id;
      mem_wr_data_beat_hold_q <= mem_wr_data_beat_idx;
      mem_wr_data_hold_q <= mem_wr_data;
      mem_wr_data_last_hold_q <= mem_wr_data_last;
    end
  end

  // Global MESI/directory invariants checked continuously, including during
  // randomized and backpressured transactions.
  always @(posedge clock) begin : coherence_invariant_assertions
    if (!reset) begin
      for (integer set_idx = 0; set_idx < 128; set_idx = set_idx + 1) begin
        for (integer way0 = 0; way0 < 4; way0 = way0 + 1) begin
          for (integer way1 = 0; way1 < 4; way1 = way1 + 1) begin
            if (dut.l1_cluster.cores[0].l1_array.valid_array[set_idx][way0] &&
                dut.l1_cluster.cores[1].l1_array.valid_array[set_idx][way1] &&
                (dut.l1_cluster.cores[0].l1_array.tag_array[set_idx][way0] ==
                 dut.l1_cluster.cores[1].l1_array.tag_array[set_idx][way1]) &&
                ((dut.l1_cluster.cores[0].l1_array.state_array[set_idx][way0] == MESI_M) ||
                 (dut.l1_cluster.cores[0].l1_array.state_array[set_idx][way0] == MESI_E)) &&
                ((dut.l1_cluster.cores[1].l1_array.state_array[set_idx][way1] == MESI_M) ||
                 (dut.l1_cluster.cores[1].l1_array.state_array[set_idx][way1] == MESI_E)))
              $fatal(1, "MESI invariant: both cores hold write permission set=%0d tag=%h",
                     set_idx,
                     dut.l1_cluster.cores[0].l1_array.tag_array[set_idx][way0]);
          end
        end
      end
      for (integer l2_set = 0; l2_set < 512; l2_set = l2_set + 1) begin
        for (integer l2_way = 0; l2_way < 8; l2_way = l2_way + 1) begin
          if (dut.l2_array.valid_array[l2_set][l2_way]) begin
            case (dut.l2_array.dir_state_array[l2_set][l2_way])
              DIR_I: assert (dut.l2_array.sharer_array[l2_set][l2_way] == 2'b00 &&
                             !dut.l2_array.owner_array[l2_set][l2_way]);
              DIR_S: assert (dut.l2_array.sharer_array[l2_set][l2_way] != 2'b00 &&
                             !dut.l2_array.owner_array[l2_set][l2_way]);
              DIR_U: assert (dut.l2_array.sharer_array[l2_set][l2_way] == 2'b00);
              default: $fatal(1, "invalid L2 directory state encoding");
            endcase
          end
        end
      end
    end
  end

  always_ff @(posedge clock) begin
    if (reset) begin
      saw_l2_live_victim_q <= 1'b0;
      observed_l2_live_victim_q <= 32'b0;
      saw_l2_shared_victim_q <= 1'b0;
      observed_l2_shared_victim_q <= 32'b0;
      observed_l2_shared_sharers_q <= 2'b00;
    end else if (dut.dir_xfer_start_valid && dut.dir_xfer_start_ready &&
                 (dut.dir_xfer_kind == XFER_L2_REFILL) &&
                 l2_victim_valid && (l2_victim_dir_state == DIR_U)) begin
      saw_l2_live_victim_q <= 1'b1;
      observed_l2_live_victim_q <= l2_victim_addr;
    end else if (dut.dir_xfer_start_valid && dut.dir_xfer_start_ready &&
                 (dut.dir_xfer_kind == XFER_L2_REFILL) &&
                 l2_victim_valid && (l2_victim_dir_state == DIR_S)) begin
      saw_l2_shared_victim_q <= 1'b1;
      observed_l2_shared_victim_q <= l2_victim_addr;
      observed_l2_shared_sharers_q <= l2_victim_sharers;
    end
  end

  function automatic logic [63:0] memory_word(
    input logic [31:0] line_addr,
    input logic [2:0] beat
  );
    memory_word = 64'hA500_0000_0000_0000 ^
                  {32'b0, line_addr} ^ {beat, 61'b0};
  endfunction

  function automatic logic [63:0] mmio_initial_word(
    input logic [31:0] addr
  );
    mmio_initial_word = 64'h5A00_0000_0000_0000 ^ {32'b0, addr};
  endfunction

  always_comb begin
    memory_response_slot = -1;
    memory_free_slot = -1;
    memory_read_candidate = 0;
    if (memory_read_valid_held_q)
      memory_response_slot = memory_read_hold_slot_q;
    else begin
      for (integer offset = 0; offset < MODEL_SLOTS; offset = offset + 1) begin
        memory_read_candidate = (memory_read_pick_q + offset) % MODEL_SLOTS;
        if ((memory_response_slot < 0) &&
            memory_active_q[memory_read_candidate])
          memory_response_slot = memory_read_candidate;
      end
    end
    for (integer slot = 0; slot < MODEL_SLOTS; slot = slot + 1)
      if (!memory_active_q[slot] && (memory_free_slot < 0))
        memory_free_slot = slot;

    mem_rd_req_ready = !stall_mem_rd_req && (memory_free_slot >= 0) &&
                       (!inject_periodic_stalls || (cycle_count % 4 != 0));
    mem_rd_data_valid = (memory_response_slot >= 0) &&
                        (memory_read_valid_held_q ||
                         !inject_periodic_stalls || (cycle_count % 3 != 0));
    mem_rd_data_txn_id = '0;
    mem_rd_data_beat_idx = '0;
    mem_rd_data = '0;
    mem_rd_data_error = 1'b0;
    mem_rd_data_last = 1'b0;
    if (memory_response_slot >= 0) begin
      mem_rd_data_txn_id = memory_txn_q[memory_response_slot];
      mem_rd_data_beat_idx = memory_beat_q[memory_response_slot];
      mem_rd_data = memory_word(memory_line_addr_q[memory_response_slot],
                                memory_beat_q[memory_response_slot]);
      for (integer slot = 0; slot < 128; slot = slot + 1)
        if (memory_slot_valid[slot] &&
            (memory_slot_addr[slot] == memory_line_addr_q[memory_response_slot]))
          mem_rd_data = backing_store[slot][memory_beat_q[memory_response_slot]];
      mem_rd_data_error = memory_error_q[memory_response_slot] &&
                          (memory_beat_q[memory_response_slot] == 3'd0);
      mem_rd_data_last = mem_rd_data_error ||
                         (memory_beat_q[memory_response_slot] == 3'd7);
    end

    mem_wr_req_ready = !stall_mem_wr_req &&
                       (!inject_periodic_stalls || (cycle_count % 3 != 0));
    mem_wr_data_ready = !stall_mem_wr_data &&
                        (!inject_periodic_stalls || (cycle_count % 4 == 1));
    mem_wr_rsp_valid = memory_write_response_pending_q;
    mem_wr_rsp_txn_id = memory_write_response_txn_q;
    mem_wr_rsp_error = memory_write_response_error_q;
    mmio_req_ready = !stall_mmio_req && !mmio_response_valid_q &&
                     (!inject_periodic_stalls || (cycle_count % 4 != 0));
    mmio_resp_valid = mmio_response_valid_q;
    mmio_resp_rdata = mmio_response_data_q;
  end

  always_ff @(posedge clock) begin : backing_memory_model
    integer write_slot;
    integer free_read_slot;
    if (reset) begin
      memory_active_q <= '0;
      memory_read_valid_held_q <= 1'b0;
      memory_read_hold_slot_q <= 0;
      memory_read_pick_q <= 0;
      memory_write_slot_q <= '0;
      memory_write_txn_q <= '0;
      memory_write_addr_q <= '0;
      memory_write_expected_beat_q <= 0;
      memory_write_response_pending_q <= 1'b0;
      memory_write_response_txn_q <= '0;
      memory_write_response_error_q <= 1'b0;
      for (integer beat = 0; beat < 8; beat = beat + 1)
        staged_write_data_q[beat] <= '0;
      mmio_response_valid_q <= 1'b0;
      mmio_response_data_q <= '0;
      mmio_response_delay_q <= 0;
      cycle_count <= 0;
      mmio_request_count <= 0;
      memory_read_count <= 0;
      for (integer slot = 0; slot < MODEL_SLOTS; slot = slot + 1) begin
        memory_beat_q[slot] <= '0;
        memory_line_addr_q[slot] <= '0;
        memory_txn_q[slot] <= '0;
        memory_error_q[slot] <= 1'b0;
      end
    end else begin
      cycle_count <= cycle_count + 1;
      if (mmio_response_delay_q > 0)
        mmio_response_delay_q <= mmio_response_delay_q - 1;
      else if (mmio_response_delay_q == 0)
        mmio_response_delay_q <= -1;

      if (mem_rd_req_valid && mem_rd_req_ready) begin
        free_read_slot = -1;
        for (integer slot = 0; slot < MODEL_SLOTS; slot = slot + 1)
          if (!memory_active_q[slot] && (free_read_slot < 0))
            free_read_slot = slot;
        if (free_read_slot < 0)
          $fatal(1, "memory accepted a read without a free response slot");
        memory_active_q[free_read_slot] <= 1'b1;
        memory_error_q[free_read_slot] <= inject_next_mem_rd_error;
        memory_read_count <= memory_read_count + 1;
        memory_beat_q[free_read_slot] <= '0;
        memory_line_addr_q[free_read_slot] <= mem_rd_req_addr;
        memory_txn_q[free_read_slot] <= mem_rd_req_txn_id;
      end

      if (mem_rd_data_valid && mem_rd_data_ready) begin
        memory_read_valid_held_q <= 1'b0;
        memory_read_pick_q <= (memory_response_slot + 1) % MODEL_SLOTS;
        if (mem_rd_data_error || (memory_beat_q[memory_response_slot] == 3'd7)) begin
          memory_active_q[memory_response_slot] <= 1'b0;
          memory_beat_q[memory_response_slot] <= '0;
          memory_error_q[memory_response_slot] <= 1'b0;
        end else begin
          memory_beat_q[memory_response_slot] <=
            memory_beat_q[memory_response_slot] + 1'b1;
        end
      end else if (mem_rd_data_valid && !mem_rd_data_ready) begin
        memory_read_valid_held_q <= 1'b1;
        memory_read_hold_slot_q <= memory_response_slot;
      end else if (!memory_read_valid_held_q) begin
        memory_read_valid_held_q <= 1'b0;
      end

      if (mem_wr_req_valid && mem_wr_req_ready) begin
        write_slot = -1;
        for (integer slot = 0; slot < 128; slot = slot + 1) begin
          if (memory_slot_valid[slot] &&
              (memory_slot_addr[slot] == mem_wr_req_addr))
            write_slot = slot;
          else if (!memory_slot_valid[slot] && (write_slot < 0))
            write_slot = slot;
        end
        if (write_slot < 0)
          $fatal(1, "test memory backing-store table is full");
        memory_write_slot_q <= 7'(write_slot);
        memory_write_txn_q <= mem_wr_req_txn_id;
        memory_write_addr_q <= mem_wr_req_addr;
        memory_write_expected_beat_q <= 0;
      end
      if (mem_wr_data_valid && mem_wr_data_ready) begin
        if (mem_wr_data_txn_id != memory_write_txn_q)
          $fatal(1, "memory write data transaction ID changed mid-line");
        if ((mem_wr_data_beat_idx != 3'(memory_write_expected_beat_q)) ||
            (mem_wr_data_last != (memory_write_expected_beat_q == 7)))
          $fatal(1, "memory write beat sequence malformed: beat=%0d expected=%0d last=%b",
                 mem_wr_data_beat_idx, memory_write_expected_beat_q,
                 mem_wr_data_last);
        staged_write_data_q[mem_wr_data_beat_idx] <= mem_wr_data;
        if (memory_write_expected_beat_q < 7)
          memory_write_expected_beat_q <= memory_write_expected_beat_q + 1;
        if (mem_wr_data_last) begin
          if (memory_write_response_pending_q)
            $fatal(1, "memory received a second write before responding to the first");
          memory_write_response_pending_q <= 1'b1;
          memory_write_response_txn_q <= mem_wr_data_txn_id;
          memory_write_response_error_q <= inject_next_mem_wr_error;
        end
      end
      if (mem_wr_rsp_valid && mem_wr_rsp_ready) begin
        if (!mem_wr_rsp_error) begin
          memory_slot_valid[memory_write_slot_q] <= 1'b1;
          memory_slot_addr[memory_write_slot_q] <= memory_write_addr_q;
          for (integer beat = 0; beat < 8; beat = beat + 1)
            backing_store[memory_write_slot_q][beat] <= staged_write_data_q[beat];
        end
        memory_write_response_pending_q <= 1'b0;
      end

      if (mmio_response_valid_q && mmio_resp_ready)
        mmio_response_valid_q <= 1'b0;
      if (mmio_req_valid && mmio_req_ready) begin
        logic [63:0] current_word;
        logic [63:0] next_word;
        mmio_request_count <= mmio_request_count + 1;
        if (mmio_req_size != 3'b011)
          $fatal(1, "MMIO bypass must preserve the 64-bit LSU access size");
        current_word = (mmio_saved_valid_q &&
                        (mmio_saved_addr_q == mmio_req_addr)) ?
                       mmio_saved_data_q : mmio_initial_word(mmio_req_addr);
        next_word = current_word;
        for (integer lane = 0; lane < 8; lane = lane + 1)
          if (mmio_req_wmask[lane])
            next_word[8*lane +: 8] = mmio_req_wdata[8*lane +: 8];
        mmio_response_data_q <= mmio_req_write ? 64'b0 : current_word;
        mmio_response_delay_q <= 3;
        mmio_saved_addr_q <= mmio_req_addr;
        mmio_saved_data_q <= mmio_req_write ? next_word : current_word;
        mmio_saved_valid_q <= 1'b1;
      end
      if ((mmio_response_delay_q == 1) && !mmio_response_valid_q)
        mmio_response_valid_q <= 1'b1;
    end
  end

  CoherentCacheSubsystem dut (
    .clock(clock), .reset(reset), .external_fatal_error(1'b0),
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
    .mem_rd_req_valid(mem_rd_req_valid), .mem_rd_req_ready(mem_rd_req_ready),
    .mem_rd_req_addr(mem_rd_req_addr),
    .mem_rd_req_txn_id(mem_rd_req_txn_id),
    .mem_rd_data_valid(mem_rd_data_valid),
    .mem_rd_data_ready(mem_rd_data_ready),
    .mem_rd_data_txn_id(mem_rd_data_txn_id),
    .mem_rd_data_beat_idx(mem_rd_data_beat_idx), .mem_rd_data(mem_rd_data),
    .mem_rd_data_last(mem_rd_data_last), .mem_rd_data_error(mem_rd_data_error),
    .mem_wr_req_valid(mem_wr_req_valid), .mem_wr_req_ready(mem_wr_req_ready),
    .mem_wr_req_addr(mem_wr_req_addr),
    .mem_wr_req_txn_id(mem_wr_req_txn_id),
    .mem_wr_data_valid(mem_wr_data_valid),
    .mem_wr_data_ready(mem_wr_data_ready),
    .mem_wr_data_txn_id(mem_wr_data_txn_id),
    .mem_wr_data_beat_idx(mem_wr_data_beat_idx), .mem_wr_data(mem_wr_data),
    .mem_wr_data_last(mem_wr_data_last),
    .mem_wr_rsp_valid(mem_wr_rsp_valid), .mem_wr_rsp_ready(mem_wr_rsp_ready),
    .mem_wr_rsp_txn_id(mem_wr_rsp_txn_id), .mem_wr_rsp_error(mem_wr_rsp_error),
    .l2_victim_valid(l2_victim_valid), .l2_victim_addr(l2_victim_addr),
    .l2_victim_dir_state(l2_victim_dir_state),
    .l2_victim_sharers(l2_victim_sharers),
    .l2_victim_owner_id(l2_victim_owner_id), .l2_victim_dirty(l2_victim_dirty),
    .l1_victim_valid(l1_victim_valid), .l1_victim_addr(l1_victim_addr),
    .l1_victim_state(l1_victim_state),
    .l1_controller_protocol_error(l1_controller_protocol_error),
    .l1_array_protocol_error(l1_array_protocol_error),
    .directory_protocol_error(directory_protocol_error),
    .l2_protocol_error(l2_protocol_error),
    .memory_adapter_protocol_error(memory_adapter_protocol_error),
    .memory_adapter_error(memory_adapter_error), .fatal_error(fatal_error),
    .mmio_protocol_error(mmio_protocol_error),
    .perf_hit_event(perf_hit_event), .perf_miss_event(perf_miss_event),
    .perf_snoop_event(perf_snoop_event),
    .perf_dirty_writeback_event(perf_dirty_writeback_event),
    .perf_inflight(perf_inflight),
    .perf_access_complete_event(perf_access_complete_event),
    .metadata_commit_valid(metadata_commit_valid),
    .metadata_commit_line_addr(metadata_commit_line_addr),
    .metadata_commit_state(metadata_commit_state),
    .metadata_commit_is_snoop(metadata_commit_is_snoop),
    .monitor_snoop_accept_valid(monitor_snoop_accept_valid),
    .monitor_snoop_accept_addr(monitor_snoop_accept_addr),
    .monitor_snoop_accept_opcode(monitor_snoop_accept_opcode),
    .monitor_snoop_accept_txn_id(monitor_snoop_accept_txn_id),
    .monitor_dir_commit_valid(), .monitor_dir_commit_addr(),
    .monitor_dir_commit_state(), .monitor_dir_commit_sharers(),
    .monitor_dir_commit_owner(),
    .monitor_owner_data_valid(), .monitor_owner_data_core(),
    .monitor_owner_data_addr(), .monitor_owner_data_beat_idx(),
    .monitor_owner_data(), .monitor_owner_data_last()
  );

  task automatic reference_get(
    input logic [31:0] addr,
    output logic [63:0] value
  );
    integer slot;
    logic found;
    logic [31:0] word_addr;
    begin
      word_addr = {addr[31:3], 3'b000};
      found = 1'b0;
      value = (addr >= 32'h3000_0000 && addr < 32'h8000_0000) ?
              mmio_initial_word(word_addr) :
              memory_word(line_align(word_addr), word_addr[5:3]);
      if (word_addr >= 32'h3000_0000 && word_addr < 32'h8000_0000) begin
        if (mmio_saved_valid_q && mmio_saved_addr_q == word_addr)
          value = mmio_saved_data_q;
      end else begin
        for (slot = 0; slot < 128; slot = slot + 1)
          if (memory_slot_valid[slot] &&
              memory_slot_addr[slot] == line_align(word_addr))
            value = backing_store[slot][word_addr[5:3]];
      end
      for (slot = 0; slot < DATA_MODEL_ENTRIES; slot = slot + 1) begin
        if (reference_valid[slot] && reference_addr[slot] == word_addr) begin
          value = reference_data[slot];
          found = 1'b1;
        end
      end
      if (!found && reference_entries >= DATA_MODEL_ENTRIES)
        $fatal(1, "scoreboard reference table overflow");
    end
  endtask

  task automatic reference_clear;
    begin
      reference_entries = 0;
      for (integer entry = 0; entry < DATA_MODEL_ENTRIES; entry = entry + 1) begin
        reference_valid[entry] = 1'b0;
        reference_addr[entry] = '0;
        reference_data[entry] = '0;
      end
      for (integer entry = 0; entry < STATE_MODEL_ENTRIES; entry = entry + 1) begin
        state_model_valid[entry] = 1'b0;
        state_model_line[entry] = '0;
        state_model_mesi[entry][0] = MESI_I;
        state_model_mesi[entry][1] = MESI_I;
      end
      state_model_entries_used = 0;
    end
  endtask

  task automatic reference_write(
    input logic [31:0] addr,
    input logic [7:0] mask,
    input logic [63:0] data
  );
    integer slot;
    integer free_slot;
    logic found;
    logic [31:0] word_addr;
    logic [63:0] current_value;
    logic [63:0] merged_value;
    begin
      word_addr = {addr[31:3], 3'b000};
      found = 1'b0;
      free_slot = -1;
      current_value = '0;
      for (slot = 0; slot < DATA_MODEL_ENTRIES; slot = slot + 1) begin
        if (reference_valid[slot] && reference_addr[slot] == word_addr) begin
          found = 1'b1;
          current_value = reference_data[slot];
          free_slot = slot;
        end else if (!reference_valid[slot] && free_slot < 0) begin
          free_slot = slot;
        end
      end
      if (!found) begin
        reference_get(word_addr, current_value);
      end
      merged_value = current_value;
      for (integer lane = 0; lane < 8; lane = lane + 1)
        if (mask[lane])
          merged_value[8*lane +: 8] = data[8*lane +: 8];
      if (free_slot < 0)
        $fatal(1, "scoreboard reference table overflow");
      if (!found)
        reference_entries = reference_entries + 1;
      reference_valid[free_slot] = 1'b1;
      reference_addr[free_slot] = word_addr;
      reference_data[free_slot] = merged_value;
    end
  endtask

  function automatic integer state_model_index(input logic [31:0] addr);
    logic [31:0] aligned;
    begin
      aligned = line_align(addr);
      state_model_index = -1;
      for (integer entry = 0; entry < state_model_entries_used; entry = entry + 1)
        if (state_model_valid[entry] && state_model_line[entry] == aligned)
          state_model_index = entry;
    end
  endfunction

  task automatic state_model_get(
    input logic [31:0] addr,
    input integer core,
    output mesi_state_t state
  );
    integer entry;
    begin
      entry = state_model_index(addr);
      state = (entry < 0) ? MESI_I : state_model_mesi[entry][core];
    end
  endtask

  task automatic benchmark_observe_cpu_handshakes;
    mesi_state_t accepted_state;
    integer latency;
    begin
      for (integer core = 0; core < 2; core = core + 1) begin
        if (cpu_req_valid[core] && !cpu_req_ready[core] &&
            ((cpu_req_addr[core] < 32'h3000_0000) ||
             (cpu_req_addr[core] >= 32'h8000_0000)))
          benchmark_request_ready_stall_cycles =
            benchmark_request_ready_stall_cycles + 1;

        if (cpu_req_valid[core] && cpu_req_ready[core] &&
            ((cpu_req_addr[core] < 32'h3000_0000) ||
             (cpu_req_addr[core] >= 32'h8000_0000))) begin
          state_model_get(cpu_req_addr[core], core, accepted_state);
          if ((!cpu_req_write[core] && (accepted_state != MESI_I)) ||
              (cpu_req_write[core] &&
               ((accepted_state == MESI_E) || (accepted_state == MESI_M))))
            benchmark_model_accept_hit_count =
              benchmark_model_accept_hit_count + 1;
          else
            benchmark_model_accept_miss_count =
              benchmark_model_accept_miss_count + 1;
          benchmark_accept_state[core] = accepted_state;
          benchmark_accept_write[core] = cpu_req_write[core];
          benchmark_accept_cycle[core] = cycle_count;
          benchmark_accept_pending[core] = 1'b1;
        end

        if (cpu_resp_valid[core] && cpu_resp_ready[core] &&
            benchmark_accept_pending[core]) begin
          latency = cycle_count - benchmark_accept_cycle[core];
          if (benchmark_accept_state[core] == MESI_I) begin
            benchmark_l1_miss_count = benchmark_l1_miss_count + 1;
            benchmark_l1_miss_cycles = benchmark_l1_miss_cycles + latency;
          end else if (benchmark_accept_write[core] &&
                       (benchmark_accept_state[core] == MESI_S)) begin
            benchmark_upgrade_count = benchmark_upgrade_count + 1;
            benchmark_upgrade_cycles = benchmark_upgrade_cycles + latency;
          end else if (benchmark_accept_write[core] &&
                       ((benchmark_accept_state[core] == MESI_E) ||
                        (benchmark_accept_state[core] == MESI_M))) begin
            benchmark_write_hit_count = benchmark_write_hit_count + 1;
            benchmark_write_hit_cycles = benchmark_write_hit_cycles + latency;
          end else if (!benchmark_accept_write[core]) begin
            benchmark_read_hit_count = benchmark_read_hit_count + 1;
            benchmark_read_hit_cycles = benchmark_read_hit_cycles + latency;
          end
          benchmark_accept_pending[core] = 1'b0;
        end
      end
    end
  endtask

  task automatic state_model_set(
    input logic [31:0] addr,
    input integer core,
    input mesi_state_t state
  );
    integer entry;
    begin
      entry = state_model_index(addr);
      if (entry < 0) begin
        if (state_model_entries_used >= STATE_MODEL_ENTRIES)
          $fatal(1, "independent MESI model table overflow");
        entry = state_model_entries_used;
        state_model_entries_used = state_model_entries_used + 1;
        state_model_valid[entry] = 1'b1;
        state_model_line[entry] = line_align(addr);
        state_model_mesi[entry][0] = MESI_I;
        state_model_mesi[entry][1] = MESI_I;
      end
      state_model_mesi[entry][core] = state;
    end
  endtask

  task automatic coverage_mark(
    input string bin_id,
    input string old_state,
    input string requester,
    input string opcode,
    input string snoop_target,
    input string new_state,
    input string data_source,
    input integer beats
  );
    begin
      $display("COV_EVENT: id=%s checker=PASS old_state=%s requester=%s opcode=%s snoop_target=%s new_state=%s data_source=%s beats=%0d",
               bin_id, old_state, requester, opcode, snoop_target,
               new_state, data_source, beats);
    end
  endtask

  task automatic state_model_observe_protocol;
    integer put_core;
    mesi_state_t model_state;
    begin
      // An E-state store is a local silent E->M transition. It commits at
      // request acceptance even when the downstream CPU response is stalled.
      // Predict a silent E->M store from the model's own committed MESI
      // state. This does not sample the DUT lookup or its next-state signals.
      if (cpu_req_valid[0] && cpu_req_ready[0] && cpu_req_write[0]) begin
        state_model_get(cpu_req_addr[0], 0, model_state);
        if (model_state == MESI_E)
          state_model_set(cpu_req_addr[0], 0, MESI_M);
      end
      if (cpu_req_valid[1] && cpu_req_ready[1] && cpu_req_write[1]) begin
        state_model_get(cpu_req_addr[1], 1, model_state);
        if (model_state == MESI_E)
          state_model_set(cpu_req_addr[1], 1, MESI_M);
      end
      if (dut.cluster_dir_req_valid && dut.dir_req_ready &&
          ((dut.cluster_dir_req_opcode == REQ_PUTS) ||
           (dut.cluster_dir_req_opcode == REQ_PUTE) ||
           (dut.cluster_dir_req_opcode == REQ_PUTM))) begin
        put_core = dut.cluster_dir_req_src_id;
        state_model_set(dut.cluster_dir_req_addr, put_core, MESI_I);
      end
      for (integer snoop_core = 0; snoop_core < 2; snoop_core = snoop_core + 1) begin
        if (monitor_snoop_accept_valid[snoop_core])
          state_model_set(monitor_snoop_accept_addr[snoop_core], snoop_core,
                          (monitor_snoop_accept_opcode[snoop_core] == SNOOP_READ) ?
                            MESI_S : MESI_I);
      end
    end
  endtask

  // Sample transaction handshakes in the active region at the clock edge.
  // Procedural tasks resume after the edge and can otherwise miss a one-cycle
  // valid/ready pulse that the DUT has already advanced past.
  always @(posedge clock) begin : state_model_protocol_monitor
    if (!reset) begin
      benchmark_observe_cpu_handshakes();
      for (integer core = 0; core < 2; core = core + 1) begin
        if (perf_hit_event[core])
          benchmark_rtl_hit_count = benchmark_rtl_hit_count + 1;
        if (perf_miss_event[core])
          benchmark_rtl_miss_count = benchmark_rtl_miss_count + 1;
      end
      state_model_observe_protocol();
    end else begin
      benchmark_accept_pending[0] = 1'b0;
      benchmark_accept_pending[1] = 1'b0;
    end
  end

  task automatic state_model_apply_cpu(
    input integer core,
    input logic [31:0] addr,
    input logic is_write
  );
    mesi_state_t own_state;
    mesi_state_t peer_state;
    begin
      if ((addr >= 32'h3000_0000) && (addr < 32'h8000_0000))
        return;
      state_model_get(addr, core, own_state);
      state_model_get(addr, 1-core, peer_state);
      if (is_write) begin
        state_model_set(addr, 1-core, MESI_I);
        state_model_set(addr, core, MESI_M);
      end else if (own_state == MESI_I) begin
        state_model_set(addr, core,
                        (peer_state == MESI_I) ? MESI_E : MESI_S);
      end
    end
  endtask

  task automatic state_model_l1_lookup(
    input integer core,
    input logic [31:0] addr,
    output integer found_way,
    output mesi_state_t observed_state
  );
    integer set_idx;
    begin
      set_idx = addr[12:6];
      found_way = -1;
      observed_state = MESI_I;
      if (core == 0) begin
        for (integer way = 0; way < 4; way = way + 1)
          if (dut.l1_cluster.cores[0].l1_array.valid_array[set_idx][way] &&
              dut.l1_cluster.cores[0].l1_array.tag_array[set_idx][way] == addr[31:13])
            found_way = way;
        if (found_way >= 0)
          observed_state = dut.l1_cluster.cores[0].l1_array.state_array[set_idx][found_way];
      end else begin
        for (integer way = 0; way < 4; way = way + 1)
          if (dut.l1_cluster.cores[1].l1_array.valid_array[set_idx][way] &&
              dut.l1_cluster.cores[1].l1_array.tag_array[set_idx][way] == addr[31:13])
            found_way = way;
        if (found_way >= 0)
          observed_state = dut.l1_cluster.cores[1].l1_array.state_array[set_idx][found_way];
      end
    end
  endtask

  task automatic state_model_l1_word(
    input integer core,
    input integer set_idx,
    input integer way,
    input integer beat,
    output logic [63:0] data
  );
    begin
      if (core == 0)
        data = dut.l1_cluster.cores[0].l1_array.data_array[set_idx][way][beat];
      else
        data = dut.l1_cluster.cores[1].l1_array.data_array[set_idx][way][beat];
    end
  endtask

  task automatic state_model_l1_entry(
    input integer core,
    input integer set_idx,
    input integer way,
    output logic valid,
    output logic [18:0] tag,
    output mesi_state_t state
  );
    begin
      if (core == 0) begin
        valid = dut.l1_cluster.cores[0].l1_array.valid_array[set_idx][way];
        tag = dut.l1_cluster.cores[0].l1_array.tag_array[set_idx][way];
        state = dut.l1_cluster.cores[0].l1_array.state_array[set_idx][way];
      end else begin
        valid = dut.l1_cluster.cores[1].l1_array.valid_array[set_idx][way];
        tag = dut.l1_cluster.cores[1].l1_array.tag_array[set_idx][way];
        state = dut.l1_cluster.cores[1].l1_array.state_array[set_idx][way];
      end
    end
  endtask

  task automatic state_model_check_all;
    integer entry;
    integer set_idx;
    integer cache_way;
    integer found_way;
    integer l2_way;
    integer found_l2_way;
    integer core;
    logic [31:0] line_addr;
    logic [63:0] expected_word;
    logic [63:0] observed_word;
    logic observed_valid;
    logic [18:0] observed_tag;
    mesi_state_t observed_state;
    directory_state_t expected_dir_state;
    logic [1:0] expected_sharers;
    logic expected_owner;
    begin
      #1;
      // Every model line is checked against both complete physical L1 copies,
      // all eight words, and the shared directory metadata.
      for (entry = 0; entry < state_model_entries_used; entry = entry + 1) begin
        if (state_model_valid[entry]) begin
          line_addr = state_model_line[entry];
          for (core = 0; core < 2; core = core + 1) begin
            state_model_l1_lookup(core, line_addr, found_way, observed_state);
            if (observed_state !== state_model_mesi[entry][core])
              $fatal(1, "MESI reference mismatch line=%08x core=%0d got=%s expected=%s",
                     line_addr, core, observed_state.name(), state_model_mesi[entry][core].name());
            if (found_way >= 0 && observed_state != MESI_I) begin
              for (integer beat = 0; beat < 8; beat = beat + 1) begin
                reference_get(line_addr + (beat * 8), expected_word);
                state_model_l1_word(core, line_addr[12:6], found_way, beat, observed_word);
                if (observed_word !== expected_word)
                  $fatal(1, "L1 data reference mismatch line=%08x core=%0d beat=%0d got=%016x expected=%016x",
                         line_addr, core, beat, observed_word, expected_word);
              end
            end
          end

          expected_sharers = 2'b00;
          expected_owner = 1'b0;
          expected_dir_state = DIR_I;
          if ((state_model_mesi[entry][0] == MESI_M) || (state_model_mesi[entry][0] == MESI_E)) begin
            expected_dir_state = DIR_U;
            expected_owner = 1'b0;
          end else if ((state_model_mesi[entry][1] == MESI_M) || (state_model_mesi[entry][1] == MESI_E)) begin
            expected_dir_state = DIR_U;
            expected_owner = 1'b1;
          end else begin
            if (state_model_mesi[entry][0] == MESI_S) expected_sharers[0] = 1'b1;
            if (state_model_mesi[entry][1] == MESI_S) expected_sharers[1] = 1'b1;
            if (expected_sharers != 2'b00)
              expected_dir_state = DIR_S;
          end
          set_idx = line_addr[14:6];
          found_l2_way = -1;
          for (l2_way = 0; l2_way < 8; l2_way = l2_way + 1)
            if (dut.l2_array.valid_array[set_idx][l2_way] &&
                dut.l2_array.tag_array[set_idx][l2_way] == line_addr[31:15])
              found_l2_way = l2_way;
          if (found_l2_way < 0) begin
            if (expected_dir_state != DIR_I)
              $fatal(1, "L1 line is absent from L2 directory line=%08x", line_addr);
          end else if (dut.l2_array.dir_state_array[set_idx][found_l2_way] !== expected_dir_state ||
                       dut.l2_array.sharer_array[set_idx][found_l2_way] !== expected_sharers ||
                       dut.l2_array.owner_array[set_idx][found_l2_way] !== expected_owner) begin
            $fatal(1, "directory reference mismatch line=%08x got=%s sharers=%b owner=%b expected=%s sharers=%b owner=%b",
                   line_addr,
                   dut.l2_array.dir_state_array[set_idx][found_l2_way].name(),
                   dut.l2_array.sharer_array[set_idx][found_l2_way],
                   dut.l2_array.owner_array[set_idx][found_l2_way],
                   expected_dir_state.name(), expected_sharers, expected_owner);
          end
        end
      end

      // Catch any unexpected resident L1 line that was not introduced by a
      // completed CPU transaction in the reference model.
      for (core = 0; core < 2; core = core + 1)
        for (set_idx = 0; set_idx < 128; set_idx = set_idx + 1)
          for (cache_way = 0; cache_way < 4; cache_way = cache_way + 1) begin
            state_model_l1_entry(core, set_idx, cache_way, observed_valid, observed_tag, observed_state);
            if (observed_valid && (observed_state != MESI_I)) begin
              line_addr = {observed_tag, set_idx[6:0], 6'b0};
              entry = state_model_index(line_addr);
              if (entry < 0 ||
                  state_model_mesi[entry][core] !== observed_state)
                $fatal(1, "unmodeled resident L1 line=%08x core=%0d", line_addr, core);
            end
          end
    end
  endtask

  task automatic cpu_access(
    input integer core,
    input logic [31:0] addr,
    input logic is_write,
    input logic [7:0] wmask,
    input logic [63:0] wdata,
    output logic [63:0] rdata
  );
    integer cycles;
    logic request_accepted;
    logic response_received;
    logic [63:0] expected_read;
    integer operation_cycles;
    integer snoop_start_cycle;
    logic snoop_seen;
    begin
      operation_cycles = 0;
      snoop_start_cycle = 0;
      snoop_seen = 1'b0;
      if (!is_write)
        reference_get(addr, expected_read);
      @(negedge clock);
      cpu_req_addr[core] = addr;
      cpu_req_write[core] = is_write;
      cpu_req_wmask[core] = wmask;
      cpu_req_wdata[core] = wdata;
      cpu_req_valid[core] = 1'b1;
      request_accepted = 1'b0;
      for (cycles = 0; cycles < 500; cycles = cycles + 1) begin
        @(posedge clock);
        operation_cycles = operation_cycles + 1;
        if (!snoop_seen &&
            ((monitor_snoop_accept_valid[0] &&
              line_align(monitor_snoop_accept_addr[0]) == line_align(addr)) ||
             (monitor_snoop_accept_valid[1] &&
              line_align(monitor_snoop_accept_addr[1]) == line_align(addr)))) begin
          snoop_seen = 1'b1;
          snoop_start_cycle = operation_cycles;
        end
        if (cpu_req_ready[core]) begin
          request_accepted = 1'b1;
          break;
        end
      end
      if (!request_accepted)
        $fatal(1, "Core%0d request timed out at %08x", core, addr);

      @(negedge clock);
      cpu_req_valid[core] = 1'b0;
      response_received = 1'b0;
      for (cycles = 0; cycles < 1000; cycles = cycles + 1) begin
        @(posedge clock);
        operation_cycles = operation_cycles + 1;
        if (!snoop_seen &&
            ((monitor_snoop_accept_valid[0] &&
              line_align(monitor_snoop_accept_addr[0]) == line_align(addr)) ||
             (monitor_snoop_accept_valid[1] &&
              line_align(monitor_snoop_accept_addr[1]) == line_align(addr)))) begin
          snoop_seen = 1'b1;
          snoop_start_cycle = operation_cycles;
        end
        if (cpu_resp_valid[core] && cpu_resp_ready[core]) begin
          if (cpu_resp_addr[core] !== addr || cpu_resp_write[core] !== is_write)
            $fatal(1, "Core%0d response metadata mismatch at %08x", core, addr);
          rdata = cpu_resp_rdata[core];
          if (!is_write && rdata !== expected_read)
            $fatal(1, "scoreboard mismatch core=%0d addr=%08x got=%016x expected=%016x",
                   core, addr, rdata, expected_read);
          response_received = 1'b1;
          break;
        end
      end
      if (!response_received) begin
        $fatal(1, "Core%0d response timed out at %08x", core, addr);
      end
      if (is_write)
        reference_write(addr, wmask, wdata);
      state_model_apply_cpu(core, addr, is_write);
      if ((addr < 32'h3000_0000) || (addr >= 32'h8000_0000)) begin
        if (snoop_seen) begin
          benchmark_snoop_count = benchmark_snoop_count + 1;
          benchmark_snoop_cycles = benchmark_snoop_cycles + (operation_cycles - snoop_start_cycle);
        end
      end
      @(negedge clock);
      if ((addr < 32'h3000_0000) || (addr >= 32'h8000_0000))
        state_model_check_all();
    end
  endtask

  task automatic cpu_issue_only(
    input integer core,
    input logic [31:0] addr,
    input logic is_write,
    input logic [7:0] wmask,
    input logic [63:0] wdata
  );
    integer cycles;
    logic accepted;
    begin
      @(negedge clock);
      cpu_req_addr[core] = addr;
      cpu_req_write[core] = is_write;
      cpu_req_wmask[core] = wmask;
      cpu_req_wdata[core] = wdata;
      cpu_req_valid[core] = 1'b1;
      accepted = 1'b0;
      for (cycles = 0; cycles < 500; cycles = cycles + 1) begin
        @(posedge clock);
        if (cpu_req_ready[core]) begin
          accepted = 1'b1;
          break;
        end
      end
      if (!accepted)
        $fatal(1, "request issue timed out core=%0d addr=%08x", core, addr);
      @(negedge clock);
      cpu_req_valid[core] = 1'b0;
    end
  endtask

  task automatic cpu_response_only(
    input integer core,
    input logic [31:0] addr,
    input logic is_write,
    input logic [7:0] wmask,
    input logic [63:0] wdata,
    output logic [63:0] rdata
  );
    integer cycles;
    logic [63:0] expected_read;
    logic response_received;
    begin
      if (!is_write)
        reference_get(addr, expected_read);
      response_received = 1'b0;
      for (cycles = 0; cycles < 1000; cycles = cycles + 1) begin
        @(posedge clock);
        if (cpu_resp_valid[core] && cpu_resp_ready[core]) begin
          if (cpu_resp_addr[core] !== addr || cpu_resp_write[core] !== is_write)
            $fatal(1, "Core%0d response metadata mismatch at %08x", core, addr);
          rdata = cpu_resp_rdata[core];
          if (!is_write && rdata !== expected_read)
            $fatal(1, "scoreboard mismatch core=%0d addr=%08x got=%016x expected=%016x",
                   core, addr, rdata, expected_read);
          response_received = 1'b1;
          break;
        end
      end
      if (!response_received)
        $fatal(1, "Core%0d response timed out at %08x", core, addr);
      if (is_write)
        reference_write(addr, wmask, wdata);
      state_model_apply_cpu(core, addr, is_write);
      @(negedge clock);
      if ((addr < 32'h3000_0000) || (addr >= 32'h8000_0000))
        state_model_check_all();
    end
  endtask

  task automatic cpu_pair_access(
    input logic [31:0] addr0,
    input logic write0,
    input logic [7:0] mask0,
    input logic [63:0] data0,
    input logic [31:0] addr1,
    input logic write1,
    input logic [7:0] mask1,
    input logic [63:0] data1,
    output logic [63:0] rdata0,
    output logic [63:0] rdata1,
    output logic last_dir_source
  );
    logic accepted [0:1];
    logic completed [0:1];
    logic [31:0] addrs [0:1];
    logic writes [0:1];
    logic [7:0] masks [0:1];
    logic [63:0] datas [0:1];
    logic [63:0] expected [0:1];
    integer cycles;
    integer core;
    begin
      addrs[0] = addr0;
      addrs[1] = addr1;
      writes[0] = write0;
      writes[1] = write1;
      masks[0] = mask0;
      masks[1] = mask1;
      datas[0] = data0;
      datas[1] = data1;
      if (!write0)
        reference_get(addr0, expected[0]);
      if (!write1)
        reference_get(addr1, expected[1]);
      for (core = 0; core < 2; core = core + 1) begin
        accepted[core] = 1'b0;
        completed[core] = 1'b0;
      end
      last_dir_source = 1'b0;
      @(negedge clock);
      for (core = 0; core < 2; core = core + 1) begin
        cpu_req_valid[core] = 1'b1;
        cpu_req_addr[core] = addrs[core];
        cpu_req_write[core] = writes[core];
        cpu_req_wmask[core] = masks[core];
        cpu_req_wdata[core] = datas[core];
      end
      for (cycles = 0; cycles < 500; cycles = cycles + 1) begin
        @(posedge clock);
        for (core = 0; core < 2; core = core + 1)
          if (!accepted[core] && cpu_req_ready[core])
            accepted[core] = 1'b1;
        if (dut.cluster_dir_req_valid && dut.dir_req_ready)
          last_dir_source = dut.cluster_dir_req_src_id;
        @(negedge clock);
        for (core = 0; core < 2; core = core + 1)
          if (accepted[core])
            cpu_req_valid[core] = 1'b0;
        if (accepted[0] && accepted[1])
          break;
      end
      if (!(accepted[0] && accepted[1]))
        $fatal(1, "dual-core request pair acceptance timed out");

      for (cycles = 0; cycles < 2000; cycles = cycles + 1) begin
        @(posedge clock);
        if (dut.cluster_dir_req_valid && dut.dir_req_ready)
          last_dir_source = dut.cluster_dir_req_src_id;
        for (core = 0; core < 2; core = core + 1) begin
          if (!completed[core] && cpu_resp_valid[core] && cpu_resp_ready[core]) begin
            if (cpu_resp_addr[core] !== addrs[core] ||
                cpu_resp_write[core] !== writes[core])
              $fatal(1, "dual-core response metadata mismatch core=%0d", core);
            if (!writes[core]) begin
              if (core == 0) begin
                rdata0 = cpu_resp_rdata[core];
                if (rdata0 !== expected[core])
                  $fatal(1, "pair scoreboard mismatch core0 got=%016x expected=%016x",
                         rdata0, expected[core]);
              end else begin
                rdata1 = cpu_resp_rdata[core];
                if (rdata1 !== expected[core])
                  $fatal(1, "pair scoreboard mismatch core1 got=%016x expected=%016x",
                         rdata1, expected[core]);
              end
            end else begin
              reference_write(addrs[core], masks[core], datas[core]);
            end
            state_model_apply_cpu(core, addrs[core], writes[core]);
            completed[core] = 1'b1;
          end
        end
        if (completed[0] && completed[1])
          break;
      end
      if (!(completed[0] && completed[1]))
        $fatal(1, "dual-core response pair timed out");
      @(negedge clock);
      state_model_check_all();
    end
  endtask

  task automatic expect_word(
    input integer core,
    input logic [31:0] addr,
    input logic [63:0] expected
  );
    logic [63:0] got;
    begin
      cpu_access(core, addr, 1'b0, 8'h00, 64'b0, got);
      if (got !== expected)
        $fatal(1, "Core%0d read %08x got %016x expected %016x",
               core, addr, got, expected);
    end
  endtask

  task automatic expect_reference_word(
    input integer core,
    input logic [31:0] addr
  );
    logic [63:0] expected;
    begin
      reference_get(addr, expected);
      expect_word(core, addr, expected);
    end
  endtask

  task automatic expect_line_with_word_override(
    input integer core,
    input logic [31:0] line_addr,
    input integer override_beat,
    input logic [63:0] override_word
  );
    logic [63:0] expected;
    begin
      for (integer beat = 0; beat < 8; beat = beat + 1) begin
        expected = (beat == override_beat) ? override_word :
                   memory_word(line_addr, 3'(beat));
        expect_word(core, line_addr + (beat * 8), expected);
      end
    end
  endtask

  task automatic expect_protocol_state(
    input mesi_state_t core0_state,
    input mesi_state_t core1_state,
    input directory_state_t directory_state,
    input logic [1:0] sharers,
    input logic owner
  );
    logic [31:0] addr0_line;
    logic [31:0] addr1_line;
    logic found0;
    logic found1;
    logic dir_found;
    mesi_state_t observed0;
    mesi_state_t observed1;
    directory_state_t observed_dir;
    logic [1:0] observed_sharers;
    logic observed_owner;
    begin
      #1;
      addr0_line = line_align(cpu_req_addr[0]);
      addr1_line = line_align(cpu_req_addr[1]);
      found0 = 1'b0;
      found1 = 1'b0;
      dir_found = 1'b0;
      observed0 = MESI_I;
      observed1 = MESI_I;
      observed_dir = DIR_I;
      observed_sharers = 2'b00;
      observed_owner = 1'b0;
      for (integer way = 0; way < 4; way = way + 1) begin
        if (dut.l1_cluster.cores[0].l1_array.valid_array[addr0_line[12:6]][way] &&
            dut.l1_cluster.cores[0].l1_array.tag_array[addr0_line[12:6]][way] ==
              addr0_line[31:13]) begin
          found0 = 1'b1;
          observed0 = dut.l1_cluster.cores[0].l1_array.state_array[addr0_line[12:6]][way];
        end
        if (dut.l1_cluster.cores[1].l1_array.valid_array[addr1_line[12:6]][way] &&
            dut.l1_cluster.cores[1].l1_array.tag_array[addr1_line[12:6]][way] ==
              addr1_line[31:13]) begin
          found1 = 1'b1;
          observed1 = dut.l1_cluster.cores[1].l1_array.state_array[addr1_line[12:6]][way];
        end
      end
      for (integer way = 0; way < 8; way = way + 1) begin
        if (dut.l2_array.valid_array[addr0_line[14:6]][way] &&
            dut.l2_array.tag_array[addr0_line[14:6]][way] == addr0_line[31:15]) begin
          dir_found = 1'b1;
          observed_dir = dut.l2_array.dir_state_array[addr0_line[14:6]][way];
          observed_sharers = dut.l2_array.sharer_array[addr0_line[14:6]][way];
          observed_owner = dut.l2_array.owner_array[addr0_line[14:6]][way];
        end
      end
      if ((observed0 !== core0_state) || (observed1 !== core1_state) ||
          (!found0 && (core0_state != MESI_I)) ||
          (!found1 && (core1_state != MESI_I)))
        $fatal(1, "L1 state mismatch: core0=%s core1=%s expected=%s/%s addr=%08x/%08x hit=%b/%b",
               observed0.name(), observed1.name(), core0_state.name(),
               core1_state.name(), addr0_line, addr1_line, found0, found1);
      if (!dir_found || observed_dir !== directory_state ||
          observed_sharers !== sharers || observed_owner !== owner)
        $fatal(1, "directory state mismatch: hit=%b state=%s sharers=%b owner=%b expected=%s/%b/%b addr=%08x",
               dir_found, observed_dir.name(), observed_sharers, observed_owner,
               directory_state.name(), sharers, owner, addr0_line);
    end
  endtask

  initial begin
    logic [63:0] ignored;
    logic [31:0] line_addr;
    logic [31:0] word_addr;
    logic [63:0] initial_word;
    logic [63:0] value0;
    logic [63:0] value1;
    logic [63:0] value2;
    logic [63:0] value3;
    logic [63:0] value4;
    logic [63:0] masked_value;
    logic [31:0] clean_owner_line;
    logic [31:0] clean_owner_word_addr;
    logic [63:0] clean_owner_value;
    logic [31:0] mmio_addr;
    logic [63:0] mmio_initial;
    logic [63:0] mmio_masked;
    logic [63:0] mmio_data;
    integer mmio_count_before;
    logic [31:0] eviction_line_addr;
    logic [31:0] eviction_word_addr;
    logic [31:0] l2_test_addr [0:8];
    logic [63:0] l2_dirty_value;
    logic fanout_victim_written;
    logic [31:0] shared_addr;
    logic [31:0] snoop_write_race_addr;
    logic [63:0] snoop_write_race_data;
    logic [63:0] snoop_write_race_readback;
    logic [31:0] different_snoop_cpu_addr;
    logic [31:0] different_snoop_target_addr;
    logic [63:0] different_snoop_cpu_data;
    logic [63:0] different_snoop_target_data;
    logic [31:0] random_addr;
    logic [31:0] random_state;
    logic [31:0] random_seed;
    logic [63:0] random_data;
    logic [63:0] concurrent_data0;
    logic [63:0] concurrent_data1;
    logic [63:0] stalled_data;
    logic last_writer;
    integer cycles;
    integer random_index;
    integer random_core;
    logic [7:0] random_mask;
    integer line_number;
    integer core;
    integer l2_line_number;
    integer memory_slot_index;
    logic found_written_victim;
    logic failed_victim_found;
    logic failed_victim_dirty;

    reset = 1'b1;
    stall_mem_rd_req = 1'b0;
    stall_mem_wr_req = 1'b0;
    stall_mem_wr_data = 1'b0;
    stall_mmio_req = 1'b0;
    inject_periodic_stalls = 1'b0;
    inject_next_mem_rd_error = 1'b0;
    inject_next_mem_wr_error = 1'b0;
    cycle_count = 0;
    benchmark_read_hit_count = 0;
    benchmark_read_hit_cycles = 0;
    benchmark_write_hit_count = 0;
    benchmark_write_hit_cycles = 0;
    benchmark_upgrade_count = 0;
    benchmark_upgrade_cycles = 0;
    benchmark_l1_miss_count = 0;
    benchmark_l1_miss_cycles = 0;
    benchmark_request_ready_stall_cycles = 0;
    benchmark_model_accept_hit_count = 0;
    benchmark_model_accept_miss_count = 0;
    benchmark_rtl_hit_count = 0;
    benchmark_rtl_miss_count = 0;
    for (integer core = 0; core < 2; core = core + 1) begin
      benchmark_accept_pending[core] = 1'b0;
      benchmark_accept_write[core] = 1'b0;
      benchmark_accept_state[core] = MESI_I;
      benchmark_accept_cycle[core] = 0;
    end
    reference_entries = 0;
    for (integer entry = 0; entry < DATA_MODEL_ENTRIES; entry = entry + 1) begin
      reference_valid[entry] = 1'b0;
      reference_addr[entry] = '0;
      reference_data[entry] = '0;
    end
    for (integer entry = 0; entry < STATE_MODEL_ENTRIES; entry = entry + 1) begin
      state_model_valid[entry] = 1'b0;
      state_model_line[entry] = '0;
      state_model_mesi[entry][0] = MESI_I;
      state_model_mesi[entry][1] = MESI_I;
    end
    state_model_entries_used = 0;
    mmio_saved_addr_q = '0;
    mmio_saved_data_q = '0;
    mmio_saved_valid_q = 1'b0;
    for (integer slot = 0; slot < 128; slot = slot + 1) begin
      memory_slot_valid[slot] = 1'b0;
      memory_slot_addr[slot] = '0;
      for (integer beat = 0; beat < 8; beat = beat + 1)
        backing_store[slot][beat] = '0;
    end
    for (core = 0; core < 2; core = core + 1) begin
      cpu_req_valid[core] = 1'b0;
      cpu_req_addr[core] = 32'b0;
      cpu_req_write[core] = 1'b0;
      cpu_req_wmask[core] = 8'b0;
      cpu_req_wdata[core] = 64'b0;
      cpu_resp_ready[core] = 1'b1;
    end

    cpu_req_valid[0] = 1'b1;
    cpu_req_addr[0] = 32'h0000_1000;
    cpu_req_valid[1] = 1'b1;
    cpu_req_addr[1] = 32'h3000_0000;
    #1;
    if (cpu_req_ready[0] || cpu_req_ready[1] || mmio_req_valid ||
        mem_rd_req_valid || mem_wr_req_valid || cpu_resp_valid[0] ||
        cpu_resp_valid[1])
      $fatal(1, "reset must block all external cache and MMIO handshakes");
    repeat (4) @(posedge clock);
    @(negedge clock);
    cpu_req_valid[0] = 1'b0;
    cpu_req_valid[1] = 1'b0;
    reset = 1'b0;

    line_addr = 32'h0000_1000;
    word_addr = line_addr + 32'd24;
    initial_word = memory_word(line_addr, 3'd3);
    value0 = 64'h0123_4567_89AB_CDEF;
    value1 = 64'hFEDC_BA98_7654_3210;
    value2 = 64'h1122_3344_5566_7788;
    value3 = 64'hAABB_CCDD_EEFF_0011;
    value4 = 64'hDEAD_BEEF_CAFE_1234;
    clean_owner_line = 32'h0000_6000;
    clean_owner_word_addr = clean_owner_line + 32'd24;
    clean_owner_value = 64'h7654_3210_FEDC_BA98;
    mmio_addr = 32'h3000_0018;
    mmio_initial = mmio_initial_word(mmio_addr);
    mmio_masked = (mmio_initial & 64'hFFFF_FFFF_0000_0000) |
                  (value3 & 64'h0000_0000_FFFF_FFFF);
    mmio_count_before = mmio_request_count;

    // Independently run the inclusive DIR_S victim path. In this two-core
    // design the Directory transaction sequencer handles one remote target;
    // the L2 victim controller must fan out sequential invalidations to both
    // sharers before writing the dirty line back.
    if ($test$plusargs("l2_multisnoop_only")) begin
      for (l2_line_number = 0; l2_line_number <= 8; l2_line_number = l2_line_number + 1)
        l2_test_addr[l2_line_number] = 32'h0040_0000 +
                                       (l2_line_number * 32'h0000_8000);
      l2_dirty_value = 64'hCAFE_BABE_0123_4567;
      for (l2_line_number = 0; l2_line_number < 6; l2_line_number = l2_line_number + 1)
        cpu_access(0, l2_test_addr[l2_line_number] + 32'd24,
                   1'b0, 8'h00, 64'b0, ignored);

      cpu_access(0, l2_test_addr[6] + 32'd24, 1'b0, 8'h00, 64'b0, ignored);
      cpu_access(1, l2_test_addr[6] + 32'd24, 1'b0, 8'h00, 64'b0, ignored);
      cpu_access(0, l2_test_addr[6] + 32'd24, 1'b1, 8'hFF,
                 l2_dirty_value, ignored);
      cpu_access(1, l2_test_addr[6] + 32'd24, 1'b0, 8'h00, 64'b0, ignored);
      cpu_req_addr[0] = l2_test_addr[6] + 32'd24;
      cpu_req_addr[1] = l2_test_addr[6] + 32'd24;
      expect_protocol_state(MESI_S, MESI_S, DIR_S, 2'b11, 1'b0);

      cpu_access(0, l2_test_addr[7] + 32'd24, 1'b0, 8'h00, 64'b0, ignored);
      cpu_access(1, l2_test_addr[8] + 32'd24, 1'b0, 8'h00, 64'b0, ignored);
      if (!saw_l2_shared_victim_q ||
          observed_l2_shared_victim_q != l2_test_addr[6] ||
          observed_l2_shared_sharers_q != 2'b11)
        $fatal(1, "isolated victim did not fan out to both sharers: saw=%b addr=%08x sharers=%b",
               saw_l2_shared_victim_q, observed_l2_shared_victim_q,
               observed_l2_shared_sharers_q);

      for (line_number = 0; line_number < 4; line_number = line_number + 1) begin
        if ((dut.l1_cluster.cores[0].l1_array.valid_array[0][line_number] &&
             dut.l1_cluster.cores[0].l1_array.tag_array[0][line_number] ==
               l2_test_addr[6][31:13]) ||
            (dut.l1_cluster.cores[1].l1_array.valid_array[0][line_number] &&
             dut.l1_cluster.cores[1].l1_array.tag_array[0][line_number] ==
               l2_test_addr[6][31:13]))
          $fatal(1, "L2 DIR_S victim fanout left a sharer valid");
      end

      fanout_victim_written = 1'b0;
      for (memory_slot_index = 0; memory_slot_index < 128;
           memory_slot_index = memory_slot_index + 1)
        if (memory_slot_valid[memory_slot_index] &&
            memory_slot_addr[memory_slot_index] == l2_test_addr[6] &&
            backing_store[memory_slot_index][3] == l2_dirty_value)
          fanout_victim_written = 1'b1;
      if (!fanout_victim_written || fatal_error)
        $fatal(1, "multi-sharer dirty victim was not written back cleanly");
      $display("PASS: isolated DIR_S victim invalidates both L1 sharers and writes back dirty data");
      $finish;
    end

    cpu_access(0, mmio_addr, 1'b0, 8'h00, 64'b0, mmio_data);
    if (mmio_data !== mmio_initial)
      $fatal(1, "MMIO read returned %016x, expected %016x",
             mmio_data, mmio_initial);
    cpu_access(0, mmio_addr, 1'b1, 8'h0F, value3, ignored);
    cpu_access(0, mmio_addr, 1'b0, 8'h00, 64'b0, mmio_data);
    if ((mmio_data !== mmio_masked) ||
        (mmio_request_count != mmio_count_before + 3) ||
        (memory_read_count != 0) ||
        dut.l1_cluster.cores[0].l1_array.cpu_lookup_hit ||
        mmio_protocol_error)
      $fatal(1, "MMIO bypass failed: data=%016x expected=%016x reqs=%0d mem_reads=%0d hit=%b err=%b",
             mmio_data, mmio_masked, mmio_request_count - mmio_count_before,
             memory_read_count,
             dut.l1_cluster.cores[0].l1_array.cpu_lookup_hit,
             mmio_protocol_error);
      coverage_mark("mmio.bypass", "na", "both", "MMIO", "none", "na", "MMIO", 0);
    $display("PASS: MMIO read/write bypasses L1, L2, and backing memory");
    expect_word(0, 32'h2FFF_FFF8, memory_word(32'h2FFF_FFC0, 3'd7));
    cpu_access(0, 32'h7FFF_FFF8, 1'b0, 8'h00, 64'b0, mmio_data);
    if (mmio_data !== mmio_initial_word(32'h7FFF_FFF8))
      $fatal(1, "upper MMIO boundary returned incorrect data");
    expect_word(0, 32'h8000_0000, memory_word(32'h8000_0000, 3'd0));
      coverage_mark("mmio.address_boundaries", "na", "both", "MMIO_boundary", "none", "na", "MMIO", 0);
    $display("PASS: cacheable/MMIO address-domain boundary cases");

    // Exercise external request/response stalls while the CPU response is
    // also blocked. The memory model inserts read-data bubbles during this
    // phase and keeps each beat stable until the DUT accepts it.
    inject_periodic_stalls = 1'b1;
    stall_mem_rd_req = 1'b1;
    cpu_resp_ready[0] = 1'b0;
    cpu_issue_only(0, 32'h0000_9000, 1'b0, 8'h00, 64'b0);
    for (cycles = 0; cycles < 100; cycles = cycles + 1) begin
      if (mem_rd_req_valid)
        break;
      @(posedge clock);
    end
    if (!mem_rd_req_valid)
      $fatal(1, "stalled memory read request was never presented");
    repeat (4) @(posedge clock);
    @(negedge clock);
    force dut.l2_array.line_wr_ready = 1'b0;
    stall_mem_rd_req = 1'b0;
    wait (dut.mem_mshr_full_q[0]);
    wait (dut.mem_fill_writer_active_q);
    #1;
    if (!dut.mem_mshr_full_q[0] || !dut.mem_fill_writer_active_q ||
        dut.l2_line_wr_ready || (dut.mem_fill_writer_beat_q != 3'd0))
      $fatal(1, "MSHR did not decouple AXI refill from a stalled L2 fill port: full=%b writer=%b ready=%b beat=%0d",
             dut.mem_mshr_full_q[0], dut.mem_fill_writer_active_q,
             dut.l2_line_wr_ready, dut.mem_fill_writer_beat_q);
    repeat (3) @(posedge clock);
    if (!dut.mem_fill_writer_active_q ||
        (dut.mem_fill_writer_beat_q != 3'd0) || cpu_resp_valid[0])
      $fatal(1, "stalled L2 fill did not hold its buffered line and block CPU completion");
    // Some simulator versions retain a forced value on optimized array ports;
    // explicitly restore READY for portable behavior.
    force dut.l2_array.line_wr_ready = 1'b1;
      coverage_mark("backpressure.mem_refill", "I", "0", "GetS", "none", "E", "memory", 8);
    $display("PASS: refill MSHR absorbs the memory line while the L2 fill port is stalled");
    for (cycles = 0; cycles < 1000; cycles = cycles + 1) begin
      if (cpu_resp_valid[0])
        break;
      @(posedge clock);
    end
    if (!cpu_resp_valid[0])
      $fatal(1, "CPU response did not arrive after memory request stall release");
    repeat (4) @(posedge clock);
    @(negedge clock);
    cpu_resp_ready[0] = 1'b1;
    cpu_response_only(0, 32'h0000_9000, 1'b0, 8'h00, 64'b0, stalled_data);
    // Give the response tracker a full ready cycle before starting the next
    // independent transaction and changing the backpressure pattern.
    @(posedge clock);
    @(negedge clock);
      coverage_mark("backpressure.independent_channels", "mixed", "both", "GetS+GetM", "none", "mixed", "memory", 8);
    $display("PASS: memory request/refill and CPU response survive independent stalls");

    stall_mmio_req = 1'b1;
    cpu_resp_ready[0] = 1'b0;
    cpu_issue_only(0, 32'h3000_0100, 1'b0, 8'h00, 64'b0);
    for (cycles = 0; cycles < 100; cycles = cycles + 1) begin
      if (mmio_req_valid)
        break;
      @(posedge clock);
    end
    if (!mmio_req_valid)
      $fatal(1, "stalled MMIO request was never presented");
    repeat (4) @(posedge clock);
    @(negedge clock);
    stall_mmio_req = 1'b0;
    for (cycles = 0; cycles < 1000; cycles = cycles + 1) begin
      if (mmio_resp_valid)
        break;
      @(posedge clock);
    end
    if (!mmio_resp_valid)
      $fatal(1, "MMIO response did not arrive after request stall release");
    repeat (4) @(posedge clock);
    @(negedge clock);
    cpu_resp_ready[0] = 1'b1;
    cpu_response_only(0, 32'h3000_0100, 1'b0, 8'h00, 64'b0, stalled_data);
    inject_periodic_stalls = 1'b0;
      coverage_mark("backpressure.mmio", "na", "0", "MMIO", "none", "na", "MMIO", 0);
    $display("PASS: MMIO request and response payloads remain stable under backpressure");

    expect_word(0, word_addr, initial_word);
    expect_protocol_state(MESI_E, MESI_I, DIR_U, 2'b00, 1'b0);
      coverage_mark("mesi.gets_cold_refill", "I", "0", "GetS", "none", "E", "memory", 8);
    $display("PASS: Core0 GetS refill from backing memory");

    // Hold an E->M CPU write response while the other core requests the same
    // line. The snoop must wait for the local store commit, then forward the
    // new data; accepting it earlier would race the array metadata/data writes.
    snoop_write_race_addr = 32'h0000_B018;
    snoop_write_race_data = 64'hD00D_F00D_CAFE_1234;
    cpu_access(0, snoop_write_race_addr, 1'b0, 8'h00, 64'b0, ignored);
    @(negedge clock);
    cpu_resp_ready[0] = 1'b0;
    cpu_resp_ready[1] = 1'b0;
    cpu_issue_only(0, snoop_write_race_addr, 1'b1, 8'hFF,
                   snoop_write_race_data);
    for (cycles = 0; cycles < 100; cycles = cycles + 1) begin
      @(posedge clock);
      if (cpu_resp_valid[0])
        break;
    end
    if (!cpu_resp_valid[0])
      $fatal(1, "local E-to-M write did not reach its stalled response");
    cpu_issue_only(1, snoop_write_race_addr, 1'b0, 8'h00, 64'b0);
    for (cycles = 0; cycles < 300; cycles = cycles + 1) begin
      @(posedge clock);
      if (dut.snoop_valid_core[0] && !dut.snoop_ready_core[0])
        break;
    end
    if (!(dut.snoop_valid_core[0] && !dut.snoop_ready_core[0]))
      $fatal(1, "same-line snoop was not backpressured behind the local write");
    @(negedge clock);
    cpu_resp_ready[0] = 1'b1;
    cpu_response_only(0, snoop_write_race_addr, 1'b1, 8'hFF,
                      snoop_write_race_data, ignored);
    @(negedge clock);
    cpu_resp_ready[1] = 1'b1;
    cpu_response_only(1, snoop_write_race_addr, 1'b0, 8'h00, 64'b0,
                      snoop_write_race_readback);
    if (snoop_write_race_readback !== snoop_write_race_data)
      $fatal(1, "same-line snoop returned stale data during local E-to-M write");
    expect_protocol_state(MESI_S, MESI_S, DIR_S, 2'b11, 1'b0);
      coverage_mark("mesi.snoop_waits_store_commit", "E", "1", "GetS+StoreCommit", "0", "S", "L1_owner", 8);
    $display("PASS: same-line SnoopRead waits for local E-to-M write commit");
    cpu_resp_ready[0] = 1'b1;
    cpu_resp_ready[1] = 1'b1;

    cpu_access(0, word_addr, 1'b1, 8'hFF, value4, ignored);
    cpu_req_addr[0] = word_addr;
    cpu_req_addr[1] = word_addr;
    expect_protocol_state(MESI_M, MESI_I, DIR_U, 2'b00, 1'b0);
    expect_line_with_word_override(0, line_addr, 3, value4);
      coverage_mark("mesi.e_to_m_silent", "E", "0", "Store", "none", "M", "local_L1", 0);
    $display("PASS: E-to-M local write is silent and preserves the full line");

    expect_word(1, word_addr, value4);
    expect_protocol_state(MESI_S, MESI_S, DIR_S, 2'b11, 1'b0);
    expect_line_with_word_override(1, line_addr, 3, value4);
      coverage_mark("mesi.gets_share_m_owner", "M", "1", "GetS", "0", "S", "remote_owner", 8);
    $display("PASS: Core1 GetS shares the full latest line from the M owner");

    cpu_access(0, word_addr, 1'b1, 8'hFF, value0, ignored);
    expect_protocol_state(MESI_M, MESI_I, DIR_U, 2'b00, 1'b0);
    expect_word(1, word_addr, value0);
      coverage_mark("mesi.getm_upgrade_s", "S", "0", "GetM", "1", "M", "L1_peer", 0);
    $display("PASS: shared-to-exclusive upgrade invalidates peer; remote read sees M data");

    cpu_access(1, word_addr, 1'b1, 8'hFF, value1, ignored);
    expect_protocol_state(MESI_I, MESI_M, DIR_U, 2'b00, 1'b1);
    cpu_access(0, word_addr, 1'b1, 8'hFF, value2, ignored);
    expect_protocol_state(MESI_M, MESI_I, DIR_U, 2'b00, 1'b0);
    expect_word(1, word_addr, value2);
    expect_line_with_word_override(1, line_addr, 3, value2);
      coverage_mark("mesi.getm_remote_owner", "M", "0", "GetM", "1", "M", "remote_owner", 8);
    $display("PASS: remote GetM invalidates an M owner and preserves its latest data");

    masked_value = (value2 & 64'hFFFF_FFFF_0000_0000) |
                   (value3 & 64'h0000_0000_FFFF_FFFF);
    cpu_access(0, word_addr, 1'b1, 8'h0F, value3, ignored);
    expect_protocol_state(MESI_M, MESI_I, DIR_U, 2'b00, 1'b0);
    expect_word(1, word_addr, masked_value);
      coverage_mark("mesi.masked_owner_write", "M", "1", "GetS_after_MaskedStore", "0", "S", "remote_owner", 8);
    $display("PASS: byte-masked write is visible after remote owner intervention");

    // Both cores miss on one line together, then race for write permission.
    // The serialized Directory must produce one coherent final value.
    shared_addr = 32'h0000_C038;
    cpu_pair_access(shared_addr, 1'b0, 8'h00, 64'b0,
                    shared_addr, 1'b0, 8'h00, 64'b0,
                    concurrent_data0, concurrent_data1, last_writer);
    if (concurrent_data0 !== memory_word(line_align(shared_addr), shared_addr[5:3]) ||
        concurrent_data1 !== concurrent_data0)
      $fatal(1, "simultaneous cold GetS returned inconsistent data");
    cpu_pair_access(shared_addr, 1'b1, 8'hFF, 64'h1357_9BDF_2468_ACE0,
                    shared_addr, 1'b1, 8'hFF, 64'h0BAD_F00D_CAFE_BABE,
                    concurrent_data0, concurrent_data1, last_writer);
    reference_write(shared_addr, 8'hFF,
                    last_writer ? 64'h0BAD_F00D_CAFE_BABE :
                                  64'h1357_9BDF_2468_ACE0);
    reference_get(shared_addr, masked_value);
    expect_word(0, shared_addr, masked_value);
    cpu_access(0, shared_addr, 1'b1, 8'h80, 64'hA500_0000_0000_0000, ignored);
    reference_get(shared_addr, masked_value);
    expect_word(1, shared_addr, masked_value);
    cpu_access(1, shared_addr, 1'b1, 8'h00, 64'hFFFF_FFFF_FFFF_FFFF, ignored);
    reference_get(shared_addr, masked_value);
    expect_word(0, shared_addr, masked_value);
      coverage_mark("cpu_pair.same_line", "mixed", "both", "GetS+GetM", "both", "M", "mixed", 8);
    $display("PASS: same-line simultaneous GetS/GetM and byte-mask corner cases");

    cpu_pair_access(32'h0000_D000, 1'b0, 8'h00, 64'b0,
                    32'h0000_E038, 1'b0, 8'h00, 64'b0,
                    concurrent_data0, concurrent_data1, last_writer);
    if (concurrent_data0 !== memory_word(32'h0000_D000, 3'd0) ||
        concurrent_data1 !== memory_word(32'h0000_E000, 3'd7))
      $fatal(1, "different-line concurrent misses returned incorrect data");
      coverage_mark("cpu_pair.different_lines", "I", "both", "GetS", "none", "E", "memory", 8);
    $display("PASS: different-address concurrent misses route to the correct cores");

    expect_word(1, clean_owner_word_addr,
                memory_word(clean_owner_line, 3'd3));
    cpu_access(0, clean_owner_word_addr, 1'b1, 8'hFF,
               clean_owner_value, ignored);
    cpu_req_addr[0] = clean_owner_word_addr;
    cpu_req_addr[1] = clean_owner_word_addr;
    expect_protocol_state(MESI_M, MESI_I, DIR_U, 2'b00, 1'b0);
    expect_line_with_word_override(0, clean_owner_line, 3,
                                   clean_owner_value);
      coverage_mark("mesi.getm_remote_clean_e", "E", "0", "GetM", "1", "M", "clean_L1_peer", 8);
    $display("PASS: remote GetM invalidates a clean E owner and receives all beats");

    // An unrelated SnoopInvalidate must still enter the independent Snoop
    // FSM while the local CPU holds a response for another line.
    different_snoop_cpu_addr = 32'h0030_0018;
    different_snoop_target_addr = 32'h0030_8018;
    different_snoop_cpu_data = 64'h55AA_0123_CDEF_9876;
    different_snoop_target_data = 64'h8877_6655_4433_2211;
    cpu_access(0, different_snoop_cpu_addr, 1'b0, 8'h00, 64'b0, ignored);
    cpu_access(0, different_snoop_target_addr, 1'b0, 8'h00, 64'b0, ignored);
    cpu_access(1, different_snoop_target_addr, 1'b0, 8'h00, 64'b0, ignored);
    @(negedge clock);
    cpu_resp_ready[0] = 1'b0;
    cpu_issue_only(0, different_snoop_cpu_addr, 1'b1, 8'hFF,
                   different_snoop_cpu_data);
    wait (cpu_resp_valid[0]);
    cpu_issue_only(1, different_snoop_target_addr, 1'b1, 8'hFF,
                   different_snoop_target_data);
    for (cycles = 0; cycles < 500; cycles = cycles + 1) begin
      if (dut.snoop_valid_core[0] && dut.snoop_ready_core[0])
        break;
      @(posedge clock);
    end
    if (!(dut.snoop_valid_core[0] && dut.snoop_ready_core[0]))
      $fatal(1, "different-line SnoopInvalidate was blocked by local CPU response");
    cpu_response_only(1, different_snoop_target_addr, 1'b1, 8'hFF,
                      different_snoop_target_data, ignored);
    @(negedge clock);
    cpu_resp_ready[0] = 1'b1;
    cpu_response_only(0, different_snoop_cpu_addr, 1'b1, 8'hFF,
                      different_snoop_cpu_data, ignored);
    expect_word(0, different_snoop_target_addr, different_snoop_target_data);
    expect_word(1, different_snoop_cpu_addr, different_snoop_cpu_data);
      coverage_mark("cpu_pair.snoop_progress", "S", "1", "GetM_Upgrade", "0", "M", "local_L1", 0);
    $display("PASS: different-line SnoopInvalidate progresses during a local CPU response stall");
    cpu_req_addr[0] = clean_owner_word_addr;
    cpu_req_addr[1] = clean_owner_word_addr;

    cpu_access(0, word_addr, 1'b1, 8'hFF, value4, ignored);
    for (line_number = 1; line_number <= 4; line_number = line_number + 1) begin
      eviction_line_addr = line_addr + (line_number * 32'h2000);
      eviction_word_addr = eviction_line_addr + 32'd24;
      expect_word(0, eviction_word_addr, memory_word(eviction_line_addr, 3'd3));
    end
    expect_word(1, word_addr, value4);
      coverage_mark("l1.putm", "M", "0", "PutM", "none", "I", "L1_owner", 8);
    $display("PASS: dirty M victim uses PutM, returns to L2, then refills by peer");

    for (line_number = 1; line_number <= 4; line_number = line_number + 1) begin
      eviction_line_addr = line_addr + (line_number * 32'h2000);
      expect_word(1, eviction_line_addr + 32'd24,
                  memory_word(eviction_line_addr, 3'd3));
    end
    if ((dut.l1_cluster.cores[1].l1_array.valid_array[64][0] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[64][0] == 19'h0) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[64][1] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[64][1] == 19'h0) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[64][2] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[64][2] == 19'h0) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[64][3] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[64][3] == 19'h0))
      $fatal(1, "PutE replacement left the evicted E line valid");
    expect_word(0, word_addr, value4);
      coverage_mark("l1.pute", "E", "0", "PutE", "none", "I", "L2", 0);
    $display("PASS: clean E victim is removed with PutE; dirty L2 data is preserved");

    expect_word(1, 32'h0000_B018, snoop_write_race_data);
    if ((dut.l1_cluster.cores[1].l1_array.valid_array[64][0] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[64][0] == 19'h1) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[64][1] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[64][1] == 19'h1) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[64][2] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[64][2] == 19'h1) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[64][3] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[64][3] == 19'h1))
      $fatal(1, "PutS replacement left the evicted S line valid");
    expect_word(0, 32'h0000_3018, memory_word(32'h0000_3000, 3'd3));
      coverage_mark("l1.puts", "S", "0", "PutS", "none", "I", "L2", 0);
    $display("PASS: shared S victim is removed with PutS while the peer retains its copy");

    l2_test_addr[0] = 32'h0000_4000;
    for (l2_line_number = 1; l2_line_number <= 8; l2_line_number = l2_line_number + 1)
      l2_test_addr[l2_line_number] = l2_test_addr[0] +
                                     (l2_line_number * 32'h0000_8000);
    l2_dirty_value = 64'hCAFE_BABE_0123_4567;

    // Fill eight congruent lines across both cores so a later core0 miss first
    // evicts a local way while the L2 replacement pointer still selects a
    // live owner in core1.
    expect_word(0, l2_test_addr[1] + 32'd24,
                memory_word(l2_test_addr[1], 3'd3));
    expect_word(1, l2_test_addr[0] + 32'd24,
                memory_word(l2_test_addr[0], 3'd3));
    cpu_access(1, l2_test_addr[0] + 32'd24, 1'b1, 8'hFF,
               l2_dirty_value, ignored);
    for (l2_line_number = 2; l2_line_number <= 4; l2_line_number = l2_line_number + 1)
      expect_word(0, l2_test_addr[l2_line_number] + 32'd24,
                  memory_word(l2_test_addr[l2_line_number], 3'd3));
    for (l2_line_number = 5; l2_line_number <= 7; l2_line_number = l2_line_number + 1)
      expect_word(1, l2_test_addr[l2_line_number] + 32'd24,
                  memory_word(l2_test_addr[l2_line_number], 3'd3));
    cpu_access(1, l2_test_addr[0] + 32'd24, 1'b1, 8'hFF,
               l2_dirty_value, ignored);
    cpu_access(1, l2_test_addr[5] + 32'd24, 1'b1, 8'hFF,
               l2_dirty_value, ignored);
    cpu_access(1, l2_test_addr[6] + 32'd24, 1'b1, 8'hFF,
               l2_dirty_value, ignored);
    cpu_access(1, l2_test_addr[7] + 32'd24, 1'b1, 8'hFF,
               l2_dirty_value, ignored);

    expect_word(0, l2_test_addr[8] + 32'd24,
                memory_word(l2_test_addr[8], 3'd3));
    @(negedge clock);
    if (!saw_l2_live_victim_q ||
        ((observed_l2_live_victim_q[31:13]) != (l2_test_addr[0][31:13]) &&
         (observed_l2_live_victim_q[31:13]) != (l2_test_addr[5][31:13]) &&
         (observed_l2_live_victim_q[31:13]) != (l2_test_addr[6][31:13]) &&
         (observed_l2_live_victim_q[31:13]) != (l2_test_addr[7][31:13])))
      $fatal(1, "test did not evict a tracked live DIR_U L2 owner victim");
    if ((dut.l1_cluster.cores[1].l1_array.valid_array[0][0] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[0][0] == observed_l2_live_victim_q[31:13]) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[0][1] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[0][1] == observed_l2_live_victim_q[31:13]) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[0][2] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[0][2] == observed_l2_live_victim_q[31:13]) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[0][3] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[0][3] == observed_l2_live_victim_q[31:13]))
      $fatal(1, "L2 live-victim back-invalidation left the old owner line valid");
      coverage_mark("l2.live_u_victim", "M", "1", "L2_Evict", "1", "I", "L1_owner", 8);
    $display("PASS: L2 live victim back-invalidates an M owner and writes back its line");
    expect_word(0, observed_l2_live_victim_q + 32'd24, l2_dirty_value);
      coverage_mark("l2.dirty_owner_writeback", "M", "1", "L2_Evict", "1", "I", "backing_memory", 8);
    $display("PASS: dirty owner data survives L2 eviction through backing memory");

    @(negedge clock);
    reset = 1'b1;
    reference_clear();
    repeat (3) @(posedge clock);
    @(negedge clock);
    reset = 1'b0;

    expect_reference_word(0, l2_test_addr[1] + 32'd24);
    expect_reference_word(1, l2_test_addr[0] + 32'd24);
    for (l2_line_number = 2; l2_line_number <= 4; l2_line_number = l2_line_number + 1)
      expect_reference_word(0, l2_test_addr[l2_line_number] + 32'd24);
    for (l2_line_number = 5; l2_line_number <= 7; l2_line_number = l2_line_number + 1)
      expect_reference_word(1, l2_test_addr[l2_line_number] + 32'd24);
    cpu_access(1, l2_test_addr[5] + 32'd24, 1'b1, 8'hFF,
               l2_dirty_value, ignored);
    cpu_access(1, l2_test_addr[6] + 32'd24, 1'b1, 8'hFF,
               l2_dirty_value, ignored);
    // Share C, then F and G. The M-owner data writes leave F as the next L2
    // victim; core0's replacement PutS removes only its copy of C.
    expect_reference_word(1, l2_test_addr[2] + 32'd24);
    expect_word(0, l2_test_addr[5] + 32'd24, l2_dirty_value);
    expect_word(0, l2_test_addr[6] + 32'd24, l2_dirty_value);
    expect_reference_word(0, l2_test_addr[8] + 32'd24);

    if (!saw_l2_shared_victim_q ||
        (observed_l2_shared_victim_q != l2_test_addr[5]) ||
        (observed_l2_shared_sharers_q != 2'b11))
      $fatal(1, "expected DIR_S victim %08x/sharers=11, got saw=%b addr=%08x sharers=%b",
        l2_test_addr[5], saw_l2_shared_victim_q,
        observed_l2_shared_victim_q, observed_l2_shared_sharers_q);
    if ((dut.l1_cluster.cores[0].l1_array.valid_array[0][0] &&
         dut.l1_cluster.cores[0].l1_array.tag_array[0][0] == observed_l2_shared_victim_q[31:13]) ||
        (dut.l1_cluster.cores[0].l1_array.valid_array[0][1] &&
         dut.l1_cluster.cores[0].l1_array.tag_array[0][1] == observed_l2_shared_victim_q[31:13]) ||
        (dut.l1_cluster.cores[0].l1_array.valid_array[0][2] &&
         dut.l1_cluster.cores[0].l1_array.tag_array[0][2] == observed_l2_shared_victim_q[31:13]) ||
        (dut.l1_cluster.cores[0].l1_array.valid_array[0][3] &&
         dut.l1_cluster.cores[0].l1_array.tag_array[0][3] == observed_l2_shared_victim_q[31:13]) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[0][0] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[0][0] == observed_l2_shared_victim_q[31:13]) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[0][1] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[0][1] == observed_l2_shared_victim_q[31:13]) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[0][2] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[0][2] == observed_l2_shared_victim_q[31:13]) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[0][3] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[0][3] == observed_l2_shared_victim_q[31:13]))
      $fatal(1, "L2 DIR_S victim back-invalidation left an L1 sharer valid");
    found_written_victim = 1'b0;
    for (memory_slot_index = 0; memory_slot_index < 128; memory_slot_index = memory_slot_index + 1)
      if (memory_slot_valid[memory_slot_index] &&
          (memory_slot_addr[memory_slot_index] == observed_l2_shared_victim_q) &&
          (backing_store[memory_slot_index][3] == l2_dirty_value))
        found_written_victim = 1'b1;
    if (!found_written_victim)
      $fatal(1, "dirty DIR_S victim data was not written back to memory");
      coverage_mark("l2.shared_multisnoop", "S", "both", "L2_Evict", "both", "I", "L2_dirty", 8);
    $display("PASS: DIR_S L2 victim invalidates both sharers and writes back dirty L2 data");

    // A repeatable constrained-random phase concentrates traffic on one L2
    // set while varying word offsets, cores, read/write mix, and byte masks.
    inject_periodic_stalls = 1'b1;
    if (!$value$plusargs("seed=%h", random_seed))
      random_seed = 32'h1ACE_B00C;
    random_state = random_seed;
    for (random_index = 0; random_index < 80; random_index = random_index + 1) begin
      random_state = {random_state[30:0],
                      random_state[31] ^ random_state[21] ^
                      random_state[1] ^ random_state[0]};
      random_addr = 32'h0010_0000 + (32'(random_state[7:4]) << 15) +
                    {random_state[10:8], 3'b000};
      random_core = random_state[0];
      case (random_state[4:2])
        3'd0: random_mask = 8'hFF;
        3'd1: random_mask = 8'h0F;
        3'd2: random_mask = 8'hF0;
        3'd3: random_mask = 8'h01;
        3'd4: random_mask = 8'h80;
        default: random_mask = 8'h00;
      endcase
      random_data = {random_state, ~random_state};
      if (random_state[1])
        cpu_access(random_core, random_addr, 1'b1, random_mask,
                   random_data, ignored);
      else
        cpu_access(random_core, random_addr, 1'b0, 8'h00,
                   64'b0, ignored);
    end
    inject_periodic_stalls = 1'b0;
      coverage_mark("random.seeded_data", "mixed", "both", "random", "mixed", "mixed", "mixed", 8);
    $display("PASS: seeded 80-operation coherence/data scoreboard regression seed=%08x",
             random_seed);

    if ((cover_cpu_resp_stall == 0) || (cover_mmio_req_stall == 0) ||
        (cover_mmio_resp_stall == 0) || (cover_mem_rd_req_stall == 0) ||
        (cover_l2_fill_stall == 0) || (cover_mem_wr_req_stall == 0) ||
        (cover_mem_wr_data_stall == 0) ||
        (cover_dir_req_stall == 0))
      $fatal(1, "backpressure coverage hole: cpu_resp=%0d mmio_req=%0d mmio_resp=%0d mem_rd_req=%0d l2_fill=%0d mem_wr_req=%0d mem_wr_data=%0d dir_req=%0d",
             cover_cpu_resp_stall, cover_mmio_req_stall,
             cover_mmio_resp_stall, cover_mem_rd_req_stall, cover_l2_fill_stall,
             cover_mem_wr_req_stall, cover_mem_wr_data_stall,
             cover_dir_req_stall);
    $display("COVER: stalled cpu_resp=%0d mmio_req=%0d mmio_resp=%0d mem_rd_req=%0d l2_fill=%0d mem_wr_req=%0d mem_wr_data=%0d dir_req=%0d",
             cover_cpu_resp_stall, cover_mmio_req_stall,
             cover_mmio_resp_stall, cover_mem_rd_req_stall, cover_l2_fill_stall,
             cover_mem_wr_req_stall, cover_mem_wr_data_stall,
             cover_dir_req_stall);

    if ((l1_controller_protocol_error != 2'b00) ||
        (l1_array_protocol_error != 2'b00) || directory_protocol_error ||
        l2_protocol_error || memory_adapter_protocol_error ||
        memory_adapter_error || mmio_protocol_error || fatal_error)
      $fatal(1, "protocol error(s): ctrl=%b array=%b dir=%b l2=%b mem=%b mmio=%b",
             l1_controller_protocol_error, l1_array_protocol_error,
             directory_protocol_error, l2_protocol_error,
             memory_adapter_protocol_error, mmio_protocol_error);

    // Reset during a blocked refill request cancels the outstanding CPU
    // transaction and its memory-side activity. The external memory model is
    // reset together with the cache subsystem by contract.
    stall_mem_rd_req = 1'b1;
    cpu_issue_only(0, 32'h000F_0000, 1'b0, 8'h00, 64'b0);
    wait (mem_rd_req_valid);
    repeat (3) @(posedge clock);
    @(negedge clock);
    reset = 1'b1;
    reference_clear();
    repeat (3) @(posedge clock);
    if (mem_rd_req_valid || mem_wr_req_valid || mmio_req_valid ||
        cpu_resp_valid[0] || cpu_resp_valid[1])
      $fatal(1, "reset did not cancel a blocked refill transaction");
    @(negedge clock);
    stall_mem_rd_req = 1'b0;
    reset = 1'b0;
    repeat (5) begin
      @(posedge clock);
      if (cpu_resp_valid[0] || cpu_resp_valid[1])
        $fatal(1, "stale CPU response escaped after refill reset");
    end
    expect_word(0, 32'h000F_0000, memory_word(32'h000F_0000, 3'd0));
      coverage_mark("reset.refill", "I", "0", "GetS+Reset", "none", "I", "memory", 0);
    $display("PASS: reset cancels an active refill without a stale response");

    // Hold an MMIO response at the peripheral boundary, then reset before it
    // can complete at the LSU.
    cpu_resp_ready[0] = 1'b0;
    cpu_issue_only(0, 32'h3000_0108, 1'b0, 8'h00, 64'b0);
    wait (mmio_resp_valid);
    if (mmio_resp_ready)
      $fatal(1, "MMIO response should be stalled by the blocked CPU response");
    repeat (2) @(posedge clock);
    @(negedge clock);
    reset = 1'b1;
    reference_clear();
    repeat (3) @(posedge clock);
    @(negedge clock);
    reset = 1'b0;
    cpu_resp_ready[0] = 1'b1;
    repeat (5) begin
      @(posedge clock);
      if (cpu_resp_valid[0] || mmio_resp_ready)
        $fatal(1, "stale MMIO response escaped after reset");
    end
      coverage_mark("reset.mmio", "na", "0", "MMIO+Reset", "none", "na", "MMIO", 0);
    $display("PASS: reset cancels a backpressured MMIO response");

    // Finally assert reset while a valid cache response itself is stalled.
    cpu_resp_ready[0] = 1'b0;
    cpu_issue_only(0, 32'h000F_0000, 1'b0, 8'h00, 64'b0);
    wait (cpu_resp_valid[0]);
    repeat (2) @(posedge clock);
    @(negedge clock);
    reset = 1'b1;
    reference_clear();
    repeat (3) @(posedge clock);
    @(negedge clock);
    reset = 1'b0;
    repeat (5) begin
      @(posedge clock);
      if (cpu_resp_valid[0])
        $fatal(1, "stalled cache response reappeared after reset");
    end
    cpu_resp_ready[0] = 1'b1;
    if ((l1_controller_protocol_error != 2'b00) ||
        (l1_array_protocol_error != 2'b00) || directory_protocol_error ||
        l2_protocol_error || memory_adapter_protocol_error ||
        memory_adapter_error || mmio_protocol_error || fatal_error)
      $fatal(1, "protocol error after reset corner cases");
      coverage_mark("reset.cpu_rsp", "E", "0", "GetS+Reset", "none", "I", "L1", 0);
    $display("PASS: reset cancels a stalled cache response without replay");

    // Reset after an M owner has started returning SnoopData to the L2 path.
    // The reset is asserted between beats; partially transferred data is
    // discarded with the cache and Directory state.
    @(negedge clock);
    reset = 1'b1;
    reference_clear();
    repeat (3) @(posedge clock);
    @(negedge clock);
    reset = 1'b0;
    cpu_access(1, l2_test_addr[0] + 32'd24, 1'b1, 8'hFF,
               l2_dirty_value, ignored);
    cpu_issue_only(0, l2_test_addr[0] + 32'd24,
                   1'b0, 8'h00, 64'b0);
    for (cycles = 0; cycles < 1000; cycles = cycles + 1) begin
      if (dut.snoop_data_valid_core[1])
        break;
      @(posedge clock);
    end
    if (!dut.snoop_data_valid_core[1])
      $fatal(1, "remote GetS never started M-owner SnoopData stream");
    cover_reset_snoop_data = cover_reset_snoop_data + 1;
    @(negedge clock);
    reset = 1'b1;
    reference_clear();
    repeat (3) @(posedge clock);
    if (dut.snoop_data_valid_core[1] || cpu_resp_valid[0] ||
        cpu_resp_valid[1] || mem_rd_req_valid || mem_wr_req_valid ||
        mem_wr_data_valid)
      $fatal(1, "reset did not cancel an active owner SnoopData stream");
    @(negedge clock);
    reset = 1'b0;
    repeat (5) begin
      @(posedge clock);
      if (cpu_resp_valid[0] || cpu_resp_valid[1])
        $fatal(1, "stale CPU response escaped after SnoopData reset");
    end
    expect_reference_word(0, l2_test_addr[0] + 32'd24);
      coverage_mark("reset.snoop_data", "M", "0", "SnoopData+Reset", "1", "I", "L1_owner", 8);
    $display("PASS: reset cancels an active owner SnoopData stream");

    // Rebuild one full congruent L2 set with an M owner in the next victim
    // way. Stall the first external writeback beat, then reset the live
    // transaction and check that no stale memory or CPU response survives.
    @(negedge clock);
    reset = 1'b1;
    reference_clear();
    repeat (3) @(posedge clock);
    @(negedge clock);
    reset = 1'b0;
    stall_mem_wr_data = 1'b1;
    for (l2_line_number = 0; l2_line_number < 6; l2_line_number = l2_line_number + 1)
      expect_reference_word(0, l2_test_addr[l2_line_number] + 32'd24);
    cpu_access(1, l2_test_addr[6] + 32'd24, 1'b1, 8'hFF,
               l2_dirty_value, ignored);
    expect_reference_word(0, l2_test_addr[7] + 32'd24);
    cpu_issue_only(0, l2_test_addr[8] + 32'd24,
                   1'b0, 8'h00, 64'b0);
    for (cycles = 0; cycles < 3000; cycles = cycles + 1) begin
      if (mem_wr_data_valid)
        break;
      @(posedge clock);
    end
    if (!mem_wr_data_valid || mem_wr_data_ready)
      $fatal(1, "test failed to stall an active L2 victim writeback beat");
    repeat (2) @(posedge clock);
    if (!mem_wr_data_valid || mem_wr_data_ready || mem_wr_data_beat_idx != 3'd0)
      $fatal(1, "stalled L2 writeback beat did not remain stable");
    cover_reset_mem_wr_data = cover_reset_mem_wr_data + 1;
    @(negedge clock);
    reset = 1'b1;
    reference_clear();
    repeat (3) @(posedge clock);
    if (mem_wr_req_valid || mem_wr_data_valid || mem_rd_req_valid ||
        cpu_resp_valid[0] || cpu_resp_valid[1])
      $fatal(1, "reset did not cancel the stalled L2 writeback transaction");
    @(negedge clock);
    stall_mem_wr_data = 1'b0;
    reset = 1'b0;
    repeat (5) begin
      @(posedge clock);
      if (mem_wr_req_valid || mem_wr_data_valid ||
          cpu_resp_valid[0] || cpu_resp_valid[1])
        $fatal(1, "stale writeback or CPU response escaped after reset");
    end
    if ((cover_reset_snoop_data == 0) || (cover_reset_mem_wr_data == 0))
      $fatal(1, "reset coverage hole: snoop_data=%0d mem_wr_data=%0d",
             cover_reset_snoop_data, cover_reset_mem_wr_data);
      coverage_mark("reset.l2_writeback", "M", "1", "L2_Writeback+Reset", "1", "I", "backing_memory", 8);
    $display("PASS: reset cancels a stalled dirty L2 writeback beat");

    // A terminal backing-memory read error must fail-stop without returning
    // fabricated data. The external memory sends only beat 0/error/last.
    @(negedge clock);
    reset = 1'b1;
    reference_clear();
    inject_next_mem_rd_error = 1'b0;
    inject_next_mem_wr_error = 1'b0;
    repeat (3) @(posedge clock);
    @(negedge clock);
    reset = 1'b0;
    inject_next_mem_rd_error = 1'b1;
    cpu_issue_only(0, 32'h0020_0000, 1'b0, 8'h00, 64'b0);
    for (cycles = 0; cycles < 1000; cycles = cycles + 1) begin
      if (fatal_error)
        break;
      @(posedge clock);
    end
    if (!fatal_error || !memory_adapter_error || memory_adapter_protocol_error ||
        cpu_resp_valid[0] || cpu_resp_valid[1] || memory_active_q)
      $fatal(1, "terminal read error did not enter clean fail-stop handling");
    @(negedge clock);
    cpu_req_valid[1] = 1'b1;
    cpu_req_addr[1] = 32'h0020_0080;
    #1;
    if (cpu_req_ready[1])
      $fatal(1, "fatal_error did not block a new CPU request");
    cpu_req_valid[1] = 1'b0;
      coverage_mark("error.mem_read", "I", "0", "GetS+MemError", "none", "I", "memory_error", 1);
    $display("PASS: terminal memory read error suppresses success and blocks new requests");

    // After a system reset, force a dirty live L2 victim and return a failed
    // write response. The victim must remain valid and dirty because beat 7
    // alone is not a write commit.
    @(negedge clock);
    reset = 1'b1;
    reference_clear();
    inject_next_mem_rd_error = 1'b0;
    inject_next_mem_wr_error = 1'b0;
    repeat (3) @(posedge clock);
    @(negedge clock);
    reset = 1'b0;
    for (l2_line_number = 0; l2_line_number < 6; l2_line_number = l2_line_number + 1)
      expect_reference_word(0, l2_test_addr[l2_line_number] + 32'd24);
    cpu_access(1, l2_test_addr[6] + 32'd24, 1'b1, 8'hFF,
               l2_dirty_value, ignored);
    expect_reference_word(0, l2_test_addr[7] + 32'd24);
    inject_next_mem_wr_error = 1'b1;
    cpu_issue_only(0, l2_test_addr[8] + 32'd24,
                   1'b0, 8'h00, 64'b0);
    for (cycles = 0; cycles < 4000; cycles = cycles + 1) begin
      if (fatal_error)
        break;
      @(posedge clock);
    end
    failed_victim_found = 1'b0;
    failed_victim_dirty = 1'b0;
    for (integer way = 0; way < 8; way = way + 1) begin
      if (dut.l2_array.valid_array[dut.victim_addr_q[14:6]][way] &&
          dut.l2_array.tag_array[dut.victim_addr_q[14:6]][way] ==
            dut.victim_addr_q[31:15]) begin
        failed_victim_found = 1'b1;
        failed_victim_dirty = dut.l2_array.dirty_array[dut.victim_addr_q[14:6]][way];
      end
    end
    if (!fatal_error || !memory_adapter_error || memory_adapter_protocol_error ||
        cpu_resp_valid[0] || cpu_resp_valid[1] || !failed_victim_found ||
        !failed_victim_dirty || mem_wr_rsp_valid)
      $fatal(1, "failed write response check: fatal=%b mem_err=%b mem_proto=%b cpu_resp=%b%b victim_found=%b dirty=%b victim_addr=%08x rsp_valid=%b rsp_err=%b engine=%0d",
             fatal_error, memory_adapter_error, memory_adapter_protocol_error,
             cpu_resp_valid[0], cpu_resp_valid[1], failed_victim_found,
             failed_victim_dirty, dut.victim_addr_q, mem_wr_rsp_valid,
             memory_write_response_error_q, dut.engine_state_q);
      coverage_mark("error.mem_write", "M", "0", "L2_Writeback+MemError", "none", "M", "backing_memory", 8);
    $display("PASS: failed write response preserves the valid dirty L2 victim");

    if (performance_events_seen != 5'b11111)
      $fatal(1, "performance event coverage incomplete: %05b", performance_events_seen);
    if ((metadata_commit_count == 0) || (metadata_snoop_commit_count == 0))
      $fatal(1, "metadata commit monitor was not exercised: commits=%0d snoops=%0d",
             metadata_commit_count, metadata_snoop_commit_count);
    if ((benchmark_model_accept_hit_count != benchmark_rtl_hit_count) ||
        (benchmark_model_accept_miss_count != benchmark_rtl_miss_count))
      $fatal(1, "accepted hit/miss classification differs from RTL: model=%0d/%0d RTL=%0d/%0d; completed=%0d/%0d",
             benchmark_model_accept_hit_count,
             benchmark_model_accept_miss_count,
             benchmark_rtl_hit_count, benchmark_rtl_miss_count,
             benchmark_read_hit_count + benchmark_write_hit_count,
             benchmark_upgrade_count + benchmark_l1_miss_count);
    $display("PASS: hit/miss/snoop/writeback and completed-access performance events observed");
    $display("BENCH: l1_hit_count=%0d l1_hit_avg_cycles=%0d l1_miss_count=%0d l1_miss_avg_cycles=%0d read_hit_count=%0d read_hit_avg_cycles=%0d write_hit_count=%0d write_hit_avg_cycles=%0d upgrade_count=%0d upgrade_avg_cycles=%0d l1_cold_miss_count=%0d l1_cold_miss_avg_cycles=%0d cpu_req_ready_stall_cycles=%0d snoop_count=%0d snoop_avg_cycles=%0d",
             benchmark_read_hit_count + benchmark_write_hit_count,
             ((benchmark_read_hit_count + benchmark_write_hit_count) == 0) ? 0 :
               (benchmark_read_hit_cycles + benchmark_write_hit_cycles) /
                 (benchmark_read_hit_count + benchmark_write_hit_count),
             benchmark_l1_miss_count + benchmark_upgrade_count,
             ((benchmark_l1_miss_count + benchmark_upgrade_count) == 0) ? 0 :
               (benchmark_l1_miss_cycles + benchmark_upgrade_cycles) /
                 (benchmark_l1_miss_count + benchmark_upgrade_count),
             benchmark_read_hit_count,
             (benchmark_read_hit_count == 0) ? 0 : benchmark_read_hit_cycles / benchmark_read_hit_count,
             benchmark_write_hit_count,
             (benchmark_write_hit_count == 0) ? 0 : benchmark_write_hit_cycles / benchmark_write_hit_count,
             benchmark_upgrade_count,
             (benchmark_upgrade_count == 0) ? 0 : benchmark_upgrade_cycles / benchmark_upgrade_count,
             benchmark_l1_miss_count,
             (benchmark_l1_miss_count == 0) ? 0 : benchmark_l1_miss_cycles / benchmark_l1_miss_count,
             benchmark_request_ready_stall_cycles,
             benchmark_snoop_count,
             (benchmark_snoop_count == 0) ? 0 : benchmark_snoop_cycles / benchmark_snoop_count);
    $display("PASS: dual-L1 MESI directed, backpressure, reset, concurrency, and random regression");
    $finish;
  end
endmodule
