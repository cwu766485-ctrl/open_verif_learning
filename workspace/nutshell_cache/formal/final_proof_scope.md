# Final protocol proof scope and release blockers

No product RTL changes, new architecture, occupancy assumptions, or waivers.

## A: Context2/3

`final_context_reachability.sby` attempts the actual complete Main subsystem,
including DualL1MesiCluster (replacement Put bypass), actual arbiter and four
actual Directory controllers. Both cover statements inspect actual allocation
bits. No assumptions cap occupancy. The frontend fails on production L2 reset
array blocking/nonblocking assignments and loop unroll. This is TOOL_LIMITED,
not cover failure and not unreachability. No legal witness was obtained; no
synthetic directed test is claimed. Inputs are unconstrained in this exploratory
harness; any future witness must be checked for CPU/memory source legality
before conversion to a directed test. Integrated capacity remains a blocker.

## B: read control

`extract_final_l2_read_control.py --check` verifies the checked-in control slice
against current actual L2 source. It retains the read acceptance priority,
hit-dependent busy, beat0 initialization, stalled beat hold, beat7 retirement
and reset, checking actual output/reset statements. Removed set/way assignments
only select data; hit is symbolic. `final_read_port` composes the slice with
actual SharedLineEngine and explicit Main routing. Inductive PASS is for that
composition. Main routing: grant ready requires idle and no transfer offer for
data-bearing grants; grant and victim reads share the port; streaming ready is
sink ready or write producer ready. Independent extraction/routing review is
still required. There is no full-top equivalence certificate and no approved
PROVEN_UNREACHABLE point disposition.

## C: remaining producers

`final_refill_producer`: actual production 4-entry bank. Only assumption:
allocation occurs when a free entry is offered (caller obligation, not an
asserted fact about Main). Responses including wrong IDs/beat/last/error remain
arbitrary. Assert matching ID/active slot, malformed input detection, allocation
initialization, full rising only on matched successful beat7, writer payload
control stability under stall, and reset clearing. Asserted full/valid/written
and writer ownership induction lemmas are guarantees, not assumptions.
No data integrity, integrated caller proof, epoch tag or liveness claim.

`final_axi_local`: actual default 4-slot AXI adapter, no protocol assumptions.
Assert response ID matches incoming AXI ID and active/issued slot, malformed
read response is terminal error, successful read Last matches beat7, BRESP error
is preserved, WLAST matches output count7, reset clears slots and outputs.
These local inductive properties do not prove outstanding queue accounting or
end-to-end producer correctness.

`final_axi_producer_bmc`: broader AR/AW/W and line response stability properties,
bounded only. Environment assumes only stalled AXI R/B valid/payload stability;
no legal ID/Last/response/latency assumptions. The same broader property set in
`final_axi_producer` has unsuccessful induction/timeout; retain UNKNOWN and
induction trace. Do not interpret induction counterexample as a reachable bug.

Reset clears local valid storage, but interface IDs contain no reset epoch.
An old external response after reallocation of the same ID cannot be recognized
as old by these interfaces. A system reset/drain contract is required for an
end-to-end no-old-response guarantee; no hidden flush assumption was added.

All coverage mappings are scope references with exact IDs and hashes, not
automatic cross-top proof transfer or exclusions. Existing BRESP/Retry tests
are reused by full regression, not reimplemented. Both release decisions remain
OPEN until all declared blocking risks are verified or independently disposed.
