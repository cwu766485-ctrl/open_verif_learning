"""Test Directory Arbitration MESI subsystem tests."""

from .support import *


@case
async def test_directory_lookup_grant_conflict_offset_sweep(coherent_env):
    """Sweep request phase to replay a waiter during an active L2 grant."""
    dut, memory, perf = await coherent_env(
        response_delay=2, backpressure_periods={"read_req": 4},
    )
    grant_conflicts = []
    cpu = DualCoreCpuDriver(dut)
    # Sweep offsets around the short grant handshake window. Each grant line
    # is deliberately L2-resident but absent from both L1s; the competing
    # Core0 request is to a distinct cold line.
    for attempt in range(4):
        for offset in range(16):
            grant_addr = 0x0440_0000 + (attempt * 16 + offset) * 64
            await cpu.access(0, grant_addr)
            for way in range(1, 5):
                await cpu.access(0, grant_addr + way * 32768)
            conflict_cursor = len(memory.snoop_data.transfer_grant_conflicts)
            waiting_addr = grant_addr + 0x1000 + offset * 64
            # Core1 launches the L2-resident refill. Core0 is offered after
            # each phase offset while the grant is active. The shared driver
            # owns both packed request lanes and checks both responses.
            try:
                await cpu.access_pair(
                    CpuRequest(waiting_addr), CpuRequest(grant_addr),
                    request_delay_cycles={0: offset},
                )
            except TimeoutError as error:
                raise TimeoutError(
                    f"offset={offset} grant={grant_addr:#x} waiting={waiting_addr:#x}; "
                    f"memory_reads={memory.read_requests[-8:]}; "
                    f"directory_commits={memory.snoop_data.directory_commits[-8:]}; "
                    f"transfer_grant_conflicts="
                    f"{memory.snoop_data.transfer_grant_conflicts[-8:]}; "
                    f"recent_l2={perf.events['l2_lookups'][-8:]}; "
                    f"recent_grants={perf.events['directory_grants'][-8:]}; {error}"
                ) from error
            conflicts = memory.snoop_data.transfer_grant_conflicts[conflict_cursor:]
            grant_conflicts.extend(
                item for item in conflicts
                if item["lookup"] != item["grant"]
            )
            if grant_conflicts:
                PYTHON_COVERAGE.sample_external("directory_lookup_conflict_grant")
                PYTHON_COVERAGE.sample_interleaving(
                    "active_grant_distinct_address_ready_stall")
                _record_model(CoherenceScoreboard())
                assert int(dut.protocol_error.value) == 0
                return
    raise AssertionError(
        "offset sweep failed to overlap a distinct-address waiter with an "
        f"active grant; observed conflicts={memory.snoop_data.lookup_conflicts}"
    )
