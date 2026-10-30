"""Randomized MESI subsystem tests."""

from .support import *


@pytest.mark.parametrize("seed", _randomized_seeds())
@case
async def test_python_seeded_randomized_coherence(coherent_env, seed):
    ready_period = 3 + seed % 5
    dut, memory, _ = await coherent_env(
        response_delay=seed % 5 + 1,
        backpressure_periods={"read_req": ready_period},
        response_gap_periods={"read_data": ready_period + 1},
    )
    cpu = DualCoreCpuDriver(dut)
    model = CoherenceScoreboard()
    # The randomized stress lets the DUT choose the actual victim way. The
    # reference model tracks coherence from CPU requests and completed Put
    # transactions, avoiding a second, potentially divergent way predictor.
    model.track_l1_replacement = False
    lookup_conflict_cursor = len(memory.snoop_data.lookup_conflicts)
    rng = random.Random(seed)
    stress_mode = bool(os.environ.get("COHERENCE_STRESS_SEED_COUNT"))
    if stress_mode:
        if os.environ.get("COHERENCE_DENSE_L2_SET_STRESS"):
            # Regression for the previously uncovered corner: nine lines
            # collide in one 8-way L2 set while also thrashing one L1 set.
            addresses = [0x0200_0800 + index * 32768 for index in range(9)]
        else:
            # Ten lines conflict in one L1 set while spreading across four L2
            # sets; the remaining addresses spread traffic over other sets. Keep
            # this pool away from the deterministic prologue's L2 sets 0 and 128.
            addresses = ([0x0200_0800 + index * 0x2000 for index in range(10)] +
                         [0x1200_1000 + index * 64 for index in range(16)])
    else:
        addresses = [0x0200_0000 + index * 64 for index in range(12)]

    def request_for(address):
        write = rng.random() < 0.4
        return CpuRequest(
            address, write=write,
            data=rng.getrandbits(64) if write else 0,
            mask=rng.randrange(1, 256) if write else 0xFF,
        )

    def seed_if_needed(address):
        word_address = address & ~0x7
        if word_address not in model.data:
            model.seed_word(address, memory.word(address, (address >> 3) & 7))

    operations = int(os.environ.get("COHERENCE_STRESS_OPERATIONS", "36"))
    if not 1 <= operations <= 500:
        raise ValueError("COHERENCE_STRESS_OPERATIONS must be in [1, 500]")
    history = []

    def apply_puts_since(cursor):
        for event in memory.snoop_data.directory_requests[cursor:]:
            if event["opcode"] in (0b011, 0b100, 0b101):
                model.observe_l1_put(event["core"], event["line"],
                                     event["opcode"])

    def apply_victim_snoops_since(cursor):
        for event in memory.snoop_data.victim_snoops[cursor:]:
            model.observe_victim_invalidate(event["core"], event["line"])

    async def checked_access(core, address, **kwargs):
        put_cursor = len(memory.snoop_data.directory_requests)
        victim_cursor = len(memory.snoop_data.victim_snoops)
        try:
            result = await cpu.access(core, address, **kwargs)
            apply_puts_since(put_cursor)
            if not model.track_l2_replacement:
                apply_victim_snoops_since(victim_cursor)
            return result
        except TimeoutError as error:
            raise TimeoutError(
                f"seed={seed:#x}, operation={index}, core={core}, "
                f"request={address:#x}, recent operations={history[-12:]}; {error}"
            ) from error

    async def checked_pair(req0, req1):
        put_cursor = len(memory.snoop_data.directory_requests)
        try:
            result = await cpu.access_pair(req0, req1)
            if model.track_l2_replacement:
                apply_puts_since(put_cursor)
            return result
        except TimeoutError as error:
            rtl_state = {
                "engine": int(dut.monitor_engine_state.value),
                "engine_addr": int(dut.monitor_engine_addr.value),
                "victim_addr": int(dut.monitor_victim_addr.value),
                "victim_targets": int(
                    dut.monitor_victim_pending_targets.value
                ),
                "victim_target": int(dut.monitor_victim_target.value),
                "snoop_valid": int(dut.monitor_snoop_offer_valid.value),
                "snoop_ready": int(dut.monitor_snoop_offer_ready.value),
                "mem_mshr_valid": int(dut.monitor_mem_mshr_valid.value),
                "directory_active": int(
                    dut.monitor_directory_active_contexts.value
                ),
                "cpu_states": int(dut.monitor_cpu_state.value),
                "l1_snoop_states": int(dut.monitor_l1_snoop_state.value),
                "cpu_active_addrs": int(dut.monitor_cpu_active_addr.value),
                "l1_replace_states": int(dut.monitor_l1_replace_state.value),
                "dir_req": (
                    int(dut.monitor_dir_req_live_valid.value),
                    int(dut.monitor_dir_req_live_ready.value),
                    int(dut.monitor_dir_req_live_addr.value),
                ),
                "dir_xfer": (
                    int(dut.monitor_dir_xfer_live_valid.value),
                    int(dut.monitor_dir_xfer_live_ready.value),
                ),
            }
            raise TimeoutError(
                f"seed={seed:#x}, operation={index}, pair=({req0}, {req1}), "
                f"recent operations={history[-12:]}; fill="
                f"{int(dut.monitor_l2_fill_active.value)}, "
                f"line_wr=(valid={int(dut.monitor_l2_line_wr_valid.value)},"
                f"ready={int(dut.monitor_l2_line_wr_ready.value)},"
                f"addr={int(dut.monitor_l2_line_wr_addr.value):#x},"
                f"beat={int(dut.monitor_l2_line_wr_beat.value)}), "
                f"dir_snoop=(data={int(dut.monitor_dir_snoop_data_to_l2.value)},"
                f"valid={int(dut.monitor_dir_snoop_valid.value)},"
                f"set_conflict={int(dut.monitor_snoop_set_conflict.value)}), "
                f"read_requests={memory.read_requests[-8:]}, "
                f"write_requests={memory.write_requests[-8:]}, "
                f"write_responses={memory.write_responses[-8:]}, "
                f"memory_state={memory.debug_snapshot}, "
                f"mem_rd=(valid={int(dut.mem_rd_data_valid.value)},"
                f"ready={int(dut.mem_rd_data_ready.value)},"
                f"id={int(dut.mem_rd_data_txn_id.value)},"
                f"beat={int(dut.mem_rd_data_beat_idx.value)}), "
                f"mem_req=(valid={int(dut.mem_rd_req_valid.value)},"
                f"ready={int(dut.mem_rd_req_ready.value)},"
                f"id={int(dut.mem_rd_req_txn_id.value)}), "
                f"snoops={memory.snoop_data.snoops[-12:]}, "
                f"victim_snoops={memory.snoop_data.victim_snoops[-12:]}, "
                f"rtl_state={rtl_state}, "
                f"snoop_responses={memory.snoop_data.snoop_response_cycles[-16:]}, "
                f"dir_snoop_responses="
                f"{memory.snoop_data.directory_snoop_response_cycles[-16:]}, "
                f"dir_commits={memory.snoop_data.directory_commits[-12:]}, "
                    f"dir_requests={memory.snoop_data.directory_requests[-16:]}, "
                    f"dir_grants={memory.snoop_data.directory_grants[-16:]}, "
                    f"l2_lookups={memory.snoop_data.l2_lookups[-16:]}, "
                f"owner_partial={memory.snoop_data.partial}; {error}"
                    f"; error_detail={int(dut.protocol_error_detail.value):012b}"
            ) from error

    # Keep a deterministic eviction prelude on the replay seed so the long
    # random sweep always reaches dirty-owner and two-sharer L2 victims.
    if stress_mode and seed == 0x5EED:
        index = -1
        dirty_base = 0x0080_2000
        dirty_values = {}
        l2_cursor = len(model.l2_evictions)
        write_cursor = len(memory.write_requests)
        for n in range(9):
            address = dirty_base + n * 32768
            value = 0xD17E000000000000 | n
            core = 0 if n < 4 or n == 8 else 1
            seed_if_needed(address)
            await checked_access(core, address, write=True, data=value)
            model.observe(core, address, write=True, write_data=value,
                          write_mask=0xFF)
            dirty_values[address] = value
        dirty_victims = [item for item in model.l2_evictions[l2_cursor:]
                         if item["state"] == "M"]
        dirty_lines = {item["line"] for item in dirty_victims}
        observed_writes = {entry[0] & ~0x3F
                           for entry in memory.write_requests[write_cursor:]}
        assert dirty_lines and dirty_lines & observed_writes, (
            f"seed={seed:#x}: expected dirty live L2 victim/writeback; "
            f"victims={dirty_victims}, writes={memory.write_requests[write_cursor:]}"
        )
        victim = dirty_victims[0]
        victim_line = victim["line"]
        reload = await checked_access(1 - victim["core"], victim_line)
        model.observe(1 - victim["core"], victim_line, response_data=reload)
        assert reload == dirty_values[victim_line], (
            f"seed={seed:#x}: dirty victim data changed after writeback"
        )
        assert len(memory.write_responses) == len(memory.write_requests)

        shared_base = 0x0100_0000
        shared_lines = [shared_base + n * 32768 for n in range(9)]
        shared_target = shared_lines[6]
        for n in range(6):
            core = 0 if n < 3 else 1
            address = shared_lines[n]
            seed_if_needed(address)
            response = await checked_access(core, address)
            model.observe(core, address, response_data=response)
        for core in (0, 1):
            seed_if_needed(shared_target)
            response = await checked_access(core, shared_target)
            model.observe(core, shared_target, response_data=response)
        address = shared_lines[7]
        seed_if_needed(address)
        response = await checked_access(0, address)
        model.observe(0, address, response_data=response)
        assert model.states[shared_target] == ["S", "S"]
        set_index = model._l2_set(shared_target)
        assert model.l2_ways[set_index][model.l2_next_way[set_index] % 8] == shared_target
        shared_expected_words = [memory.word(shared_target, beat)
                                 for beat in range(8)]
        snoop_cursor = len(memory.snoop_data.snoops)
        shared_write_cursor = len(memory.write_requests)
        address = shared_lines[8]
        seed_if_needed(address)
        response = await checked_access(0, address)
        model.observe(0, address, response_data=response)
        shared_victims = [item for item in model.l2_evictions[l2_cursor:]
                          if item["line"] == shared_target and item["state"] == "S"]
        assert {item["core"] for item in shared_victims} == {0, 1}
        assert {item["core"] for item in memory.snoop_data.snoops[snoop_cursor:]
                if item["line"] == shared_target} == {0, 1}
        if any((entry[0] & ~0x3F) == shared_target
               for entry in memory.write_requests[shared_write_cursor:]):
            assert tuple(memory._read_word(shared_target, beat)
                         for beat in range(8)) == tuple(shared_expected_words)
        memory.snoop_data.assert_directory_matches(model, shared_target)
        assert not model.l2_contains(shared_target)

    if stress_mode:
        # Random replacement order is driven by concurrent CPU/snoop events.
        # Keep the reference MESI model event-driven from this point rather
        # than predicting an L2 way from an assumed lane retirement order.
        model.track_l2_replacement = False

    for index in range(operations):
        model.operation_index = index
        if index % 6 == 5:
            # Distinct lines allow the two lanes to be checked independently
            # even if the subsystem retires their responses out of order.
            first, second = rng.sample(addresses, 2)
            req0, req1 = request_for(first), request_for(second)
            seed_if_needed(first)
            seed_if_needed(second)
            if (not req1.write and model.states[req1.addr & ~0x3F][0] == "M"):
                # Check the latest owner word locally before exercising a
                # simultaneous independent miss and remote GetS.
                owner_data = await checked_access(0, req1.addr)
                model.observe(0, req1.addr, response_data=owner_data)
            snoop_cursor = len(memory.snoop_data.transfers)
            snoop_req_cursor = len(memory.snoop_data.snoops)
            victim_snoop_cursor = len(memory.snoop_data.victim_snoops)
            put_cursor = len(memory.snoop_data.directory_requests)
            monitor_cycle_offset = cpu.cycle - memory.snoop_data.cycle
            dir_commit_cursor = len(memory.snoop_data.directory_commits)
            result0, result1 = await checked_pair(req0, req1)
            victim_evicted_req1_owner = any(
                item["line"] == (req1.addr & ~0x3F) and item["core"] == 0
                for item in memory.snoop_data.victim_snoops[victim_snoop_cursor:]
            )
            if (not req1.write and
                    model.states[req1.addr & ~0x3F][0] == "M" and
                    not victim_evicted_req1_owner):
                line = req1.addr & ~0x3F
                expected_line = [model.data.get(
                    line + 8 * beat, memory.word(line, beat))
                    for beat in range(8)]
                owner_snoops = [
                    item for item in memory.snoop_data.snoops[snoop_req_cursor:]
                    if item["line"] == line and item["core"] == 0
                ]
                owner_putm = any(
                    item["line"] == line and item["core"] == 0 and
                    item["opcode"] == 0b101
                    for item in memory.snoop_data.directory_requests[put_cursor:]
                )
                if owner_snoops:
                    assert owner_snoops[-1]["opcode"] == 0, (
                        f"remote read of Core0 M line {line:#x} must not invalidate "
                        f"the owner; observed {owner_snoops}"
                    )
                else:
                    # A concurrent same-L1-set miss from Core0 can retire the
                    # modified owner with PutM before Core1's read reaches the
                    # directory. In that legal ordering, the read is served by
                    # the newly current L2 copy and needs no SnoopRead.
                    assert owner_putm, (
                        f"Core0 M line {line:#x} had neither SnoopRead nor an "
                        f"accepted PutM; pair=({req0}, {req1}), "
                        f"victim_snoops={memory.snoop_data.victim_snoops[victim_snoop_cursor:]}, "
                        f"requests={memory.snoop_data.directory_requests[put_cursor:]}"
                    )
                owner_data = [item for item in memory.snoop_data.transfers[snoop_cursor:]
                              if item["line"] == line and item["core"] == 0]
                if owner_data:
                    memory.snoop_data.assert_line_data(
                        req1.addr, expected_line, since=snoop_cursor)
                else:
                    # Under same-set pressure, Core0 may already have accepted
                    # PutM for this victim while Directory's old snapshot was
                    # issuing SnoopRead. The L1 then correctly returns ACK
                    # without data; Directory retries the now-current L2 line.
                    assert owner_putm, (
                        f"SnoopRead of Core0 M line {line:#x} produced no owner data "
                        "and had no accepted PutM recovery"
                    )
                expected_word = model.data.get(
                    req1.addr & ~0x7, memory.word(req1.addr, (req1.addr >> 3) & 7)
                )
                assert result1 == expected_word, (
                    f"remote read of Core0 M line {line:#x} returned "
                    f"{result1:#018x}, expected current owner value {expected_word:#018x}"
                )
            pair_ops = ((0, req0, result0), (1, req1, result1))
            for core, req, result in pair_ops:
                history.append((index, core, req.addr, req.write, req.data,
                                req.mask, result))
            if stress_mode:
                ordered_events = [
                    (cpu.last_pair_completed_at[core], 1, core, req, result)
                    for core, req, result in pair_ops
                ]
                for event in memory.snoop_data.directory_requests[put_cursor:]:
                    if event["opcode"] in (0b011, 0b100, 0b101):
                        ordered_events.append((event["cycle"] +
                                               monitor_cycle_offset,
                                               0, event["core"], event, None))
                for event in memory.snoop_data.victim_snoops[victim_snoop_cursor:]:
                    ordered_events.append((event["cycle"] + monitor_cycle_offset,
                                           2, event["core"], event, None))
                ordered_events.sort(key=lambda event: (event[0], event[1]))
                try:
                    for _, kind, core, req_or_event, result in ordered_events:
                        if kind == 0:
                            model.observe_l1_put(core, req_or_event["line"],
                                                 req_or_event["opcode"])
                        elif kind == 1:
                            model.observe(core, req_or_event.addr,
                                          write=req_or_event.write,
                                          write_data=req_or_event.data,
                                          write_mask=req_or_event.mask,
                                          response_data=result)
                        else:
                            model.observe_victim_invalidate(
                                core, req_or_event["line"])
                    for core, req, _ in pair_ops:
                        memory.snoop_data.assert_directory_matches(model, req.addr)
                except AssertionError as error:
                    line_snoops = [
                        item for item in memory.snoop_data.snoops
                        if item["line"] == (req.addr & ~0x3F)
                    ]
                    line_commits = [
                        item for item in memory.snoop_data.directory_commits
                        if item["line"] == (req.addr & ~0x3F)
                    ]
                    raise AssertionError(
                        f"seed={seed:#x}, recent operations={history[-12:]}, "
                        f"new snoops={memory.snoop_data.snoops[snoop_req_cursor:]}, "
                        f"new directory requests="
                        f"{memory.snoop_data.directory_requests[put_cursor:]}, "
                        f"new dir commits="
                        f"{memory.snoop_data.directory_commits[dir_commit_cursor:]}, "
                        f"line snoops={line_snoops[-8:]}, "
                        f"line commits={line_commits[-8:]}, "
                        f"new owner-data={memory.snoop_data.transfers[snoop_cursor:]}, "
                        f"model_line_states={model.states[req.addr & ~0x3F]}, "
                        f"model_line_history={[event for event in model.transitions if event['line'] == (req.addr & ~0x3F)][-8:]}, "
                        f"put_history={[event for event in memory.snoop_data.directory_requests if event['line'] == (req.addr & ~0x3F)][-8:]}, "
                        f"victim_history={[event for event in memory.snoop_data.victim_snoops if event['line'] == (req.addr & ~0x3F)][-8:]}, "
                        f"model_l2_ways={model.l2_ways[model._l2_set(req.addr)]}, "
                        f"model_l2_next={model.l2_next_way[model._l2_set(req.addr)]}, "
                        f"model_l2_evictions={model.l2_evictions[-16:]}"
                    ) from error
            else:
                for core, req, result in pair_ops:
                    try:
                        model.observe(core, req.addr, write=req.write,
                                      write_data=req.data, write_mask=req.mask,
                                      response_data=result)
                        memory.snoop_data.assert_directory_matches(model, req.addr)
                    except AssertionError as error:
                        raise AssertionError(
                            f"seed={seed:#x}, recent operations={history[-12:]}, "
                            f"line={req.addr & ~0x3F:#x}: {error}"
                        ) from error
                if req.write:
                    readback = await checked_access(core, req.addr)
                    history.append((index, core, req.addr, False, 0, 0xFF,
                                    readback))
                    model.observe(core, req.addr, response_data=readback)
                    memory.snoop_data.assert_directory_matches(model, req.addr)
            PYTHON_COVERAGE.sample_external("random_dual_lane_pairs")
        else:
            core = rng.randrange(2)
            address = rng.choice(addresses)
            req = request_for(address)
            seed_if_needed(address)
            result = await checked_access(core, req.addr, write=req.write,
                                          data=req.data, mask=req.mask)
            history.append((index, core, req.addr, req.write, req.data,
                            req.mask, result))
            try:
                model.observe(core, req.addr, write=req.write,
                              write_data=req.data, write_mask=req.mask,
                              response_data=result)
                memory.snoop_data.assert_directory_matches(model, req.addr)
            except AssertionError as error:
                line = req.addr & ~0x3F
                line_commits = [
                    item for item in memory.snoop_data.directory_commits
                    if item["line"] == line
                ]
                line_snoops = [
                    item for item in memory.snoop_data.snoops
                    if item["line"] == line
                ]
                raise AssertionError(
                    f"seed={seed:#x}, recent operations={history[-12:]}, "
                    f"line={line:#x}, modeled_states={model.states[line]}, "
                    f"line_history={[item for item in history if item[2] & ~0x3F == line]}, "
                    f"line_transitions={[item for item in model.transitions if item['line'] == line][-16:]}, "
                    f"l1_ways=({model.l1_way_view(0, line)},"
                    f"{model.l1_way_view(1, line)}), "
                    f"model_l1_evictions={model.l1_evictions[-8:]}, "
                    f"snoops={line_snoops[-8:]}, "
                    f"directory_commits={line_commits[-12:]}"
                ) from error
            if req.write:
                readback = await checked_access(core, req.addr)
                history.append((index, core, req.addr, False, 0, 0xFF,
                                readback))
                model.observe(core, req.addr, response_data=readback)
                memory.snoop_data.assert_directory_matches(model, req.addr)

    model.assert_covered("cold_read", "cold_write", "read_hit", "write_hit")
    assert int(dut.protocol_error.value) == 0, f"protocol error for seed={seed:#x}"
    PYTHON_COVERAGE.sample_external("randomized_seeded_regression")
    PYTHON_COVERAGE.sample_external("randomized_cpu_operations", operations)
    conflicts = memory.snoop_data.lookup_conflicts[lookup_conflict_cursor:]
    distinct_conflicts = [item for item in conflicts
                          if item["incoming"] != item["active"]]
    transfer_conflicts = [item for item in distinct_conflicts
                          if item["active_kind"] == "transfer"]
    # This fixed seed is the minimized replay that consistently overlaps a
    # different-address Directory request with the active owner-transfer
    # lookup. All normal data, MESI, beat and directory checkers above remain
    # enabled while request and R-beat backpressure are active.
    if seed == 0x5EED and not stress_mode:
        assert transfer_conflicts, (
            f"seed={seed:#x} failed to recreate a distinct-address transfer "
            f"lookup race: {conflicts}"
        )
        assert memory.stalls["read_req"] > 0
        PYTHON_COVERAGE.sample_external("directory_lookup_race_regression")
        PYTHON_COVERAGE.sample_external("directory_lookup_conflict_transfer")
        PYTHON_COVERAGE.sample_interleaving(
            "active_transfer_distinct_address_ready_stall")
    if stress_mode and seed == 0x5EED:
        assert any(item["state"] == "M" for item in model.l2_evictions), (
            "stress prologue missed a dirty-owner L2 live victim"
        )
        shared_lines_evicted = {}
        for item in model.l2_evictions:
            if item["state"] == "S":
                shared_lines_evicted.setdefault(item["line"], set()).add(item["core"])
        assert any(cores == {0, 1} for cores in shared_lines_evicted.values()), (
            "stress prologue missed a two-sharer L2 live victim"
        )
    _record_model(model)
