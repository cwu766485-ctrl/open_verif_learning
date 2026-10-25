// Picker-friendly packed/scalar wrapper around the standalone AXI4 line
// adapter. This DUT boundary exposes the real five AXI channels to Python.
module LineMemoryAxi4PythonWrapper (
  input logic clock,
  input logic reset,

  input logic line_rd_req_valid,
  output logic line_rd_req_ready,
  input logic [31:0] line_rd_req_addr,
  input logic [3:0] line_rd_req_id,
  output logic line_rd_data_valid,
  input logic line_rd_data_ready,
  output logic [3:0] line_rd_data_id,
  output logic [2:0] line_rd_data_beat,
  output logic [63:0] line_rd_data,
  output logic line_rd_data_last,
  output logic line_rd_data_error,

  input logic line_wr_req_valid,
  output logic line_wr_req_ready,
  input logic [31:0] line_wr_req_addr,
  input logic [3:0] line_wr_req_id,
  input logic line_wr_data_valid,
  output logic line_wr_data_ready,
  input logic [3:0] line_wr_data_id,
  input logic [2:0] line_wr_data_beat,
  input logic [63:0] line_wr_data,
  input logic line_wr_data_last,
  output logic line_wr_rsp_valid,
  input logic line_wr_rsp_ready,
  output logic [3:0] line_wr_rsp_id,
  output logic line_wr_rsp_error,
  output logic protocol_error,

  output logic [3:0] axi_arid,
  output logic [31:0] axi_araddr,
  output logic [7:0] axi_arlen,
  output logic [2:0] axi_arsize,
  output logic [1:0] axi_arburst,
  output logic axi_arlock,
  output logic [3:0] axi_arcache,
  output logic [2:0] axi_arprot,
  output logic axi_arvalid,
  input logic axi_arready,
  input logic [3:0] axi_rid,
  input logic [63:0] axi_rdata,
  input logic [1:0] axi_rresp,
  input logic axi_rlast,
  input logic axi_rvalid,
  output logic axi_rready,

  output logic [3:0] axi_awid,
  output logic [31:0] axi_awaddr,
  output logic [7:0] axi_awlen,
  output logic [2:0] axi_awsize,
  output logic [1:0] axi_awburst,
  output logic axi_awlock,
  output logic [3:0] axi_awcache,
  output logic [2:0] axi_awprot,
  output logic axi_awvalid,
  input logic axi_awready,
  output logic [63:0] axi_wdata,
  output logic [7:0] axi_wstrb,
  output logic axi_wlast,
  output logic axi_wvalid,
  input logic axi_wready,
  input logic [3:0] axi_bid,
  input logic [1:0] axi_bresp,
  input logic axi_bvalid,
  output logic axi_bready,

  output logic mon_ar_fire,
  output logic [3:0] mon_ar_id,
  output logic [31:0] mon_ar_addr,
  output logic mon_aw_fire,
  output logic [3:0] mon_aw_id,
  output logic [31:0] mon_aw_addr,
  output logic mon_w_fire,
  output logic [63:0] mon_w_data,
  output logic [7:0] mon_w_strb,
  output logic mon_w_last,
  output logic mon_r_fire,
  output logic [3:0] mon_r_id,
  output logic [63:0] mon_r_data,
  output logic mon_r_last,
  output logic mon_b_fire,
  output logic [3:0] mon_b_id,
  output logic mon_line_rd_fire,
  output logic [3:0] mon_line_rd_id,
  output logic [2:0] mon_line_rd_beat,
  output logic [63:0] mon_line_rd_data,
  output logic mon_line_rd_last,
  output logic mon_line_rd_error,
  output logic mon_line_wr_rsp_fire,
  output logic [3:0] mon_line_wr_rsp_id,
  output logic mon_line_wr_rsp_error,
  output logic mon_ar_stall,
  output logic mon_aw_stall,
  output logic mon_w_stall,
  output logic mon_r_stall,
  output logic mon_b_stall,
  output logic mon_stability_error
);
  logic ar_stalled_q, aw_stalled_q, w_stalled_q;
  logic [56:0] ar_payload_q, aw_payload_q;
  logic [72:0] w_payload_q;

  LineMemoryAxi4Adapter #(.ID_WIDTH(4), .MAX_OUTSTANDING(4)) dut (.*);

  always_ff @(posedge clock) begin
    if (reset) begin
      ar_stalled_q <= 1'b0;
      aw_stalled_q <= 1'b0;
      w_stalled_q <= 1'b0;
      ar_payload_q <= '0;
      aw_payload_q <= '0;
      w_payload_q <= '0;
      mon_ar_stall <= 1'b0;
      mon_aw_stall <= 1'b0;
      mon_w_stall <= 1'b0;
      mon_r_stall <= 1'b0;
      mon_b_stall <= 1'b0;
      mon_stability_error <= 1'b0;
    end else begin
      mon_ar_stall <= axi_arvalid && !axi_arready;
      mon_aw_stall <= axi_awvalid && !axi_awready;
      mon_w_stall <= axi_wvalid && !axi_wready;
      mon_r_stall <= axi_rvalid && !axi_rready;
      mon_b_stall <= axi_bvalid && !axi_bready;
      if (ar_stalled_q && (!axi_arvalid ||
          {axi_arid, axi_araddr, axi_arlen, axi_arsize, axi_arburst,
           axi_arlock, axi_arcache, axi_arprot} != ar_payload_q))
        mon_stability_error <= 1'b1;
      if (aw_stalled_q && (!axi_awvalid ||
          {axi_awid, axi_awaddr, axi_awlen, axi_awsize, axi_awburst,
           axi_awlock, axi_awcache, axi_awprot} != aw_payload_q))
        mon_stability_error <= 1'b1;
      if (w_stalled_q && (!axi_wvalid ||
          {axi_wdata, axi_wstrb, axi_wlast} != w_payload_q))
        mon_stability_error <= 1'b1;
      ar_stalled_q <= axi_arvalid && !axi_arready;
      aw_stalled_q <= axi_awvalid && !axi_awready;
      w_stalled_q <= axi_wvalid && !axi_wready;
      if (axi_arvalid && !axi_arready)
        ar_payload_q <= {axi_arid, axi_araddr, axi_arlen, axi_arsize,
                         axi_arburst, axi_arlock, axi_arcache, axi_arprot};
      if (axi_awvalid && !axi_awready)
        aw_payload_q <= {axi_awid, axi_awaddr, axi_awlen, axi_awsize,
                         axi_awburst, axi_awlock, axi_awcache, axi_awprot};
      if (axi_wvalid && !axi_wready)
        w_payload_q <= {axi_wdata, axi_wstrb, axi_wlast};
    end

    mon_ar_fire <= !reset && axi_arvalid && axi_arready;
    mon_ar_id <= axi_arid;
    mon_ar_addr <= axi_araddr;
    mon_aw_fire <= !reset && axi_awvalid && axi_awready;
    mon_aw_id <= axi_awid;
    mon_aw_addr <= axi_awaddr;
    mon_w_fire <= !reset && axi_wvalid && axi_wready;
    mon_w_data <= axi_wdata;
    mon_w_strb <= axi_wstrb;
    mon_w_last <= axi_wlast;
    mon_r_fire <= !reset && axi_rvalid && axi_rready;
    mon_r_id <= axi_rid;
    mon_r_data <= axi_rdata;
    mon_r_last <= axi_rlast;
    mon_b_fire <= !reset && axi_bvalid && axi_bready;
    mon_b_id <= axi_bid;
    mon_line_rd_fire <= !reset && line_rd_data_valid && line_rd_data_ready;
    mon_line_rd_id <= line_rd_data_id;
    mon_line_rd_beat <= line_rd_data_beat;
    mon_line_rd_data <= line_rd_data;
    mon_line_rd_last <= line_rd_data_last;
    mon_line_rd_error <= line_rd_data_error;
    mon_line_wr_rsp_fire <= !reset && line_wr_rsp_valid && line_wr_rsp_ready;
    mon_line_wr_rsp_id <= line_wr_rsp_id;
    mon_line_wr_rsp_error <= line_wr_rsp_error;
  end
endmodule
