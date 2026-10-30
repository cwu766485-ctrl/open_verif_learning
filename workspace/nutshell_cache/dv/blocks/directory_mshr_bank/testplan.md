# DirectoryMshrBank Testplan

## DUT and RTL dependencies

- **DUT:** `DirectoryMshrBank` with the `DirectoryController` contexts it schedules.
- **RTL dependencies:** `rtl/common/CoherenceProtocol.sv`, `rtl/directory/DirectoryController.sv`, `rtl/directory/DirectoryMshrBank.sv`.
- **Existing bench:** `tb/DirectoryMshrBank_tb.sv`; directed stimulus and COV_EVENT statements are moved unchanged.
- Shared agents, models, scoreboards/checkers and coverage collectors remain in their existing `dv/` locations.

## Interface Groups

Context allocation/completion; Directory request/transfer/grant; shared L2 lookup and write; snoop request/response/data; replacement Put; reset.

## Features, testpoints and checkers

| Feature | Existing testcase / testpoint | Checker | Coverage Bin ID |
|---|---|---|---|
| Directory MSHR concurrency | Four distinct line misses overlap and refill out of order | `DirectoryMshrBank_tb` directed checks and its `checker=PASS` COV_EVENT | `mshr_bank.four_contexts` |
| Directory MSHR concurrency | Duplicate same-line request is suppressed while four contexts are occupied | `DirectoryMshrBank_tb` directed checks and its `checker=PASS` COV_EVENT | `mshr_bank.duplicate_suppression` |
| Directory MSHR concurrency | Different lines in one L2 set cannot retain overlapping Directory snapshots | `DirectoryMshrBank_tb` directed checks and its `checker=PASS` COV_EVENT | `mshr_bank.same_set_serialization` |
| Directory MSHR concurrency | A same-set Put can progress while an ownership transaction is active | `DirectoryMshrBank_tb` directed checks and its `checker=PASS` COV_EVENT | `mshr_bank.same_set_put_bypass` |
| Directory MSHR concurrency | A same-line replacement Put waits unless it is unblocking a stalled owner Snoop | `DirectoryMshrBank_tb` directed checks and its `checker=PASS` COV_EVENT | `mshr_bank.same_line_put_serialization` |
| Directory MSHR concurrency | A replacement Put bypasses its same-line context only when that context is stalled Snoop-targeting the Put source | `DirectoryMshrBank_tb` directed checks and its `checker=PASS` COV_EVENT | `mshr_bank.stalled_snoop_target_put` |
| Directory MSHR concurrency | A context blocked on snoop does not prevent other contexts from progressing | `DirectoryMshrBank_tb` directed checks and its `checker=PASS` COV_EVENT | `mshr_bank.snoop_independence` |
| Directory MSHR concurrency | Reset cancels four active Directory contexts without residual completion | `DirectoryMshrBank_tb` directed checks and its `checker=PASS` COV_EVENT | `mshr_bank.reset_cancel` |

## Coverage ownership and gaps

- These eight existing IDs are emitted by the MSHR block bench and are checked by `dv/coverage/coherence_closure.py`; IDs and expected meanings are unchanged.
- **Remaining gaps:** the bench is directed and finite. It does not establish unconstrained liveness, all allocation/response permutations, arbitrary long backpressure, nor complete MSHR data-path behavior. Those remain covered only to the extent stated by existing subsystem/formal targets.
- This move does not add coverage or claim new closure.
