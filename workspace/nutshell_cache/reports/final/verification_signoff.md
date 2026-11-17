# Verification Sign-off Status

**Status: OPEN — not a release sign-off.** This file is the current coverage-closure status view; consult the per-run raw reports and CI for test results.

Python/Toffee coherence closure: functional 49/49 required bins (49 total records); cross 19/19 required bins (19 total records).
Full-system checked closure artifact: functional 53/53; cross 37/37; source SHA `4c83f12d1a5302a5146c4816608ed330fd71458f`.
Dataset-scoped zero-count RTL points: 863.
Approved coverage waivers: 0.
Reviewed/eligible RTL coverage: not computed; point-by-checker review is incomplete.
Final full regression status: OPEN.
Current source fingerprint: `764db6959c66632e8f882699d2bda2973e69268f910e968bb4a28c6fa9eeb5f5`; all 8/8 required regression targets have PASS exit status and verified log hashes. Regression status: PASS; RTL code coverage release gate remains OPEN. Functional Verification Candidate evidence is separate from Reviewed RTL Code Coverage and Full Code Coverage Sign-off; code coverage remains OPEN.
Required gate summary: `coherence_verify` PASS, `coherence_full_system_verify` PASS, `coherence_hit_under_miss` PASS, `coherence_full_system_cross_closure` PASS, `coherence_full_system_stress` PASS, `coherence_coverage_audit` PASS, `coherence_full_system_evidence_gate` PASS, `coherence_full_system_replay_closure` PASS
Candidate remote CI must be checked against the published PR head; see the final verification report for the SHA-scoped GitHub Actions link. This local report generator does not query GitHub.
PPA, STA, real SRAM macro implementation, and chip-level physical implementation are excluded.
