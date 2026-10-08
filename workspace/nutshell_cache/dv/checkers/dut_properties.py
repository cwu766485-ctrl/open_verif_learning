"""Cycle-sampled invariants for the public cache DUT interface."""

from toffee import ClockCycles
from dv.common.transaction import SimpleBusRequest, SimpleBusResponse


class CacheDutProperties:
    def __init__(self, replacement_model=None):
        self.replacement_model = replacement_model
        self.outstanding_cpu_requests = 0
        self.accepted_cpu_requests = 0
        self.completed_cpu_responses = 0
        self.aborted_by_reset = 0
        self.sampled_cycles = 0
        self.forward_data_cycles = 0
        self.errors = []
        self.replacement_trace = []

    def on_reset(self):
        self.aborted_by_reset += self.outstanding_cpu_requests
        self.outstanding_cpu_requests = 0
        if self.replacement_model is not None:
            self.replacement_model.reset()

    def write(self, transaction):
        """Track requests/responses published only after driver handshakes."""
        if isinstance(transaction, SimpleBusRequest):
            self.accepted_cpu_requests += 1
            self.outstanding_cpu_requests += 1
        elif isinstance(transaction, SimpleBusResponse):
            if self.outstanding_cpu_requests == 0:
                raise AssertionError("CPU response handshake without an outstanding request")
            self.completed_cpu_responses += 1
            self.outstanding_cpu_requests -= 1

    def observe_victim_mask(self, valid, mask):
        self.sampled_cycles += 1
        if valid and (mask == 0 or mask & (mask - 1)):
            raise AssertionError(
                f"replacement selector mask must be one-hot, got 0x{mask:x}"
            )

    def observe_cycle(
        self,
        *,
        reset,
        req_valid,
        req_ready,
        rsp_valid,
        rsp_ready,
        victim_mask_valid,
        victim_mask,
    ):
        if reset:
            self.sampled_cycles += 1
            self.on_reset()
            return

        self.observe_victim_mask(victim_mask_valid, victim_mask)

        request_fire = bool(req_valid and req_ready)
        response_fire = bool(rsp_valid and rsp_ready)
        if request_fire:
            self.accepted_cpu_requests += 1
            self.outstanding_cpu_requests += 1
        if response_fire:
            if self.outstanding_cpu_requests == 0:
                raise AssertionError("CPU response handshake without an outstanding request")
            self.completed_cpu_responses += 1
            self.outstanding_cpu_requests -= 1

    async def monitor(self, dut):
        while True:
            # Snapshot reset before waiting for the edge. Reading it after
            # the clock event can see a reset write from the test coroutine
            # that occurred just after that edge, shifting the model phase.
            reset = int(dut.reset.value)
            await ClockCycles(dut, 1)
            try:
                if self.replacement_model is not None:
                    expected_mask = self.replacement_model.mask
                    self.replacement_model.tick(reset=bool(reset))
                else:
                    expected_mask = None
                actual_mask = int(dut.victim_way_mask.value)
                actual_valid = int(dut.victim_way_mask_valid.value)
                if int(dut.forward_data_valid.value):
                    self.forward_data_cycles += 1
                if expected_mask is not None:
                    self.replacement_trace.append((
                        self.sampled_cycles, reset, actual_valid,
                        self.replacement_model.state, expected_mask, actual_mask,
                    ))
                    self.replacement_trace = self.replacement_trace[-12:]
                self.observe_victim_mask(
                    valid=actual_valid,
                    mask=actual_mask,
                )
                if (
                    expected_mask is not None
                    and not reset
                    and actual_valid
                    and actual_mask != expected_mask
                ):
                    raise AssertionError(
                        "replacement LFSR mismatch: "
                        f"expected way mask 0x{expected_mask:x}, "
                        f"got 0x{actual_mask:x}; recent samples="
                        f"{self.replacement_trace!r}"
                    )
            except AssertionError as exc:
                self.errors.append(str(exc))
                return

    def assert_drained(self):
        assert not self.errors, "DUT cycle properties failed: " + "; ".join(self.errors)
        accounted = (
            self.completed_cpu_responses
            + self.aborted_by_reset
            + self.outstanding_cpu_requests
        )
        assert self.accepted_cpu_requests == accounted, (
            f"CPU request accounting mismatch: accepted={self.accepted_cpu_requests}, "
            f"completed={self.completed_cpu_responses}, reset-aborted={self.aborted_by_reset}, "
            f"outstanding={self.outstanding_cpu_requests}"
        )
        assert self.outstanding_cpu_requests == 0, (
            f"DUT monitor sees {self.outstanding_cpu_requests} request(s) "
            "without a response or reset cancellation"
        )
