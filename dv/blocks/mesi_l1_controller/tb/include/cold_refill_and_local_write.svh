    // E-state store is a local metadata transition; no Directory request.
    cpu_req_valid = 1; cpu_req_addr = 32'h1234_1048;
    cpu_req_write = 1; cpu_req_hit = 1; cpu_req_line_state = MESI_E;
    #1; if (!cpu_req_ready) $fatal(1, "E-store request not accepted");
    tick(); @(negedge clock); cpu_req_valid = 0;
    if (!cpu_meta_write_valid || cpu_meta_write_state != MESI_M ||
        cpu_meta_write_line_addr != 32'h1234_1040)
      $fatal(1, "E-to-M metadata update mismatch");
    cpu_meta_write_ready = 1; tick(); @(negedge clock);
    cpu_meta_write_ready = 0;
    if (!cpu_resp_valid || cpu_resp_addr != 32'h1234_1048 || !cpu_resp_write)
      $fatal(1, "E-store response missing");
    cpu_resp_ready = 1; tick(); @(negedge clock); cpu_resp_ready = 0;

    // A read miss gets Shared permission after all eight refill beats.
    cpu_req_valid = 1; cpu_req_addr = 32'h2000_1018;
    cpu_req_write = 0; cpu_req_hit = 0; cpu_req_line_state = MESI_I;
    #1; if (!cpu_req_ready) $fatal(1, "miss request not accepted");
    tick(); @(negedge clock); cpu_req_valid = 0;
    if (!dir_req_valid || dir_req_opcode != REQ_GETS ||
        dir_req_line_addr != 32'h2000_1000)
      $fatal(1, "read miss Directory request mismatch");
    dir_req_ready = 1; tick(); @(negedge clock); dir_req_ready = 0;
    grant_valid = 1; grant_txn_id = dir_req_txn_id; grant_opcode = GRANT_DATA_S;
    #1; if (!grant_ready) $fatal(1, "matching grant not accepted");
    tick(); @(negedge clock); grant_valid = 0;
    refill_ready = 1;
    for (int beat = 0; beat < 8; beat++) begin
      grant_data_valid = 1; grant_data_txn_id = grant_txn_id;
      grant_data_beat_idx = beat[2:0];
      grant_data = 64'h5000_0000_0000_0000 + 64'(beat);
      grant_data_last = (beat == 7); #1;
      if (!grant_data_ready || !refill_valid || refill_beat_idx != beat[2:0])
        $fatal(1, "refill beat %0d was not forwarded", beat);
      tick(); @(negedge clock);
    end
    grant_data_valid = 0; grant_data_last = 0; refill_ready = 0;
    if (!cpu_meta_write_valid || cpu_meta_write_state != MESI_S)
      $fatal(1, "refill completion did not request metadata update");
    cpu_meta_write_ready = 1; tick(); @(negedge clock); cpu_meta_write_ready = 0;
    if (!cpu_resp_valid || !grant_commit_valid ||
        cpu_resp_addr != 32'h2000_1018 || cpu_resp_write)
      $fatal(1, "read miss response/commit missing");
    cpu_resp_ready = 1; grant_commit_ready = 1;
    tick(); @(negedge clock); cpu_resp_ready = 0; grant_commit_ready = 0;
