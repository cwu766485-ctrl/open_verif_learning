// Generated source control slice; see extraction manifest and scope.
module FinalL2ReadControl(input logic clock,reset,line_rd_valid,line_rd_hit,line_data_ready,
output logic line_rd_ready,line_data_valid,line_data_last,output logic [2:0] line_data_beat_idx);
logic line_rd_busy_q;logic [2:0] line_rd_beat_q;
assign line_rd_ready=!line_rd_busy_q;assign line_data_valid=line_rd_busy_q;
assign line_data_last=line_rd_beat_q==7;assign line_data_beat_idx=line_rd_beat_q;
always @(posedge clock) begin
if(reset) begin line_rd_busy_q<=0;line_rd_beat_q<=0;end else begin
      if (line_rd_valid && line_rd_ready) begin
        line_rd_busy_q <= line_rd_hit;
        line_rd_beat_q <= '0;
      end else if (line_data_valid && line_data_ready) begin
        if (line_rd_beat_q == 3'd7) begin
          line_rd_busy_q <= 1'b0;
          line_rd_beat_q <= '0;
        end else begin
          line_rd_beat_q <= line_rd_beat_q + 1'b1;
        end
      end
end end
endmodule
