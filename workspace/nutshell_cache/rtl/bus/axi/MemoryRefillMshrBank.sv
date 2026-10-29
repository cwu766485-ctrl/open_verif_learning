// Four-entry-class refill tracking bank. It matches interleaved memory
// responses by transaction ID, collects eight beats, serializes L2 fills, and
// retires completed Directory contexts in round-robin order.
module MemoryRefillMshrBank #(
  parameter int TXN_ID_WIDTH = coherence_protocol_pkg::TXN_ID_WIDTH,
  parameter int NUM_MSHRS = 4,
  parameter int MSHR_ID_WIDTH = (NUM_MSHRS < 2) ? 1 : $clog2(NUM_MSHRS)
) (
  input logic clock,
  input logic reset,
  input logic alloc_valid,
  input logic [31:0] alloc_addr,
  input logic [MSHR_ID_WIDTH-1:0] alloc_context,
  input logic mem_rd_data_valid,
  input logic mem_rd_data_ready,
  input logic [TXN_ID_WIDTH-1:0] mem_rd_data_txn_id,
  input logic [2:0] mem_rd_data_beat_idx,
  input logic [63:0] mem_rd_data,
  input logic mem_rd_data_last,
  input logic mem_rd_data_error,
  input logic fill_start_allowed,
  input logic line_wr_valid,
  input logic line_wr_ready,
  input logic xfer_done_active,
  input logic xfer_done_valid,
  input logic xfer_done_ready,
  input logic [31:0] dir_xfer_addr,
  input logic [31:0] dir_snoop_addr,
  output logic [NUM_MSHRS-1:0] mem_mshr_valid_q,
  output logic [NUM_MSHRS-1:0] mem_mshr_full_q,
  output logic [NUM_MSHRS-1:0] mem_mshr_written_q,
  output logic [31:0] mem_mshr_addr_q [0:NUM_MSHRS-1],
  output logic [MSHR_ID_WIDTH-1:0] mem_mshr_context_q [0:NUM_MSHRS-1],
  output logic [2:0] mem_mshr_expected_q [0:NUM_MSHRS-1],
  output logic [63:0] mem_mshr_data_q [0:NUM_MSHRS-1][0:7],
  output logic mem_mshr_alloc_found,
  output logic mem_mshr_fill_found,
  output logic mem_mshr_done_found,
  output logic [MSHR_ID_WIDTH-1:0] mem_mshr_alloc_sel,
  output logic [MSHR_ID_WIDTH-1:0] mem_mshr_fill_sel,
  output logic [MSHR_ID_WIDTH-1:0] mem_mshr_done_sel,
  output logic mem_mshr_r_match,
  output logic mem_r_protocol_bad,
  output logic [MSHR_ID_WIDTH-1:0] mem_mshr_r_sel,
  output logic mem_fill_writer_active_q,
  output logic [MSHR_ID_WIDTH-1:0] mem_fill_writer_sel_q,
  output logic [2:0] mem_fill_writer_beat_q,
  output logic [MSHR_ID_WIDTH-1:0] mem_mshr_done_context,
  output logic mshr_set_conflict,
  output logic snoop_set_conflict
);
  logic [MSHR_ID_WIDTH-1:0] mem_mshr_done_rr_q;
  logic [MSHR_ID_WIDTH-1:0] mem_mshr_fill_rr_q;

  always_comb begin : mem_mshr_decode
    integer i;
    integer idx;
    integer selected;
    mem_mshr_alloc_found = 1'b0;
    mem_mshr_alloc_sel = '0;
    mem_mshr_fill_found = 1'b0;
    mem_mshr_fill_sel = '0;
    mem_mshr_r_match = 1'b0;
    mem_r_protocol_bad = 1'b0;
    mem_mshr_r_sel = '0;
    selected = -1;
    for (i = 0; i < NUM_MSHRS; i = i + 1) begin
      if (!mem_mshr_valid_q[i] && !mem_mshr_alloc_found) begin
        mem_mshr_alloc_found = 1'b1;
        mem_mshr_alloc_sel = MSHR_ID_WIDTH'(i);
      end
      if (mem_rd_data_txn_id == TXN_ID_WIDTH'(i)) begin
        mem_mshr_r_sel = MSHR_ID_WIDTH'(i);
        mem_mshr_r_match = mem_mshr_valid_q[i] && !mem_mshr_full_q[i];
      end
    end
    selected = -1;
    for (i = 0; i < NUM_MSHRS; i = i + 1) begin
      idx = (int'(mem_mshr_fill_rr_q) + i) % NUM_MSHRS;
      if ((selected < 0) && mem_mshr_valid_q[idx] &&
          mem_mshr_full_q[idx] && !mem_mshr_written_q[idx]) selected = idx;
    end
    mem_mshr_fill_found = (selected >= 0);
    mem_mshr_fill_sel = mem_mshr_fill_found ?
                        MSHR_ID_WIDTH'(selected) : '0;
    selected = -1;
    for (i = 0; i < NUM_MSHRS; i = i + 1) begin
      idx = (int'(mem_mshr_done_rr_q) + i) % NUM_MSHRS;
      if ((selected < 0) && mem_mshr_valid_q[idx] &&
          mem_mshr_written_q[idx]) selected = idx;
    end
    mem_mshr_done_found = (selected >= 0);
    mem_mshr_done_sel = mem_mshr_done_found ?
                        MSHR_ID_WIDTH'(selected) : '0;
    mem_r_protocol_bad = mem_rd_data_valid && mem_rd_data_ready &&
      (!mem_mshr_r_match ||
       (mem_rd_data_error ? !mem_rd_data_last :
        ((mem_rd_data_beat_idx != mem_mshr_expected_q[mem_mshr_r_sel]) ||
         (mem_rd_data_last != (mem_rd_data_beat_idx == 3'd7)))));
  end

  always_comb begin : decode_refill_set_conflicts
    mshr_set_conflict = 1'b0;
    snoop_set_conflict = 1'b0;
    for (integer i = 0; i < NUM_MSHRS; i = i + 1) begin
      if (mem_mshr_valid_q[i] &&
          (mem_mshr_addr_q[i][14:6] == dir_xfer_addr[14:6]))
        mshr_set_conflict = 1'b1;
      if (mem_mshr_valid_q[i] &&
          (mem_mshr_addr_q[i][14:6] == dir_snoop_addr[14:6]))
        snoop_set_conflict = 1'b1;
    end
  end

  assign mem_mshr_done_context = mem_mshr_context_q[mem_mshr_done_sel];

  always_ff @(posedge clock) begin : memory_mshr_table
    if (reset) begin
      mem_mshr_valid_q <= '0;
      mem_mshr_full_q <= '0;
      mem_mshr_written_q <= '0;
      mem_mshr_done_rr_q <= '0;
      mem_mshr_fill_rr_q <= '0;
      mem_fill_writer_active_q <= 1'b0;
      mem_fill_writer_sel_q <= '0;
      mem_fill_writer_beat_q <= '0;
      for (integer i = 0; i < NUM_MSHRS; i = i + 1) begin
        mem_mshr_addr_q[i] <= '0;
        mem_mshr_context_q[i] <= '0;
        mem_mshr_expected_q[i] <= '0;
      end
    end else begin
      if (alloc_valid) begin
        mem_mshr_valid_q[mem_mshr_alloc_sel] <= 1'b1;
        mem_mshr_full_q[mem_mshr_alloc_sel] <= 1'b0;
        mem_mshr_written_q[mem_mshr_alloc_sel] <= 1'b0;
        mem_mshr_addr_q[mem_mshr_alloc_sel] <= alloc_addr;
        mem_mshr_context_q[mem_mshr_alloc_sel] <= alloc_context;
        mem_mshr_expected_q[mem_mshr_alloc_sel] <= '0;
      end

      if (mem_rd_data_valid && mem_rd_data_ready && mem_mshr_r_match &&
          !mem_rd_data_error &&
          (mem_rd_data_beat_idx == mem_mshr_expected_q[mem_mshr_r_sel]) &&
          (mem_rd_data_last == (mem_rd_data_beat_idx == 3'd7))) begin
        mem_mshr_data_q[mem_mshr_r_sel][mem_rd_data_beat_idx] <= mem_rd_data;
        if (mem_rd_data_beat_idx == 3'd7)
          mem_mshr_full_q[mem_mshr_r_sel] <= 1'b1;
        else
          mem_mshr_expected_q[mem_mshr_r_sel] <=
            mem_mshr_expected_q[mem_mshr_r_sel] + 1'b1;
      end

      if (!mem_fill_writer_active_q && mem_mshr_fill_found && fill_start_allowed) begin
        mem_fill_writer_active_q <= 1'b1;
        mem_fill_writer_sel_q <= mem_mshr_fill_sel;
        mem_fill_writer_beat_q <= '0;
      end else if (mem_fill_writer_active_q && line_wr_valid && line_wr_ready) begin
        if (mem_fill_writer_beat_q == 3'd7) begin
          mem_fill_writer_active_q <= 1'b0;
          mem_fill_writer_beat_q <= '0;
          mem_mshr_written_q[mem_fill_writer_sel_q] <= 1'b1;
          mem_mshr_fill_rr_q <=
            (mem_fill_writer_sel_q == MSHR_ID_WIDTH'(NUM_MSHRS-1)) ? '0 :
            mem_fill_writer_sel_q + 1'b1;
        end else begin
          mem_fill_writer_beat_q <= mem_fill_writer_beat_q + 1'b1;
        end
      end

      if (!xfer_done_active && mem_mshr_done_found &&
          xfer_done_valid && xfer_done_ready) begin
        mem_mshr_valid_q[mem_mshr_done_sel] <= 1'b0;
        mem_mshr_full_q[mem_mshr_done_sel] <= 1'b0;
        mem_mshr_written_q[mem_mshr_done_sel] <= 1'b0;
        mem_mshr_done_rr_q <=
          (mem_mshr_done_sel == MSHR_ID_WIDTH'(NUM_MSHRS-1)) ? '0 :
          mem_mshr_done_sel + 1'b1;
      end
    end
  end
endmodule
