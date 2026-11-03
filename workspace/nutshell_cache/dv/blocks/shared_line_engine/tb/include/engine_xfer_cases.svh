  task automatic complete_xfer;
    begin
      @(negedge clock);
      dir_xfer_done_valid = 1'b1;
      dir_xfer_done_ready = 1'b1;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_IDLE)
        $fatal(1, "accepted transfer completion did not return engine to idle");
      @(negedge clock);
      dir_xfer_done_valid = 1'b0;
    end
  endtask

  task automatic test_refill_hit_and_cold_miss;
    begin
      @(negedge clock);
      dir_xfer_start_valid = 1'b1;
      dir_xfer_start_ready = 1'b1;
      dir_xfer_kind = XFER_L2_REFILL;
      dir_xfer_addr = 32'h0000_5103;
      dir_xfer_txn_id = TXN_ID_WIDTH'(1);
      l2_lookup_hit = 1'b1;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_XFER_DONE || engine_addr_q !== 32'h0000_5100)
        $fatal(1, "L2 refill hit did not latch aligned address and complete");
      @(negedge clock);
      dir_xfer_start_valid = 1'b0;
      l2_lookup_hit = 1'b0;
      complete_xfer();

      @(negedge clock);
      dir_xfer_start_valid = 1'b1;
      dir_xfer_kind = XFER_L2_REFILL;
      dir_xfer_addr = 32'h0000_6107;
      dir_xfer_txn_id = TXN_ID_WIDTH'(2);
      l2_alloc_victim_valid = 1'b0;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_MEM_REQ)
        $fatal(1, "cold L2 refill did not request memory when there was no victim");
      @(negedge clock);
      dir_xfer_start_valid = 1'b0;
      finish_refill_request();
      $display("PASS: L2 refill hit completes and cold miss requests backing memory");
    end
  endtask

  task automatic test_clean_invalid_victim;
    begin
      start_refill_with_victim(DIR_I, 2'b00, 1'b0, 1'b0, TXN_ID_WIDTH'(3));
      if (engine_state_q !== ENGINE_VICTIM_INVALIDATE)
        $fatal(1, "clean invalid victim did not bypass read/writeback and invalidate");
      l2_entry_invalidate_valid = 1'b1;
      l2_entry_invalidate_ready = 1'b1;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_MEM_REQ)
        $fatal(1, "invalid victim acceptance did not release refill request");
      @(negedge clock);
      l2_entry_invalidate_valid = 1'b0;
      finish_refill_request();
      $display("PASS: clean invalid L2 victim is reclaimed without dirty writeback");
    end
  endtask

  task automatic test_putm_stream;
    begin
      @(negedge clock);
      dir_xfer_start_valid = 1'b1;
      dir_xfer_start_ready = 1'b1;
      dir_xfer_kind = XFER_PUTM_TO_L2;
      dir_xfer_addr = 32'h0000_7207;
      dir_xfer_src = 1'b1;
      dir_xfer_txn_id = TXN_ID_WIDTH'(4);
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_PUTM_STREAM || !engine_src_q)
        $fatal(1, "PutM did not enter stream with the source core latched");
      @(negedge clock);
      dir_xfer_start_valid = 1'b0;
      l2_line_wr_valid = 1'b1;
      l2_line_wr_ready = 1'b0;
      l2_line_wr_beat_idx = 3'd0;
      l2_line_wr_last = 1'b0;
      repeat (2) begin
        @(posedge clock);
        #1;
        if (engine_state_q !== ENGINE_PUTM_STREAM ||
            mem_expected_beat_q !== 3'd0 || memory_adapter_protocol_error)
          $fatal(1, "PutM write backpressure lost stream ownership or beat state");
      end
      @(negedge clock);
      l2_line_wr_ready = 1'b1;
      for (integer beat = 0; beat < 8; beat = beat + 1) begin
        l2_line_wr_beat_idx = 3'(beat);
        l2_line_wr_last = (beat == 7);
        @(posedge clock);
        #1;
        if (memory_adapter_protocol_error)
          $fatal(1, "legal PutM beat %0d was rejected", beat);
        @(negedge clock);
      end
      l2_line_wr_valid = 1'b0;
      if (engine_state_q !== ENGINE_XFER_DONE)
        $fatal(1, "final PutM beat did not report transfer complete");
      complete_xfer();
      $display("PASS: PutM forwards one ordered eight-beat line and completes once");
    end
  endtask

  task automatic test_putm_malformed_beat;
    begin
      @(negedge clock);
      dir_xfer_start_valid = 1'b1;
      dir_xfer_start_ready = 1'b1;
      dir_xfer_kind = XFER_PUTM_TO_L2;
      dir_xfer_txn_id = TXN_ID_WIDTH'(7);
      @(posedge clock);
      #1;
      @(negedge clock);
      dir_xfer_start_valid = 1'b0;
      l2_line_wr_valid = 1'b1;
      l2_line_wr_ready = 1'b1;
      l2_line_wr_beat_idx = 3'd1;
      l2_line_wr_last = 1'b0;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_ERROR || !memory_adapter_protocol_error)
        $fatal(1, "skipped PutM beat did not fail-stop");
      $display("PASS: PutM skipped beat is rejected");
    end
  endtask
