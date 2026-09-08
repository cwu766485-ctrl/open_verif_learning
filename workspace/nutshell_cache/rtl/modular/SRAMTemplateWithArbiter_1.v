module SRAMTemplateWithArbiter_1(
  input         clock,
  input         reset,
  output        io_r_0_req_ready,
  input         io_r_0_req_valid,
  input  [9:0]  io_r_0_req_bits_setIdx,
  output [63:0] io_r_0_resp_data_0_data,
  output [63:0] io_r_0_resp_data_1_data,
  output [63:0] io_r_0_resp_data_2_data,
  output [63:0] io_r_0_resp_data_3_data,
  output        io_r_1_req_ready,
  input         io_r_1_req_valid,
  input  [9:0]  io_r_1_req_bits_setIdx,
  output [63:0] io_r_1_resp_data_0_data,
  output [63:0] io_r_1_resp_data_1_data,
  output [63:0] io_r_1_resp_data_2_data,
  output [63:0] io_r_1_resp_data_3_data,
  input         io_w_req_valid,
  input  [9:0]  io_w_req_bits_setIdx,
  input  [63:0] io_w_req_bits_data_data,
  input  [3:0]  io_w_req_bits_waymask
);
`ifdef RANDOMIZE_REG_INIT
  reg [31:0] _RAND_0;
  reg [63:0] _RAND_1;
  reg [63:0] _RAND_2;
  reg [63:0] _RAND_3;
  reg [63:0] _RAND_4;
  reg [31:0] _RAND_5;
  reg [63:0] _RAND_6;
  reg [63:0] _RAND_7;
  reg [63:0] _RAND_8;
  reg [63:0] _RAND_9;
`endif // RANDOMIZE_REG_INIT
  wire  ram_clock; // @[SRAMTemplate.scala 121:19]
  wire  ram_io_r_req_ready; // @[SRAMTemplate.scala 121:19]
  wire  ram_io_r_req_valid; // @[SRAMTemplate.scala 121:19]
  wire [9:0] ram_io_r_req_bits_setIdx; // @[SRAMTemplate.scala 121:19]
  wire [63:0] ram_io_r_resp_data_0_data; // @[SRAMTemplate.scala 121:19]
  wire [63:0] ram_io_r_resp_data_1_data; // @[SRAMTemplate.scala 121:19]
  wire [63:0] ram_io_r_resp_data_2_data; // @[SRAMTemplate.scala 121:19]
  wire [63:0] ram_io_r_resp_data_3_data; // @[SRAMTemplate.scala 121:19]
  wire  ram_io_w_req_valid; // @[SRAMTemplate.scala 121:19]
  wire [9:0] ram_io_w_req_bits_setIdx; // @[SRAMTemplate.scala 121:19]
  wire [63:0] ram_io_w_req_bits_data_data; // @[SRAMTemplate.scala 121:19]
  wire [3:0] ram_io_w_req_bits_waymask; // @[SRAMTemplate.scala 121:19]
  wire  readArb_io_in_0_ready; // @[SRAMTemplate.scala 124:23]
  wire  readArb_io_in_0_valid; // @[SRAMTemplate.scala 124:23]
  wire [9:0] readArb_io_in_0_bits_setIdx; // @[SRAMTemplate.scala 124:23]
  wire  readArb_io_in_1_ready; // @[SRAMTemplate.scala 124:23]
  wire  readArb_io_in_1_valid; // @[SRAMTemplate.scala 124:23]
  wire [9:0] readArb_io_in_1_bits_setIdx; // @[SRAMTemplate.scala 124:23]
  wire  readArb_io_out_ready; // @[SRAMTemplate.scala 124:23]
  wire  readArb_io_out_valid; // @[SRAMTemplate.scala 124:23]
  wire [9:0] readArb_io_out_bits_setIdx; // @[SRAMTemplate.scala 124:23]
  reg  REG; // @[SRAMTemplate.scala 130:58]
  reg [63:0] r__0_data; // @[Reg.scala 35:20]
  reg [63:0] r__1_data; // @[Reg.scala 35:20]
  reg [63:0] r__2_data; // @[Reg.scala 35:20]
  reg [63:0] r__3_data; // @[Reg.scala 35:20]
  reg  REG_1; // @[SRAMTemplate.scala 130:58]
  reg [63:0] r_1_0_data; // @[Reg.scala 35:20]
  reg [63:0] r_1_1_data; // @[Reg.scala 35:20]
  reg [63:0] r_1_2_data; // @[Reg.scala 35:20]
  reg [63:0] r_1_3_data; // @[Reg.scala 35:20]
  SRAMTemplate_1 ram ( // @[SRAMTemplate.scala 121:19]
    .clock(ram_clock),
    .io_r_req_ready(ram_io_r_req_ready),
    .io_r_req_valid(ram_io_r_req_valid),
    .io_r_req_bits_setIdx(ram_io_r_req_bits_setIdx),
    .io_r_resp_data_0_data(ram_io_r_resp_data_0_data),
    .io_r_resp_data_1_data(ram_io_r_resp_data_1_data),
    .io_r_resp_data_2_data(ram_io_r_resp_data_2_data),
    .io_r_resp_data_3_data(ram_io_r_resp_data_3_data),
    .io_w_req_valid(ram_io_w_req_valid),
    .io_w_req_bits_setIdx(ram_io_w_req_bits_setIdx),
    .io_w_req_bits_data_data(ram_io_w_req_bits_data_data),
    .io_w_req_bits_waymask(ram_io_w_req_bits_waymask)
  );
  Arbiter_3 readArb ( // @[SRAMTemplate.scala 124:23]
    .io_in_0_ready(readArb_io_in_0_ready),
    .io_in_0_valid(readArb_io_in_0_valid),
    .io_in_0_bits_setIdx(readArb_io_in_0_bits_setIdx),
    .io_in_1_ready(readArb_io_in_1_ready),
    .io_in_1_valid(readArb_io_in_1_valid),
    .io_in_1_bits_setIdx(readArb_io_in_1_bits_setIdx),
    .io_out_ready(readArb_io_out_ready),
    .io_out_valid(readArb_io_out_valid),
    .io_out_bits_setIdx(readArb_io_out_bits_setIdx)
  );
  assign io_r_0_req_ready = readArb_io_in_0_ready; // @[SRAMTemplate.scala 125:17]
  assign io_r_0_resp_data_0_data = REG ? ram_io_r_resp_data_0_data : r__0_data; // @[Hold.scala 23:48]
  assign io_r_0_resp_data_1_data = REG ? ram_io_r_resp_data_1_data : r__1_data; // @[Hold.scala 23:48]
  assign io_r_0_resp_data_2_data = REG ? ram_io_r_resp_data_2_data : r__2_data; // @[Hold.scala 23:48]
  assign io_r_0_resp_data_3_data = REG ? ram_io_r_resp_data_3_data : r__3_data; // @[Hold.scala 23:48]
  assign io_r_1_req_ready = readArb_io_in_1_ready; // @[SRAMTemplate.scala 125:17]
  assign io_r_1_resp_data_0_data = REG_1 ? ram_io_r_resp_data_0_data : r_1_0_data; // @[Hold.scala 23:48]
  assign io_r_1_resp_data_1_data = REG_1 ? ram_io_r_resp_data_1_data : r_1_1_data; // @[Hold.scala 23:48]
  assign io_r_1_resp_data_2_data = REG_1 ? ram_io_r_resp_data_2_data : r_1_2_data; // @[Hold.scala 23:48]
  assign io_r_1_resp_data_3_data = REG_1 ? ram_io_r_resp_data_3_data : r_1_3_data; // @[Hold.scala 23:48]
  assign ram_clock = clock;
  assign ram_io_r_req_valid = readArb_io_out_valid; // @[SRAMTemplate.scala 126:16]
  assign ram_io_r_req_bits_setIdx = readArb_io_out_bits_setIdx; // @[SRAMTemplate.scala 126:16]
  assign ram_io_w_req_valid = io_w_req_valid; // @[SRAMTemplate.scala 122:12]
  assign ram_io_w_req_bits_setIdx = io_w_req_bits_setIdx; // @[SRAMTemplate.scala 122:12]
  assign ram_io_w_req_bits_data_data = io_w_req_bits_data_data; // @[SRAMTemplate.scala 122:12]
  assign ram_io_w_req_bits_waymask = io_w_req_bits_waymask; // @[SRAMTemplate.scala 122:12]
  assign readArb_io_in_0_valid = io_r_0_req_valid; // @[SRAMTemplate.scala 125:17]
  assign readArb_io_in_0_bits_setIdx = io_r_0_req_bits_setIdx; // @[SRAMTemplate.scala 125:17]
  assign readArb_io_in_1_valid = io_r_1_req_valid; // @[SRAMTemplate.scala 125:17]
  assign readArb_io_in_1_bits_setIdx = io_r_1_req_bits_setIdx; // @[SRAMTemplate.scala 125:17]
  assign readArb_io_out_ready = ram_io_r_req_ready; // @[SRAMTemplate.scala 126:16]
  always @(posedge clock) begin
    REG <= io_r_0_req_ready & io_r_0_req_valid; // @[Decoupled.scala 51:35]
    if (reset) begin // @[Reg.scala 35:20]
      r__0_data <= 64'h0; // @[Reg.scala 35:20]
    end else if (REG) begin // @[Reg.scala 36:18]
      r__0_data <= ram_io_r_resp_data_0_data; // @[Reg.scala 36:22]
    end
    if (reset) begin // @[Reg.scala 35:20]
      r__1_data <= 64'h0; // @[Reg.scala 35:20]
    end else if (REG) begin // @[Reg.scala 36:18]
      r__1_data <= ram_io_r_resp_data_1_data; // @[Reg.scala 36:22]
    end
    if (reset) begin // @[Reg.scala 35:20]
      r__2_data <= 64'h0; // @[Reg.scala 35:20]
    end else if (REG) begin // @[Reg.scala 36:18]
      r__2_data <= ram_io_r_resp_data_2_data; // @[Reg.scala 36:22]
    end
    if (reset) begin // @[Reg.scala 35:20]
      r__3_data <= 64'h0; // @[Reg.scala 35:20]
    end else if (REG) begin // @[Reg.scala 36:18]
      r__3_data <= ram_io_r_resp_data_3_data; // @[Reg.scala 36:22]
    end
    REG_1 <= io_r_1_req_ready & io_r_1_req_valid; // @[Decoupled.scala 51:35]
    if (reset) begin // @[Reg.scala 35:20]
      r_1_0_data <= 64'h0; // @[Reg.scala 35:20]
    end else if (REG_1) begin // @[Reg.scala 36:18]
      r_1_0_data <= ram_io_r_resp_data_0_data; // @[Reg.scala 36:22]
    end
    if (reset) begin // @[Reg.scala 35:20]
      r_1_1_data <= 64'h0; // @[Reg.scala 35:20]
    end else if (REG_1) begin // @[Reg.scala 36:18]
      r_1_1_data <= ram_io_r_resp_data_1_data; // @[Reg.scala 36:22]
    end
    if (reset) begin // @[Reg.scala 35:20]
      r_1_2_data <= 64'h0; // @[Reg.scala 35:20]
    end else if (REG_1) begin // @[Reg.scala 36:18]
      r_1_2_data <= ram_io_r_resp_data_2_data; // @[Reg.scala 36:22]
    end
    if (reset) begin // @[Reg.scala 35:20]
      r_1_3_data <= 64'h0; // @[Reg.scala 35:20]
    end else if (REG_1) begin // @[Reg.scala 36:18]
      r_1_3_data <= ram_io_r_resp_data_3_data; // @[Reg.scala 36:22]
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
`ifdef RANDOMIZE_REG_INIT
  _RAND_0 = {1{`RANDOM}};
  REG = _RAND_0[0:0];
  _RAND_1 = {2{`RANDOM}};
  r__0_data = _RAND_1[63:0];
  _RAND_2 = {2{`RANDOM}};
  r__1_data = _RAND_2[63:0];
  _RAND_3 = {2{`RANDOM}};
  r__2_data = _RAND_3[63:0];
  _RAND_4 = {2{`RANDOM}};
  r__3_data = _RAND_4[63:0];
  _RAND_5 = {1{`RANDOM}};
  REG_1 = _RAND_5[0:0];
  _RAND_6 = {2{`RANDOM}};
  r_1_0_data = _RAND_6[63:0];
  _RAND_7 = {2{`RANDOM}};
  r_1_1_data = _RAND_7[63:0];
  _RAND_8 = {2{`RANDOM}};
  r_1_2_data = _RAND_8[63:0];
  _RAND_9 = {2{`RANDOM}};
  r_1_3_data = _RAND_9[63:0];
`endif // RANDOMIZE_REG_INIT
  `endif // RANDOMIZE
end // initial
`ifdef FIRRTL_AFTER_INITIAL
`FIRRTL_AFTER_INITIAL
`endif
`endif // SYNTHESIS
endmodule
