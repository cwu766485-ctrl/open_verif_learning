  initial begin : test
    integer i;
    integer operation;
    integer selector;
    logic [31:0] address;
    logic [63:0] value;
    logic [31:0] csr_value;
    logic [31:0] first_conflict_address;
    logic [63:0] first_conflict_data;
    integer benchmark_seed;
    integer random_state;
    integer total_ops;
    integer latency_count;
    integer sorted_latency [0:511];
    integer latency_temp;
    integer latency_p95;
    real mean_latency;
    real ops_per_cycle;
    real read_bytes_per_cycle;
    real write_bytes_per_cycle;
    real total_bytes_per_cycle;

    if (!$value$plusargs("seed=%d", benchmark_seed)) benchmark_seed = 1;
    forced_r_stall_cycles = 0;
    forced_b_stall_cycles = 0;
    random_state = benchmark_seed;
    cpu_latency_count_q[0] = 0;
    cpu_latency_count_q[1] = 0;

    cpu_req_valid[0] = 1'b0;
    cpu_req_valid[1] = 1'b0;
    cpu_req_addr[0] = '0;
    cpu_req_addr[1] = '0;
    cpu_req_write[0] = 1'b0;
    cpu_req_write[1] = 1'b0;
    cpu_req_wmask[0] = '0;
    cpu_req_wmask[1] = '0;
    cpu_req_wdata[0] = '0;
    cpu_req_wdata[1] = '0;
    cpu_resp_ready[0] = 1'b1;
    cpu_resp_ready[1] = 1'b1;
    mmio_req_ready = 1'b1;
    mmio_resp_valid = 1'b0;
    mmio_resp_rdata = '0;
    apb_psel = 1'b0;
    apb_penable = 1'b0;
    apb_pwrite = 1'b0;
    apb_paddr = '0;
    ref_write_ptr_q = 0;
    for (i = 0; i < 64; i = i + 1) begin
      ref_valid_q[i] = 1'b0;
      ref_addr_q[i] = '0;
      ref_data_q[i] = '0;
    end

    repeat (5) @(posedge clock);
    @(negedge clock);
    reset = 1'b0;

    // Cold miss, cross-core sharing, upgrade, and snoop-visible store data.
    address = 32'h0000_1000;
    cpu_access(0, 1'b0, address, '0, 1'b1, expected_word(address));
    cpu_access(1, 1'b0, address, '0, 1'b1, expected_word(address));
    value = 64'hdeed_1000_cafe_0001;
    cpu_access(0, 1'b1, address, value, 1'b0, '0);
    update_reference(address, value);
    cpu_access(1, 1'b0, address, '0, 1'b1, expected_word(address));

    // Nine dirty lines map to one L1/L2 set. This forces L1 PutM traffic,
    // inclusive L2 victim recovery, an AXI writeback, and a later memory refill.
    first_conflict_address = 32'h0000_2000;
    first_conflict_data = 64'hc001_cafe_0000_0000;
    for (i = 0; i < 9; i = i + 1) begin
      address = first_conflict_address + i * 32'h0000_8000;
      value = first_conflict_data + i;
      cpu_access(i & 1, 1'b1, address, value, 1'b0, '0);
      update_reference(address, value);
    end
    cpu_access(1, 1'b0, first_conflict_address, '0, 1'b1,
               expected_word(first_conflict_address));

    // Exercise additional read/write hits and misses across both LSU ports.
    for (operation = 0; operation < 48; operation = operation + 1) begin
      random_state = random_state * 1664525 + 1013904223;
      selector = ((random_state >> 8) & 32'h7fff_ffff) % 9;
      address = first_conflict_address + selector * 32'h0000_8000;
      if (((random_state >> 4) & 3) == 0) begin
        value = 64'hbabe_0000_0000_0000 ^
                {32'b0, benchmark_seed[31:0]} ^ operation;
        cpu_access(random_state & 1, 1'b1, address, value, 1'b0, '0);
        update_reference(address, value);
      end else begin
        cpu_access(random_state & 1, 1'b0, address, '0, 1'b1,
                   expected_word(address));
      end
    end

    // Independent different-set misses should overlap in the memory refill path.
    fork
      cpu_access(0, 1'b0, 32'h0000_6000, '0, 1'b1,
                 expected_word(32'h0000_6000));
      cpu_access(1, 1'b0, 32'h0000_7000, '0, 1'b1,
                 expected_word(32'h0000_7000));
    join

    repeat (8) @(posedge clock);
    if (fatal_error || axi_adapter_protocol_error || memory_adapter_error ||
        memory_adapter_protocol_error || mmio_protocol_error ||
        directory_protocol_error || l2_protocol_error ||
        (|l1_controller_protocol_error) || (|l1_array_protocol_error))
      $fatal(1, "end-to-end AXI/MESI test raised a fatal or protocol error");
    if ((accepted_ar_count_q == 0) ||
        (returned_r_beat_count_q != accepted_ar_count_q * 8))
      $fatal(1, "AXI read burst accounting mismatch AR=%0d R=%0d",
             accepted_ar_count_q, returned_r_beat_count_q);
    if (peak_read_outstanding_q < 2)
      $fatal(1, "parallel refill coverage missing: peak AXI reads=%0d",
             peak_read_outstanding_q);
    if ((accepted_aw_count_q == 0) ||
        (accepted_w_beat_count_q != accepted_aw_count_q * 8) ||
        (returned_b_count_q != accepted_aw_count_q))
      $fatal(1, "AXI write burst accounting mismatch AW=%0d W=%0d B=%0d",
             accepted_aw_count_q, accepted_w_beat_count_q, returned_b_count_q);
    if ((ar_stall_count_q == 0) || (aw_stall_count_q == 0) ||
        (w_stall_count_q == 0))
      $fatal(1, "AXI backpressure coverage missing: AR=%0d AW=%0d W=%0d",
             ar_stall_count_q, aw_stall_count_q, w_stall_count_q);
    if (($test$plusargs("stall_r") || $test$plusargs("stall_rb")) &&
        (forced_r_stall_cycles < 5))
      $fatal(1, "requested AXI R backpressure was not injected");
    if (($test$plusargs("stall_b") || $test$plusargs("stall_rb")) &&
        (forced_b_stall_cycles < 5))
      $fatal(1, "requested AXI B backpressure was not injected");

    apb_read(32'h04, csr_value);
    if (csr_value == 0) $fatal(1, "APB miss counter did not observe AXI traffic");
    apb_read(32'h08, csr_value);
    if (csr_value == 0) $fatal(1, "APB snoop counter did not observe coherence");
    apb_read(32'h0c, csr_value);
    if (csr_value == 0) $fatal(1, "APB dirty-writeback counter stayed zero");
    apb_read(32'h10, csr_value);
    if (csr_value != 0) $fatal(1, "APB protocol/error status is not clear: %08x", csr_value);

    total_ops = cpu_latency_count_q[0] + cpu_latency_count_q[1];
    latency_count = 0;
    mean_latency = 0.0;
    for (i = 0; i < cpu_latency_count_q[0]; i = i + 1) begin
      sorted_latency[latency_count] = cpu_latency_samples_q[0][i];
      mean_latency = mean_latency + $itor(cpu_latency_samples_q[0][i]);
      latency_count = latency_count + 1;
    end
    for (i = 0; i < cpu_latency_count_q[1]; i = i + 1) begin
      sorted_latency[latency_count] = cpu_latency_samples_q[1][i];
      mean_latency = mean_latency + $itor(cpu_latency_samples_q[1][i]);
      latency_count = latency_count + 1;
    end
    if (latency_count != total_ops || total_ops == 0 || cycle_count_q == 0)
      $fatal(1, "invalid CPU benchmark accounting");
    for (i = 1; i < latency_count; i = i + 1) begin
      latency_temp = sorted_latency[i];
      selector = i;
      while ((selector > 0) &&
             (sorted_latency[selector-1] > latency_temp)) begin
        sorted_latency[selector] = sorted_latency[selector-1];
        selector = selector - 1;
      end
      sorted_latency[selector] = latency_temp;
    end
    mean_latency = mean_latency / $itor(total_ops);
    latency_p95 = sorted_latency[((95 * latency_count + 99) / 100) - 1];
    ops_per_cycle = $itor(total_ops) / $itor(cycle_count_q);
    read_bytes_per_cycle = $itor(returned_r_beat_count_q * 8) /
                           $itor(cycle_count_q);
    write_bytes_per_cycle = $itor(accepted_w_beat_count_q * 8) /
                            $itor(cycle_count_q);
    total_bytes_per_cycle = read_bytes_per_cycle + write_bytes_per_cycle;

    $display("AXI RAM: AR=%0d R-beats=%0d peak-RD=%0d AW=%0d W-beats=%0d B=%0d stalls(ar/aw/w)=%0d/%0d/%0d",
             accepted_ar_count_q, returned_r_beat_count_q,
             peak_read_outstanding_q,
             accepted_aw_count_q, accepted_w_beat_count_q,
             returned_b_count_q, ar_stall_count_q, aw_stall_count_q,
             w_stall_count_q);
    $display("AXI_TOP_BENCH,{\"seed\":%0d,\"cycles\":%0d,\"ops\":%0d,\"mean_latency_cycles\":%0.6f,\"p95_latency_cycles\":%0d,\"ops_per_cycle\":%0.8f,\"read_beats\":%0d,\"write_beats\":%0d,\"read_bytes_per_cycle\":%0.8f,\"write_bytes_per_cycle\":%0.8f,\"total_bytes_per_cycle\":%0.8f,\"peak_read_outstanding\":%0d,\"ar_stalls\":%0d,\"aw_stalls\":%0d,\"w_stalls\":%0d,\"r_stalls\":%0d,\"b_stalls\":%0d}",
             benchmark_seed, cycle_count_q, total_ops, mean_latency,
             latency_p95, ops_per_cycle, returned_r_beat_count_q,
             accepted_w_beat_count_q, read_bytes_per_cycle,
             write_bytes_per_cycle, total_bytes_per_cycle,
             peak_read_outstanding_q, ar_stall_count_q, aw_stall_count_q,
             w_stall_count_q, r_stall_count_q, b_stall_count_q);
    $display("PASS: AXI memory-model end-to-end MESI read/write stress");
    $finish;
  end
