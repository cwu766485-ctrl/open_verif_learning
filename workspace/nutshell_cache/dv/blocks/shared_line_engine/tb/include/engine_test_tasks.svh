  task automatic initialize_inputs;
    begin
      reset = 1'b0;
      mem_r_protocol_bad = 1'b0;
      mem_rd_data_valid = 1'b0;
      mem_rd_data_ready = 1'b0;
      mem_rd_data_error = 1'b0;
      mem_mshr_r_match = 1'b0;
      mem_wr_rsp_valid = 1'b0;
      mem_wr_rsp_ready = 1'b0;
      mem_wr_rsp_txn_id = '0;
      mem_wr_rsp_error = 1'b0;
      dir_xfer_start_valid = 1'b0;
      dir_xfer_start_ready = 1'b0;
      dir_xfer_kind = XFER_L2_REFILL;
      dir_xfer_addr = '0;
      dir_xfer_src = 1'b0;
      dir_xfer_txn_id = '0;
      dir_xfer_context_id = '0;
      dir_xfer_done_valid = 1'b0;
      dir_xfer_done_ready = 1'b0;
      dir_grant_valid = 1'b0;
      dir_grant_ready = 1'b0;
      dir_grant_dst = 1'b0;
      dir_grant_has_data = 1'b0;
      dir_grant_addr = '0;
      dir_grant_txn_id = '0;
      l2_lookup_hit = 1'b0;
      l2_alloc_victim_valid = 1'b0;
      l2_alloc_victim_addr = '0;
      l2_alloc_victim_dirty = 1'b0;
      l2_alloc_victim_state = DIR_I;
      l2_alloc_victim_sharers = '0;
      l2_alloc_victim_owner = 1'b0;
      l2_line_rd_valid = 1'b0;
      l2_line_rd_ready = 1'b0;
      l2_line_rd_hit = 1'b0;
      l2_line_data_valid = 1'b0;
      l2_line_data_ready = 1'b0;
      l2_line_data_last = 1'b0;
      l2_line_wr_valid = 1'b0;
      l2_line_wr_ready = 1'b0;
      l2_line_wr_beat_idx = '0;
      l2_line_wr_last = 1'b0;
      l2_entry_invalidate_valid = 1'b0;
      l2_entry_invalidate_ready = 1'b0;
      l2_mark_clean_valid = 1'b0;
      l2_mark_clean_ready = 1'b0;
      l2_dir_write_ready = 1'b0;
      mem_rd_req_valid = 1'b0;
      mem_rd_req_ready = 1'b0;
      mem_wr_req_valid = 1'b0;
      mem_wr_req_ready = 1'b0;
      mem_wr_data_valid = 1'b0;
      mem_wr_data_ready = 1'b0;
      mem_wr_data_beat_idx = '0;
      mem_wr_data_last = 1'b0;
      for (integer core = 0; core < 2; core = core + 1) begin
        snoop_valid_core[core] = 1'b0;
        snoop_ready_core[core] = 1'b0;
        snoop_rsp_has_data_core[core] = 1'b0;
        snoop_rsp_txn_id_core[core] = '0;
        snoop_rsp_opcode_core[core] = SNOOP_RSP_INV_ACK;
        snoop_data_txn_id_core[core] = '0;
      end
      victim_snoop_data_to_l2 = 1'b0;
      victim_snoop_rsp_fire = 1'b0;
      victim_targets_after_current = '0;
      victim_owner_retired_before_snoop = 1'b0;
    end
  endtask

  task automatic reset_dut;
    begin
      @(negedge clock);
      initialize_inputs();
      reset = 1'b1;
      repeat (2) @(posedge clock);
      @(negedge clock);
      reset = 1'b0;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_IDLE || memory_adapter_protocol_error ||
          memory_adapter_error)
        $fatal(1, "reset did not clear engine state and error status");
    end
  endtask

  task automatic start_refill_with_victim(
    input directory_state_t victim_state,
    input logic [1:0] victim_sharers,
    input logic victim_owner,
    input logic victim_dirty,
    input logic [TXN_ID_WIDTH-1:0] txn_id
  );
    begin
      @(negedge clock);
      dir_xfer_start_valid = 1'b1;
      dir_xfer_start_ready = 1'b1;
      dir_xfer_kind = XFER_L2_REFILL;
      dir_xfer_addr = 32'h0000_A347;
      dir_xfer_txn_id = txn_id;
      dir_xfer_context_id = 2'd2;
      l2_alloc_victim_valid = 1'b1;
      l2_alloc_victim_addr = 32'h0000_1380;
      l2_alloc_victim_state = victim_state;
      l2_alloc_victim_sharers = victim_sharers;
      l2_alloc_victim_owner = victim_owner;
      l2_alloc_victim_dirty = victim_dirty;
      @(posedge clock);
      #1;
      @(negedge clock);
      dir_xfer_start_valid = 1'b0;
      l2_alloc_victim_valid = 1'b0;
    end
  endtask

  task automatic finish_refill_request;
    begin
      @(negedge clock);
      mem_rd_req_valid = 1'b1;
      mem_rd_req_ready = 1'b1;
      @(posedge clock);
      #1;
      if (engine_state_q !== ENGINE_IDLE)
        $fatal(1, "accepted backing-memory read did not retire refill request");
      @(negedge clock);
      mem_rd_req_valid = 1'b0;
    end
  endtask
