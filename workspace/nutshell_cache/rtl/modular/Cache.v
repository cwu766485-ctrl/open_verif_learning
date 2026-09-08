module Cache(
  input         clock,
  input         reset,
  output        io_in_req_ready,
  input         io_in_req_valid,
  input  [31:0] io_in_req_bits_addr,
  input  [2:0]  io_in_req_bits_size,
  input  [3:0]  io_in_req_bits_cmd,
  input  [7:0]  io_in_req_bits_wmask,
  input  [63:0] io_in_req_bits_wdata,
  input  [15:0] io_in_req_bits_user,
  input         io_in_resp_ready,
  output        io_in_resp_valid,
  output [3:0]  io_in_resp_bits_cmd,
  output [63:0] io_in_resp_bits_rdata,
  output [15:0] io_in_resp_bits_user,
  input  [1:0]  io_flush,
  input         io_out_mem_req_ready,
  output        io_out_mem_req_valid,
  output [31:0] io_out_mem_req_bits_addr,
  output [2:0]  io_out_mem_req_bits_size,
  output [3:0]  io_out_mem_req_bits_cmd,
  output [7:0]  io_out_mem_req_bits_wmask,
  output [63:0] io_out_mem_req_bits_wdata,
  output        io_out_mem_resp_ready,
  input         io_out_mem_resp_valid,
  input  [3:0]  io_out_mem_resp_bits_cmd,
  input  [63:0] io_out_mem_resp_bits_rdata,
  output        io_out_coh_req_ready,
  input         io_out_coh_req_valid,
  input  [31:0] io_out_coh_req_bits_addr,
  input  [2:0]  io_out_coh_req_bits_size,
  input  [3:0]  io_out_coh_req_bits_cmd,
  input  [7:0]  io_out_coh_req_bits_wmask,
  input  [63:0] io_out_coh_req_bits_wdata,
  input         io_out_coh_resp_ready,
  output        io_out_coh_resp_valid,
  output [3:0]  io_out_coh_resp_bits_cmd,
  output [63:0] io_out_coh_resp_bits_rdata,
  input         io_mmio_req_ready,
  output        io_mmio_req_valid,
  output [31:0] io_mmio_req_bits_addr,
  output [2:0]  io_mmio_req_bits_size,
  output [3:0]  io_mmio_req_bits_cmd,
  output [7:0]  io_mmio_req_bits_wmask,
  output [63:0] io_mmio_req_bits_wdata,
  output        io_mmio_resp_ready,
  input         io_mmio_resp_valid,
  input  [3:0]  io_mmio_resp_bits_cmd,
  input  [63:0] io_mmio_resp_bits_rdata,
  output        io_empty,
  output        victim_way_mask_valid,
  output [3:0]  victim_way_mask
);
`ifdef RANDOMIZE_REG_INIT
  reg [31:0] _RAND_0;
  reg [31:0] _RAND_1;
  reg [31:0] _RAND_2;
  reg [31:0] _RAND_3;
  reg [31:0] _RAND_4;
  reg [63:0] _RAND_5;
  reg [31:0] _RAND_6;
  reg [31:0] _RAND_7;
  reg [31:0] _RAND_8;
  reg [31:0] _RAND_9;
  reg [31:0] _RAND_10;
  reg [31:0] _RAND_11;
  reg [63:0] _RAND_12;
  reg [31:0] _RAND_13;
  reg [31:0] _RAND_14;
  reg [31:0] _RAND_15;
  reg [31:0] _RAND_16;
  reg [31:0] _RAND_17;
  reg [31:0] _RAND_18;
  reg [31:0] _RAND_19;
  reg [31:0] _RAND_20;
  reg [31:0] _RAND_21;
  reg [63:0] _RAND_22;
  reg [63:0] _RAND_23;
  reg [63:0] _RAND_24;
  reg [63:0] _RAND_25;
  reg [31:0] _RAND_26;
  reg [31:0] _RAND_27;
  reg [31:0] _RAND_28;
  reg [31:0] _RAND_29;
  reg [63:0] _RAND_30;
  reg [31:0] _RAND_31;
`endif // RANDOMIZE_REG_INIT
  wire  s1_io_in_ready; // @[Cache.scala 480:18]
  wire  s1_io_in_valid; // @[Cache.scala 480:18]
  wire [31:0] s1_io_in_bits_addr; // @[Cache.scala 480:18]
  wire [2:0] s1_io_in_bits_size; // @[Cache.scala 480:18]
  wire [3:0] s1_io_in_bits_cmd; // @[Cache.scala 480:18]
  wire [7:0] s1_io_in_bits_wmask; // @[Cache.scala 480:18]
  wire [63:0] s1_io_in_bits_wdata; // @[Cache.scala 480:18]
  wire [15:0] s1_io_in_bits_user; // @[Cache.scala 480:18]
  wire  s1_io_out_ready; // @[Cache.scala 480:18]
  wire  s1_io_out_valid; // @[Cache.scala 480:18]
  wire [31:0] s1_io_out_bits_req_addr; // @[Cache.scala 480:18]
  wire [2:0] s1_io_out_bits_req_size; // @[Cache.scala 480:18]
  wire [3:0] s1_io_out_bits_req_cmd; // @[Cache.scala 480:18]
  wire [7:0] s1_io_out_bits_req_wmask; // @[Cache.scala 480:18]
  wire [63:0] s1_io_out_bits_req_wdata; // @[Cache.scala 480:18]
  wire [15:0] s1_io_out_bits_req_user; // @[Cache.scala 480:18]
  wire  s1_io_metaReadBus_req_ready; // @[Cache.scala 480:18]
  wire  s1_io_metaReadBus_req_valid; // @[Cache.scala 480:18]
  wire [6:0] s1_io_metaReadBus_req_bits_setIdx; // @[Cache.scala 480:18]
  wire [18:0] s1_io_metaReadBus_resp_data_0_tag; // @[Cache.scala 480:18]
  wire  s1_io_metaReadBus_resp_data_0_valid; // @[Cache.scala 480:18]
  wire  s1_io_metaReadBus_resp_data_0_dirty; // @[Cache.scala 480:18]
  wire [18:0] s1_io_metaReadBus_resp_data_1_tag; // @[Cache.scala 480:18]
  wire  s1_io_metaReadBus_resp_data_1_valid; // @[Cache.scala 480:18]
  wire  s1_io_metaReadBus_resp_data_1_dirty; // @[Cache.scala 480:18]
  wire [18:0] s1_io_metaReadBus_resp_data_2_tag; // @[Cache.scala 480:18]
  wire  s1_io_metaReadBus_resp_data_2_valid; // @[Cache.scala 480:18]
  wire  s1_io_metaReadBus_resp_data_2_dirty; // @[Cache.scala 480:18]
  wire [18:0] s1_io_metaReadBus_resp_data_3_tag; // @[Cache.scala 480:18]
  wire  s1_io_metaReadBus_resp_data_3_valid; // @[Cache.scala 480:18]
  wire  s1_io_metaReadBus_resp_data_3_dirty; // @[Cache.scala 480:18]
  wire  s1_io_dataReadBus_req_ready; // @[Cache.scala 480:18]
  wire  s1_io_dataReadBus_req_valid; // @[Cache.scala 480:18]
  wire [9:0] s1_io_dataReadBus_req_bits_setIdx; // @[Cache.scala 480:18]
  wire [63:0] s1_io_dataReadBus_resp_data_0_data; // @[Cache.scala 480:18]
  wire [63:0] s1_io_dataReadBus_resp_data_1_data; // @[Cache.scala 480:18]
  wire [63:0] s1_io_dataReadBus_resp_data_2_data; // @[Cache.scala 480:18]
  wire [63:0] s1_io_dataReadBus_resp_data_3_data; // @[Cache.scala 480:18]
  wire  s2_clock; // @[Cache.scala 481:18]
  wire  s2_reset; // @[Cache.scala 481:18]
  wire  s2_io_in_ready; // @[Cache.scala 481:18]
  wire  s2_io_in_valid; // @[Cache.scala 481:18]
  wire [31:0] s2_io_in_bits_req_addr; // @[Cache.scala 481:18]
  wire [2:0] s2_io_in_bits_req_size; // @[Cache.scala 481:18]
  wire [3:0] s2_io_in_bits_req_cmd; // @[Cache.scala 481:18]
  wire [7:0] s2_io_in_bits_req_wmask; // @[Cache.scala 481:18]
  wire [63:0] s2_io_in_bits_req_wdata; // @[Cache.scala 481:18]
  wire [15:0] s2_io_in_bits_req_user; // @[Cache.scala 481:18]
  wire  s2_io_out_ready; // @[Cache.scala 481:18]
  wire  s2_io_out_valid; // @[Cache.scala 481:18]
  wire [31:0] s2_io_out_bits_req_addr; // @[Cache.scala 481:18]
  wire [2:0] s2_io_out_bits_req_size; // @[Cache.scala 481:18]
  wire [3:0] s2_io_out_bits_req_cmd; // @[Cache.scala 481:18]
  wire [7:0] s2_io_out_bits_req_wmask; // @[Cache.scala 481:18]
  wire [63:0] s2_io_out_bits_req_wdata; // @[Cache.scala 481:18]
  wire [15:0] s2_io_out_bits_req_user; // @[Cache.scala 481:18]
  wire [18:0] s2_io_out_bits_metas_0_tag; // @[Cache.scala 481:18]
  wire  s2_io_out_bits_metas_0_dirty; // @[Cache.scala 481:18]
  wire [18:0] s2_io_out_bits_metas_1_tag; // @[Cache.scala 481:18]
  wire  s2_io_out_bits_metas_1_dirty; // @[Cache.scala 481:18]
  wire [18:0] s2_io_out_bits_metas_2_tag; // @[Cache.scala 481:18]
  wire  s2_io_out_bits_metas_2_dirty; // @[Cache.scala 481:18]
  wire [18:0] s2_io_out_bits_metas_3_tag; // @[Cache.scala 481:18]
  wire  s2_io_out_bits_metas_3_dirty; // @[Cache.scala 481:18]
  wire [63:0] s2_io_out_bits_datas_0_data; // @[Cache.scala 481:18]
  wire [63:0] s2_io_out_bits_datas_1_data; // @[Cache.scala 481:18]
  wire [63:0] s2_io_out_bits_datas_2_data; // @[Cache.scala 481:18]
  wire [63:0] s2_io_out_bits_datas_3_data; // @[Cache.scala 481:18]
  wire  s2_io_out_bits_hit; // @[Cache.scala 481:18]
  wire [3:0] s2_io_out_bits_waymask; // @[Cache.scala 481:18]
  wire  s2_io_out_bits_mmio; // @[Cache.scala 481:18]
  wire  s2_io_out_bits_isForwardData; // @[Cache.scala 481:18]
  wire [63:0] s2_io_out_bits_forwardData_data_data; // @[Cache.scala 481:18]
  wire [3:0] s2_io_out_bits_forwardData_waymask; // @[Cache.scala 481:18]
  wire [18:0] s2_io_metaReadResp_0_tag; // @[Cache.scala 481:18]
  wire  s2_io_metaReadResp_0_valid; // @[Cache.scala 481:18]
  wire  s2_io_metaReadResp_0_dirty; // @[Cache.scala 481:18]
  wire [18:0] s2_io_metaReadResp_1_tag; // @[Cache.scala 481:18]
  wire  s2_io_metaReadResp_1_valid; // @[Cache.scala 481:18]
  wire  s2_io_metaReadResp_1_dirty; // @[Cache.scala 481:18]
  wire [18:0] s2_io_metaReadResp_2_tag; // @[Cache.scala 481:18]
  wire  s2_io_metaReadResp_2_valid; // @[Cache.scala 481:18]
  wire  s2_io_metaReadResp_2_dirty; // @[Cache.scala 481:18]
  wire [18:0] s2_io_metaReadResp_3_tag; // @[Cache.scala 481:18]
  wire  s2_io_metaReadResp_3_valid; // @[Cache.scala 481:18]
  wire  s2_io_metaReadResp_3_dirty; // @[Cache.scala 481:18]
  wire [63:0] s2_io_dataReadResp_0_data; // @[Cache.scala 481:18]
  wire [63:0] s2_io_dataReadResp_1_data; // @[Cache.scala 481:18]
  wire [63:0] s2_io_dataReadResp_2_data; // @[Cache.scala 481:18]
  wire [63:0] s2_io_dataReadResp_3_data; // @[Cache.scala 481:18]
  wire  s2_io_metaWriteBus_req_valid; // @[Cache.scala 481:18]
  wire [6:0] s2_io_metaWriteBus_req_bits_setIdx; // @[Cache.scala 481:18]
  wire [18:0] s2_io_metaWriteBus_req_bits_data_tag; // @[Cache.scala 481:18]
  wire  s2_io_metaWriteBus_req_bits_data_dirty; // @[Cache.scala 481:18]
  wire [3:0] s2_io_metaWriteBus_req_bits_waymask; // @[Cache.scala 481:18]
  wire  s2_io_dataWriteBus_req_valid; // @[Cache.scala 481:18]
  wire [9:0] s2_io_dataWriteBus_req_bits_setIdx; // @[Cache.scala 481:18]
  wire [63:0] s2_io_dataWriteBus_req_bits_data_data; // @[Cache.scala 481:18]
  wire [3:0] s2_io_dataWriteBus_req_bits_waymask; // @[Cache.scala 481:18]
  wire  s3_clock; // @[Cache.scala 482:18]
  wire  s3_reset; // @[Cache.scala 482:18]
  wire  s3_io_in_ready; // @[Cache.scala 482:18]
  wire  s3_io_in_valid; // @[Cache.scala 482:18]
  wire [31:0] s3_io_in_bits_req_addr; // @[Cache.scala 482:18]
  wire [2:0] s3_io_in_bits_req_size; // @[Cache.scala 482:18]
  wire [3:0] s3_io_in_bits_req_cmd; // @[Cache.scala 482:18]
  wire [7:0] s3_io_in_bits_req_wmask; // @[Cache.scala 482:18]
  wire [63:0] s3_io_in_bits_req_wdata; // @[Cache.scala 482:18]
  wire [15:0] s3_io_in_bits_req_user; // @[Cache.scala 482:18]
  wire [18:0] s3_io_in_bits_metas_0_tag; // @[Cache.scala 482:18]
  wire  s3_io_in_bits_metas_0_dirty; // @[Cache.scala 482:18]
  wire [18:0] s3_io_in_bits_metas_1_tag; // @[Cache.scala 482:18]
  wire  s3_io_in_bits_metas_1_dirty; // @[Cache.scala 482:18]
  wire [18:0] s3_io_in_bits_metas_2_tag; // @[Cache.scala 482:18]
  wire  s3_io_in_bits_metas_2_dirty; // @[Cache.scala 482:18]
  wire [18:0] s3_io_in_bits_metas_3_tag; // @[Cache.scala 482:18]
  wire  s3_io_in_bits_metas_3_dirty; // @[Cache.scala 482:18]
  wire [63:0] s3_io_in_bits_datas_0_data; // @[Cache.scala 482:18]
  wire [63:0] s3_io_in_bits_datas_1_data; // @[Cache.scala 482:18]
  wire [63:0] s3_io_in_bits_datas_2_data; // @[Cache.scala 482:18]
  wire [63:0] s3_io_in_bits_datas_3_data; // @[Cache.scala 482:18]
  wire  s3_io_in_bits_hit; // @[Cache.scala 482:18]
  wire [3:0] s3_io_in_bits_waymask; // @[Cache.scala 482:18]
  wire  s3_io_in_bits_mmio; // @[Cache.scala 482:18]
  wire  s3_io_in_bits_isForwardData; // @[Cache.scala 482:18]
  wire [63:0] s3_io_in_bits_forwardData_data_data; // @[Cache.scala 482:18]
  wire [3:0] s3_io_in_bits_forwardData_waymask; // @[Cache.scala 482:18]
  wire  s3_io_out_ready; // @[Cache.scala 482:18]
  wire  s3_io_out_valid; // @[Cache.scala 482:18]
  wire [3:0] s3_io_out_bits_cmd; // @[Cache.scala 482:18]
  wire [63:0] s3_io_out_bits_rdata; // @[Cache.scala 482:18]
  wire [15:0] s3_io_out_bits_user; // @[Cache.scala 482:18]
  wire  s3_io_isFinish; // @[Cache.scala 482:18]
  wire  s3_io_flush; // @[Cache.scala 482:18]
  wire  s3_io_dataReadBus_req_ready; // @[Cache.scala 482:18]
  wire  s3_io_dataReadBus_req_valid; // @[Cache.scala 482:18]
  wire [9:0] s3_io_dataReadBus_req_bits_setIdx; // @[Cache.scala 482:18]
  wire [63:0] s3_io_dataReadBus_resp_data_0_data; // @[Cache.scala 482:18]
  wire [63:0] s3_io_dataReadBus_resp_data_1_data; // @[Cache.scala 482:18]
  wire [63:0] s3_io_dataReadBus_resp_data_2_data; // @[Cache.scala 482:18]
  wire [63:0] s3_io_dataReadBus_resp_data_3_data; // @[Cache.scala 482:18]
  wire  s3_io_dataWriteBus_req_valid; // @[Cache.scala 482:18]
  wire [9:0] s3_io_dataWriteBus_req_bits_setIdx; // @[Cache.scala 482:18]
  wire [63:0] s3_io_dataWriteBus_req_bits_data_data; // @[Cache.scala 482:18]
  wire [3:0] s3_io_dataWriteBus_req_bits_waymask; // @[Cache.scala 482:18]
  wire  s3_io_metaWriteBus_req_valid; // @[Cache.scala 482:18]
  wire [6:0] s3_io_metaWriteBus_req_bits_setIdx; // @[Cache.scala 482:18]
  wire [18:0] s3_io_metaWriteBus_req_bits_data_tag; // @[Cache.scala 482:18]
  wire  s3_io_metaWriteBus_req_bits_data_dirty; // @[Cache.scala 482:18]
  wire [3:0] s3_io_metaWriteBus_req_bits_waymask; // @[Cache.scala 482:18]
  wire  s3_io_mem_req_ready; // @[Cache.scala 482:18]
  wire  s3_io_mem_req_valid; // @[Cache.scala 482:18]
  wire [31:0] s3_io_mem_req_bits_addr; // @[Cache.scala 482:18]
  wire [3:0] s3_io_mem_req_bits_cmd; // @[Cache.scala 482:18]
  wire [63:0] s3_io_mem_req_bits_wdata; // @[Cache.scala 482:18]
  wire  s3_io_mem_resp_ready; // @[Cache.scala 482:18]
  wire  s3_io_mem_resp_valid; // @[Cache.scala 482:18]
  wire [3:0] s3_io_mem_resp_bits_cmd; // @[Cache.scala 482:18]
  wire [63:0] s3_io_mem_resp_bits_rdata; // @[Cache.scala 482:18]
  wire  s3_io_mmio_req_ready; // @[Cache.scala 482:18]
  wire  s3_io_mmio_req_valid; // @[Cache.scala 482:18]
  wire [31:0] s3_io_mmio_req_bits_addr; // @[Cache.scala 482:18]
  wire [2:0] s3_io_mmio_req_bits_size; // @[Cache.scala 482:18]
  wire [3:0] s3_io_mmio_req_bits_cmd; // @[Cache.scala 482:18]
  wire [7:0] s3_io_mmio_req_bits_wmask; // @[Cache.scala 482:18]
  wire [63:0] s3_io_mmio_req_bits_wdata; // @[Cache.scala 482:18]
  wire  s3_io_mmio_resp_ready; // @[Cache.scala 482:18]
  wire  s3_io_mmio_resp_valid; // @[Cache.scala 482:18]
  wire [63:0] s3_io_mmio_resp_bits_rdata; // @[Cache.scala 482:18]
  wire  s3_io_cohResp_ready; // @[Cache.scala 482:18]
  wire  s3_io_cohResp_valid; // @[Cache.scala 482:18]
  wire [3:0] s3_io_cohResp_bits_cmd; // @[Cache.scala 482:18]
  wire [63:0] s3_io_cohResp_bits_rdata; // @[Cache.scala 482:18]
  wire  s3_io_dataReadRespToL1; // @[Cache.scala 482:18]
  wire  metaArray_clock; // @[Cache.scala 483:25]
  wire  metaArray_reset; // @[Cache.scala 483:25]
  wire  metaArray_io_r_0_req_ready; // @[Cache.scala 483:25]
  wire  metaArray_io_r_0_req_valid; // @[Cache.scala 483:25]
  wire [6:0] metaArray_io_r_0_req_bits_setIdx; // @[Cache.scala 483:25]
  wire [18:0] metaArray_io_r_0_resp_data_0_tag; // @[Cache.scala 483:25]
  wire  metaArray_io_r_0_resp_data_0_valid; // @[Cache.scala 483:25]
  wire  metaArray_io_r_0_resp_data_0_dirty; // @[Cache.scala 483:25]
  wire [18:0] metaArray_io_r_0_resp_data_1_tag; // @[Cache.scala 483:25]
  wire  metaArray_io_r_0_resp_data_1_valid; // @[Cache.scala 483:25]
  wire  metaArray_io_r_0_resp_data_1_dirty; // @[Cache.scala 483:25]
  wire [18:0] metaArray_io_r_0_resp_data_2_tag; // @[Cache.scala 483:25]
  wire  metaArray_io_r_0_resp_data_2_valid; // @[Cache.scala 483:25]
  wire  metaArray_io_r_0_resp_data_2_dirty; // @[Cache.scala 483:25]
  wire [18:0] metaArray_io_r_0_resp_data_3_tag; // @[Cache.scala 483:25]
  wire  metaArray_io_r_0_resp_data_3_valid; // @[Cache.scala 483:25]
  wire  metaArray_io_r_0_resp_data_3_dirty; // @[Cache.scala 483:25]
  wire  metaArray_io_w_req_valid; // @[Cache.scala 483:25]
  wire [6:0] metaArray_io_w_req_bits_setIdx; // @[Cache.scala 483:25]
  wire [18:0] metaArray_io_w_req_bits_data_tag; // @[Cache.scala 483:25]
  wire  metaArray_io_w_req_bits_data_dirty; // @[Cache.scala 483:25]
  wire [3:0] metaArray_io_w_req_bits_waymask; // @[Cache.scala 483:25]
  wire  dataArray_clock; // @[Cache.scala 484:25]
  wire  dataArray_reset; // @[Cache.scala 484:25]
  wire  dataArray_io_r_0_req_ready; // @[Cache.scala 484:25]
  wire  dataArray_io_r_0_req_valid; // @[Cache.scala 484:25]
  wire [9:0] dataArray_io_r_0_req_bits_setIdx; // @[Cache.scala 484:25]
  wire [63:0] dataArray_io_r_0_resp_data_0_data; // @[Cache.scala 484:25]
  wire [63:0] dataArray_io_r_0_resp_data_1_data; // @[Cache.scala 484:25]
  wire [63:0] dataArray_io_r_0_resp_data_2_data; // @[Cache.scala 484:25]
  wire [63:0] dataArray_io_r_0_resp_data_3_data; // @[Cache.scala 484:25]
  wire  dataArray_io_r_1_req_ready; // @[Cache.scala 484:25]
  wire  dataArray_io_r_1_req_valid; // @[Cache.scala 484:25]
  wire [9:0] dataArray_io_r_1_req_bits_setIdx; // @[Cache.scala 484:25]
  wire [63:0] dataArray_io_r_1_resp_data_0_data; // @[Cache.scala 484:25]
  wire [63:0] dataArray_io_r_1_resp_data_1_data; // @[Cache.scala 484:25]
  wire [63:0] dataArray_io_r_1_resp_data_2_data; // @[Cache.scala 484:25]
  wire [63:0] dataArray_io_r_1_resp_data_3_data; // @[Cache.scala 484:25]
  wire  dataArray_io_w_req_valid; // @[Cache.scala 484:25]
  wire [9:0] dataArray_io_w_req_bits_setIdx; // @[Cache.scala 484:25]
  wire [63:0] dataArray_io_w_req_bits_data_data; // @[Cache.scala 484:25]
  wire [3:0] dataArray_io_w_req_bits_waymask; // @[Cache.scala 484:25]
  wire  arb_io_in_0_ready; // @[Cache.scala 493:19]
  wire  arb_io_in_0_valid; // @[Cache.scala 493:19]
  wire [31:0] arb_io_in_0_bits_addr; // @[Cache.scala 493:19]
  wire [2:0] arb_io_in_0_bits_size; // @[Cache.scala 493:19]
  wire [3:0] arb_io_in_0_bits_cmd; // @[Cache.scala 493:19]
  wire [7:0] arb_io_in_0_bits_wmask; // @[Cache.scala 493:19]
  wire [63:0] arb_io_in_0_bits_wdata; // @[Cache.scala 493:19]
  wire  arb_io_in_1_ready; // @[Cache.scala 493:19]
  wire  arb_io_in_1_valid; // @[Cache.scala 493:19]
  wire [31:0] arb_io_in_1_bits_addr; // @[Cache.scala 493:19]
  wire [2:0] arb_io_in_1_bits_size; // @[Cache.scala 493:19]
  wire [3:0] arb_io_in_1_bits_cmd; // @[Cache.scala 493:19]
  wire [7:0] arb_io_in_1_bits_wmask; // @[Cache.scala 493:19]
  wire [63:0] arb_io_in_1_bits_wdata; // @[Cache.scala 493:19]
  wire [15:0] arb_io_in_1_bits_user; // @[Cache.scala 493:19]
  wire  arb_io_out_ready; // @[Cache.scala 493:19]
  wire  arb_io_out_valid; // @[Cache.scala 493:19]
  wire [31:0] arb_io_out_bits_addr; // @[Cache.scala 493:19]
  wire [2:0] arb_io_out_bits_size; // @[Cache.scala 493:19]
  wire [3:0] arb_io_out_bits_cmd; // @[Cache.scala 493:19]
  wire [7:0] arb_io_out_bits_wmask; // @[Cache.scala 493:19]
  wire [63:0] arb_io_out_bits_wdata; // @[Cache.scala 493:19]
  wire [15:0] arb_io_out_bits_user; // @[Cache.scala 493:19]
  wire  _T = s2_io_out_ready & s2_io_out_valid; // @[Decoupled.scala 51:35]
  reg  valid; // @[Pipeline.scala 24:24]
  wire  _GEN_0 = _T ? 1'h0 : valid; // @[Pipeline.scala 24:24 25:{25,33}]
  wire  _T_2 = s1_io_out_valid & s2_io_in_ready; // @[Pipeline.scala 26:22]
  wire  _GEN_1 = s1_io_out_valid & s2_io_in_ready | _GEN_0; // @[Pipeline.scala 26:{38,46}]
  reg [31:0] s2_io_in_bits_r_req_addr; // @[Reg.scala 19:16]
  reg [2:0] s2_io_in_bits_r_req_size; // @[Reg.scala 19:16]
  reg [3:0] s2_io_in_bits_r_req_cmd; // @[Reg.scala 19:16]
  reg [7:0] s2_io_in_bits_r_req_wmask; // @[Reg.scala 19:16]
  reg [63:0] s2_io_in_bits_r_req_wdata; // @[Reg.scala 19:16]
  reg [15:0] s2_io_in_bits_r_req_user; // @[Reg.scala 19:16]
  reg  valid_1; // @[Pipeline.scala 24:24]
  wire  _GEN_9 = s3_io_isFinish ? 1'h0 : valid_1; // @[Pipeline.scala 24:24 25:{25,33}]
  wire  _T_4 = s2_io_out_valid & s3_io_in_ready; // @[Pipeline.scala 26:22]
  wire  _GEN_10 = s2_io_out_valid & s3_io_in_ready | _GEN_9; // @[Pipeline.scala 26:{38,46}]
  reg [31:0] s3_io_in_bits_r_req_addr; // @[Reg.scala 19:16]
  reg [2:0] s3_io_in_bits_r_req_size; // @[Reg.scala 19:16]
  reg [3:0] s3_io_in_bits_r_req_cmd; // @[Reg.scala 19:16]
  reg [7:0] s3_io_in_bits_r_req_wmask; // @[Reg.scala 19:16]
  reg [63:0] s3_io_in_bits_r_req_wdata; // @[Reg.scala 19:16]
  reg [15:0] s3_io_in_bits_r_req_user; // @[Reg.scala 19:16]
  reg [18:0] s3_io_in_bits_r_metas_0_tag; // @[Reg.scala 19:16]
  reg  s3_io_in_bits_r_metas_0_dirty; // @[Reg.scala 19:16]
  reg [18:0] s3_io_in_bits_r_metas_1_tag; // @[Reg.scala 19:16]
  reg  s3_io_in_bits_r_metas_1_dirty; // @[Reg.scala 19:16]
  reg [18:0] s3_io_in_bits_r_metas_2_tag; // @[Reg.scala 19:16]
  reg  s3_io_in_bits_r_metas_2_dirty; // @[Reg.scala 19:16]
  reg [18:0] s3_io_in_bits_r_metas_3_tag; // @[Reg.scala 19:16]
  reg  s3_io_in_bits_r_metas_3_dirty; // @[Reg.scala 19:16]
  reg [63:0] s3_io_in_bits_r_datas_0_data; // @[Reg.scala 19:16]
  reg [63:0] s3_io_in_bits_r_datas_1_data; // @[Reg.scala 19:16]
  reg [63:0] s3_io_in_bits_r_datas_2_data; // @[Reg.scala 19:16]
  reg [63:0] s3_io_in_bits_r_datas_3_data; // @[Reg.scala 19:16]
  reg  s3_io_in_bits_r_hit; // @[Reg.scala 19:16]
  reg [3:0] s3_io_in_bits_r_waymask; // @[Reg.scala 19:16]
  reg  s3_io_in_bits_r_mmio; // @[Reg.scala 19:16]
  reg  s3_io_in_bits_r_isForwardData; // @[Reg.scala 19:16]
  reg [63:0] s3_io_in_bits_r_forwardData_data_data; // @[Reg.scala 19:16]
  reg [3:0] s3_io_in_bits_r_forwardData_waymask; // @[Reg.scala 19:16]
  wire  _io_in_resp_valid_T = s3_io_out_bits_cmd == 4'h4; // @[SimpleBus.scala 95:24]
  CacheStage1 s1 ( // @[Cache.scala 480:18]
    .io_in_ready(s1_io_in_ready),
    .io_in_valid(s1_io_in_valid),
    .io_in_bits_addr(s1_io_in_bits_addr),
    .io_in_bits_size(s1_io_in_bits_size),
    .io_in_bits_cmd(s1_io_in_bits_cmd),
    .io_in_bits_wmask(s1_io_in_bits_wmask),
    .io_in_bits_wdata(s1_io_in_bits_wdata),
    .io_in_bits_user(s1_io_in_bits_user),
    .io_out_ready(s1_io_out_ready),
    .io_out_valid(s1_io_out_valid),
    .io_out_bits_req_addr(s1_io_out_bits_req_addr),
    .io_out_bits_req_size(s1_io_out_bits_req_size),
    .io_out_bits_req_cmd(s1_io_out_bits_req_cmd),
    .io_out_bits_req_wmask(s1_io_out_bits_req_wmask),
    .io_out_bits_req_wdata(s1_io_out_bits_req_wdata),
    .io_out_bits_req_user(s1_io_out_bits_req_user),
    .io_metaReadBus_req_ready(s1_io_metaReadBus_req_ready),
    .io_metaReadBus_req_valid(s1_io_metaReadBus_req_valid),
    .io_metaReadBus_req_bits_setIdx(s1_io_metaReadBus_req_bits_setIdx),
    .io_metaReadBus_resp_data_0_tag(s1_io_metaReadBus_resp_data_0_tag),
    .io_metaReadBus_resp_data_0_valid(s1_io_metaReadBus_resp_data_0_valid),
    .io_metaReadBus_resp_data_0_dirty(s1_io_metaReadBus_resp_data_0_dirty),
    .io_metaReadBus_resp_data_1_tag(s1_io_metaReadBus_resp_data_1_tag),
    .io_metaReadBus_resp_data_1_valid(s1_io_metaReadBus_resp_data_1_valid),
    .io_metaReadBus_resp_data_1_dirty(s1_io_metaReadBus_resp_data_1_dirty),
    .io_metaReadBus_resp_data_2_tag(s1_io_metaReadBus_resp_data_2_tag),
    .io_metaReadBus_resp_data_2_valid(s1_io_metaReadBus_resp_data_2_valid),
    .io_metaReadBus_resp_data_2_dirty(s1_io_metaReadBus_resp_data_2_dirty),
    .io_metaReadBus_resp_data_3_tag(s1_io_metaReadBus_resp_data_3_tag),
    .io_metaReadBus_resp_data_3_valid(s1_io_metaReadBus_resp_data_3_valid),
    .io_metaReadBus_resp_data_3_dirty(s1_io_metaReadBus_resp_data_3_dirty),
    .io_dataReadBus_req_ready(s1_io_dataReadBus_req_ready),
    .io_dataReadBus_req_valid(s1_io_dataReadBus_req_valid),
    .io_dataReadBus_req_bits_setIdx(s1_io_dataReadBus_req_bits_setIdx),
    .io_dataReadBus_resp_data_0_data(s1_io_dataReadBus_resp_data_0_data),
    .io_dataReadBus_resp_data_1_data(s1_io_dataReadBus_resp_data_1_data),
    .io_dataReadBus_resp_data_2_data(s1_io_dataReadBus_resp_data_2_data),
    .io_dataReadBus_resp_data_3_data(s1_io_dataReadBus_resp_data_3_data)
  );
  CacheStage2 s2 ( // @[Cache.scala 481:18]
    .clock(s2_clock),
    .reset(s2_reset),
    .io_in_ready(s2_io_in_ready),
    .io_in_valid(s2_io_in_valid),
    .io_in_bits_req_addr(s2_io_in_bits_req_addr),
    .io_in_bits_req_size(s2_io_in_bits_req_size),
    .io_in_bits_req_cmd(s2_io_in_bits_req_cmd),
    .io_in_bits_req_wmask(s2_io_in_bits_req_wmask),
    .io_in_bits_req_wdata(s2_io_in_bits_req_wdata),
    .io_in_bits_req_user(s2_io_in_bits_req_user),
    .io_out_ready(s2_io_out_ready),
    .io_out_valid(s2_io_out_valid),
    .io_out_bits_req_addr(s2_io_out_bits_req_addr),
    .io_out_bits_req_size(s2_io_out_bits_req_size),
    .io_out_bits_req_cmd(s2_io_out_bits_req_cmd),
    .io_out_bits_req_wmask(s2_io_out_bits_req_wmask),
    .io_out_bits_req_wdata(s2_io_out_bits_req_wdata),
    .io_out_bits_req_user(s2_io_out_bits_req_user),
    .io_out_bits_metas_0_tag(s2_io_out_bits_metas_0_tag),
    .io_out_bits_metas_0_dirty(s2_io_out_bits_metas_0_dirty),
    .io_out_bits_metas_1_tag(s2_io_out_bits_metas_1_tag),
    .io_out_bits_metas_1_dirty(s2_io_out_bits_metas_1_dirty),
    .io_out_bits_metas_2_tag(s2_io_out_bits_metas_2_tag),
    .io_out_bits_metas_2_dirty(s2_io_out_bits_metas_2_dirty),
    .io_out_bits_metas_3_tag(s2_io_out_bits_metas_3_tag),
    .io_out_bits_metas_3_dirty(s2_io_out_bits_metas_3_dirty),
    .io_out_bits_datas_0_data(s2_io_out_bits_datas_0_data),
    .io_out_bits_datas_1_data(s2_io_out_bits_datas_1_data),
    .io_out_bits_datas_2_data(s2_io_out_bits_datas_2_data),
    .io_out_bits_datas_3_data(s2_io_out_bits_datas_3_data),
    .io_out_bits_hit(s2_io_out_bits_hit),
    .io_out_bits_waymask(s2_io_out_bits_waymask),
    .io_out_bits_mmio(s2_io_out_bits_mmio),
    .io_out_bits_isForwardData(s2_io_out_bits_isForwardData),
    .io_out_bits_forwardData_data_data(s2_io_out_bits_forwardData_data_data),
    .io_out_bits_forwardData_waymask(s2_io_out_bits_forwardData_waymask),
    .io_metaReadResp_0_tag(s2_io_metaReadResp_0_tag),
    .io_metaReadResp_0_valid(s2_io_metaReadResp_0_valid),
    .io_metaReadResp_0_dirty(s2_io_metaReadResp_0_dirty),
    .io_metaReadResp_1_tag(s2_io_metaReadResp_1_tag),
    .io_metaReadResp_1_valid(s2_io_metaReadResp_1_valid),
    .io_metaReadResp_1_dirty(s2_io_metaReadResp_1_dirty),
    .io_metaReadResp_2_tag(s2_io_metaReadResp_2_tag),
    .io_metaReadResp_2_valid(s2_io_metaReadResp_2_valid),
    .io_metaReadResp_2_dirty(s2_io_metaReadResp_2_dirty),
    .io_metaReadResp_3_tag(s2_io_metaReadResp_3_tag),
    .io_metaReadResp_3_valid(s2_io_metaReadResp_3_valid),
    .io_metaReadResp_3_dirty(s2_io_metaReadResp_3_dirty),
    .io_dataReadResp_0_data(s2_io_dataReadResp_0_data),
    .io_dataReadResp_1_data(s2_io_dataReadResp_1_data),
    .io_dataReadResp_2_data(s2_io_dataReadResp_2_data),
    .io_dataReadResp_3_data(s2_io_dataReadResp_3_data),
    .io_metaWriteBus_req_valid(s2_io_metaWriteBus_req_valid),
    .io_metaWriteBus_req_bits_setIdx(s2_io_metaWriteBus_req_bits_setIdx),
    .io_metaWriteBus_req_bits_data_tag(s2_io_metaWriteBus_req_bits_data_tag),
    .io_metaWriteBus_req_bits_data_dirty(s2_io_metaWriteBus_req_bits_data_dirty),
    .io_metaWriteBus_req_bits_waymask(s2_io_metaWriteBus_req_bits_waymask),
    .io_dataWriteBus_req_valid(s2_io_dataWriteBus_req_valid),
    .io_dataWriteBus_req_bits_setIdx(s2_io_dataWriteBus_req_bits_setIdx),
    .io_dataWriteBus_req_bits_data_data(s2_io_dataWriteBus_req_bits_data_data),
    .io_dataWriteBus_req_bits_waymask(s2_io_dataWriteBus_req_bits_waymask),
    .victim_way_mask(victim_way_mask)
  );
  CacheStage3 s3 ( // @[Cache.scala 482:18]
    .clock(s3_clock),
    .reset(s3_reset),
    .io_in_ready(s3_io_in_ready),
    .io_in_valid(s3_io_in_valid),
    .io_in_bits_req_addr(s3_io_in_bits_req_addr),
    .io_in_bits_req_size(s3_io_in_bits_req_size),
    .io_in_bits_req_cmd(s3_io_in_bits_req_cmd),
    .io_in_bits_req_wmask(s3_io_in_bits_req_wmask),
    .io_in_bits_req_wdata(s3_io_in_bits_req_wdata),
    .io_in_bits_req_user(s3_io_in_bits_req_user),
    .io_in_bits_metas_0_tag(s3_io_in_bits_metas_0_tag),
    .io_in_bits_metas_0_dirty(s3_io_in_bits_metas_0_dirty),
    .io_in_bits_metas_1_tag(s3_io_in_bits_metas_1_tag),
    .io_in_bits_metas_1_dirty(s3_io_in_bits_metas_1_dirty),
    .io_in_bits_metas_2_tag(s3_io_in_bits_metas_2_tag),
    .io_in_bits_metas_2_dirty(s3_io_in_bits_metas_2_dirty),
    .io_in_bits_metas_3_tag(s3_io_in_bits_metas_3_tag),
    .io_in_bits_metas_3_dirty(s3_io_in_bits_metas_3_dirty),
    .io_in_bits_datas_0_data(s3_io_in_bits_datas_0_data),
    .io_in_bits_datas_1_data(s3_io_in_bits_datas_1_data),
    .io_in_bits_datas_2_data(s3_io_in_bits_datas_2_data),
    .io_in_bits_datas_3_data(s3_io_in_bits_datas_3_data),
    .io_in_bits_hit(s3_io_in_bits_hit),
    .io_in_bits_waymask(s3_io_in_bits_waymask),
    .io_in_bits_mmio(s3_io_in_bits_mmio),
    .io_in_bits_isForwardData(s3_io_in_bits_isForwardData),
    .io_in_bits_forwardData_data_data(s3_io_in_bits_forwardData_data_data),
    .io_in_bits_forwardData_waymask(s3_io_in_bits_forwardData_waymask),
    .io_out_ready(s3_io_out_ready),
    .io_out_valid(s3_io_out_valid),
    .io_out_bits_cmd(s3_io_out_bits_cmd),
    .io_out_bits_rdata(s3_io_out_bits_rdata),
    .io_out_bits_user(s3_io_out_bits_user),
    .io_isFinish(s3_io_isFinish),
    .io_flush(s3_io_flush),
    .io_dataReadBus_req_ready(s3_io_dataReadBus_req_ready),
    .io_dataReadBus_req_valid(s3_io_dataReadBus_req_valid),
    .io_dataReadBus_req_bits_setIdx(s3_io_dataReadBus_req_bits_setIdx),
    .io_dataReadBus_resp_data_0_data(s3_io_dataReadBus_resp_data_0_data),
    .io_dataReadBus_resp_data_1_data(s3_io_dataReadBus_resp_data_1_data),
    .io_dataReadBus_resp_data_2_data(s3_io_dataReadBus_resp_data_2_data),
    .io_dataReadBus_resp_data_3_data(s3_io_dataReadBus_resp_data_3_data),
    .io_dataWriteBus_req_valid(s3_io_dataWriteBus_req_valid),
    .io_dataWriteBus_req_bits_setIdx(s3_io_dataWriteBus_req_bits_setIdx),
    .io_dataWriteBus_req_bits_data_data(s3_io_dataWriteBus_req_bits_data_data),
    .io_dataWriteBus_req_bits_waymask(s3_io_dataWriteBus_req_bits_waymask),
    .io_metaWriteBus_req_valid(s3_io_metaWriteBus_req_valid),
    .io_metaWriteBus_req_bits_setIdx(s3_io_metaWriteBus_req_bits_setIdx),
    .io_metaWriteBus_req_bits_data_tag(s3_io_metaWriteBus_req_bits_data_tag),
    .io_metaWriteBus_req_bits_data_dirty(s3_io_metaWriteBus_req_bits_data_dirty),
    .io_metaWriteBus_req_bits_waymask(s3_io_metaWriteBus_req_bits_waymask),
    .io_mem_req_ready(s3_io_mem_req_ready),
    .io_mem_req_valid(s3_io_mem_req_valid),
    .io_mem_req_bits_addr(s3_io_mem_req_bits_addr),
    .io_mem_req_bits_cmd(s3_io_mem_req_bits_cmd),
    .io_mem_req_bits_wdata(s3_io_mem_req_bits_wdata),
    .io_mem_resp_ready(s3_io_mem_resp_ready),
    .io_mem_resp_valid(s3_io_mem_resp_valid),
    .io_mem_resp_bits_cmd(s3_io_mem_resp_bits_cmd),
    .io_mem_resp_bits_rdata(s3_io_mem_resp_bits_rdata),
    .io_mmio_req_ready(s3_io_mmio_req_ready),
    .io_mmio_req_valid(s3_io_mmio_req_valid),
    .io_mmio_req_bits_addr(s3_io_mmio_req_bits_addr),
    .io_mmio_req_bits_size(s3_io_mmio_req_bits_size),
    .io_mmio_req_bits_cmd(s3_io_mmio_req_bits_cmd),
    .io_mmio_req_bits_wmask(s3_io_mmio_req_bits_wmask),
    .io_mmio_req_bits_wdata(s3_io_mmio_req_bits_wdata),
    .io_mmio_resp_ready(s3_io_mmio_resp_ready),
    .io_mmio_resp_valid(s3_io_mmio_resp_valid),
    .io_mmio_resp_bits_rdata(s3_io_mmio_resp_bits_rdata),
    .io_cohResp_ready(s3_io_cohResp_ready),
    .io_cohResp_valid(s3_io_cohResp_valid),
    .io_cohResp_bits_cmd(s3_io_cohResp_bits_cmd),
    .io_cohResp_bits_rdata(s3_io_cohResp_bits_rdata),
    .io_dataReadRespToL1(s3_io_dataReadRespToL1)
  );
  SRAMTemplateWithArbiter metaArray ( // @[Cache.scala 483:25]
    .clock(metaArray_clock),
    .reset(metaArray_reset),
    .io_r_0_req_ready(metaArray_io_r_0_req_ready),
    .io_r_0_req_valid(metaArray_io_r_0_req_valid),
    .io_r_0_req_bits_setIdx(metaArray_io_r_0_req_bits_setIdx),
    .io_r_0_resp_data_0_tag(metaArray_io_r_0_resp_data_0_tag),
    .io_r_0_resp_data_0_valid(metaArray_io_r_0_resp_data_0_valid),
    .io_r_0_resp_data_0_dirty(metaArray_io_r_0_resp_data_0_dirty),
    .io_r_0_resp_data_1_tag(metaArray_io_r_0_resp_data_1_tag),
    .io_r_0_resp_data_1_valid(metaArray_io_r_0_resp_data_1_valid),
    .io_r_0_resp_data_1_dirty(metaArray_io_r_0_resp_data_1_dirty),
    .io_r_0_resp_data_2_tag(metaArray_io_r_0_resp_data_2_tag),
    .io_r_0_resp_data_2_valid(metaArray_io_r_0_resp_data_2_valid),
    .io_r_0_resp_data_2_dirty(metaArray_io_r_0_resp_data_2_dirty),
    .io_r_0_resp_data_3_tag(metaArray_io_r_0_resp_data_3_tag),
    .io_r_0_resp_data_3_valid(metaArray_io_r_0_resp_data_3_valid),
    .io_r_0_resp_data_3_dirty(metaArray_io_r_0_resp_data_3_dirty),
    .io_w_req_valid(metaArray_io_w_req_valid),
    .io_w_req_bits_setIdx(metaArray_io_w_req_bits_setIdx),
    .io_w_req_bits_data_tag(metaArray_io_w_req_bits_data_tag),
    .io_w_req_bits_data_dirty(metaArray_io_w_req_bits_data_dirty),
    .io_w_req_bits_waymask(metaArray_io_w_req_bits_waymask)
  );
  SRAMTemplateWithArbiter_1 dataArray ( // @[Cache.scala 484:25]
    .clock(dataArray_clock),
    .reset(dataArray_reset),
    .io_r_0_req_ready(dataArray_io_r_0_req_ready),
    .io_r_0_req_valid(dataArray_io_r_0_req_valid),
    .io_r_0_req_bits_setIdx(dataArray_io_r_0_req_bits_setIdx),
    .io_r_0_resp_data_0_data(dataArray_io_r_0_resp_data_0_data),
    .io_r_0_resp_data_1_data(dataArray_io_r_0_resp_data_1_data),
    .io_r_0_resp_data_2_data(dataArray_io_r_0_resp_data_2_data),
    .io_r_0_resp_data_3_data(dataArray_io_r_0_resp_data_3_data),
    .io_r_1_req_ready(dataArray_io_r_1_req_ready),
    .io_r_1_req_valid(dataArray_io_r_1_req_valid),
    .io_r_1_req_bits_setIdx(dataArray_io_r_1_req_bits_setIdx),
    .io_r_1_resp_data_0_data(dataArray_io_r_1_resp_data_0_data),
    .io_r_1_resp_data_1_data(dataArray_io_r_1_resp_data_1_data),
    .io_r_1_resp_data_2_data(dataArray_io_r_1_resp_data_2_data),
    .io_r_1_resp_data_3_data(dataArray_io_r_1_resp_data_3_data),
    .io_w_req_valid(dataArray_io_w_req_valid),
    .io_w_req_bits_setIdx(dataArray_io_w_req_bits_setIdx),
    .io_w_req_bits_data_data(dataArray_io_w_req_bits_data_data),
    .io_w_req_bits_waymask(dataArray_io_w_req_bits_waymask)
  );
  Arbiter_4 arb ( // @[Cache.scala 493:19]
    .io_in_0_ready(arb_io_in_0_ready),
    .io_in_0_valid(arb_io_in_0_valid),
    .io_in_0_bits_addr(arb_io_in_0_bits_addr),
    .io_in_0_bits_size(arb_io_in_0_bits_size),
    .io_in_0_bits_cmd(arb_io_in_0_bits_cmd),
    .io_in_0_bits_wmask(arb_io_in_0_bits_wmask),
    .io_in_0_bits_wdata(arb_io_in_0_bits_wdata),
    .io_in_1_ready(arb_io_in_1_ready),
    .io_in_1_valid(arb_io_in_1_valid),
    .io_in_1_bits_addr(arb_io_in_1_bits_addr),
    .io_in_1_bits_size(arb_io_in_1_bits_size),
    .io_in_1_bits_cmd(arb_io_in_1_bits_cmd),
    .io_in_1_bits_wmask(arb_io_in_1_bits_wmask),
    .io_in_1_bits_wdata(arb_io_in_1_bits_wdata),
    .io_in_1_bits_user(arb_io_in_1_bits_user),
    .io_out_ready(arb_io_out_ready),
    .io_out_valid(arb_io_out_valid),
    .io_out_bits_addr(arb_io_out_bits_addr),
    .io_out_bits_size(arb_io_out_bits_size),
    .io_out_bits_cmd(arb_io_out_bits_cmd),
    .io_out_bits_wmask(arb_io_out_bits_wmask),
    .io_out_bits_wdata(arb_io_out_bits_wdata),
    .io_out_bits_user(arb_io_out_bits_user)
  );
  assign io_in_req_ready = arb_io_in_1_ready; // @[Cache.scala 494:28]
  assign io_in_resp_valid = s3_io_out_valid & _io_in_resp_valid_T ? 1'h0 : s3_io_out_valid | s3_io_dataReadRespToL1; // @[Cache.scala 510:26]
  assign io_in_resp_bits_cmd = s3_io_out_bits_cmd; // @[Cache.scala 504:14]
  assign io_in_resp_bits_rdata = s3_io_out_bits_rdata; // @[Cache.scala 504:14]
  assign io_in_resp_bits_user = s3_io_out_bits_user; // @[Cache.scala 504:14]
  assign io_out_mem_req_valid = s3_io_mem_req_valid; // @[Cache.scala 506:14]
  assign io_out_mem_req_bits_addr = s3_io_mem_req_bits_addr; // @[Cache.scala 506:14]
  assign io_out_mem_req_bits_size = 3'h3; // @[Cache.scala 506:14]
  assign io_out_mem_req_bits_cmd = s3_io_mem_req_bits_cmd; // @[Cache.scala 506:14]
  assign io_out_mem_req_bits_wmask = 8'hff; // @[Cache.scala 506:14]
  assign io_out_mem_req_bits_wdata = s3_io_mem_req_bits_wdata; // @[Cache.scala 506:14]
  assign io_out_mem_resp_ready = 1'h1; // @[Cache.scala 506:14]
  assign io_out_coh_req_ready = arb_io_in_0_ready; // @[Cache.scala 519:26]
  assign io_out_coh_resp_valid = s3_io_cohResp_valid; // @[Cache.scala 520:21]
  assign io_out_coh_resp_bits_cmd = s3_io_cohResp_bits_cmd; // @[Cache.scala 520:21]
  assign io_out_coh_resp_bits_rdata = s3_io_cohResp_bits_rdata; // @[Cache.scala 520:21]
  assign io_mmio_req_valid = s3_io_mmio_req_valid; // @[Cache.scala 507:11]
  assign io_mmio_req_bits_addr = s3_io_mmio_req_bits_addr; // @[Cache.scala 507:11]
  assign io_mmio_req_bits_size = s3_io_mmio_req_bits_size; // @[Cache.scala 507:11]
  assign io_mmio_req_bits_cmd = s3_io_mmio_req_bits_cmd; // @[Cache.scala 507:11]
  assign io_mmio_req_bits_wmask = s3_io_mmio_req_bits_wmask; // @[Cache.scala 507:11]
  assign io_mmio_req_bits_wdata = s3_io_mmio_req_bits_wdata; // @[Cache.scala 507:11]
  assign io_mmio_resp_ready = 1'h1; // @[Cache.scala 507:11]
  assign io_empty = ~s2_io_in_valid & ~s3_io_in_valid; // @[Cache.scala 508:31]
  assign s1_io_in_valid = arb_io_out_valid; // @[Cache.scala 496:12]
  assign s1_io_in_bits_addr = arb_io_out_bits_addr; // @[Cache.scala 496:12]
  assign s1_io_in_bits_size = arb_io_out_bits_size; // @[Cache.scala 496:12]
  assign s1_io_in_bits_cmd = arb_io_out_bits_cmd; // @[Cache.scala 496:12]
  assign s1_io_in_bits_wmask = arb_io_out_bits_wmask; // @[Cache.scala 496:12]
  assign s1_io_in_bits_wdata = arb_io_out_bits_wdata; // @[Cache.scala 496:12]
  assign s1_io_in_bits_user = arb_io_out_bits_user; // @[Cache.scala 496:12]
  assign s1_io_out_ready = s2_io_in_ready; // @[Pipeline.scala 29:16]
  assign s1_io_metaReadBus_req_ready = metaArray_io_r_0_req_ready; // @[Cache.scala 528:21]
  assign s1_io_metaReadBus_resp_data_0_tag = metaArray_io_r_0_resp_data_0_tag; // @[Cache.scala 528:21]
  assign s1_io_metaReadBus_resp_data_0_valid = metaArray_io_r_0_resp_data_0_valid; // @[Cache.scala 528:21]
  assign s1_io_metaReadBus_resp_data_0_dirty = metaArray_io_r_0_resp_data_0_dirty; // @[Cache.scala 528:21]
  assign s1_io_metaReadBus_resp_data_1_tag = metaArray_io_r_0_resp_data_1_tag; // @[Cache.scala 528:21]
  assign s1_io_metaReadBus_resp_data_1_valid = metaArray_io_r_0_resp_data_1_valid; // @[Cache.scala 528:21]
  assign s1_io_metaReadBus_resp_data_1_dirty = metaArray_io_r_0_resp_data_1_dirty; // @[Cache.scala 528:21]
  assign s1_io_metaReadBus_resp_data_2_tag = metaArray_io_r_0_resp_data_2_tag; // @[Cache.scala 528:21]
  assign s1_io_metaReadBus_resp_data_2_valid = metaArray_io_r_0_resp_data_2_valid; // @[Cache.scala 528:21]
  assign s1_io_metaReadBus_resp_data_2_dirty = metaArray_io_r_0_resp_data_2_dirty; // @[Cache.scala 528:21]
  assign s1_io_metaReadBus_resp_data_3_tag = metaArray_io_r_0_resp_data_3_tag; // @[Cache.scala 528:21]
  assign s1_io_metaReadBus_resp_data_3_valid = metaArray_io_r_0_resp_data_3_valid; // @[Cache.scala 528:21]
  assign s1_io_metaReadBus_resp_data_3_dirty = metaArray_io_r_0_resp_data_3_dirty; // @[Cache.scala 528:21]
  assign s1_io_dataReadBus_req_ready = dataArray_io_r_0_req_ready; // @[Cache.scala 529:21]
  assign s1_io_dataReadBus_resp_data_0_data = dataArray_io_r_0_resp_data_0_data; // @[Cache.scala 529:21]
  assign s1_io_dataReadBus_resp_data_1_data = dataArray_io_r_0_resp_data_1_data; // @[Cache.scala 529:21]
  assign s1_io_dataReadBus_resp_data_2_data = dataArray_io_r_0_resp_data_2_data; // @[Cache.scala 529:21]
  assign s1_io_dataReadBus_resp_data_3_data = dataArray_io_r_0_resp_data_3_data; // @[Cache.scala 529:21]
  assign s2_clock = clock;
  assign s2_reset = reset;
  assign s2_io_in_valid = valid; // @[Pipeline.scala 31:17]
  assign s2_io_in_bits_req_addr = s2_io_in_bits_r_req_addr; // @[Pipeline.scala 30:16]
  assign s2_io_in_bits_req_size = s2_io_in_bits_r_req_size; // @[Pipeline.scala 30:16]
  assign s2_io_in_bits_req_cmd = s2_io_in_bits_r_req_cmd; // @[Pipeline.scala 30:16]
  assign s2_io_in_bits_req_wmask = s2_io_in_bits_r_req_wmask; // @[Pipeline.scala 30:16]
  assign s2_io_in_bits_req_wdata = s2_io_in_bits_r_req_wdata; // @[Pipeline.scala 30:16]
  assign s2_io_in_bits_req_user = s2_io_in_bits_r_req_user; // @[Pipeline.scala 30:16]
  assign s2_io_out_ready = s3_io_in_ready; // @[Pipeline.scala 29:16]
  assign s2_io_metaReadResp_0_tag = s1_io_metaReadBus_resp_data_0_tag; // @[Cache.scala 535:22]
  assign s2_io_metaReadResp_0_valid = s1_io_metaReadBus_resp_data_0_valid; // @[Cache.scala 535:22]
  assign s2_io_metaReadResp_0_dirty = s1_io_metaReadBus_resp_data_0_dirty; // @[Cache.scala 535:22]
  assign s2_io_metaReadResp_1_tag = s1_io_metaReadBus_resp_data_1_tag; // @[Cache.scala 535:22]
  assign s2_io_metaReadResp_1_valid = s1_io_metaReadBus_resp_data_1_valid; // @[Cache.scala 535:22]
  assign s2_io_metaReadResp_1_dirty = s1_io_metaReadBus_resp_data_1_dirty; // @[Cache.scala 535:22]
  assign s2_io_metaReadResp_2_tag = s1_io_metaReadBus_resp_data_2_tag; // @[Cache.scala 535:22]
  assign s2_io_metaReadResp_2_valid = s1_io_metaReadBus_resp_data_2_valid; // @[Cache.scala 535:22]
  assign s2_io_metaReadResp_2_dirty = s1_io_metaReadBus_resp_data_2_dirty; // @[Cache.scala 535:22]
  assign s2_io_metaReadResp_3_tag = s1_io_metaReadBus_resp_data_3_tag; // @[Cache.scala 535:22]
  assign s2_io_metaReadResp_3_valid = s1_io_metaReadBus_resp_data_3_valid; // @[Cache.scala 535:22]
  assign s2_io_metaReadResp_3_dirty = s1_io_metaReadBus_resp_data_3_dirty; // @[Cache.scala 535:22]
  assign s2_io_dataReadResp_0_data = s1_io_dataReadBus_resp_data_0_data; // @[Cache.scala 536:22]
  assign s2_io_dataReadResp_1_data = s1_io_dataReadBus_resp_data_1_data; // @[Cache.scala 536:22]
  assign s2_io_dataReadResp_2_data = s1_io_dataReadBus_resp_data_2_data; // @[Cache.scala 536:22]
  assign s2_io_dataReadResp_3_data = s1_io_dataReadBus_resp_data_3_data; // @[Cache.scala 536:22]
  assign s2_io_metaWriteBus_req_valid = s3_io_metaWriteBus_req_valid; // @[Cache.scala 538:22]
  assign s2_io_metaWriteBus_req_bits_setIdx = s3_io_metaWriteBus_req_bits_setIdx; // @[Cache.scala 538:22]
  assign s2_io_metaWriteBus_req_bits_data_tag = s3_io_metaWriteBus_req_bits_data_tag; // @[Cache.scala 538:22]
  assign s2_io_metaWriteBus_req_bits_data_dirty = s3_io_metaWriteBus_req_bits_data_dirty; // @[Cache.scala 538:22]
  assign s2_io_metaWriteBus_req_bits_waymask = s3_io_metaWriteBus_req_bits_waymask; // @[Cache.scala 538:22]
  assign s2_io_dataWriteBus_req_valid = s3_io_dataWriteBus_req_valid; // @[Cache.scala 537:22]
  assign s2_io_dataWriteBus_req_bits_setIdx = s3_io_dataWriteBus_req_bits_setIdx; // @[Cache.scala 537:22]
  assign s2_io_dataWriteBus_req_bits_data_data = s3_io_dataWriteBus_req_bits_data_data; // @[Cache.scala 537:22]
  assign s2_io_dataWriteBus_req_bits_waymask = s3_io_dataWriteBus_req_bits_waymask; // @[Cache.scala 537:22]
  assign s3_clock = clock;
  assign s3_reset = reset;
  assign s3_io_in_valid = valid_1; // @[Pipeline.scala 31:17]
  assign s3_io_in_bits_req_addr = s3_io_in_bits_r_req_addr; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_req_size = s3_io_in_bits_r_req_size; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_req_cmd = s3_io_in_bits_r_req_cmd; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_req_wmask = s3_io_in_bits_r_req_wmask; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_req_wdata = s3_io_in_bits_r_req_wdata; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_req_user = s3_io_in_bits_r_req_user; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_metas_0_tag = s3_io_in_bits_r_metas_0_tag; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_metas_0_dirty = s3_io_in_bits_r_metas_0_dirty; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_metas_1_tag = s3_io_in_bits_r_metas_1_tag; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_metas_1_dirty = s3_io_in_bits_r_metas_1_dirty; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_metas_2_tag = s3_io_in_bits_r_metas_2_tag; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_metas_2_dirty = s3_io_in_bits_r_metas_2_dirty; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_metas_3_tag = s3_io_in_bits_r_metas_3_tag; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_metas_3_dirty = s3_io_in_bits_r_metas_3_dirty; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_datas_0_data = s3_io_in_bits_r_datas_0_data; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_datas_1_data = s3_io_in_bits_r_datas_1_data; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_datas_2_data = s3_io_in_bits_r_datas_2_data; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_datas_3_data = s3_io_in_bits_r_datas_3_data; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_hit = s3_io_in_bits_r_hit; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_waymask = s3_io_in_bits_r_waymask; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_mmio = s3_io_in_bits_r_mmio; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_isForwardData = s3_io_in_bits_r_isForwardData; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_forwardData_data_data = s3_io_in_bits_r_forwardData_data_data; // @[Pipeline.scala 30:16]
  assign s3_io_in_bits_forwardData_waymask = s3_io_in_bits_r_forwardData_waymask; // @[Pipeline.scala 30:16]
  assign s3_io_out_ready = io_in_resp_ready; // @[Cache.scala 504:14]
  assign s3_io_flush = io_flush[1]; // @[Cache.scala 505:26]
  assign s3_io_dataReadBus_req_ready = dataArray_io_r_1_req_ready; // @[Cache.scala 530:21]
  assign s3_io_dataReadBus_resp_data_0_data = dataArray_io_r_1_resp_data_0_data; // @[Cache.scala 530:21]
  assign s3_io_dataReadBus_resp_data_1_data = dataArray_io_r_1_resp_data_1_data; // @[Cache.scala 530:21]
  assign s3_io_dataReadBus_resp_data_2_data = dataArray_io_r_1_resp_data_2_data; // @[Cache.scala 530:21]
  assign s3_io_dataReadBus_resp_data_3_data = dataArray_io_r_1_resp_data_3_data; // @[Cache.scala 530:21]
  assign s3_io_mem_req_ready = io_out_mem_req_ready; // @[Cache.scala 506:14]
  assign s3_io_mem_resp_valid = io_out_mem_resp_valid; // @[Cache.scala 506:14]
  assign s3_io_mem_resp_bits_cmd = io_out_mem_resp_bits_cmd; // @[Cache.scala 506:14]
  assign s3_io_mem_resp_bits_rdata = io_out_mem_resp_bits_rdata; // @[Cache.scala 506:14]
  assign s3_io_mmio_req_ready = io_mmio_req_ready; // @[Cache.scala 507:11]
  assign s3_io_mmio_resp_valid = io_mmio_resp_valid; // @[Cache.scala 507:11]
  assign s3_io_mmio_resp_bits_rdata = io_mmio_resp_bits_rdata; // @[Cache.scala 507:11]
  assign s3_io_cohResp_ready = io_out_coh_resp_ready; // @[Cache.scala 520:21]
  assign metaArray_clock = clock;
  assign metaArray_reset = reset; // @[Cache.scala 490:37]
  assign metaArray_io_r_0_req_valid = s1_io_metaReadBus_req_valid; // @[Cache.scala 528:21]
  assign metaArray_io_r_0_req_bits_setIdx = s1_io_metaReadBus_req_bits_setIdx; // @[Cache.scala 528:21]
  assign metaArray_io_w_req_valid = s3_io_metaWriteBus_req_valid; // @[Cache.scala 532:18]
  assign metaArray_io_w_req_bits_setIdx = s3_io_metaWriteBus_req_bits_setIdx; // @[Cache.scala 532:18]
  assign metaArray_io_w_req_bits_data_tag = s3_io_metaWriteBus_req_bits_data_tag; // @[Cache.scala 532:18]
  assign metaArray_io_w_req_bits_data_dirty = s3_io_metaWriteBus_req_bits_data_dirty; // @[Cache.scala 532:18]
  assign metaArray_io_w_req_bits_waymask = s3_io_metaWriteBus_req_bits_waymask; // @[Cache.scala 532:18]
  assign dataArray_clock = clock;
  assign dataArray_reset = reset;
  assign dataArray_io_r_0_req_valid = s1_io_dataReadBus_req_valid; // @[Cache.scala 529:21]
  assign dataArray_io_r_0_req_bits_setIdx = s1_io_dataReadBus_req_bits_setIdx; // @[Cache.scala 529:21]
  assign dataArray_io_r_1_req_valid = s3_io_dataReadBus_req_valid; // @[Cache.scala 530:21]
  assign dataArray_io_r_1_req_bits_setIdx = s3_io_dataReadBus_req_bits_setIdx; // @[Cache.scala 530:21]
  assign dataArray_io_w_req_valid = s3_io_dataWriteBus_req_valid; // @[Cache.scala 533:18]
  assign dataArray_io_w_req_bits_setIdx = s3_io_dataWriteBus_req_bits_setIdx; // @[Cache.scala 533:18]
  assign dataArray_io_w_req_bits_data_data = s3_io_dataWriteBus_req_bits_data_data; // @[Cache.scala 533:18]
  assign dataArray_io_w_req_bits_waymask = s3_io_dataWriteBus_req_bits_waymask; // @[Cache.scala 533:18]
  assign arb_io_in_0_valid = io_out_coh_req_valid; // @[Cache.scala 518:24]
  assign arb_io_in_0_bits_addr = io_out_coh_req_bits_addr; // @[Cache.scala 515:19 SimpleBus.scala 64:15]
  assign arb_io_in_0_bits_size = io_out_coh_req_bits_size; // @[Cache.scala 515:19 SimpleBus.scala 66:15]
  assign arb_io_in_0_bits_cmd = io_out_coh_req_bits_cmd; // @[Cache.scala 515:19 SimpleBus.scala 65:14]
  assign arb_io_in_0_bits_wmask = io_out_coh_req_bits_wmask; // @[Cache.scala 515:19 SimpleBus.scala 68:16]
  assign arb_io_in_0_bits_wdata = io_out_coh_req_bits_wdata; // @[Cache.scala 515:19 SimpleBus.scala 67:16]
  assign arb_io_in_1_valid = io_in_req_valid; // @[Cache.scala 494:28]
  assign arb_io_in_1_bits_addr = io_in_req_bits_addr; // @[Cache.scala 494:28]
  assign arb_io_in_1_bits_size = io_in_req_bits_size; // @[Cache.scala 494:28]
  assign arb_io_in_1_bits_cmd = io_in_req_bits_cmd; // @[Cache.scala 494:28]
  assign arb_io_in_1_bits_wmask = io_in_req_bits_wmask; // @[Cache.scala 494:28]
  assign arb_io_in_1_bits_wdata = io_in_req_bits_wdata; // @[Cache.scala 494:28]
  assign arb_io_in_1_bits_user = io_in_req_bits_user; // @[Cache.scala 494:28]
  assign arb_io_out_ready = s1_io_in_ready; // @[Cache.scala 496:12]
  assign victim_way_mask_valid = s2_io_out_valid; // Interface for uvm reference model
  always @(posedge clock) begin
    if (reset) begin // @[Pipeline.scala 24:24]
      valid <= 1'h0; // @[Pipeline.scala 24:24]
    end else if (io_flush[0]) begin // @[Pipeline.scala 27:20]
      valid <= 1'h0; // @[Pipeline.scala 27:28]
    end else begin
      valid <= _GEN_1;
    end
    if (_T_2) begin // @[Reg.scala 20:18]
      s2_io_in_bits_r_req_addr <= s1_io_out_bits_req_addr; // @[Reg.scala 20:22]
    end
    if (_T_2) begin // @[Reg.scala 20:18]
      s2_io_in_bits_r_req_size <= s1_io_out_bits_req_size; // @[Reg.scala 20:22]
    end
    if (_T_2) begin // @[Reg.scala 20:18]
      s2_io_in_bits_r_req_cmd <= s1_io_out_bits_req_cmd; // @[Reg.scala 20:22]
    end
    if (_T_2) begin // @[Reg.scala 20:18]
      s2_io_in_bits_r_req_wmask <= s1_io_out_bits_req_wmask; // @[Reg.scala 20:22]
    end
    if (_T_2) begin // @[Reg.scala 20:18]
      s2_io_in_bits_r_req_wdata <= s1_io_out_bits_req_wdata; // @[Reg.scala 20:22]
    end
    if (_T_2) begin // @[Reg.scala 20:18]
      s2_io_in_bits_r_req_user <= s1_io_out_bits_req_user; // @[Reg.scala 20:22]
    end
    if (reset) begin // @[Pipeline.scala 24:24]
      valid_1 <= 1'h0; // @[Pipeline.scala 24:24]
    end else if (io_flush[1]) begin // @[Pipeline.scala 27:20]
      valid_1 <= 1'h0; // @[Pipeline.scala 27:28]
    end else begin
      valid_1 <= _GEN_10;
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_req_addr <= s2_io_out_bits_req_addr; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_req_size <= s2_io_out_bits_req_size; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_req_cmd <= s2_io_out_bits_req_cmd; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_req_wmask <= s2_io_out_bits_req_wmask; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_req_wdata <= s2_io_out_bits_req_wdata; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_req_user <= s2_io_out_bits_req_user; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_metas_0_tag <= s2_io_out_bits_metas_0_tag; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_metas_0_dirty <= s2_io_out_bits_metas_0_dirty; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_metas_1_tag <= s2_io_out_bits_metas_1_tag; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_metas_1_dirty <= s2_io_out_bits_metas_1_dirty; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_metas_2_tag <= s2_io_out_bits_metas_2_tag; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_metas_2_dirty <= s2_io_out_bits_metas_2_dirty; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_metas_3_tag <= s2_io_out_bits_metas_3_tag; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_metas_3_dirty <= s2_io_out_bits_metas_3_dirty; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_datas_0_data <= s2_io_out_bits_datas_0_data; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_datas_1_data <= s2_io_out_bits_datas_1_data; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_datas_2_data <= s2_io_out_bits_datas_2_data; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_datas_3_data <= s2_io_out_bits_datas_3_data; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_hit <= s2_io_out_bits_hit; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_waymask <= s2_io_out_bits_waymask; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_mmio <= s2_io_out_bits_mmio; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_isForwardData <= s2_io_out_bits_isForwardData; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_forwardData_data_data <= s2_io_out_bits_forwardData_data_data; // @[Reg.scala 20:22]
    end
    if (_T_4) begin // @[Reg.scala 20:18]
      s3_io_in_bits_r_forwardData_waymask <= s2_io_out_bits_forwardData_waymask; // @[Reg.scala 20:22]
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
  valid = _RAND_0[0:0];
  _RAND_1 = {1{`RANDOM}};
  s2_io_in_bits_r_req_addr = _RAND_1[31:0];
  _RAND_2 = {1{`RANDOM}};
  s2_io_in_bits_r_req_size = _RAND_2[2:0];
  _RAND_3 = {1{`RANDOM}};
  s2_io_in_bits_r_req_cmd = _RAND_3[3:0];
  _RAND_4 = {1{`RANDOM}};
  s2_io_in_bits_r_req_wmask = _RAND_4[7:0];
  _RAND_5 = {2{`RANDOM}};
  s2_io_in_bits_r_req_wdata = _RAND_5[63:0];
  _RAND_6 = {1{`RANDOM}};
  s2_io_in_bits_r_req_user = _RAND_6[15:0];
  _RAND_7 = {1{`RANDOM}};
  valid_1 = _RAND_7[0:0];
  _RAND_8 = {1{`RANDOM}};
  s3_io_in_bits_r_req_addr = _RAND_8[31:0];
  _RAND_9 = {1{`RANDOM}};
  s3_io_in_bits_r_req_size = _RAND_9[2:0];
  _RAND_10 = {1{`RANDOM}};
  s3_io_in_bits_r_req_cmd = _RAND_10[3:0];
  _RAND_11 = {1{`RANDOM}};
  s3_io_in_bits_r_req_wmask = _RAND_11[7:0];
  _RAND_12 = {2{`RANDOM}};
  s3_io_in_bits_r_req_wdata = _RAND_12[63:0];
  _RAND_13 = {1{`RANDOM}};
  s3_io_in_bits_r_req_user = _RAND_13[15:0];
  _RAND_14 = {1{`RANDOM}};
  s3_io_in_bits_r_metas_0_tag = _RAND_14[18:0];
  _RAND_15 = {1{`RANDOM}};
  s3_io_in_bits_r_metas_0_dirty = _RAND_15[0:0];
  _RAND_16 = {1{`RANDOM}};
  s3_io_in_bits_r_metas_1_tag = _RAND_16[18:0];
  _RAND_17 = {1{`RANDOM}};
  s3_io_in_bits_r_metas_1_dirty = _RAND_17[0:0];
  _RAND_18 = {1{`RANDOM}};
  s3_io_in_bits_r_metas_2_tag = _RAND_18[18:0];
  _RAND_19 = {1{`RANDOM}};
  s3_io_in_bits_r_metas_2_dirty = _RAND_19[0:0];
  _RAND_20 = {1{`RANDOM}};
  s3_io_in_bits_r_metas_3_tag = _RAND_20[18:0];
  _RAND_21 = {1{`RANDOM}};
  s3_io_in_bits_r_metas_3_dirty = _RAND_21[0:0];
  _RAND_22 = {2{`RANDOM}};
  s3_io_in_bits_r_datas_0_data = _RAND_22[63:0];
  _RAND_23 = {2{`RANDOM}};
  s3_io_in_bits_r_datas_1_data = _RAND_23[63:0];
  _RAND_24 = {2{`RANDOM}};
  s3_io_in_bits_r_datas_2_data = _RAND_24[63:0];
  _RAND_25 = {2{`RANDOM}};
  s3_io_in_bits_r_datas_3_data = _RAND_25[63:0];
  _RAND_26 = {1{`RANDOM}};
  s3_io_in_bits_r_hit = _RAND_26[0:0];
  _RAND_27 = {1{`RANDOM}};
  s3_io_in_bits_r_waymask = _RAND_27[3:0];
  _RAND_28 = {1{`RANDOM}};
  s3_io_in_bits_r_mmio = _RAND_28[0:0];
  _RAND_29 = {1{`RANDOM}};
  s3_io_in_bits_r_isForwardData = _RAND_29[0:0];
  _RAND_30 = {2{`RANDOM}};
  s3_io_in_bits_r_forwardData_data_data = _RAND_30[63:0];
  _RAND_31 = {1{`RANDOM}};
  s3_io_in_bits_r_forwardData_waymask = _RAND_31[3:0];
`endif // RANDOMIZE_REG_INIT
  `endif // RANDOMIZE
end // initial
`ifdef FIRRTL_AFTER_INITIAL
`FIRRTL_AFTER_INITIAL
`endif
`endif // SYNTHESIS
endmodule