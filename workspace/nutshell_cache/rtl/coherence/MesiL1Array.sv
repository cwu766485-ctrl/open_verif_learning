module MesiL1Array #(
  parameter int SETS = 128,
  parameter int WAYS = 4,
  parameter int TAG_WIDTH = 19
) (
  input  logic clock,
  input  logic reset,

  input  logic [31:0] cpu_lookup_addr,
  output logic cpu_lookup_hit,
  output logic [$clog2(WAYS)-1:0] cpu_lookup_way,
  output coherence_protocol_pkg::mesi_state_t cpu_lookup_state,
  output logic [63:0] cpu_lookup_word,

  input  logic [31:0] snoop_lookup_addr,
  output logic snoop_lookup_hit,
  output logic [$clog2(WAYS)-1:0] snoop_lookup_way,
  output coherence_protocol_pkg::mesi_state_t snoop_lookup_state,

  // True when replace_way selects a currently resident victim; false when it
  // selected an invalid way for allocation.
  output logic replace_valid,
  output logic [$clog2(WAYS)-1:0] replace_way,
  output coherence_protocol_pkg::mesi_state_t replace_state,
  output logic [31:0] replace_line_addr,

  input  logic cpu_meta_write_valid,
  output logic cpu_meta_write_ready,
  input  logic [31:0] cpu_meta_write_line_addr,
  input  coherence_protocol_pkg::mesi_state_t cpu_meta_write_state,
  input  logic snoop_meta_write_valid,
  output logic snoop_meta_write_ready,
  input  logic [31:0] snoop_meta_write_line_addr,
  input  coherence_protocol_pkg::mesi_state_t snoop_meta_write_state,

  input  logic refill_valid,
  output logic refill_ready,
  input  logic [31:0] refill_line_addr,
  input  logic [$clog2(WAYS)-1:0] refill_way,
  input  logic [2:0] refill_beat_idx,
  input  logic [63:0] refill_data,
  input  logic refill_last,

  input  logic cpu_store_valid,
  output logic cpu_store_ready,
  input  logic [31:0] cpu_store_addr,
  input  logic [$clog2(WAYS)-1:0] cpu_store_way,
  input  logic [7:0] cpu_store_wmask,
  input  logic [63:0] cpu_store_wdata,

  input  logic line_rd_valid,
  output logic line_rd_ready,
  input  logic [31:0] line_rd_addr,
  output logic line_rd_hit,
  output logic line_data_valid,
  input  logic line_data_ready,
  output logic [2:0] line_data_beat_idx,
  output logic [63:0] line_data,
  output logic line_data_last,

  output logic protocol_error
);
  import coherence_protocol_pkg::*;
  localparam int SET_WIDTH = $clog2(SETS);
  localparam int WAY_WIDTH = $clog2(WAYS);

  logic valid_array [0:SETS-1][0:WAYS-1];
  logic [TAG_WIDTH-1:0] tag_array [0:SETS-1][0:WAYS-1];
  mesi_state_t state_array [0:SETS-1][0:WAYS-1];
  logic [63:0] data_array [0:SETS-1][0:WAYS-1][0:7];
  logic [WAY_WIDTH-1:0] replacement_ptr [0:SETS-1];

  logic refill_pending_q;
  logic refill_alloc_valid_q;
  logic [31:0] refill_addr_q;
  logic [WAY_WIDTH-1:0] refill_way_q;
  logic [2:0] refill_expected_beat_q;
  logic line_rd_busy_q;
  logic [SET_WIDTH-1:0] line_rd_set_q;
  logic [WAY_WIDTH-1:0] line_rd_way_q;
  logic [2:0] line_rd_beat_q;

  logic [SET_WIDTH-1:0] cpu_set;
  logic [SET_WIDTH-1:0] snoop_set;
  logic [SET_WIDTH-1:0] replace_set;
  logic [SET_WIDTH-1:0] refill_set;
  logic [SET_WIDTH-1:0] store_set;
  logic refill_way_available;
  logic [SET_WIDTH-1:0] cpu_meta_set;
  logic [SET_WIDTH-1:0] snoop_meta_set;
  logic [WAY_WIDTH-1:0] cpu_meta_way;
  logic [WAY_WIDTH-1:0] snoop_meta_way;
  logic cpu_meta_found;
  logic snoop_meta_found;
  logic [TAG_WIDTH-1:0] cpu_meta_tag;
  logic [TAG_WIDTH-1:0] snoop_meta_tag;
  logic [TAG_WIDTH-1:0] cpu_tag;
  logic [TAG_WIDTH-1:0] snoop_tag;
  logic [TAG_WIDTH-1:0] store_tag;
  integer i;
  integer j;
  integer k;

  always_comb begin
    cpu_set = cpu_lookup_addr[6 +: SET_WIDTH];
    snoop_set = snoop_lookup_addr[6 +: SET_WIDTH];
    replace_set = cpu_lookup_addr[6 +: SET_WIDTH];
    refill_set = refill_line_addr[6 +: SET_WIDTH];
    store_set = cpu_store_addr[6 +: SET_WIDTH];
    cpu_tag = cpu_lookup_addr[6+SET_WIDTH +: TAG_WIDTH];
    snoop_tag = snoop_lookup_addr[6+SET_WIDTH +: TAG_WIDTH];
    store_tag = cpu_store_addr[6+SET_WIDTH +: TAG_WIDTH];
    cpu_meta_set = cpu_meta_write_line_addr[6 +: SET_WIDTH];
    snoop_meta_set = snoop_meta_write_line_addr[6 +: SET_WIDTH];
    cpu_meta_tag = cpu_meta_write_line_addr[6+SET_WIDTH +: TAG_WIDTH];
    snoop_meta_tag = snoop_meta_write_line_addr[6+SET_WIDTH +: TAG_WIDTH];

    cpu_lookup_hit = 1'b0;
    cpu_lookup_way = '0;
    cpu_lookup_state = MESI_I;
    cpu_lookup_word = 64'b0;
    snoop_lookup_hit = 1'b0;
    snoop_lookup_way = '0;
    snoop_lookup_state = MESI_I;
    for (integer w = 0; w < WAYS; w = w + 1) begin
      if (valid_array[cpu_set][w] && tag_array[cpu_set][w] == cpu_tag) begin
        cpu_lookup_hit = 1'b1;
        cpu_lookup_way = WAY_WIDTH'(w);
        cpu_lookup_state = state_array[cpu_set][w];
        cpu_lookup_word = data_array[cpu_set][w][cpu_lookup_addr[5:3]];
      end
      if (valid_array[snoop_set][w] && tag_array[snoop_set][w] == snoop_tag) begin
        snoop_lookup_hit = 1'b1;
        snoop_lookup_way = WAY_WIDTH'(w);
        snoop_lookup_state = state_array[snoop_set][w];
      end
    end

    // Prefer an invalid way. If the set is full, choose the round-robin
    // replacement pointer and report that it contains a live victim.
    replace_valid = 1'b0;
    replace_way = replacement_ptr[replace_set];
    for (integer w = WAYS-1; w >= 0; w = w - 1) begin
      if (!valid_array[replace_set][w]) begin
        replace_way = WAY_WIDTH'(w);
      end
    end
    replace_valid = valid_array[replace_set][replace_way];
    replace_state = replace_valid ? state_array[replace_set][replace_way] : MESI_I;
    replace_line_addr = replace_valid ?
      {tag_array[replace_set][replace_way], cpu_lookup_addr[6 +: SET_WIDTH], 6'b0} :
      {cpu_tag, cpu_lookup_addr[6 +: SET_WIDTH], 6'b0};

    cpu_meta_found = 1'b0;
    cpu_meta_way = '0;
    snoop_meta_found = 1'b0;
    snoop_meta_way = '0;
    for (integer w = 0; w < WAYS; w = w + 1) begin
      if (valid_array[cpu_meta_set][w] &&
          tag_array[cpu_meta_set][w] == cpu_meta_tag) begin
        cpu_meta_found = 1'b1;
        cpu_meta_way = WAY_WIDTH'(w);
      end
      if (valid_array[snoop_meta_set][w] &&
          tag_array[snoop_meta_set][w] == snoop_meta_tag) begin
        snoop_meta_found = 1'b1;
        snoop_meta_way = WAY_WIDTH'(w);
      end
    end
    if (refill_alloc_valid_q && (refill_addr_q == cpu_meta_write_line_addr)) begin
      cpu_meta_found = 1'b1;
      cpu_meta_way = refill_way_q;
    end
    if (refill_alloc_valid_q && (refill_addr_q == snoop_meta_write_line_addr)) begin
      snoop_meta_found = 1'b1;
      snoop_meta_way = refill_way_q;
    end

    // The inferred array model exposes separate producer interfaces, but the
    // SRAM contract has one metadata write port. Snoop updates have priority;
    // CPU-side metadata remains pending until the snoop commit completes.
    snoop_meta_write_ready = 1'b1;
    cpu_meta_write_ready = !snoop_meta_write_valid;
    if (refill_pending_q &&
        (refill_addr_q == cpu_meta_write_line_addr))
      cpu_meta_write_ready = 1'b0;
    if (refill_pending_q &&
        (refill_addr_q == snoop_meta_write_line_addr))
      snoop_meta_write_ready = 1'b0;

    refill_way_available = !valid_array[refill_set][refill_way] ||
      (tag_array[refill_set][refill_way] ==
       refill_line_addr[6+SET_WIDTH +: TAG_WIDTH]);
    refill_ready = (refill_way < WAYS) && refill_way_available &&
                   ((refill_beat_idx == 3'd0) ? !refill_alloc_valid_q :
                                                refill_pending_q);
    cpu_store_ready = 1'b1;
    line_rd_ready = !line_rd_busy_q;
    line_rd_hit = 1'b0;
    for (integer w = 0; w < WAYS; w = w + 1) begin
      if (valid_array[line_rd_addr[6 +: SET_WIDTH]][w] &&
          tag_array[line_rd_addr[6 +: SET_WIDTH]][w] ==
            line_rd_addr[6+SET_WIDTH +: TAG_WIDTH])
        line_rd_hit = 1'b1;
    end
    line_data_valid = line_rd_busy_q;
    line_data_beat_idx = line_rd_beat_q;
    line_data = data_array[line_rd_set_q][line_rd_way_q][line_rd_beat_q];
    line_data_last = (line_rd_beat_q == 3'd7);
  end

  always_ff @(posedge clock) begin
    if (reset) begin
      refill_pending_q <= 1'b0;
      refill_alloc_valid_q <= 1'b0;
      refill_addr_q <= 32'b0;
      refill_way_q <= '0;
      refill_expected_beat_q <= '0;
      line_rd_busy_q <= 1'b0;
      line_rd_set_q <= '0;
      line_rd_way_q <= '0;
      line_rd_beat_q <= '0;
      protocol_error <= 1'b0;
      for (i = 0; i < SETS; i = i + 1) begin
        replacement_ptr[i] <= '0;
        for (j = 0; j < WAYS; j = j + 1) begin
          valid_array[i][j] <= 1'b0;
          tag_array[i][j] <= '0;
          state_array[i][j] <= MESI_I;
        end
      end
    end else begin
      if (refill_valid && refill_ready) begin
        if (refill_beat_idx == 3'd0) begin
          refill_pending_q <= 1'b1;
          refill_alloc_valid_q <= 1'b1;
          refill_addr_q <= {refill_line_addr[31:6], 6'b0};
          refill_way_q <= refill_way;
          refill_expected_beat_q <= 3'd1;
        end else if ((refill_line_addr[31:6] != refill_addr_q[31:6]) ||
                     (refill_way != refill_way_q) ||
                     (refill_beat_idx != refill_expected_beat_q)) begin
          protocol_error <= 1'b1;
          refill_pending_q <= 1'b0;
        end
        if ((refill_last != (refill_beat_idx == 3'd7)) ||
            ((refill_beat_idx != 3'd0) &&
             ((refill_line_addr[31:6] != refill_addr_q[31:6]) ||
              (refill_way != refill_way_q) ||
              (refill_beat_idx != refill_expected_beat_q))))
          protocol_error <= 1'b1;
        data_array[refill_set][refill_way][refill_beat_idx] <= refill_data;
        if ((refill_beat_idx != 3'd0) && refill_pending_q &&
            (refill_beat_idx == refill_expected_beat_q))
          refill_expected_beat_q <= refill_expected_beat_q + 1'b1;
        if (refill_last && (refill_beat_idx == 3'd7)) begin
          refill_pending_q <= 1'b0;
          replacement_ptr[refill_set] <= refill_way + 1'b1;
        end
      end

      if (cpu_meta_write_valid && cpu_meta_write_ready) begin
        if (cpu_meta_found) begin
          tag_array[cpu_meta_set][cpu_meta_way] <= cpu_meta_tag;
          state_array[cpu_meta_set][cpu_meta_way] <= cpu_meta_write_state;
          valid_array[cpu_meta_set][cpu_meta_way] <=
            (cpu_meta_write_state != MESI_I);
          if (refill_alloc_valid_q && (refill_addr_q == cpu_meta_write_line_addr))
            refill_alloc_valid_q <= 1'b0;
        end else begin
          protocol_error <= 1'b1;
        end
      end

      if (snoop_meta_write_valid && snoop_meta_write_ready) begin
        if (snoop_meta_found) begin
          state_array[snoop_meta_set][snoop_meta_way] <= snoop_meta_write_state;
          valid_array[snoop_meta_set][snoop_meta_way] <=
            (snoop_meta_write_state != MESI_I);
        end else if (snoop_meta_write_state != MESI_I) begin
          protocol_error <= 1'b1;
        end
      end

      if (cpu_store_valid && cpu_store_ready) begin
        if (!valid_array[store_set][cpu_store_way] ||
            (tag_array[store_set][cpu_store_way] != store_tag) ||
            (state_array[store_set][cpu_store_way] != MESI_M)) begin
          protocol_error <= 1'b1;
        end else begin
          for (k = 0; k < 8; k = k + 1) begin
            if (cpu_store_wmask[k])
              data_array[store_set][cpu_store_way][cpu_store_addr[5:3]][8*k +: 8]
                <= cpu_store_wdata[8*k +: 8];
          end
        end
      end

      if (line_rd_valid && line_rd_ready) begin
        line_rd_busy_q <= line_rd_hit;
        line_rd_set_q <= line_rd_addr[6 +: SET_WIDTH];
        line_rd_beat_q <= 3'd0;
        for (j = 0; j < WAYS; j = j + 1) begin
          if (valid_array[line_rd_addr[6 +: SET_WIDTH]][j] &&
              tag_array[line_rd_addr[6 +: SET_WIDTH]][j] ==
                line_rd_addr[6+SET_WIDTH +: TAG_WIDTH])
            line_rd_way_q <= WAY_WIDTH'(j);
        end
        if (!line_rd_hit)
          protocol_error <= 1'b1;
      end else if (line_data_valid && line_data_ready) begin
        if (line_rd_beat_q == 3'd7) begin
          line_rd_busy_q <= 1'b0;
          line_rd_beat_q <= 3'd0;
        end else begin
          line_rd_beat_q <= line_rd_beat_q + 1'b1;
        end
      end
    end
  end
endmodule
