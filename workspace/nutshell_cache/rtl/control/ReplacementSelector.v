// Invalid-first replacement selection. The all-valid LFSR victim path stays
// in the generated Stage 2 baseline until it is extracted with trace checks.
module ReplacementSelector (
  input  [3:0] invalid_vec,
  input  [3:0] lfsr_way_onehot,
  output [3:0] refill_way_onehot
);
  assign refill_way_onehot = invalid_vec[3] ? 4'b1000 :
                             invalid_vec[2] ? 4'b0100 :
                             invalid_vec[1] ? 4'b0010 :
                             invalid_vec[0] ? 4'b0001 :
                             lfsr_way_onehot;
endmodule
