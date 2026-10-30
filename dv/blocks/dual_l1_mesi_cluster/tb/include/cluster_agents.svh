  task automatic tick;
    @(posedge clock);
    #1;
  endtask

  task automatic complete_read_refill(
    input logic core_id,
    input logic [31:0] request_addr,
    input logic [TXN_ID_WIDTH-1:0] txn_id,
    input logic [63:0] line_seed
  );
    integer beat;
    integer timeout;
    logic response_seen;
    begin
      if (core_id == 1'b0) begin
        grant_opcode_drive[2:0] = GRANT_DATA_E;
        grant_txn_id_drive[TXN_ID_WIDTH-1:0] = txn_id;
      end else begin
        grant_opcode_drive[5:3] = GRANT_DATA_E;
        grant_txn_id_drive[2*TXN_ID_WIDTH-1:TXN_ID_WIDTH] = txn_id;
      end
      @(negedge clock);
      #1;
      if (core_id == 1'b0)
        grant_valid_drive[0] = 1'b1;
      else
        grant_valid_drive[1] = 1'b1;
      #1;
      if (!grant_ready[core_id])
        $fatal(1, "core %0d did not accept matching data grant", core_id);
      tick();
      if (core_id == 1'b0)
        grant_valid_drive[0] = 1'b0;
      else
        grant_valid_drive[1] = 1'b0;

      if (core_id == 1'b0) begin
        grant_data_valid_drive[0] = 1'b1;
        grant_data_txn_id_drive[TXN_ID_WIDTH-1:0] = txn_id;
      end else begin
        grant_data_valid_drive[1] = 1'b1;
        grant_data_txn_id_drive[2*TXN_ID_WIDTH-1:TXN_ID_WIDTH] = txn_id;
      end
      for (beat = 0; beat < LINE_BEATS; beat = beat + 1) begin
        if (core_id == 1'b0) begin
          grant_data_beat_idx_drive[2:0] = beat[2:0];
          grant_data_drive[63:0] = line_seed + beat;
          grant_data_last_drive[0] = (beat == LINE_BEATS-1);
        end else begin
          grant_data_beat_idx_drive[5:3] = beat[2:0];
          grant_data_drive[127:64] = line_seed + beat;
          grant_data_last_drive[1] = (beat == LINE_BEATS-1);
        end
        #1;
        if (!grant_data_ready[core_id])
          $fatal(1, "core %0d refill beat %0d was not accepted", core_id, beat);
        tick();
      end
      if (core_id == 1'b0)
        grant_data_valid_drive[0] = 1'b0;
      else
        grant_data_valid_drive[1] = 1'b0;

      response_seen = 1'b0;
      for (timeout = 0; timeout < 8 && !response_seen; timeout = timeout + 1) begin
        if (cpu_resp_valid[core_id])
          response_seen = 1'b1;
        else
          tick();
      end
      if (!response_seen)
        $fatal(1, "core %0d did not receive a response after refill", core_id);

      if (cpu_resp_addr[core_id] != request_addr || cpu_resp_write[core_id] ||
          cpu_resp_rdata[core_id] !=
            (line_seed + request_addr[5:3]))
        $fatal(1, "core %0d refill response address/data mismatch", core_id);
      if (!grant_commit_valid[core_id] ||
          grant_commit_txn_id[core_id] != txn_id)
        $fatal(1, "core %0d did not commit the matching grant", core_id);
      tick();
    end
  endtask

  integer core;
  integer timeout;
  integer hit_wait;
  logic [TXN_ID_WIDTH-1:0] first_txn;
  logic [TXN_ID_WIDTH-1:0] second_txn;
