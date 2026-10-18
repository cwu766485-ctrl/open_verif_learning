// One-set, four-way metadata model driven by the real Stage3 write port.
// The model starts empty and derives hit/victim selection from its own tags,
// so no external unique-tag assumption is needed.
module CacheMetadataInvariantHarness(
  input clock,
  input reset,
  input request_valid,
  input [1:0] request_tag,
  input [3:0] request_cmd,
  input [7:0] request_wmask,
  input [63:0] request_wdata,
  input mem_req_ready,
  input mem_resp_valid,
  input [3:0] mem_resp_cmd
);
  reg [3:0] meta_valid = 4'b0000;
  reg [18:0] meta_tag_0 = 19'b0;
  reg [18:0] meta_tag_1 = 19'b0;
  reg [18:0] meta_tag_2 = 19'b0;
  reg [18:0] meta_tag_3 = 19'b0;
  reg [3:0] meta_dirty = 4'b0000;

  wire [3:0] hit_vec = {
    meta_valid[3] && (meta_tag_3 == request_tag),
    meta_valid[2] && (meta_tag_2 == request_tag),
    meta_valid[1] && (meta_tag_1 == request_tag),
    meta_valid[0] && (meta_tag_0 == request_tag)
  };
  wire [3:0] invalid_vec = ~meta_valid;
  // Four encodings are enough to exercise duplicate/replacement behavior.
  // The separately proven ReplacementSelector covers randomized full-set
  // replacement; this harness uses a deterministic one-hot victim choice.
  wire [3:0] refill_way_onehot = invalid_vec[0] ? 4'b0001 :
                                  invalid_vec[1] ? 4'b0010 :
                                  invalid_vec[2] ? 4'b0100 :
                                  invalid_vec[3] ? 4'b1000 : 4'b0001;
  wire [3:0] selected_waymask = (|hit_vec) ? hit_vec : refill_way_onehot;
  wire selected_dirty = |(selected_waymask & meta_dirty);

  wire meta_write_valid;
  wire [3:0] meta_write_waymask;
  wire [18:0] meta_write_tag;
  wire meta_write_dirty;
  wire [6:0] meta_write_set;
  wire is_finish;

  CacheStage3 dut (
    .clock(clock), .reset(reset), .io_in_ready(),
    .io_in_valid(request_valid),
    .io_in_bits_req_addr({17'b0, request_tag, 7'b0, 6'b0}),
    .io_in_bits_req_size(3'd3), .io_in_bits_req_cmd(request_cmd),
    .io_in_bits_req_wmask(request_wmask), .io_in_bits_req_wdata(request_wdata),
    .io_in_bits_req_user(16'b0),
    .io_in_bits_metas_0_tag(meta_tag_0), .io_in_bits_metas_0_dirty(meta_dirty[0]),
    .io_in_bits_metas_1_tag(meta_tag_1), .io_in_bits_metas_1_dirty(meta_dirty[1]),
    .io_in_bits_metas_2_tag(meta_tag_2), .io_in_bits_metas_2_dirty(meta_dirty[2]),
    .io_in_bits_metas_3_tag(meta_tag_3), .io_in_bits_metas_3_dirty(meta_dirty[3]),
    .io_in_bits_datas_0_data(64'b0), .io_in_bits_datas_1_data(64'b0),
    .io_in_bits_datas_2_data(64'b0), .io_in_bits_datas_3_data(64'b0),
    .io_in_bits_hit(|hit_vec), .io_in_bits_waymask(selected_waymask),
    .io_in_bits_mmio(1'b0), .io_in_bits_isForwardData(1'b0),
    .io_in_bits_forwardData_data_data(64'b0), .io_in_bits_forwardData_waymask(4'b0),
    .io_out_ready(1'b1), .io_out_valid(), .io_out_bits_cmd(), .io_out_bits_rdata(),
    .io_out_bits_user(), .io_isFinish(is_finish), .io_flush(1'b0),
    .io_dataReadBus_req_ready(1'b1), .io_dataReadBus_req_valid(),
    .io_dataReadBus_req_bits_setIdx(),
    .io_dataReadBus_resp_data_0_data(64'b0), .io_dataReadBus_resp_data_1_data(64'b0),
    .io_dataReadBus_resp_data_2_data(64'b0), .io_dataReadBus_resp_data_3_data(64'b0),
    .io_dataWriteBus_req_valid(), .io_dataWriteBus_req_bits_setIdx(),
    .io_dataWriteBus_req_bits_data_data(), .io_dataWriteBus_req_bits_waymask(),
    .io_metaWriteBus_req_valid(meta_write_valid),
    .io_metaWriteBus_req_bits_setIdx(meta_write_set),
    .io_metaWriteBus_req_bits_data_tag(meta_write_tag),
    .io_metaWriteBus_req_bits_data_dirty(meta_write_dirty),
    .io_metaWriteBus_req_bits_waymask(meta_write_waymask),
    .io_mem_req_ready(mem_req_ready), .io_mem_req_valid(), .io_mem_req_bits_addr(),
    .io_mem_req_bits_cmd(), .io_mem_req_bits_wdata(), .io_mem_resp_ready(),
    .io_mem_resp_valid(mem_resp_valid), .io_mem_resp_bits_cmd(mem_resp_cmd),
    .io_mem_resp_bits_rdata(64'b0), .io_mmio_req_ready(1'b1), .io_mmio_req_valid(),
    .io_mmio_req_bits_addr(), .io_mmio_req_bits_size(), .io_mmio_req_bits_cmd(),
    .io_mmio_req_bits_wmask(), .io_mmio_req_bits_wdata(), .io_mmio_resp_ready(),
    .io_mmio_resp_valid(1'b0), .io_mmio_resp_bits_rdata(64'b0),
    .io_cohResp_ready(1'b1), .io_cohResp_valid(), .io_cohResp_bits_cmd(),
    .io_cohResp_bits_rdata(), .io_dataReadRespToL1()
  );

  function automatic onehot4(input [3:0] value);
    begin
      onehot4 = (value != 4'b0) && ((value & (value - 4'b1)) == 4'b0);
    end
  endfunction

  reg past_valid = 1'b0;
  always @(posedge clock) begin
    past_valid <= 1'b1;
    if ($initstate)
      assume (reset);
    if (past_valid && !$past(reset) && !reset &&
        $past(request_valid && !is_finish)) begin
      assume (request_valid);
      assume ({request_tag, request_cmd, request_wmask, request_wdata} ==
              $past({request_tag, request_cmd, request_wmask, request_wdata}));
    end

    if (request_valid) begin
      assume ((request_cmd == 4'h0) || (request_cmd == 4'h1));
      assert (onehot4(selected_waymask));
    end

    // Every write targets one way. A refill tag can only replace a way after
    // hit detection has established that this tag is absent from the set.
    if (meta_write_valid) begin
      assert (meta_write_set == 7'b0);
      assert (onehot4(meta_write_waymask));
      assert (meta_write_tag == {17'b0, request_tag});
      if (|hit_vec)
        assert (meta_write_waymask == hit_vec);
      else begin
        assert (!(meta_valid[0] && (meta_tag_0 == meta_write_tag)));
        assert (!(meta_valid[1] && (meta_tag_1 == meta_write_tag)));
        assert (!(meta_valid[2] && (meta_tag_2 == meta_write_tag)));
        assert (!(meta_valid[3] && (meta_tag_3 == meta_write_tag)));
      end
    end

    assert (!(meta_valid[0] && meta_valid[1] && (meta_tag_0 == meta_tag_1)));
    assert (!(meta_valid[0] && meta_valid[2] && (meta_tag_0 == meta_tag_2)));
    assert (!(meta_valid[0] && meta_valid[3] && (meta_tag_0 == meta_tag_3)));
    assert (!(meta_valid[1] && meta_valid[2] && (meta_tag_1 == meta_tag_2)));
    assert (!(meta_valid[1] && meta_valid[3] && (meta_tag_1 == meta_tag_3)));
    assert (!(meta_valid[2] && meta_valid[3] && (meta_tag_2 == meta_tag_3)));

    if (meta_write_valid && meta_write_waymask[0]) begin
      meta_valid[0] <= 1'b1;
      meta_tag_0 <= meta_write_tag;
      meta_dirty[0] <= meta_write_dirty;
    end
    if (meta_write_valid && meta_write_waymask[1]) begin
      meta_valid[1] <= 1'b1;
      meta_tag_1 <= meta_write_tag;
      meta_dirty[1] <= meta_write_dirty;
    end
    if (meta_write_valid && meta_write_waymask[2]) begin
      meta_valid[2] <= 1'b1;
      meta_tag_2 <= meta_write_tag;
      meta_dirty[2] <= meta_write_dirty;
    end
    if (meta_write_valid && meta_write_waymask[3]) begin
      meta_valid[3] <= 1'b1;
      meta_tag_3 <= meta_write_tag;
      meta_dirty[3] <= meta_write_dirty;
    end

    cover (request_valid && !(|hit_vec) && !selected_dirty);
    cover (request_valid && !(|hit_vec) && selected_dirty);
    cover (request_valid && (|hit_vec));
    cover (meta_write_valid);
  end
endmodule
