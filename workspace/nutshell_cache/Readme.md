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
make test         # Run the Python/Toffee regression
make report       # Run tests and generate reports/coverage
make clean        # Remove generated simulator artifacts
make doctor       # Check the project-local WSL Python/EDA toolchain
```

Run these commands from Ubuntu/WSL. The Makefile sources `scripts/env.sh`,
which activates the repository-local virtualenv plus the pinned Picker and SBY
installations under `.tooling/`. Running the system `python3` directly can
produce `No module named pytest` even when the project toolchain is installed.

The maintained RTL source is under `rtl/`. The active verification
environment is under `dv/`; `src/` and `test/` are legacy migration sources.
The current regression passes 39/39 pytest cases and closes 37/37 functional
coverage goals. The local run covers six fixed seeds (384 randomized
operations); GitHub Actions uses eight fixed seeds (512 operations) on a clean
Ubuntu runner. Maintained-RTL line coverage is 98.0% raw (845/862), or 100%
(845/845) after reviewed waivers; all-source coverage including generated DUT
wrappers is 95.1% (1423/1496). Formal assumptions, limitations and the CI link
are documented in `dv/README.md` and `formal/README.md`.

The verification target is an open-toolchain DV flow based on Python/Toffee,
pytest, Picker, and Verilator, without a dependency on a commercial simulator.
UVM is not the benchmark for this project. It remains an educational and
pre-signoff environment rather than commercial sign-off equivalence; the
current coverage numbers and closure gaps are documented in `dv/README.md`.

The architecture and verification plan are documented in
`docs/cache_spec_and_verification_plan.md`.

This project verifies Verilog directly. Chisel is not required to regenerate
the DUT or run the regression.

The optional PDF summary can be regenerated with `python -m pip install -r
report/requirements.txt` followed by `python report/build_report_pdf.py`.
