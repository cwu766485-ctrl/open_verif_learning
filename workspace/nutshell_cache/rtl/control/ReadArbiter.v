module Arbiter_2(
  output       io_in_0_ready,
  input        io_in_0_valid,
  input  [6:0] io_in_0_bits_setIdx,
  input        io_out_ready,
  output       io_out_valid,
  output [6:0] io_out_bits_setIdx
);
  assign io_in_0_ready = io_out_ready;
  assign io_out_valid = io_in_0_valid;
  assign io_out_bits_setIdx = io_in_0_bits_setIdx;
endmodule
