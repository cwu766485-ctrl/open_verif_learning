# Nutshell Cache Verification Case

## Requirement
**Picker**: https://github.com/XS-MLVP/picker  
**Toffee**: https://github.com/XS-MLVP/toffee  
**Toffee-Test**: https://github.com/XS-MLVP/toffee-test

## Command
```bash
make gen_dut      # Generate the software package DUT
make split_rtl    # Split generated Cache.v into readable one-module-per-file RTL
make gen_dut_modular  # Compile the split RTL with Picker (same top-level behavior)
make test         # run test
make report       # run tests and generate Toffee + RTL coverage reports
make clean        
```

The learning-task implementation is under `src/` and `test/`.  The tests cover
reset/pipeline drain, cold-read refill followed by a hit, full and byte-masked
writes, MMIO routing, and sequential words in one cache line.  The testbench
uses a SimpleBus reference model plus separate memory and MMIO responders so
that the expected response and the selected downstream port are checked.

The architecture/specification explanation and verification plan are in
`docs/cache_spec_and_verification_plan.md`.

`rtl/Cache.v` is the original generated DUT.  `make split_rtl` creates
`rtl/modular/`, containing `CacheStage1/2/3`, array templates, arbiters and
the `Cache` top module as separate files.  This is a generated-RTL view: the
functional source of truth remains the Chisel source in `../nutshell_src`.

Reports are written to `reports/cache` (Toffee HTML) and `reports/rtl`
(Verilator/LCOV).  Generated Picker and Verilator artifacts are intentionally
kept out of the source description and can be regenerated with `make gen_dut`.
