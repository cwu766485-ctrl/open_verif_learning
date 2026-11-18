"""Independent checks for the two-entry-per-core CPU miss trackers."""

from collections import defaultdict


LINE_MASK = 0xFFFF_FFC0


class L1MshrLifecycleChecker:
    """Check CPU acceptance, L1 MSHR lifetime, lower traffic and responses.

    The checker consumes only sampled interface/monitor events. It does not
    inspect the DUT's MSHR arrays or use the architectural model as an oracle.
    """

    @staticmethod
    def check(events, *, expected_requests, first_response_must_follow_all_allocs=True):
        expected = {
            (int(core), int(address) & 0xFFFF_FFFF): int(value) & ((1 << 64) - 1)
            for core, address, value in expected_requests
        }
        if len(expected) != len(expected_requests):
            raise AssertionError("expected CPU requests must have unique core/address pairs")

        accepts = defaultdict(list)
        allocations = defaultdict(list)
        retires = defaultdict(list)
        directory_requests = defaultdict(list)
        grants = defaultdict(list)
        axi_addresses = defaultdict(list)
        axi_beats = defaultdict(list)
        responses = defaultdict(list)

        for event in events:
            source, kind = event.get("source"), event.get("event_type")
            if source == "cpu" and kind == "request_accept":
                key = (int(event["core"]), int(event["address"]) & 0xFFFF_FFFF)
                if key in expected:
                    accepts[key].append(event)
            elif source == "l1_mshr" and kind in ("allocate", "retire"):
                key = (int(event["core"]), int(event["address"]) & 0xFFFF_FFFF)
                if key in expected:
                    (allocations if kind == "allocate" else retires)[key].append(event)
            elif source == "directory" and kind == "request_accept":
                line = int(event["address"]) & LINE_MASK
                for core, address in expected:
                    if core == int(event["source_id"]) and (address & LINE_MASK) == line:
                        directory_requests[(core, address)].append(event)
            elif source == "directory" and kind == "grant_accept":
                # Grant destination is the requester core.
                line = int(event["address"]) & LINE_MASK
                for core, address in expected:
                    if core == int(event["destination"]) and (address & LINE_MASK) == line:
                        grants[(core, address)].append(event)
            elif source == "axi" and kind == "read_address":
                line = int(event["address"]) & LINE_MASK
                for core, address in expected:
                    if (address & LINE_MASK) == line:
                        axi_addresses[(core, address)].append(event)
            elif source == "axi" and kind == "read_beat":
                line = int(event["address"]) & LINE_MASK
                for core, address in expected:
                    if (address & LINE_MASK) == line:
                        axi_beats[(core, address)].append(event)
            elif source == "cpu" and kind == "response_complete":
                key = (int(event["core"]), int(event["address"]) & 0xFFFF_FFFF)
                if key in expected:
                    responses[key].append(event)

        for key in expected:
            for label, records in (
                ("CPU acceptance", accepts[key]),
                ("L1 MSHR allocation", allocations[key]),
                ("L1 MSHR retirement", retires[key]),
                ("Directory request", directory_requests[key]),
                ("Directory grant", grants[key]),
                ("AXI AR", axi_addresses[key]),
                ("CPU response", responses[key]),
            ):
                if len(records) != 1:
                    raise AssertionError(
                        f"core{key[0]} address {key[1]:#x}: expected exactly one "
                        f"{label}, observed {len(records)}"
                    )
            if len(axi_beats[key]) != 8:
                raise AssertionError(
                    f"core{key[0]} address {key[1]:#x}: expected 8 AXI R beats, "
                    f"observed {len(axi_beats[key])}"
                )

            alloc = allocations[key][0]
            retire = retires[key][0]
            request = directory_requests[key][0]
            grant = grants[key][0]
            ar = axi_addresses[key][0]
            response = responses[key][0]
            if int(request["txn_id"]) != int(grant["txn_id"]):
                raise AssertionError(f"Directory request/grant ID mismatch for {key}")
            if int(request["source_id"]) != key[0] or int(grant["destination"]) != key[0]:
                raise AssertionError(f"Directory routed {key} to the wrong core")
            if (int(ar["address"]) & LINE_MASK) != (key[1] & LINE_MASK):
                raise AssertionError(f"AXI AR line mismatch for {key}")
            beat_records = sorted(axi_beats[key], key=lambda item: int(item["beat"]))
            for index, beat in enumerate(beat_records):
                if (int(beat["txn_id"]) != int(ar["txn_id"]) or
                        int(beat["beat"]) != index or
                        int(beat["address"]) != ((key[1] & LINE_MASK) + index * 8) or
                        bool(beat["last"]) != (index == 7) or
                        int(beat["response"]) != 0):
                    raise AssertionError(f"malformed/misrouted AXI beat for {key}: {beat}")
            if int(response["data"]) != expected[key]:
                raise AssertionError(
                    f"core{key[0]} response data mismatch for {key[1]:#x}: "
                    f"got {response['data']:#x}, expected {expected[key]:#x}"
                )
            if (int(alloc["cycle"]) > int(accepts[key][0]["cycle"]) + 2 or
                    int(retire["cycle"]) < int(response["cycle"]) - 1):
                raise AssertionError(f"L1 MSHR lifecycle is not tied to CPU request {key}")

        per_core = defaultdict(list)
        for key, records in responses.items():
            per_core[key[0]].append((int(records[0]["cycle"]), key[1]))
        for core, completions in per_core.items():
            expected_order = [
                address for c, address, _value in expected_requests if int(c) == core
            ]
            observed_order = [address for _cycle, address in sorted(completions)]
            if observed_order != expected_order:
                raise AssertionError(
                    f"core{core} miss response order changed: {observed_order}, "
                    f"expected FIFO {expected_order}"
                )

        if first_response_must_follow_all_allocs:
            last_allocation = max(int(records[0]["cycle"])
                                  for records in allocations.values())
            first_response = min(int(records[0]["cycle"])
                                 for records in responses.values())
            if first_response <= last_allocation:
                raise AssertionError(
                    "a CPU response completed before all expected L1 MSHRs allocated"
                )

        return {
            "checked_requests": len(expected),
            "allocation_cycles": {
                f"core{core}:0x{address:08x}": allocations[(core, address)][0]["cycle"]
                for core, address in expected
            },
            "response_cycles": {
                f"core{core}:0x{address:08x}": responses[(core, address)][0]["cycle"]
                for core, address in expected
            },
            "directory_txn_ids": {
                f"core{core}:0x{address:08x}": directory_requests[(core, address)][0]["txn_id"]
                for core, address in expected
            },
            "axi_ids": {
                f"core{core}:0x{address:08x}": axi_addresses[(core, address)][0]["txn_id"]
                for core, address in expected
            },
        }
