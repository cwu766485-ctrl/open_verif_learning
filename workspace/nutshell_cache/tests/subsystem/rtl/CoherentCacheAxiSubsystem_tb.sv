`timescale 1ns/1ps

module CoherentCacheAxiSubsystem_tb;
  import coherence_protocol_pkg::*;
  localparam int TXN_ID_WIDTH = coherence_protocol_pkg::TXN_ID_WIDTH;
  localparam int MODEL_SLOTS = 4;
  localparam int MEMORY_LINES = 64;

  logic clock = 1'b0;
  logic reset = 1'b1;

  logic cpu_req_valid [0:1];
  logic cpu_req_ready [0:1];
  logic [31:0] cpu_req_addr [0:1];
  logic cpu_req_write [0:1];
  logic [7:0] cpu_req_wmask [0:1];
  logic [63:0] cpu_req_wdata [0:1];
  logic cpu_resp_valid [0:1];
  logic cpu_resp_ready [0:1];
  logic [31:0] cpu_resp_addr [0:1];
  logic cpu_resp_write [0:1];
  logic [63:0] cpu_resp_rdata [0:1];
  logic [TXN_ID_WIDTH-1:0] cpu_resp_txn_id [0:1];

  logic mmio_req_valid, mmio_req_ready;
  logic [31:0] mmio_req_addr;
  logic [2:0] mmio_req_size;
  logic mmio_req_write;
  logic [7:0] mmio_req_wmask;
  logic [63:0] mmio_req_wdata;
  logic mmio_resp_valid, mmio_resp_ready;
  logic [63:0] mmio_resp_rdata;

  logic apb_psel, apb_penable, apb_pwrite;
  logic [31:0] apb_paddr;
  logic apb_pready;
  logic [31:0] apb_prdata;
  logic apb_pslverr;

  logic [TXN_ID_WIDTH-1:0] axi_arid;
  logic [31:0] axi_araddr;
  logic [7:0] axi_arlen;
  logic [2:0] axi_arsize;
  logic [1:0] axi_arburst;
  logic axi_arlock;
  logic [3:0] axi_arcache;
  logic [2:0] axi_arprot;
  logic axi_arvalid, axi_arready;
  logic [TXN_ID_WIDTH-1:0] axi_rid;
  logic [63:0] axi_rdata;
  logic [1:0] axi_rresp;
  logic axi_rlast, axi_rvalid, axi_rready;

  logic [TXN_ID_WIDTH-1:0] axi_awid;
  logic [31:0] axi_awaddr;
  logic [7:0] axi_awlen;
  logic [2:0] axi_awsize;
  logic [1:0] axi_awburst;
  logic axi_awlock;
  logic [3:0] axi_awcache;
  logic [2:0] axi_awprot;
  logic axi_awvalid, axi_awready;
  logic [63:0] axi_wdata;
  logic [7:0] axi_wstrb;
  logic axi_wlast, axi_wvalid, axi_wready;
  logic [TXN_ID_WIDTH-1:0] axi_bid;
  logic [1:0] axi_bresp;
  logic axi_bvalid, axi_bready;

  logic [1:0] l1_controller_protocol_error;
  logic [1:0] l1_array_protocol_error;
  logic directory_protocol_error, l2_protocol_error;
  logic memory_adapter_protocol_error, memory_adapter_error;
  logic axi_adapter_protocol_error, mmio_protocol_error, fatal_error;

  CoherentCacheAxiSubsystem dut (.*);

  always #5 clock = ~clock;

  function automatic logic [63:0] cold_word(input logic [31:0] byte_addr);
    cold_word = 64'h1357_9bdf_2468_ace0 ^ {32'b0, {byte_addr[31:3], 3'b000}};
  endfunction

  logic memory_valid_q [0:MEMORY_LINES-1];
  logic [31:0] memory_line_addr_q [0:MEMORY_LINES-1];
  logic [63:0] memory_line_q [0:MEMORY_LINES-1][0:7];

  function automatic logic [63:0] memory_read_word(input logic [31:0] byte_addr);
    logic [31:0] line_addr;
    logic [63:0] value;
    line_addr = {byte_addr[31:6], 6'b0};
    value = cold_word(byte_addr);
    for (integer i = 0; i < MEMORY_LINES; i = i + 1)
      if (memory_valid_q[i] && (memory_line_addr_q[i] == line_addr))
        value = memory_line_q[i][byte_addr[5:3]];
    return value;
  endfunction

  logic rd_active_q [0:MODEL_SLOTS-1];
  logic [TXN_ID_WIDTH-1:0] rd_id_q [0:MODEL_SLOTS-1];
  logic [31:0] rd_addr_q [0:MODEL_SLOTS-1];
  logic [2:0] rd_beat_q [0:MODEL_SLOTS-1];
  integer rd_delay_q [0:MODEL_SLOTS-1];
  integer rd_pick_q;
  logic r_hold_valid_q;
  integer r_hold_slot_q;
  logic [TXN_ID_WIDTH-1:0] r_hold_id_q;
  logic [2:0] r_hold_beat_q;
  logic [63:0] r_hold_data_q;

  logic [TXN_ID_WIDTH-1:0] aw_fifo_id_q [0:MODEL_SLOTS-1];
  integer aw_fifo_mem_slot_q [0:MODEL_SLOTS-1];
  integer aw_fifo_head_q, aw_fifo_tail_q, aw_fifo_count_q;
  integer model_w_beat_q;
  logic b_pending_q [0:MODEL_SLOTS-1];
  logic [TXN_ID_WIDTH-1:0] b_id_q [0:MODEL_SLOTS-1];
  integer b_delay_q [0:MODEL_SLOTS-1];
  integer b_pick_q;
  logic b_hold_valid_q;
  integer b_hold_slot_q;
  logic [TXN_ID_WIDTH-1:0] b_hold_id_q;

  integer cycle_count_q;
  integer aw_forced_stall_cycles_q;
  logic aw_forced_stall_done_q;
  integer accepted_ar_count_q, returned_r_beat_count_q;
  integer peak_read_outstanding_q;
  integer accepted_aw_count_q, accepted_w_beat_count_q, returned_b_count_q;
  integer ar_stall_count_q, aw_stall_count_q, w_stall_count_q;
  integer r_stall_count_q, b_stall_count_q;
  integer forced_r_stall_cycles;
  integer forced_b_stall_cycles;
  integer cpu_latency_count_q [0:1];
  integer cpu_latency_samples_q [0:1][0:255];

  always_comb begin
    axi_arready = !reset && ((cycle_count_q % 7) != 0) &&
                  ((cycle_count_q % 5) != 1);
    axi_awready = !reset && aw_forced_stall_done_q &&
                  ((cycle_count_q % 5) != 0);
    axi_wready = !reset && ((cycle_count_q % 4) != 1);
    axi_rvalid = r_hold_valid_q;
    axi_rid = r_hold_id_q;
    axi_rdata = r_hold_data_q;
    axi_rresp = 2'b00;
    axi_rlast = (r_hold_beat_q == 3'd7);
    axi_bvalid = b_hold_valid_q;
    axi_bid = b_hold_id_q;
    axi_bresp = 2'b00;
  end

  always_ff @(posedge clock) begin : axi_memory_model
    integer active_rd_count;
    integer next_rd_count;
    integer free_rd;
    integer free_b;
    integer existing_mem;
    integer free_mem;
    integer chosen;
    integer candidate;
    integer model_slot;
    integer scan;
    if (reset) begin
      aw_fifo_head_q <= 0;
      aw_fifo_tail_q <= 0;
      aw_fifo_count_q <= 0;
      model_w_beat_q <= 0;
      rd_pick_q <= 0;
      r_hold_valid_q <= 1'b0;
      r_hold_slot_q <= 0;
      r_hold_id_q <= '0;
      r_hold_beat_q <= '0;
      r_hold_data_q <= '0;
      b_pick_q <= 0;
      b_hold_valid_q <= 1'b0;
      b_hold_slot_q <= 0;
      b_hold_id_q <= '0;
      cycle_count_q <= 0;
      aw_forced_stall_cycles_q <= 0;
      aw_forced_stall_done_q <= 1'b0;
      accepted_ar_count_q <= 0;
      peak_read_outstanding_q <= 0;
      returned_r_beat_count_q <= 0;
      accepted_aw_count_q <= 0;
      accepted_w_beat_count_q <= 0;
      returned_b_count_q <= 0;
      ar_stall_count_q <= 0;
      aw_stall_count_q <= 0;
      w_stall_count_q <= 0;
      r_stall_count_q <= 0;
      b_stall_count_q <= 0;
      for (integer i = 0; i < MODEL_SLOTS; i = i + 1) begin
        rd_active_q[i] <= 1'b0;
        rd_id_q[i] <= '0;
        rd_addr_q[i] <= '0;
        rd_beat_q[i] <= '0;
        rd_delay_q[i] <= 0;
        aw_fifo_id_q[i] <= '0;
        aw_fifo_mem_slot_q[i] <= 0;
        b_pending_q[i] <= 1'b0;
        b_id_q[i] <= '0;
        b_delay_q[i] <= 0;
      end
      for (integer i = 0; i < MEMORY_LINES; i = i + 1) begin
        memory_valid_q[i] <= 1'b0;
        memory_line_addr_q[i] <= '0;
        for (integer b = 0; b < 8; b = b + 1)
          memory_line_q[i][b] <= '0;
      end
    end else begin
      cycle_count_q <= cycle_count_q + 1;
      active_rd_count = 0;
      for (integer i = 0; i < MODEL_SLOTS; i = i + 1)
        if (rd_active_q[i]) active_rd_count = active_rd_count + 1;
      next_rd_count = active_rd_count;
      if (axi_arvalid && axi_arready) next_rd_count = next_rd_count + 1;
      if (r_hold_valid_q && axi_rready && (r_hold_beat_q == 3'd7))
        next_rd_count = next_rd_count - 1;
      if (next_rd_count > peak_read_outstanding_q)
        peak_read_outstanding_q <= next_rd_count;
      if (axi_awvalid && !aw_forced_stall_done_q) begin
        if (aw_forced_stall_cycles_q == 2)
          aw_forced_stall_done_q <= 1'b1;
        else
          aw_forced_stall_cycles_q <= aw_forced_stall_cycles_q + 1;
      end
      for (integer i = 0; i < MODEL_SLOTS; i = i + 1) begin
        if (rd_delay_q[i] > 0) rd_delay_q[i] <= rd_delay_q[i] - 1;
        if (b_delay_q[i] > 0) b_delay_q[i] <= b_delay_q[i] - 1;
      end

      if (axi_arvalid && !axi_arready) ar_stall_count_q <= ar_stall_count_q + 1;
      if (axi_awvalid && !axi_awready) aw_stall_count_q <= aw_stall_count_q + 1;
      if (axi_wvalid && !axi_wready) w_stall_count_q <= w_stall_count_q + 1;
      if (axi_rvalid && !axi_rready) r_stall_count_q <= r_stall_count_q + 1;
      if (axi_bvalid && !axi_bready) b_stall_count_q <= b_stall_count_q + 1;

      if (axi_arvalid && axi_arready) begin
        free_rd = -1;
        for (integer i = 0; i < MODEL_SLOTS; i = i + 1)
          if (!rd_active_q[i] && (free_rd < 0)) free_rd = i;
        if (free_rd < 0) $fatal(1, "AXI RAM read slot overflow");
        if ((axi_arlen != 8'd7) || (axi_arsize != 3'b011) ||
            (axi_arburst != 2'b01) || (axi_araddr[5:0] != 0))
          $fatal(1, "cache emitted malformed AXI AR burst");
        rd_active_q[free_rd] <= 1'b1;
        rd_id_q[free_rd] <= axi_arid;
        rd_addr_q[free_rd] <= axi_araddr;
        rd_beat_q[free_rd] <= '0;
        rd_delay_q[free_rd] <= 1 + ((cycle_count_q + axi_arid) % 6);
        accepted_ar_count_q <= accepted_ar_count_q + 1;
      end

      if (r_hold_valid_q && axi_rready) begin
        returned_r_beat_count_q <= returned_r_beat_count_q + 1;
        if (r_hold_beat_q == 3'd7) begin
          rd_active_q[r_hold_slot_q] <= 1'b0;
          rd_beat_q[r_hold_slot_q] <= '0;
        end else begin
          rd_beat_q[r_hold_slot_q] <= rd_beat_q[r_hold_slot_q] + 1'b1;
        end
        r_hold_valid_q <= 1'b0;
      end

      if (!r_hold_valid_q) begin
        chosen = -1;
        for (integer offset = 0; offset < MODEL_SLOTS; offset = offset + 1) begin
          candidate = (rd_pick_q + offset) % MODEL_SLOTS;
          if ((chosen < 0) && rd_active_q[candidate] &&
              (rd_delay_q[candidate] == 0))
            chosen = candidate;
        end
        if (chosen >= 0) begin
          r_hold_valid_q <= 1'b1;
          r_hold_slot_q <= chosen;
          r_hold_id_q <= rd_id_q[chosen];
          r_hold_beat_q <= rd_beat_q[chosen];
          r_hold_data_q <= memory_read_word(
            rd_addr_q[chosen] + {26'b0, rd_beat_q[chosen], 3'b000});
          rd_pick_q <= (chosen + 1) % MODEL_SLOTS;
        end
      end

      if (axi_awvalid && axi_awready) begin
        existing_mem = -1;
        free_mem = -1;
        for (integer i = 0; i < MEMORY_LINES; i = i + 1) begin
          if (memory_valid_q[i] && (memory_line_addr_q[i] == axi_awaddr))
            existing_mem = i;
          if (!memory_valid_q[i] && (free_mem < 0)) free_mem = i;
        end
        model_slot = (existing_mem >= 0) ? existing_mem : free_mem;
        if (model_slot < 0) $fatal(1, "AXI RAM backing store is full");
        if ((axi_awlen != 8'd7) || (axi_awsize != 3'b011) ||
            (axi_awburst != 2'b01) || (axi_awaddr[5:0] != 0))
          $fatal(1, "cache emitted malformed AXI AW burst");
        if (existing_mem < 0) begin
          memory_valid_q[model_slot] <= 1'b1;
          memory_line_addr_q[model_slot] <= axi_awaddr;
          for (integer b = 0; b < 8; b = b + 1)
            memory_line_q[model_slot][b] <= cold_word(axi_awaddr + b * 8);
        end
        if (aw_fifo_count_q >= MODEL_SLOTS)
          $fatal(1, "AXI RAM write address queue overflow");
        aw_fifo_id_q[aw_fifo_tail_q] <= axi_awid;
        aw_fifo_mem_slot_q[aw_fifo_tail_q] <= model_slot;
        aw_fifo_tail_q <= (aw_fifo_tail_q + 1) % MODEL_SLOTS;
        aw_fifo_count_q <= aw_fifo_count_q + 1;
        accepted_aw_count_q <= accepted_aw_count_q + 1;
      end

      if (axi_wvalid && axi_wready) begin
        if (aw_fifo_count_q == 0)
          $fatal(1, "AXI RAM observed W without a prior AW");
        if (axi_wlast != (model_w_beat_q == 7))
          $fatal(1, "AXI WLAST position mismatch at beat %0d", model_w_beat_q);
        model_slot = aw_fifo_mem_slot_q[aw_fifo_head_q];
        memory_line_q[model_slot][model_w_beat_q] <= axi_wdata;
        accepted_w_beat_count_q <= accepted_w_beat_count_q + 1;
        if (model_w_beat_q == 7) begin
          free_b = -1;
          for (integer i = 0; i < MODEL_SLOTS; i = i + 1)
            if (!b_pending_q[i] && (free_b < 0)) free_b = i;
          if (free_b < 0) $fatal(1, "AXI RAM B response slot overflow");
          b_pending_q[free_b] <= 1'b1;
          b_id_q[free_b] <= aw_fifo_id_q[aw_fifo_head_q];
          b_delay_q[free_b] <= 1 + ((cycle_count_q + aw_fifo_id_q[aw_fifo_head_q]) % 5);
          aw_fifo_head_q <= (aw_fifo_head_q + 1) % MODEL_SLOTS;
          aw_fifo_count_q <= aw_fifo_count_q - 1;
          model_w_beat_q <= 0;
        end else begin
          model_w_beat_q <= model_w_beat_q + 1;
        end
      end

      if (b_hold_valid_q && axi_bready) begin
        b_pending_q[b_hold_slot_q] <= 1'b0;
        returned_b_count_q <= returned_b_count_q + 1;
        b_hold_valid_q <= 1'b0;
      end
      if (!b_hold_valid_q) begin
        chosen = -1;
        for (integer offset = 0; offset < MODEL_SLOTS; offset = offset + 1) begin
          candidate = (b_pick_q + offset) % MODEL_SLOTS;
          if ((chosen < 0) && b_pending_q[candidate] &&
              (b_delay_q[candidate] == 0))
            chosen = candidate;
        end
        if (chosen >= 0) begin
          b_hold_valid_q <= 1'b1;
          b_hold_slot_q <= chosen;
          b_hold_id_q <= b_id_q[chosen];
          b_pick_q <= (chosen + 1) % MODEL_SLOTS;
        end
      end
    end
  end

  logic ref_valid_q [0:63];
  logic [31:0] ref_addr_q [0:63];
  logic [63:0] ref_data_q [0:63];
  integer ref_write_ptr_q;

  function automatic logic [63:0] expected_word(input logic [31:0] byte_addr);
    logic [63:0] value;
    value = cold_word(byte_addr);
    for (integer i = 0; i < 64; i = i + 1)
      if (ref_valid_q[i] && (ref_addr_q[i] == {byte_addr[31:3],3'b000}))
        value = ref_data_q[i];
    return value;
  endfunction

  task automatic update_reference(input logic [31:0] byte_addr,
                                  input logic [63:0] value);
    integer found;
    found = -1;
    for (integer i = 0; i < 64; i = i + 1)
      if (ref_valid_q[i] && (ref_addr_q[i] == {byte_addr[31:3],3'b000}))
        found = i;
    if (found < 0) begin
      found = ref_write_ptr_q;
      ref_write_ptr_q = (ref_write_ptr_q + 1) % 64;
    end
    ref_valid_q[found] = 1'b1;
    ref_addr_q[found] = {byte_addr[31:3],3'b000};
    ref_data_q[found] = value;
  endtask

  task automatic cpu_access(input integer core,
                            input logic is_write,
                            input logic [31:0] addr,
                            input logic [63:0] write_data,
                            input logic check_read,
                            input logic [63:0] expected);
    logic request_accepted;
    logic response_seen;
    integer latency_cycles;
    begin
      @(negedge clock);
      cpu_req_valid[core] = 1'b1;
      cpu_req_addr[core] = addr;
      cpu_req_write[core] = is_write;
      cpu_req_wmask[core] = 8'hff;
      cpu_req_wdata[core] = write_data;
      request_accepted = 1'b0;
      while (!request_accepted) begin
        @(posedge clock);
        request_accepted = cpu_req_ready[core];
      end
      @(negedge clock);
      cpu_req_valid[core] = 1'b0;
      response_seen = 1'b0;
      latency_cycles = 0;
      while (!response_seen) begin
        @(posedge clock);
        latency_cycles = latency_cycles + 1;
        if (cpu_resp_valid[core] && cpu_resp_ready[core]) begin
          if (cpu_resp_addr[core] != addr)
            $fatal(1, "core %0d response address mismatch", core);
          if (!is_write && check_read && (cpu_resp_rdata[core] != expected))
            $fatal(1, "core %0d read %08x returned %016x expected %016x",
                   core, addr, cpu_resp_rdata[core], expected);
          response_seen = 1'b1;
        end
      end
      if (cpu_latency_count_q[core] >= 256)
        $fatal(1, "CPU latency sample array overflow for core %0d", core);
      cpu_latency_samples_q[core][cpu_latency_count_q[core]] = latency_cycles;
      cpu_latency_count_q[core] = cpu_latency_count_q[core] + 1;
    end
  endtask

  task automatic apb_read(input logic [31:0] addr,
                          output logic [31:0] value);
    begin
      @(negedge clock);
      apb_psel = 1'b1;
      apb_penable = 1'b0;
      apb_pwrite = 1'b0;
      apb_paddr = addr;
      @(negedge clock);
      apb_penable = 1'b1;
      #1;
      if (!apb_pready || apb_pslverr)
        $fatal(1, "APB CSR read failed at offset %08x", addr);
      value = apb_prdata;
      @(negedge clock);
      apb_psel = 1'b0;
      apb_penable = 1'b0;
    end
  endtask

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

  // Force the top-level master READY low only after a response is presented.
  // The source must keep VALID/ID/data/beat/last stable for five cycles and
  // then drain normally when READY is released.
  initial begin : axi_response_backpressure_injection
    logic do_r_stall;
    logic do_b_stall;
    logic [TXN_ID_WIDTH-1:0] held_id;
    logic [63:0] held_data;
    logic held_last;
    logic [1:0] held_resp;
    do_r_stall = $test$plusargs("stall_r") || $test$plusargs("stall_rb");
    do_b_stall = $test$plusargs("stall_b") || $test$plusargs("stall_rb");
    wait (!reset);
    if (do_r_stall) begin
      wait (axi_rvalid);
      held_id = axi_rid;
      held_data = axi_rdata;
      held_last = axi_rlast;
      held_resp = axi_rresp;
      force dut.cache_core.mem_rd_data_ready = 1'b0;
      repeat (5) begin
        @(posedge clock); #1;
        if (!axi_rvalid || axi_rready || axi_rid != held_id ||
            axi_rdata != held_data || axi_rresp != held_resp ||
            axi_rlast != held_last)
          $fatal(1, "AXI R response changed during forced backpressure");
        forced_r_stall_cycles = forced_r_stall_cycles + 1;
      end
      release dut.cache_core.mem_rd_data_ready;
    end
    if (do_b_stall) begin
      wait (axi_bvalid);
      held_id = axi_bid;
      held_resp = axi_bresp;
      force dut.cache_core.mem_wr_rsp_ready = 1'b0;
      repeat (5) begin
        @(posedge clock); #1;
        if (!axi_bvalid || axi_bready || axi_bid != held_id ||
            axi_bresp != held_resp)
          $fatal(1, "AXI B response changed during forced backpressure");
        forced_b_stall_cycles = forced_b_stall_cycles + 1;
      end
      release dut.cache_core.mem_wr_rsp_ready;
    end
  end

  initial begin
    #5_000_000;
    $fatal(1, "end-to-end AXI cache test timed out");
  end
endmodule
