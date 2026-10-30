  initial begin
    #5_000_000;
    $fatal(1, "end-to-end AXI cache test timed out");
  end
