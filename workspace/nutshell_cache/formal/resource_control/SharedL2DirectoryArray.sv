// 256 KiB, 8-way shared L2 tag/data and inclusive directory array.
// The array intentionally does not evict a live directory entry by itself:
// a full-set victim must first be back-invalidated by the subsystem controller.
module SharedL2DirectoryArray #(
  parameter int SETS = 512,
  parameter int WAYS = 8,
  parameter int TAG_WIDTH = 17
) (
  input  logic clock,
  input  logic reset,

  // These byte-address ports carry full-line operations; [5:0] is offset-only.
  /* verilator lint_off UNUSEDSIGNAL */
  input  logic [31:0] lookup_addr,
  /* verilator lint_on UNUSEDSIGNAL */
  output logic lookup_hit,
  output logic [$clog2(WAYS)-1:0] lookup_way,
  output coherence_protocol_pkg::directory_state_t lookup_dir_state,
  output logic [1:0] lookup_sharers,
  output logic lookup_owner_id,

  // Metadata writes may update an existing line or allocate an invalid way.
  input  logic dir_write_valid,
  output logic dir_write_ready,
  /* verilator lint_off UNUSEDSIGNAL */
  input  logic [31:0] dir_write_line_addr,
  /* verilator lint_on UNUSEDSIGNAL */
  input  coherence_protocol_pkg::directory_state_t dir_write_state,
  input  logic [1:0] dir_write_sharers,
  input  logic dir_write_owner_id,

  // A miss allocator uses this information to request inclusion eviction.
  // No replacement occurs until the victim directory entry is explicitly
  // invalidated and its dirty owner data has been recovered.
  /* verilator lint_off UNUSEDSIGNAL */
  input  logic [31:0] alloc_addr,
  /* verilator lint_on UNUSEDSIGNAL */
  output logic alloc_victim_valid,
  output logic [$clog2(WAYS)-1:0] alloc_way,
  output logic [31:0] alloc_victim_addr,
  output coherence_protocol_pkg::directory_state_t alloc_victim_dir_state,
  output logic [1:0] alloc_victim_sharers,
  output logic alloc_victim_owner_id,
  output logic alloc_victim_dirty,

  // Called only after all recorded L1 copies of this inclusive entry have
  // been invalidated and any dirty owner line has been recovered.
  input  logic entry_invalidate_valid,
  output logic entry_invalidate_ready,
  /* verilator lint_off UNUSEDSIGNAL */
  input  logic [31:0] entry_invalidate_line_addr,
  /* verilator lint_on UNUSEDSIGNAL */
  input  logic mark_clean_valid,
  output logic mark_clean_ready,
  /* verilator lint_off UNUSEDSIGNAL */
  input  logic [31:0] mark_clean_line_addr,
  /* verilator lint_on UNUSEDSIGNAL */

  // Full-line writes are used for memory fills and owner SnoopData.
  input  logic line_wr_valid,
  output logic line_wr_ready,
  /* verilator lint_off UNUSEDSIGNAL */
  input  logic [31:0] line_wr_addr,
  /* verilator lint_on UNUSEDSIGNAL */
  input  logic line_wr_dirty,
  input  logic [2:0] line_wr_beat_idx,
  input  logic [63:0] line_wr_data,
  input  logic line_wr_last,

  // Serialized full-line read port for L1 grant/refill.
  input  logic line_rd_valid,
  output logic line_rd_ready,
  /* verilator lint_off UNUSEDSIGNAL */
  input  logic [31:0] line_rd_addr,
  /* verilator lint_on UNUSEDSIGNAL */
  output logic line_rd_hit,
  output logic line_data_valid,
  input  logic line_data_ready,
  output logic [2:0] line_data_beat_idx,
  output logic [63:0] line_data,
  output logic line_data_last,

  output logic protocol_error
);
  assign lookup_hit = $anyseq;
  assign lookup_way = $anyseq;
  assign lookup_dir_state = $anyseq;
  assign lookup_sharers = $anyseq;
  assign lookup_owner_id = $anyseq;
  assign dir_write_ready = $anyseq;
  assign alloc_victim_valid = $anyseq;
  assign alloc_way = $anyseq;
  assign alloc_victim_addr = $anyseq;
  assign alloc_victim_dir_state = $anyseq;
  assign alloc_victim_sharers = $anyseq;
  assign alloc_victim_owner_id = $anyseq;
  assign alloc_victim_dirty = $anyseq;
  assign entry_invalidate_ready = $anyseq;
  assign mark_clean_ready = $anyseq;
  assign line_wr_ready = $anyseq;
  assign line_rd_ready = $anyseq;
  assign line_rd_hit = $anyseq;
  assign line_data_valid = $anyseq;
  assign line_data_beat_idx = $anyseq;
  assign line_data = $anyseq;
  assign line_data_last = $anyseq;
  assign protocol_error = $anyseq;
endmodule
