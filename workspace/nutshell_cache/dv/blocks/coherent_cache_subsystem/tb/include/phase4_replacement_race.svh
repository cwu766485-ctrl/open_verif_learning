    begin : phase4_replacement_race
      logic [31:0] victim, replacement;
      logic [63:0] expected, observed0, observed1;
      integer retry_count;
      retry_count = 0;
      // Sweep relative request timing, rather than seeds. Each attempt starts
      // with a dirty owner and a known round-robin L1 replacement victim.
      for (integer offset = 0; offset < 10; offset++) begin
        @(negedge clock); reset = 1; reference_clear();
        repeat (3) @(posedge clock);
        @(negedge clock); reset = 0;
        victim = 32'h0b00_0000;
        replacement = victim + 4*32768;
        expected = 64'h1234_5678_9abc_def0;
        cpu_access(0, victim, 1, 8'hff, expected, ignored);
        for (integer way = 1; way < 4; way++)
          expect_reference_word(0, victim + way*32768);
        // The requester is stalled at its replacement Put when the peer
        // snoops the old line. Both operations use only CPU ports.
        @(negedge clock); cpu_resp_ready[0] = 0; cpu_resp_ready[1] = 0;
        fork
          begin
            cpu_issue_only(0, replacement, 0, 0, 0);
          end
          begin
            repeat (offset) @(posedge clock);
            cpu_issue_only(1, victim, 0, 0, 0);
          end
        join
        // Both requests were accepted before either response may be consumed.
        // Hold responses while observing Directory retry; release below.
        for (integer t = 0; t < 1000; t++) begin
          @(negedge clock);
          if ((dut.directory_controller.contexts[0].context_i.state_q == 4 &&
               dut.directory_controller.contexts[0].context_i.snoop_rsp_ready &&
               dut.directory_controller.contexts[0].context_i.snoop_rsp_valid &&
               dut.directory_controller.contexts[0].context_i.snoop_rsp_opcode != SNOOP_RSP_DATA) ||
              (dut.directory_controller.contexts[1].context_i.state_q == 4 &&
               dut.directory_controller.contexts[1].context_i.snoop_rsp_ready &&
               dut.directory_controller.contexts[1].context_i.snoop_rsp_valid &&
               dut.directory_controller.contexts[1].context_i.snoop_rsp_opcode != SNOOP_RSP_DATA))
            retry_count++;
          if (cpu_resp_valid[0] && cpu_resp_valid[1]) break;
          if (t == 999) $fatal(1, "replacement/snoop responses failed to progress");
        end
        // Both completions are now visible. Predict both CPU operations
        // before the global MESI checker examines the first consumed reply.
        state_model_apply_cpu(0, replacement, 0);
        state_model_apply_cpu(1, victim, 0);
        @(negedge clock); cpu_resp_ready[0] = 1;
        cpu_response_only(0, replacement, 0, 0, 0, observed0);
        @(negedge clock); cpu_resp_ready[1] = 1;
        cpu_response_only(1, victim, 0, 0, 0, observed1);
        if (observed1 != expected) $fatal(1, "replacement lost dirty owner data");
        expect_word(0, victim, expected);
      end
      @(negedge clock); cpu_resp_ready[0] = 1; cpu_resp_ready[1] = 1;
      if (retry_count == 0) $fatal(1, "timing sweep never reached owner-missing retry");
      $display("PHASE4: checked replacement/snoop timing sweep; observed retry responses=%0d", retry_count);
    end
