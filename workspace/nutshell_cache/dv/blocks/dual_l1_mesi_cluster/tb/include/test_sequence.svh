  initial begin
    reset = 1'b1;
    dir_req_ready_from_directory = 1'b1;
    grant_valid_drive = 2'b00;
    grant_data_valid_drive = 2'b00;
    grant_opcode_drive = '0;
    grant_txn_id_drive = '0;
    grant_data_txn_id_drive = '0;
    grant_data_beat_idx_drive = '0;
    grant_data_drive = '0;
    grant_data_last_drive = '0;
    first_txn = '0;
    second_txn = '0;
    for (core = 0; core < 2; core = core + 1) begin
      cpu_req_valid[core] = 1'b0;
      cpu_req_addr[core] = '0;
      cpu_req_write[core] = 1'b0;
      cpu_req_wmask[core] = 8'hFF;
      cpu_req_wdata[core] = '0;
      cpu_resp_ready[core] = 1'b1;
      put_xfer_start[core] = 1'b0;
      put_xfer_addr[core] = '0;
      put_xfer_txn_id[core] = '0;
      put_data_ready[core] = 1'b1;
      grant_commit_ready[core] = 1'b1;
      snoop_valid[core] = 1'b0;
      snoop_line_addr[core] = '0;
      snoop_opcode[core] = SNOOP_READ;
      snoop_txn_id[core] = '0;
      snoop_rsp_ready[core] = 1'b1;
      snoop_data_ready[core] = 1'b1;
    end

    tick();
    tick();
    reset = 1'b0;

    // Submit two independent misses together. The reset round-robin preference
    // must route core 0 first, and core 1 must remain pending until the mock
    // Directory accepts another request.
    cpu_req_addr[0] = 32'h0000_1018;
    cpu_req_addr[1] = 32'h0000_2028;
    cpu_req_valid[0] = 1'b1;
    cpu_req_valid[1] = 1'b1;
    #1;
    if (!cpu_req_ready[0] || !cpu_req_ready[1] ||
        !cpu_miss_event[0] || !cpu_miss_event[1] ||
        cpu_hit_event[0] || cpu_hit_event[1])
      $fatal(1, "both idle L1 request ports should accept independent misses");
    tick();
    cpu_req_valid[0] = 1'b0;
    cpu_req_valid[1] = 1'b0;

    timeout = 0;
    while (!dir_req_valid && timeout < 20) begin
      tick();
      timeout = timeout + 1;
    end
    if (!dir_req_valid || dir_req_src_id != 1'b0 ||
        dir_req_opcode != REQ_GETS || dir_req_line_addr != 32'h0000_1000)
      $fatal(1, "first clustered miss was not routed from core 0");
    first_txn = dir_req_txn_id;
    tick();
    dir_req_ready_from_directory = 1'b0;
    complete_read_refill(1'b0, 32'h0000_1018, first_txn,
                         64'hA000_0000_0000_0000);

    dir_req_ready_from_directory = 1'b1;
    timeout = 0;
    while (!dir_req_valid && timeout < 20) begin
      tick();
      timeout = timeout + 1;
    end
    if (!dir_req_valid || dir_req_src_id != 1'b1 ||
        dir_req_opcode != REQ_GETS || dir_req_line_addr != 32'h0000_2000)
      $fatal(1, "second clustered miss was not routed from core 1");
    second_txn = dir_req_txn_id;
    tick();
    dir_req_ready_from_directory = 1'b0;
    complete_read_refill(1'b1, 32'h0000_2028, second_txn,
                         64'hB000_0000_0000_0000);

    // A repeated read of a refilled line is reported as a cache hit and does
    // not issue another Directory request.
    cpu_req_addr[0] = 32'h0000_1018;
    cpu_req_valid[0] = 1'b1;
    #1;
    if (!cpu_req_ready[0] || !cpu_hit_event[0] || cpu_miss_event[0])
      $fatal(1, "refilled line was not reported as a CPU cache hit");
    tick();
    cpu_req_valid[0] = 1'b0;
    for (hit_wait = 0; hit_wait < 20 && !cpu_resp_valid[0]; hit_wait = hit_wait + 1)
      tick();
    if (!cpu_resp_valid[0] || cpu_resp_rdata[0] !=
        (64'hA000_0000_0000_0000 + 3))
      $fatal(1, "cache hit event response mismatch: valid=%b rdata=%016x expected=%016x state=%0d",
             cpu_resp_valid[0], cpu_resp_rdata[0],
             64'hA000_0000_0000_0000 + 3,
             dut.cores[0].l1_controller.cpu_state_q);
    tick();

    if (controller_protocol_error != 2'b00 || array_protocol_error != 2'b00)
      $fatal(1, "cluster raised a protocol error during independent refills");
    if (metadata_commit_seen != 2'b11)
      $fatal(1, "array metadata commit monitor missed refills: %b", metadata_commit_seen);

    $display("PASS DualL1MesiCluster_tb");
    $finish;
  end
