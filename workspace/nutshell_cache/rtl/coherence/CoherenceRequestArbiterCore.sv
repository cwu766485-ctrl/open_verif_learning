// Package-free flattened implementation so this exact arbiter logic can be
// checked with Yosys/SymbiYosys. The public wrapper preserves typed ports.
module CoherenceRequestArbiterCore #(
  parameter integer TXN_ID_WIDTH = 4
) (
  input  logic clock,
  input  logic reset,
  input  logic [1:0] in_valid,
  output logic [1:0] in_ready,
  input  logic [5:0] in_opcode_flat,
  input  logic [63:0] in_line_addr_flat,
  input  logic [2*TXN_ID_WIDTH-1:0] in_txn_id_flat,
  output logic out_valid,
  input  logic out_ready,
  output logic out_src_id,
  output logic [2:0] out_opcode,
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
    out_opcode = in_opcode_flat[3*select_src +: 3];
    out_line_addr = in_line_addr_flat[32*select_src +: 32];
    out_txn_id = in_txn_id_flat[TXN_ID_WIDTH*select_src +: TXN_ID_WIDTH];
  end

  // Keep the upstream ready path separate from the valid/payload mux. Apart
  // from making the handshake easier to audit, this avoids a false
  // combinational-cycle report in tools that conservatively treat one
  // always_comb block as a single dependency node.
  always_comb begin
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
