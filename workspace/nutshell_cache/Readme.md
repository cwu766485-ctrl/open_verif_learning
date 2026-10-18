# NutShell L1 DCache RTL & Verification

This project maintains and verifies a Verilog implementation of the NutShell
L1 data cache at its SimpleBus boundary.

## Tools

- Picker: exports the Verilog DUT as a Python-accessible model.
- Verilator: compiles and simulates the RTL, with optional line coverage.
- Toffee/toffee-test: bundles, agents, reference model, fixtures and reports.
- pytest: runs the self-checking regression.

## Commands

```bash
make gen_dut      # Compile maintained rtl/ with Picker/Verilator
make test         # Run the regular Python/Toffee regression
make test_slow    # Run opt-in full-capacity and mega-random stress tests
make mega_random  # Run only the large seeded cache/MMIO random test
make benchmark   # Measure deterministic L1 DCache hit/miss and RTL cycles
make report       # Run tests and generate reports/coverage
make clean        # Remove generated simulator artifacts
make doctor       # Check the project-local WSL Python/EDA toolchain
```

Run these commands from Ubuntu/WSL. The Makefile sources `scripts/env.sh`,
which activates the repository-local virtualenv plus the pinned Picker and SBY
installations under `.tooling/`. Running the system `python3` directly can
produce `No module named pytest` even when the project toolchain is installed.

The maintained RTL source is under `rtl/`. The active verification
environment is under `dv/`, with scenarios under `tests/`; `src/` is retained
as a legacy migration source. Before the new timing and mega-random tests were
added, the recorded regression passed 39/39 pytest cases and closed 37/37
functional coverage goals. The local short-random run used seven fixed seeds
(448 operations); GitHub Actions used nine (576 operations). The new slow
mega-random test defaults to 32 seeds x 512 randomized operations, plus
read-after-write checks and directed coverage setup. Maintained-RTL line
coverage is 98.1% raw (846/862), or 100%
(846/846) after reviewed waivers; all-source coverage including generated DUT
wrappers is 95.2% (1424/1496). Formal assumptions, limitations and the CI link
are documented in `dv/README.md` and `formal/README.md`.

The verification target is an open-toolchain DV flow based on Python/Toffee,
pytest, Picker, and Verilator, without a dependency on a commercial simulator.
UVM is not the benchmark for this project. It remains an educational and
pre-signoff environment rather than commercial sign-off equivalence; the
current coverage numbers and closure gaps are documented in `dv/README.md`.

The architecture and verification plan are documented in
`docs/cache_spec_and_verification_plan.md`.

## Performance baseline

`make benchmark` runs three reproducible read traces on the maintained
Verilator RTL and writes `benchmarks/results/dcache_baseline.json`. The current
baseline and measurement boundaries are documented in
[`benchmarks/README.md`](benchmarks/README.md). These are standalone L1 DCache
RTL measurements; they do not represent full-CPU IPC, CoreMark, or a physical
clock-frequency result.

This project verifies Verilog directly. Chisel is not required to regenerate
the DUT or run the regression.

The final report source and PDF are under `reports/final/`; simulation,
coverage and formal run artifacts stay under `reports/`. Regenerate the PDF
with `python -m pip install reportlab` followed by
`python reports/final/build_report_pdf.py`.
