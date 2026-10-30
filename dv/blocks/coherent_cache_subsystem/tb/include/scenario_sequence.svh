  initial begin
    logic [63:0] ignored;
    logic [31:0] line_addr;
    logic [31:0] word_addr;
    logic [63:0] initial_word;
    logic [63:0] value0;
    logic [63:0] value1;
    logic [63:0] value2;
    logic [63:0] value3;
    logic [63:0] value4;
    logic [63:0] masked_value;
    logic [31:0] clean_owner_line;
    logic [31:0] clean_owner_word_addr;
    logic [63:0] clean_owner_value;
    logic [31:0] mmio_addr;
    logic [63:0] mmio_initial;
    logic [63:0] mmio_masked;
    logic [63:0] mmio_data;
    integer mmio_count_before;
    logic [31:0] eviction_line_addr;
    logic [31:0] eviction_word_addr;
    logic [31:0] l2_test_addr [0:8];
    logic [63:0] l2_dirty_value;
    logic fanout_victim_written;
    logic [31:0] shared_addr;
    logic [31:0] snoop_write_race_addr;
    logic [63:0] snoop_write_race_data;
    logic [63:0] snoop_write_race_readback;
    logic [31:0] different_snoop_cpu_addr;
    logic [31:0] different_snoop_target_addr;
    logic [63:0] different_snoop_cpu_data;
    logic [63:0] different_snoop_target_data;
    logic [31:0] random_addr;
    logic [31:0] random_state;
    logic [31:0] random_seed;
    logic [63:0] random_data;
    logic [63:0] concurrent_data0;
    logic [63:0] concurrent_data1;
    logic [63:0] stalled_data;
    logic last_writer;
    integer cycles;
    integer random_index;
    integer random_core;
    logic [7:0] random_mask;
    integer line_number;
    integer core;
    integer l2_line_number;
    integer memory_slot_index;
    logic found_written_victim;
    logic failed_victim_found;
    logic failed_victim_dirty;

    reset = 1'b1;
    stall_mem_rd_req = 1'b0;
    stall_mem_wr_req = 1'b0;
    stall_mem_wr_data = 1'b0;
    stall_mmio_req = 1'b0;
    inject_periodic_stalls = 1'b0;
    inject_next_mem_rd_error = 1'b0;
    inject_next_mem_wr_error = 1'b0;
    cycle_count = 0;
    benchmark_read_hit_count = 0;
    benchmark_read_hit_cycles = 0;
    benchmark_write_hit_count = 0;
    benchmark_write_hit_cycles = 0;
    benchmark_upgrade_count = 0;
    benchmark_upgrade_cycles = 0;
    benchmark_l1_miss_count = 0;
    benchmark_l1_miss_cycles = 0;
    benchmark_request_ready_stall_cycles = 0;
    benchmark_model_accept_hit_count = 0;
    benchmark_model_accept_miss_count = 0;
    benchmark_rtl_hit_count = 0;
    benchmark_rtl_miss_count = 0;
    for (integer core = 0; core < 2; core = core + 1) begin
      benchmark_accept_pending[core] = 1'b0;
      benchmark_accept_write[core] = 1'b0;
      benchmark_accept_state[core] = MESI_I;
      benchmark_accept_cycle[core] = 0;
    end
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
    mmio_saved_addr_q = '0;
    mmio_saved_data_q = '0;
    mmio_saved_valid_q = 1'b0;
    for (integer slot = 0; slot < 128; slot = slot + 1) begin
      memory_slot_valid[slot] = 1'b0;
      memory_slot_addr[slot] = '0;
      for (integer beat = 0; beat < 8; beat = beat + 1)
        backing_store[slot][beat] = '0;
    end
    for (core = 0; core < 2; core = core + 1) begin
      cpu_req_valid[core] = 1'b0;
      cpu_req_addr[core] = 32'b0;
      cpu_req_write[core] = 1'b0;
      cpu_req_wmask[core] = 8'b0;
      cpu_req_wdata[core] = 64'b0;
      cpu_resp_ready[core] = 1'b1;
    end

    cpu_req_valid[0] = 1'b1;
    cpu_req_addr[0] = 32'h0000_1000;
    cpu_req_valid[1] = 1'b1;
    cpu_req_addr[1] = 32'h3000_0000;
    #1;
    if (cpu_req_ready[0] || cpu_req_ready[1] || mmio_req_valid ||
        mem_rd_req_valid || mem_wr_req_valid || cpu_resp_valid[0] ||
        cpu_resp_valid[1])
      $fatal(1, "reset must block all external cache and MMIO handshakes");
    repeat (4) @(posedge clock);
    @(negedge clock);
    cpu_req_valid[0] = 1'b0;
    cpu_req_valid[1] = 1'b0;
    reset = 1'b0;

    line_addr = 32'h0000_1000;
    word_addr = line_addr + 32'd24;
    initial_word = memory_word(line_addr, 3'd3);
    value0 = 64'h0123_4567_89AB_CDEF;
    value1 = 64'hFEDC_BA98_7654_3210;
    value2 = 64'h1122_3344_5566_7788;
    value3 = 64'hAABB_CCDD_EEFF_0011;
    value4 = 64'hDEAD_BEEF_CAFE_1234;
    clean_owner_line = 32'h0000_6000;
    clean_owner_word_addr = clean_owner_line + 32'd24;
    clean_owner_value = 64'h7654_3210_FEDC_BA98;
    mmio_addr = 32'h3000_0018;
    mmio_initial = mmio_initial_word(mmio_addr);
    mmio_masked = (mmio_initial & 64'hFFFF_FFFF_0000_0000) |
                  (value3 & 64'h0000_0000_FFFF_FFFF);
    mmio_count_before = mmio_request_count;

`include "include/l2_multisnoop_victim.svh"

`include "include/backpressure_cases.svh"

`include "include/mesi_and_concurrency_cases.svh"

`include "include/replacement_and_l2_victims.svh"

`include "include/random_and_reset_cases.svh"

`include "include/error_and_summary_cases.svh"
