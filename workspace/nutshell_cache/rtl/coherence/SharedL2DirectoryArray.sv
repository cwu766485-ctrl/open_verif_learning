// 256 KiB, 8-way shared L2 tag/data and inclusive directory array.
// The array intentionally does not evict a live directory entry by itself:
// a full-set victim must first be back-invalidated by the subsystem controller.
module SharedL2DirectoryArray #(
  parameter int SETS = 512,
  parameter int WAYS = 8,
  parameter int TAG_WIDTH = 17
) (
  input  logic clock,
  input  logic reset,

  input  logic [31:0] lookup_addr,
  output logic lookup_hit,
  output logic [$clog2(WAYS)-1:0] lookup_way,
  output coherence_protocol_pkg::directory_state_t lookup_dir_state,
  output logic [1:0] lookup_sharers,
  output logic lookup_owner_id,

  // Metadata writes may update an existing line or allocate an invalid way.
  input  logic dir_write_valid,
  output logic dir_write_ready,
  input  logic [31:0] dir_write_line_addr,
  input  coherence_protocol_pkg::directory_state_t dir_write_state,
  input  logic [1:0] dir_write_sharers,
  input  logic dir_write_owner_id,

  // A miss allocator uses this information to request inclusion eviction.
  // No replacement occurs until the victim directory entry is explicitly
  // invalidated and its dirty owner data has been recovered.
  input  logic [31:0] alloc_addr,
  output logic alloc_victim_valid,
  output logic [$clog2(WAYS)-1:0] alloc_way,
  output logic [31:0] alloc_victim_addr,
  output coherence_protocol_pkg::directory_state_t alloc_victim_dir_state,
  output logic [1:0] alloc_victim_sharers,
  output logic alloc_victim_owner_id,
  output logic alloc_victim_dirty,

  // Called only after all recorded L1 copies of this inclusive entry have
  // been invalidated and any dirty owner line has been recovered.
  input  logic entry_invalidate_valid,
  output logic entry_invalidate_ready,
  input  logic [31:0] entry_invalidate_line_addr,
  input  logic mark_clean_valid,
  output logic mark_clean_ready,
  input  logic [31:0] mark_clean_line_addr,

  // Full-line writes are used for memory fills and owner SnoopData.
  input  logic line_wr_valid,
  output logic line_wr_ready,
  input  logic [31:0] line_wr_addr,
  input  logic line_wr_dirty,
  input  logic [2:0] line_wr_beat_idx,
  input  logic [63:0] line_wr_data,
  input  logic line_wr_last,

  // Serialized full-line read port for L1 grant/refill.
  input  logic line_rd_valid,
  output logic line_rd_ready,
  input  logic [31:0] line_rd_addr,
  output logic line_rd_hit,
  output logic line_data_valid,
  input  logic line_data_ready,
  output logic [2:0] line_data_beat_idx,
  output logic [63:0] line_data,
  output logic line_data_last,

  output logic protocol_error
);
  import coherence_protocol_pkg::*;
  localparam int SET_WIDTH = $clog2(SETS);
  localparam int WAY_WIDTH = $clog2(WAYS);

  logic valid_array [0:SETS-1][0:WAYS-1];
  logic [TAG_WIDTH-1:0] tag_array [0:SETS-1][0:WAYS-1];
  directory_state_t dir_state_array [0:SETS-1][0:WAYS-1];
  logic [1:0] sharer_array [0:SETS-1][0:WAYS-1];
  logic owner_array [0:SETS-1][0:WAYS-1];
  logic dirty_array [0:SETS-1][0:WAYS-1];
  logic [63:0] data_array [0:SETS-1][0:WAYS-1][0:7];
  logic [WAY_WIDTH-1:0] replacement_ptr [0:SETS-1];

  logic [SET_WIDTH-1:0] lookup_set, write_set, alloc_set, rd_set;
  logic [TAG_WIDTH-1:0] lookup_tag, write_tag, alloc_tag, rd_tag;
  logic write_hit, write_free_found;
  logic [WAY_WIDTH-1:0] write_way;
  logic alloc_hit, alloc_free_found;
  logic [WAY_WIDTH-1:0] alloc_free_way;
  logic line_wr_hit, line_wr_free_found;
  logic [WAY_WIDTH-1:0] line_wr_way;
  logic invalidate_hit;
  logic [SET_WIDTH-1:0] invalidate_set;
  logic [TAG_WIDTH-1:0] invalidate_tag;
  logic [WAY_WIDTH-1:0] invalidate_way;
  logic clean_hit;
  logic [SET_WIDTH-1:0] clean_set;
  logic [TAG_WIDTH-1:0] clean_tag;
  logic [WAY_WIDTH-1:0] clean_way;
  logic line_rd_busy_q;
  logic [SET_WIDTH-1:0] line_rd_set_q;
  logic [WAY_WIDTH-1:0] line_rd_way_q;
  logic [2:0] line_rd_beat_q;
  logic line_wr_pending_q;
  logic [31:0] line_wr_addr_q;
  logic [WAY_WIDTH-1:0] line_wr_way_q;
  logic line_wr_dirty_q;
  logic [2:0] line_wr_expected_beat_q;
  integer i, j;

  always_comb begin
    lookup_set = lookup_addr[6 +: SET_WIDTH];
    write_set = dir_write_line_addr[6 +: SET_WIDTH];
    alloc_set = alloc_addr[6 +: SET_WIDTH];
    rd_set = line_rd_addr[6 +: SET_WIDTH];
    invalidate_set = entry_invalidate_line_addr[6 +: SET_WIDTH];
    clean_set = mark_clean_line_addr[6 +: SET_WIDTH];
    lookup_tag = lookup_addr[6+SET_WIDTH +: TAG_WIDTH];
    write_tag = dir_write_line_addr[6+SET_WIDTH +: TAG_WIDTH];
    alloc_tag = alloc_addr[6+SET_WIDTH +: TAG_WIDTH];
    rd_tag = line_rd_addr[6+SET_WIDTH +: TAG_WIDTH];
    invalidate_tag = entry_invalidate_line_addr[6+SET_WIDTH +: TAG_WIDTH];
    clean_tag = mark_clean_line_addr[6+SET_WIDTH +: TAG_WIDTH];

    lookup_hit = 1'b0;
    lookup_way = '0;
    lookup_dir_state = DIR_I;
    lookup_sharers = 2'b00;
    lookup_owner_id = 1'b0;
    write_hit = 1'b0;
    write_free_found = 1'b0;
    write_way = replacement_ptr[write_set];
    alloc_hit = 1'b0;
    alloc_free_found = 1'b0;
    alloc_free_way = replacement_ptr[alloc_set];
    line_wr_hit = 1'b0;
    line_wr_free_found = 1'b0;
    line_wr_way = replacement_ptr[line_wr_addr[6 +: SET_WIDTH]];
    line_rd_hit = 1'b0;
    invalidate_hit = 1'b0;
    invalidate_way = '0;
    clean_hit = 1'b0;
    clean_way = '0;

    for (integer w = 0; w < WAYS; w = w + 1) begin
      if (valid_array[lookup_set][w] && tag_array[lookup_set][w] == lookup_tag) begin
        lookup_hit = 1'b1;
        lookup_way = WAY_WIDTH'(w);
        lookup_dir_state = dir_state_array[lookup_set][w];
        lookup_sharers = sharer_array[lookup_set][w];
        lookup_owner_id = owner_array[lookup_set][w];
      end
      if (valid_array[write_set][w] && tag_array[write_set][w] == write_tag) begin
        write_hit = 1'b1;
        write_way = WAY_WIDTH'(w);
      end
      if (!valid_array[write_set][w]) begin
        write_free_found = 1'b1;
        write_way = WAY_WIDTH'(w);
      end
      if (valid_array[alloc_set][w] && tag_array[alloc_set][w] == alloc_tag)
        alloc_hit = 1'b1;
      if (!valid_array[alloc_set][w]) begin
        alloc_free_found = 1'b1;
        alloc_free_way = WAY_WIDTH'(w);
      end
      if (valid_array[line_wr_addr[6 +: SET_WIDTH]][w] &&
          tag_array[line_wr_addr[6 +: SET_WIDTH]][w] ==
            line_wr_addr[6+SET_WIDTH +: TAG_WIDTH]) begin
        line_wr_hit = 1'b1;
        line_wr_way = WAY_WIDTH'(w);
      end
      if (!valid_array[line_wr_addr[6 +: SET_WIDTH]][w]) begin
        line_wr_free_found = 1'b1;
        line_wr_way = WAY_WIDTH'(w);
      end
      if (valid_array[rd_set][w] && tag_array[rd_set][w] == rd_tag)
        line_rd_hit = 1'b1;
      if (valid_array[invalidate_set][w] &&
          tag_array[invalidate_set][w] == invalidate_tag) begin
        invalidate_hit = 1'b1;
        invalidate_way = WAY_WIDTH'(w);
      end
      if (valid_array[clean_set][w] && tag_array[clean_set][w] == clean_tag) begin
        clean_hit = 1'b1;
        clean_way = WAY_WIDTH'(w);
      end
    end
    for (integer w = 0; w < WAYS; w = w + 1)
      if (valid_array[write_set][w] && tag_array[write_set][w] == write_tag)
        write_way = WAY_WIDTH'(w);
    for (integer w = 0; w < WAYS; w = w + 1)
      if (valid_array[line_wr_addr[6 +: SET_WIDTH]][w] &&
          tag_array[line_wr_addr[6 +: SET_WIDTH]][w] ==
            line_wr_addr[6+SET_WIDTH +: TAG_WIDTH])
        line_wr_way = WAY_WIDTH'(w);
    if (!alloc_hit && !alloc_free_found)
      alloc_way = replacement_ptr[alloc_set];
    else if (alloc_hit) begin
      alloc_way = '0;
      for (integer w = 0; w < WAYS; w = w + 1)
        if (valid_array[alloc_set][w] && tag_array[alloc_set][w] == alloc_tag)
          alloc_way = WAY_WIDTH'(w);
    end else
      alloc_way = alloc_free_way;

    alloc_victim_valid = !alloc_hit && !alloc_free_found &&
                         valid_array[alloc_set][replacement_ptr[alloc_set]];
    alloc_victim_addr = alloc_victim_valid ?
      {tag_array[alloc_set][replacement_ptr[alloc_set]], alloc_set, 6'b0} : 32'b0;
    alloc_victim_dir_state = alloc_victim_valid ?
      dir_state_array[alloc_set][replacement_ptr[alloc_set]] : DIR_I;
    alloc_victim_sharers = alloc_victim_valid ?
      sharer_array[alloc_set][replacement_ptr[alloc_set]] : 2'b00;
    alloc_victim_owner_id = alloc_victim_valid ?
      owner_array[alloc_set][replacement_ptr[alloc_set]] : 1'b0;
    alloc_victim_dirty = alloc_victim_valid ?
      dirty_array[alloc_set][replacement_ptr[alloc_set]] : 1'b0;

    dir_write_ready = write_hit || write_free_found;
    entry_invalidate_ready = invalidate_hit;
    mark_clean_ready = clean_hit && !line_wr_pending_q;
    line_wr_ready = line_wr_pending_q ? 1'b1 : (line_wr_hit || line_wr_free_found);
    line_rd_ready = !line_rd_busy_q;
    line_data_valid = line_rd_busy_q;
    line_data_beat_idx = line_rd_beat_q;
    line_data = data_array[line_rd_set_q][line_rd_way_q][line_rd_beat_q];
    line_data_last = (line_rd_beat_q == 3'd7);
  end

  always_ff @(posedge clock) begin
    if (reset) begin
      line_rd_busy_q <= 1'b0;
      line_rd_set_q <= '0;
      line_rd_way_q <= '0;
      line_rd_beat_q <= '0;
      line_wr_pending_q <= 1'b0;
      line_wr_addr_q <= '0;
      line_wr_way_q <= '0;
      line_wr_dirty_q <= 1'b0;
      line_wr_expected_beat_q <= '0;
      protocol_error <= 1'b0;
      for (i = 0; i < SETS; i = i + 1) begin
        replacement_ptr[i] <= '0;
        for (j = 0; j < WAYS; j = j + 1) begin
          valid_array[i][j] <= 1'b0;
          tag_array[i][j] <= '0;
          dir_state_array[i][j] <= DIR_I;
          sharer_array[i][j] <= 2'b00;
          owner_array[i][j] <= 1'b0;
          dirty_array[i][j] <= 1'b0;
        end
      end
    end else begin
      if (dir_write_valid && dir_write_ready) begin
        if (((dir_write_state == DIR_I) &&
             ((dir_write_sharers != 2'b00) || dir_write_owner_id)) ||
            ((dir_write_state == DIR_S) &&
             ((dir_write_sharers == 2'b00) || dir_write_owner_id)) ||
            ((dir_write_state == DIR_U) && (dir_write_sharers != 2'b00))) begin
          protocol_error <= 1'b1;
        end else begin
          valid_array[write_set][write_way] <= 1'b1;
          tag_array[write_set][write_way] <= write_tag;
          dir_state_array[write_set][write_way] <= dir_write_state;
          sharer_array[write_set][write_way] <= dir_write_sharers;
          owner_array[write_set][write_way] <= dir_write_owner_id;
        end
      end

      if (entry_invalidate_valid && entry_invalidate_ready) begin
        if ((dir_state_array[invalidate_set][invalidate_way] != DIR_I) ||
            (sharer_array[invalidate_set][invalidate_way] != 2'b00) ||
            dirty_array[invalidate_set][invalidate_way]) begin
          protocol_error <= 1'b1;
        end else begin
          valid_array[invalidate_set][invalidate_way] <= 1'b0;
          dir_state_array[invalidate_set][invalidate_way] <= DIR_I;
          sharer_array[invalidate_set][invalidate_way] <= 2'b00;
          owner_array[invalidate_set][invalidate_way] <= 1'b0;
          dirty_array[invalidate_set][invalidate_way] <= 1'b0;
        end
      end

      if (mark_clean_valid && mark_clean_ready)
        dirty_array[clean_set][clean_way] <= 1'b0;

      if (line_wr_valid && line_wr_ready) begin
        if (!line_wr_pending_q) begin
          if (line_wr_beat_idx != 3'd0) begin
            protocol_error <= 1'b1;
          end else begin
            line_wr_addr_q <= {line_wr_addr[31:6], 6'b0};
            line_wr_way_q <= line_wr_hit ? line_wr_way :
                             line_wr_free_found ? line_wr_way : '0;
            line_wr_dirty_q <= line_wr_dirty;
            line_wr_expected_beat_q <= 3'd1;
            line_wr_pending_q <= 1'b1;
            if (!line_wr_hit && !line_wr_free_found)
              protocol_error <= 1'b1;
            else if (!line_wr_hit) begin
              valid_array[line_wr_addr[6 +: SET_WIDTH]][line_wr_way] <= 1'b1;
              tag_array[line_wr_addr[6 +: SET_WIDTH]][line_wr_way] <=
                line_wr_addr[6+SET_WIDTH +: TAG_WIDTH];
              dir_state_array[line_wr_addr[6 +: SET_WIDTH]][line_wr_way] <= DIR_I;
              sharer_array[line_wr_addr[6 +: SET_WIDTH]][line_wr_way] <= 2'b00;
              owner_array[line_wr_addr[6 +: SET_WIDTH]][line_wr_way] <= 1'b0;
              dirty_array[line_wr_addr[6 +: SET_WIDTH]][line_wr_way] <= 1'b0;
            end
          end
        end else if ((line_wr_addr[31:6] != line_wr_addr_q[31:6]) ||
                     (line_wr_beat_idx != line_wr_expected_beat_q)) begin
          protocol_error <= 1'b1;
        end else begin
          line_wr_expected_beat_q <= line_wr_expected_beat_q + 1'b1;
        end
        if ((line_wr_beat_idx != 3'd0 || !line_wr_pending_q) &&
            (line_wr_beat_idx == 3'd0 ? !line_wr_pending_q :
              ((line_wr_addr[31:6] == line_wr_addr_q[31:6]) &&
               (line_wr_beat_idx == line_wr_expected_beat_q)))) begin
          data_array[line_wr_addr[6 +: SET_WIDTH]]
                    [line_wr_pending_q ? line_wr_way_q : line_wr_way]
                    [line_wr_beat_idx] <= line_wr_data;
        end
        if (line_wr_last != (line_wr_beat_idx == 3'd7))
          protocol_error <= 1'b1;
        if (line_wr_last && line_wr_beat_idx == 3'd7) begin
          line_wr_pending_q <= 1'b0;
          dirty_array[line_wr_addr[6 +: SET_WIDTH]]
                     [line_wr_pending_q ? line_wr_way_q : line_wr_way] <=
            line_wr_pending_q ? line_wr_dirty_q : line_wr_dirty;
          replacement_ptr[line_wr_addr[6 +: SET_WIDTH]] <=
            (line_wr_pending_q ? line_wr_way_q : line_wr_way) + 1'b1;
        end
      end

      if (line_rd_valid && line_rd_ready) begin
        line_rd_busy_q <= line_rd_hit;
        line_rd_set_q <= rd_set;
        line_rd_beat_q <= '0;
        for (j = 0; j < WAYS; j = j + 1)
          if (valid_array[rd_set][j] && tag_array[rd_set][j] == rd_tag)
            line_rd_way_q <= WAY_WIDTH'(j);
      end else if (line_data_valid && line_data_ready) begin
        if (line_rd_beat_q == 3'd7) begin
          line_rd_busy_q <= 1'b0;
          line_rd_beat_q <= '0;
        end else begin
          line_rd_beat_q <= line_rd_beat_q + 1'b1;
        end
      end
    end
  end
endmodule
