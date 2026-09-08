module SRAMTemplate_1(
  input         clock,
  output        io_r_req_ready,
  input         io_r_req_valid,
  input  [9:0]  io_r_req_bits_setIdx,
  output [63:0] io_r_resp_data_0_data,
  output [63:0] io_r_resp_data_1_data,
  output [63:0] io_r_resp_data_2_data,
  output [63:0] io_r_resp_data_3_data,
  input         io_w_req_valid,
  input  [9:0]  io_w_req_bits_setIdx,
  input  [63:0] io_w_req_bits_data_data,
  input  [3:0]  io_w_req_bits_waymask
);
`ifdef RANDOMIZE_MEM_INIT
  reg [63:0] _RAND_0;
  reg [63:0] _RAND_3;
  reg [63:0] _RAND_6;
  reg [63:0] _RAND_9;
`endif // RANDOMIZE_MEM_INIT
`ifdef RANDOMIZE_REG_INIT
  reg [31:0] _RAND_1;
  reg [31:0] _RAND_2;
  reg [31:0] _RAND_4;
  reg [31:0] _RAND_5;
  reg [31:0] _RAND_7;
  reg [31:0] _RAND_8;
  reg [31:0] _RAND_10;
  reg [31:0] _RAND_11;
`endif // RANDOMIZE_REG_INIT
  reg [63:0] array_0 [0:1023]; // @[SRAMTemplate.scala 76:26]
  wire  array_0_rdata_MPORT_en; // @[SRAMTemplate.scala 76:26]
  wire [9:0] array_0_rdata_MPORT_addr; // @[SRAMTemplate.scala 76:26]
  wire [63:0] array_0_rdata_MPORT_data; // @[SRAMTemplate.scala 76:26]
  wire [63:0] array_0_MPORT_data; // @[SRAMTemplate.scala 76:26]
  wire [9:0] array_0_MPORT_addr; // @[SRAMTemplate.scala 76:26]
  wire  array_0_MPORT_mask; // @[SRAMTemplate.scala 76:26]
  wire  array_0_MPORT_en; // @[SRAMTemplate.scala 76:26]
  reg  array_0_rdata_MPORT_en_pipe_0;
  reg [9:0] array_0_rdata_MPORT_addr_pipe_0;
  reg [63:0] array_1 [0:1023]; // @[SRAMTemplate.scala 76:26]
  wire  array_1_rdata_MPORT_en; // @[SRAMTemplate.scala 76:26]
  wire [9:0] array_1_rdata_MPORT_addr; // @[SRAMTemplate.scala 76:26]
  wire [63:0] array_1_rdata_MPORT_data; // @[SRAMTemplate.scala 76:26]
  wire [63:0] array_1_MPORT_data; // @[SRAMTemplate.scala 76:26]
  wire [9:0] array_1_MPORT_addr; // @[SRAMTemplate.scala 76:26]
  wire  array_1_MPORT_mask; // @[SRAMTemplate.scala 76:26]
  wire  array_1_MPORT_en; // @[SRAMTemplate.scala 76:26]
  reg  array_1_rdata_MPORT_en_pipe_0;
  reg [9:0] array_1_rdata_MPORT_addr_pipe_0;
  reg [63:0] array_2 [0:1023]; // @[SRAMTemplate.scala 76:26]
  wire  array_2_rdata_MPORT_en; // @[SRAMTemplate.scala 76:26]
  wire [9:0] array_2_rdata_MPORT_addr; // @[SRAMTemplate.scala 76:26]
  wire [63:0] array_2_rdata_MPORT_data; // @[SRAMTemplate.scala 76:26]
  wire [63:0] array_2_MPORT_data; // @[SRAMTemplate.scala 76:26]
  wire [9:0] array_2_MPORT_addr; // @[SRAMTemplate.scala 76:26]
  wire  array_2_MPORT_mask; // @[SRAMTemplate.scala 76:26]
  wire  array_2_MPORT_en; // @[SRAMTemplate.scala 76:26]
  reg  array_2_rdata_MPORT_en_pipe_0;
  reg [9:0] array_2_rdata_MPORT_addr_pipe_0;
  reg [63:0] array_3 [0:1023]; // @[SRAMTemplate.scala 76:26]
  wire  array_3_rdata_MPORT_en; // @[SRAMTemplate.scala 76:26]
  wire [9:0] array_3_rdata_MPORT_addr; // @[SRAMTemplate.scala 76:26]
  wire [63:0] array_3_rdata_MPORT_data; // @[SRAMTemplate.scala 76:26]
  wire [63:0] array_3_MPORT_data; // @[SRAMTemplate.scala 76:26]
  wire [9:0] array_3_MPORT_addr; // @[SRAMTemplate.scala 76:26]
  wire  array_3_MPORT_mask; // @[SRAMTemplate.scala 76:26]
  wire  array_3_MPORT_en; // @[SRAMTemplate.scala 76:26]
  reg  array_3_rdata_MPORT_en_pipe_0;
  reg [9:0] array_3_rdata_MPORT_addr_pipe_0;
  wire  _realRen_T = ~io_w_req_valid; // @[SRAMTemplate.scala 89:41]
  assign array_0_rdata_MPORT_en = array_0_rdata_MPORT_en_pipe_0;
  assign array_0_rdata_MPORT_addr = array_0_rdata_MPORT_addr_pipe_0;
  assign array_0_rdata_MPORT_data = array_0[array_0_rdata_MPORT_addr]; // @[SRAMTemplate.scala 76:26]
  assign array_0_MPORT_data = io_w_req_bits_data_data;
  assign array_0_MPORT_addr = io_w_req_bits_setIdx;
  assign array_0_MPORT_mask = io_w_req_bits_waymask[0];
  assign array_0_MPORT_en = io_w_req_valid;
  assign array_1_rdata_MPORT_en = array_1_rdata_MPORT_en_pipe_0;
  assign array_1_rdata_MPORT_addr = array_1_rdata_MPORT_addr_pipe_0;
  assign array_1_rdata_MPORT_data = array_1[array_1_rdata_MPORT_addr]; // @[SRAMTemplate.scala 76:26]
  assign array_1_MPORT_data = io_w_req_bits_data_data;
  assign array_1_MPORT_addr = io_w_req_bits_setIdx;
  assign array_1_MPORT_mask = io_w_req_bits_waymask[1];
  assign array_1_MPORT_en = io_w_req_valid;
  assign array_2_rdata_MPORT_en = array_2_rdata_MPORT_en_pipe_0;
  assign array_2_rdata_MPORT_addr = array_2_rdata_MPORT_addr_pipe_0;
  assign array_2_rdata_MPORT_data = array_2[array_2_rdata_MPORT_addr]; // @[SRAMTemplate.scala 76:26]
  assign array_2_MPORT_data = io_w_req_bits_data_data;
  assign array_2_MPORT_addr = io_w_req_bits_setIdx;
  assign array_2_MPORT_mask = io_w_req_bits_waymask[2];
  assign array_2_MPORT_en = io_w_req_valid;
  assign array_3_rdata_MPORT_en = array_3_rdata_MPORT_en_pipe_0;
  assign array_3_rdata_MPORT_addr = array_3_rdata_MPORT_addr_pipe_0;
  assign array_3_rdata_MPORT_data = array_3[array_3_rdata_MPORT_addr]; // @[SRAMTemplate.scala 76:26]
  assign array_3_MPORT_data = io_w_req_bits_data_data;
  assign array_3_MPORT_addr = io_w_req_bits_setIdx;
  assign array_3_MPORT_mask = io_w_req_bits_waymask[3];
  assign array_3_MPORT_en = io_w_req_valid;
  assign io_r_req_ready = ~io_w_req_valid; // @[SRAMTemplate.scala 101:53]
  assign io_r_resp_data_0_data = array_0_rdata_MPORT_data; // @[SRAMTemplate.scala 98:{78,78}]
  assign io_r_resp_data_1_data = array_1_rdata_MPORT_data; // @[SRAMTemplate.scala 98:{78,78}]
  assign io_r_resp_data_2_data = array_2_rdata_MPORT_data; // @[SRAMTemplate.scala 98:{78,78}]
  assign io_r_resp_data_3_data = array_3_rdata_MPORT_data; // @[SRAMTemplate.scala 98:{78,78}]
  always @(posedge clock) begin
    if (array_0_MPORT_en & array_0_MPORT_mask) begin
      array_0[array_0_MPORT_addr] <= array_0_MPORT_data; // @[SRAMTemplate.scala 76:26]
    end
    array_0_rdata_MPORT_en_pipe_0 <= io_r_req_valid & _realRen_T;
    if (io_r_req_valid & _realRen_T) begin
      array_0_rdata_MPORT_addr_pipe_0 <= io_r_req_bits_setIdx;
    end
    if (array_1_MPORT_en & array_1_MPORT_mask) begin
      array_1[array_1_MPORT_addr] <= array_1_MPORT_data; // @[SRAMTemplate.scala 76:26]
    end
    array_1_rdata_MPORT_en_pipe_0 <= io_r_req_valid & _realRen_T;
    if (io_r_req_valid & _realRen_T) begin
      array_1_rdata_MPORT_addr_pipe_0 <= io_r_req_bits_setIdx;
    end
    if (array_2_MPORT_en & array_2_MPORT_mask) begin
      array_2[array_2_MPORT_addr] <= array_2_MPORT_data; // @[SRAMTemplate.scala 76:26]
    end
    array_2_rdata_MPORT_en_pipe_0 <= io_r_req_valid & _realRen_T;
    if (io_r_req_valid & _realRen_T) begin
      array_2_rdata_MPORT_addr_pipe_0 <= io_r_req_bits_setIdx;
    end
    if (array_3_MPORT_en & array_3_MPORT_mask) begin
      array_3[array_3_MPORT_addr] <= array_3_MPORT_data; // @[SRAMTemplate.scala 76:26]
    end
    array_3_rdata_MPORT_en_pipe_0 <= io_r_req_valid & _realRen_T;
    if (io_r_req_valid & _realRen_T) begin
      array_3_rdata_MPORT_addr_pipe_0 <= io_r_req_bits_setIdx;
    end
  end
// Register and memory initialization
`ifdef RANDOMIZE_GARBAGE_ASSIGN
`define RANDOMIZE
`endif
`ifdef RANDOMIZE_INVALID_ASSIGN
`define RANDOMIZE
`endif
`ifdef RANDOMIZE_REG_INIT
`define RANDOMIZE
`endif
`ifdef RANDOMIZE_MEM_INIT
`define RANDOMIZE
`endif
`ifndef RANDOM
`define RANDOM $random
`endif
`ifdef RANDOMIZE_MEM_INIT
  integer initvar;
`endif
`ifndef SYNTHESIS
`ifdef FIRRTL_BEFORE_INITIAL
`FIRRTL_BEFORE_INITIAL
`endif
initial begin
  `ifdef RANDOMIZE
    `ifdef INIT_RANDOM
      `INIT_RANDOM
    `endif
    `ifndef VERILATOR
      `ifdef RANDOMIZE_DELAY
        #`RANDOMIZE_DELAY begin end
      `else
        #0.002 begin end
      `endif
    `endif
`ifdef RANDOMIZE_MEM_INIT
  _RAND_0 = {2{`RANDOM}};
  for (initvar = 0; initvar < 1024; initvar = initvar+1)
    array_0[initvar] = _RAND_0[63:0];
  _RAND_3 = {2{`RANDOM}};
  for (initvar = 0; initvar < 1024; initvar = initvar+1)
    array_1[initvar] = _RAND_3[63:0];
  _RAND_6 = {2{`RANDOM}};
  for (initvar = 0; initvar < 1024; initvar = initvar+1)
    array_2[initvar] = _RAND_6[63:0];
  _RAND_9 = {2{`RANDOM}};
  for (initvar = 0; initvar < 1024; initvar = initvar+1)
    array_3[initvar] = _RAND_9[63:0];
`endif // RANDOMIZE_MEM_INIT
`ifdef RANDOMIZE_REG_INIT
  _RAND_1 = {1{`RANDOM}};
  array_0_rdata_MPORT_en_pipe_0 = _RAND_1[0:0];
  _RAND_2 = {1{`RANDOM}};
  array_0_rdata_MPORT_addr_pipe_0 = _RAND_2[9:0];
  _RAND_4 = {1{`RANDOM}};
  array_1_rdata_MPORT_en_pipe_0 = _RAND_4[0:0];
  _RAND_5 = {1{`RANDOM}};
  array_1_rdata_MPORT_addr_pipe_0 = _RAND_5[9:0];
  _RAND_7 = {1{`RANDOM}};
  array_2_rdata_MPORT_en_pipe_0 = _RAND_7[0:0];
  _RAND_8 = {1{`RANDOM}};
  array_2_rdata_MPORT_addr_pipe_0 = _RAND_8[9:0];
  _RAND_10 = {1{`RANDOM}};
  array_3_rdata_MPORT_en_pipe_0 = _RAND_10[0:0];
  _RAND_11 = {1{`RANDOM}};
  array_3_rdata_MPORT_addr_pipe_0 = _RAND_11[9:0];
`endif // RANDOMIZE_REG_INIT
  `endif // RANDOMIZE
end // initial
`ifdef FIRRTL_AFTER_INITIAL
`FIRRTL_AFTER_INITIAL
`endif
`endif // SYNTHESIS
endmodule
