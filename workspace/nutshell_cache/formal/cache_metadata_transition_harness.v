// Abstract one-set/4-way metadata transition lemma. CacheStage3's write-port
// contract is checked against the DUT in cache_metadata_stage3.sby.
module CacheMetadataTransitionHarness(
  input clock,
  input reset,
  input write_valid,
  input write_is_hit,
  input [1:0] request_tag,
  input [3:0] write_waymask,
  input [1:0] write_tag
);
  reg [3:0] valid = 4'b0;
  reg [1:0] tag_0 = 2'b0;
  reg [1:0] tag_1 = 2'b0;
  reg [1:0] tag_2 = 2'b0;
  reg [1:0] tag_3 = 2'b0;

  wire [3:0] hit_vec = {
    valid[3] && (tag_3 == request_tag),
    valid[2] && (tag_2 == request_tag),
    valid[1] && (tag_1 == request_tag),
    valid[0] && (tag_0 == request_tag)
  };

  function automatic onehot4(input [3:0] value);
    begin
      onehot4 = (value != 4'b0) && ((value & (value - 4'b1)) == 4'b0);
    end
  endfunction

  always @(posedge clock) begin
    if ($initstate)
      assume (reset);

    if (write_valid) begin
      assume (onehot4(write_waymask));
      assume (write_tag == request_tag);
      if (write_is_hit) begin
        assume (onehot4(hit_vec));
        assume (write_waymask == hit_vec);
      end else begin
        assume (hit_vec == 4'b0);
      end
    end

    assert (!(valid[0] && valid[1] && (tag_0 == tag_1)));
    assert (!(valid[0] && valid[2] && (tag_0 == tag_2)));
    assert (!(valid[0] && valid[3] && (tag_0 == tag_3)));
    assert (!(valid[1] && valid[2] && (tag_1 == tag_2)));
    assert (!(valid[1] && valid[3] && (tag_1 == tag_3)));
    assert (!(valid[2] && valid[3] && (tag_2 == tag_3)));

    if (write_valid && write_waymask[0]) begin
      valid[0] <= 1'b1;
      tag_0 <= write_tag;
    end
    if (write_valid && write_waymask[1]) begin
      valid[1] <= 1'b1;
      tag_1 <= write_tag;
    end
    if (write_valid && write_waymask[2]) begin
      valid[2] <= 1'b1;
      tag_2 <= write_tag;
    end
    if (write_valid && write_waymask[3]) begin
      valid[3] <= 1'b1;
      tag_3 <= write_tag;
    end

    cover (write_valid && !write_is_hit);
    cover (write_valid && write_is_hit);
  end
endmodule
