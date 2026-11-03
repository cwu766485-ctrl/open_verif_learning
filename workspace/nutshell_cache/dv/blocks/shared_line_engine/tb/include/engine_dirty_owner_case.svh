  task automatic enter_dirty_victim_snoop_wait;
    begin
      start_refill_with_victim(DIR_U, 2'b00, 1'b1, 1'b1, TXN_ID_WIDTH'(5));
      if (engine_state_q !== ENGINE_VICTIM_SNOOP_SEND ||
          victim_pending_targets_q !== 2'b10 || victim_snoop_target_q !== 1'b1 ||
          !victim_snoop_data_expected_q)
        $fatal(1, "unique dirty victim did not target its recorded owner");

      snoop_valid_core[1] = 1'b1;
      snoop_ready_core[1] = 1'b1;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_VICTIM_SNOOP_WAIT)
        $fatal(1, "accepted dirty-owner snoop did not enter response wait");
      @(negedge clock);
      snoop_valid_core[1] = 1'b0;
      snoop_data_txn_id_core[1] = TXN_ID_WIDTH'(5);
    end
  endtask

  task automatic enter_dirty_victim_write_stream;
    begin
      enter_dirty_victim_snoop_wait();
      victim_snoop_data_to_l2 = 1'b1;
      l2_line_wr_valid = 1'b1;
      l2_line_wr_ready = 1'b1;
      for (integer beat = 0; beat < 8; beat = beat + 1) begin
        l2_line_wr_beat_idx = 3'(beat);
        l2_line_wr_last = (beat == 7);
        @(posedge clock);
        #1;
        if (engine_state_q !== ENGINE_VICTIM_SNOOP_WAIT ||
            memory_adapter_protocol_error)
          $fatal(1, "valid owner data beat %0d was rejected", beat);
        @(negedge clock);
      end
      l2_line_wr_valid = 1'b0;
      victim_snoop_data_to_l2 = 1'b0;
      snoop_rsp_txn_id_core[1] = TXN_ID_WIDTH'(5);
      snoop_rsp_opcode_core[1] = SNOOP_RSP_DATA;
      snoop_rsp_has_data_core[1] = 1'b1;
      victim_targets_after_current = 2'b00;
      victim_snoop_rsp_fire = 1'b1;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_VICTIM_CLEAR_DIR ||
          memory_adapter_protocol_error || !victim_dirty_q)
        $fatal(1, "complete dirty-owner response did not proceed to directory clear");

      @(negedge clock);
      victim_snoop_rsp_fire = 1'b0;
      l2_dir_write_ready = 1'b1;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_VICTIM_READ)
        $fatal(1, "dirty victim was not read from L2 before memory writeback");
      @(negedge clock);
      l2_line_rd_valid = 1'b1;
      l2_line_rd_ready = 1'b1;
      l2_line_rd_hit = 1'b1;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_VICTIM_WRITE_REQ)
        $fatal(1, "L2 victim read did not request backing-memory write");
      @(negedge clock);
      l2_line_rd_valid = 1'b0;
      mem_wr_req_valid = 1'b1;
      mem_wr_req_ready = 1'b1;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_VICTIM_WRITE_STREAM)
        $fatal(1, "accepted memory write request did not enter write stream");
      @(negedge clock);
      mem_wr_req_valid = 1'b0;
    end
  endtask

  task automatic send_memory_write_beats(input logic malformed_first_beat);
    begin
      mem_wr_data_valid = 1'b1;
      mem_wr_data_ready = 1'b1;
      for (integer beat = 0; beat < 8; beat = beat + 1) begin
        mem_wr_data_beat_idx = (malformed_first_beat && beat == 0) ? 3'd1 : 3'(beat);
        mem_wr_data_last = (beat == 7);
        @(posedge clock);
        #1;
        @(negedge clock);
        if (malformed_first_beat && beat == 0) begin
          mem_wr_data_valid = 1'b0;
          return;
        end
      end
      mem_wr_data_valid = 1'b0;
    end
  endtask

  task automatic finish_dirty_victim_reclaim;
    begin
      mem_wr_rsp_valid = 1'b1;
      mem_wr_rsp_ready = 1'b1;
      mem_wr_rsp_txn_id = TXN_ID_WIDTH'(5);
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_VICTIM_MARK_CLEAN ||
          memory_adapter_protocol_error || memory_adapter_error)
        $fatal(1, "matching successful write response did not retire writeback");
      @(negedge clock);
      mem_wr_rsp_valid = 1'b0;
      l2_mark_clean_valid = 1'b1;
      l2_mark_clean_ready = 1'b1;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_VICTIM_INVALIDATE)
        $fatal(1, "accepted clean mark did not proceed to invalidation");
      @(negedge clock);
      l2_mark_clean_valid = 1'b0;
      l2_entry_invalidate_valid = 1'b1;
      l2_entry_invalidate_ready = 1'b1;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_MEM_REQ)
        $fatal(1, "accepted dirty victim invalidation did not release refill");
      @(negedge clock);
      l2_entry_invalidate_valid = 1'b0;
      finish_refill_request();
      if (memory_adapter_protocol_error || memory_adapter_error)
        $fatal(1, "legal dirty-owner reclaim raised an error");
    end
  endtask

  task automatic test_dirty_owner_victim_writeback;
    begin
      enter_dirty_victim_write_stream();
      send_memory_write_beats(1'b0);
      if (engine_state_q !== ENGINE_VICTIM_WRITE_WAIT_RSP)
        $fatal(1, "eight-beat writeback did not wait for memory response");
      finish_dirty_victim_reclaim();
      $display("PASS: dirty owner data is collected, written back, then victim is reclaimed");
    end
  endtask
