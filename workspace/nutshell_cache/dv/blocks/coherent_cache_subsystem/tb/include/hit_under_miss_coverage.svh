begin : hit_under_miss_raw_coverage
  logic [63:0] hit_under_miss_expected;
  logic [63:0] hit_under_miss_data;
  logic [63:0] pending_miss_expected;
  logic [TXN_ID_WIDTH-1:0] pending_miss_id;
  logic [TXN_ID_WIDTH-1:0] bypass_hit_id;
  logic pending_hit_seen;
  logic pending_miss_seen;
  integer hit_under_miss_cycles;

  // 0x9000 was filled by the preceding backpressure scenario. Keep a cold
  // miss outstanding at 0xA000 while the resident line is read and returned.
  // The backing-memory request stall makes the overlap deterministic.
  reference_get(32'h0000_9000, hit_under_miss_expected);
  reference_get(32'h0000_A000, pending_miss_expected);
  benchmark_measure_enable = 1'b0;
  inject_periodic_stalls = 1'b0;
  stall_mem_rd_req = 1'b1;
  cpu_resp_ready[0] = 1'b0;
  cpu_issue_only(0, 32'h0000_A000, 1'b0, 8'h00, 64'b0);

  pending_miss_seen = 1'b0;
  for (hit_under_miss_cycles = 0; hit_under_miss_cycles < 100; hit_under_miss_cycles++) begin
    @(posedge clock);
    if ((dut.l1_cluster.cores[0].controller_cpu_state == 3'd2) &&
        mem_rd_req_valid && !mem_rd_req_ready) begin
      pending_miss_seen = 1'b1;
      break;
    end
  end
  if (!pending_miss_seen)
    $fatal(1, "Hit-under-Miss coverage setup failed to hold a cold miss at Directory grant/refill");

  pending_miss_id = dut.l1_cluster.cores[0].ctrl_resp_txn_id;
  cpu_issue_only(0, 32'h0000_9000, 1'b0, 8'h00, 64'b0);

  pending_hit_seen = 1'b0;
  for (hit_under_miss_cycles = 0; hit_under_miss_cycles < 20; hit_under_miss_cycles++) begin
    @(posedge clock);
    if (cpu_resp_valid[0]) begin
      pending_hit_seen = 1'b1;
      break;
    end
  end
  if (!pending_hit_seen)
    $fatal(1, "resident read did not complete while a different miss was pending");
  if (cpu_resp_addr[0] !== 32'h0000_9000 || cpu_resp_write[0] !== 1'b0 ||
      cpu_resp_rdata[0] !== hit_under_miss_expected ||
      cpu_resp_txn_id[0] === pending_miss_id)
    $fatal(1, "Hit-under-Miss response mismatch: addr=%08x data=%016x id=%0d miss_id=%0d",
           cpu_resp_addr[0], cpu_resp_rdata[0], cpu_resp_txn_id[0], pending_miss_id);
  hit_under_miss_data = cpu_resp_rdata[0];
  bypass_hit_id = cpu_resp_txn_id[0];

  // The bypass response is deliberately backpressured. Its full payload and
  // allocated ID must remain stable, and the pending miss must not be lost.
  repeat (3) begin
    @(posedge clock);
    if (!cpu_resp_valid[0] || cpu_resp_addr[0] !== 32'h0000_9000 ||
        cpu_resp_rdata[0] !== hit_under_miss_data ||
        cpu_resp_txn_id[0] !== bypass_hit_id ||
        dut.l1_cluster.cores[0].controller_cpu_state != 3'd2)
      $fatal(1, "Hit-under-Miss response changed under CPU response backpressure");
  end
  @(negedge clock);
  cpu_resp_ready[0] = 1'b1;
  @(posedge clock);
  state_model_apply_cpu(0, 32'h0000_9000, 1'b0);
  @(negedge clock);
  if (cpu_resp_valid[0])
    $fatal(1, "bypass hit response was repeated after acceptance");
  state_model_check_all();

  // Release the blocked memory request and independently check the original
  // miss response retains its own address, data, and transaction ID.
  stall_mem_rd_req = 1'b0;
  cpu_resp_ready[0] = 1'b0;
  pending_miss_seen = 1'b0;
  for (hit_under_miss_cycles = 0; hit_under_miss_cycles < 1000; hit_under_miss_cycles++) begin
    @(posedge clock);
    if (cpu_resp_valid[0]) begin
      pending_miss_seen = 1'b1;
      break;
    end
  end
  if (!pending_miss_seen)
    $fatal(1, "pending miss response did not arrive after memory request was released");
  if (cpu_resp_addr[0] !== 32'h0000_A000 || cpu_resp_write[0] !== 1'b0 ||
      cpu_resp_rdata[0] !== pending_miss_expected ||
      cpu_resp_txn_id[0] !== pending_miss_id)
    $fatal(1, "pending miss response was lost or misrouted: addr=%08x data=%016x id=%0d expected_id=%0d",
           cpu_resp_addr[0], cpu_resp_rdata[0], cpu_resp_txn_id[0], pending_miss_id);
  hit_under_miss_data = cpu_resp_rdata[0];
  repeat (2) begin
    @(posedge clock);
    if (!cpu_resp_valid[0] || cpu_resp_addr[0] !== 32'h0000_A000 ||
        cpu_resp_rdata[0] !== hit_under_miss_data ||
        cpu_resp_txn_id[0] !== pending_miss_id)
      $fatal(1, "pending miss response changed under CPU response backpressure");
  end
  @(negedge clock);
  cpu_resp_ready[0] = 1'b1;
  @(posedge clock);
  state_model_apply_cpu(0, 32'h0000_A000, 1'b0);
  @(negedge clock);
  if (cpu_resp_valid[0])
    $fatal(1, "pending miss response was repeated after acceptance");
  state_model_check_all();

  benchmark_measure_enable = 1'b1;
  inject_periodic_stalls = 1'b1;
  $display("PASS: raw RTL Hit-under-Miss preserves both checked responses and distinct transaction IDs under backpressure");
end
