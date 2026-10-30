  logic ref_valid_q [0:63];
  logic [31:0] ref_addr_q [0:63];
  logic [63:0] ref_data_q [0:63];
  integer ref_write_ptr_q;

  function automatic logic [63:0] expected_word(input logic [31:0] byte_addr);
    logic [63:0] value;
    value = cold_word(byte_addr);
    for (integer i = 0; i < 64; i = i + 1)
      if (ref_valid_q[i] && (ref_addr_q[i] == {byte_addr[31:3],3'b000}))
        value = ref_data_q[i];
    return value;
  endfunction

  task automatic update_reference(input logic [31:0] byte_addr,
                                  input logic [63:0] value);
    integer found;
    found = -1;
    for (integer i = 0; i < 64; i = i + 1)
      if (ref_valid_q[i] && (ref_addr_q[i] == {byte_addr[31:3],3'b000}))
        found = i;
    if (found < 0) begin
      found = ref_write_ptr_q;
      ref_write_ptr_q = (ref_write_ptr_q + 1) % 64;
    end
    ref_valid_q[found] = 1'b1;
    ref_addr_q[found] = {byte_addr[31:3],3'b000};
    ref_data_q[found] = value;
  endtask

  task automatic cpu_access(input integer core,
                            input logic is_write,
                            input logic [31:0] addr,
                            input logic [63:0] write_data,
                            input logic check_read,
                            input logic [63:0] expected);
    logic request_accepted;
    logic response_seen;
    integer latency_cycles;
    begin
      @(negedge clock);
      cpu_req_valid[core] = 1'b1;
      cpu_req_addr[core] = addr;
      cpu_req_write[core] = is_write;
      cpu_req_wmask[core] = 8'hff;
      cpu_req_wdata[core] = write_data;
      request_accepted = 1'b0;
      while (!request_accepted) begin
        @(posedge clock);
        request_accepted = cpu_req_ready[core];
      end
      @(negedge clock);
      cpu_req_valid[core] = 1'b0;
      response_seen = 1'b0;
      latency_cycles = 0;
      while (!response_seen) begin
        @(posedge clock);
        latency_cycles = latency_cycles + 1;
        if (cpu_resp_valid[core] && cpu_resp_ready[core]) begin
          if (cpu_resp_addr[core] != addr)
            $fatal(1, "core %0d response address mismatch", core);
          if (!is_write && check_read && (cpu_resp_rdata[core] != expected))
            $fatal(1, "core %0d read %08x returned %016x expected %016x",
                   core, addr, cpu_resp_rdata[core], expected);
          response_seen = 1'b1;
        end
      end
      if (cpu_latency_count_q[core] >= 256)
        $fatal(1, "CPU latency sample array overflow for core %0d", core);
      cpu_latency_samples_q[core][cpu_latency_count_q[core]] = latency_cycles;
      cpu_latency_count_q[core] = cpu_latency_count_q[core] + 1;
    end
  endtask

  task automatic apb_read(input logic [31:0] addr,
                          output logic [31:0] value);
    begin
      @(negedge clock);
      apb_psel = 1'b1;
      apb_penable = 1'b0;
      apb_pwrite = 1'b0;
      apb_paddr = addr;
      @(negedge clock);
      apb_penable = 1'b1;
      #1;
      if (!apb_pready || apb_pslverr)
        $fatal(1, "APB CSR read failed at offset %08x", addr);
      value = apb_prdata;
      @(negedge clock);
      apb_psel = 1'b0;
      apb_penable = 1'b0;
    end
  endtask
