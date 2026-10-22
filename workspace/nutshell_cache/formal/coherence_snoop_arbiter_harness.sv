module CoherenceSnoopArbiterFormal;
  (* anyconst *) logic cpu_idle;
  (* anyconst *) logic cpu_snoop_lock;
  (* anyconst *) logic [31:0] cpu_req_addr;
  (* anyconst *) logic cpu_req_valid;
  (* anyconst *) logic [31:0] cpu_active_addr;
  (* anyconst *) logic snoop_idle;
  (* anyconst *) logic [31:0] snoop_req_addr;
  (* anyconst *) logic snoop_valid;
  (* anyconst *) logic [31:0] snoop_active_addr;
  logic cpu_req_ready;
  logic snoop_ready;

  MesiL1SnoopArbiter dut (.*);

  always_comb begin
    assert (!cpu_req_ready || cpu_idle);
    assert (!snoop_ready || snoop_idle);

    if (cpu_idle && snoop_idle && cpu_req_valid && snoop_valid &&
        (cpu_req_addr[31:6] == snoop_req_addr[31:6])) begin
      assert (!cpu_req_ready);
      assert (snoop_ready);
    end

    if (cpu_idle && !snoop_idle && cpu_req_valid &&
        (cpu_req_addr[31:6] == snoop_active_addr[31:6]))
      assert (!cpu_req_ready);

    if (!cpu_idle && cpu_snoop_lock && snoop_idle && snoop_valid &&
        (cpu_active_addr[31:6] == snoop_req_addr[31:6]))
      assert (!snoop_ready);

    if (!cpu_idle && !cpu_snoop_lock && snoop_idle && snoop_valid)
      assert (snoop_ready);

    if (cpu_idle && snoop_idle && cpu_req_valid && snoop_valid &&
        (cpu_req_addr[31:6] != snoop_req_addr[31:6])) begin
      assert (cpu_req_ready);
      assert (snoop_ready);
    end

    if (cpu_idle && snoop_idle && cpu_req_valid && !snoop_valid)
      assert (cpu_req_ready);
    if (cpu_idle && snoop_idle && snoop_valid && !cpu_req_valid)
      assert (snoop_ready);
  end
endmodule
