    // Hold an E->M CPU write response while the other core requests the same
    // line. The snoop must wait for the local store commit, then forward the
    // new data; accepting it earlier would race the array metadata/data writes.
    snoop_write_race_addr = 32'h0000_B018;
    snoop_write_race_data = 64'hD00D_F00D_CAFE_1234;
    cpu_access(0, snoop_write_race_addr, 1'b0, 8'h00, 64'b0, ignored);
    @(negedge clock);
    cpu_resp_ready[0] = 1'b0;
    cpu_resp_ready[1] = 1'b0;
    cpu_issue_only(0, snoop_write_race_addr, 1'b1, 8'hFF,
                   snoop_write_race_data);
    for (cycles = 0; cycles < 100; cycles = cycles + 1) begin
      @(posedge clock);
      if (cpu_resp_valid[0])
        break;
    end
    if (!cpu_resp_valid[0])
      $fatal(1, "local E-to-M write did not reach its stalled response");
    cpu_issue_only(1, snoop_write_race_addr, 1'b0, 8'h00, 64'b0);
    for (cycles = 0; cycles < 300; cycles = cycles + 1) begin
      @(posedge clock);
      if (dut.snoop_valid_core[0] && !dut.snoop_ready_core[0])
        break;
    end
    if (!(dut.snoop_valid_core[0] && !dut.snoop_ready_core[0]))
      $fatal(1, "same-line snoop was not backpressured behind the local write");
    @(negedge clock);
    cpu_resp_ready[0] = 1'b1;
    cpu_response_only(0, snoop_write_race_addr, 1'b1, 8'hFF,
                      snoop_write_race_data, ignored);
    @(negedge clock);
    cpu_resp_ready[1] = 1'b1;
    cpu_response_only(1, snoop_write_race_addr, 1'b0, 8'h00, 64'b0,
                      snoop_write_race_readback);
    if (snoop_write_race_readback !== snoop_write_race_data)
      $fatal(1, "same-line snoop returned stale data during local E-to-M write");
    expect_protocol_state(MESI_S, MESI_S, DIR_S, 2'b11, 1'b0);
      coverage_mark("mesi.snoop_waits_store_commit", "E", "1", "GetS+StoreCommit", "0", "S", "L1_owner", 8);
    $display("PASS: same-line SnoopRead waits for local E-to-M write commit");
    cpu_resp_ready[0] = 1'b1;
    cpu_resp_ready[1] = 1'b1;

    cpu_access(0, word_addr, 1'b1, 8'hFF, value4, ignored);
    cpu_req_addr[0] = word_addr;
    cpu_req_addr[1] = word_addr;
    expect_protocol_state(MESI_M, MESI_I, DIR_U, 2'b00, 1'b0);
    expect_line_with_word_override(0, line_addr, 3, value4);
      coverage_mark("mesi.e_to_m_silent", "E", "0", "Store", "none", "M", "local_L1", 0);
    $display("PASS: E-to-M local write is silent and preserves the full line");

    expect_word(1, word_addr, value4);
    expect_protocol_state(MESI_S, MESI_S, DIR_S, 2'b11, 1'b0);
    expect_line_with_word_override(1, line_addr, 3, value4);
      coverage_mark("mesi.gets_share_m_owner", "M", "1", "GetS", "0", "S", "remote_owner", 8);
    $display("PASS: Core1 GetS shares the full latest line from the M owner");

    cpu_access(0, word_addr, 1'b1, 8'hFF, value0, ignored);
    expect_protocol_state(MESI_M, MESI_I, DIR_U, 2'b00, 1'b0);
    expect_word(1, word_addr, value0);
      coverage_mark("mesi.getm_upgrade_s", "S", "0", "GetM", "1", "M", "L1_peer", 0);
    $display("PASS: shared-to-exclusive upgrade invalidates peer; remote read sees M data");

    cpu_access(1, word_addr, 1'b1, 8'hFF, value1, ignored);
    expect_protocol_state(MESI_I, MESI_M, DIR_U, 2'b00, 1'b1);
    cpu_access(0, word_addr, 1'b1, 8'hFF, value2, ignored);
    expect_protocol_state(MESI_M, MESI_I, DIR_U, 2'b00, 1'b0);
    expect_word(1, word_addr, value2);
    expect_line_with_word_override(1, line_addr, 3, value2);
      coverage_mark("mesi.getm_remote_owner", "M", "0", "GetM", "1", "M", "remote_owner", 8);
    $display("PASS: remote GetM invalidates an M owner and preserves its latest data");

    masked_value = (value2 & 64'hFFFF_FFFF_0000_0000) |
                   (value3 & 64'h0000_0000_FFFF_FFFF);
    cpu_access(0, word_addr, 1'b1, 8'h0F, value3, ignored);
    expect_protocol_state(MESI_M, MESI_I, DIR_U, 2'b00, 1'b0);
    expect_word(1, word_addr, masked_value);
      coverage_mark("mesi.masked_owner_write", "M", "1", "GetS_after_MaskedStore", "0", "S", "remote_owner", 8);
    $display("PASS: byte-masked write is visible after remote owner intervention");

    // Both cores miss on one line together, then race for write permission.
    // The serialized Directory must produce one coherent final value.
    shared_addr = 32'h0000_C038;
    cpu_pair_access(shared_addr, 1'b0, 8'h00, 64'b0,
                    shared_addr, 1'b0, 8'h00, 64'b0,
                    concurrent_data0, concurrent_data1, last_writer);
    if (concurrent_data0 !== memory_word(line_align(shared_addr), shared_addr[5:3]) ||
        concurrent_data1 !== concurrent_data0)
      $fatal(1, "simultaneous cold GetS returned inconsistent data");
    cpu_pair_access(shared_addr, 1'b1, 8'hFF, 64'h1357_9BDF_2468_ACE0,
                    shared_addr, 1'b1, 8'hFF, 64'h0BAD_F00D_CAFE_BABE,
                    concurrent_data0, concurrent_data1, last_writer);
    reference_write(shared_addr, 8'hFF,
                    last_writer ? 64'h0BAD_F00D_CAFE_BABE :
                                  64'h1357_9BDF_2468_ACE0);
    reference_get(shared_addr, masked_value);
    expect_word(0, shared_addr, masked_value);
    cpu_access(0, shared_addr, 1'b1, 8'h80, 64'hA500_0000_0000_0000, ignored);
    reference_get(shared_addr, masked_value);
    expect_word(1, shared_addr, masked_value);
    cpu_access(1, shared_addr, 1'b1, 8'h00, 64'hFFFF_FFFF_FFFF_FFFF, ignored);
    reference_get(shared_addr, masked_value);
    expect_word(0, shared_addr, masked_value);
      coverage_mark("cpu_pair.same_line", "mixed", "both", "GetS+GetM", "both", "M", "mixed", 8);
    $display("PASS: same-line simultaneous GetS/GetM and byte-mask corner cases");

    cpu_pair_access(32'h0000_D000, 1'b0, 8'h00, 64'b0,
                    32'h0000_E038, 1'b0, 8'h00, 64'b0,
                    concurrent_data0, concurrent_data1, last_writer);
    if (concurrent_data0 !== memory_word(32'h0000_D000, 3'd0) ||
        concurrent_data1 !== memory_word(32'h0000_E000, 3'd7))
      $fatal(1, "different-line concurrent misses returned incorrect data");
      coverage_mark("cpu_pair.different_lines", "I", "both", "GetS", "none", "E", "memory", 8);
    $display("PASS: different-address concurrent misses route to the correct cores");

    expect_word(1, clean_owner_word_addr,
                memory_word(clean_owner_line, 3'd3));
    cpu_access(0, clean_owner_word_addr, 1'b1, 8'hFF,
               clean_owner_value, ignored);
    cpu_req_addr[0] = clean_owner_word_addr;
    cpu_req_addr[1] = clean_owner_word_addr;
    expect_protocol_state(MESI_M, MESI_I, DIR_U, 2'b00, 1'b0);
    expect_line_with_word_override(0, clean_owner_line, 3,
                                   clean_owner_value);
      coverage_mark("mesi.getm_remote_clean_e", "E", "0", "GetM", "1", "M", "clean_L1_peer", 8);
    $display("PASS: remote GetM invalidates a clean E owner and receives all beats");

    // An unrelated SnoopInvalidate must still enter the independent Snoop
    // FSM while the local CPU holds a response for another line.
    different_snoop_cpu_addr = 32'h0030_0018;
    different_snoop_target_addr = 32'h0030_8018;
    different_snoop_cpu_data = 64'h55AA_0123_CDEF_9876;
    different_snoop_target_data = 64'h8877_6655_4433_2211;
    cpu_access(0, different_snoop_cpu_addr, 1'b0, 8'h00, 64'b0, ignored);
    cpu_access(0, different_snoop_target_addr, 1'b0, 8'h00, 64'b0, ignored);
    cpu_access(1, different_snoop_target_addr, 1'b0, 8'h00, 64'b0, ignored);
    @(negedge clock);
    cpu_resp_ready[0] = 1'b0;
    cpu_issue_only(0, different_snoop_cpu_addr, 1'b1, 8'hFF,
                   different_snoop_cpu_data);
    wait (cpu_resp_valid[0]);
    cpu_issue_only(1, different_snoop_target_addr, 1'b1, 8'hFF,
                   different_snoop_target_data);
    for (cycles = 0; cycles < 500; cycles = cycles + 1) begin
      if (dut.snoop_valid_core[0] && dut.snoop_ready_core[0])
        break;
      @(posedge clock);
    end
    if (!(dut.snoop_valid_core[0] && dut.snoop_ready_core[0]))
      $fatal(1, "different-line SnoopInvalidate was blocked by local CPU response");
    cpu_response_only(1, different_snoop_target_addr, 1'b1, 8'hFF,
                      different_snoop_target_data, ignored);
    @(negedge clock);
    cpu_resp_ready[0] = 1'b1;
    cpu_response_only(0, different_snoop_cpu_addr, 1'b1, 8'hFF,
                      different_snoop_cpu_data, ignored);
    expect_word(0, different_snoop_target_addr, different_snoop_target_data);
    expect_word(1, different_snoop_cpu_addr, different_snoop_cpu_data);
      coverage_mark("cpu_pair.snoop_progress", "S", "1", "GetM_Upgrade", "0", "M", "local_L1", 0);
    $display("PASS: different-line SnoopInvalidate progresses during a local CPU response stall");
    cpu_req_addr[0] = clean_owner_word_addr;
    cpu_req_addr[1] = clean_owner_word_addr;

    cpu_access(0, word_addr, 1'b1, 8'hFF, value4, ignored);
    for (line_number = 1; line_number <= 4; line_number = line_number + 1) begin
      eviction_line_addr = line_addr + (line_number * 32'h2000);
      eviction_word_addr = eviction_line_addr + 32'd24;
      expect_word(0, eviction_word_addr, memory_word(eviction_line_addr, 3'd3));
    end
    expect_word(1, word_addr, value4);
      coverage_mark("l1.putm", "M", "0", "PutM", "none", "I", "L1_owner", 8);
    $display("PASS: dirty M victim uses PutM, returns to L2, then refills by peer");

    for (line_number = 1; line_number <= 4; line_number = line_number + 1) begin
      eviction_line_addr = line_addr + (line_number * 32'h2000);
      expect_word(1, eviction_line_addr + 32'd24,
                  memory_word(eviction_line_addr, 3'd3));
    end
    if ((dut.l1_cluster.cores[1].l1_array.valid_array[64][0] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[64][0] == 19'h0) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[64][1] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[64][1] == 19'h0) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[64][2] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[64][2] == 19'h0) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[64][3] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[64][3] == 19'h0))
      $fatal(1, "PutE replacement left the evicted E line valid");
    expect_word(0, word_addr, value4);
      coverage_mark("l1.pute", "E", "0", "PutE", "none", "I", "L2", 0);
    $display("PASS: clean E victim is removed with PutE; dirty L2 data is preserved");

    expect_word(1, 32'h0000_B018, snoop_write_race_data);
    if ((dut.l1_cluster.cores[1].l1_array.valid_array[64][0] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[64][0] == 19'h1) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[64][1] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[64][1] == 19'h1) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[64][2] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[64][2] == 19'h1) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[64][3] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[64][3] == 19'h1))
      $fatal(1, "PutS replacement left the evicted S line valid");
    expect_word(0, 32'h0000_3018, memory_word(32'h0000_3000, 3'd3));
      coverage_mark("l1.puts", "S", "0", "PutS", "none", "I", "L2", 0);
    $display("PASS: shared S victim is removed with PutS while the peer retains its copy");

    l2_test_addr[0] = 32'h0000_4000;
    for (l2_line_number = 1; l2_line_number <= 8; l2_line_number = l2_line_number + 1)
      l2_test_addr[l2_line_number] = l2_test_addr[0] +
                                     (l2_line_number * 32'h0000_8000);
    l2_dirty_value = 64'hCAFE_BABE_0123_4567;
