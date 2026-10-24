// Byte-granular write merge for one 64-bit Cache word.
module ByteMaskMerge (
  input  [63:0] old_data,
  input  [63:0] write_data,
  input  [7:0]  byte_mask,
  output [63:0] merged_data
);
  wire [63:0] expanded_mask = {
    {8{byte_mask[7]}}, {8{byte_mask[6]}},
    {8{byte_mask[5]}}, {8{byte_mask[4]}},
    {8{byte_mask[3]}}, {8{byte_mask[2]}},
    {8{byte_mask[1]}}, {8{byte_mask[0]}}
  };
  assign merged_data = (old_data & ~expanded_mask) |
                       (write_data & expanded_mask);
endmodule
