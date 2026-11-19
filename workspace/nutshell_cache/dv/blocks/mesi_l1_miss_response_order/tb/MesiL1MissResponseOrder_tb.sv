module MesiL1MissResponseOrder_tb;
  localparam int TAG_WIDTH = coherence_protocol_pkg::TXN_ID_WIDTH;

  logic clock;
  logic reset;
  logic reserve_valid;
  logic reserve_ready;
  logic [TAG_WIDTH-1:0] reserve_tag;
  logic complete_valid;
  logic complete_ready;
  logic [TAG_WIDTH-1:0] complete_tag;
  logic [31:0] complete_addr;
  logic complete_write;
  logic [63:0] complete_data;
  logic resp_valid;
  logic resp_ready;
  logic [TAG_WIDTH-1:0] resp_tag;
  logic [31:0] resp_addr;
  logic resp_write;
  logic [63:0] resp_data;
  logic [1:0] monitor_occupancy;

  initial begin
    clock = 1'b0;
    forever #5 clock = ~clock;
  end

  MesiL1MissResponseOrder #(.TAG_WIDTH(TAG_WIDTH)) dut (.*);

  task automatic tick;
    @(posedge clock);
    #1;
  endtask

  task automatic reserve(input logic [TAG_WIDTH-1:0] tag);
    reserve_valid = 1'b1;
    reserve_tag = tag;
    #1;
    if (!reserve_ready)
      $fatal(1, "response order reservation unexpectedly blocked");
    tick();
    reserve_valid = 1'b0;
  endtask

  task automatic complete(
    input logic [TAG_WIDTH-1:0] tag,
    input logic [31:0] addr,
    input logic is_write,
    input logic [63:0] data
  );
    complete_valid = 1'b1;
    complete_tag = tag;
    complete_addr = addr;
    complete_write = is_write;
    complete_data = data;
    #1;
    if (!complete_ready)
      $fatal(1, "completion tag %0d did not match a live reservation", tag);
    tick();
    complete_valid = 1'b0;
  endtask

  initial begin
    reset = 1'b1;
    reserve_valid = 1'b0;
    reserve_tag = '0;
    complete_valid = 1'b0;
    complete_tag = '0;
    complete_addr = '0;
    complete_write = 1'b0;
    complete_data = '0;
    resp_ready = 1'b0;
    tick();
    reset = 1'b0;

    // Reserve older A before younger B, then finish B first. B must not be
    // exposed to the untagged LSU until A has retired.
    reserve(TAG_WIDTH'(3));
    reserve_valid = 1'b1;
    reserve_tag = TAG_WIDTH'(3);
    #1;
    if (reserve_ready)
      $fatal(1, "duplicate live transaction tag was accepted");
    reserve_valid = 1'b0;
    reserve(TAG_WIDTH'(9));
    if (monitor_occupancy != 2 || reserve_ready)
      $fatal(1, "two-entry response queue did not apply full backpressure");

    complete(TAG_WIDTH'(9), 32'h0000_9018, 1'b0, 64'hfeed_0000_0000_0099);
    if (resp_valid)
      $fatal(1, "younger completion escaped before the older miss");

    complete(TAG_WIDTH'(3), 32'h0000_1018, 1'b1, 64'hface_0000_0000_0033);
    if (!resp_valid || resp_tag != TAG_WIDTH'(3) ||
        resp_addr != 32'h0000_1018 || !resp_write ||
        resp_data != 64'hface_0000_0000_0033)
      $fatal(1, "oldest completed response was not selected first");

    // A stalled response must retain its payload. Then retire A followed by B.
    repeat (2) begin
      tick();
      if (!resp_valid || resp_tag != TAG_WIDTH'(3) ||
          resp_addr != 32'h0000_1018 || !resp_write ||
          resp_data != 64'hface_0000_0000_0033)
        $fatal(1, "response payload changed under backpressure");
    end
    resp_ready = 1'b1;
    tick();
    if (!resp_valid || resp_tag != TAG_WIDTH'(9) ||
        resp_addr != 32'h0000_9018 || resp_write ||
        resp_data != 64'hfeed_0000_0000_0099)
      $fatal(1, "younger response did not follow the older response");
    tick();
    resp_ready = 1'b0;
    if (monitor_occupancy != 0 || resp_valid)
      $fatal(1, "response queue did not retire both entries");

    // Released capacity may be reused without stale completion metadata.
    reserve(TAG_WIDTH'(3));
    complete(TAG_WIDTH'(3), 32'h0000_3018, 1'b0,
             64'hcafe_0000_0000_0033);
    resp_ready = 1'b1;
    if (!resp_valid || resp_addr != 32'h0000_3018 ||
        resp_data != 64'hcafe_0000_0000_0033)
      $fatal(1, "reused tag returned stale response payload");
    tick();

    reserve(TAG_WIDTH'(5));
    reset = 1'b1;
    tick();
    reset = 1'b0;
    if (monitor_occupancy != 0 || resp_valid || !reserve_ready)
      $fatal(1, "reset did not cancel queued miss response state");

    $display("PASS: miss responses retire in reservation order with ID routing and backpressure");
    $finish;
  end
endmodule
