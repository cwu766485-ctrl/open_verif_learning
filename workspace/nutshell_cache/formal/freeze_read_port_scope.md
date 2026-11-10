# Read-port compositional proof boundary

`freeze_read_port.sby` instantiates actual `SharedLineEngine` unchanged. The
harness models the L2 read busy/beat recurrence from
`SharedL2DirectoryArray.sv` (read acceptance and beat7 retirement), and the
routing equations from `CoherentCacheSubsystem.sv` (`route_grant_ready`,
`issue_l2_line_read`, `route_l2_line_data_ready`, memory write producer).
Tags/data are abstract; hit is arbitrary. All other engine inputs, including
malformed memory/snoop responses and reset after initialization, are symbolic.
Two initial reset edges initialize the actual FSM. No protocol assumptions.

Assertions, including induction lemmas: valid engine encoding; busy owned only
by victim read/write, grant stream or fail-stop; write beat agreement; victim
request starts at beat0; no ENGINE_GRANT_READ; no idle+busy; accepted data grant
never coincides with read busy. Reset clears the modeled reader and actual
engine. These are guarantees of the composition, not assumptions.

This proves the stated control composition inductively. It is not a full
subsystem elaboration proof, nor proof of Context capacity, tag/data integrity,
AXI adapter correctness or arbitrary external producer behavior. The recurrence
and routing correspondence require independent review; no automatic per-point
exclusion follows. Main runtime assertions independently check real routing.

Initial exploration with independent write producer Beat/Last admitted an
abstract counterexample: it could terminate engine streaming before the L2
reader finished. Matching the real shared beat/ready wires removes that
abstraction error. Counterexample retained under final_freeze/formal_exploration.
Induction additionally requires asserted busy ownership and beat0/beat agreement
lemmas; none are assumptions restricting accepted requests or malformed inputs.
