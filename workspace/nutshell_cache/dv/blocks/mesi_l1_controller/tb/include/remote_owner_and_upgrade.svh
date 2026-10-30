    // An M owner supplies the full line on a remote read, changes to S, then
    // returns the matching data response after its metadata update.
    snoop_valid = 1; snoop_line_addr = 32'h2000_1000;
    snoop_opcode = SNOOP_READ; snoop_txn_id = 4;
    snoop_tag_hit = 1; snoop_line_state = MESI_M;
    #1; if (!snoop_ready) $fatal(1, "Snoop not accepted while CPU idle");
    tick(); @(negedge clock); snoop_valid = 0;
    if (!snoop_line_rd_valid || snoop_line_rd_addr != 32'h2000_1000)
      $fatal(1, "M-line data read was not requested");
    snoop_line_rd_ready = 1; tick(); @(negedge clock); snoop_line_rd_ready = 0;
    snoop_data_ready = 1;
    for (int beat = 0; beat < 8; beat++) begin
      snoop_array_data_valid = 1; snoop_array_beat_idx = beat[2:0];
      snoop_array_data = 64'h6000_0000_0000_0000 + 64'(beat);
      snoop_array_last = (beat == 7); #1;
      if (!snoop_data_valid || !snoop_array_data_ready ||
          snoop_data_txn_id != 4 || snoop_data_beat_idx != beat[2:0] ||
          snoop_data_last != (beat == 7))
        $fatal(1, "SnoopData beat %0d mismatch", beat);
      tick(); @(negedge clock);
    end
    snoop_array_data_valid = 0; snoop_array_last = 0; snoop_data_ready = 0;
    if (!snoop_meta_write_valid || snoop_meta_write_state != MESI_S)
      $fatal(1, "M-to-S Snoop metadata update missing");
    snoop_meta_write_ready = 1; tick(); @(negedge clock);
    snoop_meta_write_ready = 0;
    if (!snoop_rsp_valid || snoop_rsp_opcode != SNOOP_RSP_DATA ||
        !snoop_rsp_has_data || snoop_rsp_txn_id != 4)
      $fatal(1, "Snoop response header mismatch");
    snoop_rsp_ready = 1; tick(); @(negedge clock); snoop_rsp_ready = 0;

    // An S hit write issues Upgrade. The Directory request and local metadata
    // commit must remain stable under backpressure; a wrong grant ID is ignored.
    cpu_req_valid = 1; cpu_req_addr = 32'h2000_1018;
    cpu_req_write = 1; cpu_req_hit = 1; cpu_req_line_state = MESI_S;
    #1; if (!cpu_req_ready) $fatal(1, "S write request not accepted");
    tick(); @(negedge clock); cpu_req_valid = 0;
    if (!dir_req_valid || dir_req_opcode != REQ_UPGRADE ||
        dir_req_line_addr != 32'h2000_1000)
      $fatal(1, "S hit write did not issue Upgrade");
    repeat (2) begin tick(); #1;
      if (!dir_req_valid || dir_req_opcode != REQ_UPGRADE ||
          dir_req_txn_id != 2)
        $fatal(1, "Upgrade request changed under Directory backpressure");
    end
    @(negedge clock); dir_req_ready = 1; tick(); @(negedge clock);
    dir_req_ready = 0; grant_valid = 1; grant_opcode = GRANT_M;
    grant_txn_id = dir_req_txn_id + 1'b1; #1;
    if (grant_ready) $fatal(1, "wrong-ID grant was accepted");
    repeat (2) tick();
    @(negedge clock); grant_txn_id = dir_req_txn_id; #1;
    if (!grant_ready) $fatal(1, "matching Upgrade grant was not accepted");
    tick(); @(negedge clock); grant_valid = 0;
    if (!cpu_meta_write_valid || cpu_meta_write_state != MESI_M)
      $fatal(1, "Upgrade did not request M metadata");
    repeat (2) begin tick(); #1;
      if (!cpu_meta_write_valid || cpu_meta_write_state != MESI_M)
        $fatal(1, "CPU metadata write changed while blocked");
    end
    @(negedge clock); cpu_meta_write_ready = 1; tick(); @(negedge clock);
    cpu_meta_write_ready = 0;
    if (!cpu_resp_valid || !grant_commit_valid)
      $fatal(1, "Upgrade response/commit missing");
    repeat (2) begin tick(); #1;
      if (!cpu_resp_valid || !grant_commit_valid ||
          cpu_resp_addr != 32'h2000_1018 || cpu_resp_txn_id != 2)
        $fatal(1, "Upgrade response/commit changed under backpressure");
    end
    @(negedge clock); cpu_resp_ready = 1; grant_commit_ready = 1;
    tick(); @(negedge clock); cpu_resp_ready = 0; grant_commit_ready = 0;

    // A write miss uses GetM, ignores a stale grant ID, and holds the first
    // refill beat stable until the array accepts it.
    cpu_req_valid = 1; cpu_req_addr = 32'h2800_0028;
    cpu_req_write = 1; cpu_req_hit = 0; cpu_req_line_state = MESI_I;
    #1; if (!cpu_req_ready) $fatal(1, "GetM miss not accepted");
    tick(); @(negedge clock); cpu_req_valid = 0;
    if (!dir_req_valid || dir_req_opcode != REQ_GETM ||
        dir_req_line_addr != 32'h2800_0000)
      $fatal(1, "write miss did not issue GetM");
    repeat (2) begin tick(); #1;
      if (!dir_req_valid || dir_req_opcode != REQ_GETM)
        $fatal(1, "GetM request changed while blocked");
    end
    @(negedge clock); dir_req_ready = 1; tick(); @(negedge clock);
    dir_req_ready = 0; grant_valid = 1; grant_opcode = GRANT_DATA_M;
    grant_txn_id = dir_req_txn_id + 1'b1; #1;
    if (grant_ready) $fatal(1, "stale GetM grant ID was accepted");
    repeat (2) tick();
    @(negedge clock); grant_txn_id = dir_req_txn_id; #1;
    if (!grant_ready) $fatal(1, "matching GetM grant was not accepted");
    tick(); @(negedge clock); grant_valid = 0;
    refill_ready = 0; grant_data_valid = 1;
    grant_data_txn_id = grant_txn_id; grant_data_beat_idx = 0;
    grant_data = 64'h7100_0000_0000_0000; grant_data_last = 0; #1;
    if (grant_data_ready || !refill_valid)
      $fatal(1, "first GetM refill beat did not stall at array");
    repeat (2) begin tick(); #1;
      if (!refill_valid || refill_beat_idx != 0 ||
          refill_data != 64'h7100_0000_0000_0000)
        $fatal(1, "GetM refill payload changed under backpressure");
    end
    @(negedge clock); refill_ready = 1;
    for (int beat = 0; beat < 8; beat++) begin
      grant_data_valid = 1; grant_data_beat_idx = beat[2:0];
      grant_data = 64'h7100_0000_0000_0000 + 64'(beat);
      grant_data_last = (beat == 7); #1;
      if (!grant_data_ready || !refill_valid || refill_beat_idx != beat[2:0])
        $fatal(1, "GetM refill beat %0d was not forwarded", beat);
      tick(); @(negedge clock);
    end
    grant_data_valid = 0; grant_data_last = 0; refill_ready = 0;
    if (!cpu_meta_write_valid || cpu_meta_write_state != MESI_M)
      $fatal(1, "GetM refill did not request M metadata");
    cpu_meta_write_ready = 1; tick(); @(negedge clock); cpu_meta_write_ready = 0;
    if (!cpu_resp_valid || !grant_commit_valid || !cpu_resp_write)
      $fatal(1, "GetM CPU response/grant commit missing");
    cpu_resp_ready = 1; grant_commit_ready = 1;
    tick(); @(negedge clock); cpu_resp_ready = 0; grant_commit_ready = 0;
