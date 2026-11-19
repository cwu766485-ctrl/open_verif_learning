# MesiL1MissResponseOrder Block Verification

This unit stores completed miss response metadata by internal MSHR tag and
only presents the oldest reserved miss to the untagged CPU response interface.
The existing Hit-under-Miss resident-read bypass remains outside this queue.

The block is currently an independently tested integration primitive. It is
not yet connected to `MesiL1Controller` or `DualL1MesiCluster`, so it does not
increase real CPU miss concurrency.

Run with `make coherence_l1_miss_response_order`.
