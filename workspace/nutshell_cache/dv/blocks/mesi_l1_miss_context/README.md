# MesiL1MissContext Block Verification

This block test instantiates two `MesiL1MissContext` instances with externally
allocated coherence transaction IDs. It verifies each context's Directory
request, grant selection, eight-beat refill association, metadata commit, and
CPU response stability under backpressure.

The test isolates the miss-context primitive. It does not verify integration
with `DualL1MesiCluster`, the per-core FIFO response arbiter, the shared L1
array, the Directory, refill MSHR bank, or four-miss system concurrency.

Run from the project root with:

```sh
make coherence_l1_miss_context
```
