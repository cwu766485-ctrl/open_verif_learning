# Formal verification gates and artifacts

Run `make formal` to execute the maintained formal gate:

| Target | Tool | Scope |
| --- | --- | --- |
| `replacement_selector.sby` | SymbiYosys/Yosys | LFSR recurrence and nonzero reset-state properties |
| `cache_way_selector.sby` | SymbiYosys/Yosys | One-hot replacement/refill selection under the documented unique-tag invariant |
| `cache_stage2_stability.sby` | SymbiYosys/Yosys | Stage2 request-payload stability during backpressure |
| `cache_stage3_response_lifecycle.ys` | Yosys SAT | 8-cycle bounded response, reset, byte-mask, refill-merge, and selected writeback-word properties |
| `cache_metadata_invariant.sby` | SymbiYosys/Yosys | K-inductive no-duplicate-valid-tag invariant under the metadata write contract |
| `cache_metadata_stage3.ys` | Yosys SAT | 12-cycle check that real Stage3 metadata writes satisfy the model contract |
| `cache_stage3_array.ys` | Yosys SAT | 12-cycle check against a one-set, four-way, eight-beat abstract data line and memory |
| `cache_metadata_reachability.sby` | SymbiYosys/Yosys cover | Refill and hit metadata-update reachability |
| `cache_stage3_reset_cover.sby` | SymbiYosys/Yosys cover | A memory request remains active when reset arrives mid-transaction |
| `cache_stage3_stall_cover.sby` | SymbiYosys/Yosys cover | A valid hit response is reachable while ready is low |
| `cache_stage3_refill_cover.sby` | SymbiYosys/Yosys cover | The final clean-refill beat is reachable |
| `cache_stage3_dirty_writeback_cover.sby` | SymbiYosys/Yosys cover | The final dirty-writeback beat is reachable |
| `formal/mutations/run.py` | Yosys SAT | Four planned RTL mutations must each produce a counterexample |

`make formal` runs all listed jobs. Logs and cover traces are generated under
`reports/formal/`; these outputs are ignored by Git and recreated by the target.

The coherence-specific formal gate is `make coherence_formal`. It runs the two
arbiter proofs plus the Directory, Directory MSHR bank, bounded Directory
progress, and L1 controller jobs. The Directory and L1 controller safety
harnesses use the Slang SystemVerilog frontend to elaborate the actual RTL and
run 16-step bounded safety
checks for transaction ID/address routing, legal directory metadata,
ready/valid payload stability, Snoop/refill data routing, sticky protocol
errors, and cancellation of in-flight outputs after reset. These bounded
checks complement the focused simulation tests; they are not unbounded
controller proofs or a proof of the dual-L1/L2 subsystem. The arbiters retain
their separate k-inductive/combinational proofs.

`coherence_directory_progress.sby` adds an explicit bounded completion check
for one cold `GetS`: with refill start/done, Directory write, Grant, and Grant
commit handshakes all available, it requires the Grant within 8 Directory
cycles and the commit within 9 cycles. This is a deterministic, fair
environment progress check for that transaction path. It does not establish
unbounded liveness under arbitrary traffic or fairness schedules.

The controller harnesses leave downstream ready signals unconstrained so
backpressure can occur for arbitrary cycles. Input stream payloads are assumed
to obey their ready/valid hold rule where that rule is part of the interface
contract. No fairness assumption is made, so the properties are safety checks
and do not claim eventual completion. Directory multi-target L1 invalidation
is not a possible single-request case in this two-core controller; the L2
victim path's two-sharer invalidation is checked by the subsystem-directed
`coherence_multisnoop` test.

The GitHub Actions coherence workflow uses the YosysHQ OSS CAD Suite rather
than Ubuntu's older Yosys package. This is needed because the maintained
Directory and L1 formal jobs use SystemVerilog packages and `import`.

The `assume`, `assert`, and `cover` statements are in the Verilog harnesses,
not in the mutation runner or the `.ys` scripts. For example,
`cache_metadata_invariant_harness.v` contains environment assumptions, the
one-hot and no-duplicate-tag assertions, and hit/miss cover points;
`cache_stage3_array_harness.v` contains the refill and dirty-writeback data
assertions. `mutations/run.py` changes selected RTL expressions and runs the
same Yosys assertions to check whether each injected bug is detected.

The metadata proof is compositional. The unbounded transition proof assumes
each update writes one way, a hit update writes the matching existing tag, and
a refill tag is absent from the set. `cache_metadata_stage3.ys` checks those
conditions against the real Stage3 metadata write port for 12 cycles. The
abstraction uses one set and four two-bit tags, which is sufficient to expose
duplicate-tag transitions while keeping the proof small. The separately
proven replacement-selector property covers full-set victim one-hot behavior.

The array harness models the selected line as eight indexed words derived
from a symbolic 64-bit seed (`seed XOR beat_index`) and an abstract memory line
with the same shape. It checks the selected victim word and writeback
command/address for each observed write request, checks each refill data write
against that beat's memory word, and records writes in a small shadow array.
Its 12-cycle SAT result is bounded; separate cover jobs reach the final
eight-beat dirty-writeback and clean-refill beats. The Stage3 SAT job also
checks byte-mask merging and write-miss first-beat merging for arbitrary
64-bit data and mask values.

Reset covers use a directed scenario in which Stage3 enters a memory-request
state before reset is asserted. The response/reset SAT property then checks
that the first post-reset sample has idle state and no stale response. This is
not a proof of the full cache's 128-set metadata-array reset sweep.

The mutation runner changes one RTL expression at a time: stalled response
`rdata`, a byte-mask lane, refill data bit 0, and writeback data bit 0. The
gate passes only when all four mutations create a formal counterexample.

Local exploratory runs that are not referenced by `make formal` are kept
separate under `reports/formal/experimental/`. In particular:

- `cache_stage3_response_lifecycle_boolector` ended with an SMT solver
  `BrokenPipeError`; it produced no proof result.
- `cache_top_response_lifecycle_abstracted` stopped during elaboration because
  an `SRAMTemplate` blackbox remained unresolved; it produced no proof result.

These are harness/tooling setup failures from exploratory attempts, not
counterexamples to the gated properties and not passing proofs. Do not include
them in formal pass statistics. Other non-gating experiments are archived in
the same directory without being treated as sign-off evidence.
