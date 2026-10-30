  // Sample transaction handshakes in the active region at the clock edge.
  // Procedural tasks resume after the edge and can otherwise miss a one-cycle
  // valid/ready pulse that the DUT has already advanced past.
  always @(posedge clock) begin : state_model_protocol_monitor
    if (!reset) begin
      benchmark_observe_cpu_handshakes();
      for (integer core = 0; core < 2; core = core + 1) begin
        if (perf_hit_event[core])
          benchmark_rtl_hit_count = benchmark_rtl_hit_count + 1;
        if (perf_miss_event[core])
          benchmark_rtl_miss_count = benchmark_rtl_miss_count + 1;
      end
      state_model_observe_protocol();
    end else begin
      benchmark_accept_pending[0] = 1'b0;
      benchmark_accept_pending[1] = 1'b0;
    end
  end

  task automatic state_model_apply_cpu(
    input integer core,
    input logic [31:0] addr,
    input logic is_write
  );
    mesi_state_t own_state;
    mesi_state_t peer_state;
    begin
      if ((addr >= 32'h3000_0000) && (addr < 32'h8000_0000))
        return;
      state_model_get(addr, core, own_state);
      state_model_get(addr, 1-core, peer_state);
      if (is_write) begin
        state_model_set(addr, 1-core, MESI_I);
        state_model_set(addr, core, MESI_M);
      end else if (own_state == MESI_I) begin
        state_model_set(addr, core,
                        (peer_state == MESI_I) ? MESI_E : MESI_S);
      end
    end
  endtask

  task automatic state_model_l1_lookup(
    input integer core,
    input logic [31:0] addr,
    output integer found_way,
    output mesi_state_t observed_state
  );
    integer set_idx;
    begin
      set_idx = addr[12:6];
      found_way = -1;
      observed_state = MESI_I;
      if (core == 0) begin
        for (integer way = 0; way < 4; way = way + 1)
          if (dut.l1_cluster.cores[0].l1_array.valid_array[set_idx][way] &&
              dut.l1_cluster.cores[0].l1_array.tag_array[set_idx][way] == addr[31:13])
            found_way = way;
        if (found_way >= 0)
          observed_state = dut.l1_cluster.cores[0].l1_array.state_array[set_idx][found_way];
      end else begin
        for (integer way = 0; way < 4; way = way + 1)
          if (dut.l1_cluster.cores[1].l1_array.valid_array[set_idx][way] &&
              dut.l1_cluster.cores[1].l1_array.tag_array[set_idx][way] == addr[31:13])
            found_way = way;
        if (found_way >= 0)
          observed_state = dut.l1_cluster.cores[1].l1_array.state_array[set_idx][found_way];
      end
    end
  endtask

  task automatic state_model_l1_word(
    input integer core,
    input integer set_idx,
    input integer way,
    input integer beat,
    output logic [63:0] data
  );
    begin
      if (core == 0)
        data = dut.l1_cluster.cores[0].l1_array.data_array[set_idx][way][beat];
      else
        data = dut.l1_cluster.cores[1].l1_array.data_array[set_idx][way][beat];
    end
  endtask

  task automatic state_model_l1_entry(
    input integer core,
    input integer set_idx,
    input integer way,
    output logic valid,
    output logic [18:0] tag,
    output mesi_state_t state
  );
    begin
      if (core == 0) begin
        valid = dut.l1_cluster.cores[0].l1_array.valid_array[set_idx][way];
        tag = dut.l1_cluster.cores[0].l1_array.tag_array[set_idx][way];
        state = dut.l1_cluster.cores[0].l1_array.state_array[set_idx][way];
      end else begin
        valid = dut.l1_cluster.cores[1].l1_array.valid_array[set_idx][way];
        tag = dut.l1_cluster.cores[1].l1_array.tag_array[set_idx][way];
        state = dut.l1_cluster.cores[1].l1_array.state_array[set_idx][way];
      end
    end
  endtask

  task automatic state_model_check_all;
    integer entry;
    integer set_idx;
    integer cache_way;
    integer found_way;
    integer l2_way;
    integer found_l2_way;
    integer core;
    logic [31:0] line_addr;
    logic [63:0] expected_word;
    logic [63:0] observed_word;
    logic observed_valid;
    logic [18:0] observed_tag;
    mesi_state_t observed_state;
    directory_state_t expected_dir_state;
    logic [1:0] expected_sharers;
    logic expected_owner;
    begin
      #1;
      // Every model line is checked against both complete physical L1 copies,
      // all eight words, and the shared directory metadata.
      for (entry = 0; entry < state_model_entries_used; entry = entry + 1) begin
        if (state_model_valid[entry]) begin
          line_addr = state_model_line[entry];
          for (core = 0; core < 2; core = core + 1) begin
            state_model_l1_lookup(core, line_addr, found_way, observed_state);
            if (observed_state !== state_model_mesi[entry][core])
              $fatal(1, "MESI reference mismatch line=%08x core=%0d got=%s expected=%s",
                     line_addr, core, observed_state.name(), state_model_mesi[entry][core].name());
            if (found_way >= 0 && observed_state != MESI_I) begin
              for (integer beat = 0; beat < 8; beat = beat + 1) begin
                reference_get(line_addr + (beat * 8), expected_word);
                state_model_l1_word(core, line_addr[12:6], found_way, beat, observed_word);
                if (observed_word !== expected_word)
                  $fatal(1, "L1 data reference mismatch line=%08x core=%0d beat=%0d got=%016x expected=%016x",
                         line_addr, core, beat, observed_word, expected_word);
              end
            end
          end

          expected_sharers = 2'b00;
          expected_owner = 1'b0;
          expected_dir_state = DIR_I;
          if ((state_model_mesi[entry][0] == MESI_M) || (state_model_mesi[entry][0] == MESI_E)) begin
            expected_dir_state = DIR_U;
            expected_owner = 1'b0;
          end else if ((state_model_mesi[entry][1] == MESI_M) || (state_model_mesi[entry][1] == MESI_E)) begin
            expected_dir_state = DIR_U;
            expected_owner = 1'b1;
          end else begin
            if (state_model_mesi[entry][0] == MESI_S) expected_sharers[0] = 1'b1;
            if (state_model_mesi[entry][1] == MESI_S) expected_sharers[1] = 1'b1;
            if (expected_sharers != 2'b00)
              expected_dir_state = DIR_S;
          end
          set_idx = line_addr[14:6];
          found_l2_way = -1;
          for (l2_way = 0; l2_way < 8; l2_way = l2_way + 1)
            if (dut.l2_array.valid_array[set_idx][l2_way] &&
                dut.l2_array.tag_array[set_idx][l2_way] == line_addr[31:15])
              found_l2_way = l2_way;
          if (found_l2_way < 0) begin
            if (expected_dir_state != DIR_I)
              $fatal(1, "L1 line is absent from L2 directory line=%08x", line_addr);
          end else if (dut.l2_array.dir_state_array[set_idx][found_l2_way] !== expected_dir_state ||
                       dut.l2_array.sharer_array[set_idx][found_l2_way] !== expected_sharers ||
                       dut.l2_array.owner_array[set_idx][found_l2_way] !== expected_owner) begin
            $fatal(1, "directory reference mismatch line=%08x got=%s sharers=%b owner=%b expected=%s sharers=%b owner=%b",
                   line_addr,
                   dut.l2_array.dir_state_array[set_idx][found_l2_way].name(),
                   dut.l2_array.sharer_array[set_idx][found_l2_way],
                   dut.l2_array.owner_array[set_idx][found_l2_way],
                   expected_dir_state.name(), expected_sharers, expected_owner);
          end
        end
      end

      // Catch any unexpected resident L1 line that was not introduced by a
      // completed CPU transaction in the reference model.
      for (core = 0; core < 2; core = core + 1)
        for (set_idx = 0; set_idx < 128; set_idx = set_idx + 1)
          for (cache_way = 0; cache_way < 4; cache_way = cache_way + 1) begin
            state_model_l1_entry(core, set_idx, cache_way, observed_valid, observed_tag, observed_state);
            if (observed_valid && (observed_state != MESI_I)) begin
              line_addr = {observed_tag, set_idx[6:0], 6'b0};
              entry = state_model_index(line_addr);
              if (entry < 0 ||
                  state_model_mesi[entry][core] !== observed_state)
                $fatal(1, "unmodeled resident L1 line=%08x core=%0d", line_addr, core);
            end
          end
    end
  endtask
