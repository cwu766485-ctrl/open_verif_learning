# Python/Toffee Full-System Verification Architecture

## DUT and verification boundary

The integrated DUT is `rtl/top/CoherentCacheAxiSubsystem.sv`. The verification-
only wrapper `dv/rtl/CoherentCacheAxiPythonWrapper.sv` connects the existing
RTL, packs the dual CPU lanes for Picker/Toffee, and exports selected internal
signals as read-only observations. Product RTL behavior and interfaces are not
changed by this environment.

The environment uses Python, Toffee, Picker, Verilator, pytest, the existing
Python reference model/scoreboard, and the selected RTL monitor taps. It uses
UVM-style separation of responsibilities; it is not SystemVerilog UVM.

## Components and ownership

| Role | Component | Responsibility |
| --- | --- | --- |
| CPU0/CPU1 | `DualCoreCpuDriver` in `dv/agents/coherent_cpu_agent.py` | Sole writer for both packed lanes; per-lane request/response lifecycle, pairing, timing, backpressure and response matching |
| AXI memory slave | `Axi4BackingMemoryAgent` | AR/R/AW/W/B, line backing memory, ID contexts, 8-beat bursts, read response interleaving, write ordering, slave-side AR/AW/W/B stalls, RVALID response gaps, error injection and reset cancellation |
| MMIO slave | `MmioSlaveAgent` | Request/response model, byte enables, delays/backpressure, response reset cancellation and independent register data |
| APB master | `ApbMasterAgent` | CSR reads, protected writes, invalid address checks and bounded APB completion |
| System environment | `FullSystemEnv` | Owns agents, reset, independent coherence scoreboard, monitor and coverage collector |
| Passive monitor | `FullSystemMonitor` | Samples actual external handshakes and existing L1/Directory/Snoop/L2/MSHR probes; never drives the DUT |
| Reference/checker | `CoherenceScoreboard` plus MMIO/AXI agent models | Checks CPU data, byte-mask merges, MESI/directory observations and bus transactions without using DUT state as expected state |
| Coverage | `FullSystemCoverage` and JSON plan | Counts checked events and crosses only after the corresponding checker succeeds |
| Sequence/replay | `FullSystemRandomSequence`, `full_system_replay.py` | Seeded legal perturbation, dual-lane pairs, saved JSONL trace and CPU transaction replay |

The CPU lanes are blocking at the architectural API. The driver may issue two
lanes together and can retire one response while continuing to offer another
lane, but this does not add CPU-side MSHRs or claim four concurrent CPU misses.

## Data independence and observation

Expected architectural data is predicted from CPU requests and the independent
scoreboard. AXI backing memory is seeded alongside the reference memory before
traffic. Actual L1 metadata commits and Directory commits are compared against
model predictions; monitor data is never used to create expected values.
Coverage for MESI transitions requires an observed L1 commit matching a model
transition. Reset clears monitor transaction contexts and records cancellation.

Gray-box visibility is intentionally partial: selected metadata, Directory,
snoop, owner-data, L2 lookup/write, MSHR occupancy and active-context probes are
available. It does not prove each MSHR's full allocation-to-retirement route or
expose every L2 data-array bit.

## Implemented scenario evidence

The directed tests currently cover:

1. Cold refill and cross-core GetS/ownership transfer with read-data and
   metadata checking.
2. Two distinct cold misses overlapping at AXI, returning out of order by ID;
   measured MSHR occupancy reaches two.
3. MMIO masked writes/readback and two-core MMIO arbitration.
4. An MMIO request concurrent with another core's cache miss, and an APB CSR
   read while the AXI refill is active.
5. Reset cancellation of a delayed AXI read and a delayed MMIO response; no
   stale response is accepted, and the AXI ID can be reused for a successful
   refill.
6. Injected AXI RRESP error: DUT fail-stop asserts and no successful CPU
   response is returned.
7. APB read-only write and unmapped-offset `PSLVERR` checks.

The default full-system random suite runs 10 deterministic seeds × 100
operations, after coverage-guided MESI-owner and dual-cold-miss preludes. It
mixes reads/writes, byte masks, response stalls and paired requests on distinct
cache lines, and checks CPU responses and observed commits. A directed
four-interface overlap test also runs CPU0 MMIO, CPU1 cache refill, AXI memory
response and APB counter read against the same live DUT, then checks their
cycle overlap and independent data/counter results. Separate seeded mixed
campaigns randomize CPU/MMIO read/write and masks while APB samples a live miss
counter under AXI AR stalls and RVALID gaps. Resource-aware scenarios create
an M owner and compare same-set serialization with distinct-set Snoop progress
during an independent refill. A dual-lane transaction trace replay has also
been exercised.

`make coherence_full_system_stress` runs 20 seeds × 500 CPU operations (10,000
operations), 20 mixed CPU/MMIO/APB/AXI seeds × 10 rounds, and 20 same/distinct
set contention seeds. The directed campaigns use independent data models and
check actual observed handshakes before crediting bins.

## Coverage scope and limits

The current verification snapshot reports 53/53 Required Functional and 35/35
Required Cross bins in the full-system checked plan. The separate Python
coherence block plan reports 49/49 functional and 19/19 cross bins. These
plans are distinct from each other and from Verilator RTL
line/branch/toggle/FSM coverage; their counts must not be added. The detailed
source SHA, gate results, raw RTL datasets and remaining gaps are maintained
in [`final_verification_report.md`](final_verification_report.md) and the
[`machine-readable run manifest`](../../reports/final/verification_run_manifest.json).

The stress tier currently runs 280 environments across CPU-random,
CPU/MMIO/APB/AXI mixed traffic, resource-aware snoop/refill, reset, injected
AXI error and reset-with-directory/snoop-pending campaigns. Optional/planned
entries such as four concurrent CPU misses remain outside the top-level
blocking CPU contract. Four-context MSHR activity is checked at the
DirectoryMshrBank block; multi-ID B response behavior is checked at the AXI
adapter.

Still open are broad combinations of channel-specific backpressure, APB
counter overflow/saturation, exhaustive L2 victim state/core combinations,
and full independent prediction of every MSHR and L2-directory transition.
The top-level two-lane CPU interface is blocking, so four concurrent CPU
misses cannot be generated through it. The integrated write path serializes
writebacks, so B response reordering is only meaningful at the adapter.
The RVALID gaps in the integrated test are source pacing, not RREADY
backpressure. Random scheduling targets legal MESI transitions, two-MSHR
out-of-order refills, mixed timing and same/distinct-set Snoop/refill
relations; it is not feedback-guided across every Directory, Snoop, MSHR and L2
feature. Replay preserves requests, pairing, seed/config, initial memory and
response stalls, while simulator cycle scheduling is re-evaluated. The
extended stress tier is separate from the default 10 × 100 closure run.

## Commands

```bash
source scripts/env.sh
make coherence_full_system_smoke
make coherence_full_system_coverage
make coherence_full_system_stress
make coherence_full_system_replay_trace \
  FULL_SYSTEM_REPLAY_TEST_ID='tests/full_system/test_full_system_coherence.py::test_dual_cold_misses_overlap_and_route_axi_responses'
```

`make coherence_full_system_verify` runs the existing `coherence_verify` suite
before the full-system suite. Existing Legacy L1, Block DV, Formal and Python
coherence entry points remain separate and unchanged.
