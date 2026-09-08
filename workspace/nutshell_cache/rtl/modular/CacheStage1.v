module CacheStage1(
  output        io_in_ready,
  input         io_in_valid,
  input  [31:0] io_in_bits_addr,
  input  [2:0]  io_in_bits_size,
  input  [3:0]  io_in_bits_cmd,
  input  [7:0]  io_in_bits_wmask,
  input  [63:0] io_in_bits_wdata,
  input  [15:0] io_in_bits_user,
  input         io_out_ready,
  output        io_out_valid,
  output [31:0] io_out_bits_req_addr,
  output [2:0]  io_out_bits_req_size,
  output [3:0]  io_out_bits_req_cmd,
  output [7:0]  io_out_bits_req_wmask,
  output [63:0] io_out_bits_req_wdata,
  output [15:0] io_out_bits_req_user,
  input         io_metaReadBus_req_ready,
  output        io_metaReadBus_req_valid,
  output [6:0]  io_metaReadBus_req_bits_setIdx,
  input  [18:0] io_metaReadBus_resp_data_0_tag,
  input         io_metaReadBus_resp_data_0_valid,
  input         io_metaReadBus_resp_data_0_dirty,
  input  [18:0] io_metaReadBus_resp_data_1_tag,
  input         io_metaReadBus_resp_data_1_valid,
  input         io_metaReadBus_resp_data_1_dirty,
  input  [18:0] io_metaReadBus_resp_data_2_tag,
  input         io_metaReadBus_resp_data_2_valid,
  input         io_metaReadBus_resp_data_2_dirty,
  input  [18:0] io_metaReadBus_resp_data_3_tag,
  input         io_metaReadBus_resp_data_3_valid,
  input         io_metaReadBus_resp_data_3_dirty,
  input         io_dataReadBus_req_ready,
  output        io_dataReadBus_req_valid,
  output [9:0]  io_dataReadBus_req_bits_setIdx,
  input  [63:0] io_dataReadBus_resp_data_0_data,
  input  [63:0] io_dataReadBus_resp_data_1_data,
  input  [63:0] io_dataReadBus_resp_data_2_data,
  input  [63:0] io_dataReadBus_resp_data_3_data
);
  wire  _io_in_ready_T_1 = io_out_ready & io_out_valid; // @[Decoupled.scala 51:35]
  assign io_in_ready = (~io_in_valid | _io_in_ready_T_1) & io_metaReadBus_req_ready & io_dataReadBus_req_ready; // @[Cache.scala 145:76]
  assign io_out_valid = io_in_valid & io_metaReadBus_req_ready & io_dataReadBus_req_ready; // @[Cache.scala 144:59]
  assign io_out_bits_req_addr = io_in_bits_addr; // @[Cache.scala 143:19]
  assign io_out_bits_req_size = io_in_bits_size; // @[Cache.scala 143:19]
  assign io_out_bits_req_cmd = io_in_bits_cmd; // @[Cache.scala 143:19]
  assign io_out_bits_req_wmask = io_in_bits_wmask; // @[Cache.scala 143:19]
  assign io_out_bits_req_wdata = io_in_bits_wdata; // @[Cache.scala 143:19]
  assign io_out_bits_req_user = io_in_bits_user; // @[Cache.scala 143:19]
  assign io_metaReadBus_req_valid = io_in_valid & io_out_ready; // @[Cache.scala 139:34]
  assign io_metaReadBus_req_bits_setIdx = io_in_bits_addr[12:6]; // @[Cache.scala 77:45]
  assign io_dataReadBus_req_valid = io_in_valid & io_out_ready; // @[Cache.scala 139:34]
  assign io_dataReadBus_req_bits_setIdx = {io_in_bits_addr[12:6],io_in_bits_addr[5:3]}; // @[Cat.scala 33:92]
endmodule
