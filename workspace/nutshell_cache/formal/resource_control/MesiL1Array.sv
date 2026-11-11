module MesiL1Array #(
  parameter int SETS = 128,
  parameter int WAYS = 4,
  parameter int TAG_WIDTH = 19
) (
  input  logic clock,
  input  logic reset,

  // Byte offsets below the word boundary are not part of this 64-bit LSU
  // interface; word selection uses address bits [5:3].
  /* verilator lint_off UNUSEDSIGNAL */
  input  logic [31:0] cpu_lookup_addr,
  /* verilator lint_on UNUSEDSIGNAL */
  output logic cpu_lookup_hit,
  output logic [$clog2(WAYS)-1:0] cpu_lookup_way,
  output coherence_protocol_pkg::mesi_state_t cpu_lookup_state,
  output logic [63:0] cpu_lookup_word,

  // Snoop and line-stream addresses are byte addresses; their low six bits
  // are intentionally ignored because all transactions are full-line.
  /* verilator lint_off UNUSEDSIGNAL */
  input  logic [31:0] snoop_lookup_addr,
  /* verilator lint_on UNUSEDSIGNAL */
  output logic snoop_lookup_hit,
  output logic [$clog2(WAYS)-1:0] snoop_lookup_way,
  output coherence_protocol_pkg::mesi_state_t snoop_lookup_state,

  // True when replace_way selects a currently resident victim; false when it
  // selected an invalid way for allocation.
  output logic replace_valid,
  output logic [$clog2(WAYS)-1:0] replace_way,
  output coherence_protocol_pkg::mesi_state_t replace_state,
  output logic [31:0] replace_line_addr,

  input  logic cpu_meta_write_valid,
  output logic cpu_meta_write_ready,
  input  logic [31:0] cpu_meta_write_line_addr,
  input  coherence_protocol_pkg::mesi_state_t cpu_meta_write_state,
  input  logic snoop_meta_write_valid,
  output logic snoop_meta_write_ready,
  input  logic [31:0] snoop_meta_write_line_addr,
  input  coherence_protocol_pkg::mesi_state_t snoop_meta_write_state,

  input  logic refill_valid,
  output logic refill_ready,
  /* verilator lint_off UNUSEDSIGNAL */
  input  logic [31:0] refill_line_addr,
  /* verilator lint_on UNUSEDSIGNAL */
  input  logic [$clog2(WAYS)-1:0] refill_way,
  input  logic [2:0] refill_beat_idx,
  input  logic [63:0] refill_data,
  input  logic refill_last,

  input  logic cpu_store_valid,
  output logic cpu_store_ready,
  /* verilator lint_off UNUSEDSIGNAL */
  input  logic [31:0] cpu_store_addr,
  /* verilator lint_on UNUSEDSIGNAL */
  input  logic [$clog2(WAYS)-1:0] cpu_store_way,
  input  logic [7:0] cpu_store_wmask,
  input  logic [63:0] cpu_store_wdata,

  input  logic line_rd_valid,
  output logic line_rd_ready,
  // Only snoop reads can legitimately lose a hit between the controller's
  // tag lookup and the shared array-read handshake. Replacement reads keep
  // this low so a missing victim remains a reportable array error.
  input  logic line_rd_miss_ok,
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
  // Symbolic undriven output cutpoint: cpu_lookup_hit
  // Symbolic undriven output cutpoint: cpu_lookup_way
  // Symbolic undriven output cutpoint: cpu_lookup_state
  // Symbolic undriven output cutpoint: cpu_lookup_word
  // Symbolic undriven output cutpoint: snoop_lookup_hit
  // Symbolic undriven output cutpoint: snoop_lookup_way
  // Symbolic undriven output cutpoint: snoop_lookup_state
  // Symbolic undriven output cutpoint: replace_valid
  // Symbolic undriven output cutpoint: replace_way
  // Symbolic undriven output cutpoint: replace_state
  // Symbolic undriven output cutpoint: replace_line_addr
  // Symbolic undriven output cutpoint: cpu_meta_write_ready
  // Symbolic undriven output cutpoint: snoop_meta_write_ready
  // Symbolic undriven output cutpoint: refill_ready
  // Symbolic undriven output cutpoint: cpu_store_ready
  // Symbolic undriven output cutpoint: line_rd_ready
  // Symbolic undriven output cutpoint: line_rd_hit
  // Symbolic undriven output cutpoint: line_data_valid
  // Symbolic undriven output cutpoint: line_data_beat_idx
  // Symbolic undriven output cutpoint: line_data
  // Symbolic undriven output cutpoint: line_data_last
  // Symbolic undriven output cutpoint: protocol_error
endmodule
