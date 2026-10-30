  task automatic cpu_access(
    input integer core,
    input logic [31:0] addr,
    input logic is_write,
    input logic [7:0] wmask,
    input logic [63:0] wdata,
    output logic [63:0] rdata
  );
    integer cycles;
    logic request_accepted;
    logic response_received;
    logic [63:0] expected_read;
    integer operation_cycles;
    integer snoop_start_cycle;
    logic snoop_seen;
    begin
      operation_cycles = 0;
      snoop_start_cycle = 0;
      snoop_seen = 1'b0;
      if (!is_write)
        reference_get(addr, expected_read);
      @(negedge clock);
      cpu_req_addr[core] = addr;
      cpu_req_write[core] = is_write;
      cpu_req_wmask[core] = wmask;
      cpu_req_wdata[core] = wdata;
      cpu_req_valid[core] = 1'b1;
      request_accepted = 1'b0;
      for (cycles = 0; cycles < 500; cycles = cycles + 1) begin
        @(posedge clock);
        operation_cycles = operation_cycles + 1;
        if (!snoop_seen &&
            ((monitor_snoop_accept_valid[0] &&
              line_align(monitor_snoop_accept_addr[0]) == line_align(addr)) ||
             (monitor_snoop_accept_valid[1] &&
              line_align(monitor_snoop_accept_addr[1]) == line_align(addr)))) begin
          snoop_seen = 1'b1;
          snoop_start_cycle = operation_cycles;
        end
        if (cpu_req_ready[core]) begin
          request_accepted = 1'b1;
          break;
        end
      end
      if (!request_accepted)
        $fatal(1, "Core%0d request timed out at %08x", core, addr);

      @(negedge clock);
      cpu_req_valid[core] = 1'b0;
      response_received = 1'b0;
      for (cycles = 0; cycles < 1000; cycles = cycles + 1) begin
        @(posedge clock);
        operation_cycles = operation_cycles + 1;
        if (!snoop_seen &&
            ((monitor_snoop_accept_valid[0] &&
              line_align(monitor_snoop_accept_addr[0]) == line_align(addr)) ||
             (monitor_snoop_accept_valid[1] &&
              line_align(monitor_snoop_accept_addr[1]) == line_align(addr)))) begin
          snoop_seen = 1'b1;
          snoop_start_cycle = operation_cycles;
        end
        if (cpu_resp_valid[core] && cpu_resp_ready[core]) begin
          if (cpu_resp_addr[core] !== addr || cpu_resp_write[core] !== is_write)
            $fatal(1, "Core%0d response metadata mismatch at %08x", core, addr);
          rdata = cpu_resp_rdata[core];
          if (!is_write && rdata !== expected_read)
            $fatal(1, "scoreboard mismatch core=%0d addr=%08x got=%016x expected=%016x",
                   core, addr, rdata, expected_read);
          response_received = 1'b1;
          break;
        end
      end
      if (!response_received) begin
        $fatal(1, "Core%0d response timed out at %08x", core, addr);
      end
      if (is_write)
        reference_write(addr, wmask, wdata);
      state_model_apply_cpu(core, addr, is_write);
      if ((addr < 32'h3000_0000) || (addr >= 32'h8000_0000)) begin
        if (snoop_seen) begin
          benchmark_snoop_count = benchmark_snoop_count + 1;
          benchmark_snoop_cycles = benchmark_snoop_cycles + (operation_cycles - snoop_start_cycle);
        end
      end
      @(negedge clock);
      if ((addr < 32'h3000_0000) || (addr >= 32'h8000_0000))
        state_model_check_all();
    end
  endtask

  task automatic cpu_issue_only(
    input integer core,
    input logic [31:0] addr,
    input logic is_write,
    input logic [7:0] wmask,
    input logic [63:0] wdata
  );
    integer cycles;
    logic accepted;
    begin
      @(negedge clock);
      cpu_req_addr[core] = addr;
      cpu_req_write[core] = is_write;
      cpu_req_wmask[core] = wmask;
      cpu_req_wdata[core] = wdata;
      cpu_req_valid[core] = 1'b1;
      accepted = 1'b0;
      for (cycles = 0; cycles < 500; cycles = cycles + 1) begin
        @(posedge clock);
        if (cpu_req_ready[core]) begin
          accepted = 1'b1;
          break;
        end
      end
      if (!accepted)
        $fatal(1, "request issue timed out core=%0d addr=%08x", core, addr);
      @(negedge clock);
      cpu_req_valid[core] = 1'b0;
    end
  endtask

  task automatic cpu_response_only(
    input integer core,
    input logic [31:0] addr,
    input logic is_write,
    input logic [7:0] wmask,
    input logic [63:0] wdata,
    output logic [63:0] rdata
  );
    integer cycles;
    logic [63:0] expected_read;
    logic response_received;
    begin
      if (!is_write)
        reference_get(addr, expected_read);
      response_received = 1'b0;
      for (cycles = 0; cycles < 1000; cycles = cycles + 1) begin
        @(posedge clock);
        if (cpu_resp_valid[core] && cpu_resp_ready[core]) begin
          if (cpu_resp_addr[core] !== addr || cpu_resp_write[core] !== is_write)
            $fatal(1, "Core%0d response metadata mismatch at %08x", core, addr);
          rdata = cpu_resp_rdata[core];
          if (!is_write && rdata !== expected_read)
            $fatal(1, "scoreboard mismatch core=%0d addr=%08x got=%016x expected=%016x",
                   core, addr, rdata, expected_read);
          response_received = 1'b1;
          break;
        end
      end
      if (!response_received)
        $fatal(1, "Core%0d response timed out at %08x", core, addr);
      if (is_write)
        reference_write(addr, wmask, wdata);
      state_model_apply_cpu(core, addr, is_write);
      @(negedge clock);
      if ((addr < 32'h3000_0000) || (addr >= 32'h8000_0000))
        state_model_check_all();
    end
  endtask

  task automatic cpu_pair_access(
    input logic [31:0] addr0,
    input logic write0,
    input logic [7:0] mask0,
    input logic [63:0] data0,
    input logic [31:0] addr1,
    input logic write1,
    input logic [7:0] mask1,
    input logic [63:0] data1,
    output logic [63:0] rdata0,
    output logic [63:0] rdata1,
    output logic last_dir_source
  );
    logic accepted [0:1];
    logic completed [0:1];
    logic [31:0] addrs [0:1];
    logic writes [0:1];
    logic [7:0] masks [0:1];
    logic [63:0] datas [0:1];
    logic [63:0] expected [0:1];
    integer cycles;
    integer core;
    begin
      addrs[0] = addr0;
      addrs[1] = addr1;
      writes[0] = write0;
      writes[1] = write1;
      masks[0] = mask0;
      masks[1] = mask1;
      datas[0] = data0;
      datas[1] = data1;
      if (!write0)
        reference_get(addr0, expected[0]);
      if (!write1)
        reference_get(addr1, expected[1]);
      for (core = 0; core < 2; core = core + 1) begin
        accepted[core] = 1'b0;
        completed[core] = 1'b0;
      end
      last_dir_source = 1'b0;
      @(negedge clock);
      for (core = 0; core < 2; core = core + 1) begin
        cpu_req_valid[core] = 1'b1;
        cpu_req_addr[core] = addrs[core];
        cpu_req_write[core] = writes[core];
        cpu_req_wmask[core] = masks[core];
        cpu_req_wdata[core] = datas[core];
      end
      for (cycles = 0; cycles < 500; cycles = cycles + 1) begin
        @(posedge clock);
        for (core = 0; core < 2; core = core + 1)
          if (!accepted[core] && cpu_req_ready[core])
            accepted[core] = 1'b1;
        if (dut.cluster_dir_req_valid && dut.dir_req_ready)
          last_dir_source = dut.cluster_dir_req_src_id;
        @(negedge clock);
        for (core = 0; core < 2; core = core + 1)
          if (accepted[core])
            cpu_req_valid[core] = 1'b0;
        if (accepted[0] && accepted[1])
          break;
      end
      if (!(accepted[0] && accepted[1]))
        $fatal(1, "dual-core request pair acceptance timed out");

      for (cycles = 0; cycles < 2000; cycles = cycles + 1) begin
        @(posedge clock);
        if (dut.cluster_dir_req_valid && dut.dir_req_ready)
          last_dir_source = dut.cluster_dir_req_src_id;
        for (core = 0; core < 2; core = core + 1) begin
          if (!completed[core] && cpu_resp_valid[core] && cpu_resp_ready[core]) begin
            if (cpu_resp_addr[core] !== addrs[core] ||
                cpu_resp_write[core] !== writes[core])
              $fatal(1, "dual-core response metadata mismatch core=%0d", core);
            if (!writes[core]) begin
              if (core == 0) begin
                rdata0 = cpu_resp_rdata[core];
                if (rdata0 !== expected[core])
                  $fatal(1, "pair scoreboard mismatch core0 got=%016x expected=%016x",
                         rdata0, expected[core]);
              end else begin
                rdata1 = cpu_resp_rdata[core];
                if (rdata1 !== expected[core])
                  $fatal(1, "pair scoreboard mismatch core1 got=%016x expected=%016x",
                         rdata1, expected[core]);
              end
            end else begin
              reference_write(addrs[core], masks[core], datas[core]);
            end
            state_model_apply_cpu(core, addrs[core], writes[core]);
            completed[core] = 1'b1;
          end
        end
        if (completed[0] && completed[1])
          break;
      end
      if (!(completed[0] && completed[1]))
        $fatal(1, "dual-core response pair timed out");
      @(negedge clock);
      state_model_check_all();
    end
  endtask
