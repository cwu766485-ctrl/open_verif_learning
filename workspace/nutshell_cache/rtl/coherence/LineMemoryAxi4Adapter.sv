// Converts line-oriented memory requests into AXI4 64-bit INCR bursts.
// Up to MAX_OUTSTANDING reads and writes may be active independently. AXI IDs
// are preserved and must be unique among active transactions on each path.
// Read beats are routed by RID (including interleaved bursts); AXI4 write
// data has no ID, so W bursts are emitted in AW acceptance order.
module LineMemoryAxi4Adapter #(
  parameter int ID_WIDTH = coherence_protocol_pkg::TXN_ID_WIDTH,
  parameter int MAX_OUTSTANDING = 4
) (
  input logic clock,
  input logic reset,

  input  logic line_rd_req_valid,
  output logic line_rd_req_ready,
  input  logic [31:0] line_rd_req_addr,
  input  logic [ID_WIDTH-1:0] line_rd_req_id,
  output logic line_rd_data_valid,
  input  logic line_rd_data_ready,
  output logic [ID_WIDTH-1:0] line_rd_data_id,
  output logic [2:0] line_rd_data_beat,
  output logic [63:0] line_rd_data,
  output logic line_rd_data_last,
  output logic line_rd_data_error,

  input  logic line_wr_req_valid,
  output logic line_wr_req_ready,
  input  logic [31:0] line_wr_req_addr,
  input  logic [ID_WIDTH-1:0] line_wr_req_id,
  input  logic line_wr_data_valid,
  output logic line_wr_data_ready,
  input  logic [ID_WIDTH-1:0] line_wr_data_id,
  input  logic [2:0] line_wr_data_beat,
  input  logic [63:0] line_wr_data,
  input  logic line_wr_data_last,
  output logic line_wr_rsp_valid,
  input  logic line_wr_rsp_ready,
  output logic [ID_WIDTH-1:0] line_wr_rsp_id,
  output logic line_wr_rsp_error,
  output logic protocol_error,

  output logic [ID_WIDTH-1:0] axi_arid,
  output logic [31:0] axi_araddr,
  output logic [7:0] axi_arlen,
  output logic [2:0] axi_arsize,
  output logic [1:0] axi_arburst,
  output logic axi_arlock,
  output logic [3:0] axi_arcache,
  output logic [2:0] axi_arprot,
  output logic axi_arvalid,
  input  logic axi_arready,
  input  logic [ID_WIDTH-1:0] axi_rid,
  input  logic [63:0] axi_rdata,
  input  logic [1:0] axi_rresp,
  input  logic axi_rlast,
  input  logic axi_rvalid,
  output logic axi_rready,

  output logic [ID_WIDTH-1:0] axi_awid,
  output logic [31:0] axi_awaddr,
  output logic [7:0] axi_awlen,
  output logic [2:0] axi_awsize,
  output logic [1:0] axi_awburst,
  output logic axi_awlock,
  output logic [3:0] axi_awcache,
  output logic [2:0] axi_awprot,
  output logic axi_awvalid,
  input  logic axi_awready,
  output logic [63:0] axi_wdata,
  output logic [7:0] axi_wstrb,
  output logic axi_wlast,
  output logic axi_wvalid,
  input  logic axi_wready,
  input  logic [ID_WIDTH-1:0] axi_bid,
  input  logic [1:0] axi_bresp,
  input  logic axi_bvalid,
  output logic axi_bready
);
  localparam logic [1:0] AXI_RESP_OKAY = 2'b00;
  localparam int SLOT_W = (MAX_OUTSTANDING < 2) ? 1 : $clog2(MAX_OUTSTANDING);
  localparam int COUNT_W = $clog2(MAX_OUTSTANDING + 1);

  logic rd_valid_q [0:MAX_OUTSTANDING-1];
  logic rd_issued_q [0:MAX_OUTSTANDING-1];
  logic rd_drain_q [0:MAX_OUTSTANDING-1];
  logic [ID_WIDTH-1:0] rd_id_q [0:MAX_OUTSTANDING-1];
  logic [31:0] rd_addr_q [0:MAX_OUTSTANDING-1];
  logic [2:0] rd_beat_q [0:MAX_OUTSTANDING-1];
  logic [SLOT_W-1:0] rd_ar_fifo_q [0:MAX_OUTSTANDING-1];
  logic [SLOT_W-1:0] rd_ar_head_q, rd_ar_tail_q;
  logic [COUNT_W-1:0] rd_ar_count_q;
  logic rd_free_found, rd_id_in_use, rd_req_fire;
  logic [SLOT_W-1:0] rd_free_slot, rd_ar_slot;
  logic rd_ar_fire, rd_match_found, rd_drain_match;
  logic [SLOT_W-1:0] rd_match_slot;
  logic rd_r_fire, rd_r_expected_last, rd_r_malformed, rd_r_error;

  logic wr_valid_q [0:MAX_OUTSTANDING-1];
  logic wr_aw_sent_q [0:MAX_OUTSTANDING-1];
  logic wr_w_done_q [0:MAX_OUTSTANDING-1];
  logic [ID_WIDTH-1:0] wr_id_q [0:MAX_OUTSTANDING-1];
  logic [31:0] wr_addr_q [0:MAX_OUTSTANDING-1];
  logic [63:0] wr_data_q [0:MAX_OUTSTANDING-1][0:7];
  logic [3:0] wr_data_count_q [0:MAX_OUTSTANDING-1];
  logic [3:0] wr_w_sent_count_q [0:MAX_OUTSTANDING-1];
  logic [SLOT_W-1:0] wr_aw_fifo_q [0:MAX_OUTSTANDING-1];
  logic [SLOT_W-1:0] wr_w_fifo_q [0:MAX_OUTSTANDING-1];
  logic [SLOT_W-1:0] wr_aw_head_q, wr_aw_tail_q;
  logic [SLOT_W-1:0] wr_w_head_q, wr_w_tail_q;
  logic [COUNT_W-1:0] wr_aw_count_q, wr_w_count_q;
  logic wr_free_found, wr_id_in_use, wr_req_fire;
  logic [SLOT_W-1:0] wr_free_slot, wr_aw_slot, wr_w_slot;
  logic wr_aw_fire, wr_w_fire, wr_w_pop, wr_rsp_fire;
  logic wr_data_match_found, wr_rsp_match_found;
  logic [SLOT_W-1:0] wr_data_match_slot, wr_rsp_match_slot;
  logic wr_data_fire;

  always_comb begin : request_slot_search
    rd_free_found = 1'b0;
    rd_id_in_use = 1'b0;
    rd_free_slot = '0;
    wr_free_found = 1'b0;
    wr_id_in_use = 1'b0;
    wr_free_slot = '0;
    rd_match_found = 1'b0;
    rd_match_slot = '0;
    rd_drain_match = 1'b0;
    wr_data_match_found = 1'b0;
    wr_data_match_slot = '0;
    wr_rsp_match_found = 1'b0;
    wr_rsp_match_slot = '0;

    for (integer i = 0; i < MAX_OUTSTANDING; i = i + 1) begin
      if (!rd_valid_q[i] && !rd_free_found) begin
        rd_free_found = 1'b1;
        rd_free_slot = SLOT_W'(i);
      end
      if (rd_valid_q[i] && (rd_id_q[i] == line_rd_req_id))
        rd_id_in_use = 1'b1;
      if (rd_valid_q[i] && rd_issued_q[i] && (rd_id_q[i] == axi_rid)) begin
        rd_match_found = 1'b1;
        rd_match_slot = SLOT_W'(i);
        rd_drain_match = rd_drain_q[i];
      end

      if (!wr_valid_q[i] && !wr_free_found) begin
        wr_free_found = 1'b1;
        wr_free_slot = SLOT_W'(i);
      end
      if (wr_valid_q[i] && (wr_id_q[i] == line_wr_req_id))
        wr_id_in_use = 1'b1;
      if (wr_valid_q[i] && (wr_id_q[i] == line_wr_data_id)) begin
        wr_data_match_found = 1'b1;
        wr_data_match_slot = SLOT_W'(i);
      end
      if (wr_valid_q[i] && (wr_id_q[i] == axi_bid)) begin
        wr_rsp_match_found = 1'b1;
        wr_rsp_match_slot = SLOT_W'(i);
      end
    end
  end

  assign line_rd_req_ready = !reset && rd_free_found && !rd_id_in_use;
  assign rd_req_fire = line_rd_req_valid && line_rd_req_ready;
  assign rd_ar_slot = rd_ar_fifo_q[rd_ar_head_q];
  assign axi_arid = rd_id_q[rd_ar_slot];
  assign axi_araddr = {rd_addr_q[rd_ar_slot][31:6], 6'b0};
  assign axi_arlen = 8'd7;
  assign axi_arsize = 3'b011;
  assign axi_arburst = 2'b01;
  assign axi_arlock = 1'b0;
  assign axi_arcache = 4'b0011;
  assign axi_arprot = 3'b000;
  assign axi_arvalid = !reset && (rd_ar_count_q != 0);
  assign rd_ar_fire = axi_arvalid && axi_arready;

  assign rd_r_expected_last = rd_match_found &&
                              (rd_beat_q[rd_match_slot] == 3'd7);
  assign rd_r_malformed = rd_match_found && !rd_drain_match &&
                          (axi_rlast != rd_r_expected_last);
  assign rd_r_error = rd_match_found && !rd_drain_match &&
                      ((axi_rresp != AXI_RESP_OKAY) || rd_r_malformed);
  assign line_rd_data_valid = !reset && axi_rvalid && rd_match_found &&
                              !rd_drain_match;
  assign line_rd_data_id = rd_match_found ? rd_id_q[rd_match_slot] : axi_rid;
  assign line_rd_data_beat = rd_match_found ? rd_beat_q[rd_match_slot] : 3'b0;
  assign line_rd_data = axi_rdata;
  // Malformed RLAST and RRESP errors terminate the line beat stream, then an
  // early/late AXI burst is drained internally through its actual RLAST.
  assign line_rd_data_last = rd_r_error || rd_r_expected_last;
  assign line_rd_data_error = line_rd_data_valid && rd_r_error;
  assign axi_rready = !reset &&
                      (!rd_match_found || rd_drain_match || line_rd_data_ready);
  assign rd_r_fire = axi_rvalid && axi_rready;

  assign line_wr_req_ready = !reset && wr_free_found && !wr_id_in_use;
  assign wr_req_fire = line_wr_req_valid && line_wr_req_ready;
  assign wr_aw_slot = wr_aw_fifo_q[wr_aw_head_q];
  assign axi_awid = wr_id_q[wr_aw_slot];
  assign axi_awaddr = {wr_addr_q[wr_aw_slot][31:6], 6'b0};
  assign axi_awlen = 8'd7;
  assign axi_awsize = 3'b011;
  assign axi_awburst = 2'b01;
  assign axi_awlock = 1'b0;
  assign axi_awcache = 4'b0011;
  assign axi_awprot = 3'b000;
  assign axi_awvalid = !reset && (wr_aw_count_q != 0);
  assign wr_aw_fire = axi_awvalid && axi_awready;

  // Buffer data by line transaction ID. The AXI4 W channel has no WID, so
  // buffered bursts are serialized in the same order as their AW handshakes.
  assign line_wr_data_ready = !reset &&
    (!wr_data_match_found || (wr_data_count_q[wr_data_match_slot] < 4'd8));
  assign wr_data_fire = line_wr_data_valid && line_wr_data_ready;
  assign wr_w_slot = wr_w_fifo_q[wr_w_head_q];
  assign axi_wdata = wr_data_q[wr_w_slot][wr_w_sent_count_q[wr_w_slot][2:0]];
  assign axi_wstrb = 8'hff;
  assign axi_wlast = (wr_w_sent_count_q[wr_w_slot] == 4'd7);
  assign axi_wvalid = !reset && (wr_w_count_q != 0) &&
                      wr_aw_sent_q[wr_w_slot] &&
                      (wr_data_count_q[wr_w_slot] == 4'd8) &&
                      (wr_w_sent_count_q[wr_w_slot] < 4'd8);
  assign wr_w_fire = axi_wvalid && axi_wready;
  assign wr_w_pop = wr_w_fire && axi_wlast;

  assign line_wr_rsp_valid = !reset && axi_bvalid && wr_rsp_match_found &&
                             wr_w_done_q[wr_rsp_match_slot];
  assign line_wr_rsp_id = wr_rsp_match_found ? wr_id_q[wr_rsp_match_slot] : axi_bid;
  assign line_wr_rsp_error = wr_rsp_match_found &&
                             (axi_bresp != AXI_RESP_OKAY);
  assign axi_bready = !reset &&
    (!wr_rsp_match_found || wr_w_done_q[wr_rsp_match_slot] &&
     line_wr_rsp_ready);
  assign wr_rsp_fire = axi_bvalid && axi_bready && wr_rsp_match_found;

  always_ff @(posedge clock) begin : outstanding_tracker
    if (reset) begin
      rd_ar_head_q <= '0;
      rd_ar_tail_q <= '0;
      rd_ar_count_q <= '0;
      wr_aw_head_q <= '0;
      wr_aw_tail_q <= '0;
      wr_aw_count_q <= '0;
      wr_w_head_q <= '0;
      wr_w_tail_q <= '0;
      wr_w_count_q <= '0;
      protocol_error <= 1'b0;
      for (integer i = 0; i < MAX_OUTSTANDING; i = i + 1) begin
        rd_valid_q[i] <= 1'b0;
        rd_issued_q[i] <= 1'b0;
        rd_drain_q[i] <= 1'b0;
        rd_id_q[i] <= '0;
        rd_addr_q[i] <= '0;
        rd_beat_q[i] <= '0;
        rd_ar_fifo_q[i] <= '0;
        wr_valid_q[i] <= 1'b0;
        wr_aw_sent_q[i] <= 1'b0;
        wr_w_done_q[i] <= 1'b0;
        wr_id_q[i] <= '0;
        wr_addr_q[i] <= '0;
        wr_data_count_q[i] <= '0;
        wr_w_sent_count_q[i] <= '0;
        wr_aw_fifo_q[i] <= '0;
        wr_w_fifo_q[i] <= '0;
        for (integer b = 0; b < 8; b = b + 1)
          wr_data_q[i][b] <= '0;
      end
    end else begin
      if ((axi_rvalid && !rd_match_found) ||
          (axi_bvalid && !wr_rsp_match_found) ||
          (axi_bvalid && wr_rsp_match_found &&
           !wr_w_done_q[wr_rsp_match_slot]) ||
          (line_wr_data_valid && !wr_data_match_found))
        protocol_error <= 1'b1;

      if (rd_req_fire) begin
        rd_valid_q[rd_free_slot] <= 1'b1;
        rd_issued_q[rd_free_slot] <= 1'b0;
        rd_drain_q[rd_free_slot] <= 1'b0;
        rd_id_q[rd_free_slot] <= line_rd_req_id;
        rd_addr_q[rd_free_slot] <= line_rd_req_addr;
        rd_beat_q[rd_free_slot] <= '0;
        rd_ar_fifo_q[rd_ar_tail_q] <= rd_free_slot;
        if (rd_ar_tail_q == SLOT_W'(MAX_OUTSTANDING-1))
          rd_ar_tail_q <= '0;
        else
          rd_ar_tail_q <= rd_ar_tail_q + 1'b1;
      end
      if (rd_ar_fire) begin
        rd_issued_q[rd_ar_slot] <= 1'b1;
        if (rd_ar_head_q == SLOT_W'(MAX_OUTSTANDING-1))
          rd_ar_head_q <= '0;
        else
          rd_ar_head_q <= rd_ar_head_q + 1'b1;
      end
      case ({rd_req_fire, rd_ar_fire})
        2'b10: rd_ar_count_q <= rd_ar_count_q + 1'b1;
        2'b01: rd_ar_count_q <= rd_ar_count_q - 1'b1;
        default: ;
      endcase

      if (rd_r_fire && rd_match_found) begin
        if (rd_drain_match) begin
          if (axi_rlast) begin
            rd_valid_q[rd_match_slot] <= 1'b0;
            rd_issued_q[rd_match_slot] <= 1'b0;
            rd_drain_q[rd_match_slot] <= 1'b0;
            rd_beat_q[rd_match_slot] <= '0;
          end
        end else begin
          if (rd_r_malformed)
            protocol_error <= 1'b1;
          if (rd_r_error) begin
            if (axi_rlast) begin
              rd_valid_q[rd_match_slot] <= 1'b0;
              rd_issued_q[rd_match_slot] <= 1'b0;
              rd_beat_q[rd_match_slot] <= '0;
            end else begin
              rd_drain_q[rd_match_slot] <= 1'b1;
            end
          end else if (axi_rlast) begin
            rd_valid_q[rd_match_slot] <= 1'b0;
            rd_issued_q[rd_match_slot] <= 1'b0;
            rd_beat_q[rd_match_slot] <= '0;
          end else begin
            rd_beat_q[rd_match_slot] <= rd_beat_q[rd_match_slot] + 1'b1;
          end
        end
      end

      if (wr_req_fire) begin
        wr_valid_q[wr_free_slot] <= 1'b1;
        wr_aw_sent_q[wr_free_slot] <= 1'b0;
        wr_w_done_q[wr_free_slot] <= 1'b0;
        wr_id_q[wr_free_slot] <= line_wr_req_id;
        wr_addr_q[wr_free_slot] <= line_wr_req_addr;
        wr_data_count_q[wr_free_slot] <= '0;
        wr_w_sent_count_q[wr_free_slot] <= '0;
        wr_aw_fifo_q[wr_aw_tail_q] <= wr_free_slot;
        wr_w_fifo_q[wr_w_tail_q] <= wr_free_slot;
        if (wr_aw_tail_q == SLOT_W'(MAX_OUTSTANDING-1))
          wr_aw_tail_q <= '0;
        else
          wr_aw_tail_q <= wr_aw_tail_q + 1'b1;
        if (wr_w_tail_q == SLOT_W'(MAX_OUTSTANDING-1))
          wr_w_tail_q <= '0;
        else
          wr_w_tail_q <= wr_w_tail_q + 1'b1;
      end
      if (wr_aw_fire) begin
        wr_aw_sent_q[wr_aw_slot] <= 1'b1;
        if (wr_aw_head_q == SLOT_W'(MAX_OUTSTANDING-1))
          wr_aw_head_q <= '0;
        else
          wr_aw_head_q <= wr_aw_head_q + 1'b1;
      end
      case ({wr_req_fire, wr_aw_fire})
        2'b10: wr_aw_count_q <= wr_aw_count_q + 1'b1;
        2'b01: wr_aw_count_q <= wr_aw_count_q - 1'b1;
        default: ;
      endcase

      if (wr_data_fire) begin
        if (wr_data_match_found) begin
          if ((line_wr_data_beat != wr_data_count_q[wr_data_match_slot][2:0]) ||
              (line_wr_data_last !=
               (wr_data_count_q[wr_data_match_slot] == 4'd7)))
            protocol_error <= 1'b1;
          if (wr_data_count_q[wr_data_match_slot] < 4'd8) begin
            wr_data_q[wr_data_match_slot]
                     [wr_data_count_q[wr_data_match_slot][2:0]] <= line_wr_data;
            wr_data_count_q[wr_data_match_slot] <=
              wr_data_count_q[wr_data_match_slot] + 1'b1;
          end
        end
      end
      if (wr_w_fire) begin
        wr_w_sent_count_q[wr_w_slot] <= wr_w_sent_count_q[wr_w_slot] + 1'b1;
        if (axi_wlast) begin
          wr_w_done_q[wr_w_slot] <= 1'b1;
          if (wr_w_head_q == SLOT_W'(MAX_OUTSTANDING-1))
            wr_w_head_q <= '0;
          else
            wr_w_head_q <= wr_w_head_q + 1'b1;
        end
      end
      case ({wr_req_fire, wr_w_pop})
        2'b10: wr_w_count_q <= wr_w_count_q + 1'b1;
        2'b01: wr_w_count_q <= wr_w_count_q - 1'b1;
        default: ;
      endcase

      if (wr_rsp_fire) begin
        wr_valid_q[wr_rsp_match_slot] <= 1'b0;
        wr_aw_sent_q[wr_rsp_match_slot] <= 1'b0;
        wr_w_done_q[wr_rsp_match_slot] <= 1'b0;
        wr_data_count_q[wr_rsp_match_slot] <= '0;
        wr_w_sent_count_q[wr_rsp_match_slot] <= '0;
      end
    end
  end
endmodule
