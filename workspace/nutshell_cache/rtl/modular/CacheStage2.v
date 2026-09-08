module CacheStage2(
  input         clock,
  input         reset,
  output        io_in_ready,
  input         io_in_valid,
  input  [31:0] io_in_bits_req_addr,
  input  [2:0]  io_in_bits_req_size,
  input  [3:0]  io_in_bits_req_cmd,
  input  [7:0]  io_in_bits_req_wmask,
  input  [63:0] io_in_bits_req_wdata,
  input  [15:0] io_in_bits_req_user,
  input         io_out_ready,
  output        io_out_valid,
  output [31:0] io_out_bits_req_addr,
  output [2:0]  io_out_bits_req_size,
  output [3:0]  io_out_bits_req_cmd,
  output [7:0]  io_out_bits_req_wmask,
  output [63:0] io_out_bits_req_wdata,
  output [15:0] io_out_bits_req_user,
  output [18:0] io_out_bits_metas_0_tag,
  output        io_out_bits_metas_0_dirty,
  output [18:0] io_out_bits_metas_1_tag,
  output        io_out_bits_metas_1_dirty,
  output [18:0] io_out_bits_metas_2_tag,
  output        io_out_bits_metas_2_dirty,
  output [18:0] io_out_bits_metas_3_tag,
  output        io_out_bits_metas_3_dirty,
  output [63:0] io_out_bits_datas_0_data,
  output [63:0] io_out_bits_datas_1_data,
  output [63:0] io_out_bits_datas_2_data,
  output [63:0] io_out_bits_datas_3_data,
  output        io_out_bits_hit,
  output [3:0]  io_out_bits_waymask,
  output        io_out_bits_mmio,
  output        io_out_bits_isForwardData,
  output [63:0] io_out_bits_forwardData_data_data,
  output [3:0]  io_out_bits_forwardData_waymask,
  output [3:0]  victim_way_mask,
  input  [18:0] io_metaReadResp_0_tag,
  input         io_metaReadResp_0_valid,
  input         io_metaReadResp_0_dirty,
  input  [18:0] io_metaReadResp_1_tag,
  input         io_metaReadResp_1_valid,
  input         io_metaReadResp_1_dirty,
  input  [18:0] io_metaReadResp_2_tag,
  input         io_metaReadResp_2_valid,
  input         io_metaReadResp_2_dirty,
  input  [18:0] io_metaReadResp_3_tag,
  input         io_metaReadResp_3_valid,
  input         io_metaReadResp_3_dirty,
  input  [63:0] io_dataReadResp_0_data,
  input  [63:0] io_dataReadResp_1_data,
  input  [63:0] io_dataReadResp_2_data,
  input  [63:0] io_dataReadResp_3_data,
  input         io_metaWriteBus_req_valid,
  input  [6:0]  io_metaWriteBus_req_bits_setIdx,
  input  [18:0] io_metaWriteBus_req_bits_data_tag,
  input         io_metaWriteBus_req_bits_data_dirty,
  input  [3:0]  io_metaWriteBus_req_bits_waymask,
  input         io_dataWriteBus_req_valid,
  input  [9:0]  io_dataWriteBus_req_bits_setIdx,
  input  [63:0] io_dataWriteBus_req_bits_data_data,
  input  [3:0]  io_dataWriteBus_req_bits_waymask
);
`ifdef RANDOMIZE_REG_INIT
  reg [31:0] _RAND_0;
  reg [31:0] _RAND_1;
  reg [31:0] _RAND_2;
  reg [31:0] _RAND_3;
  reg [63:0] _RAND_4;
  reg [31:0] _RAND_5;
  reg [63:0] _RAND_6;
  reg [31:0] _RAND_7;
`endif // RANDOMIZE_REG_INIT
  wire [2:0] addr_wordIndex = io_in_bits_req_addr[5:3]; // @[Cache.scala 174:31]
  wire [6:0] addr_index = io_in_bits_req_addr[12:6]; // @[Cache.scala 174:31]
  wire [18:0] addr_tag = io_in_bits_req_addr[31:13]; // @[Cache.scala 174:31]
  wire  isForwardMeta = io_in_valid & io_metaWriteBus_req_valid & io_metaWriteBus_req_bits_setIdx == addr_index; // @[Cache.scala 176:64]
  reg  isForwardMetaReg; // @[Cache.scala 177:33]
  wire  _GEN_0 = isForwardMeta | isForwardMetaReg; // @[Cache.scala 178:24 177:33 178:43]
  wire  _T = io_in_ready & io_in_valid; // @[Decoupled.scala 51:35]
  wire  _T_1 = ~io_in_valid; // @[Cache.scala 179:23]
  wire  _T_2 = _T | ~io_in_valid; // @[Cache.scala 179:20]
  reg [18:0] forwardMetaReg_data_tag; // @[Reg.scala 19:16]
  reg  forwardMetaReg_data_dirty; // @[Reg.scala 19:16]
  reg [3:0] forwardMetaReg_waymask; // @[Reg.scala 19:16]
  wire [18:0] _GEN_3 = isForwardMeta ? io_metaWriteBus_req_bits_data_tag : forwardMetaReg_data_tag; // @[Reg.scala 19:16 20:{18,22}]
  wire  _GEN_5 = isForwardMeta ? io_metaWriteBus_req_bits_data_dirty : forwardMetaReg_data_dirty; // @[Reg.scala 19:16 20:{18,22}]
  wire [3:0] _GEN_6 = isForwardMeta ? io_metaWriteBus_req_bits_waymask : forwardMetaReg_waymask; // @[Reg.scala 19:16 20:{18,22}]
  wire  pickForwardMeta = isForwardMetaReg | isForwardMeta; // @[Cache.scala 183:42]
  wire  forwardWaymask_0 = _GEN_6[0]; // @[Cache.scala 185:61]
  wire  forwardWaymask_1 = _GEN_6[1]; // @[Cache.scala 185:61]
  wire  forwardWaymask_2 = _GEN_6[2]; // @[Cache.scala 185:61]
  wire  forwardWaymask_3 = _GEN_6[3]; // @[Cache.scala 185:61]
  wire [18:0] metaWay_0_tag = pickForwardMeta & forwardWaymask_0 ? _GEN_3 : io_metaReadResp_0_tag; // @[Cache.scala 187:22]
  wire  metaWay_0_valid = pickForwardMeta & forwardWaymask_0 | io_metaReadResp_0_valid; // @[Cache.scala 187:22]
  wire [18:0] metaWay_1_tag = pickForwardMeta & forwardWaymask_1 ? _GEN_3 : io_metaReadResp_1_tag; // @[Cache.scala 187:22]
  wire  metaWay_1_valid = pickForwardMeta & forwardWaymask_1 | io_metaReadResp_1_valid; // @[Cache.scala 187:22]
  wire [18:0] metaWay_2_tag = pickForwardMeta & forwardWaymask_2 ? _GEN_3 : io_metaReadResp_2_tag; // @[Cache.scala 187:22]
  wire  metaWay_2_valid = pickForwardMeta & forwardWaymask_2 | io_metaReadResp_2_valid; // @[Cache.scala 187:22]
  wire [18:0] metaWay_3_tag = pickForwardMeta & forwardWaymask_3 ? _GEN_3 : io_metaReadResp_3_tag; // @[Cache.scala 187:22]
  wire  metaWay_3_valid = pickForwardMeta & forwardWaymask_3 | io_metaReadResp_3_valid; // @[Cache.scala 187:22]
  wire  _hitVec_T_2 = metaWay_0_valid & metaWay_0_tag == addr_tag & io_in_valid; // @[Cache.scala 190:73]
  wire  _hitVec_T_5 = metaWay_1_valid & metaWay_1_tag == addr_tag & io_in_valid; // @[Cache.scala 190:73]
  wire  _hitVec_T_8 = metaWay_2_valid & metaWay_2_tag == addr_tag & io_in_valid; // @[Cache.scala 190:73]
  wire  _hitVec_T_11 = metaWay_3_valid & metaWay_3_tag == addr_tag & io_in_valid; // @[Cache.scala 190:73]
  wire [3:0] hitVec = {_hitVec_T_11,_hitVec_T_8,_hitVec_T_5,_hitVec_T_2}; // @[Cache.scala 190:90]
  reg [63:0] victimWaymask_lfsr; // @[LFSR64.scala 25:23]
  wire  victimWaymask_xor = victimWaymask_lfsr[0] ^ victimWaymask_lfsr[1] ^ victimWaymask_lfsr[3] ^ victimWaymask_lfsr[4
    ]; // @[LFSR64.scala 26:43]
  wire [63:0] _victimWaymask_lfsr_T_2 = {victimWaymask_xor,victimWaymask_lfsr[63:1]}; // @[Cat.scala 33:92]
  wire [3:0] victimWaymask = 4'h1 << victimWaymask_lfsr[1:0]; // @[Cache.scala 191:42]
  assign victim_way_mask = victimWaymask; // Interface for uvm reference model
  wire  _invalidVec_T = ~metaWay_0_valid; // @[Cache.scala 193:45]
  wire  _invalidVec_T_1 = ~metaWay_1_valid; // @[Cache.scala 193:45]
  wire  _invalidVec_T_2 = ~metaWay_2_valid; // @[Cache.scala 193:45]
  wire  _invalidVec_T_3 = ~metaWay_3_valid; // @[Cache.scala 193:45]
  wire [3:0] invalidVec = {_invalidVec_T_3,_invalidVec_T_2,_invalidVec_T_1,_invalidVec_T}; // @[Cache.scala 193:56]
  wire  hasInvalidWay = |invalidVec; // @[Cache.scala 194:34]
  wire [1:0] _refillInvalidWaymask_T_3 = invalidVec >= 4'h2 ? 2'h2 : 2'h1; // @[Cache.scala 197:8]
  wire [2:0] _refillInvalidWaymask_T_4 = invalidVec >= 4'h4 ? 3'h4 : {{1'd0}, _refillInvalidWaymask_T_3}; // @[Cache.scala 196:8]
  wire [3:0] refillInvalidWaymask = invalidVec >= 4'h8 ? 4'h8 : {{1'd0}, _refillInvalidWaymask_T_4}; // @[Cache.scala 195:33]
  wire [3:0] _waymask_T = hasInvalidWay ? refillInvalidWaymask : victimWaymask; // @[Cache.scala 200:49]
  wire [3:0] waymask = io_out_bits_hit ? hitVec : _waymask_T; // @[Cache.scala 200:20]
  wire [1:0] _T_7 = waymask[0] + waymask[1]; // @[Bitwise.scala 51:90]
  wire [1:0] _T_9 = waymask[2] + waymask[3]; // @[Bitwise.scala 51:90]
  wire [2:0] _T_11 = _T_7 + _T_9; // @[Bitwise.scala 51:90]
  wire  _T_13 = _T_11 > 3'h1; // @[Cache.scala 201:26]
  wire  _T_16 = ~reset; // @[Debug.scala 56:24]
  wire [31:0] _io_out_bits_mmio_T = io_in_bits_req_addr ^ 32'h30000000; // @[NutCore.scala 86:11]
  wire  _io_out_bits_mmio_T_2 = _io_out_bits_mmio_T[31:28] == 4'h0; // @[NutCore.scala 86:44]
  wire [31:0] _io_out_bits_mmio_T_3 = io_in_bits_req_addr ^ 32'h40000000; // @[NutCore.scala 86:11]
  wire  _io_out_bits_mmio_T_5 = _io_out_bits_mmio_T_3[31:30] == 2'h0; // @[NutCore.scala 86:44]
  wire [9:0] _isForwardData_T_8 = {addr_index,addr_wordIndex}; // @[Cat.scala 33:92]
  wire  _isForwardData_T_10 = io_dataWriteBus_req_valid & io_dataWriteBus_req_bits_setIdx == _isForwardData_T_8; // @[Cache.scala 217:13]
  wire  isForwardData = io_in_valid & _isForwardData_T_10; // @[Cache.scala 216:35]
  reg  isForwardDataReg; // @[Cache.scala 219:33]
  wire  _GEN_8 = isForwardData | isForwardDataReg; // @[Cache.scala 220:24 219:33 220:43]
  reg [63:0] forwardDataReg_data_data; // @[Reg.scala 19:16]
  reg [3:0] forwardDataReg_waymask; // @[Reg.scala 19:16]
  wire  _io_in_ready_T_1 = io_out_ready & io_out_valid; // @[Decoupled.scala 51:35]
  assign io_in_ready = _T_1 | _io_in_ready_T_1; // @[Cache.scala 228:31]
  assign io_out_valid = io_in_valid; // @[Cache.scala 227:16]
  assign io_out_bits_req_addr = io_in_bits_req_addr; // @[Cache.scala 226:19]
  assign io_out_bits_req_size = io_in_bits_req_size; // @[Cache.scala 226:19]
  assign io_out_bits_req_cmd = io_in_bits_req_cmd; // @[Cache.scala 226:19]
  assign io_out_bits_req_wmask = io_in_bits_req_wmask; // @[Cache.scala 226:19]
  assign io_out_bits_req_wdata = io_in_bits_req_wdata; // @[Cache.scala 226:19]
  assign io_out_bits_req_user = io_in_bits_req_user; // @[Cache.scala 226:19]
  assign io_out_bits_metas_0_tag = pickForwardMeta & forwardWaymask_0 ? _GEN_3 : io_metaReadResp_0_tag; // @[Cache.scala 187:22]
  assign io_out_bits_metas_0_dirty = pickForwardMeta & forwardWaymask_0 ? _GEN_5 : io_metaReadResp_0_dirty; // @[Cache.scala 187:22]
  assign io_out_bits_metas_1_tag = pickForwardMeta & forwardWaymask_1 ? _GEN_3 : io_metaReadResp_1_tag; // @[Cache.scala 187:22]
  assign io_out_bits_metas_1_dirty = pickForwardMeta & forwardWaymask_1 ? _GEN_5 : io_metaReadResp_1_dirty; // @[Cache.scala 187:22]
  assign io_out_bits_metas_2_tag = pickForwardMeta & forwardWaymask_2 ? _GEN_3 : io_metaReadResp_2_tag; // @[Cache.scala 187:22]
  assign io_out_bits_metas_2_dirty = pickForwardMeta & forwardWaymask_2 ? _GEN_5 : io_metaReadResp_2_dirty; // @[Cache.scala 187:22]
  assign io_out_bits_metas_3_tag = pickForwardMeta & forwardWaymask_3 ? _GEN_3 : io_metaReadResp_3_tag; // @[Cache.scala 187:22]
  assign io_out_bits_metas_3_dirty = pickForwardMeta & forwardWaymask_3 ? _GEN_5 : io_metaReadResp_3_dirty; // @[Cache.scala 187:22]
  assign io_out_bits_datas_0_data = io_dataReadResp_0_data; // @[Cache.scala 213:21]
  assign io_out_bits_datas_1_data = io_dataReadResp_1_data; // @[Cache.scala 213:21]
  assign io_out_bits_datas_2_data = io_dataReadResp_2_data; // @[Cache.scala 213:21]
  assign io_out_bits_datas_3_data = io_dataReadResp_3_data; // @[Cache.scala 213:21]
  assign io_out_bits_hit = io_in_valid & |hitVec; // @[Cache.scala 211:34]
  assign io_out_bits_waymask = io_out_bits_hit ? hitVec : _waymask_T; // @[Cache.scala 200:20]
  assign io_out_bits_mmio = _io_out_bits_mmio_T_2 | _io_out_bits_mmio_T_5; // @[NutCore.scala 87:15]
  assign io_out_bits_isForwardData = isForwardDataReg | isForwardData; // @[Cache.scala 223:49]
  assign io_out_bits_forwardData_data_data = isForwardData ? io_dataWriteBus_req_bits_data_data :
    forwardDataReg_data_data; // @[Cache.scala 224:33]
  assign io_out_bits_forwardData_waymask = isForwardData ? io_dataWriteBus_req_bits_waymask : forwardDataReg_waymask; // @[Cache.scala 224:33]
  always @(posedge clock) begin
    if (reset) begin // @[Cache.scala 177:33]
      isForwardMetaReg <= 1'h0; // @[Cache.scala 177:33]
    end else if (_T | ~io_in_valid) begin // @[Cache.scala 179:37]
      isForwardMetaReg <= 1'h0; // @[Cache.scala 179:56]
    end else begin
      isForwardMetaReg <= _GEN_0;
    end
    if (isForwardMeta) begin // @[Reg.scala 20:18]
      forwardMetaReg_data_tag <= io_metaWriteBus_req_bits_data_tag; // @[Reg.scala 20:22]
    end
    if (isForwardMeta) begin // @[Reg.scala 20:18]
      forwardMetaReg_data_dirty <= io_metaWriteBus_req_bits_data_dirty; // @[Reg.scala 20:22]
    end
    if (isForwardMeta) begin // @[Reg.scala 20:18]
      forwardMetaReg_waymask <= io_metaWriteBus_req_bits_waymask; // @[Reg.scala 20:22]
    end
    if (reset) begin // @[LFSR64.scala 25:23]
      victimWaymask_lfsr <= 64'h1234567887654321; // @[LFSR64.scala 25:23]
    end else if (victimWaymask_lfsr == 64'h0) begin // @[LFSR64.scala 28:18]
      victimWaymask_lfsr <= 64'h1;
    end else begin
      victimWaymask_lfsr <= _victimWaymask_lfsr_T_2;
    end
    if (reset) begin // @[Cache.scala 219:33]
      isForwardDataReg <= 1'h0; // @[Cache.scala 219:33]
    end else if (_T_2) begin // @[Cache.scala 221:37]
      isForwardDataReg <= 1'h0; // @[Cache.scala 221:56]
    end else begin
      isForwardDataReg <= _GEN_8;
    end
    if (isForwardData) begin // @[Reg.scala 20:18]
      forwardDataReg_data_data <= io_dataWriteBus_req_bits_data_data; // @[Reg.scala 20:22]
    end
    if (isForwardData) begin // @[Reg.scala 20:18]
      forwardDataReg_waymask <= io_dataWriteBus_req_bits_waymask; // @[Reg.scala 20:22]
    end
    `ifndef SYNTHESIS
    `ifdef PRINTF_COND
      if (`PRINTF_COND) begin
    `endif
        if (_T_16 & ~(~(io_in_valid & _T_13))) begin
          $fwrite(32'h80000002,
            "Assertion failed\n    at Cache.scala:208 assert(!(io.in.valid && PopCount(waymask) > 1.U))\n"); // @[Cache.scala 208:9]
        end
    `ifdef PRINTF_COND
      end
    `endif
    `endif // SYNTHESIS
    `ifndef SYNTHESIS
    `ifdef STOP_COND
      if (`STOP_COND) begin
    `endif
        if (~(~(io_in_valid & _T_13)) & _T_16) begin
          $fatal; // @[Cache.scala 208:9]
        end
    `ifdef STOP_COND
      end
    `endif
    `endif // SYNTHESIS
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
  isForwardMetaReg = _RAND_0[0:0];
  _RAND_1 = {1{`RANDOM}};
  forwardMetaReg_data_tag = _RAND_1[18:0];
  _RAND_2 = {1{`RANDOM}};
  forwardMetaReg_data_dirty = _RAND_2[0:0];
  _RAND_3 = {1{`RANDOM}};
  forwardMetaReg_waymask = _RAND_3[3:0];
  _RAND_4 = {2{`RANDOM}};
  victimWaymask_lfsr = _RAND_4[63:0];
  _RAND_5 = {1{`RANDOM}};
  isForwardDataReg = _RAND_5[0:0];
  _RAND_6 = {2{`RANDOM}};
  forwardDataReg_data_data = _RAND_6[63:0];
  _RAND_7 = {1{`RANDOM}};
  forwardDataReg_waymask = _RAND_7[3:0];
`endif // RANDOMIZE_REG_INIT
  `endif // RANDOMIZE
end // initial
`ifdef FIRRTL_AFTER_INITIAL
`FIRRTL_AFTER_INITIAL
`endif
`endif // SYNTHESIS
endmodule
