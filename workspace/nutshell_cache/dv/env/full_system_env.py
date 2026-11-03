"""Four-role Python/Toffee environment for CoherentCacheAxiSubsystem."""

from collections import defaultdict, deque

from toffee import ClockCycles

from dv.agents.apb_master_agent import ApbMasterAgent
from dv.agents.axi4_backing_memory_agent import Axi4BackingMemoryAgent
from dv.agents.coherent_cpu_agent import CpuRequest, DualCoreCpuDriver
from dv.agents.mmio_slave_agent import MmioSlaveAgent
from dv.coverage.full_system_coverage import FullSystemCoverage
from dv.monitors.full_system_monitor import FullSystemMonitor
from dv.scoreboard.coherence_scoreboard import CoherenceScoreboard


MESI_TO_ENCODING = {"I": 0, "S": 1, "E": 2, "M": 3}
DIR_TO_ENCODING = {"I": 0, "S": 1, "U": 2}


class FullSystemEnv:
    """Own the four external roles and the independent architectural model.

    The CPU driver is the sole writer for both packed CPU lanes. AXI and MMIO
    agents are slaves, while APB is a master. Gray-box signals are observed by
    ``FullSystemMonitor`` and checked against the model; they never seed the
    expected data or state.
    """

    def __init__(self, dut, *, axi_options=None, mmio_options=None):
        self.dut = dut
        self.cpu = DualCoreCpuDriver(dut)
        self.axi = Axi4BackingMemoryAgent(dut, **(axi_options or {}))
        self.mmio = MmioSlaveAgent(dut, **(mmio_options or {}))
        self.apb = ApbMasterAgent(dut)
        self.monitor = FullSystemMonitor(dut)
        self.axi.observation_callback = self.monitor.record_axi_event
        self.apb.observation_callback = self.monitor.record_apb_access
        self.mmio.observation_callback = self.monitor.record_mmio_event
        self.reference = CoherenceScoreboard()
        self.coverage = FullSystemCoverage()
        self.trace_test_id = None
        self.trace_scenario_id = "unspecified"
        self.trace_seed = None
        self.trace_config = {}
        self.trace_test_status = "incomplete"
        self.trace_failure_context = None
        self.trace_operations = []

    def seed_word(self, addr, value):
        """Seed independent CPU-visible and backing-memory models before use."""
        self.reference.seed_word(addr, value)
        self.axi.seed_word(addr, value)

    async def reset(self, cycles=2):
        """Pulse the shared synchronous reset and leave input lanes idle."""
        if cycles < 1:
            raise ValueError("reset must be held for at least one cycle")
        self.dut.cpu_req_valid.value = 0
        self.dut.cpu_resp_ready.value = 0
        self.dut.reset.value = 1
        await ClockCycles(self.dut, cycles)
        self.dut.reset.value = 0
        await ClockCycles(self.dut, 1)

    def _check_observed_commits(self, line, event_start):
        states = self.reference.states[line]
        observed_l1_commits = set()
        for event in self.monitor.events[event_start:]:
            if event["event_type"] == "metadata_commit" and event["source"] == "l1":
                if event["address"] & ~0x3F != line:
                    continue
                core = event["core"]
                expected = MESI_TO_ENCODING[states[core]]
                if event["new_state"] != expected:
                    raise AssertionError(
                        f"L1 metadata commit disagrees with independent model: "
                        f"line={line:#x} core={core} actual={event['new_state']} "
                        f"expected={states[core]}"
                    )
                observed_l1_commits.add((core, event["new_state"]))
            elif event["event_type"] == "metadata_commit" and event["source"] == "directory":
                if event["address"] & ~0x3F != line:
                    continue
                expected = self.reference.directory_view(line)
                actual_state = event["state"]
                if actual_state != DIR_TO_ENCODING[expected["state"]]:
                    raise AssertionError(
                        f"Directory commit disagrees with independent model for "
                        f"{line:#x}: actual={actual_state} expected={expected}"
                    )
                if expected["state"] == "S" and event["sharers"] != expected["sharers"]:
                    raise AssertionError(
                        f"Directory sharer commit mismatch for {line:#x}: "
                        f"actual={event['sharers']:#x} expected={expected['sharers']:#x}"
                    )
                if expected["state"] == "U" and event["owner"] != expected["owner"]:
                    raise AssertionError(
                        f"Directory owner commit mismatch for {line:#x}: "
                        f"actual={event['owner']} expected={expected['owner']}"
                    )
        return observed_l1_commits

    def _credit_cpu(self, core, write, addr, accepted_cycle, completed_cycle,
                    transition_start, observed_l1_commits):
        self.coverage.sample_checked_cpu(
            core, write, accepted_cycle > 0, completed_cycle > accepted_cycle
        )
        for transition in self.reference.transitions[transition_start:]:
            if transition["line"] != (addr & ~0x3F):
                continue
            for changed_core in range(2):
                old = transition["old_state"][changed_core]
                new = transition["new_state"][changed_core]
                if old != new and (changed_core, MESI_TO_ENCODING[new]) in observed_l1_commits:
                    self.coverage.sample_checked_event(
                        f"FS.MESI.{old}_TO_{new}", checked=True
                    )

    def _check_l2_victim_predictions(self, victim_start, event_start):
        """Compare inclusive victims with the independent cache model."""
        expected_victims = self.reference.l2_victim_selections[victim_start:]
        if not expected_victims:
            return
        events = self.monitor.events[event_start:]
        observed = [event for event in events
                    if event["source"] == "l2_victim" and
                    event["event_type"] == "select"]
        if len(observed) != len(expected_victims):
            raise AssertionError(
                "L2 victim selection count disagrees with independent model: "
                f"observed={len(observed)} expected={len(expected_victims)}"
            )

        dir_encoding = {"I": 0, "S": 1, "U": 2}
        mesi_encoding = {"I": 0, "S": 1, "E": 2, "M": 3}
        for prediction, actual in zip(expected_victims, observed):
            line = prediction["line"]
            directory = prediction["directory"]
            states = prediction["states"]
            if actual["address"] != line:
                raise AssertionError(
                    f"L2 victim mismatch: actual={actual['address']:#x} "
                    f"expected={line:#x}"
                )
            if actual["directory_state"] != dir_encoding[directory["state"]]:
                raise AssertionError(
                    f"L2 victim Directory state mismatch for {line:#x}: "
                    f"actual={actual['directory_state']} expected={directory}"
                )
            if actual["sharers"] != directory["sharers"]:
                raise AssertionError(
                    f"L2 victim sharers mismatch for {line:#x}: "
                    f"actual={actual['sharers']:#x} "
                    f"expected={directory['sharers']:#x}"
                )
            if directory["state"] == "U" and actual["owner"] != directory["owner"]:
                raise AssertionError(
                    f"L2 victim owner mismatch for {line:#x}: "
                    f"actual={actual['owner']} expected={directory['owner']}"
                )

            for core, state in enumerate(states):
                if state == "I":
                    continue
                invalidations = [event for event in events
                                 if event["source"] == "l1" and
                                 event["event_type"] == "metadata_commit" and
                                 event["core"] == core and
                                 event["address"] & ~0x3F == line and
                                 event["is_snoop"] and
                                 event["old_state"] == mesi_encoding[state] and
                                 event["new_state"] == mesi_encoding["I"]]
                if not invalidations:
                    raise AssertionError(
                        f"L2 victim {line:#x} did not invalidate modeled "
                        f"Core{core} {state} copy"
                    )

            if directory["state"] == "U":
                expected_words = [self.reference.word(line + beat * 8)
                                  for beat in range(8)]
                owner_beats = [event for event in events
                               if event["source"] == "coherence" and
                               event["event_type"] == "owner_data_beat" and
                               event["address"] & ~0x3F == line]
                if ([event["beat"] for event in owner_beats] != list(range(8)) or
                        [event["data"] for event in owner_beats] != expected_words or
                        [event["last"] for event in owner_beats] !=
                        [0] * 7 + [1]):
                    raise AssertionError(
                        f"L2 victim {line:#x} owner transfer disagrees with "
                        "the independent data model"
                    )
                if not any(event["source"] == "axi" and
                           event["event_type"] == "write_address" and
                           event["address"] == line for event in events):
                    raise AssertionError(
                        f"L2 victim {line:#x} with a live owner did not reach AXI AW"
                    )
                if any(self.axi.read_word(line + beat * 8) != expected_words[beat]
                       for beat in range(8)):
                    raise AssertionError(
                        f"L2 victim {line:#x} owner data was not preserved in memory"
                    )

    async def cpu_access(self, core, addr, *, write=False, data=0, mask=0xFF,
                         **driver_options):
        if addr >= 0x3000_0000:
            raise ValueError("cpu_access is for cacheable addresses; use cpu.access for MMIO")
        predicted, _ = self.reference.predict(core, addr, write=write,
                                               write_data=data, write_mask=mask)
        transition_start = len(self.reference.transitions)
        victim_start = len(self.reference.l2_victim_selections)
        event_start = len(self.monitor.events)
        result = await self.cpu.access(core, addr, write=write, data=data,
                                       mask=mask, **driver_options)
        self.reference.observe(core, addr, write=write, write_data=data,
                               write_mask=mask, response_data=result)
        self._check_l2_victim_predictions(victim_start, event_start)
        if not write and result != predicted:
            raise AssertionError(
                f"CPU{core} read {addr:#x} returned {result:#018x}, "
                f"reference expected {predicted:#018x}"
            )
        line = addr & ~0x3F
        observed_l1_commits = self._check_observed_commits(line, event_start)
        events = self.monitor.events[event_start:]
        accepted = any(event["source"] == "cpu" and
                       event["event_type"] == "request_accept" and
                       event["core"] == core and event["address"] == (addr & 0xFFFF_FFFF)
                       for event in events)
        completed = any(event["source"] == "cpu" and
                        event["event_type"] == "response_complete" and
                        event["core"] == core and event["address"] == (addr & 0xFFFF_FFFF)
                        for event in events)
        transaction = self.cpu.transactions[-1]
        accepted = accepted or (transaction["core"] == core and
                                transaction["addr"] == addr and
                                transaction["accepted_cycle"] > 0)
        completed = completed or (transaction["core"] == core and
                                  transaction["addr"] == addr and
                                  transaction["response_cycle"] >
                                  transaction["accepted_cycle"])
        self._credit_cpu(core, write, addr, transaction["accepted_cycle"],
                         transaction["response_cycle"], transition_start,
                         observed_l1_commits)
        return result

    async def cpu_access_pair(self, core0, core1, **driver_options):
        """Issue up to two cacheable requests through the single packed driver.

        This convenience checker intentionally requires different cache lines:
        same-line arbitration is legal, but its architectural serialization
        order must be modeled explicitly by a dedicated sequence.
        """
        requests = (core0, core1)
        present = [(core, req) for core, req in enumerate(requests)
                   if req is not None]
        if not present:
            raise ValueError("cpu_access_pair needs at least one request")
        lines = []
        expected = {}
        transition_start = len(self.reference.transitions)
        for core, req in present:
            if not isinstance(req, CpuRequest):
                raise TypeError("pair members must be CpuRequest or None")
            if req.addr >= 0x3000_0000:
                raise ValueError("cpu_access_pair is for cacheable addresses")
            line = req.addr & ~0x3F
            if line in lines:
                raise ValueError("paired checker requires distinct cache lines")
            lines.append(line)
            expected[core] = self.reference.predict(
                core, req.addr, write=req.write, write_data=req.data,
                write_mask=req.mask
            )[0]

        event_start = len(self.monitor.events)
        results = await self.cpu.access_pair(core0, core1, **driver_options)
        observed_by_line = {}
        for core, req in present:
            result = results[core]
            if not req.write and result != expected[core]:
                raise AssertionError(
                    f"CPU{core} paired read {req.addr:#x} returned "
                    f"{result:#018x}; reference expected {expected[core]:#018x}"
                )
            self.reference.observe(core, req.addr, write=req.write,
                                   write_data=req.data, write_mask=req.mask,
                                   response_data=result)
            line = req.addr & ~0x3F
            if line not in observed_by_line:
                observed_by_line[line] = self._check_observed_commits(
                    line, event_start
                )
            self._credit_cpu(core, req.write, req.addr,
                             self.cpu.last_pair_accepted_at[core],
                             self.cpu.last_pair_completed_at[core],
                             transition_start, observed_by_line[line])
        return results[0], results[1]

    def coverage_report(self):
        return self.coverage.report()

    def trace_records(self):
        """Return normalized, replay-oriented records from all four roles."""
        records = [dict(event) for event in self.monitor.events]
        accepted_events = defaultdict(deque)
        response_events = defaultdict(deque)
        for event in self.monitor.events:
            if event["source"] != "cpu":
                continue
            key = (event["core"], event["address"], event["write"])
            if event["event_type"] == "request_accept":
                accepted_events[key].append(event)
            elif event["event_type"] == "response_complete":
                response_events[key].append(event)

        for transaction in sorted(self.cpu.transactions,
                                  key=lambda item: (item["request_group"],
                                                    item["core"])):
            key = (transaction["core"], transaction["addr"],
                   transaction["write"])
            accepted = (accepted_events[key].popleft()
                        if accepted_events[key] else {})
            response_event = (response_events[key].popleft()
                              if response_events[key] else {})
            records.append({
                "cycle": accepted.get("cycle", transaction["accepted_cycle"]),
                "source": "cpu_driver",
                "event_type": "transaction", "core": transaction["core"],
                "address": transaction["addr"],
                "txn_id": response_event.get("txn_id"),
                "context_id": None,
                "request_group": transaction["request_group"],
                "payload": {"write": transaction["write"],
                            "write_data": transaction["write_data"],
                            "write_mask": transaction["mask"],
                            "response_data": transaction["response_data"],
                            "response_stall_cycles": transaction[
                                "response_stall_cycles"],
                            "request_delay_cycles": transaction[
                                "request_delay_cycles"]},
                "outcome": "completed",
                "completed_cycle": response_event.get(
                    "cycle", transaction["response_cycle"]),
                "reset_epoch": accepted.get(
                    "reset_epoch", response_event.get("reset_epoch", 0)),
            })
        for event in records:
            event.setdefault("core", None)
            event.setdefault("address", None)
            event.setdefault("txn_id", None)
            event.setdefault("context_id", None)
            event.setdefault("payload", None)
            event.setdefault("outcome", "observed")
            event.setdefault("reset_epoch", 0)
        return sorted(records, key=lambda event: (event.get("cycle", 0),
                                                   event.get("source", ""),
                                                   event.get("event_type", "")))
