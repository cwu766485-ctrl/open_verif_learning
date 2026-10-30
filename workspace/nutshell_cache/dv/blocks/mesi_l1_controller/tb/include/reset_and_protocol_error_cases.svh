    // Reset while a refill beat is stalled cancels the CPU transaction.
    cpu_req_valid = 1; cpu_req_addr = 32'h2900_0000;
    cpu_req_write = 0; cpu_req_hit = 0; cpu_req_line_state = MESI_I;
    tick(); @(negedge clock); cpu_req_valid = 0;
    dir_req_ready = 1; tick(); @(negedge clock); dir_req_ready = 0;
    grant_valid = 1; grant_txn_id = dir_req_txn_id; grant_opcode = GRANT_DATA_S;
    tick(); @(negedge clock); grant_valid = 0;
    grant_data_valid = 1; grant_data_txn_id = grant_txn_id;
    grant_data_beat_idx = 0; grant_data = 64'h1; grant_data_last = 0;
    refill_ready = 0; #1;
    if (!refill_valid || grant_data_ready)
      $fatal(1, "reset test did not reach a stalled refill");
    @(negedge clock); grant_data_valid = 0; reset = 1; tick();
    @(negedge clock); reset = 0;
    if (cpu_resp_valid || dir_req_valid || protocol_error)
      $fatal(1, "reset left stale L1 transaction state");

    if (protocol_error) $fatal(1, "unexpected L1 controller protocol_error");

    // Reset and inject an out-of-order refill beat. It must fail-stop the
    // controller instead of returning a successful CPU response.
    @(negedge clock); reset = 1; repeat (2) tick();
    @(negedge clock); reset = 0;
    cpu_req_valid = 1; cpu_req_addr = 32'h4000_0080;
    cpu_req_write = 0; cpu_req_hit = 0;
    tick(); @(negedge clock); cpu_req_valid = 0;
    dir_req_ready = 1; tick(); @(negedge clock); dir_req_ready = 0;
    grant_valid = 1; grant_txn_id = dir_req_txn_id; grant_opcode = GRANT_DATA_S;
    tick(); @(negedge clock); grant_valid = 0;
    refill_ready = 1; grant_data_valid = 1;
    grant_data_txn_id = grant_txn_id; grant_data_beat_idx = 1;
    grant_data = 64'h1; grant_data_last = 0;
    #1; if (!grant_data_ready) $fatal(1, "malformed refill beat was not accepted");
    tick(); @(negedge clock); grant_data_valid = 0; refill_ready = 0;
    if (!protocol_error || cpu_resp_valid)
      $fatal(1, "malformed refill did not fail-stop without CPU success");
    $display("PASS MesiL1Controller_tb");
    $finish;
  end
