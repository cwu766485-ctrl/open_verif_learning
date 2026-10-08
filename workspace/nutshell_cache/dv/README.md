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
addresses. The model does not duplicate the RTL's cycle-by-cycle LFSR phase,
so it allows legal victims rather than predicting an exact random victim
sequence.

## Current regression and coverage

- 35/35 tests pass: 16 Toffee simulation scenarios plus 19 pure Python
  reference-model/protocol-contract/coverage-closure
  unit tests. Scenarios include reset with a refill in flight, queued same-set
  misses, byte masks, MMIO bypass, probe/release, backpressure, and exact
  eight-beat dirty-victim writeback.
- The functional plan has 20 required goals, including read/write x hit/miss
  crosses and partial-mask x hit/miss crosses. The current regression hits
  20/20 (100%); `make report` now fails if any planned goal is missed.
- The randomized cache sequence runs six fixed seeds x 64 operations (384
  operations); CI adds two fixed seeds, for eight reproducible seeds x 64
  operations (512 operations) per CI run.
- The merged Verilator line report is 95.0% (1390/1463) across maintained RTL
  plus generated DUT/wrapper sources. Maintained `rtl/` entries are 98.0%
  (836/853). `make report` merges each Toffee test's `.dat`; using only the
  global `VCache_coverage.dat` under-counts the suite.
- The regression CPU contract is the NutShell L1 DCache port: upstream LSU
  source emits single-beat `READ`/`WRITE`; `READBST` is not a legal CPU-port
  request. The shared CacheStage3 source retains hierarchy-specific burst
  logic, while the external-memory interface is exercised with eight-beat
  refills/writebacks. A contract test confirms the CPU checker rejects
  `READBST` rather than treating an unsupported request as a DUT bug.
- `make report` validates maintained-RTL coverage against the reviewed
  exclusions in `coverage/waivers.json`. Waiver-adjusted maintained RTL
  statement coverage is 100% (836/836); raw maintained-RTL coverage remains
  98.0% (836/853), and the all-source report remains 95.0%. Exclusions cover
  assertion-failure diagnostics, unreachable zero-state LFSR recovery,
  prohibited DCache flush, non-legal CPU burst paths, and two control-only
  LCOV line records whose statement bodies are hit. Generated wrappers remain
  visible in the raw HTML report but are not counted as maintained RTL.

`CacheDutProperties` tracks accepted/completed/reset-aborted CPU transactions,
samples the RTL replacement-selector one-hot invariant, and rejects accounting
imbalances. The existing ready/valid checkers verify stalled payload stability;
the protocol checker catches missing, duplicate, or illegal responses.

This is an open-source, sign-off-style regression flow, not commercial
sign-off equivalence. GitHub Actions is configured to generate the DUT, run
the multi-seed regression, gate both RTL and functional coverage, and upload
reports. Formal proofs have not been run: Yosys/SymbiYosys are not installed in
the current WSL environment, and the new protocol/reference checks are dynamic
simulation assertions rather than formal proof. UVM is not needed for this
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
