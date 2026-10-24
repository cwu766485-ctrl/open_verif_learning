`timescale 1ns/1ps

module MesiL1SnoopArbiter_tb;
  logic cpu_idle;
  logic cpu_snoop_lock;
  logic [31:0] cpu_req_addr;
  logic cpu_req_valid;
  logic [31:0] cpu_active_addr;
  logic snoop_idle;
  logic [31:0] snoop_req_addr;
  logic snoop_valid;
  logic [31:0] snoop_active_addr;
  logic cpu_req_ready;
  logic snoop_ready;

  MesiL1SnoopArbiter dut (.*);

  task automatic check_ready(
    input logic expected_cpu_ready,
    input logic expected_snoop_ready,
    input string scenario
  );
    #1;
    if (cpu_req_ready !== expected_cpu_ready ||
        snoop_ready !== expected_snoop_ready) begin
      $display("FAIL %s: cpu_ready=%b snoop_ready=%b expected=%b/%b",
               scenario, cpu_req_ready, snoop_ready,
               expected_cpu_ready, expected_snoop_ready);
      $fatal(1, "Snoop arbitration mismatch");
    end
  endtask

  initial begin
    cpu_idle = 1'b1;
    cpu_snoop_lock = 1'b0;
    cpu_req_addr = 32'h0000_1004;
    cpu_req_valid = 1'b1;
    cpu_active_addr = 32'h0000_1000;
    snoop_idle = 1'b1;
    snoop_req_addr = 32'h0000_103C;
    snoop_valid = 1'b1;
    snoop_active_addr = 32'h0000_1030;

    // Same cache line: an idle-cycle Snoop takes priority over a CPU request.
    check_ready(1'b0, 1'b1, "same-line collision");

    // Different cache lines can be accepted independently.
    snoop_req_addr = 32'h0000_1040;
    check_ready(1'b1, 1'b1, "different-line collision");

    cpu_req_valid = 1'b0;
    check_ready(1'b1, 1'b1, "Snoop only; ready is not valid-qualified");
    cpu_req_valid = 1'b1;
    snoop_valid = 1'b0;
    check_ready(1'b1, 1'b1, "CPU only; ready is not valid-qualified");

    // An already-running Snoop blocks a same-line CPU request, but not a
    // request to another line.
    snoop_idle = 1'b0;
    snoop_active_addr = 32'h0000_1010;
    cpu_req_addr = 32'h0000_1038;
    check_ready(1'b0, 1'b0, "CPU waits for active same-line Snoop");
    cpu_req_addr = 32'h0000_1040;
    check_ready(1'b1, 1'b0, "different-line CPU progresses during Snoop");

    // A CPU transaction that owns the line blocks only a matching Snoop.
    snoop_idle = 1'b1;
    snoop_valid = 1'b1;
    cpu_idle = 1'b0;
    cpu_snoop_lock = 1'b1;
    cpu_active_addr = 32'h0000_2030;
    snoop_req_addr = 32'h0000_2008;
    check_ready(1'b0, 1'b0, "Snoop waits for active same-line CPU owner");
    snoop_req_addr = 32'h0000_2040;
    check_ready(1'b0, 1'b1, "different-line Snoop progresses during CPU owner");

    // Without the CPU line lock, the independent Snoop FSM can progress.
    cpu_snoop_lock = 1'b0;
    snoop_req_addr = 32'h0000_2008;
    check_ready(1'b0, 1'b1, "Snoop progresses without CPU line lock");

    $display("PASS MesiL1SnoopArbiter_tb");
    $finish;
  end
endmodule
