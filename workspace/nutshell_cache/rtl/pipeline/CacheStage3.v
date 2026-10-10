module CacheStage3(
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
  input  [18:0] io_in_bits_metas_0_tag,
  input         io_in_bits_metas_0_dirty,
  input  [18:0] io_in_bits_metas_1_tag,
  input         io_in_bits_metas_1_dirty,
  input  [18:0] io_in_bits_metas_2_tag,
  input         io_in_bits_metas_2_dirty,
  input  [18:0] io_in_bits_metas_3_tag,
  input         io_in_bits_metas_3_dirty,
  input  [63:0] io_in_bits_datas_0_data,
  input  [63:0] io_in_bits_datas_1_data,
  input  [63:0] io_in_bits_datas_2_data,
  input  [63:0] io_in_bits_datas_3_data,
  input         io_in_bits_hit,
  input  [3:0]  io_in_bits_waymask,
  input         io_in_bits_mmio,
  input         io_in_bits_isForwardData,
  input  [63:0] io_in_bits_forwardData_data_data,
  input  [3:0]  io_in_bits_forwardData_waymask,
  input         io_out_ready,
  output        io_out_valid,
  output [3:0]  io_out_bits_cmd,
  output [63:0] io_out_bits_rdata,
  output [15:0] io_out_bits_user,
  output        io_isFinish,
  input         io_flush,
  input         io_dataReadBus_req_ready,
  output        io_dataReadBus_req_valid,
  output [9:0]  io_dataReadBus_req_bits_setIdx,
  input  [63:0] io_dataReadBus_resp_data_0_data,
  input  [63:0] io_dataReadBus_resp_data_1_data,
  input  [63:0] io_dataReadBus_resp_data_2_data,
  input  [63:0] io_dataReadBus_resp_data_3_data,
  output        io_dataWriteBus_req_valid,
  output [9:0]  io_dataWriteBus_req_bits_setIdx,
  output [63:0] io_dataWriteBus_req_bits_data_data,
  output [3:0]  io_dataWriteBus_req_bits_waymask,
  output        io_metaWriteBus_req_valid,
  output [6:0]  io_metaWriteBus_req_bits_setIdx,
  output [18:0] io_metaWriteBus_req_bits_data_tag,
  output        io_metaWriteBus_req_bits_data_dirty,
  output [3:0]  io_metaWriteBus_req_bits_waymask,
  input         io_mem_req_ready,
  output        io_mem_req_valid,
  output [31:0] io_mem_req_bits_addr,
  output [3:0]  io_mem_req_bits_cmd,
  output [63:0] io_mem_req_bits_wdata,
  output        io_mem_resp_ready,
  input         io_mem_resp_valid,
  input  [3:0]  io_mem_resp_bits_cmd,
  input  [63:0] io_mem_resp_bits_rdata,
  input         io_mmio_req_ready,
  output        io_mmio_req_valid,
  output [31:0] io_mmio_req_bits_addr,
  output [2:0]  io_mmio_req_bits_size,
  output [3:0]  io_mmio_req_bits_cmd,
  output [7:0]  io_mmio_req_bits_wmask,
  output [63:0] io_mmio_req_bits_wdata,
  output        io_mmio_resp_ready,
  input         io_mmio_resp_valid,
  input  [63:0] io_mmio_resp_bits_rdata,
  input         io_cohResp_ready,
  output        io_cohResp_valid,
  output [3:0]  io_cohResp_bits_cmd,
  output [63:0] io_cohResp_bits_rdata,
  output        io_dataReadRespToL1
);

  // --------------------------------------------------------------------------
  // Stage 3 semantic map
  // --------------------------------------------------------------------------
  // This file is generated-style Verilog.  The `_T_*` and `_GEN_*` names below
  // are FIRRTL temporaries; the aliases added in this readable view document
  // the transaction-level meaning without changing any logic or timing.
  //
  // Stage 2 has already classified the request. Stage 3 executes that
  // decision: hit response/write, dirty writeback, line refill, MMIO bypass,
  // or coherence line release. All paths share one FSM, counters, array ports
  // and ready/valid response channel, so they remain in this module.

  // [1] Request classification and selected-way metadata/data
`ifdef RANDOMIZE_REG_INIT
  reg [31:0] _RAND_0;
  reg [31:0] _RAND_1;
  reg [31:0] _RAND_2;
  reg [31:0] _RAND_3;
  reg [31:0] _RAND_4;
  reg [31:0] _RAND_5;
  reg [63:0] _RAND_6;
  reg [63:0] _RAND_7;
  reg [63:0] _RAND_8;
  reg [63:0] _RAND_9;
  reg [31:0] _RAND_10;
  reg [31:0] _RAND_11;
  reg [63:0] _RAND_12;
  reg [31:0] _RAND_13;
  reg [31:0] _RAND_14;
`endif // RANDOMIZE_REG_INIT
  wire  metaWriteArb_io_in_0_valid;
  wire [6:0] metaWriteArb_io_in_0_bits_setIdx;
  wire [18:0] metaWriteArb_io_in_0_bits_data_tag;
  wire [3:0] metaWriteArb_io_in_0_bits_waymask;
  wire  metaWriteArb_io_in_1_valid;
  wire [6:0] metaWriteArb_io_in_1_bits_setIdx;
  wire [18:0] metaWriteArb_io_in_1_bits_data_tag;
  wire  metaWriteArb_io_in_1_bits_data_dirty;
  wire [3:0] metaWriteArb_io_in_1_bits_waymask;
  wire  metaWriteArb_io_out_valid;
  wire [6:0] metaWriteArb_io_out_bits_setIdx;
  wire [18:0] metaWriteArb_io_out_bits_data_tag;
  wire  metaWriteArb_io_out_bits_data_dirty;
  wire [3:0] metaWriteArb_io_out_bits_waymask;
  wire  dataWriteArb_io_in_0_valid;
  wire [9:0] dataWriteArb_io_in_0_bits_setIdx;
  wire [63:0] dataWriteArb_io_in_0_bits_data_data;
  wire [3:0] dataWriteArb_io_in_0_bits_waymask;
  wire  dataWriteArb_io_in_1_valid;
  wire [9:0] dataWriteArb_io_in_1_bits_setIdx;
  wire [63:0] dataWriteArb_io_in_1_bits_data_data;
  wire [3:0] dataWriteArb_io_in_1_bits_waymask;
  wire  dataWriteArb_io_out_valid;
  wire [9:0] dataWriteArb_io_out_bits_setIdx;
  wire [63:0] dataWriteArb_io_out_bits_data_data;
  wire [3:0] dataWriteArb_io_out_bits_waymask;
  wire [2:0] addr_wordIndex = io_in_bits_req_addr[5:3];
  wire [6:0] addr_index = io_in_bits_req_addr[12:6];

  // Address fields used by the transaction engine:
  //   [31:13] tag, [12:6] set, [5:3] word-in-line, [2:0] byte offset.
  wire [18:0] request_tag = io_in_bits_req_addr[31:13];
  wire [5:0]  line_offset = io_in_bits_req_addr[5:0];

  wire  mmio = io_in_valid & io_in_bits_mmio;
  wire  hit = io_in_valid & io_in_bits_hit;
  wire  miss = io_in_valid & ~io_in_bits_hit;

  // Request classification from Stage 2.  `hit` and `miss` are mutually
  // exclusive for a valid request; `mmio` bypasses the cache arrays.
  wire  request_is_mmio = mmio;
  wire  request_is_hit = hit;
  wire  request_is_miss = miss;
  wire  _probe_T_1 = io_in_bits_req_cmd == 4'h8;
  wire  probe = io_in_valid & _probe_T_1;
  wire  _hitReadBurst_T = io_in_bits_req_cmd == 4'h2;
  wire  hitReadBurst = hit & _hitReadBurst_T;
  wire  request_is_probe = probe;
  wire  request_is_hit_burst = hitReadBurst;
  wire  meta_dirty = io_in_bits_waymask[0] & io_in_bits_metas_0_dirty | io_in_bits_waymask[1] & io_in_bits_metas_1_dirty
     | io_in_bits_waymask[2] & io_in_bits_metas_2_dirty | io_in_bits_waymask[3] & io_in_bits_metas_3_dirty;
  // Dirty status of the selected victim/refill way.  A dirty miss must
  // complete an 8-beat writeback before the new line can be refilled.
  wire selected_victim_is_dirty = meta_dirty;
  wire [18:0] _meta_T_18 = io_in_bits_waymask[0] ? io_in_bits_metas_0_tag : 19'h0;
  wire [18:0] _meta_T_19 = io_in_bits_waymask[1] ? io_in_bits_metas_1_tag : 19'h0;
  wire [18:0] _meta_T_20 = io_in_bits_waymask[2] ? io_in_bits_metas_2_tag : 19'h0;
  wire [18:0] _meta_T_21 = io_in_bits_waymask[3] ? io_in_bits_metas_3_tag : 19'h0;
  wire [18:0] _meta_T_22 = _meta_T_18 | _meta_T_19;
  wire [18:0] _meta_T_23 = _meta_T_22 | _meta_T_20;
  wire [18:0] meta_tag = _meta_T_23 | _meta_T_21;
  wire  _T_3 = ~reset;
  wire  useForwardData = io_in_bits_isForwardData & io_in_bits_waymask == io_in_bits_forwardData_waymask;
  wire [63:0] _dataReadArray_T_4 = io_in_bits_waymask[0] ? io_in_bits_datas_0_data : 64'h0;
  wire [63:0] _dataReadArray_T_5 = io_in_bits_waymask[1] ? io_in_bits_datas_1_data : 64'h0;
  wire [63:0] _dataReadArray_T_6 = io_in_bits_waymask[2] ? io_in_bits_datas_2_data : 64'h0;
  wire [63:0] _dataReadArray_T_7 = io_in_bits_waymask[3] ? io_in_bits_datas_3_data : 64'h0;
  wire [63:0] _dataReadArray_T_8 = _dataReadArray_T_4 | _dataReadArray_T_5;
  wire [63:0] _dataReadArray_T_9 = _dataReadArray_T_8 | _dataReadArray_T_6;
  wire [63:0] _dataReadArray_T_10 = _dataReadArray_T_9 | _dataReadArray_T_7;
  wire [63:0] dataRead = useForwardData ? io_in_bits_forwardData_data_data : _dataReadArray_T_10;
  // Word presented to the hit path.  Forwarding overrides the SRAM read when
  // Stage 3 is writing the same array entry in the same pipeline window.
  wire [63:0] selected_cache_word = dataRead;
  wire [7:0] _wordMask_T_12 = io_in_bits_req_wmask[0] ? 8'hff : 8'h0;
  wire [7:0] _wordMask_T_14 = io_in_bits_req_wmask[1] ? 8'hff : 8'h0;
  wire [7:0] _wordMask_T_16 = io_in_bits_req_wmask[2] ? 8'hff : 8'h0;
  wire [7:0] _wordMask_T_18 = io_in_bits_req_wmask[3] ? 8'hff : 8'h0;
  wire [7:0] _wordMask_T_20 = io_in_bits_req_wmask[4] ? 8'hff : 8'h0;
  wire [7:0] _wordMask_T_22 = io_in_bits_req_wmask[5] ? 8'hff : 8'h0;
  wire [7:0] _wordMask_T_24 = io_in_bits_req_wmask[6] ? 8'hff : 8'h0;
  wire [7:0] _wordMask_T_26 = io_in_bits_req_wmask[7] ? 8'hff : 8'h0;
  wire [63:0] _wordMask_T_27 = {_wordMask_T_26,_wordMask_T_24,_wordMask_T_22,_wordMask_T_20,_wordMask_T_18,
    _wordMask_T_16,_wordMask_T_14,_wordMask_T_12};
  wire [63:0] wordMask = io_in_bits_req_cmd[0] ? _wordMask_T_27 : 64'h0;
  reg [2:0] writeL2BeatCnt_value;
  // Counts beats consumed by a write-burst request (0..7).
  wire  _T_5 = io_out_ready & io_out_valid;
  wire  _T_6 = io_in_bits_req_cmd == 4'h3;
  wire  _T_7 = io_in_bits_req_cmd == 4'h7;
  wire  _T_8 = io_in_bits_req_cmd == 4'h3 | _T_7;
  wire [2:0] _value_T_1 = writeL2BeatCnt_value + 3'h1;
  wire [2:0] _GEN_0 = _T_5 & (io_in_bits_req_cmd == 4'h3 | _T_7) ? _value_T_1 : writeL2BeatCnt_value;
  wire  hitWrite = hit & io_in_bits_req_cmd[0];

  // [2] Hit read/write path: merge byte masks and update the selected way.
  wire [63:0] _dataHitWriteBus_x1_T = io_in_bits_req_wdata & wordMask;
  wire [63:0] _dataHitWriteBus_x1_T_1 = ~wordMask;
  wire [63:0] _dataHitWriteBus_x1_T_2 = dataRead & _dataHitWriteBus_x1_T_1;
  wire [2:0] _dataHitWriteBus_x3_T_3 = _T_8 ? writeL2BeatCnt_value : addr_wordIndex;
  wire  metaHitWriteBus_x5 = hitWrite & ~meta_dirty;
  reg [3:0] state;
  reg  needFlush;
  // [3] Main transaction FSM. Encodings are inherited from generated RTL:
  // 0 idle, 1 memory-read request, 2 memory-read response,
  // 3 memory-write request, 4 memory-write response,
  // 5 MMIO request, 6 MMIO response, 7 wait for upstream response,
  // 8 coherence/line-release path.
  wire  _GEN_1 = io_flush & state != 4'h0 | needFlush;
  reg [2:0] readBeatCnt_value;
  reg [2:0] writeBeatCnt_value;
  // Refill and writeback progress counters.  Each line has eight 64-bit beats.
  reg [1:0] state2;
  // Auxiliary synchronous Data Array read FSM used by writeback/release:
  // 0 request idle, 1 waiting for SRAM data, 2 data available.
  wire  _T_14 = state == 4'h3;
  wire  _T_15 = state == 4'h8;
  wire [2:0] _T_20 = _T_15 ? readBeatCnt_value : writeBeatCnt_value;
  wire  _dataWay_T = state2 == 2'h1;
  reg [63:0] dataWay_0_data;
  reg [63:0] dataWay_1_data;
  reg [63:0] dataWay_2_data;
  reg [63:0] dataWay_3_data;
  wire [63:0] _dataHitWay_T_4 = io_in_bits_waymask[0] ? dataWay_0_data : 64'h0;
  wire [63:0] _dataHitWay_T_5 = io_in_bits_waymask[1] ? dataWay_1_data : 64'h0;
  wire [63:0] _dataHitWay_T_6 = io_in_bits_waymask[2] ? dataWay_2_data : 64'h0;
  wire [63:0] _dataHitWay_T_7 = io_in_bits_waymask[3] ? dataWay_3_data : 64'h0;
  wire [63:0] _dataHitWay_T_8 = _dataHitWay_T_4 | _dataHitWay_T_5;
  wire [63:0] _dataHitWay_T_9 = _dataHitWay_T_8 | _dataHitWay_T_6;
  wire  _T_23 = io_dataReadBus_req_ready & io_dataReadBus_req_valid;
  wire  _T_26 = io_mem_req_ready & io_mem_req_valid;
  wire  _T_27 = io_cohResp_ready & io_cohResp_valid;
  wire  _T_29 = hitReadBurst & io_out_ready;
  wire [1:0] _GEN_8 = _T_26 | _T_27 | hitReadBurst & io_out_ready ? 2'h0 : state2;
  wire [31:0] raddr = {io_in_bits_req_addr[31:3],3'h0};
  wire [31:0] waddr = {meta_tag,addr_index,6'h0};
  // `raddr` is the critical-word-aligned refill address. `waddr` reconstructs
  // the evicted line address from victim tag + current set + zero line offset.
  wire  _cmd_T = state == 4'h1;

  // [Phase 2 / victim writeback + refill path]
  wire [2:0] _cmd_T_2 = writeBeatCnt_value == 3'h7 ? 3'h7 : 3'h3;
  wire [2:0] cmd = state == 4'h1 ? 3'h2 : _cmd_T_2;
  wire  _io_mem_req_valid_T_2 = state2 == 2'h2;
  reg  afterFirstRead;
  reg  alreadyOutFire;
  wire  _GEN_12 = _T_5 | alreadyOutFire;
  wire  _readingFirst_T_1 = io_mem_resp_ready & io_mem_resp_valid;
  wire  _readingFirst_T_3 = state == 4'h2;
  wire  readingFirst = ~afterFirstRead & _readingFirst_T_1 & state == 4'h2;
  wire  _inRdataRegDemand_T_2 = mmio ? state == 4'h6 : readingFirst;
  reg [63:0] inRdataRegDemand;
  wire  _io_cohResp_valid_T = state == 4'h0;

  // [Phase 2 / coherence release path]
  wire  _io_cohResp_valid_T_4 = _T_15 & _io_mem_req_valid_T_2;
  wire  _releaseLast_T_2 = _T_15 & _T_27;
  reg [2:0] releaseLast_c_value;
  wire  releaseLast_wrap_wrap = releaseLast_c_value == 3'h7;
  wire [2:0] _releaseLast_wrap_value_T_1 = releaseLast_c_value + 3'h1;
  wire  releaseLast = _releaseLast_T_2 & releaseLast_wrap_wrap;
  wire [2:0] _io_cohResp_bits_cmd_T_1 = releaseLast ? 3'h6 : 3'h0;
  wire [3:0] _io_cohResp_bits_cmd_T_2 = hit ? 4'hc : 4'h8;
  wire  respToL1Fire = _T_29 & _io_mem_req_valid_T_2;
  wire  _respToL1Last_T_6 = (_io_cohResp_valid_T | _io_cohResp_valid_T_4) & hitReadBurst & io_out_ready;
  reg [2:0] respToL1Last_c_value;
  wire  respToL1Last_wrap_wrap = respToL1Last_c_value == 3'h7;
  wire [2:0] _respToL1Last_wrap_value_T_1 = respToL1Last_c_value + 3'h1;
  wire  respToL1Last = _respToL1Last_T_6 & respToL1Last_wrap_wrap;
  wire [3:0] _state_T = hit ? 4'h8 : 4'h0;
  wire [2:0] _value_T_4 = addr_wordIndex + 3'h1;
  wire [2:0] _value_T_5 = addr_wordIndex == 3'h7 ? 3'h0 : _value_T_4;
  wire  _T_38 = ~io_flush;
  wire [3:0] _state_T_3 = meta_dirty ? 4'h3 : 4'h1;
  wire [3:0] _state_T_4 = mmio ? 4'h5 : _state_T_3;
  wire [3:0] _GEN_20 = (miss | mmio) & ~io_flush ? _state_T_4 : state;
  wire  _T_41 = io_mmio_req_ready & io_mmio_req_valid;
  wire  _T_43 = io_mmio_resp_ready & io_mmio_resp_valid;
  wire [3:0] _GEN_26 = _T_43 ? 4'h7 : state;
  wire [2:0] _value_T_7 = readBeatCnt_value + 3'h1;
  wire [2:0] _GEN_27 = _T_27 | respToL1Fire ? _value_T_7 : readBeatCnt_value;
  wire [3:0] _GEN_28 = probe & _T_27 & releaseLast | respToL1Fire & respToL1Last ? 4'h0 : state;
  wire [3:0] _GEN_29 = _T_26 ? 4'h2 : state;
  wire [2:0] _GEN_30 = _T_26 ? addr_wordIndex : readBeatCnt_value;
  wire [2:0] _GEN_31 = _T_6 ? 3'h0 : _GEN_0;
  wire  _T_57 = io_mem_resp_bits_cmd == 4'h6;
  wire [3:0] _GEN_32 = _T_57 ? 4'h7 : state;
  wire  _GEN_33 = _readingFirst_T_1 | afterFirstRead;
  wire [2:0] _GEN_34 = _readingFirst_T_1 ? _value_T_7 : readBeatCnt_value;
  wire [2:0] _GEN_35 = _readingFirst_T_1 ? _GEN_31 : _GEN_0;
  wire [3:0] _GEN_36 = _readingFirst_T_1 ? _GEN_32 : state;
  wire [2:0] _value_T_11 = writeBeatCnt_value + 3'h1;
  wire [2:0] _GEN_37 = _T_26 ? _value_T_11 : writeBeatCnt_value;
  wire  _T_60 = io_mem_req_bits_cmd == 4'h7;
  wire [3:0] _GEN_38 = _T_60 & _T_26 ? 4'h4 : state;
  wire [3:0] _GEN_39 = _readingFirst_T_1 ? 4'h1 : state;
  wire [3:0] _GEN_40 = _T_5 | needFlush | alreadyOutFire ? 4'h0 : state;
  wire [3:0] _GEN_41 = 4'h7 == state ? _GEN_40 : state;
  wire [3:0] _GEN_42 = 4'h4 == state ? _GEN_39 : _GEN_41;
  wire [2:0] _GEN_43 = 4'h3 == state ? _GEN_37 : writeBeatCnt_value;
  wire [3:0] _GEN_44 = 4'h3 == state ? _GEN_38 : _GEN_42;
  wire  _GEN_45 = 4'h2 == state ? _GEN_33 : afterFirstRead;
  wire [2:0] _GEN_46 = 4'h2 == state ? _GEN_34 : readBeatCnt_value;
  wire [2:0] _GEN_47 = 4'h2 == state ? _GEN_35 : _GEN_0;
  wire [3:0] _GEN_48 = 4'h2 == state ? _GEN_36 : _GEN_44;
  wire [2:0] _GEN_49 = 4'h2 == state ? writeBeatCnt_value : _GEN_43;
  wire [3:0] _GEN_50 = 4'h1 == state ? _GEN_29 : _GEN_48;
  wire [2:0] _GEN_51 = 4'h1 == state ? _GEN_30 : _GEN_46;
  wire  _GEN_52 = 4'h1 == state ? afterFirstRead : _GEN_45;
  wire [2:0] _GEN_53 = 4'h1 == state ? _GEN_0 : _GEN_47;
  wire [2:0] _GEN_54 = 4'h1 == state ? writeBeatCnt_value : _GEN_49;
  wire [2:0] _GEN_55 = 4'h8 == state ? _GEN_27 : _GEN_51;
  wire [3:0] _GEN_56 = 4'h8 == state ? _GEN_28 : _GEN_50;
  wire  _GEN_57 = 4'h8 == state ? afterFirstRead : _GEN_52;
  wire [2:0] _GEN_58 = 4'h8 == state ? _GEN_0 : _GEN_53;
  wire [2:0] _GEN_59 = 4'h8 == state ? writeBeatCnt_value : _GEN_54;
  wire [63:0] _dataRefill_T = readingFirst ? wordMask : 64'h0;
  wire [63:0] _dataRefill_T_1 = io_in_bits_req_wdata & _dataRefill_T;
  wire [63:0] _dataRefill_T_2 = ~_dataRefill_T;
  wire [63:0] _dataRefill_T_3 = io_mem_resp_bits_rdata & _dataRefill_T_2;
  // Critical-word-first refill merge: on the first beat of a write miss,
  // merge CPU write data under the byte mask; later beats use memory data.
  wire  dataRefillWriteBus_x9 = _readingFirst_T_3 & _readingFirst_T_1;
  wire  metaRefillWriteBus_req_valid = dataRefillWriteBus_x9 & _T_57;
  wire  _io_out_bits_cmd_T_4 = ~io_in_bits_req_cmd[0] & ~io_in_bits_req_cmd[3];
  wire [2:0] _io_out_bits_cmd_T_6 = io_in_bits_req_cmd[0] ? 3'h5 : 3'h0;
  wire [2:0] _io_out_bits_cmd_T_7 = _io_out_bits_cmd_T_4 ? 3'h6 : _io_out_bits_cmd_T_6;
  wire  _io_out_valid_T_4 = state == 4'h7;

  // [Phase 2 / CPU response and ready/valid completion]
  wire  _io_out_valid_T_23 = io_in_bits_req_cmd[0] | mmio ? _io_out_valid_T_4 : afterFirstRead & ~alreadyOutFire;
  wire  _io_out_valid_T_25 = probe ? 1'h0 : hit | _io_out_valid_T_23;
  wire  _io_isFinish_T_4 = miss ? _io_cohResp_valid_T : _T_15 & releaseLast;
  wire  _io_isFinish_T_13 = hit | io_in_bits_req_cmd[0] ? _T_5 : _io_out_valid_T_4 & _GEN_12;
  Arbiter metaWriteArb (
    .io_in_0_valid(metaWriteArb_io_in_0_valid),
    .io_in_0_bits_setIdx(metaWriteArb_io_in_0_bits_setIdx),
    .io_in_0_bits_data_tag(metaWriteArb_io_in_0_bits_data_tag),
    .io_in_0_bits_waymask(metaWriteArb_io_in_0_bits_waymask),
    .io_in_1_valid(metaWriteArb_io_in_1_valid),
    .io_in_1_bits_setIdx(metaWriteArb_io_in_1_bits_setIdx),
    .io_in_1_bits_data_tag(metaWriteArb_io_in_1_bits_data_tag),
    .io_in_1_bits_data_dirty(metaWriteArb_io_in_1_bits_data_dirty),
    .io_in_1_bits_waymask(metaWriteArb_io_in_1_bits_waymask),
    .io_out_valid(metaWriteArb_io_out_valid),
    .io_out_bits_setIdx(metaWriteArb_io_out_bits_setIdx),
    .io_out_bits_data_tag(metaWriteArb_io_out_bits_data_tag),
    .io_out_bits_data_dirty(metaWriteArb_io_out_bits_data_dirty),
    .io_out_bits_waymask(metaWriteArb_io_out_bits_waymask)
  );
  Arbiter_1 dataWriteArb (
    .io_in_0_valid(dataWriteArb_io_in_0_valid),
    .io_in_0_bits_setIdx(dataWriteArb_io_in_0_bits_setIdx),
    .io_in_0_bits_data_data(dataWriteArb_io_in_0_bits_data_data),
    .io_in_0_bits_waymask(dataWriteArb_io_in_0_bits_waymask),
    .io_in_1_valid(dataWriteArb_io_in_1_valid),
    .io_in_1_bits_setIdx(dataWriteArb_io_in_1_bits_setIdx),
    .io_in_1_bits_data_data(dataWriteArb_io_in_1_bits_data_data),
    .io_in_1_bits_waymask(dataWriteArb_io_in_1_bits_waymask),
    .io_out_valid(dataWriteArb_io_out_valid),
    .io_out_bits_setIdx(dataWriteArb_io_out_bits_setIdx),
    .io_out_bits_data_data(dataWriteArb_io_out_bits_data_data),
    .io_out_bits_waymask(dataWriteArb_io_out_bits_waymask)
  );
  assign io_in_ready = io_out_ready & (_io_cohResp_valid_T & ~hitReadBurst) & ~miss & ~probe;
  assign io_out_valid = io_in_valid & _io_out_valid_T_25;
  assign io_out_bits_cmd = {{1'd0}, _io_out_bits_cmd_T_7};
  assign io_out_bits_rdata = hit ? dataRead : inRdataRegDemand;
  assign io_out_bits_user = io_in_bits_req_user;
  assign io_isFinish = probe ? _T_27 & _io_isFinish_T_4 : _io_isFinish_T_13;
  assign io_dataReadBus_req_valid = (state == 4'h3 | state == 4'h8) & state2 == 2'h0;
  assign io_dataReadBus_req_bits_setIdx = {addr_index,_T_20};
  assign io_dataWriteBus_req_valid = dataWriteArb_io_out_valid;
  assign io_dataWriteBus_req_bits_setIdx = dataWriteArb_io_out_bits_setIdx;
  assign io_dataWriteBus_req_bits_data_data = dataWriteArb_io_out_bits_data_data;
  assign io_dataWriteBus_req_bits_waymask = dataWriteArb_io_out_bits_waymask;
  assign io_metaWriteBus_req_valid = metaWriteArb_io_out_valid;
  assign io_metaWriteBus_req_bits_setIdx = metaWriteArb_io_out_bits_setIdx;
  assign io_metaWriteBus_req_bits_data_tag = metaWriteArb_io_out_bits_data_tag;
  assign io_metaWriteBus_req_bits_data_dirty = metaWriteArb_io_out_bits_data_dirty;
  assign io_metaWriteBus_req_bits_waymask = metaWriteArb_io_out_bits_waymask;
  assign io_mem_req_valid = _cmd_T | _T_14 & state2 == 2'h2;
  assign io_mem_req_bits_addr = _cmd_T ? raddr : waddr;
  assign io_mem_req_bits_cmd = {{1'd0}, cmd};
  assign io_mem_req_bits_wdata = _dataHitWay_T_9 | _dataHitWay_T_7;
  assign io_mem_resp_ready = 1'h1;
  assign io_mmio_req_valid = state == 4'h5;
  assign io_mmio_req_bits_addr = io_in_bits_req_addr;
  assign io_mmio_req_bits_size = io_in_bits_req_size;
  assign io_mmio_req_bits_cmd = io_in_bits_req_cmd;
  assign io_mmio_req_bits_wmask = io_in_bits_req_wmask;
  assign io_mmio_req_bits_wdata = io_in_bits_req_wdata;
  assign io_mmio_resp_ready = 1'h1;
  assign io_cohResp_valid = state == 4'h0 & probe | _io_cohResp_valid_T_4;
  assign io_cohResp_bits_cmd = _T_15 ? {{1'd0}, _io_cohResp_bits_cmd_T_1} : _io_cohResp_bits_cmd_T_2;
  assign io_cohResp_bits_rdata = _dataHitWay_T_9 | _dataHitWay_T_7;
  assign io_dataReadRespToL1 = hitReadBurst & (_io_cohResp_valid_T & io_out_ready | _io_cohResp_valid_T_4);
  assign metaWriteArb_io_in_0_valid = hitWrite & ~meta_dirty;
  assign metaWriteArb_io_in_0_bits_setIdx = io_in_bits_req_addr[12:6];
  assign metaWriteArb_io_in_0_bits_data_tag = _meta_T_23 | _meta_T_21;
  assign metaWriteArb_io_in_0_bits_waymask = io_in_bits_waymask;
  assign metaWriteArb_io_in_1_valid = dataRefillWriteBus_x9 & _T_57;
  assign metaWriteArb_io_in_1_bits_setIdx = io_in_bits_req_addr[12:6];
  assign metaWriteArb_io_in_1_bits_data_tag = io_in_bits_req_addr[31:13];
  assign metaWriteArb_io_in_1_bits_data_dirty = io_in_bits_req_cmd[0];
  assign metaWriteArb_io_in_1_bits_waymask = io_in_bits_waymask;
  assign dataWriteArb_io_in_0_valid = hit & io_in_bits_req_cmd[0];
  assign dataWriteArb_io_in_0_bits_setIdx = {addr_index,_dataHitWriteBus_x3_T_3};
  assign dataWriteArb_io_in_0_bits_data_data = _dataHitWriteBus_x1_T | _dataHitWriteBus_x1_T_2;
  assign dataWriteArb_io_in_0_bits_waymask = io_in_bits_waymask;
  assign dataWriteArb_io_in_1_valid = _readingFirst_T_3 & _readingFirst_T_1;
  assign dataWriteArb_io_in_1_bits_setIdx = {addr_index,readBeatCnt_value};
  assign dataWriteArb_io_in_1_bits_data_data = _dataRefill_T_1 | _dataRefill_T_3;
  assign dataWriteArb_io_in_1_bits_waymask = io_in_bits_waymask;
  always @(posedge clock) begin
    if (reset) begin
      writeL2BeatCnt_value <= 3'h0;
    end else if (4'h0 == state) begin
      writeL2BeatCnt_value <= _GEN_0;
    end else if (4'h5 == state) begin
      writeL2BeatCnt_value <= _GEN_0;
    end else if (4'h6 == state) begin
      writeL2BeatCnt_value <= _GEN_0;
    end else begin
      writeL2BeatCnt_value <= _GEN_58;
    end
    if (reset) begin
      state <= 4'h0;
    end else if (4'h0 == state) begin
      if (probe) begin
        if (_T_27) begin
          state <= _state_T;
        end
      end else if (_T_29) begin
        state <= 4'h8;
      end else begin
        state <= _GEN_20;
      end
    end else if (4'h5 == state) begin
      if (_T_41) begin
        state <= 4'h6;
      end
    end else if (4'h6 == state) begin
      state <= _GEN_26;
    end else begin
      state <= _GEN_56;
    end
    if (reset) begin
      needFlush <= 1'h0;
    end else if (_T_5 & needFlush) begin
      needFlush <= 1'h0;
    end else begin
      needFlush <= _GEN_1;
    end
    if (reset) begin
      readBeatCnt_value <= 3'h0;
    end else if (4'h0 == state) begin
      if (probe) begin
        if (_T_27) begin
          readBeatCnt_value <= addr_wordIndex;
        end
      end else if (_T_29) begin
        readBeatCnt_value <= _value_T_5;
      end
    end else if (!(4'h5 == state)) begin
      if (!(4'h6 == state)) begin
        readBeatCnt_value <= _GEN_55;
      end
    end
    if (reset) begin
      writeBeatCnt_value <= 3'h0;
    end else if (!(4'h0 == state)) begin
      if (!(4'h5 == state)) begin
        if (!(4'h6 == state)) begin
          writeBeatCnt_value <= _GEN_59;
        end
      end
    end
    if (reset) begin
      state2 <= 2'h0;
    end else if (2'h0 == state2) begin
      if (_T_23) begin
        state2 <= 2'h1;
      end
    end else if (2'h1 == state2) begin
      state2 <= 2'h2;
    end else if (2'h2 == state2) begin
      state2 <= _GEN_8;
    end
    if (_dataWay_T) begin
      dataWay_0_data <= io_dataReadBus_resp_data_0_data;
    end
    if (_dataWay_T) begin
      dataWay_1_data <= io_dataReadBus_resp_data_1_data;
    end
    if (_dataWay_T) begin
      dataWay_2_data <= io_dataReadBus_resp_data_2_data;
    end
    if (_dataWay_T) begin
      dataWay_3_data <= io_dataReadBus_resp_data_3_data;
    end
    if (reset) begin
      afterFirstRead <= 1'h0;
    end else if (4'h0 == state) begin
      afterFirstRead <= 1'h0;
    end else if (!(4'h5 == state)) begin
      if (!(4'h6 == state)) begin
        afterFirstRead <= _GEN_57;
      end
    end
    if (reset) begin
      alreadyOutFire <= 1'h0;
    end else if (4'h0 == state) begin
      alreadyOutFire <= 1'h0;
    end else begin
      alreadyOutFire <= _GEN_12;
    end
    if (_inRdataRegDemand_T_2) begin
      if (mmio) begin
        inRdataRegDemand <= io_mmio_resp_bits_rdata;
      end else begin
        inRdataRegDemand <= io_mem_resp_bits_rdata;
      end
    end
    if (reset) begin
      releaseLast_c_value <= 3'h0;
    end else if (_releaseLast_T_2) begin
      releaseLast_c_value <= _releaseLast_wrap_value_T_1;
    end
    if (reset) begin
      respToL1Last_c_value <= 3'h0;
    end else if (_respToL1Last_T_6) begin
      respToL1Last_c_value <= _respToL1Last_wrap_value_T_1;
    end
    `ifndef SYNTHESIS
    `ifdef PRINTF_COND
      if (`PRINTF_COND) begin
    `endif
        if (~reset & ~(~(mmio & hit))) begin
          $fwrite(32'h80000002,
            "Assertion failed: MMIO request should not hit in cache\n    at Cache.scala:265 assert(!(mmio && hit), \"MMIO request should not hit in cache\")\n"
            );
        end
    `ifdef PRINTF_COND
      end
    `endif
    `endif // SYNTHESIS
    `ifndef SYNTHESIS
    `ifdef STOP_COND
      if (`STOP_COND) begin
    `endif
        if (~(~(mmio & hit)) & ~reset) begin
          $fatal;
        end
    `ifdef STOP_COND
      end
    `endif
    `endif // SYNTHESIS
    `ifndef SYNTHESIS
    `ifdef PRINTF_COND
      if (`PRINTF_COND) begin
    `endif
        if (_T_3 & ~(~(metaHitWriteBus_x5 & metaRefillWriteBus_req_valid))) begin
          $fwrite(32'h80000002,
            "Assertion failed\n    at Cache.scala:461 assert(!(metaHitWriteBus.req.valid && metaRefillWriteBus.req.valid))\n"
            );
        end
    `ifdef PRINTF_COND
      end
    `endif
    `endif // SYNTHESIS
    `ifndef SYNTHESIS
    `ifdef STOP_COND
      if (`STOP_COND) begin
    `endif
        if (~(~(metaHitWriteBus_x5 & metaRefillWriteBus_req_valid)) & _T_3) begin
          $fatal;
        end
    `ifdef STOP_COND
      end
    `endif
    `endif // SYNTHESIS
    `ifndef SYNTHESIS
    `ifdef PRINTF_COND
      if (`PRINTF_COND) begin
    `endif
        if (_T_3 & ~(~(hitWrite & dataRefillWriteBus_x9))) begin
          $fwrite(32'h80000002,
            "Assertion failed\n    at Cache.scala:462 assert(!(dataHitWriteBus.req.valid && dataRefillWriteBus.req.valid))\n"
            );
        end
    `ifdef PRINTF_COND
      end
    `endif
    `endif // SYNTHESIS
    `ifndef SYNTHESIS
    `ifdef STOP_COND
      if (`STOP_COND) begin
    `endif
        if (~(~(hitWrite & dataRefillWriteBus_x9)) & _T_3) begin
          $fatal;
        end
    `ifdef STOP_COND
      end
    `endif
    `endif // SYNTHESIS
    `ifndef SYNTHESIS
    `ifdef PRINTF_COND
      if (`PRINTF_COND) begin
    `endif
        if (_T_3 & ~_T_38) begin
          $fwrite(32'h80000002,
            "Assertion failed: only allow to flush icache\n    at Cache.scala:463 assert(!(!ro.B && io.flush), \"only allow to flush icache\")\n"
            );
        end
    `ifdef PRINTF_COND
      end
    `endif
    `endif // SYNTHESIS
    `ifndef SYNTHESIS
    `ifdef STOP_COND
      if (`STOP_COND) begin
    `endif
        if (~_T_38 & _T_3) begin
          $fatal;
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
  writeL2BeatCnt_value = _RAND_0[2:0];
  _RAND_1 = {1{`RANDOM}};
  state = _RAND_1[3:0];
  _RAND_2 = {1{`RANDOM}};
  needFlush = _RAND_2[0:0];
  _RAND_3 = {1{`RANDOM}};
  readBeatCnt_value = _RAND_3[2:0];
  _RAND_4 = {1{`RANDOM}};
  writeBeatCnt_value = _RAND_4[2:0];
  _RAND_5 = {1{`RANDOM}};
  state2 = _RAND_5[1:0];
  _RAND_6 = {2{`RANDOM}};
  dataWay_0_data = _RAND_6[63:0];
  _RAND_7 = {2{`RANDOM}};
  dataWay_1_data = _RAND_7[63:0];
  _RAND_8 = {2{`RANDOM}};
  dataWay_2_data = _RAND_8[63:0];
  _RAND_9 = {2{`RANDOM}};
  dataWay_3_data = _RAND_9[63:0];
  _RAND_10 = {1{`RANDOM}};
  afterFirstRead = _RAND_10[0:0];
  _RAND_11 = {1{`RANDOM}};
  alreadyOutFire = _RAND_11[0:0];
  _RAND_12 = {2{`RANDOM}};
  inRdataRegDemand = _RAND_12[63:0];
  _RAND_13 = {1{`RANDOM}};
  releaseLast_c_value = _RAND_13[2:0];
  _RAND_14 = {1{`RANDOM}};
  respToL1Last_c_value = _RAND_14[2:0];
`endif // RANDOMIZE_REG_INIT
  `endif // RANDOMIZE
end // initial
`ifdef FIRRTL_AFTER_INITIAL
`FIRRTL_AFTER_INITIAL
`endif
`endif // SYNTHESIS
`ifdef FORMAL
  // Stage3 response-lifecycle proof under the CPU cache port's single-beat
  // READ/WRITE contract. The parent pipeline presents one stable request until
  // io_isFinish; that is the same hold behavior enforced at CacheTop.
  reg f_lifecycle_past_valid = 1'b0;
  reg f_lifecycle_reset_seen = 1'b0;
  reg f_active_cpu_request = 1'b0;
  reg f_response_seen = 1'b0;
  wire f_legal_cpu_request =
    (io_in_bits_req_cmd == 4'h0) || (io_in_bits_req_cmd == 4'h1);
  wire f_start_cpu_request = io_in_valid && f_legal_cpu_request &&
    (state == 4'h0) && !f_active_cpu_request;
  wire f_cpu_response_fire = io_out_valid && io_out_ready;

  always @(posedge clock) begin
    f_lifecycle_past_valid <= 1'b1;
    if ($initstate)
      assume (reset);

    // CacheTop clears its Stage3-valid register synchronously with reset.
    // Constrain only the first post-reset sample to that parent guarantee.
    if (f_lifecycle_past_valid && $past(reset)) begin
      assume (!io_in_valid);
      assert (!io_out_valid);
      assert (!io_dataReadRespToL1);
    end

    if (reset) begin
      f_lifecycle_reset_seen <= 1'b1;
      f_active_cpu_request <= 1'b0;
      f_response_seen <= 1'b0;
    end else if (f_lifecycle_reset_seen) begin
      if (io_in_valid)
        assume (f_legal_cpu_request);
      // Stage2 marks MMIO as a bypass rather than a cache hit; it cannot
      // present both classifications for the same valid request.
      if (io_in_valid && io_in_bits_mmio)
        assume (!io_in_bits_hit);

      // The Stage3 control inputs must stay associated with one request until
      // finish. The wide data payload is intentionally outside this control
      // proof; its ready/valid stability is covered by the simulation checker.
      if (f_lifecycle_past_valid && !$past(reset) &&
          $past(io_in_valid && !io_isFinish)) begin
        assume (io_in_valid);
        assume ({io_in_bits_req_cmd, io_in_bits_hit, io_in_bits_mmio, meta_dirty} ==
                $past({io_in_bits_req_cmd, io_in_bits_hit,
                       io_in_bits_mmio, meta_dirty}));
      end

      if (f_start_cpu_request) begin
        f_active_cpu_request <= 1'b1;
        f_response_seen <= 1'b0;
      end

      // No CPU response can be emitted without an active (or same-cycle hit)
      // request, and each single-beat request can retire at most once.
      if (io_out_valid)
        assert (f_active_cpu_request || f_start_cpu_request);
      if (f_cpu_response_fire) begin
        assert (f_active_cpu_request || f_start_cpu_request);
        assert (!f_response_seen || f_start_cpu_request);
        f_response_seen <= 1'b1;
      end

      // Finishing a legal CPU operation without a response would lose it.
      if ((f_active_cpu_request || f_start_cpu_request) && io_isFinish) begin
        assert (f_response_seen || f_cpu_response_fire);
        f_active_cpu_request <= 1'b0;
      end

      // A stalled response must keep valid and response command stable; reset
      // is the only permitted cancellation. Simulation checks the full payload.
      if (f_lifecycle_past_valid && !$past(reset) &&
          $past(io_out_valid && !io_out_ready)) begin
        assert (io_out_valid);
        assert (io_out_bits_cmd == $past(io_out_bits_cmd));
      end
    end
  end
`endif
endmodule
