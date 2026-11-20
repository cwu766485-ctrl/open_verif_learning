"""Check reset cancellation and address-associated ID reuse evidence."""

from collections import defaultdict


LINE_MASK = 0xFFFF_FFC0


class L1MshrResetReuseChecker:
    """Verify two accepted misses are cancelled and safely replayed after reset.

    The checker relies on independently sampled CPU, L1 MSHR, Directory and AXI
    events. IDs are compared within each protocol layer; equal numeric IDs
    across different layers are not assumed to have the same meaning.
    """

    @staticmethod
    def check(events, *, core, addresses, pre_reset_epoch,
              post_reset_epoch, expected_cancelled_mshrs,
              expected_cancelled_axi_reads):
        core = int(core)
        addresses = tuple(int(address) & 0xFFFF_FFFF for address in addresses)
        if len(addresses) != 2 or len({address & LINE_MASK for address in addresses}) != 2:
            raise AssertionError("reset/reuse check requires two distinct cache lines")

        reset_events = [event for event in events
                        if event.get("source") == "system" and
                        event.get("event_type") == "reset_cancel" and
                        int(event.get("reset_epoch", -1)) == int(pre_reset_epoch)]
        if len(reset_events) != 1:
            raise AssertionError(
                f"expected one cancellation event for epoch {pre_reset_epoch}, "
                f"observed {len(reset_events)}"
            )
        cancelled = reset_events[0].get("payload", {})
        if int(cancelled.get("l1_mshr_entries", -1)) != int(expected_cancelled_mshrs):
            raise AssertionError(f"reset cancelled wrong number of L1 MSHRs: {cancelled}")
        if int(cancelled.get("axi_reads", -1)) != int(expected_cancelled_axi_reads):
            raise AssertionError(f"reset cancelled wrong number of AXI reads: {cancelled}")

        def records(source, kind, address, epoch):
            line = address & LINE_MASK
            matches = []
            for event in events:
                if (event.get("source") != source or
                        event.get("event_type") != kind or
                        int(event.get("reset_epoch", -1)) != int(epoch)):
                    continue
                if source == "directory" and int(event.get("source_id", -1)) != core:
                    continue
                if source == "l1_mshr" and int(event.get("core", -1)) != core:
                    continue
                if int(event.get("address", -1)) & LINE_MASK == line:
                    matches.append(event)
            return matches

        protocol_events = {
            "l1_mshr": ("allocate", "txn_id"),
            "directory": ("request_accept", "txn_id"),
            "axi": ("read_address", "txn_id"),
        }
        compared = defaultdict(dict)
        for address in addresses:
            line = address & LINE_MASK
            for source, (kind, id_field) in protocol_events.items():
                before = records(source, kind, address, pre_reset_epoch)
                after = records(source, kind, address, post_reset_epoch)
                if len(before) != 1 or len(after) != 1:
                    raise AssertionError(
                        f"{source}.{kind} for line {line:#x}: expected one event "
                        f"in each epoch, got {len(before)}/{len(after)}"
                    )
                before_id = int(before[0][id_field])
                after_id = int(after[0][id_field])
                if before_id != after_id:
                    raise AssertionError(
                        f"{source} ID for line {line:#x} was not reused after reset: "
                        f"{before_id} -> {after_id}"
                    )
                compared[f"{source}_id"][hex(line)] = before_id

        reset_cycle = int(reset_events[0]["cycle"])
        stale = [event for event in events
                 if event.get("source") == "cpu" and
                 event.get("event_type") == "response_complete" and
                 int(event.get("core", -1)) == core and
                 int(event.get("address", -1)) & LINE_MASK in
                 {address & LINE_MASK for address in addresses} and
                 reset_cycle < int(event.get("cycle", -1)) and
                 int(event.get("reset_epoch", -1)) == int(post_reset_epoch)]
        if len(stale) != len(addresses):
            raise AssertionError(
                f"expected one post-reset response per replayed line, got {len(stale)}"
            )

        return {
            "core": core,
            "addresses": list(addresses),
            "pre_reset_epoch": int(pre_reset_epoch),
            "post_reset_epoch": int(post_reset_epoch),
            "cancelled_l1_mshrs": len(addresses),
            "cancelled_axi_reads": int(expected_cancelled_axi_reads),
            "reused_ids_by_protocol": dict(compared),
            "post_reset_responses": len(stale),
        }
