begin : main_top_mshr_xfer_offer_lock
  logic lock_seen;
  logic lock_released;
  logic [31:0] locked_xfer_addr;
  logic [TXN_ID_WIDTH-1:0] locked_xfer_txn;
  logic [1:0] locked_xfer_context;
  logic locked_xfer_src;
  integer matching_xfer_accepts;
  logic [63:0] xfer_response0;
  logic [63:0] xfer_response1;

  // Two legal, cold CPU reads to different L2 sets. The first owns the shared
  // line engine while its memory request is stalled; the second Directory
  // context must hold its transfer offer stable until the engine is free.
  @(negedge clock);
  reset = 1'b1;
  reference_clear();
  stall_mem_rd_req = 1'b0;
  cpu_req_valid[0] = 1'b0;
  cpu_req_valid[1] = 1'b0;
  cpu_resp_ready[0] = 1'b1;
  cpu_resp_ready[1] = 1'b1;
  repeat (3) @(posedge clock);
  @(negedge clock);
  reset = 1'b0;

  lock_seen = 1'b0;
  lock_released = 1'b0;
  locked_xfer_addr = '0;
  locked_xfer_txn = '0;
  locked_xfer_context = '0;
  locked_xfer_src = 1'b0;
  matching_xfer_accepts = 0;
  stall_mem_rd_req = 1'b1;
  cpu_resp_ready[0] = 1'b0;
  cpu_resp_ready[1] = 1'b0;
  fork
    cpu_issue_only(0, 32'h0120_0000, 1'b0, 8'h00, 64'b0);
    cpu_issue_only(1, 32'h0120_0040, 1'b0, 8'h00, 64'b0);
  join

  for (integer cycle = 0; cycle < 500; cycle++) begin
    @(posedge clock);
    if (dut.directory_controller.xfer_offer_lock_q) begin
      if (!dut.dir_xfer_start_valid)
        $fatal(1, "transfer offer lock asserted without a valid offer");
      if (!lock_seen) begin
        lock_seen = 1'b1;
        locked_xfer_addr = dut.dir_xfer_addr;
        locked_xfer_txn = dut.dir_xfer_txn_id;
        locked_xfer_context = dut.dir_xfer_context_id;
        locked_xfer_src = dut.dir_xfer_src;
      end else if (dut.dir_xfer_addr !== locked_xfer_addr ||
                   dut.dir_xfer_txn_id !== locked_xfer_txn ||
                   dut.dir_xfer_context_id !== locked_xfer_context ||
                   dut.dir_xfer_src !== locked_xfer_src) begin
        $fatal(1, "locked transfer payload changed under engine backpressure");
      end
    end
    if (lock_seen && dut.dir_xfer_start_valid && dut.dir_xfer_start_ready &&
        dut.dir_xfer_addr == locked_xfer_addr &&
        dut.dir_xfer_txn_id == locked_xfer_txn &&
        dut.dir_xfer_context_id == locked_xfer_context) begin
      matching_xfer_accepts = matching_xfer_accepts + 1;
      lock_released = 1'b1;
    end
    // The first accepted transfer owns the engine and is waiting for memory.
    // Release that independent stall once the second transfer is visibly held;
    // it must complete before the locked offer can become ready.
    if (lock_seen)
      stall_mem_rd_req = 1'b0;
    if (lock_released && cpu_resp_valid[0] && cpu_resp_valid[1])
      break;
  end

  if (!lock_seen)
    $fatal(1, "legal dual-cold-miss traffic did not exercise Main Top transfer offer lock");
  if (!lock_released || matching_xfer_accepts != 1)
    $fatal(1, "locked transfer was not accepted exactly once (accepted=%0d)",
           matching_xfer_accepts);
  if (!cpu_resp_valid[0] || !cpu_resp_valid[1])
    $fatal(1, "dual-cold-miss responses did not both complete after releasing memory");
  if (cpu_resp_addr[0] !== 32'h0120_0000 ||
      cpu_resp_addr[1] !== 32'h0120_0040 ||
      cpu_resp_write[0] || cpu_resp_write[1])
    $fatal(1, "dual-cold-miss response metadata was misrouted");

  // Predict both independent fills before either response is consumed, so the
  // global MESI/data checker sees the full architectural state.
  state_model_apply_cpu(0, 32'h0120_0000, 1'b0);
  state_model_apply_cpu(1, 32'h0120_0040, 1'b0);
  @(negedge clock);
  cpu_resp_ready[0] = 1'b1;
  cpu_response_only(0, 32'h0120_0000, 1'b0, 8'h00, 64'b0,
                    xfer_response0);
  @(negedge clock);
  cpu_resp_ready[0] = 1'b0;
  cpu_resp_ready[1] = 1'b1;
  cpu_response_only(1, 32'h0120_0040, 1'b0, 8'h00, 64'b0,
                    xfer_response1);
  @(negedge clock);
  cpu_resp_ready[0] = 1'b1;
  cpu_resp_ready[1] = 1'b1;
  stall_mem_rd_req = 1'b0;
  state_model_check_all();
  $display("PASS: Main Top dual-cold-miss held Directory transfer payload stable and accepted it once; addr=%08x txn=%0d context=%0d",
           locked_xfer_addr, locked_xfer_txn, locked_xfer_context);
end
