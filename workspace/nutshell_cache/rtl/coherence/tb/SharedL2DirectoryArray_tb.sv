module SharedL2DirectoryArray_tb;
  import coherence_protocol_pkg::*;

  logic clock = 0;
  logic reset = 1;
  always #5 clock = ~clock;

  logic [31:0] lookup_addr;
  logic lookup_hit;
  logic [0:0] lookup_way;
  directory_state_t lookup_dir_state;
  logic [1:0] lookup_sharers;
  logic lookup_owner_id;
  logic dir_write_valid;
  logic dir_write_ready;
  logic [31:0] dir_write_line_addr;
  directory_state_t dir_write_state;
  logic [1:0] dir_write_sharers;
  logic dir_write_owner_id;
  logic [31:0] alloc_addr;
  logic alloc_victim_valid;
  logic [0:0] alloc_way;
  logic [31:0] alloc_victim_addr;
  directory_state_t alloc_victim_dir_state;
  logic [1:0] alloc_victim_sharers;
  logic alloc_victim_owner_id;
  logic alloc_victim_dirty;
  logic entry_invalidate_valid;
  logic entry_invalidate_ready;
  logic [31:0] entry_invalidate_line_addr;
  logic mark_clean_valid;
  logic mark_clean_ready;
  logic [31:0] mark_clean_line_addr;
  logic line_wr_valid;
  logic line_wr_ready;
  logic [31:0] line_wr_addr;
  logic line_wr_dirty;
  logic [2:0] line_wr_beat_idx;
  logic [63:0] line_wr_data;
  logic line_wr_last;
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

  SharedL2DirectoryArray #(.SETS(4), .WAYS(2), .TAG_WIDTH(24)) dut (.*);

  task automatic tick;
    @(posedge clock); #1;
  endtask

  task automatic write_line(input logic [31:0] addr, input logic dirty,
                            input logic [63:0] base);
    for (int beat = 0; beat < 8; beat++) begin
      @(negedge clock);
      line_wr_valid = 1; line_wr_addr = addr; line_wr_dirty = dirty;
      line_wr_beat_idx = beat[2:0]; line_wr_data = base + beat;
      line_wr_last = (beat == 7); #1;
      if (!line_wr_ready) $fatal(1, "L2 write backpressured beat %0d", beat);
      tick();
    end
    @(negedge clock); line_wr_valid = 0; line_wr_last = 0;
  endtask

  task automatic write_directory(input logic [31:0] addr,
                                 input directory_state_t state,
                                 input logic [1:0] sharers,
                                 input logic owner);
    @(negedge clock);
    dir_write_valid = 1; dir_write_line_addr = addr;
    dir_write_state = state; dir_write_sharers = sharers;
    dir_write_owner_id = owner; #1;
    if (!dir_write_ready) $fatal(1, "directory metadata write not ready");
    tick();
    @(negedge clock); dir_write_valid = 0;
  endtask

  initial begin
    lookup_addr = 0; dir_write_valid = 0; dir_write_line_addr = 0;
    dir_write_state = DIR_I; dir_write_sharers = 0; dir_write_owner_id = 0;
    alloc_addr = 0; entry_invalidate_valid = 0;
    entry_invalidate_line_addr = 0; mark_clean_valid = 0;
    mark_clean_line_addr = 0; line_wr_valid = 0; line_wr_addr = 0;
    line_wr_dirty = 0; line_wr_beat_idx = 0; line_wr_data = 0;
    line_wr_last = 0; line_rd_valid = 0; line_rd_addr = 0;
    line_data_ready = 0;
    repeat (3) tick();
    @(negedge clock); reset = 0;

    write_directory(32'h1000, DIR_U, 2'b00, 1'b0);
    write_line(32'h1000, 1'b1, 64'hC000_0000_0000_0000);
    lookup_addr = 32'h1000; #1;
    if (!lookup_hit || lookup_dir_state != DIR_U || lookup_owner_id != 0 ||
        lookup_sharers != 0)
      $fatal(1, "L2 directory lookup mismatch");

    // Eight-beat read port must hold its beat and payload while stalled.
    @(negedge clock); line_rd_valid = 1; line_rd_addr = 32'h1000; #1;
    if (!line_rd_ready || !line_rd_hit) $fatal(1, "L2 line read miss");
    tick();
    @(negedge clock); line_rd_valid = 0; #1;
    if (!line_data_valid || line_data_beat_idx != 0 ||
        line_data != 64'hC000_0000_0000_0000 || line_data_last)
      $fatal(1, "L2 beat zero mismatch");
    repeat (2) begin tick(); #1;
      if (!line_data_valid || line_data_beat_idx != 0 ||
          line_data != 64'hC000_0000_0000_0000)
        $fatal(1, "L2 read payload changed under stall");
    end
    for (int beat = 0; beat < 8; beat++) begin
      if (!line_data_valid || line_data_beat_idx != beat[2:0] ||
          line_data != (64'hC000_0000_0000_0000 + beat) ||
          line_data_last != (beat == 7))
        $fatal(1, "L2 line data mismatch beat %0d", beat);
      @(negedge clock); line_data_ready = 1; tick();
      @(negedge clock); line_data_ready = 0; #1;
    end

    // A second tag in this set fills the last way; third allocation reports
    // the live round-robin victim without evicting it automatically.
    write_directory(32'h1100, DIR_S, 2'b11, 1'b0);
    write_line(32'h1100, 1'b0, 64'hD000_0000_0000_0000);
    alloc_addr = 32'h1200; #1;
    if (!alloc_victim_valid || alloc_victim_addr != 32'h1000 ||
        alloc_victim_dir_state != DIR_U || !alloc_victim_dirty)
      $fatal(1, "L2 live victim report mismatch");

    // Reclaim is allowed only after directory is invalid and data is clean.
    write_directory(32'h1000, DIR_I, 2'b00, 1'b0);
    @(negedge clock); mark_clean_valid = 1; mark_clean_line_addr = 32'h1000;
    #1; if (!mark_clean_ready) $fatal(1, "mark-clean not ready");
    tick(); @(negedge clock); mark_clean_valid = 0;
    @(negedge clock); entry_invalidate_valid = 1;
    entry_invalidate_line_addr = 32'h1000; #1;
    if (!entry_invalidate_ready) $fatal(1, "entry invalidate not ready");
    tick(); @(negedge clock); entry_invalidate_valid = 0;
    alloc_addr = 32'h1200; #1;
    if (alloc_victim_valid || alloc_way != 1)
      $fatal(1, "invalidated slot was not made allocatable");

    if (protocol_error) $fatal(1, "unexpected L2 protocol_error");

    // Reset, then send a skipped write beat and require a sticky protocol
    // fault instead of accepting an incomplete cache line as complete.
    @(negedge clock); reset = 1; repeat (2) tick();
    @(negedge clock); reset = 0;
    line_wr_valid = 1; line_wr_addr = 32'h4000; line_wr_dirty = 1;
    line_wr_beat_idx = 0; line_wr_data = 64'h1; line_wr_last = 0;
    tick(); @(negedge clock);
    line_wr_beat_idx = 2; line_wr_data = 64'h3;
    #1; if (!line_wr_ready) $fatal(1, "malformed L2 write beat was not accepted");
    tick(); @(negedge clock); line_wr_valid = 0;
    if (!protocol_error) $fatal(1, "malformed L2 write did not latch protocol_error");
    $display("PASS SharedL2DirectoryArray_tb");
    $finish;
  end
endmodule
