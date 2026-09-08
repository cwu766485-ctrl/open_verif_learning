module Arbiter_1(
  input         io_in_0_valid,
  input  [9:0]  io_in_0_bits_setIdx,
  input  [63:0] io_in_0_bits_data_data,
  input  [3:0]  io_in_0_bits_waymask,
  input         io_in_1_valid,
  input  [9:0]  io_in_1_bits_setIdx,
  input  [63:0] io_in_1_bits_data_data,
  input  [3:0]  io_in_1_bits_waymask,
  output        io_out_valid,
  output [9:0]  io_out_bits_setIdx,
  output [63:0] io_out_bits_data_data,
  output [3:0]  io_out_bits_waymask
);
  wire  grant_1 = ~io_in_0_valid; // @[Arbiter.scala 45:78]
  assign io_out_valid = ~grant_1 | io_in_1_valid; // @[Arbiter.scala 147:31]
  assign io_out_bits_setIdx = io_in_0_valid ? io_in_0_bits_setIdx : io_in_1_bits_setIdx; // @[Arbiter.scala 136:15 138:26 140:19]
  assign io_out_bits_data_data = io_in_0_valid ? io_in_0_bits_data_data : io_in_1_bits_data_data; // @[Arbiter.scala 136:15 138:26 140:19]
  assign io_out_bits_waymask = io_in_0_valid ? io_in_0_bits_waymask : io_in_1_bits_waymask; // @[Arbiter.scala 136:15 138:26 140:19]
endmodule
