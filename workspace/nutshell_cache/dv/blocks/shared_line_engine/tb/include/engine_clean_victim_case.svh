  task automatic test_clean_shared_victim_reclaim;
    begin
      start_refill_with_victim(DIR_S, 2'b11, 1'b0, 1'b0, TXN_ID_WIDTH'(3));
      if (engine_state_q !== ENGINE_VICTIM_SNOOP_SEND ||
          victim_pending_targets_q !== 2'b11 || victim_snoop_target_q !== 1'b0)
        $fatal(1, "shared victim did not select the first recorded sharer");

      snoop_valid_core[0] = 1'b1;
      snoop_ready_core[0] = 1'b0;
      repeat (2) begin
        @(posedge clock);
        #1;
        if (engine_state_q !== ENGINE_VICTIM_SNOOP_SEND ||
            !snoop_valid_core[0] || snoop_valid_core[1])
          $fatal(1, "snoop send backpressure changed the selected target");
      end
      @(negedge clock);
      snoop_ready_core[0] = 1'b1;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_VICTIM_SNOOP_WAIT)
        $fatal(1, "accepted victim snoop did not wait for response");
      @(negedge clock);
      snoop_valid_core[0] = 1'b0;
      snoop_rsp_txn_id_core[0] = TXN_ID_WIDTH'(3);
      snoop_rsp_opcode_core[0] = SNOOP_RSP_INV_ACK;
      victim_targets_after_current = 2'b10;
      victim_snoop_rsp_fire = 1'b1;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_VICTIM_SNOOP_SEND ||
          victim_pending_targets_q !== 2'b10 || victim_snoop_target_q !== 1'b1 ||
          memory_adapter_protocol_error)
        $fatal(1, "first sharer response did not select the remaining target");

      @(negedge clock);
      victim_snoop_rsp_fire = 1'b0;
      snoop_valid_core[0] = 1'b0;
      snoop_valid_core[1] = 1'b1;
      snoop_ready_core[1] = 1'b1;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_VICTIM_SNOOP_WAIT)
        $fatal(1, "second sharer snoop was not accepted");
      @(negedge clock);
      snoop_valid_core[1] = 1'b0;
      snoop_rsp_txn_id_core[1] = TXN_ID_WIDTH'(3);
      snoop_rsp_opcode_core[1] = SNOOP_RSP_INV_ACK;
      victim_targets_after_current = 2'b00;
      victim_snoop_rsp_fire = 1'b1;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_VICTIM_CLEAR_DIR || memory_adapter_protocol_error)
        $fatal(1, "final sharer response did not advance to directory clear");

      @(negedge clock);
      victim_snoop_rsp_fire = 1'b0;
      repeat (2) begin
        @(posedge clock);
        #1;
        if (engine_state_q !== ENGINE_VICTIM_CLEAR_DIR)
          $fatal(1, "directory-clear backpressure did not hold victim transaction");
      end
      @(negedge clock);
      l2_dir_write_ready = 1'b1;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_VICTIM_INVALIDATE)
        $fatal(1, "clean shared victim did not proceed to L2 invalidation");
      @(negedge clock);
      l2_entry_invalidate_valid = 1'b1;
      l2_entry_invalidate_ready = 1'b1;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_MEM_REQ)
        $fatal(1, "accepted victim invalidation did not release refill request");
      @(negedge clock);
      l2_entry_invalidate_valid = 1'b0;
      finish_refill_request();
      if (memory_adapter_protocol_error || memory_adapter_error)
        $fatal(1, "legal clean victim reclaim raised an error");
      $display("PASS: clean shared L2 victim is snooped, directory-cleared and invalidated");
    end
  endtask
