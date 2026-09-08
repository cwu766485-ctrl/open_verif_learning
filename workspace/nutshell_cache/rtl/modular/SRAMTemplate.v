module SRAMTemplate(
  input         clock,
  input         reset,
  output        io_r_req_ready,
  input         io_r_req_valid,
  input  [6:0]  io_r_req_bits_setIdx,
  output [18:0] io_r_resp_data_0_tag,
  output        io_r_resp_data_0_valid,
  output        io_r_resp_data_0_dirty,
  output [18:0] io_r_resp_data_1_tag,
  output        io_r_resp_data_1_valid,
  output        io_r_resp_data_1_dirty,
  output [18:0] io_r_resp_data_2_tag,
  output        io_r_resp_data_2_valid,
  output        io_r_resp_data_2_dirty,
  output [18:0] io_r_resp_data_3_tag,
  output        io_r_resp_data_3_valid,
  output        io_r_resp_data_3_dirty,
  input         io_w_req_valid,
  input  [6:0]  io_w_req_bits_setIdx,
  input  [18:0] io_w_req_bits_data_tag,
  input         io_w_req_bits_data_dirty,
  input  [3:0]  io_w_req_bits_waymask
);
`ifdef RANDOMIZE_MEM_INIT
  reg [31:0] _RAND_0;
  reg [31:0] _RAND_3;
  reg [31:0] _RAND_6;
  reg [31:0] _RAND_9;
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
  reg [31:0] _RAND_12;
  reg [31:0] _RAND_13;
`endif // RANDOMIZE_REG_INIT
  reg [20:0] array_0 [0:127]; // @[SRAMTemplate.scala 76:26]
  wire  array_0_rdata_MPORT_en; // @[SRAMTemplate.scala 76:26]
  wire [6:0] array_0_rdata_MPORT_addr; // @[SRAMTemplate.scala 76:26]
  wire [20:0] array_0_rdata_MPORT_data; // @[SRAMTemplate.scala 76:26]
  wire [20:0] array_0_MPORT_data; // @[SRAMTemplate.scala 76:26]
  wire [6:0] array_0_MPORT_addr; // @[SRAMTemplate.scala 76:26]
  wire  array_0_MPORT_mask; // @[SRAMTemplate.scala 76:26]
  wire  array_0_MPORT_en; // @[SRAMTemplate.scala 76:26]
  reg  array_0_rdata_MPORT_en_pipe_0;
  reg [6:0] array_0_rdata_MPORT_addr_pipe_0;
  reg [20:0] array_1 [0:127]; // @[SRAMTemplate.scala 76:26]
  wire  array_1_rdata_MPORT_en; // @[SRAMTemplate.scala 76:26]
  wire [6:0] array_1_rdata_MPORT_addr; // @[SRAMTemplate.scala 76:26]
  wire [20:0] array_1_rdata_MPORT_data; // @[SRAMTemplate.scala 76:26]
  wire [20:0] array_1_MPORT_data; // @[SRAMTemplate.scala 76:26]
  wire [6:0] array_1_MPORT_addr; // @[SRAMTemplate.scala 76:26]
  wire  array_1_MPORT_mask; // @[SRAMTemplate.scala 76:26]
  wire  array_1_MPORT_en; // @[SRAMTemplate.scala 76:26]
  reg  array_1_rdata_MPORT_en_pipe_0;
  reg [6:0] array_1_rdata_MPORT_addr_pipe_0;
  reg [20:0] array_2 [0:127]; // @[SRAMTemplate.scala 76:26]
  wire  array_2_rdata_MPORT_en; // @[SRAMTemplate.scala 76:26]
  wire [6:0] array_2_rdata_MPORT_addr; // @[SRAMTemplate.scala 76:26]
  wire [20:0] array_2_rdata_MPORT_data; // @[SRAMTemplate.scala 76:26]
  wire [20:0] array_2_MPORT_data; // @[SRAMTemplate.scala 76:26]
  wire [6:0] array_2_MPORT_addr; // @[SRAMTemplate.scala 76:26]
  wire  array_2_MPORT_mask; // @[SRAMTemplate.scala 76:26]
  wire  array_2_MPORT_en; // @[SRAMTemplate.scala 76:26]
  reg  array_2_rdata_MPORT_en_pipe_0;
  reg [6:0] array_2_rdata_MPORT_addr_pipe_0;
  reg [20:0] array_3 [0:127]; // @[SRAMTemplate.scala 76:26]
  wire  array_3_rdata_MPORT_en; // @[SRAMTemplate.scala 76:26]
  wire [6:0] array_3_rdata_MPORT_addr; // @[SRAMTemplate.scala 76:26]
  wire [20:0] array_3_rdata_MPORT_data; // @[SRAMTemplate.scala 76:26]
  wire [20:0] array_3_MPORT_data; // @[SRAMTemplate.scala 76:26]
  wire [6:0] array_3_MPORT_addr; // @[SRAMTemplate.scala 76:26]
  wire  array_3_MPORT_mask; // @[SRAMTemplate.scala 76:26]
  wire  array_3_MPORT_en; // @[SRAMTemplate.scala 76:26]
  reg  array_3_rdata_MPORT_en_pipe_0;
  reg [6:0] array_3_rdata_MPORT_addr_pipe_0;
  reg  resetState; // @[SRAMTemplate.scala 80:30]
  reg [6:0] resetSet; // @[Counter.scala 61:40]
  wire  wrap_wrap = resetSet == 7'h7f; // @[Counter.scala 73:24]
  wire [6:0] _wrap_value_T_1 = resetSet + 7'h1; // @[Counter.scala 77:24]
  wire  resetFinish = resetState & wrap_wrap; // @[Counter.scala 118:{16,23} 117:24]
  wire  _GEN_2 = resetFinish ? 1'h0 : resetState; // @[SRAMTemplate.scala 82:24 80:30 82:38]
  wire  wen = io_w_req_valid | resetState; // @[SRAMTemplate.scala 88:52]
  wire  _realRen_T = ~wen; // @[SRAMTemplate.scala 89:41]
  wire [20:0] _wdataword_T = {io_w_req_bits_data_tag,1'h1,io_w_req_bits_data_dirty}; // @[SRAMTemplate.scala 92:78]
  wire [3:0] waymask = resetState ? 4'hf : io_w_req_bits_waymask; // @[SRAMTemplate.scala 93:20]
  wire [20:0] _rdata_WIRE_1 = array_0_rdata_MPORT_data; // @[SRAMTemplate.scala 98:{78,78}]
  wire [20:0] _rdata_WIRE_2 = array_1_rdata_MPORT_data; // @[SRAMTemplate.scala 98:{78,78}]
  wire [20:0] _rdata_WIRE_3 = array_2_rdata_MPORT_data; // @[SRAMTemplate.scala 98:{78,78}]
  wire [20:0] _rdata_WIRE_4 = array_3_rdata_MPORT_data; // @[SRAMTemplate.scala 98:{78,78}]
  assign array_0_rdata_MPORT_en = array_0_rdata_MPORT_en_pipe_0;
  assign array_0_rdata_MPORT_addr = array_0_rdata_MPORT_addr_pipe_0;
  assign array_0_rdata_MPORT_data = array_0[array_0_rdata_MPORT_addr]; // @[SRAMTemplate.scala 76:26]
  assign array_0_MPORT_data = resetState ? 21'h0 : _wdataword_T;
  assign array_0_MPORT_addr = resetState ? resetSet : io_w_req_bits_setIdx;
  assign array_0_MPORT_mask = waymask[0];
  assign array_0_MPORT_en = io_w_req_valid | resetState;
  assign array_1_rdata_MPORT_en = array_1_rdata_MPORT_en_pipe_0;
  assign array_1_rdata_MPORT_addr = array_1_rdata_MPORT_addr_pipe_0;
  assign array_1_rdata_MPORT_data = array_1[array_1_rdata_MPORT_addr]; // @[SRAMTemplate.scala 76:26]
  assign array_1_MPORT_data = resetState ? 21'h0 : _wdataword_T;
  assign array_1_MPORT_addr = resetState ? resetSet : io_w_req_bits_setIdx;
  assign array_1_MPORT_mask = waymask[1];
  assign array_1_MPORT_en = io_w_req_valid | resetState;
  assign array_2_rdata_MPORT_en = array_2_rdata_MPORT_en_pipe_0;
  assign array_2_rdata_MPORT_addr = array_2_rdata_MPORT_addr_pipe_0;
  assign array_2_rdata_MPORT_data = array_2[array_2_rdata_MPORT_addr]; // @[SRAMTemplate.scala 76:26]
  assign array_2_MPORT_data = resetState ? 21'h0 : _wdataword_T;
  assign array_2_MPORT_addr = resetState ? resetSet : io_w_req_bits_setIdx;
  assign array_2_MPORT_mask = waymask[2];
  assign array_2_MPORT_en = io_w_req_valid | resetState;
  assign array_3_rdata_MPORT_en = array_3_rdata_MPORT_en_pipe_0;
  assign array_3_rdata_MPORT_addr = array_3_rdata_MPORT_addr_pipe_0;
  assign array_3_rdata_MPORT_data = array_3[array_3_rdata_MPORT_addr]; // @[SRAMTemplate.scala 76:26]
  assign array_3_MPORT_data = resetState ? 21'h0 : _wdataword_T;
  assign array_3_MPORT_addr = resetState ? resetSet : io_w_req_bits_setIdx;
  assign array_3_MPORT_mask = waymask[3];
  assign array_3_MPORT_en = io_w_req_valid | resetState;
  assign io_r_req_ready = ~resetState & _realRen_T; // @[SRAMTemplate.scala 101:33]
  assign io_r_resp_data_0_tag = _rdata_WIRE_1[20:2]; // @[SRAMTemplate.scala 98:78]
  assign io_r_resp_data_0_valid = _rdata_WIRE_1[1]; // @[SRAMTemplate.scala 98:78]
  assign io_r_resp_data_0_dirty = _rdata_WIRE_1[0]; // @[SRAMTemplate.scala 98:78]
  assign io_r_resp_data_1_tag = _rdata_WIRE_2[20:2]; // @[SRAMTemplate.scala 98:78]
  assign io_r_resp_data_1_valid = _rdata_WIRE_2[1]; // @[SRAMTemplate.scala 98:78]
  assign io_r_resp_data_1_dirty = _rdata_WIRE_2[0]; // @[SRAMTemplate.scala 98:78]
  assign io_r_resp_data_2_tag = _rdata_WIRE_3[20:2]; // @[SRAMTemplate.scala 98:78]
  assign io_r_resp_data_2_valid = _rdata_WIRE_3[1]; // @[SRAMTemplate.scala 98:78]
  assign io_r_resp_data_2_dirty = _rdata_WIRE_3[0]; // @[SRAMTemplate.scala 98:78]
  assign io_r_resp_data_3_tag = _rdata_WIRE_4[20:2]; // @[SRAMTemplate.scala 98:78]
  assign io_r_resp_data_3_valid = _rdata_WIRE_4[1]; // @[SRAMTemplate.scala 98:78]
  assign io_r_resp_data_3_dirty = _rdata_WIRE_4[0]; // @[SRAMTemplate.scala 98:78]
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
    resetState <= reset | _GEN_2; // @[SRAMTemplate.scala 80:{30,30}]
    if (reset) begin // @[Counter.scala 61:40]
      resetSet <= 7'h0; // @[Counter.scala 61:40]
    end else if (resetState) begin // @[Counter.scala 118:16]
      resetSet <= _wrap_value_T_1; // @[Counter.scala 77:15]
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
  _RAND_0 = {1{`RANDOM}};
  for (initvar = 0; initvar < 128; initvar = initvar+1)
    array_0[initvar] = _RAND_0[20:0];
  _RAND_3 = {1{`RANDOM}};
  for (initvar = 0; initvar < 128; initvar = initvar+1)
    array_1[initvar] = _RAND_3[20:0];
  _RAND_6 = {1{`RANDOM}};
  for (initvar = 0; initvar < 128; initvar = initvar+1)
    array_2[initvar] = _RAND_6[20:0];
  _RAND_9 = {1{`RANDOM}};
  for (initvar = 0; initvar < 128; initvar = initvar+1)
    array_3[initvar] = _RAND_9[20:0];
`endif // RANDOMIZE_MEM_INIT
`ifdef RANDOMIZE_REG_INIT
  _RAND_1 = {1{`RANDOM}};
  array_0_rdata_MPORT_en_pipe_0 = _RAND_1[0:0];
  _RAND_2 = {1{`RANDOM}};
  array_0_rdata_MPORT_addr_pipe_0 = _RAND_2[6:0];
  _RAND_4 = {1{`RANDOM}};
  array_1_rdata_MPORT_en_pipe_0 = _RAND_4[0:0];
  _RAND_5 = {1{`RANDOM}};
  array_1_rdata_MPORT_addr_pipe_0 = _RAND_5[6:0];
  _RAND_7 = {1{`RANDOM}};
  array_2_rdata_MPORT_en_pipe_0 = _RAND_7[0:0];
  _RAND_8 = {1{`RANDOM}};
  array_2_rdata_MPORT_addr_pipe_0 = _RAND_8[6:0];
  _RAND_10 = {1{`RANDOM}};
  array_3_rdata_MPORT_en_pipe_0 = _RAND_10[0:0];
  _RAND_11 = {1{`RANDOM}};
  array_3_rdata_MPORT_addr_pipe_0 = _RAND_11[6:0];
  _RAND_12 = {1{`RANDOM}};
  resetState = _RAND_12[0:0];
  _RAND_13 = {1{`RANDOM}};
  resetSet = _RAND_13[6:0];
`endif // RANDOMIZE_REG_INIT
  `endif // RANDOMIZE
end // initial
`ifdef FIRRTL_AFTER_INITIAL
`FIRRTL_AFTER_INITIAL
`endif
`endif // SYNTHESIS
endmodule
