"""Directed-prelude and coverage-feedback sequences for full-system DV."""

from dataclasses import dataclass
import random

from dv.agents.coherent_cpu_agent import CpuRequest
from dv.sequences.cross_agent_sequences import run_owner_transfer_refill_apb


@dataclass(frozen=True)
class RandomConfig:
    seed: int
    operations: int = 100
    address_count: int = 12
    write_probability: float = 0.4
    pair_probability: float = 0.15
    response_stall_max: int = 2

    def __post_init__(self):
        if self.operations < 0:
            raise ValueError("operations must be non-negative")
        if self.address_count < 4:
            raise ValueError("address_count must be at least four")
        if not 0.0 <= self.write_probability <= 1.0:
            raise ValueError("write_probability must be in [0, 1]")
        if not 0.0 <= self.pair_probability <= 1.0:
            raise ValueError("pair_probability must be in [0, 1]")
        if self.response_stall_max < 0:
            raise ValueError("response_stall_max must be non-negative")


class CoverageFeedback:
    """Small legal scheduler that favors under-hit checked CPU bins."""

    def choose_core(self, coverage, rng):
        missing = [core for core in (0, 1)
                   if coverage.bins[f"FS.CPU.READ.CORE{core}"] == 0 or
                   coverage.bins[f"FS.CPU.WRITE.CORE{core}"] == 0]
        return rng.choice(missing) if missing else rng.randrange(2)

    def choose_write(self, coverage, core, probability, rng):
        if coverage.bins[f"FS.CPU.WRITE.CORE{core}"] == 0:
            return True
        if coverage.bins[f"FS.CPU.READ.CORE{core}"] == 0:
            return False
        return rng.random() < probability


class CoverageGuidedScenarioScheduler:
    """Select executable directed preludes from checked, currently unhit bins."""

    TARGETS = (
        {
            "scenario_id": "SC03_SC04_MESI_OWNER_PING_PONG",
            "bins": ("FS.MESI.I_TO_E", "FS.MESI.I_TO_S",
                     "FS.MESI.M_TO_S", "FS.MESI.S_TO_M"),
            "description": "Construct the shared-line ownership transitions.",
        },
        {
            "scenario_id": "SC08_SC14_DUAL_COLD_MISS_OOO",
            "bins": ("FS.MSHR.OCCUPANCY_2", "FS.AXI.READ_OUT_OF_ORDER"),
            "description": "Overlap distinct misses and reverse AXI R completion order.",
        },
        {
            "scenario_id": "CR01_OWNER_TRANSFER_REFILL_APB",
            "bins": ("FS.XAGENT.OWNER_TRANSFER_REFILL_APB",),
            "cross_bins": ("FS.CROSS.OWNER_TRANSFER_REFILL_APB_DISTINCT_SET",),
            "description": "Checked M-owner transfer overlaps a distinct AXI refill and APB sample.",
        },
        {
            "scenario_id": "SC01_SC02_SC03_SC04_SC05_MESI_TRANSITIONS",
            "bins": tuple(f"FS.MESI.{transition}" for transition in (
                "I_TO_E", "I_TO_S", "I_TO_M", "E_TO_M", "E_TO_S",
                "E_TO_I", "S_TO_M", "S_TO_I", "M_TO_S", "M_TO_I",
            )),
            "description": "Build all required legal MESI transitions using CPU traffic.",
        },
    )

    def next_target(self, coverage, rng):
        pending = [target for target in self.TARGETS
                   if any(coverage.bins[bin_id] == 0
                          for bin_id in target["bins"]) or
                   any(coverage.cross[bin_id] == 0
                       for bin_id in target.get("cross_bins", ()))]
        if not pending:
            return None
        # Prefer the target with the largest number of unhit required bins;
        # seeded choice among ties makes the scheduler reproducible.
        scores = [
            sum(coverage.bins[bin_id] == 0 for bin_id in item["bins"]) +
            sum(coverage.cross[bin_id] == 0
                for bin_id in item.get("cross_bins", ()))
            for item in pending
        ]
        highest = max(scores)
        return rng.choice([item for item, score in zip(pending, scores)
                           if score == highest])


async def run_legal_mesi_transition_scenario(env, addresses, rng):
    """Exercise the ten required legal MESI transitions through CPU ports.

    Expected data and stable permission state are advanced by the independent
    scoreboard in ``FullSystemEnv`` after every completed CPU transaction.
    The helper never writes DUT internals.
    """
    if len(addresses) < 3:
        raise ValueError("MESI transition scenario needs three independent lines")
    remote_line, shared_line, invalidate_line = addresses[:3]
    for address in (remote_line, shared_line, invalidate_line):
        env.seed_word(address, rng.getrandbits(64))

    # I->E, E->M, M->S, I->S, S->M and S->I.
    await env.cpu_access(0, remote_line)
    await env.cpu_access(0, remote_line, write=True,
                         data=rng.getrandbits(64), mask=0xFF)
    await env.cpu_access(1, remote_line)
    await env.cpu_access(1, remote_line, write=True,
                         data=rng.getrandbits(64), mask=0xFF)

    # I->M and remote-owner M->I.
    await env.cpu_access(0, remote_line, write=True,
                         data=rng.getrandbits(64), mask=0xFF)

    # E->S while the peer takes I->S.
    await env.cpu_access(0, shared_line)
    await env.cpu_access(1, shared_line)

    # E->I on a remote GetM; requester takes I->M.
    await env.cpu_access(0, invalidate_line)
    await env.cpu_access(1, invalidate_line, write=True,
                         data=rng.getrandbits(64), mask=0xFF)

    return {
        "scenario_id": "SC01_SC02_SC03_SC04_SC05_MESI_TRANSITIONS",
        "addresses": [remote_line, shared_line, invalidate_line],
        "required_bins": [
            "FS.MESI.I_TO_E", "FS.MESI.I_TO_S", "FS.MESI.I_TO_M",
            "FS.MESI.E_TO_M", "FS.MESI.E_TO_S", "FS.MESI.E_TO_I",
            "FS.MESI.S_TO_M", "FS.MESI.S_TO_I", "FS.MESI.M_TO_S",
            "FS.MESI.M_TO_I",
        ],
    }


class FullSystemRandomSequence:
    """Run deterministic MESI prelude, then seeded legal CPU perturbations."""

    def __init__(self, config: RandomConfig):
        self.config = config
        self.rng = random.Random(config.seed)
        self.feedback = CoverageFeedback()
        self.scheduler = CoverageGuidedScenarioScheduler()
        self.base = 0x0040_0000 + ((config.seed & 0xFF) << 16)
        self.addresses = [self.base + index * 0x40
                          for index in range(config.address_count)]
        self.history = []

    async def run(self, env):
        # Seed all backing words so every random word has an independent,
        # deterministic initial value in both the memory and reference model.
        for line_index, line in enumerate(self.addresses):
            for beat in range(8):
                address = line + beat * 8
                value = ((self.config.seed & 0xFFFF_FFFF) << 32) ^ \
                        (line_index << 12) ^ (beat * 0x0101_0101_0101_0101)
                env.seed_word(address, value)

        while target := self.scheduler.next_target(env.coverage, self.rng):
            if target["scenario_id"] == "SC01_SC02_SC03_SC04_SC05_MESI_TRANSITIONS":
                scenario = await run_legal_mesi_transition_scenario(
                    env, self.addresses[-3:], self.rng
                )
                missing = [bin_id for bin_id in target["bins"]
                           if env.coverage.bins[bin_id] == 0]
                if missing:
                    raise AssertionError(
                        f"checked MESI transition scenario missed bins: {missing}"
                    )
                self.history.append({"kind": "directed_target", **scenario,
                                     "description": target["description"]})
                continue

            if target["scenario_id"] == "SC03_SC04_MESI_OWNER_PING_PONG":
                shared_line = self.addresses[-1]
                await env.cpu_access(0, shared_line)
                await env.cpu_access(1, shared_line)
                await env.cpu_access(1, shared_line, write=True,
                                     data=self.rng.getrandbits(64), mask=0xFF)
                await env.cpu_access(0, shared_line)
                await env.cpu_access(0, shared_line, write=True,
                                     data=self.rng.getrandbits(64), mask=0xFF)
                self.history.append({"kind": "directed_target",
                                     "scenario_id": target["scenario_id"],
                                     "bins": list(target["bins"]),
                                     "description": target["description"]})
                continue

            if target["scenario_id"] == "SC08_SC14_DUAL_COLD_MISS_OOO":
                requests = (CpuRequest(self.addresses[0]),
                            CpuRequest(self.addresses[1]))
                ar_start = len(env.axi.read_addresses)
                completion_start = len(env.axi.read_completions)
                env.axi.force_next_reads_out_of_order(2)
                request_delays = {
                    0: self.rng.randrange(2),
                    1: self.rng.randrange(2),
                }
                results = await env.cpu_access_pair(
                    requests[0], requests[1],
                    request_delay_cycles=request_delays,
                    response_stall_cycles=self.rng.randrange(
                        self.config.response_stall_max + 1
                    ),
                )
                expected = tuple(env.reference.word(request.addr)
                                 for request in requests)
                if results != expected:
                    raise AssertionError(
                        f"dual cold miss data mismatch: {results} != {expected}"
                    )
                accepted = env.axi.read_addresses[ar_start:]
                completed = env.axi.read_completions[completion_start:]
                if len(accepted) != 2 or len(completed) != 2:
                    raise AssertionError(
                        f"dual cold miss did not produce two AXI reads: "
                        f"AR={accepted}, R={completed}"
                    )
                accepted_ids = [item[0] for item in accepted]
                completed_ids = [item[0] for item in completed]
                if completed_ids != list(reversed(accepted_ids)):
                    raise AssertionError(
                        f"AXI R did not complete out of order: "
                        f"AR={accepted_ids}, R={completed_ids}"
                    )
                if env.monitor.mshr_occupancy_histogram[2] == 0:
                    raise AssertionError("two refill MSHRs were never active together")
                env.coverage.sample_checked_event(
                    "FS.AXI.READ_OUT_OF_ORDER", checked=True
                )
                env.coverage.sample_checked_event(
                    "FS.MSHR.OCCUPANCY_2", checked=True
                )
                self.history.append({
                    "kind": "directed_target",
                    "scenario_id": target["scenario_id"],
                    "bins": list(target["bins"]),
                    "description": target["description"],
                    "request_delays": request_delays,
                    "forced_read_reorder_group": 2,
                    "accepted_ids": accepted_ids,
                    "completion_ids": completed_ids,
                })
                continue

            if target["scenario_id"] == "CR01_OWNER_TRANSFER_REFILL_APB":
                scenario_seed = self.rng.getrandbits(32)
                scenario = await run_owner_transfer_refill_apb(
                    env, seed=scenario_seed
                )
                missing_bins = [bin_id for bin_id in target["bins"]
                                if env.coverage.bins[bin_id] == 0]
                missing_cross = [bin_id for bin_id in target.get("cross_bins", ())
                                 if env.coverage.cross[bin_id] == 0]
                if missing_bins or missing_cross:
                    raise AssertionError(
                        f"checked CR01 sequence missed coverage: "
                        f"bins={missing_bins}, cross={missing_cross}"
                    )
                self.history.append({"kind": "directed_target", **scenario,
                                     "description": target["description"]})
                continue

            raise AssertionError(f"no builder for scenario {target['scenario_id']}")

        for operation in range(self.config.operations):
            if self.rng.random() < self.config.pair_probability:
                selected_lines = self.rng.sample(self.addresses, 2)
                requests = []
                for core, line in enumerate(selected_lines):
                    write = self.feedback.choose_write(
                        env.coverage, core, self.config.write_probability,
                        self.rng
                    )
                    word = line + self.rng.randrange(8) * 8
                    requests.append(CpuRequest(
                        addr=word, write=write,
                        data=self.rng.getrandbits(64) if write else 0,
                        mask=self.rng.randrange(1, 0x100) if write else 0xFF,
                    ))
                response_stall = self.rng.randrange(
                    self.config.response_stall_max + 1
                )
                item = {
                    "index": operation, "kind": "dual_lane",
                    "requests": [{"core": core, "address": request.addr,
                                  "write": request.write,
                                  "data": request.data,
                                  "mask": request.mask}
                                 for core, request in enumerate(requests)],
                    "response_stall_cycles": response_stall,
                }
                self.history.append(item)
                try:
                    await env.cpu_access_pair(
                        requests[0], requests[1],
                        response_stall_cycles=response_stall
                    )
                except Exception as error:
                    raise AssertionError(
                        f"full-system seed={self.config.seed:#x}, "
                        f"operation={operation}, recent={self.history[-8:]}"
                    ) from error
                continue

            core = self.feedback.choose_core(env.coverage, self.rng)
            write = self.feedback.choose_write(
                env.coverage, core, self.config.write_probability, self.rng
            )
            line = self.rng.choice(self.addresses)
            word = line + self.rng.randrange(8) * 8
            data = self.rng.getrandbits(64) if write else 0
            mask = self.rng.randrange(1, 0x100) if write else 0xFF
            response_stall = self.rng.randrange(
                self.config.response_stall_max + 1
            )
            item = {"index": operation, "core": core, "address": word,
                    "kind": "single", "write": write, "data": data, "mask": mask,
                    "response_stall_cycles": response_stall}
            self.history.append(item)
            try:
                await env.cpu_access(
                    core, word, write=write, data=data, mask=mask,
                    response_stall_cycles=response_stall
                )
            except Exception as error:
                raise AssertionError(
                    f"full-system seed={self.config.seed:#x}, "
                    f"operation={operation}, recent={self.history[-8:]}"
                ) from error
        return self.history


class ScenarioTemplate:
    """Trace identity for one reusable protocol-level scenario shape."""

    def __init__(self, scenario_id, required_bins, description):
        self.scenario_id = scenario_id
        self.required_bins = tuple(required_bins)
        self.description = description


DIRECTED_TEMPLATES = (
    ScenarioTemplate("MESI_OWNER_PING_PONG",
                     ("FS.MESI.I_TO_E", "FS.MESI.I_TO_S",
                      "FS.MESI.M_TO_S", "FS.MESI.S_TO_M"),
                     "Alternating reads and writes transfer a shared line."),
    ScenarioTemplate("DUAL_COLD_MISS",
                     ("FS.MSHR.OCCUPANCY_2", "FS.AXI.READ_OUT_OF_ORDER"),
                     "Two independent cold misses overlap and return by AXI ID."),
    ScenarioTemplate("MESI_LEGAL_TRANSITIONS",
                     tuple(f"FS.MESI.{transition}" for transition in (
                         "I_TO_E", "I_TO_S", "I_TO_M", "E_TO_M", "E_TO_S",
                         "E_TO_I", "S_TO_M", "S_TO_I", "M_TO_S", "M_TO_I",
                     )),
                     "Checked CPU traffic covers all ten required legal transitions."),
)
