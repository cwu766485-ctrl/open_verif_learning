# LineMemoryAxi4Adapter + CachePerformanceCsr Testplan

## DUT and RTL dependencies

- DUT: `LineMemoryAxi4Adapter + CachePerformanceCsr`.
- RTL dependencies: `rtl/common/CoherenceProtocol.sv`, `rtl/bus/axi/LineMemoryAxi4Adapter.sv`, `rtl/bus/apb/CachePerformanceCsr.sv`.
- Existing bench: `tb/CacheBusBlocks_tb.sv`; the SV test body is unchanged by this move.
- Shared verification components stay in their existing `dv/agents`, `dv/models`, `dv/scoreboard`, `dv/checkers`, `dv/monitors` and `dv/coverage` locations.

## Interface Groups

AXI AW/W/B and AR/R; cache line request/response; APB setup/access/read/write.

## Features and testpoints

AXI burst fields; outstanding IDs and response routing; beat sequencing; independent backpressure; APB CSR address, access and counters.

| Feature / testpoint | Existing testcase | Checker / expected result | Coverage mapping |
|---|---|---|---|
| Read burst | AR/R translation, beat collection and error drain | fatal checks burst fields, beats, backpressure and line error | no coherence bin; bus bench only |
| Write burst | AW/W collection/order and B response | fatal checks payload, WLAST, held B response and error propagation | no coherence bin; bus bench only |
| Four outstanding/ID routing | queue four reads/writes, interleave R and reorder B | fatal checks depth, ID association, payload and ordered W serialization | no coherence bin; bus bench only |
| APB CSR | read counters/status and attempt CSR writes | fatal checks APB setup/access, read data and write rejection | no coherence bin; bus bench only |
| Unknown RID | inject unknown read response ID | fatal checks drain and protocol_error | no coherence bin; bus bench only |

## Coverage ownership and gaps

- Coverage Bin IDs are unchanged. This directory move does not add bins, mark uncovered behavior covered, or claim new closure. The maintained integrated map is `dv/coverage/coherence_map.json`; Legacy L1 coverage remains separately owned by its existing Python tests/map.
- Shared agents, reference models, scoreboard/checkers and coverage collectors are not duplicated.
- Related integrated bins are sampled only by the integrated subsystem regression; they are not credited to this block bench. Missing scenarios remain gaps, and this directory refactor does not claim new coverage closure.
