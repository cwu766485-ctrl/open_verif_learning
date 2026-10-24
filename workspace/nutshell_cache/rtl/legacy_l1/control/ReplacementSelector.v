// LFSR victim and invalid-first refill-way selection shared by CacheStage2
// and the standalone SymbiYosys proof target.
module ReplacementSelector (
  input         clock,
  input         reset,
  input  [3:0]  invalid_vec,
  output [3:0]  lfsr_way_onehot,
  output [3:0]  refill_way_onehot
);
  localparam [63:0] RESET_SEED = 64'h1234567887654321;

  reg [63:0] lfsr_state;
  wire feedback = lfsr_state[0] ^ lfsr_state[1] ^
                  lfsr_state[3] ^ lfsr_state[4];

  assign lfsr_way_onehot = 4'h1 << lfsr_state[1:0];
  assign refill_way_onehot = invalid_vec[3] ? 4'b1000 :
                             invalid_vec[2] ? 4'b0100 :
                             invalid_vec[1] ? 4'b0010 :
                             invalid_vec[0] ? 4'b0001 :
                             lfsr_way_onehot;

  always @(posedge clock) begin
    if (reset)
      lfsr_state <= RESET_SEED;
    else if (lfsr_state == 64'b0)
      lfsr_state <= 64'b1;
    else
      lfsr_state <= {feedback, lfsr_state[63:1]};
  end

`ifdef FORMAL
  function automatic is_onehot4(input [3:0] value);
    begin
      is_onehot4 = (value != 4'b0000) &&
                   ((value & (value - 4'b0001)) == 4'b0000);
    end
  endfunction

  reg f_past_valid = 1'b0;
  reg f_reset_seen = 1'b0;
  always @(posedge clock) begin
    f_past_valid <= 1'b1;
    if (!f_reset_seen)
      assume (reset);
    if (reset)
      f_reset_seen <= 1'b1;
    assert (is_onehot4(lfsr_way_onehot));
    assert (is_onehot4(refill_way_onehot));
    if (f_reset_seen)
      assert (lfsr_state != 64'b0);
    if (f_past_valid) begin
      if ($past(reset))
        assert (lfsr_state == RESET_SEED);
      else if ($past(lfsr_state) == 64'b0)
        assert (lfsr_state == 64'b1);
      else
        assert (lfsr_state == {
          $past(lfsr_state[0] ^ lfsr_state[1] ^
                lfsr_state[3] ^ lfsr_state[4]),
          $past(lfsr_state[63:1])
        });
    end
  end
`endif
endmodule
