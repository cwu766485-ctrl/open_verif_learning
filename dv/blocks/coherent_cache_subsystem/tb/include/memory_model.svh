  function automatic logic [63:0] memory_word(
    input logic [31:0] line_addr,
    input logic [2:0] beat
  );
    memory_word = 64'hA500_0000_0000_0000 ^
                  {32'b0, line_addr} ^ {beat, 61'b0};
  endfunction

  function automatic logic [63:0] mmio_initial_word(
    input logic [31:0] addr
  );
    mmio_initial_word = 64'h5A00_0000_0000_0000 ^ {32'b0, addr};
  endfunction

  always_comb begin
    memory_response_slot = -1;
    memory_free_slot = -1;
    memory_read_candidate = 0;
    if (memory_read_valid_held_q)
      memory_response_slot = memory_read_hold_slot_q;
    else begin
      for (integer offset = 0; offset < MODEL_SLOTS; offset = offset + 1) begin
        memory_read_candidate = (memory_read_pick_q + offset) % MODEL_SLOTS;
        if ((memory_response_slot < 0) &&
            memory_active_q[memory_read_candidate])
          memory_response_slot = memory_read_candidate;
      end
    end
    for (integer slot = 0; slot < MODEL_SLOTS; slot = slot + 1)
      if (!memory_active_q[slot] && (memory_free_slot < 0))
        memory_free_slot = slot;

    mem_rd_req_ready = !stall_mem_rd_req && (memory_free_slot >= 0) &&
                       (!inject_periodic_stalls || (cycle_count % 4 != 0));
    mem_rd_data_valid = (memory_response_slot >= 0) &&
                        (memory_read_valid_held_q ||
                         !inject_periodic_stalls || (cycle_count % 3 != 0));
    mem_rd_data_txn_id = '0;
    mem_rd_data_beat_idx = '0;
    mem_rd_data = '0;
    mem_rd_data_error = 1'b0;
    mem_rd_data_last = 1'b0;
    if (memory_response_slot >= 0) begin
      mem_rd_data_txn_id = memory_txn_q[memory_response_slot];
      mem_rd_data_beat_idx = memory_beat_q[memory_response_slot];
      mem_rd_data = memory_word(memory_line_addr_q[memory_response_slot],
                                memory_beat_q[memory_response_slot]);
      for (integer slot = 0; slot < 128; slot = slot + 1)
        if (memory_slot_valid[slot] &&
            (memory_slot_addr[slot] == memory_line_addr_q[memory_response_slot]))
          mem_rd_data = backing_store[slot][memory_beat_q[memory_response_slot]];
      mem_rd_data_error = memory_error_q[memory_response_slot] &&
                          (memory_beat_q[memory_response_slot] == 3'd0);
      mem_rd_data_last = mem_rd_data_error ||
                         (memory_beat_q[memory_response_slot] == 3'd7);
    end

    mem_wr_req_ready = !stall_mem_wr_req &&
                       (!inject_periodic_stalls || (cycle_count % 3 != 0));
    mem_wr_data_ready = !stall_mem_wr_data &&
                        (!inject_periodic_stalls || (cycle_count % 4 == 1));
    mem_wr_rsp_valid = memory_write_response_pending_q;
    mem_wr_rsp_txn_id = memory_write_response_txn_q;
    mem_wr_rsp_error = memory_write_response_error_q;
    mmio_req_ready = !stall_mmio_req && !mmio_response_valid_q &&
                     (!inject_periodic_stalls || (cycle_count % 4 != 0));
    mmio_resp_valid = mmio_response_valid_q;
    mmio_resp_rdata = mmio_response_data_q;
  end

  always_ff @(posedge clock) begin : backing_memory_model
    integer write_slot;
    integer free_read_slot;
    if (reset) begin
      memory_active_q <= '0;
      memory_read_valid_held_q <= 1'b0;
      memory_read_hold_slot_q <= 0;
      memory_read_pick_q <= 0;
      memory_write_slot_q <= '0;
      memory_write_txn_q <= '0;
      memory_write_addr_q <= '0;
      memory_write_expected_beat_q <= 0;
      memory_write_response_pending_q <= 1'b0;
      memory_write_response_txn_q <= '0;
      memory_write_response_error_q <= 1'b0;
      for (integer beat = 0; beat < 8; beat = beat + 1)
        staged_write_data_q[beat] <= '0;
      mmio_response_valid_q <= 1'b0;
      mmio_response_data_q <= '0;
      mmio_response_delay_q <= 0;
      cycle_count <= 0;
      mmio_request_count <= 0;
      memory_read_count <= 0;
      for (integer slot = 0; slot < MODEL_SLOTS; slot = slot + 1) begin
        memory_beat_q[slot] <= '0;
        memory_line_addr_q[slot] <= '0;
        memory_txn_q[slot] <= '0;
        memory_error_q[slot] <= 1'b0;
      end
    end else begin
      cycle_count <= cycle_count + 1;
      if (mmio_response_delay_q > 0)
        mmio_response_delay_q <= mmio_response_delay_q - 1;
      else if (mmio_response_delay_q == 0)
        mmio_response_delay_q <= -1;

      if (mem_rd_req_valid && mem_rd_req_ready) begin
        free_read_slot = -1;
        for (integer slot = 0; slot < MODEL_SLOTS; slot = slot + 1)
          if (!memory_active_q[slot] && (free_read_slot < 0))
            free_read_slot = slot;
        if (free_read_slot < 0)
          $fatal(1, "memory accepted a read without a free response slot");
        memory_active_q[free_read_slot] <= 1'b1;
        memory_error_q[free_read_slot] <= inject_next_mem_rd_error;
        memory_read_count <= memory_read_count + 1;
        memory_beat_q[free_read_slot] <= '0;
        memory_line_addr_q[free_read_slot] <= mem_rd_req_addr;
        memory_txn_q[free_read_slot] <= mem_rd_req_txn_id;
      end

      if (mem_rd_data_valid && mem_rd_data_ready) begin
        memory_read_valid_held_q <= 1'b0;
        memory_read_pick_q <= (memory_response_slot + 1) % MODEL_SLOTS;
        if (mem_rd_data_error || (memory_beat_q[memory_response_slot] == 3'd7)) begin
          memory_active_q[memory_response_slot] <= 1'b0;
          memory_beat_q[memory_response_slot] <= '0;
          memory_error_q[memory_response_slot] <= 1'b0;
        end else begin
          memory_beat_q[memory_response_slot] <=
            memory_beat_q[memory_response_slot] + 1'b1;
        end
      end else if (mem_rd_data_valid && !mem_rd_data_ready) begin
        memory_read_valid_held_q <= 1'b1;
        memory_read_hold_slot_q <= memory_response_slot;
      end else if (!memory_read_valid_held_q) begin
        memory_read_valid_held_q <= 1'b0;
      end

      if (mem_wr_req_valid && mem_wr_req_ready) begin
        write_slot = -1;
        for (integer slot = 0; slot < 128; slot = slot + 1) begin
          if (memory_slot_valid[slot] &&
              (memory_slot_addr[slot] == mem_wr_req_addr))
            write_slot = slot;
          else if (!memory_slot_valid[slot] && (write_slot < 0))
            write_slot = slot;
        end
        if (write_slot < 0)
          $fatal(1, "test memory backing-store table is full");
        memory_write_slot_q <= 7'(write_slot);
        memory_write_txn_q <= mem_wr_req_txn_id;
        memory_write_addr_q <= mem_wr_req_addr;
        memory_write_expected_beat_q <= 0;
      end
      if (mem_wr_data_valid && mem_wr_data_ready) begin
        if (mem_wr_data_txn_id != memory_write_txn_q)
          $fatal(1, "memory write data transaction ID changed mid-line");
        if ((mem_wr_data_beat_idx != 3'(memory_write_expected_beat_q)) ||
            (mem_wr_data_last != (memory_write_expected_beat_q == 7)))
          $fatal(1, "memory write beat sequence malformed: beat=%0d expected=%0d last=%b",
                 mem_wr_data_beat_idx, memory_write_expected_beat_q,
                 mem_wr_data_last);
        staged_write_data_q[mem_wr_data_beat_idx] <= mem_wr_data;
        if (memory_write_expected_beat_q < 7)
          memory_write_expected_beat_q <= memory_write_expected_beat_q + 1;
        if (mem_wr_data_last) begin
          if (memory_write_response_pending_q)
            $fatal(1, "memory received a second write before responding to the first");
          memory_write_response_pending_q <= 1'b1;
          memory_write_response_txn_q <= mem_wr_data_txn_id;
          memory_write_response_error_q <= inject_next_mem_wr_error;
        end
      end
      if (mem_wr_rsp_valid && mem_wr_rsp_ready) begin
        if (!mem_wr_rsp_error) begin
          memory_slot_valid[memory_write_slot_q] <= 1'b1;
          memory_slot_addr[memory_write_slot_q] <= memory_write_addr_q;
          for (integer beat = 0; beat < 8; beat = beat + 1)
            backing_store[memory_write_slot_q][beat] <= staged_write_data_q[beat];
        end
        memory_write_response_pending_q <= 1'b0;
      end

      if (mmio_response_valid_q && mmio_resp_ready)
        mmio_response_valid_q <= 1'b0;
      if (mmio_req_valid && mmio_req_ready) begin
        logic [63:0] current_word;
        logic [63:0] next_word;
        mmio_request_count <= mmio_request_count + 1;
        if (mmio_req_size != 3'b011)
          $fatal(1, "MMIO bypass must preserve the 64-bit LSU access size");
        current_word = (mmio_saved_valid_q &&
                        (mmio_saved_addr_q == mmio_req_addr)) ?
                       mmio_saved_data_q : mmio_initial_word(mmio_req_addr);
        next_word = current_word;
        for (integer lane = 0; lane < 8; lane = lane + 1)
          if (mmio_req_wmask[lane])
            next_word[8*lane +: 8] = mmio_req_wdata[8*lane +: 8];
        mmio_response_data_q <= mmio_req_write ? 64'b0 : current_word;
        mmio_response_delay_q <= 3;
        mmio_saved_addr_q <= mmio_req_addr;
        mmio_saved_data_q <= mmio_req_write ? next_word : current_word;
        mmio_saved_valid_q <= 1'b1;
      end
      if ((mmio_response_delay_q == 1) && !mmio_response_valid_q)
        mmio_response_valid_q <= 1'b1;
    end
  end

  CoherentCacheSubsystem dut (
    .clock(clock), .reset(reset), .external_fatal_error(1'b0),
    .cpu_req_valid(cpu_req_valid), .cpu_req_ready(cpu_req_ready),
    .cpu_req_addr(cpu_req_addr), .cpu_req_write(cpu_req_write),
    .cpu_req_wmask(cpu_req_wmask), .cpu_req_wdata(cpu_req_wdata),
    .cpu_resp_valid(cpu_resp_valid), .cpu_resp_ready(cpu_resp_ready),
    .cpu_resp_addr(cpu_resp_addr), .cpu_resp_write(cpu_resp_write),
    .cpu_resp_rdata(cpu_resp_rdata), .cpu_resp_txn_id(cpu_resp_txn_id),
    .mmio_req_valid(mmio_req_valid), .mmio_req_ready(mmio_req_ready),
    .mmio_req_addr(mmio_req_addr), .mmio_req_size(mmio_req_size),
    .mmio_req_write(mmio_req_write), .mmio_req_wmask(mmio_req_wmask),
    .mmio_req_wdata(mmio_req_wdata), .mmio_resp_valid(mmio_resp_valid),
    .mmio_resp_ready(mmio_resp_ready), .mmio_resp_rdata(mmio_resp_rdata),
    .mem_rd_req_valid(mem_rd_req_valid), .mem_rd_req_ready(mem_rd_req_ready),
    .mem_rd_req_addr(mem_rd_req_addr),
    .mem_rd_req_txn_id(mem_rd_req_txn_id),
    .mem_rd_data_valid(mem_rd_data_valid),
    .mem_rd_data_ready(mem_rd_data_ready),
    .mem_rd_data_txn_id(mem_rd_data_txn_id),
    .mem_rd_data_beat_idx(mem_rd_data_beat_idx), .mem_rd_data(mem_rd_data),
    .mem_rd_data_last(mem_rd_data_last), .mem_rd_data_error(mem_rd_data_error),
    .mem_wr_req_valid(mem_wr_req_valid), .mem_wr_req_ready(mem_wr_req_ready),
    .mem_wr_req_addr(mem_wr_req_addr),
    .mem_wr_req_txn_id(mem_wr_req_txn_id),
    .mem_wr_data_valid(mem_wr_data_valid),
    .mem_wr_data_ready(mem_wr_data_ready),
    .mem_wr_data_txn_id(mem_wr_data_txn_id),
    .mem_wr_data_beat_idx(mem_wr_data_beat_idx), .mem_wr_data(mem_wr_data),
    .mem_wr_data_last(mem_wr_data_last),
    .mem_wr_rsp_valid(mem_wr_rsp_valid), .mem_wr_rsp_ready(mem_wr_rsp_ready),
    .mem_wr_rsp_txn_id(mem_wr_rsp_txn_id), .mem_wr_rsp_error(mem_wr_rsp_error),
    .l2_victim_valid(l2_victim_valid), .l2_victim_addr(l2_victim_addr),
    .l2_victim_dir_state(l2_victim_dir_state),
    .l2_victim_sharers(l2_victim_sharers),
    .l2_victim_owner_id(l2_victim_owner_id), .l2_victim_dirty(l2_victim_dirty),
    .l1_victim_valid(l1_victim_valid), .l1_victim_addr(l1_victim_addr),
    .l1_victim_state(l1_victim_state),
    .l1_controller_protocol_error(l1_controller_protocol_error),
    .l1_array_protocol_error(l1_array_protocol_error),
    .directory_protocol_error(directory_protocol_error),
    .directory_protocol_error_code(),
    .l2_protocol_error(l2_protocol_error),
    .memory_adapter_protocol_error(memory_adapter_protocol_error),
    .memory_adapter_error(memory_adapter_error), .fatal_error(fatal_error),
    .mmio_protocol_error(mmio_protocol_error),
    .perf_hit_event(perf_hit_event), .perf_miss_event(perf_miss_event),
    .perf_snoop_event(perf_snoop_event),
    .perf_dirty_writeback_event(perf_dirty_writeback_event),
    .perf_inflight(perf_inflight),
    .perf_access_complete_event(perf_access_complete_event),
    .metadata_commit_valid(metadata_commit_valid),
    .metadata_commit_line_addr(metadata_commit_line_addr),
    .metadata_commit_state(metadata_commit_state),
    .metadata_commit_is_snoop(metadata_commit_is_snoop),
    .monitor_snoop_accept_valid(monitor_snoop_accept_valid),
    .monitor_victim_snoop_accept_valid(),
    .monitor_victim_snoop_accept_core(),
    .monitor_victim_snoop_accept_addr(),
    .monitor_snoop_accept_addr(monitor_snoop_accept_addr),
    .monitor_snoop_accept_opcode(monitor_snoop_accept_opcode),
    .monitor_snoop_accept_txn_id(monitor_snoop_accept_txn_id),
    .monitor_dir_commit_valid(), .monitor_dir_commit_addr(),
    .monitor_dir_commit_state(), .monitor_dir_commit_sharers(),
    .monitor_dir_commit_owner(),
    .monitor_owner_data_valid(), .monitor_owner_data_core(),
    .monitor_owner_data_addr(), .monitor_owner_data_beat_idx(),
    .monitor_owner_data(), .monitor_owner_data_last(),
    .monitor_dir_lookup_conflict_valid(),
    .monitor_dir_lookup_conflict_incoming_addr(),
    .monitor_dir_lookup_conflict_active_addr(),
    .monitor_dir_lookup_conflict_is_transfer(),
    .monitor_dir_transfer_grant_conflict_valid(),
    .monitor_dir_transfer_grant_conflict_lookup_addr(),
    .monitor_dir_transfer_grant_conflict_grant_addr(),
    .monitor_dir_req_accept_valid(), .monitor_dir_req_accept_addr(),
    .monitor_l2_lookup_valid(), .monitor_l2_lookup_addr(),
    .monitor_l2_lookup_hit(), .monitor_dir_grant_accept_valid(),
    .monitor_dir_grant_accept_addr()
  );
