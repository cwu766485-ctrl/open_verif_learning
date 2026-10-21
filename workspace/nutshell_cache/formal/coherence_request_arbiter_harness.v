// Formal harness for the flattened core used by the synthesizable public
// CoherenceRequestArbiter wrapper.
module CoherenceRequestArbiterFormal(
  input clock,
  input reset,
  input [1:0] in_valid,
  input out_ready,
  input [5:0] in_opcode_flat,
  input [63:0] in_line_addr_flat,
  input [7:0] in_txn_id_flat
);
  wire [1:0] in_ready;
  wire out_valid;
  wire out_src_id;
  wire [2:0] out_opcode;
  wire [31:0] out_line_addr;
  wire [3:0] out_txn_id;

  reg past_valid = 1'b0;
  reg past_accept_both = 1'b0;
  reg past_src = 1'b0;

  CoherenceRequestArbiterCore #(.TXN_ID_WIDTH(4)) dut (
    .clock(clock), .reset(reset), .in_valid(in_valid), .in_ready(in_ready),
    .in_opcode_flat(in_opcode_flat),
    .in_line_addr_flat(in_line_addr_flat),
    .in_txn_id_flat(in_txn_id_flat),
    .out_valid(out_valid), .out_ready(out_ready), .out_src_id(out_src_id),
    .out_opcode(out_opcode), .out_line_addr(out_line_addr),
    .out_txn_id(out_txn_id)
  );

  always @(posedge clock) begin
    past_valid <= 1'b1;
    past_accept_both <= (in_valid == 2'b11) && out_ready && !reset;
    past_src <= out_src_id;

    if ($initstate)
      assume (reset);

    // Ready is one-hot-or-zero and only the selected valid request can fire.
    assert ((in_ready == 2'b00) || (in_ready == 2'b01) ||
            (in_ready == 2'b10));
    assert (!in_ready[0] || (out_valid && out_ready && !out_src_id));
    assert (!in_ready[1] || (out_valid && out_ready && out_src_id));
    if (out_valid) begin
      assert (in_valid[out_src_id]);
      assert (out_opcode == in_opcode_flat[3*out_src_id +: 3]);
      assert (out_line_addr == in_line_addr_flat[32*out_src_id +: 32]);
      assert (out_txn_id == in_txn_id_flat[4*out_src_id +: 4]);
    end

    // A blocked selection cannot jump to the other source. The source must
    // keep its valid/payload stable until accepted.
    if (past_valid && !$past(reset) && $past(out_valid && !out_ready)) begin
      assert (out_valid && out_src_id == $past(out_src_id));
      if (!$past(out_src_id)) begin
        assume (in_valid[0]);
        assume (in_opcode_flat[2:0] == $past(in_opcode_flat[2:0]));
        assume (in_line_addr_flat[31:0] == $past(in_line_addr_flat[31:0]));
        assume (in_txn_id_flat[3:0] == $past(in_txn_id_flat[3:0]));
      end else begin
        assume (in_valid[1]);
        assume (in_opcode_flat[5:3] == $past(in_opcode_flat[5:3]));
        assume (in_line_addr_flat[63:32] == $past(in_line_addr_flat[63:32]));
        assume (in_txn_id_flat[7:4] == $past(in_txn_id_flat[7:4]));
      end
    end

    // Under persistent two-way contention, a successful arbitration alternates
    // the winner, which is the arbiter's bounded fairness guarantee.
    if (past_valid && past_accept_both && (in_valid == 2'b11) &&
        out_ready && !reset)
      assert (out_src_id != past_src);
  end
endmodule
