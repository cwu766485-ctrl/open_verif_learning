// Semantic reference unit for the 32-bit Cache address layout.
module AddressDecoder (
  input  [31:0] addr,
  output [18:0] tag,
  output [6:0]  set_index,
  output [2:0]  word_index,
  output [2:0]  byte_offset
);
  assign tag         = addr[31:13];
  assign set_index   = addr[12:6];
  assign word_index  = addr[5:3];
  assign byte_offset = addr[2:0];
endmodule
