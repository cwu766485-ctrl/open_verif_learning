// Single-context contract. Inputs are sampled handshakes, not assumptions.
// Reset cancels all credits. Exactly one metadata commit and grant may occur
// for an accepted request; a completion requires a previously accepted grant.
module DirectoryTransactionProperties (
  input logic clock, reset,
  input logic req_fire, write_fire, grant_fire, commit_fire,
  input logic [3:0] state,
  input logic write_valid,
  input logic [1:0] write_state, write_sharers,
  input logic write_owner,
  input logic req_ready, snoop_valid, xfer_valid, grant_valid,
  input logic snoop_ready, xfer_done_ready, commit_ready, error
);
  logic pending = 0, written = 0, granted = 0;
  logic past_valid = 0;
  always @(posedge clock) begin
    past_valid <= 1;
    if (reset) begin
      pending <= 0; written <= 0; granted <= 0;
    end else if (past_valid) begin
      if (req_fire) begin
        assert (!pending);
        pending <= 1; written <= 0; granted <= 0;
      end
      if (write_fire) begin
        assert (pending && !written && !granted);
        written <= 1;
      end
      if (grant_fire) begin
        assert (pending && written && !granted);
        granted <= 1;
      end
      if (commit_fire) begin
        assert (pending && written && granted);
        pending <= 0;
      end
      // Induction strengthening ties the independent handshake credits to
      // the implementation's phase. It is asserted, never assumed.
      assert (pending == ((state >= 1 && state <= 7) || state == 9));
      if (state >= 1 && state <= 5) assert (!written && !granted);
      if (state == 6) assert (written && !granted);
      if (state == 7 || state == 8) assert (written && granted);
      if (write_valid) begin
        assert (write_state != 3);
        if (write_state == 0) assert (write_sharers == 0 && !write_owner);
        if (write_state == 1) assert (write_sharers != 0 && !write_owner);
        if (write_state == 2) assert (write_sharers == 0);
      end
    end
    if (past_valid && $past(reset)) begin
      assert (state == 0 && req_ready);
      assert (!snoop_valid && !xfer_valid && !grant_valid && !write_valid);
      assert (!snoop_ready && !xfer_done_ready && !commit_ready && !error);
    end
  end
endmodule
