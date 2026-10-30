  task automatic expect_word(
    input integer core,
    input logic [31:0] addr,
    input logic [63:0] expected
  );
    logic [63:0] got;
    begin
      cpu_access(core, addr, 1'b0, 8'h00, 64'b0, got);
      if (got !== expected)
        $fatal(1, "Core%0d read %08x got %016x expected %016x",
               core, addr, got, expected);
    end
  endtask

  task automatic expect_reference_word(
    input integer core,
    input logic [31:0] addr
  );
    logic [63:0] expected;
    begin
      reference_get(addr, expected);
      expect_word(core, addr, expected);
    end
  endtask

  task automatic expect_line_with_word_override(
    input integer core,
    input logic [31:0] line_addr,
    input integer override_beat,
    input logic [63:0] override_word
  );
    logic [63:0] expected;
    begin
      for (integer beat = 0; beat < 8; beat = beat + 1) begin
        expected = (beat == override_beat) ? override_word :
                   memory_word(line_addr, 3'(beat));
        expect_word(core, line_addr + (beat * 8), expected);
      end
    end
  endtask

  task automatic expect_protocol_state(
    input mesi_state_t core0_state,
    input mesi_state_t core1_state,
    input directory_state_t directory_state,
    input logic [1:0] sharers,
    input logic owner
  );
    logic [31:0] addr0_line;
    logic [31:0] addr1_line;
    logic found0;
    logic found1;
    logic dir_found;
    mesi_state_t observed0;
    mesi_state_t observed1;
    directory_state_t observed_dir;
    logic [1:0] observed_sharers;
    logic observed_owner;
    begin
      #1;
      addr0_line = line_align(cpu_req_addr[0]);
      addr1_line = line_align(cpu_req_addr[1]);
      found0 = 1'b0;
      found1 = 1'b0;
      dir_found = 1'b0;
      observed0 = MESI_I;
      observed1 = MESI_I;
      observed_dir = DIR_I;
      observed_sharers = 2'b00;
      observed_owner = 1'b0;
      for (integer way = 0; way < 4; way = way + 1) begin
        if (dut.l1_cluster.cores[0].l1_array.valid_array[addr0_line[12:6]][way] &&
            dut.l1_cluster.cores[0].l1_array.tag_array[addr0_line[12:6]][way] ==
              addr0_line[31:13]) begin
          found0 = 1'b1;
          observed0 = dut.l1_cluster.cores[0].l1_array.state_array[addr0_line[12:6]][way];
        end
        if (dut.l1_cluster.cores[1].l1_array.valid_array[addr1_line[12:6]][way] &&
            dut.l1_cluster.cores[1].l1_array.tag_array[addr1_line[12:6]][way] ==
              addr1_line[31:13]) begin
          found1 = 1'b1;
          observed1 = dut.l1_cluster.cores[1].l1_array.state_array[addr1_line[12:6]][way];
        end
      end
      for (integer way = 0; way < 8; way = way + 1) begin
        if (dut.l2_array.valid_array[addr0_line[14:6]][way] &&
            dut.l2_array.tag_array[addr0_line[14:6]][way] == addr0_line[31:15]) begin
          dir_found = 1'b1;
          observed_dir = dut.l2_array.dir_state_array[addr0_line[14:6]][way];
          observed_sharers = dut.l2_array.sharer_array[addr0_line[14:6]][way];
          observed_owner = dut.l2_array.owner_array[addr0_line[14:6]][way];
        end
      end
      if ((observed0 !== core0_state) || (observed1 !== core1_state) ||
          (!found0 && (core0_state != MESI_I)) ||
          (!found1 && (core1_state != MESI_I)))
        $fatal(1, "L1 state mismatch: core0=%s core1=%s expected=%s/%s addr=%08x/%08x hit=%b/%b",
               observed0.name(), observed1.name(), core0_state.name(),
               core1_state.name(), addr0_line, addr1_line, found0, found1);
      if (!dir_found || observed_dir !== directory_state ||
          observed_sharers !== sharers || observed_owner !== owner)
        $fatal(1, "directory state mismatch: hit=%b state=%s sharers=%b owner=%b expected=%s/%b/%b addr=%08x",
               dir_found, observed_dir.name(), observed_sharers, observed_owner,
               directory_state.name(), sharers, owner, addr0_line);
    end
  endtask
