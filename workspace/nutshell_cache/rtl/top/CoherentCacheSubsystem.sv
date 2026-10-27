// Dual-LSU subsystem: two blocking private MESI L1s, a four-context Directory
// bank, one inclusive shared L2 array, and line-oriented backing-memory ports. L2
// victims are reclaimed only after their inclusive L1 copies are invalidated.
module CoherentCacheSubsystem #(
  parameter int TXN_ID_WIDTH = coherence_protocol_pkg::TXN_ID_WIDTH,
  parameter int NUM_MSHRS = 4
) (
  input logic clock,
  input logic reset,
  // Optional wrapper-level fail-stop input (for example AXI adapter errors).
  input logic external_fatal_error,

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

  // NutShell-compatible non-cacheable MMIO bypass. Addresses in
  // [0x3000_0000, 0x8000_0000) bypass both L1s and the shared L2. The LSU
  // interface is one 64-bit word; byte enables are carried in wmask.
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

  // Backing memory supplies a full 64-byte line in eight 64-bit beats and
  // echoes the request transaction ID. A failed read is one terminal beat
  // with error=1 and last=1; see docs/cache.md for the v1 contract.
  output logic mem_rd_req_valid,
  input  logic mem_rd_req_ready,
  output logic [31:0] mem_rd_req_addr,
  output logic [TXN_ID_WIDTH-1:0] mem_rd_req_txn_id,
  input  logic mem_rd_data_valid,
  output logic mem_rd_data_ready,
  input  logic [TXN_ID_WIDTH-1:0] mem_rd_data_txn_id,
  input  logic [2:0] mem_rd_data_beat_idx,
  input  logic [63:0] mem_rd_data,
  input  logic mem_rd_data_last,
  input  logic mem_rd_data_error,

  // Dirty L2 victims are written back as eight 64-bit beats, followed by an
  // explicit response. The victim stays dirty/valid until the response passes.
  output logic mem_wr_req_valid,
  input  logic mem_wr_req_ready,
  output logic [31:0] mem_wr_req_addr,
  output logic [TXN_ID_WIDTH-1:0] mem_wr_req_txn_id,
  output logic mem_wr_data_valid,
  input  logic mem_wr_data_ready,
  output logic [TXN_ID_WIDTH-1:0] mem_wr_data_txn_id,
  output logic [2:0] mem_wr_data_beat_idx,
  output logic [63:0] mem_wr_data,
  output logic mem_wr_data_last,
  input  logic mem_wr_rsp_valid,
  output logic mem_wr_rsp_ready,
  input  logic [TXN_ID_WIDTH-1:0] mem_wr_rsp_txn_id,
  input  logic mem_wr_rsp_error,

  // Victim information is exposed to support directed system-level checks.
  output logic l2_victim_valid,
  output logic [31:0] l2_victim_addr,
  output coherence_protocol_pkg::directory_state_t l2_victim_dir_state,
  output logic [1:0] l2_victim_sharers,
  output logic l2_victim_owner_id,
  output logic l2_victim_dirty,
  output logic [1:0] l1_victim_valid,
  output logic [31:0] l1_victim_addr [0:1],
  output coherence_protocol_pkg::mesi_state_t l1_victim_state [0:1],

  output logic [1:0] l1_controller_protocol_error,
  output logic [1:0] l1_array_protocol_error,
  output logic directory_protocol_error,
  output logic [3:0] directory_protocol_error_code,
  output logic l2_protocol_error,
  output logic memory_adapter_protocol_error,
  output logic memory_adapter_error,
  output logic fatal_error,
  output logic mmio_protocol_error,
  output logic [1:0] perf_hit_event,
  output logic [1:0] perf_miss_event,
  output logic [1:0] perf_snoop_event,
  output logic perf_dirty_writeback_event,
  output logic [1:0] perf_inflight,
  output logic [1:0] perf_access_complete_event,
  // A refill lookup is counted at the shared L2 data-array decision point.
  // These are refill hits/misses, not all directory metadata probes.
  output logic perf_l2_refill_hit_event,
  output logic perf_l2_refill_miss_event,

  // Stable monitor port for accepted L1 metadata commits.
  output logic metadata_commit_valid [0:1],
  output logic [31:0] metadata_commit_line_addr [0:1],
  output coherence_protocol_pkg::mesi_state_t metadata_commit_state [0:1],
  output logic metadata_commit_is_snoop [0:1],

  // Accepted L1 snoop requests, including Directory and inclusive-victim
  // back-invalidations, for protocol monitors and transaction reference models.
  output logic monitor_snoop_accept_valid [0:1],
  output logic [31:0] monitor_snoop_accept_addr [0:1],
  output coherence_protocol_pkg::snoop_opcode_t monitor_snoop_accept_opcode [0:1],
  output logic [TXN_ID_WIDTH-1:0] monitor_snoop_accept_txn_id [0:1],
  output logic monitor_victim_snoop_accept_valid,
  output logic monitor_victim_snoop_accept_core,
  output logic [31:0] monitor_victim_snoop_accept_addr,
  output logic [1:0] monitor_snoop_rsp_valid,
  output logic [1:0] monitor_snoop_rsp_ready,
  output logic [TXN_ID_WIDTH-1:0] monitor_snoop_rsp_txn_id [0:1],
  output coherence_protocol_pkg::snoop_response_t monitor_snoop_rsp_opcode [0:1],
  output logic monitor_dir_snoop_target,
  output logic [TXN_ID_WIDTH-1:0] monitor_dir_snoop_txn_id,
  output logic monitor_dir_snoop_rsp_valid,
  output logic monitor_dir_snoop_rsp_ready,
  // Accepted directory metadata updates for independent DV/reference models.
  output logic monitor_dir_commit_valid,
  output logic [31:0] monitor_dir_commit_addr,
  output logic [1:0] monitor_dir_commit_state,
  output logic [1:0] monitor_dir_commit_sharers,
  output logic monitor_dir_commit_owner,
  // Accepted owner-data beats written into the inclusive L2. These taps let
  // an independent DV monitor check the transferred line payload.
  output logic monitor_owner_data_valid,
  output logic monitor_owner_data_core,
  output logic [31:0] monitor_owner_data_addr,
  output logic [2:0] monitor_owner_data_beat_idx,
  output logic [63:0] monitor_owner_data,
  output logic monitor_owner_data_last,
  // Requests blocked because an active Directory context owns the shared
  // L2 lookup mux. These taps make the lookup-race regression observable.
  output logic monitor_dir_lookup_conflict_valid,
  output logic [31:0] monitor_dir_lookup_conflict_incoming_addr,
  output logic [31:0] monitor_dir_lookup_conflict_active_addr,
  output logic monitor_dir_lookup_conflict_is_transfer,
  // An already allocated refill lookup and a data-bearing grant can become
  // eligible together. The refill owns the shared lookup/engine slot first.
  output logic monitor_dir_transfer_grant_conflict_valid,
  output logic [31:0] monitor_dir_transfer_grant_conflict_lookup_addr,
  output logic [31:0] monitor_dir_transfer_grant_conflict_grant_addr,
  // Cycle markers for Python benchmark stage attribution. Directory metadata
  // lookup occurs in the transfer-start cycle; these pins expose its boundary.
  output logic monitor_dir_req_accept_valid,
  output logic [31:0] monitor_dir_req_accept_addr,
  output logic monitor_dir_req_accept_src_id,
  output coherence_protocol_pkg::request_opcode_t monitor_dir_req_accept_opcode,
  output logic monitor_l2_lookup_valid,
  output logic [31:0] monitor_l2_lookup_addr,
  output logic monitor_l2_lookup_hit,
  output logic monitor_dir_grant_accept_valid,
  output logic [31:0] monitor_dir_grant_accept_addr,
  // Observable for resource-contention regression; asserted during the
  // eight-beat refill stream into the shared L2 data array.
  output logic monitor_l2_fill_active,
  output logic monitor_l2_line_wr_valid,
  output logic monitor_l2_line_wr_ready,
  output logic [31:0] monitor_l2_line_wr_addr,
  output logic [2:0] monitor_l2_line_wr_beat,
  output logic monitor_dir_snoop_data_to_l2,
  output logic monitor_dir_snoop_valid,
  output logic monitor_snoop_set_conflict,
  // Debug-only transaction snapshot used by timeout diagnostics in Python DV.
  output logic [4:0] monitor_engine_state,
  output logic [31:0] monitor_engine_addr,
  output logic [31:0] monitor_victim_addr,
  output logic [1:0] monitor_victim_pending_targets,
  output logic monitor_victim_target,
  output logic [1:0] monitor_snoop_offer_valid,
  output logic [1:0] monitor_snoop_offer_ready,
  output logic [NUM_MSHRS-1:0] monitor_mem_mshr_valid,
  output logic [NUM_MSHRS-1:0] monitor_directory_active_contexts,
  output logic monitor_dir_req_live_valid,
  output logic monitor_dir_req_live_ready,
  output logic [31:0] monitor_dir_req_live_addr,
  output logic monitor_dir_xfer_live_valid,
  output logic monitor_dir_xfer_live_ready,
  output logic [5:0] monitor_cpu_state,
  output logic [5:0] monitor_l1_snoop_state,
  output logic [63:0] monitor_cpu_active_addr,
  output logic [7:0] monitor_l1_replace_state
);
  import coherence_protocol_pkg::*;

  logic cluster_cpu_req_valid [0:1];
  logic cluster_cpu_req_ready [0:1];
  logic cluster_cpu_resp_valid [0:1];
  logic cluster_cpu_resp_ready [0:1];
  logic [31:0] cluster_cpu_resp_addr [0:1];
  logic cluster_cpu_resp_write [0:1];
  logic [63:0] cluster_cpu_resp_rdata [0:1];
  logic [TXN_ID_WIDTH-1:0] cluster_cpu_resp_txn_id [0:1];
  logic cluster_perf_hit_event [0:1];
  logic cluster_perf_miss_event [0:1];
  logic cpu_req_is_mmio [0:1];
  logic [1:0] mmio_candidates;
  logic mmio_select_core;
  logic mmio_accept;
  logic mmio_owner_pending;
  logic mmio_resp_to_core [0:1];
  logic [TXN_ID_WIDTH-1:0] mmio_txn_counter_q;
  logic [TXN_ID_WIDTH-1:0] mmio_txn_q;
  logic [31:0] mmio_addr_q;
  logic mmio_write_q;
  logic [7:0] mmio_wmask_q;
  logic [63:0] mmio_wdata_q;
  logic mmio_owner_q;
  logic mmio_prefer_core1_q;
  typedef enum logic [1:0] {
    MMIO_IDLE,
    MMIO_SEND_REQ,
    MMIO_WAIT_RESP
  } mmio_state_t;
  mmio_state_t mmio_state_q;

  logic cluster_dir_req_valid;
  logic cluster_dir_req_src_id;
  request_opcode_t cluster_dir_req_opcode;
  logic [31:0] cluster_dir_req_addr;
  logic [TXN_ID_WIDTH-1:0] cluster_dir_req_txn_id;

  logic grant_valid_core [0:1];
  logic grant_ready_core [0:1];
  grant_opcode_t grant_opcode_core [0:1];
  logic [TXN_ID_WIDTH-1:0] grant_txn_id_core [0:1];
  logic grant_data_valid_core [0:1];
  logic cluster_grant_data_ready_core [0:1];
  logic [TXN_ID_WIDTH-1:0] grant_data_txn_id_core [0:1];
  logic [2:0] grant_data_beat_idx_core [0:1];
  logic [63:0] grant_data_core [0:1];
  logic grant_data_last_core [0:1];
  logic grant_commit_valid_core [0:1];
  logic grant_commit_ready_core [0:1];
  logic [TXN_ID_WIDTH-1:0] grant_commit_txn_id_core [0:1];

  logic snoop_valid_core [0:1];
  logic snoop_ready_core [0:1];
  logic [31:0] snoop_addr_core [0:1];
  snoop_opcode_t snoop_opcode_core [0:1];
  logic [TXN_ID_WIDTH-1:0] snoop_txn_id_core [0:1];
  logic snoop_rsp_valid_core [0:1];
  logic snoop_rsp_ready_core [0:1];
  snoop_response_t snoop_rsp_opcode_core [0:1];
  logic [TXN_ID_WIDTH-1:0] snoop_rsp_txn_id_core [0:1];
  logic snoop_rsp_has_data_core [0:1];
  logic snoop_data_valid_core [0:1];
  logic snoop_data_ready_core [0:1];
  logic [TXN_ID_WIDTH-1:0] snoop_data_txn_id_core [0:1];
  logic [2:0] snoop_data_beat_idx_core [0:1];
  logic [63:0] snoop_data_core [0:1];
  logic snoop_data_last_core [0:1];
  logic put_xfer_start_core [0:1];
  logic [31:0] put_xfer_addr_core [0:1];
  logic [TXN_ID_WIDTH-1:0] put_xfer_txn_id_core [0:1];
  logic put_data_valid_core [0:1];
  logic put_data_ready_core [0:1];
  logic [2:0] put_data_beat_idx_core [0:1];
  logic [63:0] put_data_core [0:1];
  logic put_data_last_core [0:1];

  logic dir_req_ready, dir_bank_req_ready, dir_lookup_available;
  logic dir_write_valid, dir_write_ready;
  logic l2_dir_write_valid, l2_dir_write_ready;
  logic [31:0] l2_dir_write_addr;
  directory_state_t l2_dir_write_state;
  logic [1:0] l2_dir_write_sharers;
  logic l2_dir_write_owner;
  logic [31:0] dir_write_addr;
  directory_state_t dir_write_state;
  logic [1:0] dir_write_sharers;
  logic dir_write_owner;
  logic dir_snoop_valid, dir_snoop_ready, dir_snoop_target;
  // The inclusive-victim engine reuses the Directory snoop wires but owns a
  // separate response FSM. Remember an accepted Directory snoop until its
  // response retires so a victim operation cannot steal that response.
  logic dir_snoop_inflight_q;
  snoop_opcode_t dir_snoop_opcode;
  logic [31:0] dir_snoop_addr;
  logic [TXN_ID_WIDTH-1:0] dir_snoop_txn_id;
  logic dir_snoop_rsp_valid, dir_snoop_rsp_ready, dir_snoop_rsp_src;
  snoop_response_t dir_snoop_rsp_opcode;
  logic [TXN_ID_WIDTH-1:0] dir_snoop_rsp_txn_id;
  logic dir_xfer_start_valid, dir_xfer_start_ready;
  line_xfer_kind_t dir_xfer_kind;
  logic [31:0] dir_xfer_addr;
  logic dir_xfer_src;
  logic [TXN_ID_WIDTH-1:0] dir_xfer_txn_id;
  logic dir_xfer_done_valid, dir_xfer_done_ready;
  logic dir_grant_valid, dir_grant_ready, dir_grant_dst;
  grant_opcode_t dir_grant_opcode;
  logic dir_grant_has_data;
  logic [31:0] dir_grant_addr;
  logic [TXN_ID_WIDTH-1:0] dir_grant_txn_id;
  logic dir_grant_commit_valid, dir_grant_commit_ready;
  logic dir_grant_commit_src_id;
  logic [TXN_ID_WIDTH-1:0] dir_grant_commit_txn_id;
  localparam int MSHR_ID_WIDTH = (NUM_MSHRS < 2) ? 1 : $clog2(NUM_MSHRS);
  logic [MSHR_ID_WIDTH-1:0] dir_xfer_context_id;
  logic [MSHR_ID_WIDTH-1:0] dir_xfer_done_context_id;
  logic [MSHR_ID_WIDTH-1:0] engine_context_q;
  logic dir_snoop_data_to_l2;
  logic victim_snoop_active, victim_snoop_data_to_l2;
  logic victim_snoop_rsp_fire;
  logic [1:0] victim_pending_targets_q;
  logic [1:0] victim_targets_after_current;
  logic victim_snoop_target_q, victim_snoop_data_expected_q;
  logic victim_snoop_data_complete_q, victim_dirty_q;
  logic victim_owner_retired_before_snoop;

  logic [31:0] l2_lookup_addr;
  logic l2_lookup_hit;
  // The array exposes way selection for standalone checks; subsystem control
  // is address-based and does not consume these optional observations.
  /* verilator lint_off UNUSEDSIGNAL */
  logic [2:0] l2_lookup_way;
  directory_state_t l2_lookup_state;
  logic [1:0] l2_lookup_sharers;
  logic l2_lookup_owner;
  logic [31:0] l2_alloc_addr;
  logic l2_alloc_victim_valid;
  logic [2:0] l2_alloc_way;
  /* verilator lint_on UNUSEDSIGNAL */
  logic [31:0] l2_alloc_victim_addr;
  directory_state_t l2_alloc_victim_state;
  logic [1:0] l2_alloc_victim_sharers;
  logic l2_alloc_victim_owner, l2_alloc_victim_dirty;
  logic l2_line_wr_valid, l2_line_wr_ready;
  logic [31:0] l2_line_wr_addr;
  logic l2_line_wr_dirty;
  logic [2:0] l2_line_wr_beat_idx;
  logic [63:0] l2_line_wr_data;
  logic l2_line_wr_last;
  logic l2_line_rd_valid, l2_line_rd_ready, l2_line_rd_hit;
  logic [31:0] l2_line_rd_addr;
  logic l2_line_data_valid, l2_line_data_ready;
  logic [2:0] l2_line_data_beat_idx;
  logic [63:0] l2_line_data;
  logic l2_line_data_last;
  logic l2_entry_invalidate_ready, l2_mark_clean_ready;
  logic l2_entry_invalidate_valid, l2_mark_clean_valid;
  logic [31:0] l2_entry_invalidate_addr, l2_mark_clean_addr;
  logic l1_replace_valid_core [0:1];

  typedef enum logic [4:0] {
    ENGINE_IDLE,
    ENGINE_VICTIM_READ,
    ENGINE_VICTIM_WRITE_REQ,
    ENGINE_VICTIM_WRITE_STREAM,
    ENGINE_VICTIM_WRITE_WAIT_RSP,
    ENGINE_VICTIM_MARK_CLEAN,
    ENGINE_VICTIM_INVALIDATE,
    ENGINE_PUTM_STREAM,
    ENGINE_MEM_REQ,
    ENGINE_XFER_DONE,
    ENGINE_GRANT_READ,
    ENGINE_GRANT_STREAM,
    ENGINE_VICTIM_SNOOP_SEND,
    ENGINE_VICTIM_SNOOP_WAIT,
    ENGINE_VICTIM_CLEAR_DIR,
    ENGINE_ERROR
  } engine_state_t;
  engine_state_t engine_state_q;
  logic [31:0] engine_addr_q;
  logic [TXN_ID_WIDTH-1:0] engine_txn_q;
  logic engine_src_q;
  logic [2:0] mem_expected_beat_q;
  logic [2:0] victim_expected_beat_q;
  logic [31:0] victim_addr_q;
  logic grant_dst_q;
  logic [31:0] grant_addr_q;
  logic [TXN_ID_WIDTH-1:0] grant_txn_q;
  logic [1:0] perf_inflight_q;

  logic [NUM_MSHRS-1:0] mem_mshr_valid_q;
  logic [NUM_MSHRS-1:0] mem_mshr_full_q;
  logic [NUM_MSHRS-1:0] mem_mshr_written_q;
  logic [31:0] mem_mshr_addr_q [0:NUM_MSHRS-1];
  logic [MSHR_ID_WIDTH-1:0] mem_mshr_context_q [0:NUM_MSHRS-1];
  logic [2:0] mem_mshr_expected_q [0:NUM_MSHRS-1];
  logic [63:0] mem_mshr_data_q [0:NUM_MSHRS-1][0:7];
  logic mem_mshr_alloc_found, mem_mshr_fill_found, mem_mshr_done_found;
  logic [MSHR_ID_WIDTH-1:0] mem_mshr_alloc_sel, mem_mshr_fill_sel;
  logic [MSHR_ID_WIDTH-1:0] mem_mshr_done_sel, mem_mshr_done_rr_q;
  logic [MSHR_ID_WIDTH-1:0] mem_mshr_fill_rr_q;
  logic mem_mshr_r_match;
  logic mem_r_protocol_bad;
  logic [MSHR_ID_WIDTH-1:0] mem_mshr_r_sel;
  logic mem_fill_writer_active_q;
  logic [MSHR_ID_WIDTH-1:0] mem_fill_writer_sel_q;
  logic [2:0] mem_fill_writer_beat_q;
  logic mshr_set_conflict, snoop_set_conflict, dir_snoop_issue_enable;

  always_comb begin : mem_mshr_decode
    integer i;
    integer idx;
    integer selected;
    mem_mshr_alloc_found = 1'b0;
    mem_mshr_alloc_sel = '0;
    mem_mshr_fill_found = 1'b0;
    mem_mshr_fill_sel = '0;
    mem_mshr_r_match = 1'b0;
    mem_r_protocol_bad = 1'b0;
    mem_mshr_r_sel = '0;
    selected = -1;
    for (i = 0; i < NUM_MSHRS; i = i + 1) begin
      if (!mem_mshr_valid_q[i] && !mem_mshr_alloc_found) begin
        mem_mshr_alloc_found = 1'b1;
        mem_mshr_alloc_sel = MSHR_ID_WIDTH'(i);
      end
      if (mem_rd_data_txn_id == TXN_ID_WIDTH'(i)) begin
        mem_mshr_r_sel = MSHR_ID_WIDTH'(i);
        mem_mshr_r_match = mem_mshr_valid_q[i] && !mem_mshr_full_q[i];
      end
    end
    selected = -1;
    for (i = 0; i < NUM_MSHRS; i = i + 1) begin
      idx = (int'(mem_mshr_fill_rr_q) + i) % NUM_MSHRS;
      if ((selected < 0) && mem_mshr_valid_q[idx] &&
          mem_mshr_full_q[idx] && !mem_mshr_written_q[idx]) selected = idx;
    end
    mem_mshr_fill_found = (selected >= 0);
    mem_mshr_fill_sel = mem_mshr_fill_found ?
                        MSHR_ID_WIDTH'(selected) : '0;
    selected = -1;
    for (i = 0; i < NUM_MSHRS; i = i + 1) begin
      idx = (int'(mem_mshr_done_rr_q) + i) % NUM_MSHRS;
      if ((selected < 0) && mem_mshr_valid_q[idx] &&
          mem_mshr_written_q[idx]) selected = idx;
    end
    mem_mshr_done_found = (selected >= 0);
    mem_mshr_done_sel = mem_mshr_done_found ?
                        MSHR_ID_WIDTH'(selected) : '0;
    mem_r_protocol_bad = mem_rd_data_valid && mem_rd_data_ready &&
      (!mem_mshr_r_match ||
       (mem_rd_data_error ? !mem_rd_data_last :
        ((mem_rd_data_beat_idx != mem_mshr_expected_q[mem_mshr_r_sel]) ||
         (mem_rd_data_last != (mem_rd_data_beat_idx == 3'd7)))));
  end

  // These interlocks only compare a Directory line with in-flight refill
  // lines. Keep them out of the MSHR response decoder's output cone so the
  // Directory ready path cannot appear to feed its own context selector.
  always_comb begin : decode_refill_set_conflicts
    mshr_set_conflict = 1'b0;
    snoop_set_conflict = 1'b0;
    for (integer i = 0; i < NUM_MSHRS; i = i + 1) begin
      if (mem_mshr_valid_q[i] &&
          (mem_mshr_addr_q[i][14:6] == dir_xfer_addr[14:6]))
        mshr_set_conflict = 1'b1;
      if (mem_mshr_valid_q[i] &&
          (mem_mshr_addr_q[i][14:6] == dir_snoop_addr[14:6]))
        snoop_set_conflict = 1'b1;
    end
  end

  for (genvar perf_core = 0; perf_core < 2; perf_core = perf_core + 1) begin : perf_events
    assign perf_hit_event[perf_core] = cluster_perf_hit_event[perf_core];
    assign perf_miss_event[perf_core] = cluster_perf_miss_event[perf_core];
    assign perf_snoop_event[perf_core] = snoop_valid_core[perf_core] &&
                                          snoop_ready_core[perf_core];
    assign perf_access_complete_event[perf_core] = perf_inflight_q[perf_core] &&
      cpu_resp_valid[perf_core] && cpu_resp_ready[perf_core];
    assign perf_inflight[perf_core] = perf_inflight_q[perf_core] && !fatal_error;
  end

  assign perf_dirty_writeback_event = !reset &&
    (engine_state_q == ENGINE_VICTIM_WRITE_WAIT_RSP) &&
    mem_wr_rsp_valid && mem_wr_rsp_ready &&
    (mem_wr_rsp_txn_id == engine_txn_q) && !mem_wr_rsp_error;

  always_ff @(posedge clock) begin
    if (reset) begin
      perf_l2_refill_hit_event <= 1'b0;
      perf_l2_refill_miss_event <= 1'b0;
    end else begin
      perf_l2_refill_hit_event <= dir_xfer_start_valid &&
        dir_xfer_start_ready && (dir_xfer_kind == XFER_L2_REFILL) &&
        l2_lookup_hit;
      perf_l2_refill_miss_event <= dir_xfer_start_valid &&
        dir_xfer_start_ready && (dir_xfer_kind == XFER_L2_REFILL) &&
        !l2_lookup_hit;
    end
  end

  always_ff @(posedge clock) begin
    if (reset) begin
      dir_snoop_inflight_q <= 1'b0;
    end else begin
      if (dir_snoop_valid && dir_snoop_ready)
        dir_snoop_inflight_q <= 1'b1;
      if (dir_snoop_rsp_valid && dir_snoop_rsp_ready)
        dir_snoop_inflight_q <= 1'b0;
    end
  end

  always_comb begin
    fatal_error = external_fatal_error ||
                  (|l1_controller_protocol_error) ||
                  (|l1_array_protocol_error) ||
                  directory_protocol_error || l2_protocol_error ||
                  memory_adapter_protocol_error || memory_adapter_error ||
                  mmio_protocol_error;
  end

  assign victim_snoop_active =
    (engine_state_q == ENGINE_VICTIM_SNOOP_SEND) ||
    (engine_state_q == ENGINE_VICTIM_SNOOP_WAIT);
  assign victim_snoop_data_to_l2 =
    (engine_state_q == ENGINE_VICTIM_SNOOP_WAIT) &&
    victim_snoop_data_expected_q;
  assign victim_targets_after_current = victim_pending_targets_q &
    ~(victim_snoop_target_q ? 2'b10 : 2'b01);
  // A dirty victim owner may have completed PutM and disappeared while the
  // eviction waited for its snoop slot. INV_ACK without data is then legal:
  // the accepted PutM already made the current L2 line authoritative.
  assign victim_owner_retired_before_snoop =
    victim_snoop_data_expected_q && !victim_snoop_data_complete_q &&
    (mem_expected_beat_q == 3'd0) &&
    (snoop_rsp_opcode_core[victim_snoop_target_q] == SNOOP_RSP_INV_ACK) &&
    !snoop_rsp_has_data_core[victim_snoop_target_q];
  assign l2_dir_write_valid =
    (engine_state_q == ENGINE_VICTIM_CLEAR_DIR) ? 1'b1 : dir_write_valid;
  assign l2_dir_write_addr =
    (engine_state_q == ENGINE_VICTIM_CLEAR_DIR) ? victim_addr_q : dir_write_addr;
  assign l2_dir_write_state =
    (engine_state_q == ENGINE_VICTIM_CLEAR_DIR) ? DIR_I : dir_write_state;
  assign l2_dir_write_sharers =
    (engine_state_q == ENGINE_VICTIM_CLEAR_DIR) ? 2'b00 : dir_write_sharers;
  assign l2_dir_write_owner =
    (engine_state_q == ENGINE_VICTIM_CLEAR_DIR) ? 1'b0 : dir_write_owner;
  assign dir_write_ready = l2_dir_write_ready &&
                           (engine_state_q != ENGINE_VICTIM_CLEAR_DIR);

  // The active Directory transaction owns the metadata lookup port while a
  // line transfer starts. A queued request from the other L1 must not redirect
  // the lookup used to decide whether this refill hits or needs a victim.
  assign l2_lookup_addr = dir_xfer_start_valid ? dir_xfer_addr :
                          dir_grant_valid ? dir_grant_addr :
                          cluster_dir_req_valid ? cluster_dir_req_addr :
                          engine_addr_q;
  // The L2 metadata lookup is shared. Do not allocate a new Directory
  // context while a transfer-start or grant lookup owns that port, or the
  // newly accepted request can capture another line's owner/sharer state.
  assign dir_lookup_available = !reset && !dir_xfer_start_valid &&
                                !dir_grant_valid;
  assign dir_req_ready = dir_bank_req_ready && dir_lookup_available;
  assign l2_alloc_addr = dir_xfer_start_valid ? dir_xfer_addr : engine_addr_q;
  assign monitor_dir_lookup_conflict_valid = !reset && cluster_dir_req_valid &&
    dir_bank_req_ready && (dir_xfer_start_valid || dir_grant_valid);
  assign monitor_dir_lookup_conflict_incoming_addr = cluster_dir_req_addr;
  assign monitor_dir_lookup_conflict_active_addr = l2_lookup_addr;
  assign monitor_dir_lookup_conflict_is_transfer = dir_xfer_start_valid;
  assign monitor_dir_transfer_grant_conflict_valid = !reset &&
    dir_xfer_start_valid && dir_xfer_start_ready && dir_grant_valid &&
    dir_grant_has_data;
  assign monitor_dir_transfer_grant_conflict_lookup_addr = dir_xfer_addr;
  assign monitor_dir_transfer_grant_conflict_grant_addr = dir_grant_addr;
  assign monitor_dir_req_accept_valid = !reset && cluster_dir_req_valid &&
                                        dir_req_ready;
  assign monitor_dir_req_accept_addr = cluster_dir_req_addr;
  assign monitor_dir_req_accept_src_id = cluster_dir_req_src_id;
  assign monitor_dir_req_accept_opcode = cluster_dir_req_opcode;
  assign monitor_l2_lookup_valid = !reset && dir_xfer_start_valid &&
                                   dir_xfer_start_ready &&
                                   (dir_xfer_kind == XFER_L2_REFILL);
  assign monitor_l2_lookup_addr = dir_xfer_addr;
  assign monitor_l2_lookup_hit = l2_lookup_hit;
  assign monitor_dir_grant_accept_valid = !reset && dir_grant_valid &&
                                          dir_grant_ready;
  assign monitor_dir_grant_accept_addr = dir_grant_addr;
  assign monitor_l2_fill_active = mem_fill_writer_active_q;
  assign monitor_l2_line_wr_valid = l2_line_wr_valid;
  assign monitor_l2_line_wr_ready = l2_line_wr_ready;
  assign monitor_l2_line_wr_addr = l2_line_wr_addr;
  assign monitor_l2_line_wr_beat = l2_line_wr_beat_idx;
  assign monitor_dir_snoop_data_to_l2 = dir_snoop_data_to_l2;
  assign monitor_dir_snoop_valid = dir_snoop_valid;
  assign monitor_snoop_set_conflict = snoop_set_conflict;
  assign monitor_engine_state = engine_state_q;
  assign monitor_engine_addr = engine_addr_q;
  assign monitor_victim_addr = victim_addr_q;
  assign monitor_victim_pending_targets = victim_pending_targets_q;
  assign monitor_victim_target = victim_snoop_target_q;
  assign monitor_snoop_offer_valid = {snoop_valid_core[1], snoop_valid_core[0]};
  assign monitor_snoop_offer_ready = {snoop_ready_core[1], snoop_ready_core[0]};
  assign monitor_mem_mshr_valid = mem_mshr_valid_q;
  assign monitor_dir_req_live_valid = cluster_dir_req_valid;
  assign monitor_dir_req_live_ready = dir_req_ready;
  assign monitor_dir_req_live_addr = cluster_dir_req_addr;
  assign monitor_dir_xfer_live_valid = dir_xfer_start_valid;
  assign monitor_dir_xfer_live_ready = dir_xfer_start_ready;
  assign monitor_victim_snoop_accept_valid = !reset && victim_snoop_active &&
    snoop_valid_core[victim_snoop_target_q] &&
    snoop_ready_core[victim_snoop_target_q];
  assign monitor_victim_snoop_accept_core = victim_snoop_target_q;
  assign monitor_victim_snoop_accept_addr = victim_addr_q;
  assign monitor_dir_snoop_rsp_valid = dir_snoop_rsp_valid;
  assign monitor_dir_snoop_rsp_ready = dir_snoop_rsp_ready;
  assign monitor_dir_snoop_target = dir_snoop_target;
  assign monitor_dir_snoop_txn_id = dir_snoop_txn_id;

  always_ff @(posedge clock) begin
    if (!reset && victim_snoop_active)
      assert (!dir_snoop_inflight_q)
        else $error("L2 victim snoop took ownership while a Directory snoop was outstanding");
    if (!reset && mem_fill_writer_active_q) begin
      assert (l2_line_wr_valid &&
              (l2_line_wr_addr == mem_mshr_addr_q[mem_fill_writer_sel_q]) &&
              (l2_line_wr_beat_idx == mem_fill_writer_beat_q))
        else $error("active L2 refill lost ownership of the shared line-write port");
    end
    if (!reset && !victim_snoop_active &&
        snoop_valid_core[dir_snoop_target] &&
        snoop_ready_core[dir_snoop_target]) begin
      assert (dir_snoop_valid && dir_snoop_ready)
        else $error("L1 accepted a Snoop not accepted by the Directory bank");
    end
    if (!reset && cluster_dir_req_valid && dir_req_ready) begin
      assert (l2_lookup_addr == cluster_dir_req_addr)
        else $error("Directory accepted a request with a mismatched L2 lookup");
    end
    if (!reset && dir_xfer_start_valid && dir_xfer_start_ready &&
        dir_grant_valid && dir_grant_has_data) begin
      assert (!dir_grant_ready)
        else $error("data grant accepted while a refill owned the shared engine");
      assert (!grant_valid_core[dir_grant_dst])
        else $error("data grant leaked to an L1 while refill owned the engine");
    end
    if (!reset && dir_grant_valid && dir_grant_ready && dir_grant_has_data) begin
      assert (l2_line_rd_valid &&
              (l2_line_rd_addr == line_align(dir_grant_addr)))
        else $error("accepted data grant did not prefetch its L2 line");
    end
    if (!reset && mem_fill_writer_active_q && dir_snoop_valid &&
        dir_snoop_ready) begin
      assert (!dir_snoop_data_to_l2)
        else $error("owner-data snoop overlapped the shared L2 fill writer");
    end
  end

  assign mmio_owner_pending = (mmio_state_q != MMIO_IDLE);

  always_comb begin
    for (integer core = 0; core < 2; core = core + 1) begin
      cpu_req_is_mmio[core] = (cpu_req_addr[core] >= 32'h3000_0000) &&
                              (cpu_req_addr[core] <  32'h8000_0000);
      cluster_cpu_req_valid[core] = cpu_req_valid[core] &&
                                    !cpu_req_is_mmio[core] &&
                                    !fatal_error &&
                                    !(mmio_owner_pending &&
                                      (mmio_owner_q == 1'(core)));
      cluster_cpu_resp_ready[core] = cpu_resp_ready[core] &&
                                     !fatal_error &&
                                     !(mmio_owner_pending &&
                                       (mmio_owner_q == 1'(core)));
      mmio_candidates[core] = cpu_req_valid[core] &&
                              cpu_req_is_mmio[core] &&
                              !reset &&
                              !fatal_error &&
                              cluster_cpu_req_ready[core] &&
                              !(mmio_owner_pending &&
                                (mmio_owner_q == 1'(core)));
    end

    if (mmio_candidates[0] && mmio_candidates[1])
      mmio_select_core = mmio_prefer_core1_q;
    else
      mmio_select_core = mmio_candidates[1];
    mmio_accept = (mmio_state_q == MMIO_IDLE) &&
                  mmio_candidates[mmio_select_core];

    for (integer core = 0; core < 2; core = core + 1) begin
      cpu_req_ready[core] = !reset && !fatal_error && (cpu_req_is_mmio[core] ?
        (mmio_accept && (mmio_select_core == 1'(core))) :
        (cluster_cpu_req_ready[core] &&
         !(mmio_owner_pending && (mmio_owner_q == 1'(core)))));
      mmio_resp_to_core[core] = (mmio_state_q == MMIO_WAIT_RESP) &&
                                mmio_resp_valid &&
                                (mmio_owner_q == 1'(core));
      cpu_resp_valid[core] = !reset && !fatal_error &&
                             (cluster_cpu_resp_valid[core] ||
                                        mmio_resp_to_core[core]);
      cpu_resp_addr[core] = (mmio_owner_pending &&
                             (mmio_owner_q == 1'(core))) ?
                            mmio_addr_q : cluster_cpu_resp_addr[core];
      cpu_resp_write[core] = (mmio_owner_pending &&
                              (mmio_owner_q == 1'(core))) ?
                             mmio_write_q : cluster_cpu_resp_write[core];
      cpu_resp_rdata[core] = mmio_resp_to_core[core] ?
                             mmio_resp_rdata : cluster_cpu_resp_rdata[core];
      cpu_resp_txn_id[core] = (mmio_owner_pending &&
                               (mmio_owner_q == 1'(core))) ?
                              mmio_txn_q : cluster_cpu_resp_txn_id[core];
    end

    mmio_req_valid = !reset && !fatal_error &&
                     (mmio_state_q == MMIO_SEND_REQ);
    mmio_req_addr = mmio_addr_q;
    mmio_req_size = 3'b011;
    mmio_req_write = mmio_write_q;
    mmio_req_wmask = mmio_wmask_q;
    mmio_req_wdata = mmio_wdata_q;
    mmio_resp_ready = !reset && !fatal_error &&
                      (mmio_state_q == MMIO_WAIT_RESP) &&
                      cpu_resp_ready[mmio_owner_q];
  end

  assign dir_xfer_start_ready = (engine_state_q == ENGINE_IDLE) &&
                                !mem_fill_writer_active_q &&
                                !mshr_set_conflict &&
                                // Once an owner-data Snoop has been accepted,
                                // its stream owns the L2 write port. A stalled
                                // Snoop offer must not block a same-line PutM:
                                // the replacement can be waiting for this PutM
                                // before it can accept the Snoop. PutM is
                                // drained first, then the missing-line Snoop
                                // response falls back to the newly committed
                                // L2 copy in DirectoryController.
                                (!dir_snoop_data_to_l2 ||
                                 ((dir_xfer_kind == XFER_PUTM_TO_L2) &&
                                  dir_snoop_valid &&
                                  !dir_snoop_inflight_q &&
                                  !dir_snoop_ready)) &&
                                // A live L2 victim uses the same L1 snoop
                                // response path as Directory transactions.
                                // Wait for the outstanding Directory snoop
                                // to retire, including the cycle it is first
                                // offered, before taking ownership of that
                                // path for back-invalidation.
                                !((dir_xfer_kind == XFER_L2_REFILL) &&
                                  l2_alloc_victim_valid &&
                                  (dir_snoop_inflight_q || dir_snoop_valid ||
                                   dir_snoop_rsp_valid));

  // Snoop payload/valid are independent of the return ready path. Keep them
  // in their own combinational cone because an L1 may qualify ready by line
  // address while a Directory MSHR holds valid and address stable.
  always_comb begin : route_snoop_payload
    snoop_valid_core[0] = 1'b0;
    snoop_valid_core[1] = 1'b0;
    put_xfer_start_core[0] = 1'b0;
    put_xfer_start_core[1] = 1'b0;
    put_xfer_addr_core[0] = dir_xfer_addr;
    put_xfer_addr_core[1] = dir_xfer_addr;
    put_xfer_txn_id_core[0] = dir_xfer_txn_id;
    put_xfer_txn_id_core[1] = dir_xfer_txn_id;
    snoop_addr_core[0] = dir_snoop_addr;
    snoop_addr_core[1] = dir_snoop_addr;
    snoop_opcode_core[0] = dir_snoop_opcode;
    snoop_opcode_core[1] = dir_snoop_opcode;
    snoop_txn_id_core[0] = dir_snoop_txn_id;
    snoop_txn_id_core[1] = dir_snoop_txn_id;
    // Keep request valid and ready coupled: otherwise an L1 could consume a
    // Snoop while the Directory MSHR did not accept the same request.
    dir_snoop_issue_enable = !victim_snoop_active && !snoop_set_conflict &&
      // Once PutM owns the line-write engine, hold off a new dirty-owner
      // Snoop until the eight-beat PutM stream releases the shared L2 port.
      (engine_state_q != ENGINE_PUTM_STREAM) &&
      (!mem_fill_writer_active_q || !dir_snoop_data_to_l2);
    if (victim_snoop_active) begin
      snoop_addr_core[0] = victim_addr_q;
      snoop_addr_core[1] = victim_addr_q;
      snoop_opcode_core[0] = SNOOP_INVALIDATE;
      snoop_opcode_core[1] = SNOOP_INVALIDATE;
      snoop_txn_id_core[0] = engine_txn_q;
      snoop_txn_id_core[1] = engine_txn_q;
      if (engine_state_q == ENGINE_VICTIM_SNOOP_SEND)
        snoop_valid_core[victim_snoop_target_q] = 1'b1;
    end else if (dir_snoop_target)
      snoop_valid_core[1] = dir_snoop_valid && dir_snoop_issue_enable;
    else
      snoop_valid_core[0] = dir_snoop_valid && dir_snoop_issue_enable;
    if (dir_xfer_start_valid && dir_xfer_start_ready &&
        (dir_xfer_kind == XFER_PUTM_TO_L2))
      put_xfer_start_core[dir_xfer_src] = 1'b1;
  end

  always_comb begin : route_snoop_handshake
    dir_snoop_ready = victim_snoop_active ? 1'b0 :
                      (snoop_ready_core[dir_snoop_target] &&
                       dir_snoop_issue_enable);

    dir_snoop_rsp_valid = victim_snoop_active ? 1'b0 :
                          snoop_rsp_valid_core[dir_snoop_target];
    dir_snoop_rsp_src = dir_snoop_target;
    dir_snoop_rsp_opcode = snoop_rsp_opcode_core[dir_snoop_target];
    dir_snoop_rsp_txn_id = snoop_rsp_txn_id_core[dir_snoop_target];
    snoop_rsp_ready_core[0] = 1'b0;
    snoop_rsp_ready_core[1] = 1'b0;
    if (victim_snoop_active)
      snoop_rsp_ready_core[victim_snoop_target_q] =
        (engine_state_q == ENGINE_VICTIM_SNOOP_WAIT);
    else
      snoop_rsp_ready_core[dir_snoop_target] = dir_snoop_rsp_ready;
    victim_snoop_rsp_fire = victim_snoop_active &&
      (engine_state_q == ENGINE_VICTIM_SNOOP_WAIT) &&
      snoop_rsp_valid_core[victim_snoop_target_q] &&
      snoop_rsp_ready_core[victim_snoop_target_q];
  end

  always_comb begin : route_grant_and_data
    grant_valid_core[0] = 1'b0;
    grant_valid_core[1] = 1'b0;
    grant_opcode_core[0] = dir_grant_opcode;
    grant_opcode_core[1] = dir_grant_opcode;
    grant_txn_id_core[0] = dir_grant_txn_id;
    grant_txn_id_core[1] = dir_grant_txn_id;
    if (dir_grant_dst)
      grant_valid_core[1] = dir_grant_valid &&
                            (!dir_grant_has_data ||
                             ((engine_state_q == ENGINE_IDLE) &&
                              !dir_xfer_start_valid));
    else
      grant_valid_core[0] = dir_grant_valid &&
                            (!dir_grant_has_data ||
                             ((engine_state_q == ENGINE_IDLE) &&
                              !dir_xfer_start_valid));
  end

  always_comb begin : route_grant_ready
    dir_grant_ready = grant_ready_core[dir_grant_dst] &&
                      (!dir_grant_has_data ||
                       ((engine_state_q == ENGINE_IDLE) &&
                        !dir_xfer_start_valid));
  end

  always_comb begin : route_grant_commit
    dir_grant_commit_valid = grant_commit_valid_core[0] |
                             grant_commit_valid_core[1];
    dir_grant_commit_src_id = grant_commit_valid_core[0] ? 1'b0 : 1'b1;
    dir_grant_commit_txn_id = grant_commit_valid_core[0] ?
      grant_commit_txn_id_core[0] : grant_commit_txn_id_core[1];
  end

  always_comb begin : route_grant_commit_ready
    grant_commit_ready_core[0] = dir_grant_commit_ready &&
                                 !dir_grant_commit_src_id;
    grant_commit_ready_core[1] = dir_grant_commit_ready &&
                                 dir_grant_commit_src_id;
  end

  always_comb begin : route_grant_data
    grant_data_valid_core[0] = 1'b0;
    grant_data_valid_core[1] = 1'b0;
    grant_data_txn_id_core[0] = grant_txn_q;
    grant_data_txn_id_core[1] = grant_txn_q;
    grant_data_beat_idx_core[0] = l2_line_data_beat_idx;
    grant_data_beat_idx_core[1] = l2_line_data_beat_idx;
    grant_data_core[0] = l2_line_data;
    grant_data_core[1] = l2_line_data;
    grant_data_last_core[0] = l2_line_data_last;
    grant_data_last_core[1] = l2_line_data_last;
    if (engine_state_q == ENGINE_GRANT_STREAM) begin
      grant_data_valid_core[grant_dst_q] = l2_line_data_valid;
    end
  end

  always_comb begin : route_l2_line_data_ready
    // The actual ready mux is written explicitly to avoid a combinational
    // dependency through an unselected core's channel.
    if (engine_state_q == ENGINE_GRANT_STREAM)
      l2_line_data_ready = cluster_grant_data_ready_core[grant_dst_q];
    else if (engine_state_q == ENGINE_VICTIM_WRITE_STREAM)
      l2_line_data_ready = mem_wr_data_ready;
    else
      l2_line_data_ready = 1'b0;
  end

  always_comb begin : issue_l2_line_read
    l2_line_rd_valid = (engine_state_q == ENGINE_GRANT_READ) ||
                       (engine_state_q == ENGINE_VICTIM_READ) ||
                       ((engine_state_q == ENGINE_IDLE) &&
                        dir_grant_valid && dir_grant_ready &&
                        dir_grant_has_data);
    if (engine_state_q == ENGINE_VICTIM_READ)
      l2_line_rd_addr = victim_addr_q;
    else if ((engine_state_q == ENGINE_IDLE) && dir_grant_valid &&
             dir_grant_ready && dir_grant_has_data)
      l2_line_rd_addr = line_align(dir_grant_addr);
    else
      l2_line_rd_addr = grant_addr_q;
  end

  always_comb begin : route_xfer_completion
    dir_xfer_done_valid = (engine_state_q == ENGINE_XFER_DONE) ||
                          ((engine_state_q != ENGINE_XFER_DONE) &&
                           mem_mshr_done_found);
    dir_xfer_done_context_id = (engine_state_q == ENGINE_XFER_DONE) ?
                               engine_context_q :
                               mem_mshr_context_q[mem_mshr_done_sel];
  end

  always_comb begin : route_memory_channels
    mem_rd_req_valid = !reset && !fatal_error &&
                       (engine_state_q == ENGINE_MEM_REQ) &&
                       mem_mshr_alloc_found;
    mem_rd_req_addr = engine_addr_q;
    mem_rd_req_txn_id = TXN_ID_WIDTH'(mem_mshr_alloc_sel);
    // Drain responses for transactions that were already issued, even after a
    // fatal protocol error. Blocking these ready signals can strand an AXI
    // response and feeds the fatal status back into the MSHR/Snoop arbitration
    // network. Fatal status still blocks admission of new requests below.
    mem_rd_data_ready = !reset;
    mem_wr_rsp_ready = !reset;

    mem_wr_req_valid = !reset &&
                       !fatal_error &&
                       (engine_state_q == ENGINE_VICTIM_WRITE_REQ);
    mem_wr_req_addr = victim_addr_q;
    mem_wr_req_txn_id = engine_txn_q;
    mem_wr_data_valid = !reset && !fatal_error &&
                        (engine_state_q == ENGINE_VICTIM_WRITE_STREAM) &&
                        l2_line_data_valid;
    mem_wr_data_beat_idx = l2_line_data_beat_idx;
    mem_wr_data = l2_line_data;
    mem_wr_data_last = l2_line_data_last;
    mem_wr_data_txn_id = engine_txn_q;
  end

  always_comb begin : route_victim_metadata_ops
    l2_entry_invalidate_valid =
      (engine_state_q == ENGINE_VICTIM_INVALIDATE);
    l2_entry_invalidate_addr = victim_addr_q;
    l2_mark_clean_valid = (engine_state_q == ENGINE_VICTIM_MARK_CLEAN);
    l2_mark_clean_addr = victim_addr_q;
  end

  always_comb begin : route_l2_line_write_payload
    l2_line_wr_valid = 1'b0;
    l2_line_wr_addr = 32'b0;
    l2_line_wr_dirty = 1'b0;
    l2_line_wr_beat_idx = 3'b0;
    l2_line_wr_data = 64'b0;
    l2_line_wr_last = 1'b0;
    monitor_owner_data_core = 1'b0;
    monitor_owner_data_addr = 32'b0;
    monitor_owner_data_beat_idx = 3'b0;
    monitor_owner_data = 64'b0;
    monitor_owner_data_last = 1'b0;
    if (engine_state_q == ENGINE_PUTM_STREAM) begin
      l2_line_wr_valid = put_data_valid_core[engine_src_q];
      l2_line_wr_addr = engine_addr_q;
      l2_line_wr_dirty = 1'b1;
      l2_line_wr_beat_idx = put_data_beat_idx_core[engine_src_q];
      l2_line_wr_data = put_data_core[engine_src_q];
      l2_line_wr_last = put_data_last_core[engine_src_q];
    end else if (victim_snoop_data_to_l2) begin
      l2_line_wr_valid = snoop_data_valid_core[victim_snoop_target_q];
      l2_line_wr_addr = victim_addr_q;
      l2_line_wr_dirty = 1'b1;
      l2_line_wr_beat_idx = snoop_data_beat_idx_core[victim_snoop_target_q];
      l2_line_wr_data = snoop_data_core[victim_snoop_target_q];
      l2_line_wr_last = snoop_data_last_core[victim_snoop_target_q];
      monitor_owner_data_core = victim_snoop_target_q;
      monitor_owner_data_addr = victim_addr_q;
      monitor_owner_data_beat_idx =
        snoop_data_beat_idx_core[victim_snoop_target_q];
      monitor_owner_data = snoop_data_core[victim_snoop_target_q];
      monitor_owner_data_last = snoop_data_last_core[victim_snoop_target_q];
    // A refill writer owns the shared L2 line-write port through beat 7.
    // A pending owner-data SnoopRead waits until the refill has drained.
    end else if (mem_fill_writer_active_q) begin
      l2_line_wr_valid = 1'b1;
      l2_line_wr_addr = mem_mshr_addr_q[mem_fill_writer_sel_q];
      l2_line_wr_dirty = 1'b0;
      l2_line_wr_beat_idx = mem_fill_writer_beat_q;
      l2_line_wr_data =
        mem_mshr_data_q[mem_fill_writer_sel_q][mem_fill_writer_beat_q];
      l2_line_wr_last = (mem_fill_writer_beat_q == 3'd7);
    end else if (dir_snoop_data_to_l2) begin
      l2_line_wr_valid = snoop_data_valid_core[dir_snoop_target];
      l2_line_wr_addr = dir_snoop_addr;
      l2_line_wr_dirty = 1'b1;
      l2_line_wr_beat_idx = snoop_data_beat_idx_core[dir_snoop_target];
      l2_line_wr_data = snoop_data_core[dir_snoop_target];
      l2_line_wr_last = snoop_data_last_core[dir_snoop_target];
      monitor_owner_data_core = dir_snoop_target;
      monitor_owner_data_addr = dir_snoop_addr;
      monitor_owner_data_beat_idx = snoop_data_beat_idx_core[dir_snoop_target];
      monitor_owner_data = snoop_data_core[dir_snoop_target];
      monitor_owner_data_last = snoop_data_last_core[dir_snoop_target];
    end
  end

  always_comb begin : route_l2_line_write_ready
    put_data_ready_core[0] = 1'b0;
    put_data_ready_core[1] = 1'b0;
    snoop_data_ready_core[0] = 1'b0;
    snoop_data_ready_core[1] = 1'b0;
    monitor_owner_data_valid = 1'b0;
    if (engine_state_q == ENGINE_PUTM_STREAM) begin
      put_data_ready_core[engine_src_q] = l2_line_wr_ready;
    end else if (victim_snoop_data_to_l2) begin
      snoop_data_ready_core[victim_snoop_target_q] = l2_line_wr_ready;
      monitor_owner_data_valid = snoop_data_valid_core[victim_snoop_target_q] &&
                                 l2_line_wr_ready;
    end else if (mem_fill_writer_active_q) begin
      // Refill stream has priority; hold owner-data Snoop until beat 7.
    end else if (dir_snoop_data_to_l2) begin
      snoop_data_ready_core[dir_snoop_target] = l2_line_wr_ready;
      monitor_owner_data_valid = snoop_data_valid_core[dir_snoop_target] &&
                                 l2_line_wr_ready;
    end
  end

  assign l2_victim_valid = l2_alloc_victim_valid;
  assign l2_victim_addr = l2_alloc_victim_addr;
  assign l2_victim_dir_state = l2_alloc_victim_state;
  assign l2_victim_sharers = l2_alloc_victim_sharers;
  assign l2_victim_owner_id = l2_alloc_victim_owner;
  assign l2_victim_dirty = l2_alloc_victim_dirty;
  assign monitor_dir_commit_valid = !reset && l2_dir_write_valid &&
                                    l2_dir_write_ready;
  assign monitor_dir_commit_addr = l2_dir_write_addr;
  assign monitor_dir_commit_state = l2_dir_write_state;
  assign monitor_dir_commit_sharers = l2_dir_write_sharers;
  assign monitor_dir_commit_owner = l2_dir_write_owner;
  assign l1_victim_valid[0] = l1_replace_valid_core[0];
  assign l1_victim_valid[1] = l1_replace_valid_core[1];
  for (genvar snoop_core = 0; snoop_core < 2; snoop_core = snoop_core + 1) begin : gen_snoop_monitor
    assign monitor_snoop_accept_valid[snoop_core] = !reset &&
      snoop_valid_core[snoop_core] && snoop_ready_core[snoop_core];
    assign monitor_snoop_accept_addr[snoop_core] = snoop_addr_core[snoop_core];
    assign monitor_snoop_accept_opcode[snoop_core] = snoop_opcode_core[snoop_core];
    assign monitor_snoop_accept_txn_id[snoop_core] = snoop_txn_id_core[snoop_core];
    assign monitor_snoop_rsp_valid[snoop_core] = snoop_rsp_valid_core[snoop_core];
    assign monitor_snoop_rsp_ready[snoop_core] = snoop_rsp_ready_core[snoop_core];
    assign monitor_snoop_rsp_txn_id[snoop_core] = snoop_rsp_txn_id_core[snoop_core];
    assign monitor_snoop_rsp_opcode[snoop_core] = snoop_rsp_opcode_core[snoop_core];
  end

  /* verilator lint_off PINCONNECTEMPTY */
  DualL1MesiCluster #(.TXN_ID_WIDTH(TXN_ID_WIDTH)) l1_cluster (
    .clock(clock), .reset(reset),
    .cpu_req_valid(cluster_cpu_req_valid), .cpu_req_ready(cluster_cpu_req_ready),
    .cpu_req_addr(cpu_req_addr), .cpu_req_write(cpu_req_write),
    .cpu_req_wmask(cpu_req_wmask), .cpu_req_wdata(cpu_req_wdata),
    .cpu_resp_valid(cluster_cpu_resp_valid),
    .cpu_resp_ready(cluster_cpu_resp_ready),
    .cpu_resp_addr(cluster_cpu_resp_addr), .cpu_resp_write(cluster_cpu_resp_write),
    .cpu_resp_rdata(cluster_cpu_resp_rdata),
    .cpu_resp_txn_id(cluster_cpu_resp_txn_id),
    .cpu_hit_event(cluster_perf_hit_event),
    .cpu_miss_event(cluster_perf_miss_event),
    .metadata_commit_valid(metadata_commit_valid),
    .metadata_commit_line_addr(metadata_commit_line_addr),
    .metadata_commit_state(metadata_commit_state),
    .metadata_commit_is_snoop(metadata_commit_is_snoop),
    .dir_req_valid(cluster_dir_req_valid),
    .dir_req_ready_from_directory(dir_req_ready),
    .dir_req_src_id(cluster_dir_req_src_id),
    .dir_req_opcode(cluster_dir_req_opcode),
    .dir_req_line_addr(cluster_dir_req_addr), .dir_req_txn_id(cluster_dir_req_txn_id),
    .put_xfer_start(put_xfer_start_core),
    .put_xfer_addr(put_xfer_addr_core),
    .put_xfer_txn_id(put_xfer_txn_id_core),
    .put_data_valid(put_data_valid_core),
    .put_data_ready(put_data_ready_core),
    .put_data_beat_idx(put_data_beat_idx_core),
    .put_data(put_data_core), .put_data_last(put_data_last_core),
    .grant_valid(grant_valid_core), .grant_ready(grant_ready_core),
    .grant_opcode(grant_opcode_core), .grant_txn_id(grant_txn_id_core),
    .grant_data_valid(grant_data_valid_core),
    .grant_data_ready(cluster_grant_data_ready_core),
    .grant_data_txn_id(grant_data_txn_id_core),
    .grant_data_beat_idx(grant_data_beat_idx_core),
    .grant_data(grant_data_core), .grant_data_last(grant_data_last_core),
    .grant_commit_valid(grant_commit_valid_core),
    .grant_commit_ready(grant_commit_ready_core),
    .grant_commit_txn_id(grant_commit_txn_id_core),
    .snoop_valid(snoop_valid_core), .snoop_ready(snoop_ready_core),
    .snoop_line_addr(snoop_addr_core), .snoop_opcode(snoop_opcode_core),
    .snoop_txn_id(snoop_txn_id_core),
    .snoop_rsp_valid(snoop_rsp_valid_core),
    .snoop_rsp_ready(snoop_rsp_ready_core),
    .snoop_rsp_opcode(snoop_rsp_opcode_core),
    .snoop_rsp_txn_id(snoop_rsp_txn_id_core),
    .snoop_rsp_has_data(snoop_rsp_has_data_core),
    .snoop_data_valid(snoop_data_valid_core),
    .snoop_data_ready(snoop_data_ready_core),
    .snoop_data_txn_id(snoop_data_txn_id_core),
    .snoop_data_beat_idx(snoop_data_beat_idx_core),
    .snoop_data(snoop_data_core), .snoop_data_last(snoop_data_last_core),
    .replace_valid(l1_replace_valid_core), .replace_way(),
    .replace_state(l1_victim_state), .replace_line_addr(l1_victim_addr),
    .controller_protocol_error(l1_controller_protocol_error),
    .array_protocol_error(l1_array_protocol_error),
    .monitor_cpu_state(monitor_cpu_state),
    .monitor_snoop_state(monitor_l1_snoop_state),
    .monitor_cpu_active_addr(monitor_cpu_active_addr),
    .monitor_replace_state(monitor_l1_replace_state)
  );
  /* verilator lint_on PINCONNECTEMPTY */

  DirectoryMshrBank #(
    .TXN_ID_WIDTH(TXN_ID_WIDTH), .NUM_MSHRS(NUM_MSHRS),
    .L2_SET_INDEX_WIDTH(9)
  ) directory_controller (
    .clock(clock), .reset(reset),
    .req_valid(cluster_dir_req_valid && dir_lookup_available),
    .req_ready(dir_bank_req_ready),
    .req_src_id(cluster_dir_req_src_id), .req_opcode(cluster_dir_req_opcode),
    .req_line_addr(cluster_dir_req_addr), .req_txn_id(cluster_dir_req_txn_id),
    .lookup_dir_state(l2_lookup_state), .lookup_sharers(l2_lookup_sharers),
    .lookup_owner_id(l2_lookup_owner),
    .dir_write_valid(dir_write_valid), .dir_write_ready(dir_write_ready),
    .dir_write_line_addr(dir_write_addr), .dir_write_state(dir_write_state),
    .dir_write_sharers(dir_write_sharers), .dir_write_owner_id(dir_write_owner),
    .snoop_req_valid(dir_snoop_valid), .snoop_req_ready(dir_snoop_ready),
    .snoop_target_id(dir_snoop_target), .snoop_req_opcode(dir_snoop_opcode),
    .snoop_req_line_addr(dir_snoop_addr), .snoop_req_txn_id(dir_snoop_txn_id),
    .snoop_rsp_valid(dir_snoop_rsp_valid), .snoop_rsp_ready(dir_snoop_rsp_ready),
    .snoop_rsp_src_id(dir_snoop_rsp_src), .snoop_rsp_opcode(dir_snoop_rsp_opcode),
    .snoop_rsp_txn_id(dir_snoop_rsp_txn_id),
    .line_xfer_start_valid(dir_xfer_start_valid),
    .line_xfer_start_ready(dir_xfer_start_ready), .line_xfer_kind(dir_xfer_kind),
    .line_xfer_addr(dir_xfer_addr), .line_xfer_src_id(dir_xfer_src),
    .line_xfer_txn_id(dir_xfer_txn_id),
    .line_xfer_context_id(dir_xfer_context_id),
    .line_xfer_done_valid(dir_xfer_done_valid),
    .line_xfer_done_ready(dir_xfer_done_ready),
    .line_xfer_done_context_id(dir_xfer_done_context_id),
    .grant_valid(dir_grant_valid), .grant_ready(dir_grant_ready),
    .grant_dst_id(dir_grant_dst), .grant_opcode(dir_grant_opcode),
    .grant_has_data(dir_grant_has_data), .grant_line_addr(dir_grant_addr),
    .grant_txn_id(dir_grant_txn_id),
    .grant_commit_valid(dir_grant_commit_valid),
    .grant_commit_ready(dir_grant_commit_ready),
    .grant_commit_src_id(dir_grant_commit_src_id),
    .grant_commit_txn_id(dir_grant_commit_txn_id),
    .snoop_data_to_l2(dir_snoop_data_to_l2),
    .protocol_error(directory_protocol_error),
    .protocol_error_code(directory_protocol_error_code),
    .monitor_active_contexts(monitor_directory_active_contexts)
  );

  SharedL2DirectoryArray #(.SETS(512), .WAYS(8), .TAG_WIDTH(17)) l2_array (
    .clock(clock), .reset(reset), .lookup_addr(l2_lookup_addr),
    .lookup_hit(l2_lookup_hit), .lookup_way(l2_lookup_way),
    .lookup_dir_state(l2_lookup_state), .lookup_sharers(l2_lookup_sharers),
    .lookup_owner_id(l2_lookup_owner),
    .dir_write_valid(l2_dir_write_valid), .dir_write_ready(l2_dir_write_ready),
    .dir_write_line_addr(l2_dir_write_addr), .dir_write_state(l2_dir_write_state),
    .dir_write_sharers(l2_dir_write_sharers), .dir_write_owner_id(l2_dir_write_owner),
    .alloc_addr(l2_alloc_addr), .alloc_victim_valid(l2_alloc_victim_valid),
    .alloc_way(l2_alloc_way), .alloc_victim_addr(l2_alloc_victim_addr),
    .alloc_victim_dir_state(l2_alloc_victim_state),
    .alloc_victim_sharers(l2_alloc_victim_sharers),
    .alloc_victim_owner_id(l2_alloc_victim_owner),
    .alloc_victim_dirty(l2_alloc_victim_dirty),
    .entry_invalidate_valid(l2_entry_invalidate_valid),
    .entry_invalidate_ready(l2_entry_invalidate_ready),
    .entry_invalidate_line_addr(l2_entry_invalidate_addr),
    .mark_clean_valid(l2_mark_clean_valid),
    .mark_clean_ready(l2_mark_clean_ready),
    .mark_clean_line_addr(l2_mark_clean_addr),
    .line_wr_valid(l2_line_wr_valid), .line_wr_ready(l2_line_wr_ready),
    .line_wr_addr(l2_line_wr_addr), .line_wr_dirty(l2_line_wr_dirty),
    .line_wr_beat_idx(l2_line_wr_beat_idx), .line_wr_data(l2_line_wr_data),
    .line_wr_last(l2_line_wr_last),
    .line_rd_valid(l2_line_rd_valid), .line_rd_ready(l2_line_rd_ready),
    .line_rd_addr(l2_line_rd_addr), .line_rd_hit(l2_line_rd_hit),
    .line_data_valid(l2_line_data_valid), .line_data_ready(l2_line_data_ready),
    .line_data_beat_idx(l2_line_data_beat_idx), .line_data(l2_line_data),
    .line_data_last(l2_line_data_last), .protocol_error(l2_protocol_error)
  );

  always_ff @(posedge clock) begin
    if (reset) begin
      mmio_state_q <= MMIO_IDLE;
      mmio_txn_counter_q <= '0;
      mmio_txn_q <= '0;
      mmio_addr_q <= '0;
      mmio_write_q <= 1'b0;
      mmio_wmask_q <= '0;
      mmio_wdata_q <= '0;
      mmio_owner_q <= 1'b0;
      mmio_prefer_core1_q <= 1'b0;
      mmio_protocol_error <= 1'b0;
    end else begin
      if (mmio_resp_valid && (mmio_state_q != MMIO_WAIT_RESP))
        mmio_protocol_error <= 1'b1;

      case (mmio_state_q)
        MMIO_IDLE: begin
          if (mmio_accept) begin
            mmio_owner_q <= mmio_select_core;
            mmio_txn_q <= mmio_txn_counter_q;
            mmio_txn_counter_q <= mmio_txn_counter_q + 1'b1;
            mmio_addr_q <= cpu_req_addr[mmio_select_core];
            mmio_write_q <= cpu_req_write[mmio_select_core];
            mmio_wmask_q <= cpu_req_wmask[mmio_select_core];
            mmio_wdata_q <= cpu_req_wdata[mmio_select_core];
            mmio_state_q <= MMIO_SEND_REQ;
          end
        end

        MMIO_SEND_REQ: begin
          if (mmio_req_valid && mmio_req_ready)
            mmio_state_q <= MMIO_WAIT_RESP;
        end

        MMIO_WAIT_RESP: begin
          if (mmio_resp_valid && mmio_resp_ready) begin
            mmio_prefer_core1_q <= ~mmio_owner_q;
            mmio_state_q <= MMIO_IDLE;
          end
        end

        default: begin
          mmio_protocol_error <= 1'b1;
          mmio_state_q <= MMIO_IDLE;
        end
      endcase
    end
  end

  always_ff @(posedge clock) begin
    if (reset || fatal_error) begin
      perf_inflight_q <= 2'b00;
    end else begin
      for (integer perf_idx = 0; perf_idx < 2; perf_idx = perf_idx + 1) begin
        if (perf_access_complete_event[perf_idx])
          perf_inflight_q[perf_idx] <= 1'b0;
        else if (cpu_req_valid[perf_idx] && cpu_req_ready[perf_idx] &&
                 !cpu_req_is_mmio[perf_idx])
          perf_inflight_q[perf_idx] <= 1'b1;
      end
    end
  end

  always_ff @(posedge clock) begin : memory_mshr_table
    if (reset) begin
      mem_mshr_valid_q <= '0;
      mem_mshr_full_q <= '0;
      mem_mshr_written_q <= '0;
      mem_mshr_done_rr_q <= '0;
      mem_mshr_fill_rr_q <= '0;
      mem_fill_writer_active_q <= 1'b0;
      mem_fill_writer_sel_q <= '0;
      mem_fill_writer_beat_q <= '0;
      for (integer i = 0; i < NUM_MSHRS; i = i + 1) begin
        mem_mshr_addr_q[i] <= '0;
        mem_mshr_context_q[i] <= '0;
        mem_mshr_expected_q[i] <= '0;
      end
    end else begin
      if ((engine_state_q == ENGINE_MEM_REQ) &&
          mem_rd_req_valid && mem_rd_req_ready) begin
        mem_mshr_valid_q[mem_mshr_alloc_sel] <= 1'b1;
        mem_mshr_full_q[mem_mshr_alloc_sel] <= 1'b0;
        mem_mshr_written_q[mem_mshr_alloc_sel] <= 1'b0;
        mem_mshr_addr_q[mem_mshr_alloc_sel] <= engine_addr_q;
        mem_mshr_context_q[mem_mshr_alloc_sel] <= engine_context_q;
        mem_mshr_expected_q[mem_mshr_alloc_sel] <= '0;
      end

      if (mem_rd_data_valid && mem_rd_data_ready && mem_mshr_r_match &&
          !mem_rd_data_error &&
          (mem_rd_data_beat_idx == mem_mshr_expected_q[mem_mshr_r_sel]) &&
          (mem_rd_data_last == (mem_rd_data_beat_idx == 3'd7))) begin
        mem_mshr_data_q[mem_mshr_r_sel][mem_rd_data_beat_idx] <= mem_rd_data;
        if (mem_rd_data_beat_idx == 3'd7)
          mem_mshr_full_q[mem_mshr_r_sel] <= 1'b1;
        else
          mem_mshr_expected_q[mem_mshr_r_sel] <=
            mem_mshr_expected_q[mem_mshr_r_sel] + 1'b1;
      end

      if (!mem_fill_writer_active_q && mem_mshr_fill_found &&
          !victim_snoop_active &&
          !(dir_snoop_data_to_l2 && !dir_snoop_valid) &&
          !(dir_snoop_valid && !snoop_set_conflict) &&
          ((engine_state_q == ENGINE_IDLE &&
            !(dir_xfer_start_valid && dir_xfer_start_ready)) ||
           (engine_state_q == ENGINE_GRANT_READ) ||
           (engine_state_q == ENGINE_GRANT_STREAM))) begin
        mem_fill_writer_active_q <= 1'b1;
        mem_fill_writer_sel_q <= mem_mshr_fill_sel;
        mem_fill_writer_beat_q <= '0;
      end else if (mem_fill_writer_active_q && l2_line_wr_valid &&
                   l2_line_wr_ready) begin
        if (mem_fill_writer_beat_q == 3'd7) begin
          mem_fill_writer_active_q <= 1'b0;
          mem_fill_writer_beat_q <= '0;
          mem_mshr_written_q[mem_fill_writer_sel_q] <= 1'b1;
          mem_mshr_fill_rr_q <=
            (mem_fill_writer_sel_q == MSHR_ID_WIDTH'(NUM_MSHRS-1)) ? '0 :
            mem_fill_writer_sel_q + 1'b1;
        end else begin
          mem_fill_writer_beat_q <= mem_fill_writer_beat_q + 1'b1;
        end
      end

      if ((engine_state_q != ENGINE_XFER_DONE) && mem_mshr_done_found &&
          dir_xfer_done_valid && dir_xfer_done_ready) begin
        mem_mshr_valid_q[mem_mshr_done_sel] <= 1'b0;
        mem_mshr_full_q[mem_mshr_done_sel] <= 1'b0;
        mem_mshr_written_q[mem_mshr_done_sel] <= 1'b0;
        mem_mshr_done_rr_q <=
          (mem_mshr_done_sel == MSHR_ID_WIDTH'(NUM_MSHRS-1)) ? '0 :
          mem_mshr_done_sel + 1'b1;
      end
    end
  end

  always_ff @(posedge clock) begin
    if (reset) begin
      engine_state_q <= ENGINE_IDLE;
      engine_addr_q <= '0;
      engine_txn_q <= '0;
      engine_context_q <= '0;
      engine_src_q <= 1'b0;
      mem_expected_beat_q <= '0;
      victim_expected_beat_q <= '0;
      victim_addr_q <= '0;
      victim_pending_targets_q <= 2'b00;
      victim_snoop_target_q <= 1'b0;
      victim_snoop_data_expected_q <= 1'b0;
      victim_snoop_data_complete_q <= 1'b0;
      victim_dirty_q <= 1'b0;
      grant_dst_q <= 1'b0;
      grant_addr_q <= '0;
      grant_txn_q <= '0;
      memory_adapter_protocol_error <= 1'b0;
      memory_adapter_error <= 1'b0;
    end else begin
      if (mem_r_protocol_bad) begin
        memory_adapter_protocol_error <= 1'b1;
        engine_state_q <= ENGINE_ERROR;
      end else if (mem_rd_data_valid && mem_rd_data_ready &&
                   mem_mshr_r_match && mem_rd_data_error) begin
        memory_adapter_error <= 1'b1;
        engine_state_q <= ENGINE_ERROR;
      end else if (mem_wr_rsp_valid && mem_wr_rsp_ready &&
                   (engine_state_q != ENGINE_VICTIM_WRITE_WAIT_RSP)) begin
        memory_adapter_protocol_error <= 1'b1;
        engine_state_q <= ENGINE_ERROR;
      end else case (engine_state_q)
        ENGINE_IDLE: begin
          if (dir_xfer_start_valid && dir_xfer_start_ready) begin
            engine_addr_q <= line_align(dir_xfer_addr);
            engine_txn_q <= dir_xfer_txn_id;
            engine_context_q <= dir_xfer_context_id;
            mem_expected_beat_q <= '0;
            if (dir_xfer_kind == XFER_L2_REFILL) begin
              if (l2_lookup_hit)
                engine_state_q <= ENGINE_XFER_DONE;
              else if (l2_alloc_victim_valid) begin
                victim_addr_q <= l2_alloc_victim_addr;
                victim_dirty_q <= l2_alloc_victim_dirty;
                victim_snoop_data_complete_q <= 1'b0;
                if ((l2_alloc_victim_state == DIR_I) &&
                    (l2_alloc_victim_sharers == 2'b00) &&
                    !l2_alloc_victim_owner) begin
                  if (l2_alloc_victim_dirty)
                    engine_state_q <= ENGINE_VICTIM_READ;
                  else
                    engine_state_q <= ENGINE_VICTIM_INVALIDATE;
                end else if ((l2_alloc_victim_state == DIR_S) &&
                             (l2_alloc_victim_sharers != 2'b00) &&
                             !l2_alloc_victim_owner) begin
                  victim_pending_targets_q <= l2_alloc_victim_sharers;
                  victim_snoop_target_q <= !l2_alloc_victim_sharers[0];
                  victim_snoop_data_expected_q <= 1'b0;
                  engine_state_q <= ENGINE_VICTIM_SNOOP_SEND;
                end else if ((l2_alloc_victim_state == DIR_U) &&
                             (l2_alloc_victim_sharers == 2'b00)) begin
                  victim_pending_targets_q <= l2_alloc_victim_owner ?
                                              2'b10 : 2'b01;
                  victim_snoop_target_q <= l2_alloc_victim_owner;
                  victim_snoop_data_expected_q <= 1'b1;
                  victim_snoop_data_complete_q <= 1'b0;
                  victim_dirty_q <= 1'b1;
                  mem_expected_beat_q <= 3'd0;
                  engine_state_q <= ENGINE_VICTIM_SNOOP_SEND;
                end else begin
                  memory_adapter_protocol_error <= 1'b1;
                  engine_state_q <= ENGINE_ERROR;
                end
              end else
                engine_state_q <= ENGINE_MEM_REQ;
            end else if (dir_xfer_kind == XFER_PUTM_TO_L2) begin
              engine_src_q <= dir_xfer_src;
              engine_state_q <= ENGINE_PUTM_STREAM;
            end else begin
              memory_adapter_protocol_error <= 1'b1;
              engine_state_q <= ENGINE_ERROR;
            end
          end else if (dir_grant_valid && dir_grant_ready &&
                       dir_grant_has_data) begin
            grant_dst_q <= dir_grant_dst;
            grant_addr_q <= line_align(dir_grant_addr);
            grant_txn_q <= dir_grant_txn_id;
            if (l2_line_rd_valid && l2_line_rd_ready) begin
              if (l2_line_rd_hit)
                engine_state_q <= ENGINE_GRANT_STREAM;
              else begin
                memory_adapter_protocol_error <= 1'b1;
                engine_state_q <= ENGINE_ERROR;
              end
            end else begin
              engine_state_q <= ENGINE_GRANT_READ;
            end
          end
        end

        ENGINE_VICTIM_READ: begin
          if (l2_line_rd_valid && l2_line_rd_ready) begin
            if (l2_line_rd_hit) begin
              victim_expected_beat_q <= 3'd0;
              engine_state_q <= ENGINE_VICTIM_WRITE_REQ;
            end else begin
              memory_adapter_protocol_error <= 1'b1;
              engine_state_q <= ENGINE_ERROR;
            end
          end
        end

        ENGINE_VICTIM_WRITE_REQ: begin
          if (mem_wr_req_valid && mem_wr_req_ready)
            engine_state_q <= ENGINE_VICTIM_WRITE_STREAM;
        end

        ENGINE_VICTIM_WRITE_STREAM: begin
          if (mem_wr_data_valid && mem_wr_data_ready) begin
            if ((mem_wr_data_beat_idx != victim_expected_beat_q) ||
                (mem_wr_data_last != (mem_wr_data_beat_idx == 3'd7))) begin
              memory_adapter_protocol_error <= 1'b1;
              engine_state_q <= ENGINE_ERROR;
            end else if (mem_wr_data_beat_idx == 3'd7) begin
              engine_state_q <= ENGINE_VICTIM_WRITE_WAIT_RSP;
            end else begin
              victim_expected_beat_q <= victim_expected_beat_q + 1'b1;
            end
          end
        end

        ENGINE_VICTIM_WRITE_WAIT_RSP: begin
          if (mem_wr_rsp_valid && mem_wr_rsp_ready) begin
            if (mem_wr_rsp_txn_id != engine_txn_q) begin
              memory_adapter_protocol_error <= 1'b1;
              engine_state_q <= ENGINE_ERROR;
            end else if (mem_wr_rsp_error) begin
              memory_adapter_error <= 1'b1;
              engine_state_q <= ENGINE_ERROR;
            end else begin
              engine_state_q <= ENGINE_VICTIM_MARK_CLEAN;
            end
          end
        end

        ENGINE_VICTIM_MARK_CLEAN: begin
          if (l2_mark_clean_valid && l2_mark_clean_ready)
            engine_state_q <= ENGINE_VICTIM_INVALIDATE;
        end

        ENGINE_VICTIM_INVALIDATE: begin
          if (l2_entry_invalidate_valid && l2_entry_invalidate_ready)
            engine_state_q <= ENGINE_MEM_REQ;
        end

        ENGINE_VICTIM_SNOOP_SEND: begin
          if (snoop_valid_core[victim_snoop_target_q] &&
              snoop_ready_core[victim_snoop_target_q])
            engine_state_q <= ENGINE_VICTIM_SNOOP_WAIT;
        end

        ENGINE_VICTIM_SNOOP_WAIT: begin
          if (victim_snoop_data_to_l2 && l2_line_wr_valid && l2_line_wr_ready) begin
            if ((l2_line_wr_beat_idx != mem_expected_beat_q) ||
                (l2_line_wr_last != (l2_line_wr_beat_idx == 3'd7)) ||
                (snoop_data_txn_id_core[victim_snoop_target_q] != engine_txn_q)) begin
              memory_adapter_protocol_error <= 1'b1;
              engine_state_q <= ENGINE_ERROR;
            end else if (l2_line_wr_beat_idx == 3'd7) begin
              victim_snoop_data_complete_q <= 1'b1;
              mem_expected_beat_q <= 3'd0;
            end else begin
              mem_expected_beat_q <= mem_expected_beat_q + 1'b1;
            end
          end

          if (victim_snoop_rsp_fire) begin
            if ((snoop_rsp_txn_id_core[victim_snoop_target_q] != engine_txn_q) ||
                (victim_snoop_data_expected_q &&
                 !((snoop_rsp_opcode_core[victim_snoop_target_q] == SNOOP_RSP_DATA &&
                    snoop_rsp_has_data_core[victim_snoop_target_q] &&
                    victim_snoop_data_complete_q) ||
                   victim_owner_retired_before_snoop)) ||
                (!victim_snoop_data_expected_q &&
                 ((snoop_rsp_opcode_core[victim_snoop_target_q] != SNOOP_RSP_INV_ACK) ||
                  snoop_rsp_has_data_core[victim_snoop_target_q]))) begin
              memory_adapter_protocol_error <= 1'b1;
              engine_state_q <= ENGINE_ERROR;
            end else begin
              victim_pending_targets_q <= victim_targets_after_current;
              victim_snoop_data_expected_q <= 1'b0;
              victim_snoop_data_complete_q <= 1'b0;
              if (victim_targets_after_current == 2'b00)
                engine_state_q <= ENGINE_VICTIM_CLEAR_DIR;
              else begin
                victim_snoop_target_q <= !victim_targets_after_current[0];
                engine_state_q <= ENGINE_VICTIM_SNOOP_SEND;
              end
            end
          end
        end

        ENGINE_VICTIM_CLEAR_DIR: begin
          if (l2_dir_write_ready) begin
            if (victim_dirty_q)
              engine_state_q <= ENGINE_VICTIM_READ;
            else
              engine_state_q <= ENGINE_VICTIM_INVALIDATE;
          end
        end

        ENGINE_MEM_REQ: begin
          if (mem_rd_req_valid && mem_rd_req_ready)
            engine_state_q <= ENGINE_IDLE;
        end

        ENGINE_PUTM_STREAM: begin
          if (l2_line_wr_valid && l2_line_wr_ready) begin
            if ((l2_line_wr_beat_idx != mem_expected_beat_q) ||
                (l2_line_wr_last != (l2_line_wr_beat_idx == 3'd7))) begin
              memory_adapter_protocol_error <= 1'b1;
              engine_state_q <= ENGINE_ERROR;
            end else if (l2_line_wr_beat_idx == 3'd7) begin
              engine_state_q <= ENGINE_XFER_DONE;
            end else begin
              mem_expected_beat_q <= mem_expected_beat_q + 1'b1;
            end
          end
        end

        ENGINE_XFER_DONE: begin
          if (dir_xfer_done_valid && dir_xfer_done_ready)
            engine_state_q <= ENGINE_IDLE;
        end

        ENGINE_GRANT_READ: begin
          if (l2_line_rd_valid && l2_line_rd_ready) begin
            if (l2_line_rd_hit)
              engine_state_q <= ENGINE_GRANT_STREAM;
            else begin
              memory_adapter_protocol_error <= 1'b1;
              engine_state_q <= ENGINE_ERROR;
            end
          end
        end

        ENGINE_GRANT_STREAM: begin
          if (l2_line_data_valid && l2_line_data_ready && l2_line_data_last)
            engine_state_q <= ENGINE_IDLE;
        end

        ENGINE_ERROR: engine_state_q <= ENGINE_ERROR;

        default: begin
          memory_adapter_protocol_error <= 1'b1;
          engine_state_q <= ENGINE_ERROR;
        end
      endcase
    end
  end
endmodule
