// Blocking dual-LSU subsystem: two private MESI L1s, one Directory, one
// inclusive shared L2 array, and line-oriented backing-memory ports. L2
// victims are reclaimed only after their inclusive L1 copies are invalidated.
module CoherentCacheSubsystem #(
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
  // echoes mem_rd_req_txn_id on every response beat.
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

  // Dirty L2 victims are written back as eight 64-bit beats. Completion is
  // the handshake of beat 7; the memory model has no separate write response.
  // Request and every data beat carry the same transaction ID.
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
  output logic l2_protocol_error,
  output logic memory_adapter_protocol_error,
  output logic mmio_protocol_error
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

  logic [1:0] cluster_dir_req_ready;
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

  logic dir_req_ready;
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
  logic [TXN_ID_WIDTH-1:0] dir_xfer_done_txn_id;
  logic dir_grant_valid, dir_grant_ready, dir_grant_dst;
  grant_opcode_t dir_grant_opcode;
  logic dir_grant_has_data;
  logic [31:0] dir_grant_addr;
  logic [TXN_ID_WIDTH-1:0] dir_grant_txn_id;
  logic dir_grant_commit_valid, dir_grant_commit_ready;
  logic [TXN_ID_WIDTH-1:0] dir_grant_commit_txn_id;
  logic dir_snoop_data_to_l2;
  logic victim_snoop_active, victim_snoop_data_to_l2;
  logic victim_snoop_rsp_fire;
  logic [1:0] victim_pending_targets_q;
  logic [1:0] victim_targets_after_current;
  logic victim_snoop_target_q, victim_snoop_data_expected_q;
  logic victim_snoop_data_complete_q, victim_dirty_q;

  logic [31:0] l2_lookup_addr;
  logic l2_lookup_hit;
  logic [2:0] l2_lookup_way;
  directory_state_t l2_lookup_state;
  logic [1:0] l2_lookup_sharers;
  logic l2_lookup_owner;
  logic [31:0] l2_alloc_addr;
  logic l2_alloc_victim_valid;
  logic [2:0] l2_alloc_way;
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

  typedef enum logic [3:0] {
    ENGINE_IDLE,
    ENGINE_VICTIM_READ,
    ENGINE_VICTIM_WRITE_REQ,
    ENGINE_VICTIM_WRITE_STREAM,
    ENGINE_VICTIM_MARK_CLEAN,
    ENGINE_VICTIM_INVALIDATE,
    ENGINE_PUTM_STREAM,
    ENGINE_MEM_REQ,
    ENGINE_MEM_STREAM,
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

  assign victim_snoop_active =
    (engine_state_q == ENGINE_VICTIM_SNOOP_SEND) ||
    (engine_state_q == ENGINE_VICTIM_SNOOP_WAIT);
  assign victim_snoop_data_to_l2 =
    (engine_state_q == ENGINE_VICTIM_SNOOP_WAIT) &&
    victim_snoop_data_expected_q;
  assign victim_targets_after_current = victim_pending_targets_q &
    ~(victim_snoop_target_q ? 2'b10 : 2'b01);
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

  assign l2_lookup_addr = cluster_dir_req_valid ? cluster_dir_req_addr :
                          dir_xfer_start_valid ? dir_xfer_addr :
                          dir_grant_valid ? dir_grant_addr : engine_addr_q;
  assign l2_alloc_addr = dir_xfer_start_valid ? dir_xfer_addr : engine_addr_q;

  assign mmio_owner_pending = (mmio_state_q != MMIO_IDLE);

  always_comb begin
    for (integer core = 0; core < 2; core = core + 1) begin
      cpu_req_is_mmio[core] = (cpu_req_addr[core] >= 32'h3000_0000) &&
                              (cpu_req_addr[core] <  32'h8000_0000);
      cluster_cpu_req_valid[core] = cpu_req_valid[core] &&
                                    !cpu_req_is_mmio[core] &&
                                    !(mmio_owner_pending &&
                                      (mmio_owner_q == 1'(core)));
      cluster_cpu_resp_ready[core] = cpu_resp_ready[core] &&
                                     !(mmio_owner_pending &&
                                       (mmio_owner_q == 1'(core)));
      mmio_candidates[core] = cpu_req_valid[core] &&
                              cpu_req_is_mmio[core] &&
                              !reset &&
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
      cpu_req_ready[core] = !reset && (cpu_req_is_mmio[core] ?
        (mmio_accept && (mmio_select_core == 1'(core))) :
        (cluster_cpu_req_ready[core] &&
         !(mmio_owner_pending && (mmio_owner_q == 1'(core)))));
      mmio_resp_to_core[core] = (mmio_state_q == MMIO_WAIT_RESP) &&
                                mmio_resp_valid &&
                                (mmio_owner_q == 1'(core));
      cpu_resp_valid[core] = !reset && (cluster_cpu_resp_valid[core] ||
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

    mmio_req_valid = !reset && (mmio_state_q == MMIO_SEND_REQ);
    mmio_req_addr = mmio_addr_q;
    mmio_req_size = 3'b011;
    mmio_req_write = mmio_write_q;
    mmio_req_wmask = mmio_wmask_q;
    mmio_req_wdata = mmio_wdata_q;
    mmio_resp_ready = !reset && (mmio_state_q == MMIO_WAIT_RESP) &&
                      cpu_resp_ready[mmio_owner_q];
  end

  always_comb begin
    dir_xfer_start_ready = (engine_state_q == ENGINE_IDLE);
    snoop_valid_core[0] = 1'b0;
    snoop_valid_core[1] = 1'b0;
    put_xfer_start_core[0] = 1'b0;
    put_xfer_start_core[1] = 1'b0;
    put_xfer_addr_core[0] = dir_xfer_addr;
    put_xfer_addr_core[1] = dir_xfer_addr;
    put_xfer_txn_id_core[0] = dir_xfer_txn_id;
    put_xfer_txn_id_core[1] = dir_xfer_txn_id;
    put_data_ready_core[0] = 1'b0;
    put_data_ready_core[1] = 1'b0;
    snoop_addr_core[0] = dir_snoop_addr;
    snoop_addr_core[1] = dir_snoop_addr;
    snoop_opcode_core[0] = dir_snoop_opcode;
    snoop_opcode_core[1] = dir_snoop_opcode;
    snoop_txn_id_core[0] = dir_snoop_txn_id;
    snoop_txn_id_core[1] = dir_snoop_txn_id;
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
      snoop_valid_core[1] = dir_snoop_valid;
    else
      snoop_valid_core[0] = dir_snoop_valid;
    if (dir_xfer_start_valid && dir_xfer_start_ready &&
        (dir_xfer_kind == XFER_PUTM_TO_L2))
      put_xfer_start_core[dir_xfer_src] = 1'b1;
    dir_snoop_ready = victim_snoop_active ? 1'b0 :
                      snoop_ready_core[dir_snoop_target];

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

    grant_valid_core[0] = 1'b0;
    grant_valid_core[1] = 1'b0;
    grant_opcode_core[0] = dir_grant_opcode;
    grant_opcode_core[1] = dir_grant_opcode;
    grant_txn_id_core[0] = dir_grant_txn_id;
    grant_txn_id_core[1] = dir_grant_txn_id;
    if (dir_grant_dst)
      grant_valid_core[1] = dir_grant_valid;
    else
      grant_valid_core[0] = dir_grant_valid;
    dir_grant_ready = grant_ready_core[dir_grant_dst];

    dir_grant_commit_valid = grant_commit_valid_core[0] |
                             grant_commit_valid_core[1];
    dir_grant_commit_txn_id = grant_commit_valid_core[0] ?
      grant_commit_txn_id_core[0] : grant_commit_txn_id_core[1];
    grant_commit_ready_core[0] = dir_grant_commit_ready;
    grant_commit_ready_core[1] = dir_grant_commit_ready;

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

    // The actual ready mux is written explicitly to avoid a combinational
    // dependency through an unselected core's channel.
    if (engine_state_q == ENGINE_GRANT_STREAM)
      l2_line_data_ready = cluster_grant_data_ready_core[grant_dst_q];
    else if (engine_state_q == ENGINE_VICTIM_WRITE_STREAM)
      l2_line_data_ready = mem_wr_data_ready;
    else
      l2_line_data_ready = 1'b0;

    l2_line_rd_valid = (engine_state_q == ENGINE_GRANT_READ) ||
                       (engine_state_q == ENGINE_VICTIM_READ);
    l2_line_rd_addr = (engine_state_q == ENGINE_VICTIM_READ) ?
                      victim_addr_q : grant_addr_q;
    dir_xfer_done_valid = (engine_state_q == ENGINE_XFER_DONE);
    dir_xfer_done_txn_id = engine_txn_q;

    mem_rd_req_valid = !reset && (engine_state_q == ENGINE_MEM_REQ);
    mem_rd_req_addr = engine_addr_q;
    mem_rd_req_txn_id = engine_txn_q;
    mem_rd_data_ready = !reset &&
                        (engine_state_q == ENGINE_MEM_STREAM) &&
                        ((mem_rd_data_txn_id != engine_txn_q) ||
                         l2_line_wr_ready);

    mem_wr_req_valid = !reset &&
                       (engine_state_q == ENGINE_VICTIM_WRITE_REQ);
    mem_wr_req_addr = victim_addr_q;
    mem_wr_req_txn_id = engine_txn_q;
    mem_wr_data_valid = !reset &&
                        (engine_state_q == ENGINE_VICTIM_WRITE_STREAM) &&
                        l2_line_data_valid;
    mem_wr_data_beat_idx = l2_line_data_beat_idx;
    mem_wr_data = l2_line_data;
    mem_wr_data_last = l2_line_data_last;
    mem_wr_data_txn_id = engine_txn_q;

    l2_entry_invalidate_valid =
      (engine_state_q == ENGINE_VICTIM_INVALIDATE);
    l2_entry_invalidate_addr = victim_addr_q;
    l2_mark_clean_valid = (engine_state_q == ENGINE_VICTIM_MARK_CLEAN);
    l2_mark_clean_addr = victim_addr_q;

    l2_line_wr_valid = 1'b0;
    l2_line_wr_addr = 32'b0;
    l2_line_wr_dirty = 1'b0;
    l2_line_wr_beat_idx = 3'b0;
    l2_line_wr_data = 64'b0;
    l2_line_wr_last = 1'b0;
    snoop_data_ready_core[0] = 1'b0;
    snoop_data_ready_core[1] = 1'b0;
    if (engine_state_q == ENGINE_MEM_STREAM) begin
      l2_line_wr_valid = mem_rd_data_valid &&
                         (mem_rd_data_txn_id == engine_txn_q);
      l2_line_wr_addr = engine_addr_q;
      l2_line_wr_dirty = 1'b0;
      l2_line_wr_beat_idx = mem_rd_data_beat_idx;
      l2_line_wr_data = mem_rd_data;
      l2_line_wr_last = mem_rd_data_last;
    end else if (engine_state_q == ENGINE_PUTM_STREAM) begin
      l2_line_wr_valid = put_data_valid_core[engine_src_q];
      l2_line_wr_addr = engine_addr_q;
      l2_line_wr_dirty = 1'b1;
      l2_line_wr_beat_idx = put_data_beat_idx_core[engine_src_q];
      l2_line_wr_data = put_data_core[engine_src_q];
      l2_line_wr_last = put_data_last_core[engine_src_q];
      put_data_ready_core[engine_src_q] = l2_line_wr_ready;
    end else if (victim_snoop_data_to_l2) begin
      l2_line_wr_valid = snoop_data_valid_core[victim_snoop_target_q];
      l2_line_wr_addr = victim_addr_q;
      l2_line_wr_dirty = 1'b1;
      l2_line_wr_beat_idx = snoop_data_beat_idx_core[victim_snoop_target_q];
      l2_line_wr_data = snoop_data_core[victim_snoop_target_q];
      l2_line_wr_last = snoop_data_last_core[victim_snoop_target_q];
      snoop_data_ready_core[victim_snoop_target_q] = l2_line_wr_ready;
    end else if (dir_snoop_data_to_l2) begin
      l2_line_wr_valid = snoop_data_valid_core[dir_snoop_target];
      l2_line_wr_addr = dir_snoop_addr;
      l2_line_wr_dirty = 1'b1;
      l2_line_wr_beat_idx = snoop_data_beat_idx_core[dir_snoop_target];
      l2_line_wr_data = snoop_data_core[dir_snoop_target];
      l2_line_wr_last = snoop_data_last_core[dir_snoop_target];
      snoop_data_ready_core[dir_snoop_target] = l2_line_wr_ready;
    end

  end

  assign l2_victim_valid = l2_alloc_victim_valid;
  assign l2_victim_addr = l2_alloc_victim_addr;
  assign l2_victim_dir_state = l2_alloc_victim_state;
  assign l2_victim_sharers = l2_alloc_victim_sharers;
  assign l2_victim_owner_id = l2_alloc_victim_owner;
  assign l2_victim_dirty = l2_alloc_victim_dirty;
  assign l1_victim_valid[0] = l1_replace_valid_core[0];
  assign l1_victim_valid[1] = l1_replace_valid_core[1];

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
    .dir_req_ready(cluster_dir_req_ready), .dir_req_valid(cluster_dir_req_valid),
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
    .array_protocol_error(l1_array_protocol_error)
  );

  DirectoryController #(.TXN_ID_WIDTH(TXN_ID_WIDTH)) directory_controller (
    .clock(clock), .reset(reset),
    .req_valid(cluster_dir_req_valid), .req_ready(dir_req_ready),
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
    .line_xfer_done_valid(dir_xfer_done_valid),
    .line_xfer_done_ready(dir_xfer_done_ready),
    .line_xfer_done_txn_id(dir_xfer_done_txn_id),
    .grant_valid(dir_grant_valid), .grant_ready(dir_grant_ready),
    .grant_dst_id(dir_grant_dst), .grant_opcode(dir_grant_opcode),
    .grant_has_data(dir_grant_has_data), .grant_line_addr(dir_grant_addr),
    .grant_txn_id(dir_grant_txn_id),
    .grant_commit_valid(dir_grant_commit_valid),
    .grant_commit_ready(dir_grant_commit_ready),
    .grant_commit_txn_id(dir_grant_commit_txn_id),
    .snoop_data_to_l2(dir_snoop_data_to_l2),
    .protocol_error(directory_protocol_error)
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
    if (reset) begin
      engine_state_q <= ENGINE_IDLE;
      engine_addr_q <= '0;
      engine_txn_q <= '0;
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
    end else begin
      case (engine_state_q)
        ENGINE_IDLE: begin
          if (dir_xfer_start_valid && dir_xfer_start_ready) begin
            engine_addr_q <= line_align(dir_xfer_addr);
            engine_txn_q <= dir_xfer_txn_id;
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
            engine_state_q <= ENGINE_GRANT_READ;
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
              engine_state_q <= ENGINE_VICTIM_MARK_CLEAN;
            end else begin
              victim_expected_beat_q <= victim_expected_beat_q + 1'b1;
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
                 ((snoop_rsp_opcode_core[victim_snoop_target_q] != SNOOP_RSP_DATA) ||
                  !snoop_rsp_has_data_core[victim_snoop_target_q] ||
                  !victim_snoop_data_complete_q)) ||
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
            engine_state_q <= ENGINE_MEM_STREAM;
        end

        ENGINE_MEM_STREAM: begin
          if (mem_rd_data_valid && mem_rd_data_ready) begin
            if ((mem_rd_data_txn_id != engine_txn_q) ||
                (mem_rd_data_beat_idx != mem_expected_beat_q) ||
                (mem_rd_data_last != (mem_rd_data_beat_idx == 3'd7))) begin
              memory_adapter_protocol_error <= 1'b1;
              engine_state_q <= ENGINE_ERROR;
            end else if (mem_rd_data_beat_idx == 3'd7) begin
              engine_state_q <= ENGINE_XFER_DONE;
            end else begin
              mem_expected_beat_q <= mem_expected_beat_q + 1'b1;
            end
          end
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
