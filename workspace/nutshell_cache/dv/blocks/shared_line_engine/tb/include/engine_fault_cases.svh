  task automatic expect_engine_protocol_error(input string case_name);
    begin
      #1;
      if (engine_state_q !== ENGINE_ERROR || !memory_adapter_protocol_error)
        $fatal(1, "%s did not latch protocol error", case_name);
      $display("PASS: %s is rejected with protocol error", case_name);
    end
  endtask

  task automatic test_memory_protocol_faults;
    begin
      mem_r_protocol_bad = 1'b1;
      @(posedge clock);
      expect_engine_protocol_error("malformed memory R channel");
      reset_dut();

      mem_rd_data_valid = 1'b1;
      mem_rd_data_ready = 1'b1;
      mem_mshr_r_match = 1'b1;
      mem_rd_data_error = 1'b1;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_ERROR || !memory_adapter_error ||
          memory_adapter_protocol_error)
        $fatal(1, "matched memory read error was not reported as a data error");
      $display("PASS: matched memory R error fail-stops without protocol misclassification");
      reset_dut();

      mem_wr_rsp_valid = 1'b1;
      mem_wr_rsp_ready = 1'b1;
      @(posedge clock);
      expect_engine_protocol_error("write response outside an owned write transaction");
      reset_dut();

      start_refill_with_victim(DIR_I, 2'b01, 1'b0, 1'b0, TXN_ID_WIDTH'(2));
      expect_engine_protocol_error("inconsistent invalid-victim directory metadata");
    end
  endtask

  task automatic test_dirty_writeback_faults;
    begin
      reset_dut();
      enter_dirty_victim_write_stream();
      send_memory_write_beats(1'b1);
      expect_engine_protocol_error("skipped memory write beat");

      reset_dut();
      enter_dirty_victim_write_stream();
      send_memory_write_beats(1'b0);
      if (engine_state_q !== ENGINE_VICTIM_WRITE_WAIT_RSP)
        $fatal(1, "well-formed writeback did not await response before ID fault test");
      @(negedge clock);
      mem_wr_rsp_valid = 1'b1;
      mem_wr_rsp_ready = 1'b1;
      mem_wr_rsp_txn_id = TXN_ID_WIDTH'(6);
      @(posedge clock);
      expect_engine_protocol_error("write response transaction ID mismatch");

      reset_dut();
      enter_dirty_victim_write_stream();
      send_memory_write_beats(1'b0);
      @(negedge clock);
      mem_wr_rsp_valid = 1'b1;
      mem_wr_rsp_ready = 1'b1;
      mem_wr_rsp_txn_id = TXN_ID_WIDTH'(5);
      mem_wr_rsp_error = 1'b1;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_ERROR || !memory_adapter_error ||
          memory_adapter_protocol_error)
        $fatal(1, "memory write error response was not reported as data error");
      $display("PASS: matching write ID with error status fail-stops as memory error");

      reset_dut();
      dir_xfer_start_valid = 1'b1;
      dir_xfer_start_ready = 1'b1;
      dir_xfer_kind = line_xfer_kind_t'(2'b11);
      @(posedge clock);
      expect_engine_protocol_error("unsupported line-transfer opcode");

      reset_dut();
      enter_dirty_victim_snoop_wait();
      snoop_rsp_txn_id_core[1] = TXN_ID_WIDTH'(6);
      snoop_rsp_opcode_core[1] = SNOOP_RSP_DATA;
      snoop_rsp_has_data_core[1] = 1'b1;
      victim_targets_after_current = 2'b00;
      victim_snoop_rsp_fire = 1'b1;
      @(posedge clock);
      expect_engine_protocol_error("dirty-owner snoop response transaction ID mismatch");

      reset_dut();
      enter_dirty_victim_snoop_wait();
      snoop_rsp_txn_id_core[1] = TXN_ID_WIDTH'(5);
      snoop_rsp_opcode_core[1] = SNOOP_RSP_INV_ACK;
      snoop_rsp_has_data_core[1] = 1'b0;
      victim_targets_after_current = 2'b00;
      victim_snoop_rsp_fire = 1'b1;
      @(posedge clock);
      expect_engine_protocol_error("dirty-owner no-data response");

      reset_dut();
      enter_dirty_victim_snoop_wait();
      victim_snoop_data_to_l2 = 1'b1;
      l2_line_wr_valid = 1'b1;
      l2_line_wr_ready = 1'b1;
      l2_line_wr_beat_idx = 3'd1;
      l2_line_wr_last = 1'b0;
      @(posedge clock);
      expect_engine_protocol_error("owner data beat index mismatch");

      reset_dut();
      enter_dirty_victim_snoop_wait();
      victim_snoop_data_to_l2 = 1'b1;
      l2_line_wr_valid = 1'b1;
      l2_line_wr_ready = 1'b1;
      l2_line_wr_beat_idx = 3'd0;
      l2_line_wr_last = 1'b1;
      @(posedge clock);
      expect_engine_protocol_error("owner data early last marker");

      reset_dut();
      enter_dirty_victim_snoop_wait();
      victim_snoop_data_to_l2 = 1'b1;
      l2_line_wr_valid = 1'b1;
      l2_line_wr_ready = 1'b1;
      l2_line_wr_beat_idx = 3'd0;
      l2_line_wr_last = 1'b0;
      snoop_data_txn_id_core[1] = TXN_ID_WIDTH'(6);
      @(posedge clock);
      expect_engine_protocol_error("owner data transaction ID mismatch");
    end
  endtask
