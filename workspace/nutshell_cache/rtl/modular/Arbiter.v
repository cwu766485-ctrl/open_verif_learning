module Arbiter(
  input         io_in_0_valid,
  input  [6:0]  io_in_0_bits_setIdx,
  input  [18:0] io_in_0_bits_data_tag,
  input  [3:0]  io_in_0_bits_waymask,
  input         io_in_1_valid,
  input  [6:0]  io_in_1_bits_setIdx,
  input  [18:0] io_in_1_bits_data_tag,
  input         io_in_1_bits_data_dirty,
  input  [3:0]  io_in_1_bits_waymask,
  output        io_out_valid,
  output [6:0]  io_out_bits_setIdx,
  output [18:0] io_out_bits_data_tag,
  output        io_out_bits_data_dirty,
  output [3:0]  io_out_bits_waymask
);
  wire  grant_1 = ~io_in_0_valid; // @[Arbiter.scala 45:78]
  assign io_out_valid = ~grant_1 | io_in_1_valid; // @[Arbiter.scala 147:31]
  assign io_out_bits_setIdx = io_in_0_valid ? io_in_0_bits_setIdx : io_in_1_bits_setIdx; // @[Arbiter.scala 136:15 138:26 140:19]
  assign io_out_bits_data_tag = io_in_0_valid ? io_in_0_bits_data_tag : io_in_1_bits_data_tag; // @[Arbiter.scala 136:15 138:26 140:19]
  assign io_out_bits_data_dirty = io_in_0_valid | io_in_1_bits_data_dirty; // @[Arbiter.scala 136:15 138:26 140:19]
  assign io_out_bits_waymask = io_in_0_valid ? io_in_0_bits_waymask : io_in_1_bits_waymask; // @[Arbiter.scala 136:15 138:26 140:19]
endmodule
