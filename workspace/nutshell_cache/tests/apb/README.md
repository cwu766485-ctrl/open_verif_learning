# APB tests

The APB performance CSR is exercised together with the AXI line adapter in
`dv/blocks/bus_blocks/tb/CacheBusBlocks_tb.sv`, through
`make coherence_bus_blocks`. There is no APB-only bench; coverage is recorded
in `dv/blocks/bus_blocks/testplan.md`.
