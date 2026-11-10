# NutShell Cache Phase 4 Closure

**Code Coverage Decision: OPEN.** No unreachable/waiver exclusion has independent approval. Functional Verification Candidate is a separate, limited scope requiring the current complete regression, checked functional evidence, and published CI; it cannot establish Full Code Coverage Sign-off.

Source under test: `69f9fb4615717b9d9b096d9e11262438522cd960`. Baseline PR/source: `461cc1e053d4ddfadc2a6b8a5e71e72a889c2e20`. Report commit is the commit containing this file, distinct from the source commit. `phase4/source_identity.json` records the source fingerprint. PR: https://github.com/cwu766485-ctrl/open_verif_learning/pull/1.

## Verification increment

* Main Subsystem CPU-port timing sweep overlaps a dirty owner's replacement with peer GetS at offsets0..9. Both requests are accepted, response backpressure retains completion evidence, the checker compares dirty data and all eight words/MESI/directory state, and a mandatory precondition check requires an actual owner-missing retry. No internal state force.
* The existing reference model incorrectly created Shared state when a SnoopRead targeted a copy already removed by Put. It now preserves Invalid based on its own event-derived MESI model, without using DUT lookup state to predict outcomes. Both CPU operations are predicted before the global checker compares concurrently completed responses.
* Directory Block adds both-requester shared GetS, self-owner GetM with snoop/refill, sole-sharer Upgrade/PutS, and acknowledged stale PutS/PutE with explicit metadata/grant expectations. Some are valid bank-boundary recovery inputs; they are not assumed ordinary CPU-generated traffic.
* MSHR Block locks write and grant offers from Context1/2/3 while Context0 becomes a competing eligible producer, verifies full payload, and checks all allocated contexts retire. This does not transfer Block coverage into Main.
* Report generation now consumes current fingerprint-bound required regression records and checks exit status plus actual log hashes. Missing, changed or stale evidence yields OPEN. The old legacy status-file dependency no longer causes UNKNOWN against valid current PASS evidence.

## Formal boundaries

| Configuration | Result/scope | Assumptions |
| --- | --- | --- |
| coherence_directory_unconstrained | Encoding invariant, inductive proof; current final rerun required | Two initial reset edges; all ports otherwise unconstrained |
| coherence_directory_transactions | Bounded safety, depth24; one metadata/grant per transaction, completion after grant, coherent metadata, reset cancellation | Same initialization; no interface assumptions |
| coherence_directory_transactions_induction | UNKNOWN: base case passed; induction failed | Same; no unreachable conclusion |
| coherence_directory_mshr_bank | Bounded safety, depth12; per-slot accept/retire accounting, reset clear, existing arbitration properties | Existing legal opcode/metadata constraints, initial reset |

Initial exploration logs and induction trace are in `phase4/formal_exploration.json`; the optional induction configuration reproduces UNKNOWN. These properties do not establish system liveness, all legal permission paths, all reachable FSM arcs, or integrated Snoop/refill correctness. No formal result has independent approval to exclude raw points.

Reachability study: `phase4/reachability_study.md`. Grant-read contention, Main Context2/3, malformed internal producer traffic and remaining replacement/metadata races retain OPEN obligations unless actual same-top coverage or adequate reviewed proof is supplied.

## Review and release scope

The 28,759 baseline toggle zeros retain their individual IDs. Address/Tag, Data, Byte Mask, Transaction/Context ID, FSM Encoding and unclassified signal queues are review categories, not constant or unreachable findings. New control scenarios may naturally change toggle counts. All remaining bits require stimulus or structural/reachability evidence; no low-activity exclusion.

Required denominators, functional/cross bins and RTL architecture are unchanged. Approved Unreachable/Waiver list: empty. Independent approver: none. Reviewed Eligible Coverage is not calculated. Full Code Coverage Sign-off: OPEN.

Limited Functional Verification Candidate proposed for review: RTL v1.1 coherent two-core cache and existing CPU/MMIO/APB/AXI four-agent integration under the checked 53 functional/35 cross plan, existing 280-seed campaign, reset/error/replay tests and explicitly bounded formal results. It excludes any claim that all code/control/toggle obligations are closed, integrated contexts2/3 are reachable, or the whole protocol is inductively proved. Candidate recommendation remains dependent on final current-source evidence below.

## Final results

All eight required regression targets PASS on the source SHA above, with source fingerprints and verified log hashes. Functional53/53, Cross35/35, Stress280/280. Replay1/1; Cross closure21/21; Hit-under-Miss3/3. Gate unit tests19/19; related unit checks22/22.

| Dataset | Metric | Before | After | Delta |
| --- | --- | ---: | ---: | ---: |
| axi_subsystem | line | 901/1068 | 901/1068 | +0 |
| axi_subsystem | branch | 509/632 | 509/632 | +0 |
| axi_subsystem | toggle | 15623/32332 | 15623/32332 | +0 |
| axi_subsystem | fsm_state | 30/54 | 30/54 | +0 |
| axi_subsystem | fsm_arc | 4/48 | 4/48 | +0 |
| bus_blocks | line | 67/68 | 67/68 | +0 |
| bus_blocks | branch | 70/76 | 70/76 | +0 |
| bus_blocks | toggle | 1100/2450 | 1100/2450 | +0 |
| bus_blocks | fsm_state | 0/0 | 0/0 | +0 |
| bus_blocks | fsm_arc | 0/0 | 0/0 | +0 |
| directory_controller | line | 149/182 | 160/182 | +11 |
| directory_controller | branch | 33/42 | 36/42 | +3 |
| directory_controller | toggle | 255/612 | 258/612 | +3 |
| directory_controller | fsm_state | 10/10 | 10/10 | +0 |
| directory_controller | fsm_arc | 3/9 | 3/9 | +0 |
| directory_mshr_bank | line | 167/286 | 167/286 | +0 |
| directory_mshr_bank | branch | 100/128 | 100/128 | +0 |
| directory_mshr_bank | toggle | 1189/2904 | 1249/2904 | +60 |
| directory_mshr_bank | fsm_state | 31/40 | 31/40 | +0 |
| directory_mshr_bank | fsm_arc | 11/36 | 11/36 | +0 |
| main_subsystem | line | 850/992 | 864/992 | +14 |
| main_subsystem | branch | 468/556 | 473/556 | +5 |
| main_subsystem | toggle | 21887/27474 | 21923/27474 | +36 |
| main_subsystem | fsm_state | 30/54 | 30/54 | +0 |
| main_subsystem | fsm_arc | 13/48 | 13/48 | +0 |
| mesi_l1_controller | line | 107/132 | 107/132 | +0 |
| mesi_l1_controller | branch | 41/46 | 41/46 | +0 |
| mesi_l1_controller | toggle | 688/1804 | 688/1804 | +0 |
| mesi_l1_controller | fsm_state | 7/7 | 7/7 | +0 |
| mesi_l1_controller | fsm_arc | 3/6 | 3/6 | +0 |
| shared_l2_directory_array | line | 75/79 | 75/79 | +0 |
| shared_l2_directory_array | branch | 65/74 | 65/74 | +0 |
| shared_l2_directory_array | toggle | 197/1778 | 197/1778 | +0 |
| shared_l2_directory_array | fsm_state | 0/0 | 0/0 | +0 |
| shared_l2_directory_array | fsm_arc | 0/0 | 0/0 | +0 |
| shared_line_engine | line | 101/104 | 101/104 | +0 |
| shared_line_engine | branch | 44/52 | 44/52 | +0 |
| shared_line_engine | toggle | 304/648 | 304/648 | +0 |
| shared_line_engine | fsm_state | 0/0 | 0/0 | +0 |
| shared_line_engine | fsm_arc | 0/0 | 0/0 | +0 |

Exact Point ID diff: `phase4/point_diff.csv.gz`;132 NEW_RAW_HIT,74699 unchanged status,0 lost hits,0 added/removed IDs. Newly hit Line25,Branch8,Toggle99,FSM State0,FSM Arc0. Main increase:14 Line,5 Branch,36 Toggle. Main new paths include Directory retry lines463/466/471–483, Snoop Tag Miss lines365–368, same-line Put bypass and replacement conflict branches.

Raw points74831; hits45132→45264; all 45264 hits machine-attested; unattested0; manifest errors0. Zero points29699→29567; non-toggle940→907; toggle28759→28660. Remaining by metric: {'branch': 268, 'fsm_arc': 113, 'fsm_state': 57, 'line': 469, 'toggle': 28660}.

Toggle review queues (all OPEN): {'UNCLASSIFIED': 3283, 'ADDRESS_TAG': 20648, 'DATA': 3717, 'TRANSACTION_CONTEXT_ID': 736, 'BYTE_MASK': 176, 'FSM_ENCODING': 100}. Baseline individual IDs remain mapped in the diff; no denominator change or exclusion.

`coherence_release_gate`: OPEN, make exit2 (gate executable exit1),29567 required open findings. No additional identity/hash/regression findings. Approved Unreachable/Waiver list remains empty. Reviewed Eligible Coverage not calculated; Full Code Coverage Sign-off OPEN.

Current `verification_signoff.md` now reports regression8/8 PASS using the live fingerprint/log contract; code sign-off separately remains OPEN. Current matrix labels its non-toggle907-row scope. Complete zero review (including28660 toggles): `phase4/zero_point_review.csv.gz`. Formal property-to-point candidates: `phase4/formal_point_mapping.csv.gz`, all OPEN; no per-point unreachable claim.

Final formal logs: `phase4/formal_final.json`; raw/line-info archives and hashes: `phase4/raw_archive.json`, `phase4/dataset_manifest.json`. Full regression logs: `reports/closure/release_runs/*.log.gz`; exit/hash records: `reports/closure/rtl_release_regression_status.json`, `rtl_release_gate_status.json`. All raw totals are dataset scoped; summed point counts are workload counts, not pooled coverage percentages.

Remaining OPEN risk: Main integrated Context2/3 allocation/retirement; SharedLineEngine Grant Read/port contention structural invariant; remaining valid Directory recovery/Put/Upgrade scenarios; L1 metadata/replacement/snoop races not covered by this GetS sweep; defensive producers and per-instance reset/error arcs; per-bit address/ID/data/toggle classification. Reachability analysis is not independent approval.

**Functional Verification Release Candidate: proposed for independent review within the limited scope above**, supported by current53/53,35/35,280/280 and eight PASS regression targets. It does not change required code coverage obligations or convert OPEN to full sign-off.

Source CI success: https://github.com/cwu766485-ctrl/open_verif_learning/actions/runs/42771057555 and https://github.com/cwu766485-ctrl/open_verif_learning/actions/runs/42771051488 (both head69f9fb4). PR #1 is open. No merge/tag. Report-only PR SHA is recorded by the final report commit, distinct from tested source.
