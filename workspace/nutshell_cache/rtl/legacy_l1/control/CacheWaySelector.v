// Select a unique hit way or a separately verified refill/victim way.
module CacheWaySelector (
  input        request_valid,
  input  [3:0] hit_vec,
  input  [3:0] refill_waymask,
  output       hit,
  output [3:0] selected_waymask
);
  assign hit = request_valid & |hit_vec;
  assign selected_waymask = hit ? hit_vec : refill_waymask;

`ifdef FORMAL
  function automatic is_onehot4(input [3:0] value);
    begin
      is_onehot4 = (value != 4'b0000) &&
                   ((value & (value - 4'b0001)) == 4'b0000);
    end
  endfunction

  always @* begin
    // Unique valid tags are a cache metadata invariant. The tag comparator
    // therefore produces either no hit or exactly one hit way. The refill
    // selector is separately proven one-hot in replacement_selector.sby.
    assume ((hit_vec == 4'b0000) || is_onehot4(hit_vec));
    assume (is_onehot4(refill_waymask));
    assert (!request_valid || is_onehot4(selected_waymask));
  end
`endif
endmodule
