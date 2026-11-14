# L1 producer guarantee boundary

`freeze_l1_producer.sby` uses the unmodified actual MesiL1Controller and
MesiL1SnoopArbiter, production transaction width 4. Initial two reset edges,
then arbitrary inputs and arbitrary later reset. No protocol assumptions.

Independent public accepted CPU requests drive a modulo-16 ID model; accepted
snoop handshakes capture a separate ID. Assertions tie implementation storage to
this model as induction lemmas (never assumptions), then check public request,
response, refill/commit and snoop output IDs. The snoop beat/last output is
proved to forward its array input. Reset guarantees clear FSMs and no stale
request/response/commit/snoop output. k-induction PASS is limited to these
properties; it does not prove whole-system MESI, liveness, incoming array beat
legality, integrated Context capacity or AXI response matching.

Illegal FSM encodings are also checked (CPU 0..6, snoop 0..5). Malformed input
traffic remains in scope; this proof makes no claim that malformed refill
payload cannot be forwarded before fail-stop. Existing fault tests and other
producer obligations remain separate. No coverage point is automatically waived.
