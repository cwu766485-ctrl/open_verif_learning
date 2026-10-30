  // Global MESI/directory invariants checked continuously, including during
  // randomized and backpressured transactions.
  always @(posedge clock) begin : coherence_invariant_assertions
    if (!reset) begin
      for (integer set_idx = 0; set_idx < 128; set_idx = set_idx + 1) begin
        for (integer way0 = 0; way0 < 4; way0 = way0 + 1) begin
          for (integer way1 = 0; way1 < 4; way1 = way1 + 1) begin
            if (dut.l1_cluster.cores[0].l1_array.valid_array[set_idx][way0] &&
                dut.l1_cluster.cores[1].l1_array.valid_array[set_idx][way1] &&
                (dut.l1_cluster.cores[0].l1_array.tag_array[set_idx][way0] ==
                 dut.l1_cluster.cores[1].l1_array.tag_array[set_idx][way1]) &&
                ((dut.l1_cluster.cores[0].l1_array.state_array[set_idx][way0] == MESI_M) ||
                 (dut.l1_cluster.cores[0].l1_array.state_array[set_idx][way0] == MESI_E)) &&
                ((dut.l1_cluster.cores[1].l1_array.state_array[set_idx][way1] == MESI_M) ||
                 (dut.l1_cluster.cores[1].l1_array.state_array[set_idx][way1] == MESI_E)))
              $fatal(1, "MESI invariant: both cores hold write permission set=%0d tag=%h",
                     set_idx,
                     dut.l1_cluster.cores[0].l1_array.tag_array[set_idx][way0]);
          end
        end
      end
      for (integer l2_set = 0; l2_set < 512; l2_set = l2_set + 1) begin
        for (integer l2_way = 0; l2_way < 8; l2_way = l2_way + 1) begin
          if (dut.l2_array.valid_array[l2_set][l2_way]) begin
            case (dut.l2_array.dir_state_array[l2_set][l2_way])
              DIR_I: assert (dut.l2_array.sharer_array[l2_set][l2_way] == 2'b00 &&
                             !dut.l2_array.owner_array[l2_set][l2_way]);
              DIR_S: assert (dut.l2_array.sharer_array[l2_set][l2_way] != 2'b00 &&
                             !dut.l2_array.owner_array[l2_set][l2_way]);
              DIR_U: assert (dut.l2_array.sharer_array[l2_set][l2_way] == 2'b00);
              default: $fatal(1, "invalid L2 directory state encoding");
            endcase
          end
        end
      end
    end
  end

  always_ff @(posedge clock) begin
    if (reset) begin
      saw_l2_live_victim_q <= 1'b0;
      observed_l2_live_victim_q <= 32'b0;
      saw_l2_shared_victim_q <= 1'b0;
      observed_l2_shared_victim_q <= 32'b0;
      observed_l2_shared_sharers_q <= 2'b00;
    end else if (dut.dir_xfer_start_valid && dut.dir_xfer_start_ready &&
                 (dut.dir_xfer_kind == XFER_L2_REFILL) &&
                 l2_victim_valid && (l2_victim_dir_state == DIR_U)) begin
      saw_l2_live_victim_q <= 1'b1;
      observed_l2_live_victim_q <= l2_victim_addr;
    end else if (dut.dir_xfer_start_valid && dut.dir_xfer_start_ready &&
                 (dut.dir_xfer_kind == XFER_L2_REFILL) &&
                 l2_victim_valid && (l2_victim_dir_state == DIR_S)) begin
      saw_l2_shared_victim_q <= 1'b1;
      observed_l2_shared_victim_q <= l2_victim_addr;
      observed_l2_shared_sharers_q <= l2_victim_sharers;
    end
  end
