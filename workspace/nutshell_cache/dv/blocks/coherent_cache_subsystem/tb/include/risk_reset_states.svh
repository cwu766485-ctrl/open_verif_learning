    begin : risk_reset_states
      logic reached;
      logic [31:0] reset_line;
      // Observe, never force, context0 in seven normal transient states.
      // Context0 is selected after each reset. Error states and contexts 2/3
      // are separate obligations; this test makes no claim about them.
      for (integer target = 1; target <= 8; target++) begin
        if (target == 2) continue; // WAIT_XFER already exercised by existing reset tests.
        @(negedge clock); reset = 1; reference_clear();
        cpu_req_valid[0] = 0; cpu_req_valid[1] = 0;
        repeat (3) @(posedge clock);
        @(negedge clock); reset = 0;
        reset_line = 32'h00b0_1800 + 64*target;
        if (target == 3 || target == 4)
          expect_word(1, reset_line, memory_word(reset_line, 0));
        cpu_issue_only(0, reset_line, 0, 0, 0);
        reached = 0;
        for (integer wait_cycle = 0; wait_cycle < 500; wait_cycle++) begin
          @(negedge clock);
          if (int'(dut.directory_controller.contexts[0].context_i.state_q) == target) begin
            reached = 1;
            break;
          end
        end
        if (!reached) $fatal(1, "legal reset precondition not reached state=%0d", target);
        reset = 1; reference_clear();
        repeat (3) @(posedge clock);
        @(negedge clock); reset = 0;
        repeat (5) begin
          @(posedge clock); #1;
          if (cpu_resp_valid[0] || cpu_resp_valid[1] || fatal_error ||
              mem_rd_req_valid || mem_wr_req_valid)
            $fatal(1, "reset from Directory state %0d leaked stale output", target);
        end
        expect_word(0, reset_line, memory_word(reset_line, 0));
      end
      $display("PASS: seven observed Directory transient reset cancellations and checked recovery reads");
    end
