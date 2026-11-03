    // Exercise the APB counters and status mapping.
    hit_event = 2'b01;
    miss_event = 2'b10;
    snoop_event = 2'b11;
    dirty_writeback_event = 1'b1;
    cache_inflight = 2'b01;
    tick();
    @(negedge clock);
    hit_event = '0;
    miss_event = '0;
    snoop_event = '0;
    dirty_writeback_event = 1'b0;
    cache_inflight = '0;
    access_complete_event = 2'b01;
    error_status = 5'b0_1101;
    tick();
    @(negedge clock);
    access_complete_event = '0;
    repeat (2) tick();
    apb_read(32'h00, 32'd1);
    apb_read(32'h04, 32'd1);
    apb_read(32'h08, 32'd2);
    apb_read(32'h0c, 32'd1);
    apb_read(32'h10, 32'h0000_000d);
    apb_read(32'h14, 32'd1);
    apb_read(32'h18, 32'd1);

    @(negedge clock);
    apb_psel = 1'b1;
    apb_penable = 1'b0;
    apb_pwrite = 1'b1;
    apb_paddr = 32'h00;
    @(negedge clock);
    apb_penable = 1'b1;
    #1;
    if (!apb_pready || !apb_pslverr)
      $fatal(1, "APB writes must be rejected by the read-only CSR block");
    @(negedge clock);
    apb_psel = 1'b0;
    apb_penable = 1'b0;
    apb_pwrite = 1'b0;

    // Seed the 32-bit counters at the overflow boundary so wrap semantics
    // can be checked without simulating 2^32 events. The increments below
    // still enter through the real event inputs of CachePerformanceCsr.
    @(negedge clock);
    csr.hit_count_q = 32'hffff_ffff;
    csr.miss_count_q = 32'hffff_fffe;
    csr.snoop_count_q = 32'hffff_ffff;
    csr.dirty_writeback_count_q = 32'hffff_ffff;
    csr.access_cycle_count_q = 32'hffff_ffff;
    csr.completed_access_count_q = 32'hffff_fffe;
    hit_event = 2'b01;
    miss_event = 2'b11;
    snoop_event = 2'b01;
    dirty_writeback_event = 1'b1;
    cache_inflight = 2'b01;
    access_complete_event = 2'b11;
    tick();
    @(negedge clock);
    hit_event = '0;
    miss_event = '0;
    snoop_event = '0;
    dirty_writeback_event = 1'b0;
    cache_inflight = '0;
    access_complete_event = '0;
    apb_read(32'h00, 32'd0);
    apb_read(32'h04, 32'd0);
    apb_read(32'h08, 32'd0);
    apb_read(32'h0c, 32'd0);
    apb_read(32'h14, 32'd0);
    apb_read(32'h18, 32'd0);

    // Restore a clean CSR baseline for any later block-level checks.
    @(negedge clock);
    reset = 1'b1;
    tick();
    @(negedge clock);
    reset = 1'b0;
