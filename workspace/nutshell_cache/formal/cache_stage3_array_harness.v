// Reduced one-set/one-line-per-way SRAM model plus an abstract 8-beat memory.
// Each symbolic 64-bit seed defines eight distinct words by XORing the beat
// index into the low bits. Assertions check writeback/refill ordering against
// those independent line functions and record refill data in a small shadow array.
module CacheStage3ArrayHarness(
  input clock,
  input reset,
  input victim_dirty,
  input [63:0] victim_line_seed,
  input [63:0] abstract_memory_seed
);
  wire data_read_valid;
  wire [9:0] data_read_set;
  wire data_write_valid;
  wire [9:0] data_write_set;
  wire [63:0] data_write_data;
  wire [3:0] data_write_waymask;
  wire mem_req_valid;
  wire [31:0] mem_req_addr;
  wire [3:0] mem_req_cmd;
  wire [63:0] mem_req_wdata;
  wire mem_resp_valid;
  wire [3:0] mem_resp_cmd;
  wire [63:0] mem_resp_data;
  wire is_finish;

  reg writeback_complete = 1'b0;
  reg writeback_response_sent = 1'b0;
  reg refill_active = 1'b0;
  reg [3:0] writeback_count = 4'b0;
  reg [3:0] refill_count = 4'b0;
  reg [7:0] refill_seen = 8'b0;
  reg [63:0] refill_array [0:7];
  reg [63:0] refill_expected [0:7];
  reg f_past_valid = 1'b0;

  function automatic [63:0] get_victim_word(input [2:0] index);
    begin
      get_victim_word = victim_line_seed ^ {61'b0, index};
    end
  endfunction
  function automatic [63:0] get_memory_word(input [2:0] index);
    begin
      get_memory_word = abstract_memory_seed ^ {61'b0, index};
    end
  endfunction

  assign mem_resp_valid = (writeback_complete && !writeback_response_sent) ||
                          (refill_active && refill_count < 4'd8);
  assign mem_resp_cmd = (writeback_complete && !writeback_response_sent) ? 4'h5 :
                        (refill_count == 4'd7 ? 4'h6 : 4'h0);
  assign mem_resp_data = (writeback_complete && !writeback_response_sent) ?
                         64'b0 : get_memory_word(refill_count[2:0]);

  CacheStage3 dut (
    .clock(clock), .reset(reset), .io_in_ready(), .io_in_valid(1'b1),
    .io_in_bits_req_addr(32'h0000_4000), .io_in_bits_req_size(3'd3),
    .io_in_bits_req_cmd(4'h0), .io_in_bits_req_wmask(8'hff),
    .io_in_bits_req_wdata(64'hfeed_face_cafe_beef), .io_in_bits_req_user(16'b0),
    .io_in_bits_metas_0_tag(19'h1), .io_in_bits_metas_0_dirty(victim_dirty),
    .io_in_bits_metas_1_tag(19'h0), .io_in_bits_metas_1_dirty(1'b0),
    .io_in_bits_metas_2_tag(19'h0), .io_in_bits_metas_2_dirty(1'b0),
    .io_in_bits_metas_3_tag(19'h0), .io_in_bits_metas_3_dirty(1'b0),
    .io_in_bits_datas_0_data(64'b0), .io_in_bits_datas_1_data(64'b0),
    .io_in_bits_datas_2_data(64'b0), .io_in_bits_datas_3_data(64'b0),
    .io_in_bits_hit(1'b0), .io_in_bits_waymask(4'b0001), .io_in_bits_mmio(1'b0),
    .io_in_bits_isForwardData(1'b0), .io_in_bits_forwardData_data_data(64'b0),
    .io_in_bits_forwardData_waymask(4'b0), .io_out_ready(1'b1), .io_out_valid(),
    .io_out_bits_cmd(), .io_out_bits_rdata(), .io_out_bits_user(),
    .io_isFinish(is_finish), .io_flush(1'b0),
    .io_dataReadBus_req_ready(1'b1), .io_dataReadBus_req_valid(data_read_valid),
    .io_dataReadBus_req_bits_setIdx(data_read_set),
    .io_dataReadBus_resp_data_0_data(get_victim_word(data_read_set[2:0])),
    .io_dataReadBus_resp_data_1_data(64'b0),
    .io_dataReadBus_resp_data_2_data(64'b0),
    .io_dataReadBus_resp_data_3_data(64'b0),
    .io_dataWriteBus_req_valid(data_write_valid),
    .io_dataWriteBus_req_bits_setIdx(data_write_set),
    .io_dataWriteBus_req_bits_data_data(data_write_data),
    .io_dataWriteBus_req_bits_waymask(data_write_waymask),
    .io_metaWriteBus_req_valid(), .io_metaWriteBus_req_bits_setIdx(),
    .io_metaWriteBus_req_bits_data_tag(), .io_metaWriteBus_req_bits_data_dirty(),
    .io_metaWriteBus_req_bits_waymask(),
    .io_mem_req_ready(1'b1), .io_mem_req_valid(mem_req_valid),
    .io_mem_req_bits_addr(mem_req_addr), .io_mem_req_bits_cmd(mem_req_cmd),
    .io_mem_req_bits_wdata(mem_req_wdata), .io_mem_resp_ready(),
    .io_mem_resp_valid(mem_resp_valid), .io_mem_resp_bits_cmd(mem_resp_cmd),
    .io_mem_resp_bits_rdata(mem_resp_data), .io_mmio_req_ready(1'b1),
    .io_mmio_req_valid(), .io_mmio_req_bits_addr(), .io_mmio_req_bits_size(),
    .io_mmio_req_bits_cmd(), .io_mmio_req_bits_wmask(), .io_mmio_req_bits_wdata(),
    .io_mmio_resp_ready(), .io_mmio_resp_valid(1'b0),
    .io_mmio_resp_bits_rdata(64'b0), .io_cohResp_ready(1'b1),
    .io_cohResp_valid(), .io_cohResp_bits_cmd(), .io_cohResp_bits_rdata(),
    .io_dataReadRespToL1()
  );

  integer i;
  always @(posedge clock) begin
    f_past_valid <= 1'b1;
    if ($initstate)
      assume (reset);
    if (f_past_valid)
      assume (!reset);
    if (f_past_valid && !$past(reset)) begin
      assume (victim_line_seed == $past(victim_line_seed));
      assume (abstract_memory_seed == $past(abstract_memory_seed));
    end

    if (reset) begin
      writeback_complete <= 1'b0;
      writeback_response_sent <= 1'b0;
      refill_active <= 1'b0;
      writeback_count <= 4'b0;
      refill_count <= 4'b0;
      refill_seen <= 8'b0;
    end else begin
      if (data_read_valid)
        assert (data_read_set[2:0] == writeback_count[2:0]);

      if (mem_req_valid && (mem_req_cmd == 4'h3 || mem_req_cmd == 4'h7)) begin
        assert (mem_req_addr == 32'h0000_2000);
        assert (mem_req_wdata == get_victim_word(writeback_count[2:0]));
        assert (data_read_set[2:0] == writeback_count[2:0]);
        if (writeback_count < 4'd7)
          assert (mem_req_cmd == 4'h3);
        else
          assert (mem_req_cmd == 4'h7);
        writeback_count <= writeback_count + 4'd1;
        if (mem_req_cmd == 4'h7)
          writeback_complete <= 1'b1;
      end

      if (mem_resp_valid && writeback_complete && !writeback_response_sent)
        writeback_response_sent <= 1'b1;

      if (mem_req_valid && mem_req_cmd == 4'h2) begin
        refill_active <= 1'b1;
        refill_count <= 4'b0;
      end else if (refill_active && mem_resp_valid) begin
        refill_count <= refill_count + 4'd1;
        if (refill_count == 4'd7)
          refill_active <= 1'b0;
      end

      if (data_write_valid) begin
        assert (refill_active);
        assert (data_write_set[2:0] == refill_count[2:0]);
        assert (data_write_waymask == 4'b0001);
        assert (data_write_data == get_memory_word(refill_count[2:0]));
        refill_array[refill_count[2:0]] <= data_write_data;
        refill_expected[refill_count[2:0]] <= get_memory_word(refill_count[2:0]);
        refill_seen[refill_count[2:0]] <= 1'b1;
      end

      for (i = 0; i < 8; i = i + 1)
        if (refill_seen[i])
          assert (refill_array[i] == refill_expected[i]);
    end

    cover (mem_req_valid && mem_req_cmd == 4'h7);
    cover (refill_active && refill_count == 4'd7 && mem_resp_valid);
  end
endmodule
