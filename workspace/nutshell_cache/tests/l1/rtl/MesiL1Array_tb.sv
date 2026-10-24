module MesiL1Array_tb;
  import coherence_protocol_pkg::*;

  logic clock = 0;
  logic reset = 1;
  always #5 clock = ~clock;

  logic [31:0] cpu_lookup_addr;
  logic cpu_lookup_hit;
  logic [0:0] cpu_lookup_way;
  mesi_state_t cpu_lookup_state;
  logic [63:0] cpu_lookup_word;
  logic [31:0] snoop_lookup_addr;
  logic snoop_lookup_hit;
  logic [0:0] snoop_lookup_way;
  mesi_state_t snoop_lookup_state;
  logic replace_valid;
  logic [0:0] replace_way;
  mesi_state_t replace_state;
  logic [31:0] replace_line_addr;
  logic cpu_meta_write_valid;
  logic cpu_meta_write_ready;
  logic [31:0] cpu_meta_write_line_addr;
  mesi_state_t cpu_meta_write_state;
  logic snoop_meta_write_valid;
  logic snoop_meta_write_ready;
  logic [31:0] snoop_meta_write_line_addr;
  mesi_state_t snoop_meta_write_state;
  logic refill_valid;
  logic refill_ready;
  logic [31:0] refill_line_addr;
  logic [0:0] refill_way;
  logic [2:0] refill_beat_idx;
  logic [63:0] refill_data;
  logic refill_last;
  logic cpu_store_valid;
  logic cpu_store_ready;
  logic [31:0] cpu_store_addr;
  logic [0:0] cpu_store_way;
  logic [7:0] cpu_store_wmask;
  logic [63:0] cpu_store_wdata;
  logic line_rd_valid;
  logic line_rd_ready;
  logic [31:0] line_rd_addr;
  logic line_rd_hit;
  logic line_data_valid;
  logic line_data_ready;
  logic [2:0] line_data_beat_idx;
  logic [63:0] line_data;
  logic line_data_last;
  logic protocol_error;

  MesiL1Array #(.SETS(4), .WAYS(2), .TAG_WIDTH(24)) dut (.*);

  task automatic tick;
    @(posedge clock); #1;
  endtask

  task automatic refill_line(input logic [31:0] addr, input logic way,
                             input logic [63:0] base);
    for (int beat = 0; beat < 8; beat++) begin
      @(negedge clock);
      refill_valid = 1;
      refill_line_addr = addr;
      refill_way = way;
      refill_beat_idx = beat[2:0];
      refill_data = base + beat;
      refill_last = (beat == 7);
      #1;
      if (!refill_ready) $fatal(1, "refill unexpectedly backpressured beat %0d", beat);
      tick();
    end
    @(negedge clock); refill_valid = 0; refill_last = 0;
  endtask

  initial begin
    cpu_lookup_addr = 0; snoop_lookup_addr = 0;
    cpu_meta_write_valid = 0; cpu_meta_write_line_addr = 0;
    cpu_meta_write_state = MESI_I;
    snoop_meta_write_valid = 0; snoop_meta_write_line_addr = 0;
    snoop_meta_write_state = MESI_I;
    refill_valid = 0; refill_line_addr = 0; refill_way = 0;
    refill_beat_idx = 0; refill_data = 0; refill_last = 0;
    cpu_store_valid = 0; cpu_store_addr = 0; cpu_store_way = 0;
    cpu_store_wmask = 0; cpu_store_wdata = 0;
    line_rd_valid = 0; line_rd_addr = 0; line_data_ready = 0;
    repeat (3) tick();
    @(negedge clock); reset = 0;

    refill_line(32'h0000_1000, 1'b0, 64'hA000_0000_0000_0000);
    @(negedge clock);
    cpu_meta_write_valid = 1;
    cpu_meta_write_line_addr = 32'h0000_1000;
    cpu_meta_write_state = MESI_M;
    #1; if (!cpu_meta_write_ready) $fatal(1, "metadata write not ready");
    tick();
    @(negedge clock); cpu_meta_write_valid = 0;
    cpu_lookup_addr = 32'h0000_1000;
    #1;
    if (!cpu_lookup_hit || cpu_lookup_way != 0 || cpu_lookup_state != MESI_M ||
        cpu_lookup_word != 64'hA000_0000_0000_0000)
      $fatal(1, "refill lookup/data mismatch");

    // Byte lanes 0 and 2 update only the selected word.
    @(negedge clock);
    cpu_store_valid = 1; cpu_store_addr = 32'h0000_1000;
    cpu_store_way = 0; cpu_store_wmask = 8'b0000_0101;
    cpu_store_wdata = 64'h1122_3344_5566_7788;
    tick();
    @(negedge clock); cpu_store_valid = 0; cpu_lookup_addr = 32'h1000;
    #1;
    if (cpu_lookup_word != 64'hA000_0000_0066_0088)
      $fatal(1, "byte masked store mismatch: %h", cpu_lookup_word);

    // Snoop metadata write and lookup observe the new stable state.
    @(negedge clock);
    snoop_meta_write_valid = 1; snoop_meta_write_line_addr = 32'h1000;
    snoop_meta_write_state = MESI_S;
    tick();
    @(negedge clock); snoop_meta_write_valid = 0;
    snoop_lookup_addr = 32'h1000; #1;
    if (!snoop_lookup_hit || snoop_lookup_state != MESI_S)
      $fatal(1, "snoop metadata update mismatch");

    // Read all eight beats; stall beat zero and ensure it remains stable.
    @(negedge clock); line_rd_valid = 1; line_rd_addr = 32'h1000;
    #1; if (!line_rd_ready || !line_rd_hit) $fatal(1, "line read miss");
    tick();
    @(negedge clock); line_rd_valid = 0;
    #1;
    if (!line_data_valid || line_data_beat_idx != 0 || line_data_last ||
        line_data != 64'hA000_0000_0066_0088)
      $fatal(1, "line read beat 0 mismatch");
    repeat (2) begin tick(); #1;
      if (!line_data_valid || line_data_beat_idx != 0 ||
          line_data != 64'hA000_0000_0066_0088)
        $fatal(1, "line read beat changed under backpressure");
    end
    for (int beat = 0; beat < 8; beat++) begin
      if (!line_data_valid || line_data_beat_idx != beat[2:0] ||
          line_data != (64'hA000_0000_0000_0000 + beat +
                        ((beat == 0) ? 64'h0066_0088 : 0)) ||
          line_data_last != (beat == 7)) begin
        // Beat zero has two byte lanes overwritten; compare its exact value.
        if (!(beat == 0 && line_data_valid && line_data_beat_idx == 0 &&
              line_data == 64'hA000_0000_0066_0088))
          $fatal(1, "line data mismatch at beat %0d: %h", beat, line_data);
      end
      @(negedge clock); line_data_ready = 1; tick();
      @(negedge clock); line_data_ready = 0; #1;
    end

    // Fill the other way and confirm replacement points at a live line.
    refill_line(32'h0000_1100, 1'b1, 64'hB000_0000_0000_0000);
    @(negedge clock); cpu_meta_write_valid = 1;
    cpu_meta_write_line_addr = 32'h1100; cpu_meta_write_state = MESI_E;
    tick(); @(negedge clock); cpu_meta_write_valid = 0;
    cpu_lookup_addr = 32'h1200; #1;
    if (!replace_valid || replace_way != 0 || replace_state != MESI_S ||
        replace_line_addr != 32'h1000)
      $fatal(1, "replacement victim selection mismatch");

    if (protocol_error) $fatal(1, "unexpected array protocol_error");

    // Reset, then violate the refill beat sequence. The block must latch the
    // protocol fault rather than silently complete a partial line.
    @(negedge clock); reset = 1; repeat (2) tick();
    @(negedge clock); reset = 0;
    refill_valid = 1; refill_line_addr = 32'h2000;
    refill_way = 0; refill_beat_idx = 0; refill_data = 64'h1; refill_last = 0;
    tick(); @(negedge clock);
    refill_beat_idx = 2; refill_data = 64'h3;
    #1; if (!refill_ready) $fatal(1, "malformed refill beat was not accepted");
    tick(); @(negedge clock); refill_valid = 0;
    if (!protocol_error) $fatal(1, "malformed refill did not latch protocol_error");
    $display("PASS MesiL1Array_tb");
    $finish;
  end
endmodule
