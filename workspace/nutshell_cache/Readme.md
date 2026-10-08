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

Run these commands from Ubuntu/WSL. The Makefile sources
`../../.tooling/env.sh`, which selects the project-local virtualenv containing
Picker, Toffee, pytest and Verilator helpers. Running the system `python3`
directly can produce `No module named pytest` even when the project toolchain is
installed.

The maintained RTL source is under `rtl/`. The active verification
environment is under `dv/`; `src/` and `test/` are legacy migration sources.
The regression contains 35 passing tests: 16 Toffee/Verilator simulation
scenarios and 19 Python unit tests. CI runs eight fixed random seeds (512
operations total), checks all 20 planned functional coverage goals, and gates
maintained-RTL line coverage against documented waivers. The latest measured
results and limitations are in `dv/README.md`.

The verification target is an open-toolchain DV flow based on Python/Toffee,
pytest, Picker, and Verilator, without a dependency on a commercial simulator.
UVM is not the benchmark for this project. It remains an educational and
pre-signoff environment rather than commercial sign-off equivalence; the
current coverage numbers and closure gaps are documented in `dv/README.md`.

The architecture and verification plan are documented in
`docs/cache_spec_and_verification_plan.md`.

This project verifies Verilog directly. Chisel is not required to regenerate
the DUT or run the regression.
