# Tests

Python/Toffee pytest cases for the original single-L1 cache are under `l1/`;
verification infrastructure unit tests are under `unit/`. SystemVerilog
module benches are under `l1/rtl`, `directory/rtl`, `l2/rtl`, `axi/rtl`,
`coherence/rtl`, and `subsystem/rtl`; APB CSR checks currently share the AXI
bus-block bench documented in `apb/README.md`. They are built through dedicated Make
targets; pytest remains the Python regression entry point.
