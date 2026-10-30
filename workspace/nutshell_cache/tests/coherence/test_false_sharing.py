"""Test False Sharing MESI subsystem tests."""

from .support import *


@case
async def test_python_false_sharing_ab(coherent_env):
    """Compare two cores writing distinct words in one line vs separate lines."""
    rows = []
    base = 0x0320_0000
    rounds = 16
    dut, memory, perf = await coherent_env(
        response_delay=3,
        backpressure_periods={"read_req": 5},
        response_gap_periods={"read_data": 4},
    )

    async def run_case(name, second_addr):
        if rows:
            dut.reset.value = 1
            await ClockCycles(dut, 3)
            dut.reset.value = 0
            await ClockCycles(dut, 1)
        cpu = DualCoreCpuDriver(dut)
        model = CoherenceScoreboard()
        model.track_l1_replacement = False
        case_base = base + (0x1000 if name == "different_64B_lines" else 0)
        first_addr = case_base
        second_addr = case_base + (second_addr - base)
        first_line, second_line = first_addr & ~0x3F, second_addr & ~0x3F
        for line in {first_line, second_line}:
            memory.lines[line] = [0x9000_0000_0000_0000 + beat
                                  for beat in range(8)]
        model.seed_word(first_addr, memory.lines[first_line][0])
        model.seed_word(second_addr, memory.lines[second_line][(second_addr >> 3) & 7])

        # Warm both participants into the intended starting state: S/S for a
        # shared line, E/E on distinct lines. Setup is excluded from the window.
        for core, addr in ((0, first_addr), (1, second_addr)):
            value = await _model_access(cpu, model, memory.snoop_data, core, addr)
            assert value == model.word(addr)

        before_perf = perf.snapshot()
        before_cycles = cpu.cycle
        before_snoops = len(memory.snoop_data.snoops)
        before_requests = len(memory.snoop_data.directory_requests)
        before_mem_reads = len(memory.read_requests)
        before_mem_writes = len(memory.write_responses)
        latency_start = (len(cpu.latencies[0]), len(cpu.latencies[1]))
        expected = [0, 0]
        for index in range(rounds):
            expected[0] = 0xA000_0000_0000_0000 | (index << 8) | 0x10
            expected[1] = 0xB000_0000_0000_0000 | (index << 8) | 0x20
            await _model_access(cpu, model, memory.snoop_data, 0, first_addr,
                                write=True, data=expected[0],
                                response_stall_cycles=int(index % 5 == 0))
            await _model_access(cpu, model, memory.snoop_data, 1, second_addr,
                                write=True, data=expected[1],
                                response_stall_cycles=int(index % 7 == 0))

        after_perf = perf.snapshot()
        cycles = cpu.cycle - before_cycles
        samples = (cpu.latencies[0][latency_start[0]:] +
                   cpu.latencies[1][latency_start[1]:])
        requests = memory.snoop_data.directory_requests[before_requests:]
        snoops = memory.snoop_data.snoops[before_snoops:]
        mem_read_lines = len(memory.read_requests) - before_mem_reads
        mem_write_lines = len(memory.write_responses) - before_mem_writes
        getm = sum(item["opcode"] == 0b001 for item in requests)
        upgrade = sum(item["opcode"] == 0b010 for item in requests)
        hit0 = after_perf["l1_hit_core0"] - before_perf["l1_hit_core0"]
        hit1 = after_perf["l1_hit_core1"] - before_perf["l1_hit_core1"]
        miss0 = after_perf["l1_miss_core0"] - before_perf["l1_miss_core0"]
        miss1 = after_perf["l1_miss_core1"] - before_perf["l1_miss_core1"]
        l2hit = after_perf["l2_refill_hit"] - before_perf["l2_refill_hit"]
        l2miss = after_perf["l2_refill_miss"] - before_perf["l2_refill_miss"]

        # Verify final distinct words after measuring; these reads are outside
        # the A/B performance window.
        got0 = await _model_access(cpu, model, memory.snoop_data, 0, first_addr)
        got1 = await _model_access(cpu, model, memory.snoop_data, 1, second_addr)
        assert (got0, got1) == tuple(expected)
        for addr in {first_addr, second_addr}:
            memory.snoop_data.assert_directory_matches(model, addr)
        assert int(dut.protocol_error.value) == 0
        return {
            "case": name,
            "line_addresses": [first_line, second_line],
            "writes": rounds * 2,
            "window_cycles": cycles,
            "operations_per_cycle": (rounds * 2 / cycles if cycles else None),
            "mean_latency_cycles": (sum(samples) / len(samples) if samples else None),
            "p95_latency_cycles": _p95(samples),
            "l1_hits": hit0 + hit1,
            "l1_misses": miss0 + miss1,
            "l1_hit_rate": _rate(hit0 + hit1, hit0 + hit1 + miss0 + miss1),
            "l1_miss_rate": _rate(miss0 + miss1, hit0 + hit1 + miss0 + miss1),
            "l2_refill_hits": l2hit,
            "l2_refill_misses": l2miss,
            "l2_hit_rate": _rate(l2hit, l2hit + l2miss),
            "l2_miss_rate": _rate(l2miss, l2hit + l2miss),
            "memory_read_lines": mem_read_lines,
            "memory_write_lines": mem_write_lines,
            "read_bandwidth_bytes_per_cycle": (
                mem_read_lines * 64 / cycles if cycles else None
            ),
            "write_bandwidth_bytes_per_cycle": (
                mem_write_lines * 64 / cycles if cycles else None
            ),
            "total_bandwidth_bytes_per_cycle": (
                (mem_read_lines + mem_write_lines) * 64 / cycles
                if cycles else None
            ),
            "snoops": len(snoops),
            "getm_requests": getm,
            "upgrade_requests": upgrade,
            "final_values": [got0, got1],
        }

    same = await run_case("same_64B_line_different_words", base + 8)
    separate = await run_case("different_64B_lines", base + 64)
    assert same["writes"] == separate["writes"]
    assert same["final_values"] == separate["final_values"]
    assert same["snoops"] > separate["snoops"]
    assert same["getm_requests"] + same["upgrade_requests"] > 0
    assert separate["getm_requests"] + separate["upgrade_requests"] == 0
    rows.extend((same, separate))
    artifact = {
        "schema_version": 1,
        "benchmark": "false_sharing_ab",
        "seed": "deterministic",
        "rounds_per_core": rounds,
        "memory_response_delay_cycles": 3,
        "measurement_units": "Verilator RTL simulation cycles; not silicon PPA",
        "cases": rows,
    }
    result_path = Path("reports/coherence/false_sharing_ab.json")
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    PYTHON_COVERAGE.sample_external("false_sharing_same_line")
    PYTHON_COVERAGE.sample_external("false_sharing_separate_lines")
    PYTHON_COVERAGE.sample_external("false_sharing_data_checked")
    PYTHON_COVERAGE.sample_interleaving("false_sharing_same_line_ping_pong")
    _record_model(CoherenceScoreboard())
