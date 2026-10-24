// Read-only APB3 performance counters. Counters are 32-bit, reset to zero,
// and wrap modulo 2^32. Average cache-access latency is total cycles divided
// by completed accesses in software.
module CachePerformanceCsr (
  input logic clock,
  input logic reset,

  input logic [1:0] hit_event,
  input logic [1:0] miss_event,
  input logic [1:0] snoop_event,
  input logic dirty_writeback_event,
  input logic [1:0] cache_inflight,
  input logic [1:0] access_complete_event,
  input logic [4:0] error_status,

  input  logic apb_psel,
  input  logic apb_penable,
  input  logic apb_pwrite,
  input  logic [31:0] apb_paddr,
  output logic apb_pready,
  output logic [31:0] apb_prdata,
  output logic apb_pslverr
);
  logic [31:0] hit_count_q;
  logic [31:0] miss_count_q;
  logic [31:0] snoop_count_q;
  logic [31:0] dirty_writeback_count_q;
  logic [31:0] access_cycle_count_q;
  logic [31:0] completed_access_count_q;

  function automatic logic [31:0] count2(input logic [1:0] value);
    count2 = {30'b0, value[0]} + {30'b0, value[1]};
  endfunction

  function automatic logic [31:0] count1(input logic value);
    count1 = value ? 32'd1 : 32'd0;
  endfunction

  always_ff @(posedge clock) begin
    if (reset) begin
      hit_count_q <= '0;
      miss_count_q <= '0;
      snoop_count_q <= '0;
      dirty_writeback_count_q <= '0;
      access_cycle_count_q <= '0;
      completed_access_count_q <= '0;
    end else begin
      hit_count_q <= hit_count_q + count2(hit_event);
      miss_count_q <= miss_count_q + count2(miss_event);
      snoop_count_q <= snoop_count_q + count2(snoop_event);
      dirty_writeback_count_q <= dirty_writeback_count_q +
                                 count1(dirty_writeback_event);
      access_cycle_count_q <= access_cycle_count_q + count2(cache_inflight);
      completed_access_count_q <= completed_access_count_q +
                                  count2(access_complete_event);
    end
  end

  always_comb begin
    apb_pready = apb_psel && apb_penable;
    apb_prdata = 32'b0;
    apb_pslverr = 1'b0;
    if (apb_psel && apb_penable) begin
      if (apb_pwrite) begin
        apb_pslverr = 1'b1;
      end else begin
        case (apb_paddr)
          32'h0000_0000: apb_prdata = hit_count_q;
          32'h0000_0004: apb_prdata = miss_count_q;
          32'h0000_0008: apb_prdata = snoop_count_q;
          32'h0000_000c: apb_prdata = dirty_writeback_count_q;
          // [0] fatal, [1] protocol error, [2] memory response error,
          // [3] MMIO protocol error; [4] reserved.
          32'h0000_0010: apb_prdata = {27'b0, error_status};
          32'h0000_0014: apb_prdata = access_cycle_count_q;
          32'h0000_0018: apb_prdata = completed_access_count_q;
          default: apb_pslverr = 1'b1;
        endcase
      end
    end
  end
endmodule
