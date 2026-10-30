  task automatic reference_get(
    input logic [31:0] addr,
    output logic [63:0] value
  );
    integer slot;
    logic found;
    logic [31:0] word_addr;
    begin
      word_addr = {addr[31:3], 3'b000};
      found = 1'b0;
      value = (addr >= 32'h3000_0000 && addr < 32'h8000_0000) ?
              mmio_initial_word(word_addr) :
              memory_word(line_align(word_addr), word_addr[5:3]);
      if (word_addr >= 32'h3000_0000 && word_addr < 32'h8000_0000) begin
        if (mmio_saved_valid_q && mmio_saved_addr_q == word_addr)
          value = mmio_saved_data_q;
      end else begin
        for (slot = 0; slot < 128; slot = slot + 1)
          if (memory_slot_valid[slot] &&
              memory_slot_addr[slot] == line_align(word_addr))
            value = backing_store[slot][word_addr[5:3]];
      end
      for (slot = 0; slot < DATA_MODEL_ENTRIES; slot = slot + 1) begin
        if (reference_valid[slot] && reference_addr[slot] == word_addr) begin
          value = reference_data[slot];
          found = 1'b1;
        end
      end
      if (!found && reference_entries >= DATA_MODEL_ENTRIES)
        $fatal(1, "scoreboard reference table overflow");
    end
  endtask

  task automatic reference_clear;
    begin
      reference_entries = 0;
      for (integer entry = 0; entry < DATA_MODEL_ENTRIES; entry = entry + 1) begin
        reference_valid[entry] = 1'b0;
        reference_addr[entry] = '0;
        reference_data[entry] = '0;
      end
      for (integer entry = 0; entry < STATE_MODEL_ENTRIES; entry = entry + 1) begin
        state_model_valid[entry] = 1'b0;
        state_model_line[entry] = '0;
        state_model_mesi[entry][0] = MESI_I;
        state_model_mesi[entry][1] = MESI_I;
      end
      state_model_entries_used = 0;
    end
  endtask

  task automatic reference_write(
    input logic [31:0] addr,
    input logic [7:0] mask,
    input logic [63:0] data
  );
    integer slot;
    integer free_slot;
    logic found;
    logic [31:0] word_addr;
    logic [63:0] current_value;
    logic [63:0] merged_value;
    begin
      word_addr = {addr[31:3], 3'b000};
      found = 1'b0;
      free_slot = -1;
      current_value = '0;
      for (slot = 0; slot < DATA_MODEL_ENTRIES; slot = slot + 1) begin
        if (reference_valid[slot] && reference_addr[slot] == word_addr) begin
          found = 1'b1;
          current_value = reference_data[slot];
          free_slot = slot;
        end else if (!reference_valid[slot] && free_slot < 0) begin
          free_slot = slot;
        end
      end
      if (!found) begin
        reference_get(word_addr, current_value);
      end
      merged_value = current_value;
      for (integer lane = 0; lane < 8; lane = lane + 1)
        if (mask[lane])
          merged_value[8*lane +: 8] = data[8*lane +: 8];
      if (free_slot < 0)
        $fatal(1, "scoreboard reference table overflow");
      if (!found)
        reference_entries = reference_entries + 1;
      reference_valid[free_slot] = 1'b1;
      reference_addr[free_slot] = word_addr;
      reference_data[free_slot] = merged_value;
    end
  endtask

  function automatic integer state_model_index(input logic [31:0] addr);
    logic [31:0] aligned;
    begin
      aligned = line_align(addr);
      state_model_index = -1;
      for (integer entry = 0; entry < state_model_entries_used; entry = entry + 1)
        if (state_model_valid[entry] && state_model_line[entry] == aligned)
          state_model_index = entry;
    end
  endfunction

  task automatic state_model_get(
    input logic [31:0] addr,
    input integer core,
    output mesi_state_t state
  );
    integer entry;
    begin
      entry = state_model_index(addr);
      state = (entry < 0) ? MESI_I : state_model_mesi[entry][core];
    end
  endtask

  task automatic benchmark_observe_cpu_handshakes;
    mesi_state_t accepted_state;
    integer latency;
    begin
      for (integer core = 0; core < 2; core = core + 1) begin
        if (cpu_req_valid[core] && !cpu_req_ready[core] &&
            ((cpu_req_addr[core] < 32'h3000_0000) ||
             (cpu_req_addr[core] >= 32'h8000_0000)))
          benchmark_request_ready_stall_cycles =
            benchmark_request_ready_stall_cycles + 1;

        if (cpu_req_valid[core] && cpu_req_ready[core] &&
            ((cpu_req_addr[core] < 32'h3000_0000) ||
             (cpu_req_addr[core] >= 32'h8000_0000))) begin
          state_model_get(cpu_req_addr[core], core, accepted_state);
          if ((!cpu_req_write[core] && (accepted_state != MESI_I)) ||
              (cpu_req_write[core] &&
               ((accepted_state == MESI_E) || (accepted_state == MESI_M))))
            benchmark_model_accept_hit_count =
              benchmark_model_accept_hit_count + 1;
          else
            benchmark_model_accept_miss_count =
              benchmark_model_accept_miss_count + 1;
          benchmark_accept_state[core] = accepted_state;
          benchmark_accept_write[core] = cpu_req_write[core];
          benchmark_accept_cycle[core] = cycle_count;
          benchmark_accept_pending[core] = 1'b1;
        end

        if (cpu_resp_valid[core] && cpu_resp_ready[core] &&
            benchmark_accept_pending[core]) begin
          latency = cycle_count - benchmark_accept_cycle[core];
          if (benchmark_accept_state[core] == MESI_I) begin
            benchmark_l1_miss_count = benchmark_l1_miss_count + 1;
            benchmark_l1_miss_cycles = benchmark_l1_miss_cycles + latency;
          end else if (benchmark_accept_write[core] &&
                       (benchmark_accept_state[core] == MESI_S)) begin
            benchmark_upgrade_count = benchmark_upgrade_count + 1;
            benchmark_upgrade_cycles = benchmark_upgrade_cycles + latency;
          end else if (benchmark_accept_write[core] &&
                       ((benchmark_accept_state[core] == MESI_E) ||
                        (benchmark_accept_state[core] == MESI_M))) begin
            benchmark_write_hit_count = benchmark_write_hit_count + 1;
            benchmark_write_hit_cycles = benchmark_write_hit_cycles + latency;
          end else if (!benchmark_accept_write[core]) begin
            benchmark_read_hit_count = benchmark_read_hit_count + 1;
            benchmark_read_hit_cycles = benchmark_read_hit_cycles + latency;
          end
          benchmark_accept_pending[core] = 1'b0;
        end
      end
    end
  endtask

  task automatic state_model_set(
    input logic [31:0] addr,
    input integer core,
    input mesi_state_t state
  );
    integer entry;
    begin
      entry = state_model_index(addr);
      if (entry < 0) begin
        if (state_model_entries_used >= STATE_MODEL_ENTRIES)
          $fatal(1, "independent MESI model table overflow");
        entry = state_model_entries_used;
        state_model_entries_used = state_model_entries_used + 1;
        state_model_valid[entry] = 1'b1;
        state_model_line[entry] = line_align(addr);
        state_model_mesi[entry][0] = MESI_I;
        state_model_mesi[entry][1] = MESI_I;
      end
      state_model_mesi[entry][core] = state;
    end
  endtask

  task automatic coverage_mark(
    input string bin_id,
    input string old_state,
    input string requester,
    input string opcode,
    input string snoop_target,
    input string new_state,
    input string data_source,
    input integer beats
  );
    begin
      $display("COV_EVENT: id=%s checker=PASS old_state=%s requester=%s opcode=%s snoop_target=%s new_state=%s data_source=%s beats=%0d",
               bin_id, old_state, requester, opcode, snoop_target,
               new_state, data_source, beats);
    end
  endtask

  task automatic state_model_observe_protocol;
    integer put_core;
    mesi_state_t model_state;
    begin
      // An E-state store is a local silent E->M transition. It commits at
      // request acceptance even when the downstream CPU response is stalled.
      // Predict a silent E->M store from the model's own committed MESI
      // state. This does not sample the DUT lookup or its next-state signals.
      if (cpu_req_valid[0] && cpu_req_ready[0] && cpu_req_write[0]) begin
        state_model_get(cpu_req_addr[0], 0, model_state);
        if (model_state == MESI_E)
          state_model_set(cpu_req_addr[0], 0, MESI_M);
      end
      if (cpu_req_valid[1] && cpu_req_ready[1] && cpu_req_write[1]) begin
        state_model_get(cpu_req_addr[1], 1, model_state);
        if (model_state == MESI_E)
          state_model_set(cpu_req_addr[1], 1, MESI_M);
      end
      if (dut.cluster_dir_req_valid && dut.dir_req_ready &&
          ((dut.cluster_dir_req_opcode == REQ_PUTS) ||
           (dut.cluster_dir_req_opcode == REQ_PUTE) ||
           (dut.cluster_dir_req_opcode == REQ_PUTM))) begin
        put_core = dut.cluster_dir_req_src_id;
        state_model_set(dut.cluster_dir_req_addr, put_core, MESI_I);
      end
      for (integer snoop_core = 0; snoop_core < 2; snoop_core = snoop_core + 1) begin
        if (monitor_snoop_accept_valid[snoop_core])
          state_model_set(monitor_snoop_accept_addr[snoop_core], snoop_core,
                          (monitor_snoop_accept_opcode[snoop_core] == SNOOP_READ) ?
                            MESI_S : MESI_I);
      end
    end
  endtask
