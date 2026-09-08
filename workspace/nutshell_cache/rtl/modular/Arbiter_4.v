module Arbiter_4(
  output        io_in_0_ready,
  input         io_in_0_valid,
  input  [31:0] io_in_0_bits_addr,
  input  [2:0]  io_in_0_bits_size,
  input  [3:0]  io_in_0_bits_cmd,
  input  [7:0]  io_in_0_bits_wmask,
  input  [63:0] io_in_0_bits_wdata,
  output        io_in_1_ready,
  input         io_in_1_valid,
  input  [31:0] io_in_1_bits_addr,
  input  [2:0]  io_in_1_bits_size,
  input  [3:0]  io_in_1_bits_cmd,
  input  [7:0]  io_in_1_bits_wmask,
  input  [63:0] io_in_1_bits_wdata,
  input  [15:0] io_in_1_bits_user,
  input         io_out_ready,
  output        io_out_valid,
  output [31:0] io_out_bits_addr,
  output [2:0]  io_out_bits_size,
  output [3:0]  io_out_bits_cmd,
  output [7:0]  io_out_bits_wmask,
  output [63:0] io_out_bits_wdata,
  output [15:0] io_out_bits_user
);
  wire  grant_1 = ~io_in_0_valid; // @[Arbiter.scala 45:78]
  assign io_in_0_ready = io_out_ready; // @[Arbiter.scala 146:19]
  assign io_in_1_ready = grant_1 & io_out_ready; // @[Arbiter.scala 146:19]
  assign io_out_valid = ~grant_1 | io_in_1_valid; // @[Arbiter.scala 147:31]
  assign io_out_bits_addr = io_in_0_valid ? io_in_0_bits_addr : io_in_1_bits_addr; // @[Arbiter.scala 136:15 138:26 140:19]
  assign io_out_bits_size = io_in_0_valid ? io_in_0_bits_size : io_in_1_bits_size; // @[Arbiter.scala 136:15 138:26 140:19]
  assign io_out_bits_cmd = io_in_0_valid ? io_in_0_bits_cmd : io_in_1_bits_cmd; // @[Arbiter.scala 136:15 138:26 140:19]
  assign io_out_bits_wmask = io_in_0_valid ? io_in_0_bits_wmask : io_in_1_bits_wmask; // @[Arbiter.scala 136:15 138:26 140:19]
  assign io_out_bits_wdata = io_in_0_valid ? io_in_0_bits_wdata : io_in_1_bits_wdata; // @[Arbiter.scala 136:15 138:26 140:19]
  assign io_out_bits_user = io_in_0_valid ? 16'h0 : io_in_1_bits_user; // @[Arbiter.scala 136:15 138:26 140:19]
endmodule
