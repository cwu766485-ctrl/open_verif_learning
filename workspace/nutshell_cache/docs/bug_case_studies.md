# MESI Cache Bug Case Studies

These cases record three RTL defects found during subsystem verification. Each
case follows the same chain: observable failure, root cause, RTL change, and a
regression that checks the behavior independently. Test names and coverage
mapping are in the [Testplan-to-Coverage Matrix](testplan_to_coverage_matrix.md).

## 1. Shared Directory lookup race

**Observed failure.** Concurrent misses could return or commit metadata for the
wrong cache line when a new request arrived while the shared L2 lookup port was
still serving an earlier transfer or Grant.

**Root cause.** Request context allocation and the single shared lookup address
were not admitted atomically. The Directory could capture the new request while
the L2 array still selected the previous transaction's address. The resulting
Directory snapshot and data lookup referred to different lines.

**Fix.** Gate both request `valid` and `ready` until the shared lookup port can
serve the new address. Add lookup-address checks so a stalled transaction
cannot be silently retargeted by a competing request.

**Regression evidence.** A fixed-seed dual-core replay checks the active and
incoming line addresses, returned data, Snoop beats, and committed Directory
state. `test_directory_lookup_grant_conflict_offset_sweep` varies the request
offset and conflict timing. The complete 20-seed stress regression also passes.

**Verification lesson.** A context being allocated is not evidence that its
data lookup used the same address. Check the accepted request, selected array
address, Grant and final Directory commit as one transaction.

## 2. Grant/Snoop ready-valid admission mismatch

**Observed failure.** An L1 could consume a Grant while the Directory was
backpressured and then wait forever for data that the top-level transaction
engine had not launched. A related refill/Snoop interleaving let the L1 accept
an invalidation that the Directory had not accepted, so the response could not
match an active Directory transaction.

**Root cause.** On these paths, `valid` was exposed to the L1 using a different
condition from the Directory's `ready`. The two endpoints could therefore
disagree about whether the same handshake had occurred.

**Fix.** Derive upstream `valid` and `ready` from one admission condition for
Grant and Snoop transactions. Preserve refill ownership of the shared L2 data
write port for owner-data Snoop; allow only clean invalidation to overlap the
refill stream. Add assertions that an L1-accepted Snoop is also accepted by the
Directory and that Grant data belongs to the matching transaction.

**Regression evidence.** The Grant conflict offset sweep checks returned data
and model state. `test_clean_snoop_overlaps_l2_fill_stream` exercises clean
Snoop in both core directions. Integrated AXI R-only, B-only, and R+B response
stall tests check payload stability and successful drain.

**Verification lesson.** For every ready/valid channel, observe the handshake
at both producer and consumer. Checking only that the test eventually passes
can miss a lost transaction that appears later as a timeout.

## 3. Dense same-set PutM / owner-data Snoop deadlock

**Observed failure.** A workload mapping nine lines to one L2 set and issuing
dual-core random traffic with backpressure failed on 14 of 20 seeds, reporting
Directory mismatches, protocol errors, or response timeouts.

**Root cause.** An L1 replacement `PutM` needed the shared L2 write port to
retire a dirty victim. At the same time, an owner-data Snoop waited for that
port, while the L1 replacement path could not advance until its pending Put
completed. This formed a resource and handshake wait cycle.

**Fix.** Permit the same-set `PutM` to bypass the ownership-request lock only
while the owner-data Snoop has not handshaken and no Snoop data stream is active.
Once an owner-data Snoop is accepted, it retains the shared data-port exclusion.
Same-set ownership requests remain serialized; different sets can use separate
Directory contexts.

**Regression evidence.** `coherence_dense_set_stress` first forces dirty-owner
and shared live victims, then runs 20 deterministic seeds × 200 mixed
operations. The independent checker compares data, MESI permissions, Directory
owner/sharer state, and transaction completion. The repaired configuration
passes 20/20 seeds.

**Verification lesson.** A fix for a deadlock must constrain the bypass to the
precise unaccepted-request window. Also test both sides of the handshake and
keep an accepted owner-data transfer protected from a competing writer.

## Scope

These examples demonstrate bug discovery and regression closure; they do not
claim exhaustive RTL mutation or an unbounded proof of system progress. Current
Formal evidence is component-level and bounded. The independent
[coverage-gap review](coherence_coverage_gap_review.md) lists legal recovery
paths still scheduled for the v1.1 verification backlog.
