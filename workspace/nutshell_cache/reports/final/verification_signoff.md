# Verification Sign-off Status

**Status: OPEN — not a release sign-off.** This file is the current coverage-closure status view; consult the per-run raw reports and CI for test results.

Python/Toffee coherence closure: functional 49/49 required bins (49 total records); cross 19/19 required bins (19 total records).
Full-system checked closure artifact: functional 53/53; cross 37/37; source SHA `3a4c720ef11ba9f6be126c97f725a78d276f8a82`.
Dataset-scoped zero-count RTL points: 869.
Approved coverage waivers: 0.
Reviewed/eligible RTL coverage: not computed; point-by-checker review is incomplete.
Final required regression status: 8/8 PASS with source fingerprint `d25006778cded048cf4f9a4e638c3725a606460537df96d7a36f239a6cce4e01`; before/after fingerprint matched for every target and current log hashes are in `reports/closure/rtl_release_regression_status.json`.
The RTL Release Gate unit tests passed 19/19. The release audit remains OPEN and exits 2 because 29,466 required Raw zero points have no accepted point-level disposition. Functional Verification Candidate evidence is separate from Reviewed RTL Code Coverage and Full Code Coverage Sign-off; code coverage remains OPEN.
Required gate summary: `coherence_verify` PASS, `coherence_full_system_verify` PASS, `coherence_hit_under_miss` PASS, `coherence_full_system_cross_closure` PASS, `coherence_full_system_stress` PASS, `coherence_coverage_audit` PASS, `coherence_full_system_evidence_gate` PASS, `coherence_full_system_replay_closure` PASS
Candidate remote CI must be checked against the published PR head; see the final verification report for the SHA-scoped GitHub Actions link. This local report generator does not query GitHub.
PPA, STA, real SRAM macro implementation, and chip-level physical implementation are excluded.
