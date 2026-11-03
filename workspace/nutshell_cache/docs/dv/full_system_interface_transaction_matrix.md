# Full-System Interface and Transaction Matrix

| Interface | Producer → Consumer | Acceptance / completion | Backpressure | Reset behavior modeled in this slice | Error boundary |
| --- | --- | --- | --- | --- | --- |
| CPU lane 0/1 | CPU Agent → subsystem; subsystem → CPU Agent | Request and response each require their own `valid && ready`; response matching uses lane/address/write | Independent lane request delay and response ready through the driver | Reset tests cancel delayed AXI/MMIO calls, clear active requests, and check no stale response | CPU-visible fail-stop is checked for AXI RRESP error; other error recovery remains open |
| AXI AR/R | Adapter → backing-memory slave | AR handshake creates an ID context; eight R beats complete at accepted `RLAST` | AR READY is stalled by the slave; R response pacing can insert source-side `RVALID` gaps. `CoherentCacheAxiSubsystem` holds `RREADY` high outside reset, so receiver-side R backpressure is not reachable at this top and remains an Adapter Block test. | AXI agent clears active contexts when reset is observed; memory contents persist | Integrated RRESP fail-stop is tested; other error/recovery combinations remain open |
| AXI AW/W/B | Adapter → backing-memory slave | AW allocates a write; W is consumed in AW order because AXI4 has no WID; B retires the matching ID after eight accepted beats | AW/W READY and B production/consumer READY are independently scheduled | Outstanding AW/W/B contexts are cleared on reset; full system cancellation checker remains planned | Optional BRESP error injection is present in agent configuration; integrated recovery is not yet closed |
| MMIO request/response | Subsystem → MMIO Agent | Request handshake, then a single untagged response handshake | Request READY delay and response-valid delay / response READY stall are modeled | Integration test cancels a delayed response on reset and checks no stale completion | Current interface has no error response field; do not invent one |
| APB3 | APB Agent → CSR | Setup (`PSEL && !PENABLE`), access (`PSEL && PENABLE`), completion at `PREADY` | Bounded wait for `PREADY` | APB reset during access and full CSR reset semantics need dedicated tests | Read-only write and unmapped address return `PSLVERR`; `PWDATA` is absent from product interface |

## AXI transaction checks

- AR/AW must be aligned 64-byte incrementing bursts with `LEN=7`, `SIZE=3`.
- The burst must not cross a 4 KiB boundary.
- Read IDs remain unique until the final beat retires; responses can interleave
  by ID while each ID's beat order remains monotonic.
- W beats are never interleaved across AW transactions and `WLAST` is asserted
  only on beat seven.
- R/B payloads are retained while the corresponding READY is low.
- Backing-memory updates merge accepted WSTRB lanes, allowing later reads to
  observe writes after writeback.

These checks apply to the new Python/Toffee integrated-top agent. Existing
adapter-only AXI regression remains a separate checker and scope.
