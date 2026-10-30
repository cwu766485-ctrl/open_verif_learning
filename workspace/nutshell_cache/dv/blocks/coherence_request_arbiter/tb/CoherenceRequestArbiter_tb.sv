`timescale 1ns/1ps

module CoherenceRequestArbiter_tb;
  import coherence_protocol_pkg::*;

  logic clock = 1'b0;
  logic reset;
  logic [1:0] in_valid;
  logic [1:0] in_ready;
  request_opcode_t in_opcode [0:1];
  logic [31:0] in_line_addr [0:1];
  logic [TXN_ID_WIDTH-1:0] in_txn_id [0:1];
  logic out_valid;
  logic out_ready;
  logic out_src_id;
  request_opcode_t out_opcode;
  logic [31:0] out_line_addr;
  logic [TXN_ID_WIDTH-1:0] out_txn_id;

  always #5 clock = ~clock;

  CoherenceRequestArbiter dut (.*);

  task automatic tick;
    @(posedge clock);
    #1;
  endtask

  initial begin
    reset = 1'b1;
    in_valid = 2'b00;
    out_ready = 1'b0;
    in_opcode[0] = REQ_GETS;
    in_opcode[1] = REQ_GETM;
    in_line_addr[0] = 32'h0000_1040;
    in_line_addr[1] = 32'h0000_2080;
    in_txn_id[0] = 4'h3;
    in_txn_id[1] = 4'hA;

    tick();
    reset = 1'b0;
    #1;
    if (out_valid || in_ready != 2'b00)
      $fatal(1, "arbiter should be idle after reset");

    // Reset preference is core 0. Begin with core 0 stalled, then make core 1
    // valid while the selected source must remain locked.
    in_valid = 2'b01;
    #1;
    if (!out_valid || out_src_id != 1'b0 || out_opcode != REQ_GETS ||
        out_line_addr != 32'h0000_1040 || out_txn_id != 4'h3 ||
        in_ready != 2'b00)
      $fatal(1, "initial priority or stalled core-0 payload is incorrect");
    tick();

    in_valid = 2'b11;
    #1;
    if (!out_valid || out_src_id != 1'b0 || out_opcode != REQ_GETS ||
        out_line_addr != 32'h0000_1040 || out_txn_id != 4'h3)
      $fatal(1, "locked source changed or core-0 payload was not retained");

    out_ready = 1'b1;
    #1;
    if (in_ready != 2'b01)
      $fatal(1, "ready must be asserted only for the selected source");
    tick();

    // After accepting core 0, round-robin preference moves to core 1.
    in_opcode[0] = REQ_GETS;
    in_line_addr[0] = 32'h0000_4000;
    in_txn_id[0] = 4'h6;
    #1;
    if (!out_valid || out_src_id != 1'b1 || out_opcode != REQ_GETM ||
        out_line_addr != 32'h0000_2080 || out_txn_id != 4'hA ||
        in_ready != 2'b10)
      $fatal(1, "round-robin did not select core 1 after core 0 handshake");
    tick();

    // Keep both requesters active with their next requests; the next winner
    // must alternate back to core 0.
    in_opcode[1] = REQ_PUTM;
    in_line_addr[1] = 32'h0000_5080;
    in_txn_id[1] = 4'hB;
    #1;
    if (!out_valid || out_src_id != 1'b0 || out_opcode != REQ_GETS ||
        out_line_addr != 32'h0000_4000 || out_txn_id != 4'h6)
      $fatal(1, "round-robin did not alternate back to core 0");
    tick();

    // A reset clears both the grant lock and round-robin preference.
    out_ready = 1'b0;
    tick();
    reset = 1'b1;
    tick();
    reset = 1'b0;
    out_ready = 1'b1;
    #1;
    if (!out_valid || out_src_id != 1'b0)
      $fatal(1, "reset did not restore core-0 arbitration preference");

    $display("PASS CoherenceRequestArbiter_tb");
    $finish;
  end
endmodule
