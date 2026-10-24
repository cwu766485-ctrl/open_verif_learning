// Per-L1 arbitration between a blocking CPU transaction and the independent
// Snoop FSM. Same-line work is serialized; different-line work can overlap.
module MesiL1SnoopArbiter (
  input  logic cpu_idle,
  input  logic cpu_snoop_lock,
  input  logic [31:0] cpu_req_addr,
  input  logic cpu_req_valid,
  input  logic [31:0] cpu_active_addr,
  input  logic snoop_idle,
  input  logic [31:0] snoop_req_addr,
  input  logic snoop_valid,
  input  logic [31:0] snoop_active_addr,
  output logic cpu_req_ready,
  output logic snoop_ready
);
  logic simultaneous_same_line;

  always_comb begin
    simultaneous_same_line =
      (cpu_req_addr[31:6] == snoop_req_addr[31:6]);

    // Snoop wins an idle-cycle same-line collision. A CPU transaction that
    // already owns the line finishes before its Snoop can be accepted.
    cpu_req_ready = cpu_idle &&
      !(!snoop_idle && cpu_req_valid &&
        (cpu_req_addr[31:6] == snoop_active_addr[31:6])) &&
      !(snoop_idle && snoop_valid && simultaneous_same_line);

    // Once a Snoop owns the line, a same-line CPU request waits until the
    // Snoop's state/data response has committed and the Snoop FSM is idle.
    snoop_ready = snoop_idle &&
      !(cpu_snoop_lock && !cpu_idle && snoop_valid &&
        (cpu_active_addr[31:6] == snoop_req_addr[31:6]));
  end
endmodule
