module FreezeL1ProducerFormal(
  input logic clock,
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


  MesiL1Controller dut (.*);

  // Independent public-handshake model; all incoming protocol/data inputs
  // remain unconstrained, including malformed IDs, beats and opcodes.
  logic [3:0] next_cpu_id=0, accepted_cpu_id=0, accepted_snoop_id=0;
  logic [31:0] accepted_cpu_addr=0;
  always @(posedge clock) begin
    past_valid<=1;
    if(init_reset_count<2) init_reset_count<=init_reset_count+1'b1;
    if(reset) begin
      next_cpu_id<=0;accepted_cpu_id<=0;accepted_snoop_id<=0;accepted_cpu_addr<=0;
    end else begin
      if(cpu_req_valid && cpu_req_ready) begin
        accepted_cpu_id<=next_cpu_id; next_cpu_id<=next_cpu_id+1'b1;
        accepted_cpu_addr<=cpu_req_addr;
      end
      if(snoop_valid && snoop_ready) accepted_snoop_id<=snoop_txn_id;
    end
    if(past_valid && init_reset_count>=2) begin
      // Asserted strengthening links independent model to implementation.
      assert(dut.txn_counter_q==next_cpu_id);
      assert(dut.cpu_txn_q==accepted_cpu_id);
      assert(dut.cpu_addr_q==accepted_cpu_addr);
      assert(dut.snoop_txn_q==accepted_snoop_id);
      assert(monitor_cpu_state<=6 && monitor_snoop_state<=5);
      if(dir_req_valid) begin
        assert(dir_req_txn_id==accepted_cpu_id);
        assert(dir_req_line_addr==line_align(accepted_cpu_addr));
      end
      if(grant_commit_valid) assert(grant_commit_txn_id==accepted_cpu_id);
      if(cpu_resp_valid) assert(cpu_resp_txn_id==accepted_cpu_id);
      if(refill_valid) assert(refill_txn_id==accepted_cpu_id && grant_data_txn_id==accepted_cpu_id);
      if(snoop_rsp_valid) assert(snoop_rsp_txn_id==accepted_snoop_id);
      if(snoop_data_valid) begin
        assert(snoop_data_txn_id==accepted_snoop_id);
        assert(snoop_data_beat_idx==snoop_array_beat_idx);
        assert(snoop_data_last==snoop_array_last);
      end
      if($past(reset)) begin
        assert(monitor_cpu_state==0 && monitor_snoop_state==0);
        assert(!dir_req_valid && !grant_commit_valid && !cpu_resp_valid && !snoop_rsp_valid && !snoop_data_valid);
      end
    end
  end
endmodule
