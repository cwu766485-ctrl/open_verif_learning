    // Independently run the inclusive DIR_S victim path. In this two-core
    // design the Directory transaction sequencer handles one remote target;
    // the L2 victim controller must fan out sequential invalidations to both
    // sharers before writing the dirty line back.
    if ($test$plusargs("l2_multisnoop_only")) begin
      for (l2_line_number = 0; l2_line_number <= 8; l2_line_number = l2_line_number + 1)
        l2_test_addr[l2_line_number] = 32'h0040_0000 +
                                       (l2_line_number * 32'h0000_8000);
      l2_dirty_value = 64'hCAFE_BABE_0123_4567;
      for (l2_line_number = 0; l2_line_number < 6; l2_line_number = l2_line_number + 1)
        cpu_access(0, l2_test_addr[l2_line_number] + 32'd24,
                   1'b0, 8'h00, 64'b0, ignored);

      cpu_access(0, l2_test_addr[6] + 32'd24, 1'b0, 8'h00, 64'b0, ignored);
      cpu_access(1, l2_test_addr[6] + 32'd24, 1'b0, 8'h00, 64'b0, ignored);
      cpu_access(0, l2_test_addr[6] + 32'd24, 1'b1, 8'hFF,
                 l2_dirty_value, ignored);
      cpu_access(1, l2_test_addr[6] + 32'd24, 1'b0, 8'h00, 64'b0, ignored);
      cpu_req_addr[0] = l2_test_addr[6] + 32'd24;
      cpu_req_addr[1] = l2_test_addr[6] + 32'd24;
      expect_protocol_state(MESI_S, MESI_S, DIR_S, 2'b11, 1'b0);

      cpu_access(0, l2_test_addr[7] + 32'd24, 1'b0, 8'h00, 64'b0, ignored);
      cpu_access(1, l2_test_addr[8] + 32'd24, 1'b0, 8'h00, 64'b0, ignored);
      if (!saw_l2_shared_victim_q ||
          observed_l2_shared_victim_q != l2_test_addr[6] ||
          observed_l2_shared_sharers_q != 2'b11)
        $fatal(1, "isolated victim did not fan out to both sharers: saw=%b addr=%08x sharers=%b",
               saw_l2_shared_victim_q, observed_l2_shared_victim_q,
               observed_l2_shared_sharers_q);

      for (line_number = 0; line_number < 4; line_number = line_number + 1) begin
        if ((dut.l1_cluster.cores[0].l1_array.valid_array[0][line_number] &&
             dut.l1_cluster.cores[0].l1_array.tag_array[0][line_number] ==
               l2_test_addr[6][31:13]) ||
            (dut.l1_cluster.cores[1].l1_array.valid_array[0][line_number] &&
             dut.l1_cluster.cores[1].l1_array.tag_array[0][line_number] ==
               l2_test_addr[6][31:13]))
          $fatal(1, "L2 DIR_S victim fanout left a sharer valid");
      end

      fanout_victim_written = 1'b0;
      for (memory_slot_index = 0; memory_slot_index < 128;
           memory_slot_index = memory_slot_index + 1)
        if (memory_slot_valid[memory_slot_index] &&
            memory_slot_addr[memory_slot_index] == l2_test_addr[6] &&
            backing_store[memory_slot_index][3] == l2_dirty_value)
          fanout_victim_written = 1'b1;
      if (!fanout_victim_written || fatal_error)
        $fatal(1, "multi-sharer dirty victim was not written back cleanly");
      $display("PASS: isolated DIR_S victim invalidates both L1 sharers and writes back dirty data");
      $finish;
    end

    cpu_access(0, mmio_addr, 1'b0, 8'h00, 64'b0, mmio_data);
    if (mmio_data !== mmio_initial)
      $fatal(1, "MMIO read returned %016x, expected %016x",
             mmio_data, mmio_initial);
    cpu_access(0, mmio_addr, 1'b1, 8'h0F, value3, ignored);
    cpu_access(0, mmio_addr, 1'b0, 8'h00, 64'b0, mmio_data);
    if ((mmio_data !== mmio_masked) ||
        (mmio_request_count != mmio_count_before + 3) ||
        (memory_read_count != 0) ||
        dut.l1_cluster.cores[0].l1_array.cpu_lookup_hit ||
        mmio_protocol_error)
      $fatal(1, "MMIO bypass failed: data=%016x expected=%016x reqs=%0d mem_reads=%0d hit=%b err=%b",
             mmio_data, mmio_masked, mmio_request_count - mmio_count_before,
             memory_read_count,
             dut.l1_cluster.cores[0].l1_array.cpu_lookup_hit,
             mmio_protocol_error);
      coverage_mark("mmio.bypass", "na", "both", "MMIO", "none", "na", "MMIO", 0);
    $display("PASS: MMIO read/write bypasses L1, L2, and backing memory");
    expect_word(0, 32'h2FFF_FFF8, memory_word(32'h2FFF_FFC0, 3'd7));
    cpu_access(0, 32'h7FFF_FFF8, 1'b0, 8'h00, 64'b0, mmio_data);
    if (mmio_data !== mmio_initial_word(32'h7FFF_FFF8))
      $fatal(1, "upper MMIO boundary returned incorrect data");
    expect_word(0, 32'h8000_0000, memory_word(32'h8000_0000, 3'd0));
      coverage_mark("mmio.address_boundaries", "na", "both", "MMIO_boundary", "none", "na", "MMIO", 0);
    $display("PASS: cacheable/MMIO address-domain boundary cases");
