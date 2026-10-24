// Four-way tag comparison. hit_vec is one-hot-or-zero when the metadata
// invariant (no duplicate valid tags in a set) holds.
module TagCompareUnit (
  input  [18:0] request_tag,
  input  [18:0] tag0, input valid0,
  input  [18:0] tag1, input valid1,
  input  [18:0] tag2, input valid2,
  input  [18:0] tag3, input valid3,
  output [3:0]  hit_vec,
  output        hit
);
  assign hit_vec[0] = valid0 && (tag0 == request_tag);
  assign hit_vec[1] = valid1 && (tag1 == request_tag);
  assign hit_vec[2] = valid2 && (tag2 == request_tag);
  assign hit_vec[3] = valid3 && (tag3 == request_tag);
  assign hit = |hit_vec;
endmodule
