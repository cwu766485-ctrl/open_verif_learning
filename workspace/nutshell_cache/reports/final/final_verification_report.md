# NutShell Cache v1.1 — Final Front-End DV Closure

**Functional Verification Release Decision: OPEN**  
**Full RTL Code Coverage Sign-off Decision: OPEN**

## Frozen Snapshot

- Branch: `codex/v1.1-final-dv-evidence`
- Commit: `a246f2cce3d4b706b3c0bdd60dded625ad121133`
- Verification Source Fingerprint: `e86c8380271a1531a44cbd21caac37182e5441023b4c3d6264b09436bc27a8eb`
- PR #3: OPEN to `dv-closure-phase2`; no merge or tag created.
- GitHub Actions on this exact PR head: `cache-regression` and `coherence-regression` both SUCCESS (runs `43692888994` and `43692885775`).
- Product RTL and microarchitecture were not changed.

The source fingerprint includes Python tests and verification collateral and is distinct from the Git SHA and Raw dataset fingerprints. Verilator Raw datasets use Verilator 5.053 devel (`v5.052-521-g6388139f7`), Python 3.12.3, the recorded top-specific filelists, and top-specific test sets in `rtl_coverage_dataset_manifest.json`.

## Software-Visible Checks

- Concurrent DATA/READY/ACK: 100 generations, over 800 accepted CPU transactions, READY observed before consumer DATA reads, unique request groups, request accepted while the peer response remained outstanding, byte-accurate scoreboard, and Directory/Grant/Commit/Snoop trace. Detailed cycle trace: `reports/coherence/generation_counter_concurrent_trace.json`. This is evidence for observed executions only; it does not claim RVWMO or FENCE correctness.
- Same-address dual stores: the independent history checker permits either full-word cross-core serialization, correlates CPU accept/response with Directory request/grant IDs and L1 Modified commit, and requires both later Loads to observe a legal final value.
- Same-set contention: 24 paired different-line rounds and repeated same-line ownership ping-pong; per-core accepted/completed totals (74/73), maximum request wait (<=16 cycles), response latency (<=1000 cycles), Context Allocate/Retire balance, Grant/Snoop activity and final data are checked. This is finite progress evidence under the deterministic memory agent, not unbounded fairness.
- MMIO edges: aligned accesses below `0x30000000`, at `0x30000000`, at `0x7ffffff8`, and at `0x80000000` check exact routing, masks and AXI refill addresses. Unsupported unaligned CPU behavior remains unspecified.
- L1/L2 set edges and Word0/Word7 are reused from CR11. Complementary `0xAA`/`0x55` cache masks and owner transfer are covered there; a zero byte mask has no specified CPU result and was not assigned invented behavior. APB invalid/readonly accesses already check PSLVERR. A 32-bit performance-counter wrap is not exercised because there is no counter load interface and natural wrap requires over 2^32 events. Existing tests cover AXI R error, BRESP error, reset during read/write stalls, and reset before write B completion; persistence after an externally completed B followed by reset is not claimed beyond the documented reset/drain contract.
- The four focused new/strengthened tests passed. Full-System coverage: 72 passed, 1 optional saved-trace replay skipped; checked coverage 53/53 Functional and 37/37 Cross. Full-System stress: 280/280 passed.

Eight fingerprint-bound required regression gates passed with exit 0 and verified log hashes: `coherence_verify`, `coherence_full_system_verify`, `coherence_hit_under_miss`, `coherence_full_system_cross_closure`, `coherence_full_system_stress`, `coherence_coverage_audit`, `coherence_full_system_evidence_gate`, and `coherence_full_system_replay_closure`.

## Raw RTL Coverage

Each row is an independent elaborated dataset; no cross-Top counts are combined. The `source` value is the dataset source/manifest fingerprint; `raw SHA-256` identifies its raw `.dat` file.

| Dataset / Top | Line | Branch | Toggle | FSM State | FSM Arc | Dataset source fingerprint | Raw SHA-256 |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Main / `CoherentCacheSubsystem_tb` | 864/992 | 473/556 | 21931/27474 | 30/54 | 13/48 | `0c308a374ee86d22c3c0ef7dad73d4cb5ffe70f5cfac8e0a8c38c1567fc351be` | `cf32934f7c2b5ae6def7520c2aa184f17bf1725c7ac85aa80d0ecef63ee5b4f4` |
| AXI / `CoherentCacheAxiSubsystem_tb` | 901/1068 | 509/632 | 15623/32332 | 30/54 | 4/48 | `d6a23d5abebf75f89e6f0933432d8bb8588c0e05a52d4ba3473f2a07546b6b12` | `97330f3cce65d9cf83898bd9000f3ca87598f49f952c97b83a95427804542681` |
| Directory / `DirectoryController_tb` | 178/182 | 37/42 | 260/612 | 10/10 | 3/9 | `be2e40dad76d53bbe36f56c7763fae6b2acd0b7042797c2a84ec726998e9aa72` | `e9982c1f1462cd4bda4ddd16f5f82a4632c696e81e46f6636e0684a0020182a5` |
| Directory MSHR / `DirectoryMshrBank_tb` | 167/286 | 100/128 | 1249/2904 | 31/40 | 11/36 | `016f47231fc89cf02f6b6df9d7e6ae24d83fb5e668145086f1bff723d7b30fb8` | `1badff2d1a4c11f6aa6302b4d405248ff8318e19c2a0461424f87c428d7ec39b` |
| Shared Line / `SharedLineEngine_tb` | 101/104 | 44/52 | 304/648 | N/A | N/A | `7e8c2e624de3bdc17519aaf4d64fe65525a4cfb9f6d6e08fa0095b6254e09871` | `2577449b714135d44bb4eb101d3dd26d14e7c936431dbe26af557a45c686f575` |
| L1 Controller / `MesiL1Controller_tb` | 124/132 | 43/46 | 741/1804 | 7/7 | 3/6 | `2438a31deb8ab100062c9576453904eaa6c7e26de8be34d55fb71e393e04b79a` | `b5198eb88f08edc0798126c2d00b1719c885d66ef04301a2f52d98b78237a3cd` |
| L2 Array / `SharedL2DirectoryArray_tb` | 75/79 | 65/74 | 197/1778 | N/A | N/A | `7a73dd0a41f05882360a9dd0c2b3b500ee75d015bbf033054a17f73d4812aa09` | `23bc422d613c62f41a4e8a6b834523e6a596d175bc3d3f8234be51b3c99b053c` |
| Bus / `CacheBusBlocks_tb` | 67/68 | 70/76 | 1100/2450 | N/A | N/A | `70f1267216f0a46fc41b8533ff2e59c9ebf9a10f84a001caaa72b93e00d850d1` | `4ddfd4e57fb4e5f4578a494e3729f9c19da334a252894205f6ea1c61b65653bf` |

The prior tracked dataset manifest has source fingerprint `819b8656e469947612ac43bbe740800ce09b1014cb9529e82eddb14c1ff2ae47`; its eight raw SHA-256 values match the refreshed datasets exactly. Therefore, compared with that immediately preceding manifest, every dataset has **0 newly hit IDs, 0 lost hit IDs, and 0 denominator changes**. The Python/Toffee tests do not emit compatible native RTL Raw points, so their success is not credited as RTL coverage.

There is an older compressed archive under `reports/final/rtl_coverage_raw/` whose Main dataset yields 850/992 Line, 468/556 Branch, 19996/27474 Toggle, 30/54 FSM State, and 7/48 FSM Arc. It does not match the preceding manifest's raw SHA and is not used as the Before snapshot. This archive/report inconsistency is retained for audit and must not be used to claim extra coverage.

The primary Main dataset still has 128 Line, 83 Branch, 24 FSM State, and 35 FSM Arc misses. Across eight datasets, the coverage matrix has 869 dataset-scoped zero records for Line/Branch/FSM; the Release Gate inventories 29,466 zero points including Toggle. No newly hit IDs can be attributed to the new Python tests. Every Required zero point remains OPEN; no waiver or unreachable exclusion was approved.

## Formal Boundaries

- Context 2/3 integrated reachability: TIMEOUT. The retained resource abstraction did not produce a legal integrated witness or an unreachability proof; an abstract cover witness would require replay against real arrays.
- L2 Read Control correspondence: PENDING independent review. The write-site/control-slice audit is not a full-top equivalence proof.
- AXI/Refill lifetime: the actual refill caller/admission proof and AXI response stability property have inductive PASS within their recorded boundaries; split AR/AW/W/Read induction remains UNKNOWN. A broader depth-8 check is bounded only. FIFO ownership and full Beat/Last lifetime safety remain OPEN.
- Component formal runs in `coherence_verify` passed, but do not close these integrated obligations or establish an unbounded whole-system proof.

## Release Decision

The Raw RTL Release Gate was rerun on this snapshot. It returned **exit 1**, reporting 29,466 unresolved zero-count points and related OPEN findings. Its 19 supporting unit tests passed. Functional Verification remains **OPEN** because integrated reachability, independent L2 control correspondence review, and broad AXI/Refill lifecycle proof remain unresolved; there is no recorded risk-acceptance owner, so no CONDITIONAL candidate is issued. Full RTL Code Coverage remains **OPEN**. No merge, waiver approval, branch deletion, or release tag was performed.
