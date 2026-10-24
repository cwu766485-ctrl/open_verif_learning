// Adapts the subsystem's 64-byte, eight-beat line-memory contract to a
// 64-bit AXI4 INCR burst. The current Directory is blocking, so the adapter
// accepts at most one read and one write transaction at a time. Read and
// write paths are independent and AXI IDs are preserved end to end.
module LineMemoryAxi4Adapter #(
  parameter int ID_WIDTH = coherence_protocol_pkg::TXN_ID_WIDTH
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

  logic rd_active_q;
  logic rd_drain_q;
  logic [ID_WIDTH-1:0] rd_id_q;
  logic [2:0] rd_beat_q;
  logic rd_fire;
  logic rd_id_error;
  logic rd_response_error;

  logic wr_active_q;
  logic wr_last_seen_q;
  logic [ID_WIDTH-1:0] wr_id_q;
  logic [2:0] wr_beat_q;
  logic wr_fire;
  logic b_fire;

  assign axi_arid = line_rd_req_id;
  assign axi_araddr = {line_rd_req_addr[31:6], 6'b0};
  assign axi_arlen = 8'd7;
  assign axi_arsize = 3'b011;
  assign axi_arburst = 2'b01;
  assign axi_arlock = 1'b0;
  assign axi_arcache = 4'b0011;
  assign axi_arprot = 3'b000;
  assign axi_arvalid = !reset && line_rd_req_valid && !rd_active_q;
  assign line_rd_req_ready = !reset && !rd_active_q && axi_arready;

  assign rd_id_error = (axi_rid != rd_id_q);
  assign rd_response_error = (axi_rresp != AXI_RESP_OKAY) || rd_id_error;
  assign line_rd_data_valid = !reset && rd_active_q && !rd_drain_q &&
                              axi_rvalid;
  assign line_rd_data_id = axi_rid;
  assign line_rd_data_beat = rd_beat_q;
  assign line_rd_data = axi_rdata;
  // A failed AXI beat terminates the cache line response immediately. Any
  // remaining AXI beats are drained internally through RREADY.
  assign line_rd_data_last = rd_response_error ? 1'b1 : axi_rlast;
  assign line_rd_data_error = rd_response_error;
  assign axi_rready = !reset && rd_active_q &&
                      (rd_drain_q || line_rd_data_ready);
  assign rd_fire = axi_rvalid && axi_rready;

  assign axi_awid = line_wr_req_id;
  assign axi_awaddr = {line_wr_req_addr[31:6], 6'b0};
  assign axi_awlen = 8'd7;
  assign axi_awsize = 3'b011;
  assign axi_awburst = 2'b01;
  assign axi_awlock = 1'b0;
  assign axi_awcache = 4'b0011;
  assign axi_awprot = 3'b000;
  assign axi_awvalid = !reset && line_wr_req_valid && !wr_active_q;
  assign line_wr_req_ready = !reset && !wr_active_q && axi_awready;

  assign axi_wdata = line_wr_data;
  assign axi_wstrb = 8'hff;
  // WLAST follows the accepted eight-beat line position. The input marker is
  // checked below so a malformed producer cannot corrupt the AXI burst.
  assign axi_wlast = (wr_beat_q == 3'd7);
  assign axi_wvalid = !reset && wr_active_q && !wr_last_seen_q &&
                      line_wr_data_valid;
  assign line_wr_data_ready = !reset && wr_active_q && !wr_last_seen_q &&
                              axi_wready;
  assign wr_fire = axi_wvalid && axi_wready;

  assign line_wr_rsp_valid = !reset && axi_bvalid && wr_active_q &&
                             wr_last_seen_q;
  assign line_wr_rsp_id = axi_bid;
  assign line_wr_rsp_error = (axi_bresp != AXI_RESP_OKAY) ||
                             (axi_bid != wr_id_q);
  assign axi_bready = !reset && wr_active_q && wr_last_seen_q &&
                      line_wr_rsp_ready;
  assign b_fire = axi_bvalid && axi_bready;

  always_ff @(posedge clock) begin
    if (reset) begin
      rd_active_q <= 1'b0;
      rd_drain_q <= 1'b0;
      rd_id_q <= '0;
      rd_beat_q <= '0;
      wr_active_q <= 1'b0;
      wr_last_seen_q <= 1'b0;
      wr_id_q <= '0;
      wr_beat_q <= '0;
      protocol_error <= 1'b0;
    end else begin
      if ((axi_rvalid && !rd_active_q &&
           !(axi_arvalid && axi_arready)) ||
          (axi_bvalid && !wr_active_q &&
           !(axi_awvalid && axi_awready)) ||
          (axi_bvalid && wr_active_q && !wr_last_seen_q))
        protocol_error <= 1'b1;

      if (axi_arvalid && axi_arready) begin
        rd_active_q <= 1'b1;
        rd_drain_q <= 1'b0;
        rd_id_q <= line_rd_req_id;
        rd_beat_q <= '0;
      end

      if (rd_fire) begin
        if (rd_drain_q) begin
          if (axi_rlast) begin
            rd_active_q <= 1'b0;
            rd_drain_q <= 1'b0;
          end
        end else begin
          if (rd_id_error)
            protocol_error <= 1'b1;
          if (axi_rlast != (rd_beat_q == 3'd7))
            protocol_error <= 1'b1;
          if (rd_response_error) begin
            if (axi_rlast) begin
              rd_active_q <= 1'b0;
            end else begin
              rd_drain_q <= 1'b1;
            end
          end else if (axi_rlast) begin
            rd_active_q <= 1'b0;
          end else if (rd_beat_q == 3'd7) begin
            // Missing RLAST: report the malformed line response upstream and
            // keep draining until the AXI transaction finally terminates.
            protocol_error <= 1'b1;
            rd_drain_q <= 1'b1;
          end else begin
            rd_beat_q <= rd_beat_q + 1'b1;
          end
        end
      end

      if (axi_awvalid && axi_awready) begin
        wr_active_q <= 1'b1;
        wr_last_seen_q <= 1'b0;
        wr_id_q <= line_wr_req_id;
        wr_beat_q <= '0;
      end

      if (wr_fire) begin
        if ((line_wr_data_id != wr_id_q) ||
            (line_wr_data_beat != wr_beat_q) ||
            (line_wr_data_last != (wr_beat_q == 3'd7)))
          protocol_error <= 1'b1;
        if (wr_beat_q == 3'd7) begin
          wr_last_seen_q <= 1'b1;
        end else begin
          wr_beat_q <= wr_beat_q + 1'b1;
        end
      end

      if (b_fire) begin
        if (axi_bid != wr_id_q)
          protocol_error <= 1'b1;
        wr_active_q <= 1'b0;
        wr_last_seen_q <= 1'b0;
      end
    end
  end
endmodule
