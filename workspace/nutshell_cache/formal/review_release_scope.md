# Final release review scope

No external independent approver participated. Automated/source review is not
independent approval. No waiver, code deletion or full-top unreachable approval.

## Resource extraction

Generator retains actual Main, cluster, both actual L1 control/snoop FSMs,
replacement FSM and Put bypass, actual arbiter and actual Directory bank.
Only two array module bodies become nondeterministic output cutpoints, set
explicitly by Yosys setundef -undriven -anyseq. Original port headers and source
hashes are recorded. No occupancy assumption. This is an overapproximation,
not equivalent data/cache behavior: any abstract cover witness must be replayed
against real metadata/streams. TIMEOUT is OPEN, not proven unreachable.

## Read slice audit

Global nonblocking write-site checks now verify busy/beat have no additional
writers outside the extraction. Retained acceptance, hit, reset, stall and beat7
control use the actual source; set/way choose only payload. Actual Main routing
and engine grant ownership remain the stated compositional boundary. This is
an author/tool audit only; independent review is PENDING. No abstract proof
point is automatically marked unreachable.

## Refill caller

review_refill_caller instantiates actual production four-entry bank, retaining
previous bank assertions, but replaces alloc-free assumption with the Main
admission equation: symbolic caller eligibility AND actual alloc_found, reset
gated. Main's route_memory_channels explicitly gates mem_rd_req_valid by
mem_mshr_alloc_found; allocation additionally requires engine MEM_REQ and req
handshake. This discharges free-slot admission for that combinational caller
boundary without occupancy/protocol assumptions. Main engine/context identity,
data correctness and other producer invariants remain separate obligations.

## AXI decomposition

review_axi_{ar,aw,w,read,response} split prior channel stability property sets,
actual production four-slot adapter, same local ID/error/reset guarantees.
Only AXI R/B source stalled valid/payload stability assumptions; no legal ID,
response code, Last or latency assumptions. Depth8 k-induction attempts have
60-second timeout; distinguish UNKNOWN induction and timeout from reachable
failure. FIFO queue ownership invariants may still be required; no assumptions
are added to conceal these gaps. Scope of prior local inductive and bounded
checks is preserved. External shared reset/drain contract remains docs/cache.md.
