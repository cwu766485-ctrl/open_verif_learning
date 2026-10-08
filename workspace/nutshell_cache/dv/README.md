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
Alongside it, `SetAssociativeTagModel` models the cache's 128 sets, four ways,
valid/tag/dirty state, and 64-byte lines. It predicts hit/miss before looking
at memory traffic whenever its abstract state makes the answer deterministic;
when randomized replacement leaves multiple legal states, observed traffic
resolves and prunes those candidates. It rejects impossible hit/miss histories.
The scoreboard checks dirty-victim addresses against legal model choices and
compares all eight writeback data beats, masks, commands, and burst-base
addresses. A separate `LfsrReplacementModel` independently advances the RTL
seed and polynomial every sampled cycle; `CacheDutProperties` compares its
predicted one-hot victim mask against the actual selector on every valid cycle.
The tag model still keeps a set of legal physical-way states when replacement
history is ambiguous, so it does not yet predict each evicted tag's exact way.

## Current regression and coverage

- 37/37 pytest cases pass. Scenarios include reset with a refill in flight,
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
- The merged Verilator line report is 95.1% (1403/1476) across maintained RTL
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
  98.0% (845/862), and the all-source report is 95.1%. Exclusions cover
  assertion-failure diagnostics, unreachable zero-state LFSR recovery,
  prohibited DCache flush, non-legal CPU burst paths, and two control-only
  LCOV line records whose statement bodies are hit. Generated wrappers remain
  visible in the raw HTML report but are not counted as maintained RTL.

`CacheDutProperties` tracks accepted/completed/reset-aborted CPU transactions,
samples the RTL replacement-selector one-hot invariant, and rejects accounting
imbalances. The existing ready/valid checkers verify stalled payload stability;
the protocol checker catches missing, duplicate, or illegal responses.

This is an open-source, sign-off-style regression flow, not commercial
sign-off equivalence. GitHub Actions is configured to install the toolchain
from scratch, generate the DUT, run formal checks and the multi-seed
regression, gate RTL/functional coverage, and upload reports. Local
SymbiYosys/Yosys/Z3 runs currently prove the LFSR recurrence and nonzero reset
state, one-hot replacement/refill selection (under the unique-tag invariant),
and Stage2 request-payload stability under backpressure (assuming a compliant
upstream ready/valid source). Response loss/duplication and stale-response
checks are currently simulation properties with checker fault injection; they
are not yet end-to-end formal proofs. The tag model's exact physical-way state
and a full-cache reset proof remain future work. UVM is not needed for this
project's goal of demonstrating Python and open-source verification breadth.

## Run

Run inside WSL with the project toolchain activated:

```bash
make gen_dut
make test
make report
```

`make report` runs the regression once and generates merged RTL line coverage
plus functional coverage reports under `reports/`.
