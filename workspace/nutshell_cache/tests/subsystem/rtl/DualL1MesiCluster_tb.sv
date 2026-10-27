`timescale 1ns/1ps

module DualL1MesiCluster_tb;
  import coherence_protocol_pkg::*;

  logic clock = 1'b0;
  logic reset;

  logic cpu_req_valid [0:1];
  logic cpu_req_ready [0:1];
  logic [31:0] cpu_req_addr [0:1];
  logic cpu_req_write [0:1];
  logic [7:0] cpu_req_wmask [0:1];
  logic [63:0] cpu_req_wdata [0:1];
  logic cpu_resp_valid [0:1];
  logic cpu_resp_ready [0:1];
  logic [31:0] cpu_resp_addr [0:1];
  logic cpu_resp_write [0:1];
  logic [63:0] cpu_resp_rdata [0:1];
  logic [TXN_ID_WIDTH-1:0] cpu_resp_txn_id [0:1];
  logic cpu_hit_event [0:1];
  logic cpu_miss_event [0:1];
  logic metadata_commit_valid [0:1];
  logic [31:0] metadata_commit_line_addr [0:1];
  mesi_state_t metadata_commit_state [0:1];
  logic metadata_commit_is_snoop [0:1];
  logic [1:0] metadata_commit_seen = 2'b00;
  logic [5:0] monitor_cpu_state, monitor_snoop_state;
  logic [63:0] monitor_cpu_active_addr;
  logic [7:0] monitor_replace_state;

  logic [1:0] dir_req_ready;
  logic dir_req_valid;
  logic dir_req_ready_from_directory;
  logic dir_req_src_id;
  request_opcode_t dir_req_opcode;
  logic [31:0] dir_req_line_addr;
  logic [TXN_ID_WIDTH-1:0] dir_req_txn_id;

  logic put_xfer_start [0:1];
  logic [31:0] put_xfer_addr [0:1];
  logic [TXN_ID_WIDTH-1:0] put_xfer_txn_id [0:1];
  logic put_data_valid [0:1];
  logic put_data_ready [0:1];
  logic [2:0] put_data_beat_idx [0:1];
  logic [63:0] put_data [0:1];
  logic put_data_last [0:1];

  logic grant_valid [0:1];
  logic [1:0] grant_valid_drive;
  logic grant_ready [0:1];
  grant_opcode_t grant_opcode [0:1];
  logic [5:0] grant_opcode_drive;
  logic [TXN_ID_WIDTH-1:0] grant_txn_id [0:1];
  logic [2*TXN_ID_WIDTH-1:0] grant_txn_id_drive;
  logic grant_data_valid [0:1];
  logic [1:0] grant_data_valid_drive;
  logic grant_data_ready [0:1];
  logic [TXN_ID_WIDTH-1:0] grant_data_txn_id [0:1];
  logic [2*TXN_ID_WIDTH-1:0] grant_data_txn_id_drive;
  logic [2:0] grant_data_beat_idx [0:1];
  logic [5:0] grant_data_beat_idx_drive;
  logic [63:0] grant_data [0:1];
  logic [127:0] grant_data_drive;
  logic grant_data_last [0:1];
  logic [1:0] grant_data_last_drive;
  logic grant_commit_valid [0:1];
  logic grant_commit_ready [0:1];
  logic [TXN_ID_WIDTH-1:0] grant_commit_txn_id [0:1];

  logic snoop_valid [0:1];
  logic snoop_ready [0:1];
  logic [31:0] snoop_line_addr [0:1];
  snoop_opcode_t snoop_opcode [0:1];
  logic [TXN_ID_WIDTH-1:0] snoop_txn_id [0:1];
  logic snoop_rsp_valid [0:1];
  logic snoop_rsp_ready [0:1];
  snoop_response_t snoop_rsp_opcode [0:1];
  logic [TXN_ID_WIDTH-1:0] snoop_rsp_txn_id [0:1];
  logic snoop_rsp_has_data [0:1];
  logic snoop_data_valid [0:1];
  logic snoop_data_ready [0:1];
  logic [TXN_ID_WIDTH-1:0] snoop_data_txn_id [0:1];
  logic [2:0] snoop_data_beat_idx [0:1];
  logic [63:0] snoop_data [0:1];
  logic snoop_data_last [0:1];

  logic replace_valid [0:1];
  logic [1:0] replace_way [0:1];
  mesi_state_t replace_state [0:1];
  logic [31:0] replace_line_addr [0:1];
  logic [1:0] controller_protocol_error;
  logic [1:0] array_protocol_error;

  always #5 clock = ~clock;

  always @(posedge clock) begin
    if (!reset) begin
      for (integer core_id = 0; core_id < 2; core_id++) begin
        if (metadata_commit_valid[core_id]) begin
          if (metadata_commit_line_addr[core_id][5:0] != 6'b0 ||
              metadata_commit_state[core_id] != MESI_E || metadata_commit_is_snoop[core_id])
            $fatal(1, "unexpected refill metadata commit core=%0d addr=%08x state=%0d snoop=%b",
                   core_id, metadata_commit_line_addr[core_id],
                   metadata_commit_state[core_id], metadata_commit_is_snoop[core_id]);
          metadata_commit_seen[core_id] <= 1'b1;
        end
      end
    end
  end

  always_comb begin
    grant_valid[0] = grant_valid_drive[0];
    grant_valid[1] = grant_valid_drive[1];
    grant_opcode[0] = grant_opcode_t'(grant_opcode_drive[2:0]);
    grant_opcode[1] = grant_opcode_t'(grant_opcode_drive[5:3]);
    grant_txn_id[0] = grant_txn_id_drive[TXN_ID_WIDTH-1:0];
    grant_txn_id[1] = grant_txn_id_drive[2*TXN_ID_WIDTH-1:TXN_ID_WIDTH];
    grant_data_valid[0] = grant_data_valid_drive[0];
    grant_data_valid[1] = grant_data_valid_drive[1];
    grant_data_txn_id[0] = grant_data_txn_id_drive[TXN_ID_WIDTH-1:0];
    grant_data_txn_id[1] = grant_data_txn_id_drive[2*TXN_ID_WIDTH-1:TXN_ID_WIDTH];
    grant_data_beat_idx[0] = grant_data_beat_idx_drive[2:0];
    grant_data_beat_idx[1] = grant_data_beat_idx_drive[5:3];
    grant_data[0] = grant_data_drive[63:0];
    grant_data[1] = grant_data_drive[127:64];
    grant_data_last[0] = grant_data_last_drive[0];
    grant_data_last[1] = grant_data_last_drive[1];
  end

  DualL1MesiCluster dut (.*);

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

  initial begin
    reset = 1'b1;
    dir_req_ready_from_directory = 1'b1;
    grant_valid_drive = 2'b00;
    grant_data_valid_drive = 2'b00;
    grant_opcode_drive = '0;
    grant_txn_id_drive = '0;
    grant_data_txn_id_drive = '0;
    grant_data_beat_idx_drive = '0;
    grant_data_drive = '0;
    grant_data_last_drive = '0;
    first_txn = '0;
    second_txn = '0;
    for (core = 0; core < 2; core = core + 1) begin
      cpu_req_valid[core] = 1'b0;
      cpu_req_addr[core] = '0;
      cpu_req_write[core] = 1'b0;
      cpu_req_wmask[core] = 8'hFF;
      cpu_req_wdata[core] = '0;
      cpu_resp_ready[core] = 1'b1;
      put_xfer_start[core] = 1'b0;
      put_xfer_addr[core] = '0;
      put_xfer_txn_id[core] = '0;
      put_data_ready[core] = 1'b1;
      grant_commit_ready[core] = 1'b1;
      snoop_valid[core] = 1'b0;
      snoop_line_addr[core] = '0;
      snoop_opcode[core] = SNOOP_READ;
      snoop_txn_id[core] = '0;
      snoop_rsp_ready[core] = 1'b1;
      snoop_data_ready[core] = 1'b1;
    end

    tick();
    tick();
    reset = 1'b0;

    // Submit two independent misses together. The reset round-robin preference
    // must route core 0 first, and core 1 must remain pending until the mock
    // Directory accepts another request.
    cpu_req_addr[0] = 32'h0000_1018;
    cpu_req_addr[1] = 32'h0000_2028;
    cpu_req_valid[0] = 1'b1;
    cpu_req_valid[1] = 1'b1;
    #1;
    if (!cpu_req_ready[0] || !cpu_req_ready[1] ||
        !cpu_miss_event[0] || !cpu_miss_event[1] ||
        cpu_hit_event[0] || cpu_hit_event[1])
      $fatal(1, "both idle L1 request ports should accept independent misses");
    tick();
    cpu_req_valid[0] = 1'b0;
    cpu_req_valid[1] = 1'b0;

    timeout = 0;
    while (!dir_req_valid && timeout < 20) begin
      tick();
      timeout = timeout + 1;
    end
    if (!dir_req_valid || dir_req_src_id != 1'b0 ||
        dir_req_opcode != REQ_GETS || dir_req_line_addr != 32'h0000_1000)
      $fatal(1, "first clustered miss was not routed from core 0");
    first_txn = dir_req_txn_id;
    tick();
    dir_req_ready_from_directory = 1'b0;
    complete_read_refill(1'b0, 32'h0000_1018, first_txn,
                         64'hA000_0000_0000_0000);

    dir_req_ready_from_directory = 1'b1;
    timeout = 0;
    while (!dir_req_valid && timeout < 20) begin
      tick();
      timeout = timeout + 1;
    end
    if (!dir_req_valid || dir_req_src_id != 1'b1 ||
        dir_req_opcode != REQ_GETS || dir_req_line_addr != 32'h0000_2000)
      $fatal(1, "second clustered miss was not routed from core 1");
    second_txn = dir_req_txn_id;
    tick();
    dir_req_ready_from_directory = 1'b0;
    complete_read_refill(1'b1, 32'h0000_2028, second_txn,
                         64'hB000_0000_0000_0000);

    // A repeated read of a refilled line is reported as a cache hit and does
    // not issue another Directory request.
    cpu_req_addr[0] = 32'h0000_1018;
    cpu_req_valid[0] = 1'b1;
    #1;
    if (!cpu_req_ready[0] || !cpu_hit_event[0] || cpu_miss_event[0])
      $fatal(1, "refilled line was not reported as a CPU cache hit");
    tick();
    cpu_req_valid[0] = 1'b0;
    for (hit_wait = 0; hit_wait < 20 && !cpu_resp_valid[0]; hit_wait = hit_wait + 1)
      tick();
    if (!cpu_resp_valid[0] || cpu_resp_rdata[0] !=
        (64'hA000_0000_0000_0000 + 3))
      $fatal(1, "cache hit event response mismatch: valid=%b rdata=%016x expected=%016x state=%0d",
             cpu_resp_valid[0], cpu_resp_rdata[0],
             64'hA000_0000_0000_0000 + 3,
             dut.cores[0].l1_controller.cpu_state_q);
    tick();

    if (controller_protocol_error != 2'b00 || array_protocol_error != 2'b00)
      $fatal(1, "cluster raised a protocol error during independent refills");
    if (metadata_commit_seen != 2'b11)
      $fatal(1, "array metadata commit monitor missed refills: %b", metadata_commit_seen);

    $display("PASS DualL1MesiCluster_tb");
    $finish;
  end
endmodule
