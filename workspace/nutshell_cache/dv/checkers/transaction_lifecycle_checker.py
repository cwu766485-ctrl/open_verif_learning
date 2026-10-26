"""Transaction-ID matching and exactly-once lifecycle checks for DV monitors."""


class TransactionLifecycleChecker:
    """Track accepted work until one matching completion or reset cancellation.

    IDs may be reused after retirement. While active, an ID is unique; a
    response must match the request's ID, address and operation. Reset retires
    each active entry once as canceled.
    """

    def __init__(self, name="transaction"):
        self.name = name
        self.pending = {}
        self.completed = []
        self.cancelled = []

    def accept(self, txn_id, addr, opcode):
        txn_id = int(txn_id)
        if txn_id in self.pending:
            raise AssertionError(
                f"{self.name}: ID {txn_id} reused while transaction is active"
            )
        self.pending[txn_id] = (int(addr), opcode)

    def complete(self, txn_id, addr, opcode):
        txn_id = int(txn_id)
        expected = self.pending.get(txn_id)
        observed = (int(addr), opcode)
        if expected is None:
            raise AssertionError(
                f"{self.name}: response for unknown or retired ID {txn_id}"
            )
        if observed != expected:
            raise AssertionError(
                f"{self.name}: response mismatch for ID {txn_id}: "
                f"observed={observed}, expected={expected}"
            )
        del self.pending[txn_id]
        self.completed.append((txn_id, *observed))

    def reset(self):
        self.cancelled.extend(
            (txn_id, addr, opcode)
            for txn_id, (addr, opcode) in sorted(self.pending.items())
        )
        self.pending.clear()

    def assert_drained(self):
        if self.pending:
            raise AssertionError(
                f"{self.name}: {len(self.pending)} transaction(s) remain active: "
                f"{self.pending}"
            )
