# Phase 4 control-path reachability study

Analysis is not independent approval. No point is excluded or waived.

* SharedLineEngine ENGINE_GRANT_READ requires an accepted data grant while
  l2_line_rd_ready is low (SharedLineEngine.sv:195–208). Top accepts data grants
  only in ENGINE_IDLE with no transfer-start offer (CoherentCacheSubsystem.sv:699).
  Its line-read request is issued in that same cycle (:748). L2 read-ready is
  exactly !line_rd_busy_q (SharedL2DirectoryArray.sv:238). The only normal busy
  interval starts on an accepted line read (:351), and ends on accepted beat7
  (:359). Grant-stream and victim-write-stream hold the engine until that last
  beat; the engine cannot accept another data grant while those states own the
  read port. This is a structural invariant candidate, not a completed integrated
  formal proof. Block backpressure already reaches ENGINE_GRANT_READ; that hit
  cannot close the Main Top point. Main Top remains OPEN pending integrated
  reachability proof or an actual legal counterexample.
* Main Directory context allocation is first-free. To allocate slot2/3 requires
  three/four simultaneous live Directory requests. The two blocking L1 CPU
  controllers normally admit at most one ownership request per core. Extra slots
  require replacement Put bypass while older contexts wait for snoops; same-set
  and same-line guards otherwise serialize allocation. Standalone four-context
  allocation/retirement is legal at the bank boundary and has independent tests;
  it is not proof of integrated slot2/3 reachability. Main slot2/3 remain OPEN.
* Directory retry (DirectoryController.sv:463–483) requires the observed owner
  to respond ACK/INV_ACK instead of DATA after its replacement Put has made L2
  authoritative. A timing sweep targets a dirty owner's replacement concurrently
  with the peer's GetS. DUT states/handshakes are observed, never forced. The
  scoreboard models Put removal and absent-line SnoopRead without inventing a
  Shared copy. Final data and both L1/Directory MESI states are checked.
* Main Snoop Tag Miss (MesiL1Controller.sv:365) likewise requires a snoop snapshot
  that outlives the target's removal. A normal coherent owner/sharer snoop hits;
  direct CPU traffic to unrelated absent lines does not create a directory snoop.
* Main malformed beat/Last/ID and illegal metadata controls cannot be claimed
  unreachable merely because producers are internal. Existing Block fault tests
  verify selected defensive responses; integrated assumptions/producer invariants
  still need proofs and per-point mapping. They remain OPEN.
