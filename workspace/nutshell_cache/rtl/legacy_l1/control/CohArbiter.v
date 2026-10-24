module Arbiter_3(
  output       io_in_0_ready,
  input        io_in_0_valid,
  input  [9:0] io_in_0_bits_setIdx,
  output       io_in_1_ready,
  input        io_in_1_valid,
  input  [9:0] io_in_1_bits_setIdx,
  input        io_out_ready,
  output       io_out_valid,
  output [9:0] io_out_bits_setIdx
);
  wire  grant_1 = ~io_in_0_valid;
  assign io_in_0_ready = io_out_ready;
  assign io_in_1_ready = grant_1 & io_out_ready;
  assign io_out_valid = ~grant_1 | io_in_1_valid;
  assign io_out_bits_setIdx = io_in_0_valid ? io_in_0_bits_setIdx : io_in_1_bits_setIdx;
endmodule
