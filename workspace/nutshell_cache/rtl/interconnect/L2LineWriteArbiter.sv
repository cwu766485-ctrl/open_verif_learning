// Selects the owner of the shared L2 line-write port. Stream priority and
// payload stability are intentionally kept identical to the original top.
module L2LineWriteArbiter (
  input logic engine_putm_stream,
  input logic engine_src,
  input logic [31:0] engine_addr,
  input logic put_data_valid_core [0:1],
  output logic put_data_ready_core [0:1],
  input logic [2:0] put_data_beat_idx_core [0:1],
  input logic [63:0] put_data_core [0:1],
  input logic put_data_last_core [0:1],
  input logic victim_snoop_data_to_l2,
  input logic victim_snoop_target,
  input logic [31:0] victim_addr,
  input logic snoop_data_valid_core [0:1],
  output logic snoop_data_ready_core [0:1],
  input logic [2:0] snoop_data_beat_idx_core [0:1],
  input logic [63:0] snoop_data_core [0:1],
  input logic snoop_data_last_core [0:1],
  input logic refill_active,
  input logic [31:0] refill_addr,
  input logic [2:0] refill_beat,
  input logic [63:0] refill_data,
  input logic dir_snoop_data_to_l2,
  input logic dir_snoop_target,
  input logic [31:0] dir_snoop_addr,
  input logic line_wr_ready,
  output logic line_wr_valid,
  output logic [31:0] line_wr_addr,
  output logic line_wr_dirty,
  output logic [2:0] line_wr_beat_idx,
  output logic [63:0] line_wr_data,
  output logic line_wr_last,
  output logic monitor_owner_data_valid,
  output logic monitor_owner_data_core,
  output logic [31:0] monitor_owner_data_addr,
  output logic [2:0] monitor_owner_data_beat_idx,
  output logic [63:0] monitor_owner_data,
  output logic monitor_owner_data_last
);
  always_comb begin : route_l2_line_write_payload
    line_wr_valid = 1'b0;
    line_wr_addr = 32'b0;
    line_wr_dirty = 1'b0;
    line_wr_beat_idx = 3'b0;
    line_wr_data = 64'b0;
    line_wr_last = 1'b0;
    monitor_owner_data_core = 1'b0;
    monitor_owner_data_addr = 32'b0;
    monitor_owner_data_beat_idx = 3'b0;
    monitor_owner_data = 64'b0;
    monitor_owner_data_last = 1'b0;
    if (engine_putm_stream) begin
      line_wr_valid = put_data_valid_core[engine_src];
      line_wr_addr = engine_addr;
      line_wr_dirty = 1'b1;
      line_wr_beat_idx = put_data_beat_idx_core[engine_src];
      line_wr_data = put_data_core[engine_src];
      line_wr_last = put_data_last_core[engine_src];
    end else if (victim_snoop_data_to_l2) begin
      line_wr_valid = snoop_data_valid_core[victim_snoop_target];
      line_wr_addr = victim_addr;
      line_wr_dirty = 1'b1;
      line_wr_beat_idx = snoop_data_beat_idx_core[victim_snoop_target];
      line_wr_data = snoop_data_core[victim_snoop_target];
      line_wr_last = snoop_data_last_core[victim_snoop_target];
      monitor_owner_data_core = victim_snoop_target;
      monitor_owner_data_addr = victim_addr;
      monitor_owner_data_beat_idx = snoop_data_beat_idx_core[victim_snoop_target];
      monitor_owner_data = snoop_data_core[victim_snoop_target];
      monitor_owner_data_last = snoop_data_last_core[victim_snoop_target];
    end else if (refill_active) begin
      line_wr_valid = 1'b1;
      line_wr_addr = refill_addr;
      line_wr_dirty = 1'b0;
      line_wr_beat_idx = refill_beat;
      line_wr_data = refill_data;
      line_wr_last = (refill_beat == 3'd7);
    end else if (dir_snoop_data_to_l2) begin
      line_wr_valid = snoop_data_valid_core[dir_snoop_target];
      line_wr_addr = dir_snoop_addr;
      line_wr_dirty = 1'b1;
      line_wr_beat_idx = snoop_data_beat_idx_core[dir_snoop_target];
      line_wr_data = snoop_data_core[dir_snoop_target];
      line_wr_last = snoop_data_last_core[dir_snoop_target];
      monitor_owner_data_core = dir_snoop_target;
      monitor_owner_data_addr = dir_snoop_addr;
      monitor_owner_data_beat_idx = snoop_data_beat_idx_core[dir_snoop_target];
      monitor_owner_data = snoop_data_core[dir_snoop_target];
      monitor_owner_data_last = snoop_data_last_core[dir_snoop_target];
    end
  end

  always_comb begin : route_l2_line_write_ready
    put_data_ready_core[0] = 1'b0;
    put_data_ready_core[1] = 1'b0;
    snoop_data_ready_core[0] = 1'b0;
    snoop_data_ready_core[1] = 1'b0;
    monitor_owner_data_valid = 1'b0;
    if (engine_putm_stream) begin
      put_data_ready_core[engine_src] = line_wr_ready;
    end else if (victim_snoop_data_to_l2) begin
      snoop_data_ready_core[victim_snoop_target] = line_wr_ready;
      monitor_owner_data_valid = snoop_data_valid_core[victim_snoop_target] &&
                                 line_wr_ready;
    end else if (refill_active) begin
      // Refill retains the port through beat 7.
    end else if (dir_snoop_data_to_l2) begin
      snoop_data_ready_core[dir_snoop_target] = line_wr_ready;
      monitor_owner_data_valid = snoop_data_valid_core[dir_snoop_target] &&
                                 line_wr_ready;
    end
  end
endmodule
