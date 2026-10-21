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
  logic prefer_core1_q;
  logic locked_q;
  logic locked_src_q;
  logic select_src;

  always_comb begin
    if (locked_q)
      select_src = locked_src_q;
    else if (in_valid[0] && in_valid[1])
      select_src = prefer_core1_q;
    else
      select_src = in_valid[1];

    out_valid = in_valid[select_src];
    out_src_id = select_src;
    out_opcode = in_opcode[select_src];
    out_line_addr = in_line_addr[select_src];
    out_txn_id = in_txn_id[select_src];
    in_ready = 2'b00;
    if (out_valid)
      in_ready[select_src] = out_ready;
  end

  always_ff @(posedge clock) begin
    if (reset) begin
      prefer_core1_q <= 1'b0;
      locked_q <= 1'b0;
      locked_src_q <= 1'b0;
    end else begin
      if (out_valid && out_ready) begin
        prefer_core1_q <= ~select_src;
        locked_q <= 1'b0;
      end else if (out_valid && !out_ready) begin
        locked_q <= 1'b1;
        locked_src_q <= select_src;
      end else begin
        locked_q <= 1'b0;
      end
    end
  end
endmodule
