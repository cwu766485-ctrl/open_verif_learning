
    // SnoopInvalidate of M returns all line beats, invalidates metadata, and
    // holds both the metadata update and response header until accepted.
    snoop_valid = 1; snoop_line_addr = 32'h2800_0000;
    snoop_opcode = SNOOP_INVALIDATE; snoop_txn_id = 5;
    snoop_tag_hit = 1; snoop_line_state = MESI_M; #1;
    if (!snoop_ready) $fatal(1, "M SnoopInvalidate not accepted");
    tick(); @(negedge clock); snoop_valid = 0;
    if (!snoop_line_rd_valid) $fatal(1, "M invalidation did not request line data");
    repeat (2) begin tick(); #1;
      if (!snoop_line_rd_valid || snoop_line_rd_addr != 32'h2800_0000)
        $fatal(1, "Snoop line read changed while blocked");
    end
    @(negedge clock); snoop_line_rd_ready = 1; tick(); @(negedge clock);
    snoop_line_rd_ready = 0; snoop_data_ready = 0;
    snoop_array_data_valid = 1; snoop_array_beat_idx = 0;
    snoop_array_data = 64'h8200_0000_0000_0000; snoop_array_last = 0; #1;
    if (!snoop_data_valid || snoop_array_data_ready)
      $fatal(1, "SnoopData first beat was not held under backpressure");
    repeat (2) begin tick(); #1;
      if (!snoop_data_valid || snoop_data_beat_idx != 0 ||
          snoop_data != 64'h8200_0000_0000_0000)
        $fatal(1, "SnoopData changed under backpressure");
    end
    @(negedge clock); snoop_data_ready = 1;
    for (int beat = 0; beat < 8; beat++) begin
      snoop_array_data_valid = 1; snoop_array_beat_idx = beat[2:0];
      snoop_array_data = 64'h8200_0000_0000_0000 + 64'(beat);
      snoop_array_last = (beat == 7); #1;
      if (!snoop_data_valid || !snoop_array_data_ready ||
          snoop_data_beat_idx != beat[2:0] || snoop_data_last != (beat == 7))
        $fatal(1, "SnoopInvalidate data beat %0d mismatch", beat);
      tick(); @(negedge clock);
    end
    snoop_array_data_valid = 0; snoop_array_last = 0; snoop_data_ready = 0;
    if (!snoop_meta_write_valid || snoop_meta_write_state != MESI_I)
      $fatal(1, "M SnoopInvalidate did not invalidate metadata");
    repeat (2) begin tick(); #1;
      if (!snoop_meta_write_valid || snoop_meta_write_state != MESI_I)
        $fatal(1, "Snoop invalidation metadata changed under backpressure");
    end
    @(negedge clock); snoop_meta_write_ready = 1; tick(); @(negedge clock);
    snoop_meta_write_ready = 0;
    if (!snoop_rsp_valid || snoop_rsp_opcode != SNOOP_RSP_DATA ||
        !snoop_rsp_has_data || snoop_rsp_txn_id != 5)
      $fatal(1, "M SnoopInvalidate response mismatch");
    repeat (2) begin tick(); #1;
      if (!snoop_rsp_valid || snoop_rsp_opcode != SNOOP_RSP_DATA ||
          snoop_rsp_txn_id != 5)
        $fatal(1, "Snoop response changed under backpressure");
    end
    @(negedge clock); snoop_rsp_ready = 1; tick(); @(negedge clock);
    snoop_rsp_ready = 0;

    // The line was M at Snoop acceptance, but a concurrent cache metadata
    // transition removes it before the shared line-read port accepts. Return
    // a no-data ACK so Directory can retry from L2 instead of poisoning the
    // L1 protocol-error latch.
    snoop_valid = 1; snoop_line_addr = 32'h2000_2000;
    snoop_opcode = SNOOP_READ; snoop_txn_id = 7;
    snoop_tag_hit = 1; snoop_line_state = MESI_M; #1;
    if (!snoop_ready) $fatal(1, "stale SnoopRead not accepted");
    tick(); @(negedge clock); snoop_valid = 0;
    snoop_line_rd_ready = 1; snoop_line_rd_hit = 0; #1;
    if (!snoop_line_rd_valid)
      $fatal(1, "stale SnoopRead did not request line-array access");
    tick(); @(negedge clock);
    snoop_line_rd_ready = 0; snoop_line_rd_hit = 1;
    if (!snoop_rsp_valid || snoop_rsp_opcode != SNOOP_RSP_ACK ||
        snoop_rsp_has_data || snoop_rsp_txn_id != 7 || protocol_error)
      $fatal(1, "missing SnoopRead line did not return recoverable ACK");
    snoop_rsp_ready = 1; tick(); @(negedge clock); snoop_rsp_ready = 0;

    // A Shared copy invalidates without sending line data and returns InvAck.
    snoop_valid = 1; snoop_line_addr = 32'h2000_1000;
    snoop_opcode = SNOOP_INVALIDATE; snoop_txn_id = 6;
    snoop_tag_hit = 1; snoop_line_state = MESI_S; #1;
    if (!snoop_ready) $fatal(1, "S SnoopInvalidate not accepted");
    tick(); @(negedge clock); snoop_valid = 0;
    if (!snoop_meta_write_valid || snoop_meta_write_state != MESI_I)
      $fatal(1, "S invalidation did not request I metadata");
    snoop_meta_write_ready = 1; tick(); @(negedge clock);
    snoop_meta_write_ready = 0;
    if (!snoop_rsp_valid || snoop_rsp_opcode != SNOOP_RSP_INV_ACK ||
        snoop_rsp_has_data || snoop_rsp_txn_id != 6)
      $fatal(1, "S invalidation did not return InvAck");
    snoop_rsp_ready = 1; tick(); @(negedge clock); snoop_rsp_ready = 0;
