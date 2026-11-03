# SharedLineEngine Block Verification

The independent Verilator bench exercises the production `SharedLineEngine` through its directory, L2, snoop and memory interfaces. Scenarios include immediate and delayed grant reads, L2 refill, PutM, clean multi-sharer victim reclaim, dirty-owner data recovery/writeback, channel backpressure, reset after errors, and selected protocol fault injection.

Scenario code is split into focused include files under `tb/include/`; the top-level bench only declares signals, instantiates the DUT and sequences the named tests. Each case checks state progression, transaction/beat identity, completion and error classification. Internal state is observed for checking but never forced.

Run from the project root:

```bash
source scripts/env.sh
make COHERENCE_JOBS=2 coherence_shared_line_engine
```

See [`testplan.md`](testplan.md) for the interface map, case-to-checker mapping, current raw coverage and remaining gaps. This Block dataset is reported separately and must not be added to subsystem percentages or used to close misses in another elaboration.
