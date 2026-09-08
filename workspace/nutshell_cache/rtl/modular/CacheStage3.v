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
  wire  metaWriteArb_io_in_0_valid; // @[Cache.scala 254:28]
  wire [6:0] metaWriteArb_io_in_0_bits_setIdx; // @[Cache.scala 254:28]
  wire [18:0] metaWriteArb_io_in_0_bits_data_tag; // @[Cache.scala 254:28]
  wire [3:0] metaWriteArb_io_in_0_bits_waymask; // @[Cache.scala 254:28]
  wire  metaWriteArb_io_in_1_valid; // @[Cache.scala 254:28]
  wire [6:0] metaWriteArb_io_in_1_bits_setIdx; // @[Cache.scala 254:28]
  wire [18:0] metaWriteArb_io_in_1_bits_data_tag; // @[Cache.scala 254:28]
  wire  metaWriteArb_io_in_1_bits_data_dirty; // @[Cache.scala 254:28]
  wire [3:0] metaWriteArb_io_in_1_bits_waymask; // @[Cache.scala 254:28]
  wire  metaWriteArb_io_out_valid; // @[Cache.scala 254:28]
  wire [6:0] metaWriteArb_io_out_bits_setIdx; // @[Cache.scala 254:28]
  wire [18:0] metaWriteArb_io_out_bits_data_tag; // @[Cache.scala 254:28]
  wire  metaWriteArb_io_out_bits_data_dirty; // @[Cache.scala 254:28]
  wire [3:0] metaWriteArb_io_out_bits_waymask; // @[Cache.scala 254:28]
  wire  dataWriteArb_io_in_0_valid; // @[Cache.scala 255:28]
  wire [9:0] dataWriteArb_io_in_0_bits_setIdx; // @[Cache.scala 255:28]
  wire [63:0] dataWriteArb_io_in_0_bits_data_data; // @[Cache.scala 255:28]
  wire [3:0] dataWriteArb_io_in_0_bits_waymask; // @[Cache.scala 255:28]
  wire  dataWriteArb_io_in_1_valid; // @[Cache.scala 255:28]
  wire [9:0] dataWriteArb_io_in_1_bits_setIdx; // @[Cache.scala 255:28]
  wire [63:0] dataWriteArb_io_in_1_bits_data_data; // @[Cache.scala 255:28]
  wire [3:0] dataWriteArb_io_in_1_bits_waymask; // @[Cache.scala 255:28]
  wire  dataWriteArb_io_out_valid; // @[Cache.scala 255:28]
  wire [9:0] dataWriteArb_io_out_bits_setIdx; // @[Cache.scala 255:28]
  wire [63:0] dataWriteArb_io_out_bits_data_data; // @[Cache.scala 255:28]
  wire [3:0] dataWriteArb_io_out_bits_waymask; // @[Cache.scala 255:28]
  wire [2:0] addr_wordIndex = io_in_bits_req_addr[5:3]; // @[Cache.scala 258:31]
  wire [6:0] addr_index = io_in_bits_req_addr[12:6]; // @[Cache.scala 258:31]
  wire  mmio = io_in_valid & io_in_bits_mmio; // @[Cache.scala 259:26]
  wire  hit = io_in_valid & io_in_bits_hit; // @[Cache.scala 260:25]
  wire  miss = io_in_valid & ~io_in_bits_hit; // @[Cache.scala 261:26]
  wire  _probe_T_1 = io_in_bits_req_cmd == 4'h8; // @[SimpleBus.scala 79:23]
  wire  probe = io_in_valid & _probe_T_1; // @[Cache.scala 262:39]
  wire  _hitReadBurst_T = io_in_bits_req_cmd == 4'h2; // @[SimpleBus.scala 76:27]
  wire  hitReadBurst = hit & _hitReadBurst_T; // @[Cache.scala 263:26]
  wire  meta_dirty = io_in_bits_waymask[0] & io_in_bits_metas_0_dirty | io_in_bits_waymask[1] & io_in_bits_metas_1_dirty
     | io_in_bits_waymask[2] & io_in_bits_metas_2_dirty | io_in_bits_waymask[3] & io_in_bits_metas_3_dirty; // @[Mux.scala 27:73]
  wire [18:0] _meta_T_18 = io_in_bits_waymask[0] ? io_in_bits_metas_0_tag : 19'h0; // @[Mux.scala 27:73]
  wire [18:0] _meta_T_19 = io_in_bits_waymask[1] ? io_in_bits_metas_1_tag : 19'h0; // @[Mux.scala 27:73]
  wire [18:0] _meta_T_20 = io_in_bits_waymask[2] ? io_in_bits_metas_2_tag : 19'h0; // @[Mux.scala 27:73]
  wire [18:0] _meta_T_21 = io_in_bits_waymask[3] ? io_in_bits_metas_3_tag : 19'h0; // @[Mux.scala 27:73]
  wire [18:0] _meta_T_22 = _meta_T_18 | _meta_T_19; // @[Mux.scala 27:73]
  wire [18:0] _meta_T_23 = _meta_T_22 | _meta_T_20; // @[Mux.scala 27:73]
  wire [18:0] meta_tag = _meta_T_23 | _meta_T_21; // @[Mux.scala 27:73]
  wire  _T_3 = ~reset; // @[Cache.scala 265:9]
  wire  useForwardData = io_in_bits_isForwardData & io_in_bits_waymask == io_in_bits_forwardData_waymask; // @[Cache.scala 273:49]
  wire [63:0] _dataReadArray_T_4 = io_in_bits_waymask[0] ? io_in_bits_datas_0_data : 64'h0; // @[Mux.scala 27:73]
  wire [63:0] _dataReadArray_T_5 = io_in_bits_waymask[1] ? io_in_bits_datas_1_data : 64'h0; // @[Mux.scala 27:73]
  wire [63:0] _dataReadArray_T_6 = io_in_bits_waymask[2] ? io_in_bits_datas_2_data : 64'h0; // @[Mux.scala 27:73]
  wire [63:0] _dataReadArray_T_7 = io_in_bits_waymask[3] ? io_in_bits_datas_3_data : 64'h0; // @[Mux.scala 27:73]
  wire [63:0] _dataReadArray_T_8 = _dataReadArray_T_4 | _dataReadArray_T_5; // @[Mux.scala 27:73]
  wire [63:0] _dataReadArray_T_9 = _dataReadArray_T_8 | _dataReadArray_T_6; // @[Mux.scala 27:73]
  wire [63:0] _dataReadArray_T_10 = _dataReadArray_T_9 | _dataReadArray_T_7; // @[Mux.scala 27:73]
  wire [63:0] dataRead = useForwardData ? io_in_bits_forwardData_data_data : _dataReadArray_T_10; // @[Cache.scala 275:21]
  wire [7:0] _wordMask_T_12 = io_in_bits_req_wmask[0] ? 8'hff : 8'h0; // @[Bitwise.scala 77:12]
  wire [7:0] _wordMask_T_14 = io_in_bits_req_wmask[1] ? 8'hff : 8'h0; // @[Bitwise.scala 77:12]
  wire [7:0] _wordMask_T_16 = io_in_bits_req_wmask[2] ? 8'hff : 8'h0; // @[Bitwise.scala 77:12]
  wire [7:0] _wordMask_T_18 = io_in_bits_req_wmask[3] ? 8'hff : 8'h0; // @[Bitwise.scala 77:12]
  wire [7:0] _wordMask_T_20 = io_in_bits_req_wmask[4] ? 8'hff : 8'h0; // @[Bitwise.scala 77:12]
  wire [7:0] _wordMask_T_22 = io_in_bits_req_wmask[5] ? 8'hff : 8'h0; // @[Bitwise.scala 77:12]
  wire [7:0] _wordMask_T_24 = io_in_bits_req_wmask[6] ? 8'hff : 8'h0; // @[Bitwise.scala 77:12]
  wire [7:0] _wordMask_T_26 = io_in_bits_req_wmask[7] ? 8'hff : 8'h0; // @[Bitwise.scala 77:12]
  wire [63:0] _wordMask_T_27 = {_wordMask_T_26,_wordMask_T_24,_wordMask_T_22,_wordMask_T_20,_wordMask_T_18,
    _wordMask_T_16,_wordMask_T_14,_wordMask_T_12}; // @[Cat.scala 33:92]
  wire [63:0] wordMask = io_in_bits_req_cmd[0] ? _wordMask_T_27 : 64'h0; // @[Cache.scala 276:21]
  reg [2:0] writeL2BeatCnt_value; // @[Counter.scala 61:40]
  wire  _T_5 = io_out_ready & io_out_valid; // @[Decoupled.scala 51:35]
  wire  _T_6 = io_in_bits_req_cmd == 4'h3; // @[Cache.scala 279:32]
  wire  _T_7 = io_in_bits_req_cmd == 4'h7; // @[SimpleBus.scala 78:27]
  wire  _T_8 = io_in_bits_req_cmd == 4'h3 | _T_7; // @[Cache.scala 279:60]
  wire [2:0] _value_T_1 = writeL2BeatCnt_value + 3'h1; // @[Counter.scala 77:24]
  wire [2:0] _GEN_0 = _T_5 & (io_in_bits_req_cmd == 4'h3 | _T_7) ? _value_T_1 : writeL2BeatCnt_value; // @[Cache.scala 279:83 Counter.scala 77:15 61:40]
  wire  hitWrite = hit & io_in_bits_req_cmd[0]; // @[Cache.scala 283:22]
  wire [63:0] _dataHitWriteBus_x1_T = io_in_bits_req_wdata & wordMask; // @[BitUtils.scala 34:14]
  wire [63:0] _dataHitWriteBus_x1_T_1 = ~wordMask; // @[BitUtils.scala 34:39]
  wire [63:0] _dataHitWriteBus_x1_T_2 = dataRead & _dataHitWriteBus_x1_T_1; // @[BitUtils.scala 34:37]
  wire [2:0] _dataHitWriteBus_x3_T_3 = _T_8 ? writeL2BeatCnt_value : addr_wordIndex; // @[Cache.scala 286:51]
  wire  metaHitWriteBus_x5 = hitWrite & ~meta_dirty; // @[Cache.scala 289:22]
  reg [3:0] state; // @[Cache.scala 294:22]
  reg  needFlush; // @[Cache.scala 295:26]
  wire  _GEN_1 = io_flush & state != 4'h0 | needFlush; // @[Cache.scala 295:26 297:{41,53}]
  reg [2:0] readBeatCnt_value; // @[Counter.scala 61:40]
  reg [2:0] writeBeatCnt_value; // @[Counter.scala 61:40]
  reg [1:0] state2; // @[Cache.scala 304:23]
  wire  _T_14 = state == 4'h3; // @[Cache.scala 306:39]
  wire  _T_15 = state == 4'h8; // @[Cache.scala 306:66]
  wire [2:0] _T_20 = _T_15 ? readBeatCnt_value : writeBeatCnt_value; // @[Cache.scala 307:33]
  wire  _dataWay_T = state2 == 2'h1; // @[Cache.scala 308:60]
  reg [63:0] dataWay_0_data; // @[Reg.scala 19:16]
  reg [63:0] dataWay_1_data; // @[Reg.scala 19:16]
  reg [63:0] dataWay_2_data; // @[Reg.scala 19:16]
  reg [63:0] dataWay_3_data; // @[Reg.scala 19:16]
  wire [63:0] _dataHitWay_T_4 = io_in_bits_waymask[0] ? dataWay_0_data : 64'h0; // @[Mux.scala 27:73]
  wire [63:0] _dataHitWay_T_5 = io_in_bits_waymask[1] ? dataWay_1_data : 64'h0; // @[Mux.scala 27:73]
  wire [63:0] _dataHitWay_T_6 = io_in_bits_waymask[2] ? dataWay_2_data : 64'h0; // @[Mux.scala 27:73]
  wire [63:0] _dataHitWay_T_7 = io_in_bits_waymask[3] ? dataWay_3_data : 64'h0; // @[Mux.scala 27:73]
  wire [63:0] _dataHitWay_T_8 = _dataHitWay_T_4 | _dataHitWay_T_5; // @[Mux.scala 27:73]
  wire [63:0] _dataHitWay_T_9 = _dataHitWay_T_8 | _dataHitWay_T_6; // @[Mux.scala 27:73]
  wire  _T_23 = io_dataReadBus_req_ready & io_dataReadBus_req_valid; // @[Decoupled.scala 51:35]
  wire  _T_26 = io_mem_req_ready & io_mem_req_valid; // @[Decoupled.scala 51:35]
  wire  _T_27 = io_cohResp_ready & io_cohResp_valid; // @[Decoupled.scala 51:35]
  wire  _T_29 = hitReadBurst & io_out_ready; // @[Cache.scala 314:79]
  wire [1:0] _GEN_8 = _T_26 | _T_27 | hitReadBurst & io_out_ready ? 2'h0 : state2; // @[Cache.scala 314:105 304:23 314:96]
  wire [31:0] raddr = {io_in_bits_req_addr[31:3],3'h0}; // @[Cat.scala 33:92]
  wire [31:0] waddr = {meta_tag,addr_index,6'h0}; // @[Cat.scala 33:92]
  wire  _cmd_T = state == 4'h1; // @[Cache.scala 322:23]
  wire [2:0] _cmd_T_2 = writeBeatCnt_value == 3'h7 ? 3'h7 : 3'h3; // @[Cache.scala 323:8]
  wire [2:0] cmd = state == 4'h1 ? 3'h2 : _cmd_T_2; // @[Cache.scala 322:16]
  wire  _io_mem_req_valid_T_2 = state2 == 2'h2; // @[Cache.scala 329:89]
  reg  afterFirstRead; // @[Cache.scala 336:31]
  reg  alreadyOutFire; // @[Reg.scala 35:20]
  wire  _GEN_12 = _T_5 | alreadyOutFire; // @[Reg.scala 36:18 35:20 36:22]
  wire  _readingFirst_T_1 = io_mem_resp_ready & io_mem_resp_valid; // @[Decoupled.scala 51:35]
  wire  _readingFirst_T_3 = state == 4'h2; // @[Cache.scala 338:68]
  wire  readingFirst = ~afterFirstRead & _readingFirst_T_1 & state == 4'h2; // @[Cache.scala 338:58]
  wire  _inRdataRegDemand_T_2 = mmio ? state == 4'h6 : readingFirst; // @[Cache.scala 340:39]
  reg [63:0] inRdataRegDemand; // @[Reg.scala 19:16]
  wire  _io_cohResp_valid_T = state == 4'h0; // @[Cache.scala 343:31]
  wire  _io_cohResp_valid_T_4 = _T_15 & _io_mem_req_valid_T_2; // @[Cache.scala 344:46]
  wire  _releaseLast_T_2 = _T_15 & _T_27; // @[Cache.scala 346:49]
  reg [2:0] releaseLast_c_value; // @[Counter.scala 61:40]
  wire  releaseLast_wrap_wrap = releaseLast_c_value == 3'h7; // @[Counter.scala 73:24]
  wire [2:0] _releaseLast_wrap_value_T_1 = releaseLast_c_value + 3'h1; // @[Counter.scala 77:24]
  wire  releaseLast = _releaseLast_T_2 & releaseLast_wrap_wrap; // @[Counter.scala 118:{16,23} 117:24]
  wire [2:0] _io_cohResp_bits_cmd_T_1 = releaseLast ? 3'h6 : 3'h0; // @[Cache.scala 347:54]
  wire [3:0] _io_cohResp_bits_cmd_T_2 = hit ? 4'hc : 4'h8; // @[Cache.scala 348:8]
  wire  respToL1Fire = _T_29 & _io_mem_req_valid_T_2; // @[Cache.scala 350:51]
  wire  _respToL1Last_T_6 = (_io_cohResp_valid_T | _io_cohResp_valid_T_4) & hitReadBurst & io_out_ready; // @[Cache.scala 351:112]
  reg [2:0] respToL1Last_c_value; // @[Counter.scala 61:40]
  wire  respToL1Last_wrap_wrap = respToL1Last_c_value == 3'h7; // @[Counter.scala 73:24]
  wire [2:0] _respToL1Last_wrap_value_T_1 = respToL1Last_c_value + 3'h1; // @[Counter.scala 77:24]
  wire  respToL1Last = _respToL1Last_T_6 & respToL1Last_wrap_wrap; // @[Counter.scala 118:{16,23} 117:24]
  wire [3:0] _state_T = hit ? 4'h8 : 4'h0; // @[Cache.scala 360:23]
  wire [2:0] _value_T_4 = addr_wordIndex + 3'h1; // @[Cache.scala 365:93]
  wire [2:0] _value_T_5 = addr_wordIndex == 3'h7 ? 3'h0 : _value_T_4; // @[Cache.scala 365:33]
  wire  _T_38 = ~io_flush; // @[Cache.scala 366:38]
  wire [3:0] _state_T_3 = meta_dirty ? 4'h3 : 4'h1; // @[Cache.scala 367:42]
  wire [3:0] _state_T_4 = mmio ? 4'h5 : _state_T_3; // @[Cache.scala 367:21]
  wire [3:0] _GEN_20 = (miss | mmio) & ~io_flush ? _state_T_4 : state; // @[Cache.scala 366:49 367:15 294:22]
  wire  _T_41 = io_mmio_req_ready & io_mmio_req_valid; // @[Decoupled.scala 51:35]
  wire  _T_43 = io_mmio_resp_ready & io_mmio_resp_valid; // @[Decoupled.scala 51:35]
  wire [3:0] _GEN_26 = _T_43 ? 4'h7 : state; // @[Cache.scala 294:22 372:{48,56}]
  wire [2:0] _value_T_7 = readBeatCnt_value + 3'h1; // @[Counter.scala 77:24]
  wire [2:0] _GEN_27 = _T_27 | respToL1Fire ? _value_T_7 : readBeatCnt_value; // @[Cache.scala 375:46 Counter.scala 77:15 61:40]
  wire [3:0] _GEN_28 = probe & _T_27 & releaseLast | respToL1Fire & respToL1Last ? 4'h0 : state; // @[Cache.scala 294:22 376:{86,94}]
  wire [3:0] _GEN_29 = _T_26 ? 4'h2 : state; // @[Cache.scala 379:48 380:13 294:22]
  wire [2:0] _GEN_30 = _T_26 ? addr_wordIndex : readBeatCnt_value; // @[Cache.scala 379:48 381:25 Counter.scala 61:40]
  wire [2:0] _GEN_31 = _T_6 ? 3'h0 : _GEN_0; // @[Cache.scala 388:{52,75}]
  wire  _T_57 = io_mem_resp_bits_cmd == 4'h6; // @[SimpleBus.scala 91:24]
  wire [3:0] _GEN_32 = _T_57 ? 4'h7 : state; // @[Cache.scala 294:22 389:{44,52}]
  wire  _GEN_33 = _readingFirst_T_1 | afterFirstRead; // @[Cache.scala 385:31 386:24 336:31]
  wire [2:0] _GEN_34 = _readingFirst_T_1 ? _value_T_7 : readBeatCnt_value; // @[Cache.scala 385:31 Counter.scala 77:15 61:40]
  wire [2:0] _GEN_35 = _readingFirst_T_1 ? _GEN_31 : _GEN_0; // @[Cache.scala 385:31]
  wire [3:0] _GEN_36 = _readingFirst_T_1 ? _GEN_32 : state; // @[Cache.scala 294:22 385:31]
  wire [2:0] _value_T_11 = writeBeatCnt_value + 3'h1; // @[Counter.scala 77:24]
  wire [2:0] _GEN_37 = _T_26 ? _value_T_11 : writeBeatCnt_value; // @[Cache.scala 394:30 Counter.scala 77:15 61:40]
  wire  _T_60 = io_mem_req_bits_cmd == 4'h7; // @[SimpleBus.scala 78:27]
  wire [3:0] _GEN_38 = _T_60 & _T_26 ? 4'h4 : state; // @[Cache.scala 294:22 395:{63,71}]
  wire [3:0] _GEN_39 = _readingFirst_T_1 ? 4'h1 : state; // @[Cache.scala 294:22 398:{51,59}]
  wire [3:0] _GEN_40 = _T_5 | needFlush | alreadyOutFire ? 4'h0 : state; // @[Cache.scala 294:22 399:{74,82}]
  wire [3:0] _GEN_41 = 4'h7 == state ? _GEN_40 : state; // @[Cache.scala 353:18 294:22]
  wire [3:0] _GEN_42 = 4'h4 == state ? _GEN_39 : _GEN_41; // @[Cache.scala 353:18]
  wire [2:0] _GEN_43 = 4'h3 == state ? _GEN_37 : writeBeatCnt_value; // @[Cache.scala 353:18 Counter.scala 61:40]
  wire [3:0] _GEN_44 = 4'h3 == state ? _GEN_38 : _GEN_42; // @[Cache.scala 353:18]
  wire  _GEN_45 = 4'h2 == state ? _GEN_33 : afterFirstRead; // @[Cache.scala 353:18 336:31]
  wire [2:0] _GEN_46 = 4'h2 == state ? _GEN_34 : readBeatCnt_value; // @[Cache.scala 353:18 Counter.scala 61:40]
  wire [2:0] _GEN_47 = 4'h2 == state ? _GEN_35 : _GEN_0; // @[Cache.scala 353:18]
  wire [3:0] _GEN_48 = 4'h2 == state ? _GEN_36 : _GEN_44; // @[Cache.scala 353:18]
  wire [2:0] _GEN_49 = 4'h2 == state ? writeBeatCnt_value : _GEN_43; // @[Cache.scala 353:18 Counter.scala 61:40]
  wire [3:0] _GEN_50 = 4'h1 == state ? _GEN_29 : _GEN_48; // @[Cache.scala 353:18]
  wire [2:0] _GEN_51 = 4'h1 == state ? _GEN_30 : _GEN_46; // @[Cache.scala 353:18]
  wire  _GEN_52 = 4'h1 == state ? afterFirstRead : _GEN_45; // @[Cache.scala 353:18 336:31]
  wire [2:0] _GEN_53 = 4'h1 == state ? _GEN_0 : _GEN_47; // @[Cache.scala 353:18]
  wire [2:0] _GEN_54 = 4'h1 == state ? writeBeatCnt_value : _GEN_49; // @[Cache.scala 353:18 Counter.scala 61:40]
  wire [2:0] _GEN_55 = 4'h8 == state ? _GEN_27 : _GEN_51; // @[Cache.scala 353:18]
  wire [3:0] _GEN_56 = 4'h8 == state ? _GEN_28 : _GEN_50; // @[Cache.scala 353:18]
  wire  _GEN_57 = 4'h8 == state ? afterFirstRead : _GEN_52; // @[Cache.scala 353:18 336:31]
  wire [2:0] _GEN_58 = 4'h8 == state ? _GEN_0 : _GEN_53; // @[Cache.scala 353:18]
  wire [2:0] _GEN_59 = 4'h8 == state ? writeBeatCnt_value : _GEN_54; // @[Cache.scala 353:18 Counter.scala 61:40]
  wire [63:0] _dataRefill_T = readingFirst ? wordMask : 64'h0; // @[Cache.scala 402:67]
  wire [63:0] _dataRefill_T_1 = io_in_bits_req_wdata & _dataRefill_T; // @[BitUtils.scala 34:14]
  wire [63:0] _dataRefill_T_2 = ~_dataRefill_T; // @[BitUtils.scala 34:39]
  wire [63:0] _dataRefill_T_3 = io_mem_resp_bits_rdata & _dataRefill_T_2; // @[BitUtils.scala 34:37]
  wire  dataRefillWriteBus_x9 = _readingFirst_T_3 & _readingFirst_T_1; // @[Cache.scala 404:39]
  wire  metaRefillWriteBus_req_valid = dataRefillWriteBus_x9 & _T_57; // @[Cache.scala 412:59]
  wire  _io_out_bits_cmd_T_4 = ~io_in_bits_req_cmd[0] & ~io_in_bits_req_cmd[3]; // @[SimpleBus.scala 73:26]
  wire [2:0] _io_out_bits_cmd_T_6 = io_in_bits_req_cmd[0] ? 3'h5 : 3'h0; // @[Cache.scala 440:79]
  wire [2:0] _io_out_bits_cmd_T_7 = _io_out_bits_cmd_T_4 ? 3'h6 : _io_out_bits_cmd_T_6; // @[Cache.scala 440:27]
  wire  _io_out_valid_T_4 = state == 4'h7; // @[Cache.scala 446:48]
  wire  _io_out_valid_T_23 = io_in_bits_req_cmd[0] | mmio ? _io_out_valid_T_4 : afterFirstRead & ~alreadyOutFire; // @[Cache.scala 447:45]
  wire  _io_out_valid_T_25 = probe ? 1'h0 : hit | _io_out_valid_T_23; // @[Cache.scala 447:8]
  wire  _io_isFinish_T_4 = miss ? _io_cohResp_valid_T : _T_15 & releaseLast; // @[Cache.scala 454:51]
  wire  _io_isFinish_T_13 = hit | io_in_bits_req_cmd[0] ? _T_5 : _io_out_valid_T_4 & _GEN_12; // @[Cache.scala 455:8]
  Arbiter metaWriteArb ( // @[Cache.scala 254:28]
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
  Arbiter_1 dataWriteArb ( // @[Cache.scala 255:28]
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
  assign io_in_ready = io_out_ready & (_io_cohResp_valid_T & ~hitReadBurst) & ~miss & ~probe; // @[Cache.scala 458:79]
  assign io_out_valid = io_in_valid & _io_out_valid_T_25; // @[Cache.scala 445:31]
  assign io_out_bits_cmd = {{1'd0}, _io_out_bits_cmd_T_7}; // @[Cache.scala 440:21]
  assign io_out_bits_rdata = hit ? dataRead : inRdataRegDemand; // @[Cache.scala 439:29]
  assign io_out_bits_user = io_in_bits_req_user; // @[Cache.scala 442:56]
  assign io_isFinish = probe ? _T_27 & _io_isFinish_T_4 : _io_isFinish_T_13; // @[Cache.scala 454:21]
  assign io_dataReadBus_req_valid = (state == 4'h3 | state == 4'h8) & state2 == 2'h0; // @[Cache.scala 306:81]
  assign io_dataReadBus_req_bits_setIdx = {addr_index,_T_20}; // @[Cat.scala 33:92]
  assign io_dataWriteBus_req_valid = dataWriteArb_io_out_valid; // @[Cache.scala 409:23]
  assign io_dataWriteBus_req_bits_setIdx = dataWriteArb_io_out_bits_setIdx; // @[Cache.scala 409:23]
  assign io_dataWriteBus_req_bits_data_data = dataWriteArb_io_out_bits_data_data; // @[Cache.scala 409:23]
  assign io_dataWriteBus_req_bits_waymask = dataWriteArb_io_out_bits_waymask; // @[Cache.scala 409:23]
  assign io_metaWriteBus_req_valid = metaWriteArb_io_out_valid; // @[Cache.scala 419:23]
  assign io_metaWriteBus_req_bits_setIdx = metaWriteArb_io_out_bits_setIdx; // @[Cache.scala 419:23]
  assign io_metaWriteBus_req_bits_data_tag = metaWriteArb_io_out_bits_data_tag; // @[Cache.scala 419:23]
  assign io_metaWriteBus_req_bits_data_dirty = metaWriteArb_io_out_bits_data_dirty; // @[Cache.scala 419:23]
  assign io_metaWriteBus_req_bits_waymask = metaWriteArb_io_out_bits_waymask; // @[Cache.scala 419:23]
  assign io_mem_req_valid = _cmd_T | _T_14 & state2 == 2'h2; // @[Cache.scala 329:48]
  assign io_mem_req_bits_addr = _cmd_T ? raddr : waddr; // @[Cache.scala 324:35]
  assign io_mem_req_bits_cmd = {{1'd0}, cmd}; // @[SimpleBus.scala 65:14]
  assign io_mem_req_bits_wdata = _dataHitWay_T_9 | _dataHitWay_T_7; // @[Mux.scala 27:73]
  assign io_mem_resp_ready = 1'h1; // @[Cache.scala 328:21]
  assign io_mmio_req_valid = state == 4'h5; // @[Cache.scala 334:31]
  assign io_mmio_req_bits_addr = io_in_bits_req_addr; // @[Cache.scala 332:20]
  assign io_mmio_req_bits_size = io_in_bits_req_size; // @[Cache.scala 332:20]
  assign io_mmio_req_bits_cmd = io_in_bits_req_cmd; // @[Cache.scala 332:20]
  assign io_mmio_req_bits_wmask = io_in_bits_req_wmask; // @[Cache.scala 332:20]
  assign io_mmio_req_bits_wdata = io_in_bits_req_wdata; // @[Cache.scala 332:20]
  assign io_mmio_resp_ready = 1'h1; // @[Cache.scala 333:22]
  assign io_cohResp_valid = state == 4'h0 & probe | _io_cohResp_valid_T_4; // @[Cache.scala 343:53]
  assign io_cohResp_bits_cmd = _T_15 ? {{1'd0}, _io_cohResp_bits_cmd_T_1} : _io_cohResp_bits_cmd_T_2; // @[Cache.scala 347:29]
  assign io_cohResp_bits_rdata = _dataHitWay_T_9 | _dataHitWay_T_7; // @[Mux.scala 27:73]
  assign io_dataReadRespToL1 = hitReadBurst & (_io_cohResp_valid_T & io_out_ready | _io_cohResp_valid_T_4); // @[Cache.scala 459:39]
  assign metaWriteArb_io_in_0_valid = hitWrite & ~meta_dirty; // @[Cache.scala 289:22]
  assign metaWriteArb_io_in_0_bits_setIdx = io_in_bits_req_addr[12:6]; // @[Cache.scala 77:45]
  assign metaWriteArb_io_in_0_bits_data_tag = _meta_T_23 | _meta_T_21; // @[Mux.scala 27:73]
  assign metaWriteArb_io_in_0_bits_waymask = io_in_bits_waymask; // @[Cache.scala 288:29 SRAMTemplate.scala 38:24]
  assign metaWriteArb_io_in_1_valid = dataRefillWriteBus_x9 & _T_57; // @[Cache.scala 412:59]
  assign metaWriteArb_io_in_1_bits_setIdx = io_in_bits_req_addr[12:6]; // @[Cache.scala 77:45]
  assign metaWriteArb_io_in_1_bits_data_tag = io_in_bits_req_addr[31:13]; // @[Cache.scala 258:31]
  assign metaWriteArb_io_in_1_bits_data_dirty = io_in_bits_req_cmd[0]; // @[SimpleBus.scala 74:22]
  assign metaWriteArb_io_in_1_bits_waymask = io_in_bits_waymask; // @[Cache.scala 411:32 SRAMTemplate.scala 38:24]
  assign dataWriteArb_io_in_0_valid = hit & io_in_bits_req_cmd[0]; // @[Cache.scala 283:22]
  assign dataWriteArb_io_in_0_bits_setIdx = {addr_index,_dataHitWriteBus_x3_T_3}; // @[Cat.scala 33:92]
  assign dataWriteArb_io_in_0_bits_data_data = _dataHitWriteBus_x1_T | _dataHitWriteBus_x1_T_2; // @[BitUtils.scala 34:26]
  assign dataWriteArb_io_in_0_bits_waymask = io_in_bits_waymask; // @[Cache.scala 284:29 SRAMTemplate.scala 38:24]
  assign dataWriteArb_io_in_1_valid = _readingFirst_T_3 & _readingFirst_T_1; // @[Cache.scala 404:39]
  assign dataWriteArb_io_in_1_bits_setIdx = {addr_index,readBeatCnt_value}; // @[Cat.scala 33:92]
  assign dataWriteArb_io_in_1_bits_data_data = _dataRefill_T_1 | _dataRefill_T_3; // @[BitUtils.scala 34:26]
  assign dataWriteArb_io_in_1_bits_waymask = io_in_bits_waymask; // @[Cache.scala 403:32 SRAMTemplate.scala 38:24]
  always @(posedge clock) begin
    if (reset) begin // @[Counter.scala 61:40]
      writeL2BeatCnt_value <= 3'h0; // @[Counter.scala 61:40]
    end else if (4'h0 == state) begin // @[Cache.scala 353:18]
      writeL2BeatCnt_value <= _GEN_0;
    end else if (4'h5 == state) begin // @[Cache.scala 353:18]
      writeL2BeatCnt_value <= _GEN_0;
    end else if (4'h6 == state) begin // @[Cache.scala 353:18]
      writeL2BeatCnt_value <= _GEN_0;
    end else begin
      writeL2BeatCnt_value <= _GEN_58;
    end
    if (reset) begin // @[Cache.scala 294:22]
      state <= 4'h0; // @[Cache.scala 294:22]
    end else if (4'h0 == state) begin // @[Cache.scala 353:18]
      if (probe) begin // @[Cache.scala 358:20]
        if (_T_27) begin // @[Cache.scala 359:32]
          state <= _state_T; // @[Cache.scala 360:17]
        end
      end else if (_T_29) begin // @[Cache.scala 363:50]
        state <= 4'h8; // @[Cache.scala 364:15]
      end else begin
        state <= _GEN_20;
      end
    end else if (4'h5 == state) begin // @[Cache.scala 353:18]
      if (_T_41) begin // @[Cache.scala 371:46]
        state <= 4'h6; // @[Cache.scala 371:54]
      end
    end else if (4'h6 == state) begin // @[Cache.scala 353:18]
      state <= _GEN_26;
    end else begin
      state <= _GEN_56;
    end
    if (reset) begin // @[Cache.scala 295:26]
      needFlush <= 1'h0; // @[Cache.scala 295:26]
    end else if (_T_5 & needFlush) begin // @[Cache.scala 298:35]
      needFlush <= 1'h0; // @[Cache.scala 298:47]
    end else begin
      needFlush <= _GEN_1;
    end
    if (reset) begin // @[Counter.scala 61:40]
      readBeatCnt_value <= 3'h0; // @[Counter.scala 61:40]
    end else if (4'h0 == state) begin // @[Cache.scala 353:18]
      if (probe) begin // @[Cache.scala 358:20]
        if (_T_27) begin // @[Cache.scala 359:32]
          readBeatCnt_value <= addr_wordIndex; // @[Cache.scala 361:29]
        end
      end else if (_T_29) begin // @[Cache.scala 363:50]
        readBeatCnt_value <= _value_T_5; // @[Cache.scala 365:27]
      end
    end else if (!(4'h5 == state)) begin // @[Cache.scala 353:18]
      if (!(4'h6 == state)) begin // @[Cache.scala 353:18]
        readBeatCnt_value <= _GEN_55;
      end
    end
    if (reset) begin // @[Counter.scala 61:40]
      writeBeatCnt_value <= 3'h0; // @[Counter.scala 61:40]
    end else if (!(4'h0 == state)) begin // @[Cache.scala 353:18]
      if (!(4'h5 == state)) begin // @[Cache.scala 353:18]
        if (!(4'h6 == state)) begin // @[Cache.scala 353:18]
          writeBeatCnt_value <= _GEN_59;
        end
      end
    end
    if (reset) begin // @[Cache.scala 304:23]
      state2 <= 2'h0; // @[Cache.scala 304:23]
    end else if (2'h0 == state2) begin // @[Cache.scala 311:19]
      if (_T_23) begin // @[Cache.scala 312:51]
        state2 <= 2'h1; // @[Cache.scala 312:60]
      end
    end else if (2'h1 == state2) begin // @[Cache.scala 311:19]
      state2 <= 2'h2; // @[Cache.scala 313:35]
    end else if (2'h2 == state2) begin // @[Cache.scala 311:19]
      state2 <= _GEN_8;
    end
    if (_dataWay_T) begin // @[Reg.scala 20:18]
      dataWay_0_data <= io_dataReadBus_resp_data_0_data; // @[Reg.scala 20:22]
    end
    if (_dataWay_T) begin // @[Reg.scala 20:18]
      dataWay_1_data <= io_dataReadBus_resp_data_1_data; // @[Reg.scala 20:22]
    end
    if (_dataWay_T) begin // @[Reg.scala 20:18]
      dataWay_2_data <= io_dataReadBus_resp_data_2_data; // @[Reg.scala 20:22]
    end
    if (_dataWay_T) begin // @[Reg.scala 20:18]
      dataWay_3_data <= io_dataReadBus_resp_data_3_data; // @[Reg.scala 20:22]
    end
    if (reset) begin // @[Cache.scala 336:31]
      afterFirstRead <= 1'h0; // @[Cache.scala 336:31]
    end else if (4'h0 == state) begin // @[Cache.scala 353:18]
      afterFirstRead <= 1'h0; // @[Cache.scala 355:22]
    end else if (!(4'h5 == state)) begin // @[Cache.scala 353:18]
      if (!(4'h6 == state)) begin // @[Cache.scala 353:18]
        afterFirstRead <= _GEN_57;
      end
    end
    if (reset) begin // @[Reg.scala 35:20]
      alreadyOutFire <= 1'h0; // @[Reg.scala 35:20]
    end else if (4'h0 == state) begin // @[Cache.scala 353:18]
      alreadyOutFire <= 1'h0; // @[Cache.scala 356:22]
    end else begin
      alreadyOutFire <= _GEN_12;
    end
    if (_inRdataRegDemand_T_2) begin // @[Reg.scala 20:18]
      if (mmio) begin // @[Cache.scala 339:39]
        inRdataRegDemand <= io_mmio_resp_bits_rdata;
      end else begin
        inRdataRegDemand <= io_mem_resp_bits_rdata;
      end
    end
    if (reset) begin // @[Counter.scala 61:40]
      releaseLast_c_value <= 3'h0; // @[Counter.scala 61:40]
    end else if (_releaseLast_T_2) begin // @[Counter.scala 118:16]
      releaseLast_c_value <= _releaseLast_wrap_value_T_1; // @[Counter.scala 77:15]
    end
    if (reset) begin // @[Counter.scala 61:40]
      respToL1Last_c_value <= 3'h0; // @[Counter.scala 61:40]
    end else if (_respToL1Last_T_6) begin // @[Counter.scala 118:16]
      respToL1Last_c_value <= _respToL1Last_wrap_value_T_1; // @[Counter.scala 77:15]
    end
    `ifndef SYNTHESIS
    `ifdef PRINTF_COND
      if (`PRINTF_COND) begin
    `endif
        if (~reset & ~(~(mmio & hit))) begin
          $fwrite(32'h80000002,
            "Assertion failed: MMIO request should not hit in cache\n    at Cache.scala:265 assert(!(mmio && hit), \"MMIO request should not hit in cache\")\n"
            ); // @[Cache.scala 265:9]
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
          $fatal; // @[Cache.scala 265:9]
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
            ); // @[Cache.scala 461:9]
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
          $fatal; // @[Cache.scala 461:9]
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
            ); // @[Cache.scala 462:9]
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
          $fatal; // @[Cache.scala 462:9]
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
            ); // @[Cache.scala 463:9]
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
          $fatal; // @[Cache.scala 463:9]
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
endmodule
