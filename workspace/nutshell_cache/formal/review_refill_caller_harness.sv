module ReviewRefillCallerFormal(
input logic  clock ,
input logic caller_request ,
input logic [31:0] alloc_addr ,
input logic [2-1:0] alloc_context ,
input logic  mem_rd_data_valid ,
input logic  mem_rd_data_ready ,
input logic [4-1:0] mem_rd_data_txn_id ,
input logic [2:0] mem_rd_data_beat_idx ,
input logic [63:0] mem_rd_data ,
input logic  mem_rd_data_last ,
input logic  mem_rd_data_error ,
input logic  fill_start_allowed ,
input logic  line_wr_valid ,
input logic  line_wr_ready ,
input logic  xfer_done_active ,
input logic  xfer_done_valid ,
input logic  xfer_done_ready ,
input logic [31:0] dir_xfer_addr ,
input logic [31:0] dir_snoop_addr ,
input logic reset_later
);
logic [4-1:0] mem_mshr_valid_q ;
logic [4-1:0] mem_mshr_full_q ;
logic [4-1:0] mem_mshr_written_q ;
logic [31:0] mem_mshr_addr_q [0:4-1];
logic [2-1:0] mem_mshr_context_q [0:4-1];
logic [2:0] mem_mshr_expected_q [0:4-1];
logic [63:0] mem_mshr_data_q [0:4-1][0:7];
logic  mem_mshr_alloc_found ;
logic  mem_mshr_fill_found ;
logic  mem_mshr_done_found ;
logic [2-1:0] mem_mshr_alloc_sel ;
logic [2-1:0] mem_mshr_fill_sel ;
logic [2-1:0] mem_mshr_done_sel ;
logic  mem_mshr_r_match ;
logic  mem_r_protocol_bad ;
logic [2-1:0] mem_mshr_r_sel ;
logic  mem_fill_writer_active_q ;
logic [2-1:0] mem_fill_writer_sel_q ;
logic [2:0] mem_fill_writer_beat_q ;
logic [2-1:0] mem_mshr_done_context ;
logic  mshr_set_conflict ;
logic  snoop_set_conflict ;
logic reset;logic [1:0] init_count=0;logic past_valid=0;
assign reset=init_count<2 || reset_later;
logic alloc_valid;
// Main route_memory_channels + bank instance connection: symbolic engine
// eligibility subsumes engine==MEM_REQ, !fatal and !reset; free is actual bank.
assign alloc_valid = !reset && caller_request && mem_mshr_alloc_found;
MemoryRefillMshrBank dut(.*);
always @(posedge clock) begin
 past_valid<=1;
 if(init_count<2)init_count<=init_count+1'b1;
 if(init_count>=2 && !reset) begin
  for(integer i=0;i<4;i=i+1) begin
   assert(!mem_mshr_full_q[i] || mem_mshr_valid_q[i]);
   assert(!mem_mshr_written_q[i] || mem_mshr_full_q[i]);
  end
  if(mem_fill_writer_active_q) begin
   assert(mem_mshr_valid_q[mem_fill_writer_sel_q]);
   assert(mem_mshr_full_q[mem_fill_writer_sel_q]);
   assert(!mem_mshr_written_q[mem_fill_writer_sel_q]);
  end
  // Caller guarantee obligation; no assumptions about response ID/beat/last.
  assert(!alloc_valid || mem_mshr_alloc_found);
  if(mem_mshr_r_match) begin
   assert(mem_rd_data_txn_id<4);
   assert(mem_mshr_r_sel==mem_rd_data_txn_id);
   assert(mem_mshr_valid_q[mem_mshr_r_sel] && !mem_mshr_full_q[mem_mshr_r_sel]);
  end
  if(mem_rd_data_valid && mem_rd_data_ready && mem_rd_data_txn_id>=4)assert(mem_r_protocol_bad);
  if(mem_rd_data_valid && mem_rd_data_ready && mem_mshr_r_match && !mem_rd_data_error &&
     (mem_rd_data_beat_idx!=mem_mshr_expected_q[mem_mshr_r_sel] || mem_rd_data_last!=(mem_rd_data_beat_idx==7)))assert(mem_r_protocol_bad);
 end
 if(past_valid && init_count>=2 && !$past(reset) && !reset) begin
  for(integer i=0;i<4;i=i+1) begin
   if($past(alloc_valid && mem_mshr_alloc_sel==i)) begin assert(mem_mshr_valid_q[i]);assert(!mem_mshr_full_q[i]);assert(!mem_mshr_written_q[i]);assert(mem_mshr_expected_q[i]==0);end
   if(!$past(alloc_valid && mem_mshr_alloc_sel==i) &&
      !$past(!xfer_done_active && mem_mshr_done_found && xfer_done_valid && xfer_done_ready && mem_mshr_done_sel==i)) begin
    if(!$past(mem_mshr_full_q[i]) && mem_mshr_full_q[i]) begin
     assert($past(mem_rd_data_valid && mem_rd_data_ready && mem_mshr_r_match && mem_mshr_r_sel==i && !mem_rd_data_error && mem_rd_data_beat_idx==7 && mem_rd_data_last && mem_mshr_expected_q[i]==7));
    end
   end
  end
  if($past(mem_fill_writer_active_q && !(line_wr_valid && line_wr_ready))) begin assert(mem_fill_writer_active_q);assert(mem_fill_writer_sel_q==$past(mem_fill_writer_sel_q));assert(mem_fill_writer_beat_q==$past(mem_fill_writer_beat_q));end
 end
 if(past_valid && init_count>=2 && $past(reset)) begin assert(mem_mshr_valid_q==0);assert(mem_mshr_full_q==0);assert(mem_mshr_written_q==0);assert(!mem_fill_writer_active_q);end
end
endmodule
