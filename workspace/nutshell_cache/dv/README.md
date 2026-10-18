# NutShell Cache open-source DV environment

The active environment verifies the NutShell L1 DCache at its SimpleBus
boundary. It uses Python/Toffee agents and checkers with pytest and
Picker/Verilator; the workflow does not depend on a commercial simulator.
SystemVerilog UVM is not a project requirement. The goal is to build a
reusable, inspectable verification flow on an open toolchain, while borrowing
the useful verification concepts of agents, sequences, monitors, scoreboards,
protocol checks, and coverage.

## Architecture

```text
tests/ stimulus and directed/random scenarios
  -> CacheTestbench
     -> CPU / memory / MMIO / coherence agents and monitors
     -> CacheReferenceModel -> in-order CacheScoreboard
     -> bus protocol + ready/valid checkers
     -> functional coverage collector -> JSON / HTML report
```

`agents/` implements bus drivers and monitors; `protocol/` and `common/`
define interfaces and transactions; `models/` contains the reference and RAM
models; `env/` binds bus roles to DUT ports; `testbench/` composes the
scoreboard, checkers, and coverage. Tests currently drive the agents directly
rather than through a separate sequencer API.

## Reference model

The CPU-visible oracle maintains sparse 64-bit memory with byte-mask semantics.
Alongside it, `SetAssociativeTagModel` tracks the cache's 128 sets, four
physical ways, valid/tag/dirty state, and 64-byte lines. It independently
predicts hit/miss, invalid-first refill selection, and the exact LFSR-selected
victim way. `CacheTop` exposes a verification-only Stage2 transfer event;
`CacheDutProperties` compares each event's hit/miss and way mask against the
Refm before updating its state. The scoreboard consumes the saved pre-access
prediction and checks the exact dirty-victim address plus all eight writeback
data beats, masks, commands, and burst-base addresses. The LFSR model advances
independently each sampled clock and is checked against the RTL selector on
every valid cycle.

## Current regression and coverage

- Before the new directed timing test was added, the recorded regression
  passed 39/39 pytest cases. Scenarios include reset with a refill in flight,
  queued same-set misses, byte masks, MMIO bypass, probe/release,
  backpressure, same-word data forwarding, and exact eight-beat dirty-victim
  writeback.
- The previous recorded functional plan had 37 goals and hit 37/37 (100%). The
  expanded plan now has 45 goals, adding cache/MMIO region and MMIO operation
  crosses, adjacent-line boundary traffic, dirty-miss, and downstream
  memory/MMIO backpressure crosses. The new
  plan has not yet been rerun; `make report` checks closure against all goals.
- The randomized cache sequence runs seven fixed seeds x 64 operations (448
  operations); CI adds two fixed seeds, for nine reproducible seeds x 64
  operations (576 operations) per CI run.
- The merged Verilator line report is 95.2% (1424/1496) across maintained RTL
  plus generated DUT/wrapper sources. Maintained `rtl/` entries are 98.1%
  (846/862). `make report` merges each Toffee test's `.dat`; using only the
  global `VCache_coverage.dat` under-counts the suite.
- The regression CPU contract is the NutShell L1 DCache port: upstream LSU
  source emits single-beat `READ`/`WRITE`; `READBST` is not a legal CPU-port
  request. The shared CacheStage3 source retains hierarchy-specific burst
  logic, while the external-memory interface is exercised with eight-beat
  refills/writebacks. A contract test confirms the CPU checker rejects
  `READBST` rather than treating an unsupported request as a DUT bug.
- `make report` validates maintained-RTL coverage against the reviewed
  exclusions in `coverage/waivers.json`. Waiver-adjusted maintained RTL
  statement coverage is 100% (846/846); raw maintained-RTL coverage remains
  98.1% (846/862), and the all-source report is 95.2% (1424/1496). Exclusions cover
  assertion-failure diagnostics, unreachable zero-state LFSR recovery,
  prohibited DCache flush, non-legal CPU burst paths, and two control-only
  LCOV line records whose statement bodies are hit. Generated wrappers remain
  visible in the raw HTML report but are not counted as maintained RTL.

`tests/test_protocol_contract.py` unit-tests the checker's transaction rules
without running the DUT; it rejects illegal CPU commands, unpaired/duplicate
responses, and stale responses after reset. `tests/test_timing.py` checks real
RTL timing by delaying downstream request acceptance and holding the CPU
response sink not-ready, then checking that response valid and payload remain
stable until handshake. The full-capacity all-zero/all-one/alternating-bit
data sweep adds an address-signature pass to catch address aliasing. The new
mega-random test uses 32 fixed seeds x 512 operations by default, guarantees
cache/MMIO and conflict-eviction scenarios, and checks generated stores with
readbacks and the scoreboard. Both are marked `slow` and run with
`make test_slow`; `make mega_random` runs only the mega-random test. Set
`NUTSHELL_MEGA_RANDOM_SEEDS` to append reproducible seeds and
`NUTSHELL_MEGA_RANDOM_OPS` to change the per-seed random length. Normal
`make test` and `make report` omit these slow tests.

The formal proof harnesses live under `formal/`. The mutation runner that
checks whether formal assertions catch injected RTL changes also lives under
`formal/mutations/`; `dv/fault_injection/` remains separate because it tests
the Python checker and scoreboard with bad transaction observations.

`CacheDutProperties` tracks accepted/completed/reset-aborted CPU transactions,
samples the RTL replacement-selector one-hot invariant, and rejects accounting
imbalances. The ready/valid checkers verify full stalled-payload stability;
the protocol checker catches missing, duplicate, stale, or illegal responses.

The Stage3 harness now checks response provenance and duplicate retirement,
reset cancellation, and stalled response `valid`, `cmd`, and `rdata` stability.
Independent formal expressions check byte-mask merging on hit writes, the
first-beat write-miss merge, and the selected victim word sent to memory. A
12-cycle harness connects Stage3 to a reduced one-set/four-way/eight-beat
abstract data line and memory model, then checks refill writes and dirty
writeback data/address/command behavior. These Stage3 checks are bounded;
the proof assumptions and bounds are listed in `../formal/README.md`.

The metadata invariant is proved by k-induction in a reduced transition model:
valid ways in a set never contain duplicate tags when hit updates retain the
matching tag and refills install a tag that was not already present. A
12-cycle SAT bridge checks those write conditions against the actual Stage3
metadata output. Directed SymbiYosys cover jobs exercise metadata refill/hit,
reset during an active memory transaction, stalled responses, and the final
beats of dirty writeback/refill. `make formal` also injects four planned RTL
mutations and requires every one to be caught by an assertion.

The data-line model is a constrained abstraction, not a proof of the complete
128-set SRAM implementation. The metadata transition proof is unbounded under
its write contract; the Stage3 integration, data movement, and lifecycle
checks are bounded to their documented depths. Full-cache reset sweep and
unbounded end-to-end transaction behavior remain outside the current proof.

This is an open-source, sign-off-style regression flow, not commercial
sign-off equivalence. GitHub Actions is configured to install the toolchain
from scratch, generate the DUT, run formal checks and the multi-seed
regression, gate RTL/functional coverage, and upload reports. Local
SymbiYosys/Yosys runs prove the LFSR recurrence and nonzero reset state,
one-hot replacement/refill selection (under the unique-tag invariant), Stage2
request-payload stability under backpressure, and bounded Stage3 response
control properties. An unbounded end-to-end response lifecycle proof and a
full-cache reset proof remain future work. UVM is not needed for this project's
goal of demonstrating Python and open-source verification breadth.

The current clean-runner workflow is tracked on the project branch; its live
status and run history are available at
https://github.com/cwu766485-ctrl/open_verif_learning/actions/workflows/nutshell-cache-dv.yml.
The workflow runs nine fixed seeds (576 randomized operations) in addition
to the local seven-seed regression.

## Run

Run inside WSL with the project toolchain activated:

```bash
make gen_dut
make test
make report
```

`make report` runs the regression once and generates merged RTL line coverage
plus functional coverage reports under `reports/`.
