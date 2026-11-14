    // Same-top functional stimulus. High tags remain cacheable; each byte
    // lane and each word in a full line is checked through the remote core.
    begin : risk_closure_patterns
      logic [31:0] addr;
      logic [63:0] expected;
      logic [63:0] data;
      logic [63:0] ignored_pattern;
      for (integer tag_bit = 15; tag_bit < 32; tag_bit++) begin
        addr = (32'h1 << tag_bit) | 32'h0000_1c00;
        if (addr >= 32'h3000_0000 && addr < 32'h8000_0000) addr |= 32'h8000_0000;
        // 0x30000000 MMIO is never selected by these one-hot addresses.
        for (integer word_idx = 0; word_idx < 8; word_idx++) begin
          expected = 64'hffff_ffff_ffff_ffff;
          cpu_access(0, addr + 8*word_idx, 1, 8'hff, expected, ignored_pattern);
          expect_word(1, addr + 8*word_idx, expected);
          for (integer lane = 0; lane < 8; lane++) begin
            data = 64'ha55a_9669_f00f_3cc3 ^ (64'h0101_0101_0101_0101 * lane);
            expected = (expected & ~(64'hff << (8*lane))) |
                       (data & (64'hff << (8*lane)));
            cpu_access(lane % 2, addr + 8*word_idx, 1, 8'(1 << lane), data, ignored_pattern);
            expect_word(1 - lane % 2, addr + 8*word_idx, expected);
          end
          cpu_access(1, addr + 8*word_idx, 1, 8'hff, 64'h0, ignored_pattern);
          expect_word(0, addr + 8*word_idx, 64'h0);
        end
      end
      $display("PASS: same-top high address tags, eight word offsets, each byte lane, ones/zeros and remote owner data checked");
    end
