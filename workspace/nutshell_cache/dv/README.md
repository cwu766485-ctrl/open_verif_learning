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

- 39/39 pytest cases pass. Scenarios include reset with a refill in flight,
  queued same-set misses, byte masks, MMIO bypass, probe/release,
  backpressure, same-word data forwarding, and exact eight-beat dirty-victim
  writeback.
- The functional plan has 37 goals covering set occupancy, hit/miss and partial
  writes, clean/dirty victims, backpressure channels, probe release, reset
  cancellation, and data forwarding. The current regression hits 37/37
  (100%); `make report` fails if any planned goal is missed.
- The randomized cache sequence runs six fixed seeds x 64 operations (384
  operations); CI adds two fixed seeds, for eight reproducible seeds x 64
  operations (512 operations) per CI run.
- The merged Verilator line report is 95.1% (1423/1496) across maintained RTL
  plus generated DUT/wrapper sources. Maintained `rtl/` entries are 98.0%
  (845/862). `make report` merges each Toffee test's `.dat`; using only the
  global `VCache_coverage.dat` under-counts the suite.
- The regression CPU contract is the NutShell L1 DCache port: upstream LSU
  source emits single-beat `READ`/`WRITE`; `READBST` is not a legal CPU-port
  request. The shared CacheStage3 source retains hierarchy-specific burst
  logic, while the external-memory interface is exercised with eight-beat
  refills/writebacks. A contract test confirms the CPU checker rejects
  `READBST` rather than treating an unsupported request as a DUT bug.
- `make report` validates maintained-RTL coverage against the reviewed
  exclusions in `coverage/waivers.json`. Waiver-adjusted maintained RTL
  statement coverage is 100% (845/845); raw maintained-RTL coverage remains
  98.0% (845/862), and the all-source report is 95.1% (1423/1496). Exclusions cover
  assertion-failure diagnostics, unreachable zero-state LFSR recovery,
  prohibited DCache flush, non-legal CPU burst paths, and two control-only
  LCOV line records whose statement bodies are hit. Generated wrappers remain
  visible in the raw HTML report but are not counted as maintained RTL.

`CacheDutProperties` tracks accepted/completed/reset-aborted CPU transactions,
samples the RTL replacement-selector one-hot invariant, and rejects accounting
imbalances. The ready/valid checkers verify full stalled-payload stability;
the protocol checker catches missing, duplicate, stale, or illegal responses.

The Stage3 response-control harness runs an 8-cycle bounded Yosys SAT check for
response provenance/duplicate retirement, reset cancellation, and stalled
response valid/command stability. It uses actual CacheStage3 RTL with data
arrays abstracted to constants, under the upstream single-beat READ/WRITE,
stable-until-finish, and MMIO-bypass contracts. This is a bounded safety check,
not an unbounded lifecycle proof; full response data-payload stability remains
covered by simulation checkers.

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
The workflow runs eight fixed seeds (512 randomized operations) in addition
to the local six-seed regression.

## Run

Run inside WSL with the project toolchain activated:

```bash
make gen_dut
make test
make report
```

`make report` runs the regression once and generates merged RTL line coverage
plus functional coverage reports under `reports/`.
