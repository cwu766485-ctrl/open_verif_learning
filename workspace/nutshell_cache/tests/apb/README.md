# APB tests

The APB performance CSR is currently exercised together with the AXI line
adapter in `tests/axi/rtl/CacheBusBlocks_tb.sv`, through
`make coherence_bus_blocks`. A dedicated APB-only bench can be split out if the
CSR verification grows independently.
