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

    // Beat 7 without Last is a distinct malformed transfer: the beat index
    // is in range, but the line is incomplete. Exercise the explicit final-
    // beat rejection arm (rather than only the out-of-order-index arm above).
    @(negedge clock); reset = 1; repeat (2) tick();
    @(negedge clock); reset = 0;
    cpu_req_valid = 1; cpu_req_addr = 32'h4000_0100;
    cpu_req_write = 0; cpu_req_hit = 0; cpu_req_line_state = MESI_I;
    tick(); @(negedge clock); cpu_req_valid = 0;
    dir_req_ready = 1; tick(); @(negedge clock); dir_req_ready = 0;
    grant_valid = 1; grant_txn_id = dir_req_txn_id; grant_opcode = GRANT_DATA_S;
    tick(); @(negedge clock); grant_valid = 0;
    refill_ready = 1; grant_data_valid = 1;
    grant_data_txn_id = grant_txn_id;
    for (integer beat = 0; beat < 7; beat++) begin
      grant_data_beat_idx = 3'(beat); grant_data_last = 0;
      #1; if (!grant_data_ready) $fatal(1, "legal refill prefix rejected");
      tick(); @(negedge clock);
      if (protocol_error) $fatal(1, "legal refill prefix raised error");
    end
    grant_data_beat_idx = 7;
    grant_data = 64'h7; grant_data_last = 0;
    #1; if (!grant_data_ready) $fatal(1, "beat-7 missing-Last refill was not accepted");
    tick(); @(negedge clock); grant_data_valid = 0; refill_ready = 0;
    if (!protocol_error || cpu_resp_valid || monitor_cpu_state != 3'd6)
      $fatal(1, "beat-7 missing-Last refill did not enter CPU error state");

    // Exercise the corresponding snoop-data boundary independently. A final
    // beat without Last must not produce a successful SnoopData response.
    @(negedge clock); reset = 1; repeat (2) tick();
    @(negedge clock); reset = 0;
    snoop_valid = 1; snoop_line_addr = 32'h4000_0200;
    snoop_opcode = SNOOP_READ; snoop_txn_id = 9;
    snoop_tag_hit = 1; snoop_line_state = MESI_M; #1;
    if (!snoop_ready) $fatal(1, "malformed-beat SnoopRead was not accepted");
    tick(); @(negedge clock); snoop_valid = 0;
    snoop_line_rd_ready = 1; snoop_line_rd_hit = 1;
    tick(); @(negedge clock); snoop_line_rd_ready = 0;
    snoop_data_ready = 1; snoop_array_data_valid = 1;
    for (integer beat = 0; beat < 7; beat++) begin
      snoop_array_beat_idx = 3'(beat); snoop_array_last = 0;
      #1; if (!snoop_array_data_ready) $fatal(1, "legal snoop prefix rejected");
      tick(); @(negedge clock);
      if (protocol_error) $fatal(1, "legal snoop prefix raised error");
    end
    snoop_array_beat_idx = 7; snoop_array_data = 64'h9; snoop_array_last = 0;
    #1; if (!snoop_array_data_ready || !snoop_data_valid)
      $fatal(1, "beat-7 missing-Last snoop beat was not accepted");
    tick(); @(negedge clock); snoop_array_data_valid = 0; snoop_data_ready = 0;
    if (!protocol_error || monitor_snoop_state != 3'd5 || snoop_rsp_valid)
      $fatal(1, "beat-7 missing-Last snoop did not fail-stop");
    $display("PASS MesiL1Controller_tb");
    $finish;
  end
