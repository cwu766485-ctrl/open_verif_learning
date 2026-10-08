"""Cycle-sampled ready/valid stability checker used by SimpleBus agents."""


class ReadyValidChecker:
    def __init__(self, name="simplebus"):
        self.name = name
        self.errors = []
        self.stall_cycles = 0
        self.stall_cycles_by_channel = {}
        self._stalled_payload = {}

    def observe(self, channel, valid, ready, payload):
        """Call once per sampled clock edge for each ready/valid channel."""
        valid, ready = bool(valid), bool(ready)
        previous = self._stalled_payload.get(channel)
        if previous is not None and (not valid or tuple(payload) != previous):
            message = (
                f"{self.name}.{channel}: valid/payload changed while stalled; "
                f"expected valid=1 payload={previous}, got valid={int(valid)} payload={tuple(payload)}"
            )
            self.errors.append(message)
            raise AssertionError(message)

        if valid and not ready:
            self.stall_cycles += 1
            self.stall_cycles_by_channel[channel] = self.stall_cycles_by_channel.get(channel, 0) + 1
            self._stalled_payload[channel] = tuple(payload)
        else:
            self._stalled_payload.pop(channel, None)

    def reset(self):
        """Forget a stall across a reset, which is allowed to cancel a transfer."""
        self._stalled_payload.clear()

    def assert_no_errors(self):
        assert not self.errors, f"{self.name} protocol errors: {self.errors!r}"

    def write(self, _transaction):
        # Transaction-level protocol checking lives in CacheProtocolChecker.
        return None
