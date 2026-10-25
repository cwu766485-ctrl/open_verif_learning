# Tests

Python/Toffee pytest cases for the original single-L1 cache are under `l1/`;
the first two-core MESI subsystem test is under `coherence/`. Verification
infrastructure unit tests are under `unit/`. SystemVerilog module and
subsystem benches under `l1/rtl`, `directory/rtl`, `l2/rtl`, `axi/rtl`,
`coherence/rtl`, and `subsystem/rtl` remain migration baselines while their
scenarios move into Python. Run the new Picker/Toffee subsystem test with
`make coherence_python_test`; build and run individual SV baselines through
their dedicated Make targets. Retire an SV test only after its Python
replacement covers the same protocol behavior and checks.
