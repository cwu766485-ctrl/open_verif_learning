    // Fill eight congruent lines across both cores so a later core0 miss first
    // evicts a local way while the L2 replacement pointer still selects a
    // live owner in core1.
    expect_word(0, l2_test_addr[1] + 32'd24,
                memory_word(l2_test_addr[1], 3'd3));
    expect_word(1, l2_test_addr[0] + 32'd24,
                memory_word(l2_test_addr[0], 3'd3));
    cpu_access(1, l2_test_addr[0] + 32'd24, 1'b1, 8'hFF,
               l2_dirty_value, ignored);
    for (l2_line_number = 2; l2_line_number <= 4; l2_line_number = l2_line_number + 1)
      expect_word(0, l2_test_addr[l2_line_number] + 32'd24,
                  memory_word(l2_test_addr[l2_line_number], 3'd3));
    for (l2_line_number = 5; l2_line_number <= 7; l2_line_number = l2_line_number + 1)
      expect_word(1, l2_test_addr[l2_line_number] + 32'd24,
                  memory_word(l2_test_addr[l2_line_number], 3'd3));
    cpu_access(1, l2_test_addr[0] + 32'd24, 1'b1, 8'hFF,
               l2_dirty_value, ignored);
    cpu_access(1, l2_test_addr[5] + 32'd24, 1'b1, 8'hFF,
               l2_dirty_value, ignored);
    cpu_access(1, l2_test_addr[6] + 32'd24, 1'b1, 8'hFF,
               l2_dirty_value, ignored);
    cpu_access(1, l2_test_addr[7] + 32'd24, 1'b1, 8'hFF,
               l2_dirty_value, ignored);

    expect_word(0, l2_test_addr[8] + 32'd24,
                memory_word(l2_test_addr[8], 3'd3));
    @(negedge clock);
    if (!saw_l2_live_victim_q ||
        ((observed_l2_live_victim_q[31:13]) != (l2_test_addr[0][31:13]) &&
         (observed_l2_live_victim_q[31:13]) != (l2_test_addr[5][31:13]) &&
         (observed_l2_live_victim_q[31:13]) != (l2_test_addr[6][31:13]) &&
         (observed_l2_live_victim_q[31:13]) != (l2_test_addr[7][31:13])))
      $fatal(1, "test did not evict a tracked live DIR_U L2 owner victim");
    if ((dut.l1_cluster.cores[1].l1_array.valid_array[0][0] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[0][0] == observed_l2_live_victim_q[31:13]) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[0][1] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[0][1] == observed_l2_live_victim_q[31:13]) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[0][2] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[0][2] == observed_l2_live_victim_q[31:13]) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[0][3] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[0][3] == observed_l2_live_victim_q[31:13]))
      $fatal(1, "L2 live-victim back-invalidation left the old owner line valid");
      coverage_mark("l2.live_u_victim", "M", "1", "L2_Evict", "1", "I", "L1_owner", 8);
    $display("PASS: L2 live victim back-invalidates an M owner and writes back its line");
    expect_word(0, observed_l2_live_victim_q + 32'd24, l2_dirty_value);
      coverage_mark("l2.dirty_owner_writeback", "M", "1", "L2_Evict", "1", "I", "backing_memory", 8);
    $display("PASS: dirty owner data survives L2 eviction through backing memory");

    @(negedge clock);
    reset = 1'b1;
    reference_clear();
    repeat (3) @(posedge clock);
    @(negedge clock);
    reset = 1'b0;

    expect_reference_word(0, l2_test_addr[1] + 32'd24);
    expect_reference_word(1, l2_test_addr[0] + 32'd24);
    for (l2_line_number = 2; l2_line_number <= 4; l2_line_number = l2_line_number + 1)
      expect_reference_word(0, l2_test_addr[l2_line_number] + 32'd24);
    for (l2_line_number = 5; l2_line_number <= 7; l2_line_number = l2_line_number + 1)
      expect_reference_word(1, l2_test_addr[l2_line_number] + 32'd24);
    cpu_access(1, l2_test_addr[5] + 32'd24, 1'b1, 8'hFF,
               l2_dirty_value, ignored);
    cpu_access(1, l2_test_addr[6] + 32'd24, 1'b1, 8'hFF,
               l2_dirty_value, ignored);
    // Share C, then F and G. The M-owner data writes leave F as the next L2
    // victim; core0's replacement PutS removes only its copy of C.
    expect_reference_word(1, l2_test_addr[2] + 32'd24);
    expect_word(0, l2_test_addr[5] + 32'd24, l2_dirty_value);
    expect_word(0, l2_test_addr[6] + 32'd24, l2_dirty_value);
    expect_reference_word(0, l2_test_addr[8] + 32'd24);

    if (!saw_l2_shared_victim_q ||
        (observed_l2_shared_victim_q != l2_test_addr[5]) ||
        (observed_l2_shared_sharers_q != 2'b11))
      $fatal(1, "expected DIR_S victim %08x/sharers=11, got saw=%b addr=%08x sharers=%b",
        l2_test_addr[5], saw_l2_shared_victim_q,
        observed_l2_shared_victim_q, observed_l2_shared_sharers_q);
    if ((dut.l1_cluster.cores[0].l1_array.valid_array[0][0] &&
         dut.l1_cluster.cores[0].l1_array.tag_array[0][0] == observed_l2_shared_victim_q[31:13]) ||
        (dut.l1_cluster.cores[0].l1_array.valid_array[0][1] &&
         dut.l1_cluster.cores[0].l1_array.tag_array[0][1] == observed_l2_shared_victim_q[31:13]) ||
        (dut.l1_cluster.cores[0].l1_array.valid_array[0][2] &&
         dut.l1_cluster.cores[0].l1_array.tag_array[0][2] == observed_l2_shared_victim_q[31:13]) ||
        (dut.l1_cluster.cores[0].l1_array.valid_array[0][3] &&
         dut.l1_cluster.cores[0].l1_array.tag_array[0][3] == observed_l2_shared_victim_q[31:13]) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[0][0] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[0][0] == observed_l2_shared_victim_q[31:13]) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[0][1] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[0][1] == observed_l2_shared_victim_q[31:13]) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[0][2] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[0][2] == observed_l2_shared_victim_q[31:13]) ||
        (dut.l1_cluster.cores[1].l1_array.valid_array[0][3] &&
         dut.l1_cluster.cores[1].l1_array.tag_array[0][3] == observed_l2_shared_victim_q[31:13]))
      $fatal(1, "L2 DIR_S victim back-invalidation left an L1 sharer valid");
    found_written_victim = 1'b0;
    for (memory_slot_index = 0; memory_slot_index < 128; memory_slot_index = memory_slot_index + 1)
      if (memory_slot_valid[memory_slot_index] &&
          (memory_slot_addr[memory_slot_index] == observed_l2_shared_victim_q) &&
          (backing_store[memory_slot_index][3] == l2_dirty_value))
        found_written_victim = 1'b1;
    if (!found_written_victim)
      $fatal(1, "dirty DIR_S victim data was not written back to memory");
      coverage_mark("l2.shared_multisnoop", "S", "both", "L2_Evict", "both", "I", "L2_dirty", 8);
    $display("PASS: DIR_S L2 victim invalidates both sharers and writes back dirty L2 data");
