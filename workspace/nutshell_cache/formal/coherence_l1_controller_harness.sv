module CoherenceL1ControllerFormal(
  input logic reset_after_init,
  input logic cpu_req_valid,
  input logic [31:0] cpu_req_addr,
  input logic cpu_req_write,
  input logic cpu_req_hit,
  input logic [1:0] cpu_req_line_state_bits,
  input logic cpu_resp_ready,
  input logic dir_req_ready,
  input logic grant_valid,
  input logic [2:0] grant_opcode_bits,
  input logic [3:0] grant_txn_id,
  input logic grant_data_valid,
  input logic [3:0] grant_data_txn_id,
  input logic [2:0] grant_data_beat_idx,
  input logic [63:0] grant_data,
  input logic grant_data_last,
  input logic refill_ready,
  input logic grant_commit_ready,
  input logic snoop_valid,
  input logic [31:0] snoop_line_addr,
  input logic [1:0] snoop_opcode_bits,
  input logic [3:0] snoop_txn_id,
  input logic snoop_tag_hit,
  input logic [1:0] snoop_line_state_bits,
  input logic snoop_rsp_ready,
  input logic snoop_line_rd_ready,
  input logic snoop_line_rd_hit,
  input logic snoop_array_data_valid,
  input logic [2:0] snoop_array_beat_idx,
  input logic [63:0] snoop_array_data,
  input logic snoop_array_last,
  input logic snoop_data_ready,
  input logic cpu_meta_write_ready,
  input logic snoop_meta_write_ready
);
  import coherence_protocol_pkg::*;

  (* gclk *) logic formal_timestep;
  logic clock = 1'b0;

  logic reset;
  logic [1:0] init_reset_count = 2'b00;
  mesi_state_t cpu_req_line_state;
  grant_opcode_t grant_opcode;
  snoop_opcode_t snoop_opcode;
  mesi_state_t snoop_line_state;

  logic cpu_req_ready, cpu_resp_valid;
  logic [31:0] cpu_resp_addr;
  logic cpu_resp_write;
  logic [TXN_ID_WIDTH-1:0] cpu_resp_txn_id;
  logic dir_req_valid;
  request_opcode_t dir_req_opcode;
  logic [31:0] dir_req_line_addr;
  logic [TXN_ID_WIDTH-1:0] dir_req_txn_id;
  logic grant_ready, grant_data_ready;
  logic refill_valid;
  logic [TXN_ID_WIDTH-1:0] refill_txn_id;
  logic [2:0] refill_beat_idx;
  logic [63:0] refill_data;
  logic refill_last, grant_commit_valid;
  logic [TXN_ID_WIDTH-1:0] grant_commit_txn_id;
  logic snoop_ready, snoop_rsp_valid;
  snoop_response_t snoop_rsp_opcode;
  logic [TXN_ID_WIDTH-1:0] snoop_rsp_txn_id;
  logic snoop_rsp_has_data, snoop_line_rd_valid;
  logic [31:0] snoop_line_rd_addr;
  logic snoop_array_data_ready, snoop_data_valid;
  logic [TXN_ID_WIDTH-1:0] snoop_data_txn_id;
  logic [2:0] snoop_data_beat_idx;
  logic [63:0] snoop_data;
  logic snoop_data_last;
  logic [2:0] monitor_cpu_state, monitor_snoop_state;
  logic [31:0] monitor_cpu_active_addr;
  logic cpu_meta_write_valid;
  logic [31:0] cpu_meta_write_line_addr;
  mesi_state_t cpu_meta_write_state;
  logic snoop_meta_write_valid;
  logic [31:0] snoop_meta_write_line_addr;
  mesi_state_t snoop_meta_write_state;
  logic protocol_error;
  logic past_valid = 1'b0;

  always_comb reset = (init_reset_count < 2) || reset_after_init;

  always_comb begin
    cpu_req_line_state = mesi_state_t'(cpu_req_line_state_bits);
    grant_opcode = grant_opcode_t'(grant_opcode_bits);
    snoop_opcode = snoop_opcode_t'(snoop_opcode_bits);
    snoop_line_state = mesi_state_t'(snoop_line_state_bits);
  end

  always @(posedge formal_timestep)
    clock <= ~clock;

  MesiL1Controller dut (.*);

  always @(posedge clock) begin
    past_valid <= 1'b1;
    if (init_reset_count < 2)
      init_reset_count <= init_reset_count + 1'b1;

    if (past_valid && !reset) begin
      assert (!dir_req_valid || (dir_req_line_addr[5:0] == 6'b0));
      assert (!grant_ready || (grant_txn_id == dir_req_txn_id));
      assert (!cpu_resp_valid ||
              ((cpu_resp_txn_id == dir_req_txn_id) &&
               (cpu_resp_addr[31:6] == dir_req_line_addr[31:6])));
      assert (!grant_commit_valid ||
              (grant_commit_txn_id == dir_req_txn_id));
      assert (!grant_data_ready ||
              (refill_ready && grant_data_txn_id == refill_txn_id));
      assert (!refill_valid ||
              (grant_data_valid && grant_data_txn_id == refill_txn_id));
      assert (!snoop_rsp_valid ||
              (snoop_rsp_txn_id == snoop_data_txn_id));
      assert (!snoop_data_valid ||
              (snoop_array_data_valid &&
               snoop_data_beat_idx == snoop_array_beat_idx &&
               snoop_data == snoop_array_data &&
               snoop_data_last == snoop_array_last));
      assert (!cpu_meta_write_valid ||
              (cpu_meta_write_line_addr[5:0] == 6'b0));
      assert (!snoop_meta_write_valid ||
              (snoop_meta_write_line_addr[5:0] == 6'b0));
    end

    if (past_valid && !reset && !$past(reset)) begin
      if ($past(cpu_resp_valid && !cpu_resp_ready)) begin
        assert (cpu_resp_valid);
        assert (cpu_resp_addr == $past(cpu_resp_addr));
        assert (cpu_resp_write == $past(cpu_resp_write));
        assert (cpu_resp_txn_id == $past(cpu_resp_txn_id));
      end
      if ($past(dir_req_valid && !dir_req_ready)) begin
        assert (dir_req_valid);
        assert (dir_req_opcode == $past(dir_req_opcode));
        assert (dir_req_line_addr == $past(dir_req_line_addr));
        assert (dir_req_txn_id == $past(dir_req_txn_id));
      end
      if ($past(grant_commit_valid && !grant_commit_ready)) begin
        assert (grant_commit_valid);
        assert (grant_commit_txn_id == $past(grant_commit_txn_id));
      end
      if ($past(cpu_meta_write_valid && !cpu_meta_write_ready)) begin
        assert (cpu_meta_write_valid);
        assert (cpu_meta_write_line_addr == $past(cpu_meta_write_line_addr));
        assert (cpu_meta_write_state == $past(cpu_meta_write_state));
      end
      if ($past(snoop_line_rd_valid && !snoop_line_rd_ready)) begin
        assert (snoop_line_rd_valid);
        assert (snoop_line_rd_addr == $past(snoop_line_rd_addr));
      end
      if ($past(snoop_meta_write_valid && !snoop_meta_write_ready)) begin
        assert (snoop_meta_write_valid);
        assert (snoop_meta_write_line_addr == $past(snoop_meta_write_line_addr));
        assert (snoop_meta_write_state == $past(snoop_meta_write_state));
      end
      if ($past(snoop_rsp_valid && !snoop_rsp_ready)) begin
        assert (snoop_rsp_valid);
        assert (snoop_rsp_opcode == $past(snoop_rsp_opcode));
        assert (snoop_rsp_txn_id == $past(snoop_rsp_txn_id));
        assert (snoop_rsp_has_data == $past(snoop_rsp_has_data));
      end
      if ($past(refill_valid && !refill_ready)) begin
        assume (grant_data_valid);
        assume (grant_data_txn_id == $past(grant_data_txn_id));
        assume (grant_data_beat_idx == $past(grant_data_beat_idx));
        assume (grant_data == $past(grant_data));
        assume (grant_data_last == $past(grant_data_last));
        assert (refill_valid);
        assert (refill_data == $past(refill_data));
        assert (refill_beat_idx == $past(refill_beat_idx));
        assert (refill_last == $past(refill_last));
      end
      if ($past(snoop_data_valid && !snoop_data_ready)) begin
        assume (snoop_array_data_valid);
        assume (snoop_array_beat_idx == $past(snoop_array_beat_idx));
        assume (snoop_array_data == $past(snoop_array_data));
        assume (snoop_array_last == $past(snoop_array_last));
        assert (snoop_data_valid);
        assert (snoop_data == $past(snoop_data));
        assert (snoop_data_beat_idx == $past(snoop_data_beat_idx));
        assert (snoop_data_last == $past(snoop_data_last));
      end
      if ($past(protocol_error))
        assert (protocol_error);
      if ($past(reset)) begin
        assert (!cpu_resp_valid && !dir_req_valid && !grant_commit_valid &&
                !snoop_rsp_valid && !snoop_line_rd_valid &&
                !cpu_meta_write_valid && !snoop_meta_write_valid);
      end
    end
  end
endmodule
