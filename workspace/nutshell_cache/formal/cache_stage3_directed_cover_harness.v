// Directed, assertion-free wrappers keep cover search focused on reachability.
module CacheStage3ResetCoverHarness(input clock);
  reg [3:0] cycle = 4'b0;
  always @(posedge clock)
    if (cycle < 4'd7) cycle <= cycle + 4'd1;

  wire reset = (cycle == 4'd0) || (cycle == 4'd3);
  wire request_valid = (cycle >= 4'd1) && (cycle < 4'd3);
  wire mem_req_valid;

  CacheStage3 dut (
    .clock(clock), .reset(reset), .io_in_ready(), .io_in_valid(request_valid),
    .io_in_bits_req_addr(32'h0000_1000), .io_in_bits_req_size(3'd3),
    .io_in_bits_req_cmd(4'h0), .io_in_bits_req_wmask(8'hff),
    .io_in_bits_req_wdata(64'b0), .io_in_bits_req_user(16'b0),
    .io_in_bits_metas_0_tag(19'b0), .io_in_bits_metas_0_dirty(1'b0),
    .io_in_bits_metas_1_tag(19'b0), .io_in_bits_metas_1_dirty(1'b0),
    .io_in_bits_metas_2_tag(19'b0), .io_in_bits_metas_2_dirty(1'b0),
    .io_in_bits_metas_3_tag(19'b0), .io_in_bits_metas_3_dirty(1'b0),
    .io_in_bits_datas_0_data(64'b0), .io_in_bits_datas_1_data(64'b0),
    .io_in_bits_datas_2_data(64'b0), .io_in_bits_datas_3_data(64'b0),
    .io_in_bits_hit(1'b0), .io_in_bits_waymask(4'b0001), .io_in_bits_mmio(1'b0),
    .io_in_bits_isForwardData(1'b0), .io_in_bits_forwardData_data_data(64'b0),
    .io_in_bits_forwardData_waymask(4'b0), .io_out_ready(1'b0),
    .io_out_valid(), .io_out_bits_cmd(), .io_out_bits_rdata(), .io_out_bits_user(),
    .io_isFinish(), .io_flush(1'b0), .io_dataReadBus_req_ready(1'b1),
    .io_dataReadBus_req_valid(), .io_dataReadBus_req_bits_setIdx(),
    .io_dataReadBus_resp_data_0_data(64'b0), .io_dataReadBus_resp_data_1_data(64'b0),
    .io_dataReadBus_resp_data_2_data(64'b0), .io_dataReadBus_resp_data_3_data(64'b0),
    .io_dataWriteBus_req_valid(), .io_dataWriteBus_req_bits_setIdx(),
    .io_dataWriteBus_req_bits_data_data(), .io_dataWriteBus_req_bits_waymask(),
    .io_metaWriteBus_req_valid(), .io_metaWriteBus_req_bits_setIdx(),
    .io_metaWriteBus_req_bits_data_tag(), .io_metaWriteBus_req_bits_data_dirty(),
    .io_metaWriteBus_req_bits_waymask(), .io_mem_req_ready(1'b0),
    .io_mem_req_valid(mem_req_valid), .io_mem_req_bits_addr(), .io_mem_req_bits_cmd(),
    .io_mem_req_bits_wdata(), .io_mem_resp_ready(), .io_mem_resp_valid(1'b0),
    .io_mem_resp_bits_cmd(4'b0), .io_mem_resp_bits_rdata(64'b0),
    .io_mmio_req_ready(1'b1), .io_mmio_req_valid(), .io_mmio_req_bits_addr(),
    .io_mmio_req_bits_size(), .io_mmio_req_bits_cmd(), .io_mmio_req_bits_wmask(),
    .io_mmio_req_bits_wdata(), .io_mmio_resp_ready(), .io_mmio_resp_valid(1'b0),
    .io_mmio_resp_bits_rdata(64'b0), .io_cohResp_ready(1'b1),
    .io_cohResp_valid(), .io_cohResp_bits_cmd(), .io_cohResp_bits_rdata(),
    .io_dataReadRespToL1()
  );

  always @(posedge clock)
    cover ((cycle == 4'd3) && mem_req_valid && reset);
endmodule

module CacheStage3StallCoverHarness(input clock);
  reg [3:0] cycle = 4'b0;
  always @(posedge clock)
    if (cycle < 4'd7) cycle <= cycle + 4'd1;

  wire reset = cycle == 4'd0;
  wire request_valid = cycle >= 4'd1;
  wire response_valid;
  wire response_ready = 1'b0;

  CacheStage3 dut (
    .clock(clock), .reset(reset), .io_in_ready(), .io_in_valid(request_valid),
    .io_in_bits_req_addr(32'h0000_1000), .io_in_bits_req_size(3'd3),
    .io_in_bits_req_cmd(4'h0), .io_in_bits_req_wmask(8'hff),
    .io_in_bits_req_wdata(64'b0), .io_in_bits_req_user(16'b0),
    .io_in_bits_metas_0_tag(19'b0), .io_in_bits_metas_0_dirty(1'b0),
    .io_in_bits_metas_1_tag(19'b0), .io_in_bits_metas_1_dirty(1'b0),
    .io_in_bits_metas_2_tag(19'b0), .io_in_bits_metas_2_dirty(1'b0),
    .io_in_bits_metas_3_tag(19'b0), .io_in_bits_metas_3_dirty(1'b0),
    .io_in_bits_datas_0_data(64'h1234), .io_in_bits_datas_1_data(64'b0),
    .io_in_bits_datas_2_data(64'b0), .io_in_bits_datas_3_data(64'b0),
    .io_in_bits_hit(1'b1), .io_in_bits_waymask(4'b0001), .io_in_bits_mmio(1'b0),
    .io_in_bits_isForwardData(1'b0), .io_in_bits_forwardData_data_data(64'b0),
    .io_in_bits_forwardData_waymask(4'b0), .io_out_ready(response_ready),
    .io_out_valid(response_valid), .io_out_bits_cmd(), .io_out_bits_rdata(),
    .io_out_bits_user(), .io_isFinish(), .io_flush(1'b0),
    .io_dataReadBus_req_ready(1'b1), .io_dataReadBus_req_valid(),
    .io_dataReadBus_req_bits_setIdx(), .io_dataReadBus_resp_data_0_data(64'b0),
    .io_dataReadBus_resp_data_1_data(64'b0), .io_dataReadBus_resp_data_2_data(64'b0),
    .io_dataReadBus_resp_data_3_data(64'b0), .io_dataWriteBus_req_valid(),
    .io_dataWriteBus_req_bits_setIdx(), .io_dataWriteBus_req_bits_data_data(),
    .io_dataWriteBus_req_bits_waymask(), .io_metaWriteBus_req_valid(),
    .io_metaWriteBus_req_bits_setIdx(), .io_metaWriteBus_req_bits_data_tag(),
    .io_metaWriteBus_req_bits_data_dirty(), .io_metaWriteBus_req_bits_waymask(),
    .io_mem_req_ready(1'b1), .io_mem_req_valid(), .io_mem_req_bits_addr(),
    .io_mem_req_bits_cmd(), .io_mem_req_bits_wdata(), .io_mem_resp_ready(),
    .io_mem_resp_valid(1'b0), .io_mem_resp_bits_cmd(4'b0),
    .io_mem_resp_bits_rdata(64'b0), .io_mmio_req_ready(1'b1), .io_mmio_req_valid(),
    .io_mmio_req_bits_addr(), .io_mmio_req_bits_size(), .io_mmio_req_bits_cmd(),
    .io_mmio_req_bits_wmask(), .io_mmio_req_bits_wdata(), .io_mmio_resp_ready(),
    .io_mmio_resp_valid(1'b0), .io_mmio_resp_bits_rdata(64'b0),
    .io_cohResp_ready(1'b1), .io_cohResp_valid(), .io_cohResp_bits_cmd(),
    .io_cohResp_bits_rdata(), .io_dataReadRespToL1()
  );

  always @(posedge clock)
    cover ((cycle >= 4'd1) && response_valid && !response_ready);
endmodule
