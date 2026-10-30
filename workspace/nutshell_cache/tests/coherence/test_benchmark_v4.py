"""Benchmark V4 MESI subsystem tests."""

from .support import *


@pytest.mark.asyncio
@case
@pytest.mark.benchmark
@pytest.mark.benchmark_v4
async def test_coherence_benchmark_v4(coherent_env):
    """Measure cache capacity, coherence, concurrency, fairness and traffic."""
    dut, memory, perf = await coherent_env(response_delay=2)
    cpu = DualCoreCpuDriver(dut)
    rows = []

    async def reset_cache():
        dut.reset.value = 1
        await ClockCycles(dut, 4)
        dut.reset.value = 0
        await ClockCycles(dut, 1)

    async def measure(name, case_name, seed, delay, expected_ops,
                      initial_state, workload):
        memory.response_delay = delay
        counts_before = perf.snapshot()
        resources_before = perf.extended_snapshot()
        event_cursor = perf.event_snapshot()
        transaction_cursor = len(cpu.transactions)
        cpu_req_stalls_before = dict(cpu.request_stall_cycles)
        cpu_resp_stalls_before = dict(cpu.response_stall_cycles)
        memory_stalls_before = dict(memory.stalls)
        memory_gaps_before = dict(memory.response_gaps)
        read_req_before = len(memory.read_requests)
        write_req_before = len(memory.write_requests)
        read_beats_before = memory.read_beats
        write_beats_before = memory.write_beats
        await workload()
        counts_after = perf.snapshot()
        resources_after = perf.extended_snapshot()
        event_delta = perf.events_since(event_cursor)
        transactions = cpu.transactions[transaction_cursor:]
        counts = {key: counts_after[key] - counts_before[key]
                  for key in counts_before}
        completions = transactions
        requests = transactions
        directory_requests = event_delta["directory_requests"]
        cycles = counts["cycles"]
        l1_events_by_core = {0: [], 1: []}
        for event_name, classification in (("l1_hits", "hit"),
                                            ("l1_misses", "miss")):
            for item in event_delta[event_name]:
                l1_events_by_core[item["core"]].append(
                    (item["cycle"], item["addr"], item["write"], classification)
                )
        for core_events in l1_events_by_core.values():
            core_events.sort(key=lambda item: item[0])
        l1_hit_events = event_delta["l1_hits"]
        l1_miss_events = event_delta["l1_misses"]
        if len(l1_hit_events) + len(l1_miss_events) != len(completions):
            raise AssertionError(
                f"{name}/{case_name}: L1 event count does not match completed "
                f"CPU requests ({len(l1_hit_events)} hits + "
                f"{len(l1_miss_events)} misses vs {len(completions)} completions)"
            )
        l1_event_index = {0: 0, 1: 0}
        for transaction in completions:
            core = transaction["core"]
            event_index = l1_event_index[core]
            if event_index >= len(l1_events_by_core[core]):
                transaction["l1_class"] = "unknown"
                continue
            _, event_addr, event_write, classification = l1_events_by_core[core][event_index]
            l1_event_index[core] += 1
            if (event_addr != (transaction["addr"] & 0xFFFFFFC0) or
                    event_write != transaction["write"]):
                transaction["l1_class"] = "unknown"
            else:
                transaction["l1_class"] = classification
        unknown = [item for item in completions
                   if item["l1_class"] == "unknown"]
        if unknown:
            raise AssertionError(
                f"{name}/{case_name}: L1 event did not match CPU transaction "
                f"address/operation: {unknown[:4]}"
            )
        latencies = [item["latency_cycles"] for item in completions]
        if len(completions) != expected_ops:
            raise AssertionError(
                f"{name}/{case_name}: expected {expected_ops} CPU completions, "
                f"observed {len(completions)}"
            )
        hit_samples = [item["latency_cycles"] for item in completions
                       if item["l1_class"] == "hit"]
        miss_samples = [item["latency_cycles"] for item in completions
                        if item["l1_class"] == "miss"]
        read_samples = [item["latency_cycles"] for item in completions
                        if not item["write"]]
        write_samples = [item["latency_cycles"] for item in completions
                         if item["write"]]
        read_hit = sum(not item["write"] for item in l1_hit_events)
        read_miss = sum(not item["write"] for item in l1_miss_events)
        write_hit = sum(bool(item["write"]) for item in l1_hit_events)
        write_miss = sum(bool(item["write"]) for item in l1_miss_events)
        l1_hits = len(l1_hit_events)
        l1_misses = len(l1_miss_events)
        upgrades = sum(item["opcode"] == 0b010 for item in directory_requests)
        data_misses = max(0, l1_misses - upgrades)
        l2_hits = counts["l2_refill_hit"]
        l2_misses = counts["l2_refill_miss"]
        read_beats = memory.read_beats - read_beats_before
        write_beats = memory.write_beats - write_beats_before
        read_bytes = read_beats * 8
        write_bytes = write_beats * 8
        logical_bytes = sum(
            8 if not item["write"] else int(item["mask"]).bit_count()
            for item in requests
        )
        read_ops = sum(not item["write"] for item in requests)
        write_ops = len(requests) - read_ops
        by_core = {
            core: [item for item in completions if item["core"] == core]
            for core in range(2)
        }
        core_ops = {core: len(by_core[core]) for core in range(2)}
        core_throughput = {
            f"core{core}_ops_per_cycle": core_ops[core] / cycles if cycles else None
            for core in range(2)
        }
        throughput = len(completions) / cycles if cycles else None
        fairness_denominator = sum(value * value for value in core_ops.values())
        fairness = (
            (sum(core_ops.values()) ** 2) / (2 * fairness_denominator)
            if fairness_denominator else None
        )
        mshr_hist = _v4_counter_delta(
            resources_after["mshr_occupancy_histogram"],
            resources_before["mshr_occupancy_histogram"],
        )
        context_hist = _v4_counter_delta(
            resources_after["directory_context_histogram"],
            resources_before["directory_context_histogram"],
        )
        mshr_hist = {int(key): value for key, value in mshr_hist.items() if value}
        context_hist = {int(key): value for key, value in context_hist.items()
                        if value}
        mshr_cycles = sum(mshr_hist.values())
        context_cycles = sum(context_hist.values())
        mshr_peak = max(mshr_hist, default=0)
        context_peak = max(context_hist, default=0)
        stall_delta = _v4_counter_delta(
            resources_after["stall_cycles"], resources_before["stall_cycles"]
        )
        for core in range(2):
            stall_delta[f"cpu_req_core{core}"] = (
                cpu.request_stall_cycles[core] -
                cpu_req_stalls_before[core]
            )
            stall_delta[f"cpu_resp_core{core}"] = (
                cpu.response_stall_cycles[core] -
                cpu_resp_stalls_before[core]
            )
        for source, destination in (
            ("read_req", "mem_read_req"),
            ("read_data", "mem_read_data"),
            ("write_req", "mem_write_req"),
            ("write_data", "mem_write_data"),
            ("write_rsp", "mem_write_rsp"),
        ):
            observed = memory.stalls.get(source, 0) - memory_stalls_before.get(source, 0)
            stall_delta[destination] = observed
        response_gap_delta = _v4_counter_delta(
            dict(memory.response_gaps), memory_gaps_before
        )
        row = {
            "workload": name,
            "case": case_name,
            "seed": seed,
            "memory_response_latency_cycles": delay,
            "initial_cache_state": initial_state,
            "requested_ops": expected_ops,
            "completed_ops": len(completions),
            "read_ops": read_ops,
            "write_ops": write_ops,
            "window_cycles": cycles,
            "mean_latency_cycles": (sum(latencies) / len(latencies)
                                     if latencies else None),
            "amat_cycles": (sum(latencies) / len(latencies)
                            if latencies else None),
            "p95_latency_cycles": _v4_percentile(latencies, 0.95),
            "p99_latency_cycles": _v4_percentile(latencies, 0.99),
            "mean_read_latency_cycles": (sum(read_samples) / len(read_samples)
                                          if read_samples else None),
            "mean_write_latency_cycles": (sum(write_samples) / len(write_samples)
                                           if write_samples else None),
            "read_amat_cycles": (sum(read_samples) / len(read_samples)
                                 if read_samples else None),
            "write_amat_cycles": (sum(write_samples) / len(write_samples)
                                  if write_samples else None),
            "mean_hit_latency_cycles": (sum(hit_samples) / len(hit_samples)
                                         if hit_samples else None),
            "mean_miss_latency_cycles": (sum(miss_samples) / len(miss_samples)
                                          if miss_samples else None),
            "miss_penalty_cycles": (
                sum(miss_samples) / len(miss_samples) -
                sum(hit_samples) / len(hit_samples)
                if hit_samples and miss_samples else None
            ),
            "ops_per_cycle": throughput,
            "core0_ops": core_ops[0],
            "core1_ops": core_ops[1],
            **core_throughput,
            "jain_per_core_fairness": fairness,
            "l1_read_hits": read_hit,
            "l1_read_misses": read_miss,
            "l1_read_hit_rate": _rate(read_hit, read_hit + read_miss),
            "l1_read_miss_rate": _rate(read_miss, read_hit + read_miss),
            "l1_write_hits": write_hit,
            "l1_write_misses": write_miss,
            "l1_write_hit_rate": _rate(write_hit, write_hit + write_miss),
            "l1_write_miss_rate": _rate(write_miss, write_hit + write_miss),
            "l1_hits": l1_hits,
            "l1_misses": l1_misses,
            "l1_hit_rate": _rate(l1_hits, l1_hits + l1_misses),
            "l1_miss_rate": _rate(l1_misses, l1_hits + l1_misses),
            "l1_core0_hits": sum(item["core"] == 0 for item in l1_hit_events),
            "l1_core0_misses": sum(item["core"] == 0 for item in l1_miss_events),
            "l1_core1_hits": sum(item["core"] == 1 for item in l1_hit_events),
            "l1_core1_misses": sum(item["core"] == 1 for item in l1_miss_events),
            "data_misses": data_misses,
            "permission_upgrade_misses": upgrades,
            "l2_refill_hits": l2_hits,
            "l2_refill_misses": l2_misses,
            "l2_refill_hit_rate": _rate(l2_hits, l2_hits + l2_misses),
            "l2_refill_miss_rate": _rate(l2_misses, l2_hits + l2_misses),
            "snoops": counts["snoops"],
            "snoops_per_op": _rate(counts["snoops"], len(completions)),
            "dirty_writebacks": counts["dirty_writebacks"],
            "dirty_writebacks_per_op": _rate(counts["dirty_writebacks"],
                                              len(completions)),
            "memory_read_lines": len(memory.read_requests) - read_req_before,
            "memory_write_lines": len(memory.write_requests) - write_req_before,
            "memory_read_bytes": read_bytes,
            "memory_write_bytes": write_bytes,
            "memory_total_bytes": read_bytes + write_bytes,
            "read_bandwidth_bytes_per_cycle": _rate(read_bytes, cycles),
            "write_bandwidth_bytes_per_cycle": _rate(write_bytes, cycles),
            "aggregate_bandwidth_bytes_per_cycle": _rate(
                read_bytes + write_bytes, cycles
            ),
            "traffic_amplification": _rate(read_bytes + write_bytes,
                                            logical_bytes),
            "logical_cpu_bytes": logical_bytes,
            "mshr_mean_occupancy": (
                sum(level * count for level, count in mshr_hist.items()) /
                mshr_cycles if mshr_cycles else 0.0
            ),
            "mshr_peak_occupancy": mshr_peak,
            "mshr_full_cycles": mshr_hist.get(4, 0),
            "mshr_occupancy_histogram": mshr_hist,
            "directory_mean_active_contexts": (
                sum(level * count for level, count in context_hist.items()) /
                context_cycles if context_cycles else 0.0
            ),
            "directory_peak_active_contexts": context_peak,
            "directory_full_context_cycles": context_hist.get(4, 0),
            "directory_context_histogram": context_hist,
            "stall_cycles": stall_delta,
            "memory_response_gaps": response_gap_delta,
        }
        rows.append(row)
        print("COHERENCE_BENCHMARK_V4," + json.dumps(row, sort_keys=True))
        return row

    # B01: steady-state private L1 hits.
    await reset_cache()
    warm_addr = 0x0100_0000
    await cpu.access(0, warm_addr)
    async def warm_l1():
        for _ in range(128):
            assert await cpu.access(0, warm_addr) == memory.word(warm_addr, 0)
    await measure("B01_warm_l1", "core0_repeated_line", 0, 2, 128,
                  "line resident in Core0 L1 before measurement", warm_l1)

    # B02: 8-byte stride captures compulsory line misses and spatial locality.
    await reset_cache()
    scan_base = 0x0120_0000
    scan_words = 16 * 1024 // 8
    async def sequential_scan():
        for index in range(scan_words):
            addr = scan_base + index * 8
            value = await cpu.access(0, addr)
            assert value == memory.word(addr, (addr >> 3) & 7)
    await measure("B02_sequential_scan", "16KiB_8B_stride", 0xB002, 2,
                  scan_words, "cold L1 and L2", sequential_scan)

    # B03: populate each working set once, then measure a repeat pass.
    for index, size_kib in enumerate((4, 16, 32, 64, 256, 512)):
        await reset_cache()
        base = 0x0400_0000 + index * 0x0010_0000
        line_count = size_kib * 1024 // 64
        for line in range(line_count):
            await cpu.access(0, base + line * 64)
        async def working_set_repeat(start=base, count=line_count):
            for line in range(count):
                addr = start + line * 64
                value = await cpu.access(0, addr)
                assert value == memory.word(addr, (addr >> 3) & 7)
        await measure("B03_working_set_sweep", f"{size_kib}KiB", 0xB030 + index,
                      2, line_count,
                      f"{size_kib}KiB populated by a complete first pass",
                      working_set_repeat)

    # B04: conflict pressure at the four-way L1 and eight-way shared L2 sets.
    await reset_cache()
    l1_conflict_base = 0x1000_0000
    l1_conflict = [l1_conflict_base + way * 32768 for way in range(5)]
    for addr in l1_conflict[:4]:
        await cpu.access(0, addr)
    async def l1_conflict_replay():
        for addr in l1_conflict[4:] + l1_conflict[:4]:
            assert await cpu.access(0, addr) == memory.word(addr, (addr >> 3) & 7)
    await measure("B04_set_conflict", "L1_same_set_five_lines", 0xB041, 2, 5,
                  "four lines resident in one L1 set; fifth line conflicts",
                  l1_conflict_replay)

    await reset_cache()
    l2_conflict_base = 0x1100_0000
    l2_conflict = [l2_conflict_base + way * 32768 for way in range(9)]
    conflict_values = [0xD000_0000_0000_0000 + way for way in range(9)]
    for addr, value in zip(l2_conflict[:8], conflict_values[:8]):
        await cpu.access(0, addr, write=True, data=value)
    async def l2_conflict_ninth_line():
        await cpu.access(0, l2_conflict[8], write=True, data=conflict_values[8])
    l2_conflict_row = await measure(
        "B04_set_conflict", "L2_same_set_nine_dirty_lines", 0xB042, 2, 1,
        "eight dirty lines occupy one L2 set; ninth line forces live victim recovery",
        l2_conflict_ninth_line,
    )
    assert l2_conflict_row["dirty_writebacks"] > 0
    for addr, expected in zip(l2_conflict, conflict_values):
        assert await cpu.access(0, addr) == expected

    # B05: equal operation counts, controlled read/write ratios and a fixed seed.
    for ratio_index, (label, write_percent) in enumerate(
            (("100R_0W", 0), ("80R_20W", 20), ("50R_50W", 50))):
        await reset_cache()
        seed = 0xB050 + ratio_index
        randomizer = random.Random(seed)
        base = 0x1200_0000 + ratio_index * 0x10000
        addresses = [base + line * 64 for line in range(32)]
        model = CoherenceScoreboard()
        model.track_l1_replacement = False
        for addr in addresses:
            model.seed_word(addr, memory.word(addr, (addr >> 3) & 7))
        if ratio_index == 2:
            memory.backpressure_periods.update(
                {"read_req": 5, "write_req": 7, "write_data": 5}
            )
            memory.response_gap_periods["read_data"] = 4
        async def mixed_read_write(
                reference=model, rng=randomizer, pool=addresses,
                write_pct=write_percent):
            for operation in range(256):
                addr = rng.choice(pool)
                core = rng.randrange(2)
                write = rng.randrange(100) < write_pct
                data = rng.getrandbits(64) if write else 0
                mask = rng.randrange(1, 256) if write else 0xFF
                result = await _model_access(
                    cpu, reference, memory.snoop_data, core, addr,
                    write=write, data=data, mask=mask,
                )
                if not write:
                    assert result == reference.word(addr)
        row = await measure("B05_mixed_read_write", label, seed, 2, 256,
                            "32 cache lines; deterministic random core/address stream",
                            mixed_read_write)
        if ratio_index == 2:
            memory.backpressure_periods.clear()
            memory.response_gap_periods.clear()
        assert row["completed_ops"] == 256
        for addr in addresses:
            expected = model.word(addr)
            observed = await cpu.access(0, addr)
            assert observed == expected, f"B05 readback {addr:#x} mismatch"

    # B06: paired distinct-set cold misses under a controllable memory delay.
    for delay in (2, 20, 50, 100):
        await reset_cache()
        base = 0x1400_0000 + delay * 0x10000
        async def dual_core_parallel_misses(start=base):
            for pair in range(8):
                addr0 = start + pair * 128
                addr1 = addr0 + 64
                result0, result1 = await cpu.access_pair(
                    CpuRequest(addr0), CpuRequest(addr1)
                )
                assert result0 == memory.word(addr0, (addr0 >> 3) & 7)
                assert result1 == memory.word(addr1, (addr1 >> 3) & 7)
        row = await measure(
            "B06_dual_core_parallel_miss", f"memory_delay_{delay}cy",
            0xB060 + delay, delay, 16,
            "16 cold lines in distinct L2 sets; eight simultaneous dual-core pairs",
            dual_core_parallel_misses,
        )
        assert row["core0_ops"] == row["core1_ops"] == 8

        await reset_cache()
        async def serial_cold_misses(start=base):
            for line in range(16):
                addr = start + line * 64
                value = await cpu.access(0, addr)
                assert value == memory.word(addr, (addr >> 3) & 7)
        serial_row = await measure(
            "B06_serial_cold_miss", f"memory_delay_{delay}cy",
            0xB160 + delay, delay, 16,
            "16 cold lines; Core0 issues one blocking miss at a time",
            serial_cold_misses,
        )
        assert serial_row["core0_ops"] == 16 and serial_row["core1_ops"] == 0

    # B07: repeated writer ownership movement on a single line.
    await reset_cache()
    ping_addr = 0x1600_0000
    await cpu.access(0, ping_addr, write=True, data=0x7000)
    async def ownership_ping_pong():
        for index in range(64):
            core = index & 1
            await cpu.access(core, ping_addr, write=True,
                             data=0x7100 + index)
    ping_row = await measure(
        "B07_ownership_ping_pong", "64_alternating_stores", 0xB070, 2, 64,
        "Core0 owns the line in M before alternating stores", ownership_ping_pong,
    )
    assert ping_row["snoops"] > 0
    assert await cpu.access(0, ping_addr) == 0x7100 + 63

    # B08: false-sharing A/B with matched writes and separate final data checks.
    false_sharing_rows = []
    for case_index, same_line in enumerate((True, False)):
        await reset_cache()
        base = 0x1800_0000 + case_index * 0x10000
        addr0 = base
        addr1 = base + (8 if same_line else 64)
        model = CoherenceScoreboard()
        model.track_l1_replacement = False
        for addr in (addr0, addr1):
            model.seed_word(addr, memory.word(addr, (addr >> 3) & 7))
        await _model_access(cpu, model, memory.snoop_data, 0, addr0)
        await _model_access(cpu, model, memory.snoop_data, 1, addr1)
        label = "same_line_different_words" if same_line else "different_lines"
        async def false_sharing_pairs(first=addr0, second=addr1,
                                      reference=model, salt=case_index):
            for index in range(32):
                value0 = 0xA000_0000_0000_0000 | (salt << 16) | index
                value1 = 0xB000_0000_0000_0000 | (salt << 16) | index
                await cpu.access_pair(
                    CpuRequest(first, True, value0),
                    CpuRequest(second, True, value1),
                )
                reference.observe(0, first, write=True, write_data=value0)
                reference.observe(1, second, write=True, write_data=value1)
        row = await measure(
            "B08_false_sharing", label, 0xB080 + case_index, 2, 64,
            "both lines are shared before matched paired stores", false_sharing_pairs,
        )
        false_sharing_rows.append(row)
        observed0 = await _model_access(
            cpu, model, memory.snoop_data, 0, addr0
        )
        observed1 = await _model_access(
            cpu, model, memory.snoop_data, 1, addr1
        )
        assert observed0 == model.word(addr0)
        assert observed1 == model.word(addr1)
        for addr in {addr0, addr1}:
            memory.snoop_data.assert_directory_matches(model, addr)
    assert false_sharing_rows[0]["snoops"] > false_sharing_rows[1]["snoops"]

    print(f"Benchmark v4: completed {len(rows)} workload rows")
