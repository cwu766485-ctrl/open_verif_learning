module SRAMTemplateWithArbiter(
  input         clock,
  input         reset,
  output        io_r_0_req_ready,
  input         io_r_0_req_valid,
  input  [6:0]  io_r_0_req_bits_setIdx,
  output [18:0] io_r_0_resp_data_0_tag,
  output        io_r_0_resp_data_0_valid,
  output        io_r_0_resp_data_0_dirty,
  output [18:0] io_r_0_resp_data_1_tag,
  output        io_r_0_resp_data_1_valid,
  output        io_r_0_resp_data_1_dirty,
  output [18:0] io_r_0_resp_data_2_tag,
  output        io_r_0_resp_data_2_valid,
  output        io_r_0_resp_data_2_dirty,
  output [18:0] io_r_0_resp_data_3_tag,
  output        io_r_0_resp_data_3_valid,
  output        io_r_0_resp_data_3_dirty,
  input         io_w_req_valid,
  input  [6:0]  io_w_req_bits_setIdx,
  input  [18:0] io_w_req_bits_data_tag,
  input         io_w_req_bits_data_dirty,
  input  [3:0]  io_w_req_bits_waymask
);
`ifdef RANDOMIZE_REG_INIT
  reg [31:0] _RAND_0;
  reg [31:0] _RAND_1;
  reg [31:0] _RAND_2;
  reg [31:0] _RAND_3;
  reg [31:0] _RAND_4;
  reg [31:0] _RAND_5;
  reg [31:0] _RAND_6;
  reg [31:0] _RAND_7;
  reg [31:0] _RAND_8;
  reg [31:0] _RAND_9;
  reg [31:0] _RAND_10;
  reg [31:0] _RAND_11;
  reg [31:0] _RAND_12;
`endif // RANDOMIZE_REG_INIT
  wire  ram_clock; // @[SRAMTemplate.scala 121:19]
  wire  ram_reset; // @[SRAMTemplate.scala 121:19]
  wire  ram_io_r_req_ready; // @[SRAMTemplate.scala 121:19]
  wire  ram_io_r_req_valid; // @[SRAMTemplate.scala 121:19]
  wire [6:0] ram_io_r_req_bits_setIdx; // @[SRAMTemplate.scala 121:19]
  wire [18:0] ram_io_r_resp_data_0_tag; // @[SRAMTemplate.scala 121:19]
  wire  ram_io_r_resp_data_0_valid; // @[SRAMTemplate.scala 121:19]
  wire  ram_io_r_resp_data_0_dirty; // @[SRAMTemplate.scala 121:19]
  wire [18:0] ram_io_r_resp_data_1_tag; // @[SRAMTemplate.scala 121:19]
  wire  ram_io_r_resp_data_1_valid; // @[SRAMTemplate.scala 121:19]
  wire  ram_io_r_resp_data_1_dirty; // @[SRAMTemplate.scala 121:19]
  wire [18:0] ram_io_r_resp_data_2_tag; // @[SRAMTemplate.scala 121:19]
  wire  ram_io_r_resp_data_2_valid; // @[SRAMTemplate.scala 121:19]
  wire  ram_io_r_resp_data_2_dirty; // @[SRAMTemplate.scala 121:19]
  wire [18:0] ram_io_r_resp_data_3_tag; // @[SRAMTemplate.scala 121:19]
  wire  ram_io_r_resp_data_3_valid; // @[SRAMTemplate.scala 121:19]
  wire  ram_io_r_resp_data_3_dirty; // @[SRAMTemplate.scala 121:19]
  wire  ram_io_w_req_valid; // @[SRAMTemplate.scala 121:19]
  wire [6:0] ram_io_w_req_bits_setIdx; // @[SRAMTemplate.scala 121:19]
  wire [18:0] ram_io_w_req_bits_data_tag; // @[SRAMTemplate.scala 121:19]
  wire  ram_io_w_req_bits_data_dirty; // @[SRAMTemplate.scala 121:19]
  wire [3:0] ram_io_w_req_bits_waymask; // @[SRAMTemplate.scala 121:19]
  wire  readArb_io_in_0_ready; // @[SRAMTemplate.scala 124:23]
  wire  readArb_io_in_0_valid; // @[SRAMTemplate.scala 124:23]
  wire [6:0] readArb_io_in_0_bits_setIdx; // @[SRAMTemplate.scala 124:23]
  wire  readArb_io_out_ready; // @[SRAMTemplate.scala 124:23]
  wire  readArb_io_out_valid; // @[SRAMTemplate.scala 124:23]
  wire [6:0] readArb_io_out_bits_setIdx; // @[SRAMTemplate.scala 124:23]
  reg  REG; // @[SRAMTemplate.scala 130:58]
  reg [18:0] r_0_tag; // @[Reg.scala 35:20]
  reg  r_0_valid; // @[Reg.scala 35:20]
  reg  r_0_dirty; // @[Reg.scala 35:20]
  reg [18:0] r_1_tag; // @[Reg.scala 35:20]
  reg  r_1_valid; // @[Reg.scala 35:20]
  reg  r_1_dirty; // @[Reg.scala 35:20]
  reg [18:0] r_2_tag; // @[Reg.scala 35:20]
  reg  r_2_valid; // @[Reg.scala 35:20]
  reg  r_2_dirty; // @[Reg.scala 35:20]
  reg [18:0] r_3_tag; // @[Reg.scala 35:20]
  reg  r_3_valid; // @[Reg.scala 35:20]
  reg  r_3_dirty; // @[Reg.scala 35:20]
  SRAMTemplate ram ( // @[SRAMTemplate.scala 121:19]
    .clock(ram_clock),
    .reset(ram_reset),
    .io_r_req_ready(ram_io_r_req_ready),
    .io_r_req_valid(ram_io_r_req_valid),
    .io_r_req_bits_setIdx(ram_io_r_req_bits_setIdx),
    .io_r_resp_data_0_tag(ram_io_r_resp_data_0_tag),
    .io_r_resp_data_0_valid(ram_io_r_resp_data_0_valid),
    .io_r_resp_data_0_dirty(ram_io_r_resp_data_0_dirty),
    .io_r_resp_data_1_tag(ram_io_r_resp_data_1_tag),
    .io_r_resp_data_1_valid(ram_io_r_resp_data_1_valid),
    .io_r_resp_data_1_dirty(ram_io_r_resp_data_1_dirty),
    .io_r_resp_data_2_tag(ram_io_r_resp_data_2_tag),
    .io_r_resp_data_2_valid(ram_io_r_resp_data_2_valid),
    .io_r_resp_data_2_dirty(ram_io_r_resp_data_2_dirty),
    .io_r_resp_data_3_tag(ram_io_r_resp_data_3_tag),
    .io_r_resp_data_3_valid(ram_io_r_resp_data_3_valid),
    .io_r_resp_data_3_dirty(ram_io_r_resp_data_3_dirty),
    .io_w_req_valid(ram_io_w_req_valid),
    .io_w_req_bits_setIdx(ram_io_w_req_bits_setIdx),
    .io_w_req_bits_data_tag(ram_io_w_req_bits_data_tag),
    .io_w_req_bits_data_dirty(ram_io_w_req_bits_data_dirty),
    .io_w_req_bits_waymask(ram_io_w_req_bits_waymask)
  );
  Arbiter_2 readArb ( // @[SRAMTemplate.scala 124:23]
    .io_in_0_ready(readArb_io_in_0_ready),
    .io_in_0_valid(readArb_io_in_0_valid),
    .io_in_0_bits_setIdx(readArb_io_in_0_bits_setIdx),
    .io_out_ready(readArb_io_out_ready),
    .io_out_valid(readArb_io_out_valid),
    .io_out_bits_setIdx(readArb_io_out_bits_setIdx)
  );
  assign io_r_0_req_ready = readArb_io_in_0_ready; // @[SRAMTemplate.scala 125:17]
  assign io_r_0_resp_data_0_tag = REG ? ram_io_r_resp_data_0_tag : r_0_tag; // @[Hold.scala 23:48]
  assign io_r_0_resp_data_0_valid = REG ? ram_io_r_resp_data_0_valid : r_0_valid; // @[Hold.scala 23:48]
  assign io_r_0_resp_data_0_dirty = REG ? ram_io_r_resp_data_0_dirty : r_0_dirty; // @[Hold.scala 23:48]
  assign io_r_0_resp_data_1_tag = REG ? ram_io_r_resp_data_1_tag : r_1_tag; // @[Hold.scala 23:48]
  assign io_r_0_resp_data_1_valid = REG ? ram_io_r_resp_data_1_valid : r_1_valid; // @[Hold.scala 23:48]
  assign io_r_0_resp_data_1_dirty = REG ? ram_io_r_resp_data_1_dirty : r_1_dirty; // @[Hold.scala 23:48]
  assign io_r_0_resp_data_2_tag = REG ? ram_io_r_resp_data_2_tag : r_2_tag; // @[Hold.scala 23:48]
  assign io_r_0_resp_data_2_valid = REG ? ram_io_r_resp_data_2_valid : r_2_valid; // @[Hold.scala 23:48]
  assign io_r_0_resp_data_2_dirty = REG ? ram_io_r_resp_data_2_dirty : r_2_dirty; // @[Hold.scala 23:48]
  assign io_r_0_resp_data_3_tag = REG ? ram_io_r_resp_data_3_tag : r_3_tag; // @[Hold.scala 23:48]
  assign io_r_0_resp_data_3_valid = REG ? ram_io_r_resp_data_3_valid : r_3_valid; // @[Hold.scala 23:48]
  assign io_r_0_resp_data_3_dirty = REG ? ram_io_r_resp_data_3_dirty : r_3_dirty; // @[Hold.scala 23:48]
  assign ram_clock = clock;
  assign ram_reset = reset;
  assign ram_io_r_req_valid = readArb_io_out_valid; // @[SRAMTemplate.scala 126:16]
  assign ram_io_r_req_bits_setIdx = readArb_io_out_bits_setIdx; // @[SRAMTemplate.scala 126:16]
  assign ram_io_w_req_valid = io_w_req_valid; // @[SRAMTemplate.scala 122:12]
  assign ram_io_w_req_bits_setIdx = io_w_req_bits_setIdx; // @[SRAMTemplate.scala 122:12]
  assign ram_io_w_req_bits_data_tag = io_w_req_bits_data_tag; // @[SRAMTemplate.scala 122:12]
  assign ram_io_w_req_bits_data_dirty = io_w_req_bits_data_dirty; // @[SRAMTemplate.scala 122:12]
  assign ram_io_w_req_bits_waymask = io_w_req_bits_waymask; // @[SRAMTemplate.scala 122:12]
  assign readArb_io_in_0_valid = io_r_0_req_valid; // @[SRAMTemplate.scala 125:17]
  assign readArb_io_in_0_bits_setIdx = io_r_0_req_bits_setIdx; // @[SRAMTemplate.scala 125:17]
  assign readArb_io_out_ready = ram_io_r_req_ready; // @[SRAMTemplate.scala 126:16]
  always @(posedge clock) begin
    REG <= io_r_0_req_ready & io_r_0_req_valid; // @[Decoupled.scala 51:35]
    if (reset) begin // @[Reg.scala 35:20]
      r_0_tag <= 19'h0; // @[Reg.scala 35:20]
    end else if (REG) begin // @[Reg.scala 36:18]
      r_0_tag <= ram_io_r_resp_data_0_tag; // @[Reg.scala 36:22]
    end
    if (reset) begin // @[Reg.scala 35:20]
      r_0_valid <= 1'h0; // @[Reg.scala 35:20]
    end else if (REG) begin // @[Reg.scala 36:18]
      r_0_valid <= ram_io_r_resp_data_0_valid; // @[Reg.scala 36:22]
    end
    if (reset) begin // @[Reg.scala 35:20]
      r_0_dirty <= 1'h0; // @[Reg.scala 35:20]
    end else if (REG) begin // @[Reg.scala 36:18]
      r_0_dirty <= ram_io_r_resp_data_0_dirty; // @[Reg.scala 36:22]
    end
    if (reset) begin // @[Reg.scala 35:20]
      r_1_tag <= 19'h0; // @[Reg.scala 35:20]
    end else if (REG) begin // @[Reg.scala 36:18]
      r_1_tag <= ram_io_r_resp_data_1_tag; // @[Reg.scala 36:22]
    end
    if (reset) begin // @[Reg.scala 35:20]
      r_1_valid <= 1'h0; // @[Reg.scala 35:20]
    end else if (REG) begin // @[Reg.scala 36:18]
      r_1_valid <= ram_io_r_resp_data_1_valid; // @[Reg.scala 36:22]
    end
    if (reset) begin // @[Reg.scala 35:20]
      r_1_dirty <= 1'h0; // @[Reg.scala 35:20]
    end else if (REG) begin // @[Reg.scala 36:18]
      r_1_dirty <= ram_io_r_resp_data_1_dirty; // @[Reg.scala 36:22]
    end
    if (reset) begin // @[Reg.scala 35:20]
      r_2_tag <= 19'h0; // @[Reg.scala 35:20]
    end else if (REG) begin // @[Reg.scala 36:18]
      r_2_tag <= ram_io_r_resp_data_2_tag; // @[Reg.scala 36:22]
    end
    if (reset) begin // @[Reg.scala 35:20]
      r_2_valid <= 1'h0; // @[Reg.scala 35:20]
    end else if (REG) begin // @[Reg.scala 36:18]
      r_2_valid <= ram_io_r_resp_data_2_valid; // @[Reg.scala 36:22]
    end
    if (reset) begin // @[Reg.scala 35:20]
      r_2_dirty <= 1'h0; // @[Reg.scala 35:20]
    end else if (REG) begin // @[Reg.scala 36:18]
      r_2_dirty <= ram_io_r_resp_data_2_dirty; // @[Reg.scala 36:22]
    end
    if (reset) begin // @[Reg.scala 35:20]
      r_3_tag <= 19'h0; // @[Reg.scala 35:20]
    end else if (REG) begin // @[Reg.scala 36:18]
      r_3_tag <= ram_io_r_resp_data_3_tag; // @[Reg.scala 36:22]
    end
    if (reset) begin // @[Reg.scala 35:20]
      r_3_valid <= 1'h0; // @[Reg.scala 35:20]
    end else if (REG) begin // @[Reg.scala 36:18]
      r_3_valid <= ram_io_r_resp_data_3_valid; // @[Reg.scala 36:22]
    end
    if (reset) begin // @[Reg.scala 35:20]
      r_3_dirty <= 1'h0; // @[Reg.scala 35:20]
    end else if (REG) begin // @[Reg.scala 36:18]
      r_3_dirty <= ram_io_r_resp_data_3_dirty; // @[Reg.scala 36:22]
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
  _RAND_1 = {1{`RANDOM}};
  r_0_tag = _RAND_1[18:0];
  _RAND_2 = {1{`RANDOM}};
  r_0_valid = _RAND_2[0:0];
  _RAND_3 = {1{`RANDOM}};
  r_0_dirty = _RAND_3[0:0];
  _RAND_4 = {1{`RANDOM}};
  r_1_tag = _RAND_4[18:0];
  _RAND_5 = {1{`RANDOM}};
  r_1_valid = _RAND_5[0:0];
  _RAND_6 = {1{`RANDOM}};
  r_1_dirty = _RAND_6[0:0];
  _RAND_7 = {1{`RANDOM}};
  r_2_tag = _RAND_7[18:0];
  _RAND_8 = {1{`RANDOM}};
  r_2_valid = _RAND_8[0:0];
  _RAND_9 = {1{`RANDOM}};
  r_2_dirty = _RAND_9[0:0];
  _RAND_10 = {1{`RANDOM}};
  r_3_tag = _RAND_10[18:0];
  _RAND_11 = {1{`RANDOM}};
  r_3_valid = _RAND_11[0:0];
  _RAND_12 = {1{`RANDOM}};
  r_3_dirty = _RAND_12[0:0];
`endif // RANDOMIZE_REG_INIT
  `endif // RANDOMIZE
end // initial
`ifdef FIRRTL_AFTER_INITIAL
`FIRRTL_AFTER_INITIAL
`endif
`endif // SYNTHESIS
endmodule
