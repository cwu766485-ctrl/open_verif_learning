`timescale 1ns/1ps

module CoherentCacheAxiSubsystem_tb;
  import coherence_protocol_pkg::*;
`include "include/signals.svh"

`include "include/axi_memory_model.svh"

`include "include/reference_model_and_cpu_tasks.svh"

`include "include/benchmark_sequence.svh"

`include "include/response_backpressure.svh"

`include "include/timeout_guard.svh"
endmodule
