module ReviewAxiAwFormal(
input logic  clock,
input logic  line_rd_req_valid,
input logic [31:0] line_rd_req_addr,
input logic [4-1:0] line_rd_req_id,
input logic  line_rd_data_ready,
input logic  line_wr_req_valid,
input logic [31:0] line_wr_req_addr,
input logic [4-1:0] line_wr_req_id,
input logic  line_wr_data_valid,
input logic [4-1:0] line_wr_data_id,
input logic [2:0] line_wr_data_beat,
input logic [63:0] line_wr_data,
input logic  line_wr_data_last,
input logic  line_wr_rsp_ready,
input logic  axi_arready,
input logic [4-1:0] axi_rid,
input logic [63:0] axi_rdata,
input logic [1:0] axi_rresp,
input logic  axi_rlast,
input logic  axi_rvalid,
input logic  axi_awready,
input logic  axi_wready,
input logic [4-1:0] axi_bid,
input logic [1:0] axi_bresp,
input logic  axi_bvalid,
input logic reset_later
);
logic  line_rd_req_ready;
logic  line_rd_data_valid;
logic [4-1:0] line_rd_data_id;
logic [2:0] line_rd_data_beat;
logic [63:0] line_rd_data;
logic  line_rd_data_last;
logic  line_rd_data_error;
logic  line_wr_req_ready;
logic  line_wr_data_ready;
logic  line_wr_rsp_valid;
logic [4-1:0] line_wr_rsp_id;
logic  line_wr_rsp_error;
logic  protocol_error;
logic [4-1:0] axi_arid;
logic [31:0] axi_araddr;
logic [7:0] axi_arlen;
logic [2:0] axi_arsize;
logic [1:0] axi_arburst;
logic  axi_arlock;
logic [3:0] axi_arcache;
logic [2:0] axi_arprot;
logic  axi_arvalid;
logic  axi_rready;
logic [4-1:0] axi_awid;
logic [31:0] axi_awaddr;
logic [7:0] axi_awlen;
logic [2:0] axi_awsize;
logic [1:0] axi_awburst;
logic  axi_awlock;
logic [3:0] axi_awcache;
logic [2:0] axi_awprot;
logic  axi_awvalid;
logic [63:0] axi_wdata;
logic [7:0] axi_wstrb;
logic  axi_wlast;
logic  axi_wvalid;
logic  axi_bready;
  logic reset; logic [1:0] init_count=0; logic past_valid=0;
  assign reset=init_count<2 || reset_later;
  LineMemoryAxi4Adapter dut(.*);
  // Environment obligation: AXI R/B sources hold stalled payload. No ID,
  // response-code, beat/last legality or bounded-latency assumptions.
  always @(posedge clock) begin
    past_valid<=1;
    if(init_count<2) init_count<=init_count+1'b1;
    if(past_valid && !$past(reset) && !reset) begin
      if($past(axi_rvalid && !axi_rready)) begin
        assume(axi_rvalid);
        assume({axi_rid,axi_rdata,axi_rresp,axi_rlast}==$past({axi_rid,axi_rdata,axi_rresp,axi_rlast}));
      end
      if($past(axi_bvalid && !axi_bready)) begin
        assume(axi_bvalid);
        assume({axi_bid,axi_bresp}==$past({axi_bid,axi_bresp}));
      end
      if($past(axi_awvalid && !axi_awready)) begin assert(axi_awvalid);assert({axi_awid,axi_awaddr}==$past({axi_awid,axi_awaddr}));end
    end
    if(init_count>=2) begin
      if(reset) assert(!line_rd_data_valid && !line_wr_rsp_valid && !axi_arvalid && !axi_awvalid && !axi_wvalid);
      if(line_rd_data_valid) begin
        assert(line_rd_data_id==axi_rid);
        assert(dut.rd_valid_q[dut.rd_match_slot] && dut.rd_issued_q[dut.rd_match_slot]);
        assert(line_rd_data_error || (line_rd_data_last==(line_rd_data_beat==7)));
        if(axi_rresp!=0 || axi_rlast!=(line_rd_data_beat==7)) assert(line_rd_data_error && line_rd_data_last);
      end
      if(line_wr_rsp_valid) begin
        assert(line_wr_rsp_id==axi_bid);
        assert(dut.wr_valid_q[dut.wr_rsp_match_slot] && dut.wr_w_done_q[dut.wr_rsp_match_slot]);
        assert(line_wr_rsp_error==(axi_bresp!=0));
      end
      if(axi_wvalid) begin assert(axi_wlast==(dut.wr_w_sent_count_q[dut.wr_w_slot]==7));end
      if($past(reset)) begin
        for(integer i=0;i<4;i=i+1) begin assert(!dut.rd_valid_q[i]);assert(!dut.wr_valid_q[i]);end
      end
    end
  end
endmodule
