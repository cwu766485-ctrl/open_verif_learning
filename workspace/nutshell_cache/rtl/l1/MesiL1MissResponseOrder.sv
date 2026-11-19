// Retire completed L1 miss responses in the order their MSHRs were reserved.
// Hit-under-Miss responses remain on the existing independent bypass path.
module MesiL1MissResponseOrder #(
  parameter int TAG_WIDTH = coherence_protocol_pkg::TXN_ID_WIDTH
) (
  input  logic clock,
  input  logic reset,

  input  logic reserve_valid,
  output logic reserve_ready,
  input  logic [TAG_WIDTH-1:0] reserve_tag,

  input  logic complete_valid,
  output logic complete_ready,
  input  logic [TAG_WIDTH-1:0] complete_tag,
  input  logic [31:0] complete_addr,
  input  logic complete_write,
  input  logic [63:0] complete_data,

  output logic resp_valid,
  input  logic resp_ready,
  output logic [TAG_WIDTH-1:0] resp_tag,
  output logic [31:0] resp_addr,
  output logic resp_write,
  output logic [63:0] resp_data,

  output logic [1:0] monitor_occupancy
);
  logic [1:0] valid_q;
  logic [1:0] complete_q;
  logic [TAG_WIDTH-1:0] tag_q [0:1];
  logic [31:0] addr_q [0:1];
  logic write_q [0:1];
  logic [63:0] data_q [0:1];
  logic head_q;
  logic tail_q;
  logic [1:0] count_q;
  logic match_found;
  logic match_idx;
  logic reserve_tag_live;
  logic reserve_fire;
  logic complete_fire;
  logic resp_fire;

  always_comb begin
    match_found = 1'b0;
    match_idx = 1'b0;
    reserve_tag_live = 1'b0;
    for (int unsigned i = 0; i < 2; i++) begin
      if (valid_q[i] && (tag_q[i] == complete_tag)) begin
        match_found = 1'b1;
        match_idx = 1'(i);
      end
      if (valid_q[i] && (tag_q[i] == reserve_tag))
        reserve_tag_live = 1'b1;
    end

    reserve_ready = (count_q < 2) && !reserve_tag_live;
    complete_ready = match_found && !complete_q[match_idx];
    resp_valid = valid_q[head_q] && complete_q[head_q];
    resp_tag = tag_q[head_q];
    resp_addr = addr_q[head_q];
    resp_write = write_q[head_q];
    resp_data = data_q[head_q];
    monitor_occupancy = count_q;

    reserve_fire = reserve_valid && reserve_ready;
    complete_fire = complete_valid && complete_ready;
    resp_fire = resp_valid && resp_ready;
  end

  always_ff @(posedge clock) begin
    if (reset) begin
      valid_q <= '0;
      complete_q <= '0;
      tag_q[0] <= '0;
      tag_q[1] <= '0;
      addr_q[0] <= '0;
      addr_q[1] <= '0;
      write_q[0] <= 1'b0;
      write_q[1] <= 1'b0;
      data_q[0] <= '0;
      data_q[1] <= '0;
      head_q <= 1'b0;
      tail_q <= 1'b0;
      count_q <= '0;
    end else begin
      if (reserve_fire) begin
        valid_q[tail_q] <= 1'b1;
        complete_q[tail_q] <= 1'b0;
        tag_q[tail_q] <= reserve_tag;
        addr_q[tail_q] <= '0;
        write_q[tail_q] <= 1'b0;
        data_q[tail_q] <= '0;
        tail_q <= ~tail_q;
      end

      if (complete_fire) begin
        complete_q[match_idx] <= 1'b1;
        addr_q[match_idx] <= complete_addr;
        write_q[match_idx] <= complete_write;
        data_q[match_idx] <= complete_data;
      end

      if (resp_fire) begin
        valid_q[head_q] <= 1'b0;
        complete_q[head_q] <= 1'b0;
        head_q <= ~head_q;
      end

      case ({reserve_fire, resp_fire})
        2'b10: count_q <= count_q + 1'b1;
        2'b01: count_q <= count_q - 1'b1;
        default: count_q <= count_q;
      endcase
    end
  end
endmodule
