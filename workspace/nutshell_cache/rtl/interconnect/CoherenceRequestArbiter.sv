module CoherenceRequestArbiter #(
  parameter int TXN_ID_WIDTH = coherence_protocol_pkg::TXN_ID_WIDTH
) (
  input  logic clock,
  input  logic reset,
  input  logic [1:0] in_valid,
  output logic [1:0] in_ready,
  input  coherence_protocol_pkg::request_opcode_t in_opcode [0:1],
  input  logic [31:0] in_line_addr [0:1],
  input  logic [TXN_ID_WIDTH-1:0] in_txn_id [0:1],
  output logic out_valid,
  input  logic out_ready,
  output logic out_src_id,
  output coherence_protocol_pkg::request_opcode_t out_opcode,
  output logic [31:0] out_line_addr,
  output logic [TXN_ID_WIDTH-1:0] out_txn_id
);
  logic [5:0] in_opcode_flat;
  logic [63:0] in_line_addr_flat;
  logic [2*TXN_ID_WIDTH-1:0] in_txn_id_flat;
  logic [2:0] out_opcode_flat;
  always_comb begin
    in_opcode_flat = {in_opcode[1], in_opcode[0]};
    in_line_addr_flat = {in_line_addr[1], in_line_addr[0]};
    in_txn_id_flat = {in_txn_id[1], in_txn_id[0]};
    out_opcode = coherence_protocol_pkg::request_opcode_t'(out_opcode_flat);
  end

  CoherenceRequestArbiterCore #(.TXN_ID_WIDTH(TXN_ID_WIDTH)) core (
    .clock(clock), .reset(reset), .in_valid(in_valid), .in_ready(in_ready),
    .in_opcode_flat(in_opcode_flat), .in_line_addr_flat(in_line_addr_flat),
    .in_txn_id_flat(in_txn_id_flat), .out_valid(out_valid),
    .out_ready(out_ready), .out_src_id(out_src_id),
    .out_opcode(out_opcode_flat), .out_line_addr(out_line_addr),
    .out_txn_id(out_txn_id)
  );
endmodule
