"""Benchmark V3 MESI subsystem tests."""

from .support import *


@pytest.mark.asyncio
@case
@pytest.mark.benchmark
async def test_coherence_benchmark_v3(coherent_env):
    """Run repeatable cache, mixed-traffic, and latency-sweep workloads."""
    dut, memory, perf = await coherent_env()
    cpu = DualCoreCpuDriver(dut)
    rows = []
    benchmark_seeds = (0x1A2B, 0x5EED, 0xC0FFEE, 0xBADC0DE, 0xD15EA5E)

    async def measure(name, delay, initial_state, ops, workload, seed=0):
        memory.response_delay = delay
        before_perf = perf.snapshot()
        before_stage_events = perf.event_snapshot()
        before_read_req = len(memory.read_requests)
        before_read_complete = len(memory.read_completions)
        before_write_req = len(memory.write_requests)
        before_write_rsp = len(memory.write_responses)
        before_read_beats = memory.read_beats
        before_write_beats = memory.write_beats
        before_latencies = (len(cpu.latencies[0]), len(cpu.latencies[1]))
        await workload()
        after_perf = perf.snapshot()
        after_read_req = len(memory.read_requests)
        after_read_complete = len(memory.read_completions)
        after_write_req = len(memory.write_requests)
        after_write_rsp = len(memory.write_responses)
        after_read_beats = memory.read_beats
        after_write_beats = memory.write_beats
        samples = (cpu.latencies[0][before_latencies[0]:] +
                   cpu.latencies[1][before_latencies[1]:])
        delta = {key: after_perf[key] - before_perf[key]
                 for key in before_perf}
        stage_events = perf.events_since(before_stage_events)
        dir_to_lookup = _phase_samples(
            stage_events["directory_accepts"], stage_events["l2_lookups"]
        )
        l1_to_dir = _phase_samples(
            stage_events["l1_misses"], stage_events["directory_accepts"]
        )
        memory_read_requests = [
            {"addr": addr, "id": txn_id, "cycle": cycle}
            for addr, txn_id, cycle in memory.read_requests[before_read_req:]
        ]
        memory_read_completions = [
            {"addr": addr, "id": txn_id, "cycle": cycle}
            for addr, txn_id, cycle in memory.read_completions[before_read_complete:]
        ]
        memory_write_requests = [
            {"addr": addr, "id": txn_id, "cycle": cycle}
            for addr, txn_id, cycle in memory.write_requests[before_write_req:]
        ]
        memory_write_responses = [
            {"id": txn_id, "cycle": cycle}
            for txn_id, cycle in memory.write_responses[before_write_rsp:]
        ]
        l2_hit_events = [event for event in stage_events["l2_lookups"]
                         if event["hit"]]
        l2_miss_events = [event for event in stage_events["l2_lookups"]
                          if not event["hit"]]
        l2_hit_to_grant = _phase_samples(
            l2_hit_events, stage_events["directory_grants"]
        )
        l2_miss_to_memory = _phase_samples(
            l2_miss_events, memory_read_requests
        )
        memory_read_service = _phase_samples(
            memory_read_requests, memory_read_completions,
            start_key="id", end_key="id"
        )
        memory_write_service = _phase_samples(
            memory_write_requests, memory_write_responses,
            start_key="id", end_key="id"
        )
        cycles = delta["cycles"]
        l1_hits = delta["l1_hit_core0"] + delta["l1_hit_core1"]
        l1_misses = delta["l1_miss_core0"] + delta["l1_miss_core1"]
        l2_hits = delta["l2_refill_hit"]
        l2_misses = delta["l2_refill_miss"]
        read_beats = after_read_beats - before_read_beats
        write_beats = after_write_beats - before_write_beats
        read_bytes = read_beats * 8
        write_bytes = write_beats * 8
        total_bytes = read_bytes + write_bytes
        row = {
            "workload": name,
            "memory_response_latency_cycles": delay,
            "seed": seed,
            "initial_cache_state": initial_state,
            "ops": ops,
            "window_cycles": cycles,
            "mean_req_to_resp_cycles": (sum(samples) / len(samples)
                                        if samples else None),
            "p95_req_to_resp_cycles": _p95(samples),
            "ops_per_cycle": _rate(ops, cycles),
            "phase_cycles": {
                "l1_miss_to_directory_accept": _phase_stats(l1_to_dir),
                "directory_accept_to_l2_lookup": _phase_stats(dir_to_lookup),
                "l2_hit_lookup_to_grant": _phase_stats(l2_hit_to_grant),
                "l2_miss_lookup_to_memory_request": _phase_stats(l2_miss_to_memory),
                "memory_read_request_to_last_beat": _phase_stats(memory_read_service),
                "memory_write_request_to_response": _phase_stats(memory_write_service),
            },
            "l1_hit_count": l1_hits,
            "l1_miss_count": l1_misses,
            "l1_hit_rate": _rate(l1_hits, l1_hits + l1_misses),
            "l1_miss_rate": _rate(l1_misses, l1_hits + l1_misses),
            "l1_core0_hit_count": delta["l1_hit_core0"],
            "l1_core0_miss_count": delta["l1_miss_core0"],
            "l1_core1_hit_count": delta["l1_hit_core1"],
            "l1_core1_miss_count": delta["l1_miss_core1"],
            "l2_refill_hit_count": l2_hits,
            "l2_refill_miss_count": l2_misses,
            "l2_refill_hit_rate": _rate(l2_hits, l2_hits + l2_misses),
            "l2_refill_miss_rate": _rate(l2_misses, l2_hits + l2_misses),
            "snoops": delta["snoops"],
            "dirty_writebacks": delta["dirty_writebacks"],
            "memory_read_lines": after_read_req - before_read_req,
            "memory_write_lines": after_write_req - before_write_req,
            "memory_read_bytes": read_bytes,
            "memory_write_bytes": write_bytes,
            "memory_read_bytes_per_cycle": _rate(read_bytes, cycles),
            "memory_write_bytes_per_cycle": _rate(write_bytes, cycles),
            "memory_total_bytes_per_cycle": _rate(total_bytes, cycles),
            "memory_read_mib_per_second": (
                _rate(read_bytes, cycles) * 100_000_000 / (1024 * 1024)
                if cycles else None
            ),
            "memory_write_mib_per_second": (
                _rate(write_bytes, cycles) * 100_000_000 / (1024 * 1024)
                if cycles else None
            ),
            "memory_total_mib_per_second": (
                _rate(total_bytes, cycles) * 100_000_000 / (1024 * 1024)
                if cycles else None
            ),
            "paired_vs_serialized_speedup": None,
        }
        rows.append(row)
        print("COHERENCE_BENCHMARK_V3," + json.dumps(row, sort_keys=True))

    for latency_index, delay in enumerate((2, 20, 50, 100)):
        # Use separate L2 set ranges per latency point so earlier delay runs
        # cannot evict the retained L2-hit line of a later point.
        base = 0x10000000 + latency_index * 0x2000

        warm = base
        await cpu.access(0, warm)
        async def warm_reads(addr=warm):
            for _ in range(64):
                await cpu.access(0, addr)
        await measure("warm_l1_reads", delay,
                      "Core0 line resident before the 64 measured reads", 64,
                      warm_reads)

        # Eight independent same-set samples per memory-delay point provide
        # 32 L2-hit observations while keeping each target in a separate L2
        # set. Shuffle the four L1 conflict lines from a fixed seed.
        for sample_index in range(8):
            seed = benchmark_seeds[(latency_index * 8 + sample_index) %
                                   len(benchmark_seeds)]
            rng = random.Random(seed)
            l2_addr = base + 0x1000 + sample_index * 64
            await cpu.access(0, l2_addr)
            eviction_ways = list(range(1, 5))
            rng.shuffle(eviction_ways)
            for way in eviction_ways:
                await cpu.access(0, l2_addr + way * 32768)

            async def l2_read(addr=l2_addr):
                result = await cpu.access(0, addr)
                assert result == memory.word(addr, (addr >> 3) & 7)

            await measure(
                "l2_hit_after_l1_replacement", delay,
                "Target absent from L1 and retained in L2 after four same-index L1 conflicts",
                1, l2_read, seed=seed,
            )

        serial_base = base + 0x40000
        async def serialized_cold():
            for n in range(16):
                await cpu.access(0, serial_base + 64 * n)
        await measure("serialized_cold_misses", delay,
                      "16 distinct lines absent from both L1s and shared L2", 16,
                      serialized_cold)

        parallel_base = base + 0x80000
        async def parallel_cold():
            for n in range(8):
                await cpu.access_pair(
                    CpuRequest(parallel_base + 128 * n),
                    CpuRequest(parallel_base + 128 * n + 64),
                )
        await measure("parallel_dual_l1_cold_misses", delay,
                      "16 distinct lines absent from both L1s and shared L2; paired issue",
                      16, parallel_cold)

        ping_addr = base + 0xC0000
        await cpu.access(0, ping_addr, write=True, data=0x1000 + delay)
        async def ownership_ping_pong(addr=ping_addr):
            for n in range(16):
                await cpu.access(n & 1, addr, write=True,
                                 data=0xA0000000 + delay * 32 + n)
        await measure("ownership_write_ping_pong", delay,
                      "Core0 owns the line in M before alternating core stores",
                      16, ownership_ping_pong)


    # Run the dirty victim last. It deliberately leaves an evicted dirty line
    # in the backing memory, so it must not alter the starting state of the
    # cold-miss workloads at the other latency points.
    delay = 100
    dirty_base = 0x00802000
    for n in range(8):
        owner = 0 if n < 4 else 1
        await cpu.access(owner, dirty_base + n * 32768, write=True,
                         data=0xD17A0000 + delay * 16 + n)
        assert int(dut.protocol_error.value) == 0, (
            f"protocol error during dirty-set setup line {n} at delay {delay}"
        )

    async def dirty_l2_victim(addr=dirty_base + 8 * 32768,
                              value=0xD17A0000 + delay * 16 + 8):
        await cpu.access(0, addr, write=True, data=value)
        assert int(dut.protocol_error.value) == 0, (
            f"protocol error after dirty L2 victim at delay {delay}"
        )
    await measure("dirty_l2_victim_writeback", delay,
                  "Eight same-set M lines live across both L1s; ninth line triggers L2 victim writeback",
                  1, dirty_l2_victim)

    # Mixed reads/writes and dual-core pairs use five reproducible seeds. Each
    # seed owns a disjoint address range and an independent architectural
    # reference model; every final line is read back through the DUT.
    for seed_index, seed in enumerate(benchmark_seeds):
        rng = random.Random(seed)
        mixed_base = 0x20000000 + seed_index * 0x01000000
        mixed_addresses = [mixed_base + line * 64 + (line % 8) * 8
                           for line in range(8)]
        model = CoherenceScoreboard()

        def seed_line(address):
            if (address & ~0x7) not in model.data:
                model.seed_word(
                    address, memory.word(address, (address >> 3) & 7)
                )

        async def mixed_workload(addresses=mixed_addresses, reference=model,
                                 randomizer=rng):
            for operation in range(48):
                if operation % 4 == 0:
                    first, second = randomizer.sample(addresses, 2)
                    requests = []
                    for address in (first, second):
                        seed_line(address)
                        write = randomizer.random() < 0.35
                        requests.append(CpuRequest(
                            address, write=write,
                            data=randomizer.getrandbits(64) if write else 0,
                            mask=randomizer.randrange(1, 256) if write else 0xFF,
                        ))
                    result0, result1 = await cpu.access_pair(
                        requests[0], requests[1]
                    )
                    for core, request, result in (
                            (0, requests[0], result0),
                            (1, requests[1], result1)):
                        expected = reference.word(request.addr)
                        if not request.write:
                            assert result == expected, (
                                f"seed={seed:#x} op={operation} "
                                f"addr={request.addr:#x}: {result:#x} != {expected:#x}"
                            )
                        reference.observe(
                            core, request.addr, write=request.write,
                            write_data=request.data, write_mask=request.mask,
                            response_data=result,
                        )
                else:
                    address = randomizer.choice(addresses)
                    seed_line(address)
                    core = randomizer.randrange(2)
                    write = randomizer.random() < 0.35
                    value = randomizer.getrandbits(64) if write else 0
                    mask = randomizer.randrange(1, 256) if write else 0xFF
                    result = await cpu.access(
                        core, address, write=write, data=value, mask=mask
                    )
                    expected = reference.word(address)
                    if not write:
                        assert result == expected, (
                            f"seed={seed:#x} op={operation} "
                            f"addr={address:#x}: {result:#x} != {expected:#x}"
                        )
                    reference.observe(
                        core, address, write=write, write_data=value,
                        write_mask=mask, response_data=result,
                    )

            for address in addresses:
                expected = reference.word(address)
                result = await cpu.access(0, address)
                assert result == expected, (
                    f"seed={seed:#x} final read {address:#x}: "
                    f"{result:#x} != {expected:#x}"
                )
                reference.observe(0, address, response_data=result)

        await measure(
            "seeded_mixed_dual_core", 20,
            "Eight target lines absent from both L1s and L2; disjoint region per seed",
            56, mixed_workload, seed=seed,
        )
        assert int(dut.protocol_error.value) == 0, (
            f"protocol error in mixed benchmark seed {seed:#x}"
        )

    # The serialized and paired runs carry the same 16 cold misses per latency
    # point. Report the measured overlap benefit without assuming a speedup.
    by_key = {(r["memory_response_latency_cycles"], r["workload"]): r
              for r in rows}
    for row in rows:
        if row["workload"] == "parallel_dual_l1_cold_misses":
            serial = by_key[(row["memory_response_latency_cycles"],
                             "serialized_cold_misses")]
            row["paired_vs_serialized_speedup"] = _rate(
                serial["window_cycles"], row["window_cycles"]
            )

    result_dir = Path(__file__).resolve().parents[2] / "benchmarks" / "results"
    result_dir.mkdir(parents=True, exist_ok=True)
    json_path = result_dir / "coherence_benchmark_v3.json"
    csv_path = result_dir / "coherence_benchmark_v3.csv"
    payload = {
        "schema_version": 4,
        "benchmark_version": 3,
        "dut": "CoherentCacheSubsystem via Picker/Verilator",
        "clock_period_ns": 10,
        "memory_model": "64-byte writable line model; response delay is a simulation parameter",
        "metric_definitions": {
            "l1_hit_miss": "accepted CPU request classified by L1 MESI state; S-store is a miss/upgrade",
            "l2_refill_hit_miss": "accepted Directory L2 refill lookup; not a count of all metadata probes",
            "memory_bandwidth": "accepted 64-bit R/W line beats times eight bytes, divided by benchmark cycles",
            "ops_per_cycle": "completed CPU operations divided by the measured window cycles",
            "phase_cycles": "observed same-line milestone deltas: L1 miss to Directory acceptance, Directory acceptance to L2 refill lookup, L2 hit to grant or L2 miss to backing-memory request, and accepted memory request to final response beat/write response; L2 metadata lookup itself is combinational",
            "seeded_mixed_dual_core": "five fixed seeds, dual-core paired and single-lane reads/writes, independent architectural scoreboards, final readback of all target lines",
        },
        "results": rows,
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    # These checks also validate that an L2-hit workload is really a refill
    # hit without another backing-memory transaction, and that ping-pong snoops.
    for row in rows:
        if row["workload"] == "l2_hit_after_l1_replacement":
            assert row["l1_miss_count"] == 1
            assert row["l2_refill_hit_count"] >= 1
            assert row["memory_read_lines"] == 0
        if row["workload"] == "seeded_mixed_dual_core":
            assert row["ops"] == 56
            assert row["l1_hit_count"] + row["l1_miss_count"] >= row["ops"]
        if row["workload"] == "ownership_write_ping_pong":
            assert row["snoops"] > 0
        if row["workload"] == "dirty_l2_victim_writeback":
            assert row["snoops"] > 0
            assert row["dirty_writebacks"] > 0
            assert row["memory_write_lines"] > 0
    l2_samples = [row for row in rows
                  if row["workload"] == "l2_hit_after_l1_replacement"]
    mixed_samples = [row for row in rows
                     if row["workload"] == "seeded_mixed_dual_core"]
    assert len(l2_samples) == 32, f"expected 32 independent L2-hit samples, got {len(l2_samples)}"
    assert sum(row["l2_refill_hit_count"] for row in l2_samples) == 32
    assert sum(row["memory_read_lines"] for row in l2_samples) == 0
    assert len(mixed_samples) == len(benchmark_seeds)
    assert {row["seed"] for row in mixed_samples} == set(benchmark_seeds)
