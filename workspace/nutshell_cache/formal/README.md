# Formal verification gates and artifacts

Run `make formal` to execute the maintained formal gate:

| Target | Tool | Scope |
| --- | --- | --- |
| `replacement_selector.sby` | SymbiYosys/Yosys | LFSR recurrence and nonzero reset-state properties |
| `cache_way_selector.sby` | SymbiYosys/Yosys | One-hot replacement/refill selection under the documented unique-tag invariant |
| `cache_stage2_stability.sby` | SymbiYosys/Yosys | Stage2 request-payload stability during backpressure |
| `cache_stage3_response_lifecycle.ys` | Yosys SAT | 8-cycle bounded Stage3 response/reset-control checks with data arrays abstracted |

The first three SBY jobs and the bounded Stage3 SAT script are the release
gate. Their logs are generated under `reports/formal/`; these outputs are
ignored by Git and recreated by `make formal`. Assumptions and proof limits,
including the lack of an unbounded end-to-end lifecycle proof and full-cache
reset proof, are documented in `../dv/README.md`.

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
