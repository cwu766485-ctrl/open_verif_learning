  task automatic test_grant_read_backpressure;
    integer beat;
    begin
      @(negedge clock);
      dir_grant_valid = 1'b1;
      dir_grant_ready = 1'b1;
      dir_grant_dst = 1'b1;
      dir_grant_has_data = 1'b1;
      dir_grant_addr = 32'h0000_8247;
      dir_grant_txn_id = TXN_ID_WIDTH'(6);
      l2_line_rd_valid = 1'b1;
      l2_line_rd_ready = 1'b0;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_GRANT_READ || grant_addr_q !== 32'h0000_8240 ||
          grant_txn_q !== TXN_ID_WIDTH'(6) || !grant_dst_q)
        $fatal(1, "accepted grant did not latch into ENGINE_GRANT_READ");
      repeat (3) begin
        @(posedge clock);
        #1;
        if (engine_state_q !== ENGINE_GRANT_READ || memory_adapter_protocol_error)
          $fatal(1, "L2 read stall did not preserve grant-read state");
      end
      @(negedge clock);
      dir_grant_valid = 1'b0;
      l2_line_rd_ready = 1'b1;
      l2_line_rd_hit = 1'b1;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_GRANT_STREAM)
        $fatal(1, "accepted L2 hit did not enter grant stream");
      @(negedge clock);
      l2_line_rd_valid = 1'b0;
      l2_line_data_valid = 1'b1;
      l2_line_data_ready = 1'b1;
      for (beat = 0; beat < 8; beat = beat + 1) begin
        @(negedge clock);
        l2_line_data_last = (beat == 7);
        @(posedge clock);
        #1;
        if (memory_adapter_protocol_error)
          $fatal(1, "grant stream raised protocol error at beat %0d", beat);
        if ((beat < 7 && engine_state_q !== ENGINE_GRANT_STREAM) ||
            (beat == 7 && engine_state_q !== ENGINE_IDLE))
          $fatal(1, "grant stream retired at wrong beat %0d (state=%0d)", beat, engine_state_q);
      end
      @(negedge clock);
      l2_line_data_valid = 1'b0;
      l2_line_data_last = 1'b0;
      $display("PASS: grant read backpressure holds state and retires after eight accepted beats");
    end
  endtask

  task automatic test_grant_read_miss_fault;
    begin
      @(negedge clock);
      dir_grant_valid = 1'b1;
      dir_grant_ready = 1'b1;
      dir_grant_has_data = 1'b1;
      dir_grant_addr = 32'h0000_8247;
      dir_grant_txn_id = TXN_ID_WIDTH'(6);
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_GRANT_READ)
        $fatal(1, "grant with no immediate L2 read acceptance did not wait");

      @(negedge clock);
      dir_grant_valid = 1'b0;
      l2_line_rd_valid = 1'b1;
      l2_line_rd_ready = 1'b1;
      l2_line_rd_hit = 1'b0;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_ERROR || !memory_adapter_protocol_error)
        $fatal(1, "L2 miss after accepted data grant did not fail-stop");
      $display("PASS: grant read L2 miss is rejected as a protocol error");
    end
  endtask

  task automatic test_grant_immediate_l2_hit;
    begin
      @(negedge clock);
      dir_grant_valid = 1'b1;
      dir_grant_ready = 1'b1;
      dir_grant_has_data = 1'b1;
      dir_grant_addr = 32'h0000_9157;
      dir_grant_txn_id = TXN_ID_WIDTH'(9);
      l2_line_rd_valid = 1'b1;
      l2_line_rd_ready = 1'b1;
      l2_line_rd_hit = 1'b1;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_GRANT_STREAM || grant_addr_q !== 32'h0000_9140)
        $fatal(1, "same-cycle grant/L2 hit did not enter grant stream");
      @(negedge clock);
      dir_grant_valid = 1'b0;
      l2_line_rd_valid = 1'b0;
      l2_line_data_valid = 1'b1;
      l2_line_data_ready = 1'b1;
      l2_line_data_last = 1'b0;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_GRANT_STREAM)
        $fatal(1, "non-final grant data beat retired the stream");
      @(negedge clock);
      l2_line_data_last = 1'b1;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_IDLE || memory_adapter_protocol_error)
        $fatal(1, "final grant data beat did not retire cleanly");
      $display("PASS: immediate L2 hit enters grant stream and waits for final data beat");
    end
  endtask

  task automatic test_grant_immediate_l2_miss_fault;
    begin
      @(negedge clock);
      dir_grant_valid = 1'b1;
      dir_grant_ready = 1'b1;
      dir_grant_has_data = 1'b1;
      l2_line_rd_valid = 1'b1;
      l2_line_rd_ready = 1'b1;
      l2_line_rd_hit = 1'b0;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_ERROR || !memory_adapter_protocol_error)
        $fatal(1, "same-cycle grant/L2 miss did not fail-stop");
      $display("PASS: immediate L2 miss after grant is rejected");
    end
  endtask
