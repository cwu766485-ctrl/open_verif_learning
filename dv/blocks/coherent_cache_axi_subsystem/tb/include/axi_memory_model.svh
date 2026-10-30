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
