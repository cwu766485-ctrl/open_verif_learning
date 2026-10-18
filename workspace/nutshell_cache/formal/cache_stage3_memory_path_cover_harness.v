module CacheStage3MemoryPathCover #(parameter DIRTY_VICTIM = 1'b0)(input clock);
  reg reset_seen = 1'b0;
  always @(posedge clock)
    reset_seen <= 1'b1;
  wire reset = !reset_seen;

  reg writeback_done = 1'b0;
  reg writeback_response_sent = 1'b0;
  reg refill_active = 1'b0;
  reg [3:0] refill_count = 4'b0;
  wire mem_req_valid;
  wire [3:0] mem_req_cmd;
  wire mem_resp_valid = (writeback_done && !writeback_response_sent) ||
                        (refill_active && refill_count < 4'd8);
  wire [3:0] mem_resp_cmd = (writeback_done && !writeback_response_sent) ? 4'h5 :
                             (refill_count == 4'd7 ? 4'h6 : 4'h0);

  CacheStage3 dut (
    .clock(clock), .reset(reset), .io_in_ready(), .io_in_valid(1'b1),
    .io_in_bits_req_addr(32'h0000_4000), .io_in_bits_req_size(3'd3),
    .io_in_bits_req_cmd(4'h0), .io_in_bits_req_wmask(8'hff),
    .io_in_bits_req_wdata(64'b0), .io_in_bits_req_user(16'b0),
    .io_in_bits_metas_0_tag(19'h1), .io_in_bits_metas_0_dirty(DIRTY_VICTIM),
    .io_in_bits_metas_1_tag(19'h0), .io_in_bits_metas_1_dirty(1'b0),
    .io_in_bits_metas_2_tag(19'h0), .io_in_bits_metas_2_dirty(1'b0),
    .io_in_bits_metas_3_tag(19'h0), .io_in_bits_metas_3_dirty(1'b0),
    .io_in_bits_datas_0_data(64'b0), .io_in_bits_datas_1_data(64'b0),
    .io_in_bits_datas_2_data(64'b0), .io_in_bits_datas_3_data(64'b0),
    .io_in_bits_hit(1'b0), .io_in_bits_waymask(4'b0001), .io_in_bits_mmio(1'b0),
    .io_in_bits_isForwardData(1'b0), .io_in_bits_forwardData_data_data(64'b0),
    .io_in_bits_forwardData_waymask(4'b0), .io_out_ready(1'b1),
    .io_out_valid(), .io_out_bits_cmd(), .io_out_bits_rdata(), .io_out_bits_user(),
    .io_isFinish(), .io_flush(1'b0), .io_dataReadBus_req_ready(1'b1),
    .io_dataReadBus_req_valid(), .io_dataReadBus_req_bits_setIdx(),
    .io_dataReadBus_resp_data_0_data(64'h1111),
    .io_dataReadBus_resp_data_1_data(64'b0),
    .io_dataReadBus_resp_data_2_data(64'b0),
    .io_dataReadBus_resp_data_3_data(64'b0),
    .io_dataWriteBus_req_valid(), .io_dataWriteBus_req_bits_setIdx(),
    .io_dataWriteBus_req_bits_data_data(), .io_dataWriteBus_req_bits_waymask(),
    .io_metaWriteBus_req_valid(), .io_metaWriteBus_req_bits_setIdx(),
    .io_metaWriteBus_req_bits_data_tag(), .io_metaWriteBus_req_bits_data_dirty(),
    .io_metaWriteBus_req_bits_waymask(), .io_mem_req_ready(1'b1),
    .io_mem_req_valid(mem_req_valid), .io_mem_req_bits_addr(),
    .io_mem_req_bits_cmd(mem_req_cmd), .io_mem_req_bits_wdata(),
    .io_mem_resp_ready(), .io_mem_resp_valid(mem_resp_valid),
    .io_mem_resp_bits_cmd(mem_resp_cmd), .io_mem_resp_bits_rdata(64'hbeef),
    .io_mmio_req_ready(1'b1), .io_mmio_req_valid(), .io_mmio_req_bits_addr(),
    .io_mmio_req_bits_size(), .io_mmio_req_bits_cmd(), .io_mmio_req_bits_wmask(),
    .io_mmio_req_bits_wdata(), .io_mmio_resp_ready(), .io_mmio_resp_valid(1'b0),
    .io_mmio_resp_bits_rdata(64'b0), .io_cohResp_ready(1'b1),
    .io_cohResp_valid(), .io_cohResp_bits_cmd(), .io_cohResp_bits_rdata(),
    .io_dataReadRespToL1()
  );

  always @(posedge clock) begin
    if (reset) begin
      writeback_done <= 1'b0;
      writeback_response_sent <= 1'b0;
      refill_active <= 1'b0;
      refill_count <= 4'b0;
    end else begin
      if (mem_req_valid && mem_req_cmd == 4'h7)
        writeback_done <= 1'b1;
      if (writeback_done && !writeback_response_sent)
        writeback_response_sent <= 1'b1;
      if (mem_req_valid && mem_req_cmd == 4'h2) begin
        refill_active <= 1'b1;
        refill_count <= 4'b0;
      end else if (refill_active && mem_resp_valid &&
                   !(writeback_done && !writeback_response_sent)) begin
        refill_count <= refill_count + 4'd1;
        if (refill_count == 4'd7)
          refill_active <= 1'b0;
      end
    end

    if (DIRTY_VICTIM)
      cover (!reset && mem_req_valid && mem_req_cmd == 4'h7);
    else
      cover (!reset && refill_active && refill_count == 4'd7 && mem_resp_valid);
  end
endmodule

module CacheStage3DirtyWritebackCoverHarness(input clock);
  CacheStage3MemoryPathCover #(.DIRTY_VICTIM(1'b1)) scenario(.clock(clock));
endmodule

module CacheStage3CleanRefillCoverHarness(input clock);
  CacheStage3MemoryPathCover #(.DIRTY_VICTIM(1'b0)) scenario(.clock(clock));
endmodule
