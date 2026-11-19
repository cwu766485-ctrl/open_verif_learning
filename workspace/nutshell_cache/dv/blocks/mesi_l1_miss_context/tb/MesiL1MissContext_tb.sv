module MesiL1MissContext_tb;
  import coherence_protocol_pkg::*;

  localparam int NUM_CONTEXTS = 2;

  logic clock;
  logic reset = 1'b1;
  initial clock = 1'b0;
  always #5 clock = ~clock;

  logic [NUM_CONTEXTS-1:0] cpu_req_valid, cpu_req_ready;
  logic [NUM_CONTEXTS-1:0][31:0] cpu_req_addr;
  logic [NUM_CONTEXTS-1:0] cpu_req_write, cpu_req_hit;
  mesi_state_t [NUM_CONTEXTS-1:0] cpu_req_line_state;
  logic [NUM_CONTEXTS-1:0][TXN_ID_WIDTH-1:0] cpu_req_txn_id;
  logic [NUM_CONTEXTS-1:0] ctx_resp_valid, ctx_resp_ready;
  logic [NUM_CONTEXTS-1:0][31:0] ctx_resp_addr;
  logic [NUM_CONTEXTS-1:0] ctx_resp_write;
  logic [NUM_CONTEXTS-1:0][TXN_ID_WIDTH-1:0] ctx_resp_txn_id;
  logic [NUM_CONTEXTS-1:0][63:0] ctx_resp_data;
  logic cpu_resp_valid;
  logic cpu_resp_ready;
  logic [31:0] cpu_resp_addr;
  logic cpu_resp_write;
  logic [TXN_ID_WIDTH-1:0] cpu_resp_txn_id;
  logic [63:0] cpu_resp_data;
  logic [1:0] response_order_occupancy;
  logic reserve_valid, reserve_ready;
  logic [TXN_ID_WIDTH-1:0] reserve_tag;
  logic complete_valid, complete_ready;
  logic [TXN_ID_WIDTH-1:0] complete_tag;
  logic [31:0] complete_addr;
  logic complete_write;
  logic [63:0] complete_data;
  logic complete_sel_valid, complete_sel_idx;

  logic [NUM_CONTEXTS-1:0] dir_req_valid, dir_req_ready;
  request_opcode_t [NUM_CONTEXTS-1:0] dir_req_opcode;
  logic [NUM_CONTEXTS-1:0][31:0] dir_req_line_addr;
  logic [NUM_CONTEXTS-1:0][TXN_ID_WIDTH-1:0] dir_req_txn_id;
  logic [NUM_CONTEXTS-1:0] grant_valid, grant_ready;
  grant_opcode_t [NUM_CONTEXTS-1:0] grant_opcode;
  logic [NUM_CONTEXTS-1:0][TXN_ID_WIDTH-1:0] grant_txn_id;

  logic [NUM_CONTEXTS-1:0] grant_data_valid, grant_data_ready;
  logic [NUM_CONTEXTS-1:0][TXN_ID_WIDTH-1:0] grant_data_txn_id;
  logic [NUM_CONTEXTS-1:0][2:0] grant_data_beat_idx;
  logic [NUM_CONTEXTS-1:0][63:0] grant_data;
  logic [NUM_CONTEXTS-1:0] grant_data_last;
  logic [NUM_CONTEXTS-1:0] refill_valid, refill_ready;
  logic [NUM_CONTEXTS-1:0][TXN_ID_WIDTH-1:0] refill_txn_id;
  logic [NUM_CONTEXTS-1:0][2:0] refill_beat_idx;
  logic [NUM_CONTEXTS-1:0][63:0] refill_data;
  logic [NUM_CONTEXTS-1:0] refill_last;
  logic [NUM_CONTEXTS-1:0] grant_commit_valid, grant_commit_ready;
  logic [NUM_CONTEXTS-1:0][TXN_ID_WIDTH-1:0] grant_commit_txn_id;
  logic [NUM_CONTEXTS-1:0] cpu_meta_write_valid, cpu_meta_write_ready;
  logic [NUM_CONTEXTS-1:0][31:0] cpu_meta_write_line_addr;
  mesi_state_t [NUM_CONTEXTS-1:0] cpu_meta_write_state;
  logic [NUM_CONTEXTS-1:0] protocol_error;
  logic [NUM_CONTEXTS-1:0][2:0] monitor_cpu_state;
  logic [NUM_CONTEXTS-1:0][31:0] monitor_cpu_active_addr;

  for (genvar context_idx = 0; context_idx < NUM_CONTEXTS; context_idx++) begin : gen_context
    MesiL1MissContext #(
      .EXTERNAL_TXN_ID(1'b1)
    ) dut (
      .clock,
      .reset,
      .cpu_req_valid(cpu_req_valid[context_idx]),
      .cpu_req_ready(cpu_req_ready[context_idx]),
      .cpu_req_addr(cpu_req_addr[context_idx]),
      .cpu_req_write(cpu_req_write[context_idx]),
      .cpu_req_hit(cpu_req_hit[context_idx]),
      .cpu_req_line_state(cpu_req_line_state[context_idx]),
      .cpu_req_txn_id(cpu_req_txn_id[context_idx]),
      .cpu_resp_valid(ctx_resp_valid[context_idx]),
      .cpu_resp_ready(ctx_resp_ready[context_idx]),
      .cpu_resp_addr(ctx_resp_addr[context_idx]),
      .cpu_resp_write(ctx_resp_write[context_idx]),
      .cpu_resp_txn_id(ctx_resp_txn_id[context_idx]),
      .dir_req_valid(dir_req_valid[context_idx]),
      .dir_req_ready(dir_req_ready[context_idx]),
      .dir_req_opcode(dir_req_opcode[context_idx]),
      .dir_req_line_addr(dir_req_line_addr[context_idx]),
      .dir_req_txn_id(dir_req_txn_id[context_idx]),
      .grant_valid(grant_valid[context_idx]),
      .grant_ready(grant_ready[context_idx]),
      .grant_opcode(grant_opcode[context_idx]),
      .grant_txn_id(grant_txn_id[context_idx]),
      .grant_data_valid(grant_data_valid[context_idx]),
      .grant_data_ready(grant_data_ready[context_idx]),
      .grant_data_txn_id(grant_data_txn_id[context_idx]),
      .grant_data_beat_idx(grant_data_beat_idx[context_idx]),
      .grant_data(grant_data[context_idx]),
      .grant_data_last(grant_data_last[context_idx]),
      .refill_valid(refill_valid[context_idx]),
      .refill_ready(refill_ready[context_idx]),
      .refill_txn_id(refill_txn_id[context_idx]),
      .refill_beat_idx(refill_beat_idx[context_idx]),
      .refill_data(refill_data[context_idx]),
      .refill_last(refill_last[context_idx]),
      .grant_commit_valid(grant_commit_valid[context_idx]),
      .grant_commit_ready(grant_commit_ready[context_idx]),
      .grant_commit_txn_id(grant_commit_txn_id[context_idx]),
      .cpu_meta_write_valid(cpu_meta_write_valid[context_idx]),
      .cpu_meta_write_ready(cpu_meta_write_ready[context_idx]),
      .cpu_meta_write_line_addr(cpu_meta_write_line_addr[context_idx]),
      .cpu_meta_write_state(cpu_meta_write_state[context_idx]),
      .protocol_error(protocol_error[context_idx]),
      .monitor_cpu_state(monitor_cpu_state[context_idx]),
      .monitor_cpu_active_addr(monitor_cpu_active_addr[context_idx])
    );
  end

  // Each independent context may finish out of order. Capture its completed
  // payload by transaction tag, then expose responses through the untagged
  // LSU interface in original reservation order.
  always_comb begin
    complete_sel_valid = 1'b0;
    complete_sel_idx = 1'b0;
    for (int unsigned i = 0; i < NUM_CONTEXTS; i++) begin
      if (ctx_resp_valid[i] && !complete_sel_valid) begin
        complete_sel_valid = 1'b1;
        complete_sel_idx = 1'(i);
      end
    end
    complete_valid = complete_sel_valid;
    complete_tag = ctx_resp_txn_id[complete_sel_idx];
    complete_addr = ctx_resp_addr[complete_sel_idx];
    complete_write = ctx_resp_write[complete_sel_idx];
    complete_data = ctx_resp_data[complete_sel_idx];
  end

  always_comb begin
    ctx_resp_ready = '0;
    if (complete_sel_valid)
      ctx_resp_ready[complete_sel_idx] = complete_ready;
  end

  MesiL1MissResponseOrder response_order (
    .clock, .reset,
    .reserve_valid, .reserve_ready, .reserve_tag,
    .complete_valid, .complete_ready, .complete_tag,
    .complete_addr, .complete_write, .complete_data,
    .resp_valid(cpu_resp_valid), .resp_ready(cpu_resp_ready),
    .resp_tag(cpu_resp_txn_id), .resp_addr(cpu_resp_addr),
    .resp_write(cpu_resp_write), .resp_data(cpu_resp_data),
    .monitor_occupancy(response_order_occupancy)
  );

  task automatic tick;
    @(posedge clock);
    #1;
  endtask

  task automatic reserve_response(input logic [TXN_ID_WIDTH-1:0] tag);
    reserve_valid = 1'b1;
    reserve_tag = tag;
    #1;
    if (!reserve_ready)
      $fatal(1, "response reservation tag %0d unexpectedly blocked", tag);
    tick();
    reserve_valid = 1'b0;
  endtask

  task automatic send_refill(input int context_idx, input logic [3:0] txn_id,
                             input logic [63:0] base_data);
    for (int beat = 0; beat < 8; beat++) begin
      @(negedge clock);
      grant_data_valid = '1;
      grant_data_txn_id = {NUM_CONTEXTS{txn_id}};
      grant_data_beat_idx = {NUM_CONTEXTS{3'(beat)}};
      grant_data = {NUM_CONTEXTS{base_data + 64'(beat)}};
      grant_data_last = {NUM_CONTEXTS{beat == 7}};
      #1;
      if (!grant_data_ready[context_idx] || !refill_valid[context_idx] ||
          grant_data_ready[1-context_idx] || refill_valid[1-context_idx])
        $fatal(1, "refill txn %0d beat %0d was not isolated to context %0d",
               txn_id, beat, context_idx);
      if (refill_txn_id[context_idx] != txn_id ||
          refill_beat_idx[context_idx] != 3'(beat) ||
          refill_data[context_idx] != base_data + 64'(beat) ||
          refill_last[context_idx] != (beat == 7))
        $fatal(1, "refill payload/tag mismatch for txn %0d beat %0d",
               txn_id, beat);
      tick();
      grant_data_valid = '0;
    end
  endtask

  initial begin : test_sequence
    cpu_req_valid = '0;
    cpu_req_ready = '1;
    cpu_req_addr = '0;
    cpu_req_write = '0;
    cpu_req_hit = '0;
    cpu_req_line_state = '{default: MESI_I};
    cpu_req_txn_id = '0;
    cpu_resp_ready = 1'b0;
    reserve_valid = 1'b0;
    reserve_tag = '0;
    dir_req_ready = '1;
    grant_valid = '0;
    grant_opcode = '{default: GRANT_DATA_S};
    grant_txn_id = '0;
    grant_data_valid = '0;
    grant_data_txn_id = '0;
    grant_data_beat_idx = '0;
    grant_data = '0;
    grant_data_last = '0;
    refill_ready = '1;
    grant_commit_ready = '1;
    cpu_meta_write_ready = '0;

    repeat (2) tick();
    reset = 1'b0;

    // Allocate two independent miss contexts with externally assigned tags.
    reserve_response(4'h3);
    reserve_response(4'h9);
    @(negedge clock);
    cpu_req_valid = '1;
    cpu_req_addr[0] = 32'h0000_1018;
    cpu_req_addr[1] = 32'h0000_9018;
    cpu_req_txn_id[0] = 4'h3;
    cpu_req_txn_id[1] = 4'h9;
    tick();
    cpu_req_valid = '0;
    #1;
    if (dir_req_valid != '1 || dir_req_txn_id[0] != 4'h3 ||
        dir_req_txn_id[1] != 4'h9 || dir_req_line_addr[0] != 32'h0000_1000 ||
        dir_req_line_addr[1] != 32'h0000_9000 ||
        dir_req_txn_id[0] == dir_req_txn_id[1] ||
        dir_req_opcode[0] != REQ_GETS || dir_req_opcode[1] != REQ_GETS ||
        monitor_cpu_state != {2{3'd1}} ||
        monitor_cpu_active_addr[0] != 32'h0000_1018 ||
        monitor_cpu_active_addr[1] != 32'h0000_9018)
      $fatal(1, "independent Directory requests lost their assigned tags/addresses");
    tick();
    dir_req_ready = '0;

    // A shared response tag may be observed by both contexts; only its owner
    // may acknowledge it. Complete the younger tag first to exercise routing.
    @(negedge clock);
    grant_valid = '1;
    grant_txn_id = {2{4'h9}};
    #1;
    if (grant_ready != 2'b10)
      $fatal(1, "grant ID 9 was not accepted exclusively by context 1: %b", grant_ready);
    tick();
    grant_valid = '0;

    @(negedge clock);
    grant_valid = '1;
    grant_txn_id = {2{4'h3}};
    #1;
    if (grant_ready != 2'b01)
      $fatal(1, "grant ID 3 was not accepted exclusively by context 0: %b", grant_ready);
    tick();
    grant_valid = '0;

    // Return all beats for the younger miss before the older miss.
    send_refill(1, 4'h9, 64'h9000_0000_0000_0000);
    send_refill(0, 4'h3, 64'h3000_0000_0000_0000);

    #1;
    if (cpu_meta_write_valid != '1 ||
        cpu_meta_write_line_addr[1] != 32'h0000_9000 ||
        cpu_meta_write_state[1] != MESI_S ||
        cpu_meta_write_line_addr[0] != 32'h0000_1000 ||
        cpu_meta_write_state[0] != MESI_S)
      $fatal(1, "parallel context metadata commits were misrouted");
    cpu_resp_ready = 1'b0;
    cpu_meta_write_ready = 2'b10;
    tick();
    #1;
    if (cpu_meta_write_valid != 2'b01 || cpu_meta_write_line_addr[0] != 32'h0000_1000)
      $fatal(1, "metadata backpressure was not isolated to the owning context");
    if (!grant_commit_valid[1] || grant_commit_txn_id[1] != 4'h9 ||
        !ctx_resp_valid[1] || ctx_resp_txn_id[1] != 4'h9)
      $fatal(1, "context 1 did not commit its grant before exposing completion");
    ctx_resp_data[0] = 64'h3000_0000_0000_0003;
    ctx_resp_data[1] = 64'h9000_0000_0000_0009;
    tick();
    #1;
    if (cpu_resp_valid || response_order_occupancy != 2'd2)
      $fatal(1, "younger context completion escaped ordered LSU response queue");
    cpu_meta_write_ready = '1;
    tick();

    // The younger context completed first but is held. Once the older context
    // completes, the untagged LSU must observe A then B, with each payload
    // retained while response backpressure is asserted.
    #1;
    if (ctx_resp_valid != 2'b01 || ctx_resp_addr[0] != 32'h0000_1018 ||
        ctx_resp_write[0] || ctx_resp_txn_id[0] != 4'h3 ||
        !grant_commit_valid[0] ||
        grant_commit_txn_id[0] != 4'h3 ||
        protocol_error != '0) begin
      $fatal(1, "older context completion/commit association mismatch");
    end
    tick();
    #1;
    if (!cpu_resp_valid || cpu_resp_addr != 32'h0000_1018 ||
        cpu_resp_txn_id != 4'h3 || cpu_resp_write ||
        cpu_resp_data != 64'h3000_0000_0000_0003)
      $fatal(1, "older response did not retire first with its data");
    repeat (2) begin
      tick();
      if (!cpu_resp_valid || cpu_resp_addr != 32'h0000_1018 ||
          cpu_resp_txn_id != 4'h3 ||
          cpu_resp_data != 64'h3000_0000_0000_0003)
        $fatal(1, "ordered LSU response changed under backpressure");
    end
    cpu_resp_ready = 1'b1;
    tick();
    #1;
    if (!cpu_resp_valid || cpu_resp_addr != 32'h0000_9018 ||
        cpu_resp_txn_id != 4'h9 ||
        cpu_resp_data != 64'h9000_0000_0000_0009)
      $fatal(1, "younger response did not follow the older response");
    tick();
    if (cpu_resp_valid || response_order_occupancy != 0 || protocol_error != '0)
      $fatal(1, "contexts did not retire cleanly");

    $display("PASS MesiL1MissContext_tb: external ID routing, out-of-order refill association, response stall");
    $finish;
  end
endmodule
