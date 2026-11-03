"""Independent correlation checks for integrated refill-MSHR lifecycles."""

from collections import defaultdict


LINE_MASK = 0xFFFF_FFC0


class MshrLifecycleChecker:
    """Correlate MSHR slot transitions with AXI, L2, Directory, and CPU events.

    MSHR transaction IDs are the externally visible slot IDs. The checker uses
    only sampled handshakes/monitor events and CPU-driver responses; it does
    not read the DUT's internal address/context arrays or the reference model.
    """

    @staticmethod
    def check(events, *, expected_lines, expected_words=None,
              expected_cores=None):
        expected_lines = {int(line) & LINE_MASK for line in expected_lines}
        if not expected_lines:
            raise AssertionError("MSHR lifecycle check needs expected refill lines")
        expected_words = {
            int(address) & LINE_MASK: int(value)
            for address, value in (expected_words or {}).items()
        }
        expected_cores = {
            int(address) & LINE_MASK: int(core)
            for address, core in (expected_cores or {}).items()
        }

        allocs = defaultdict(list)
        retires = defaultdict(list)
        ar_by_id = defaultdict(list)
        r_by_id_line = defaultdict(list)
        fill_beats = defaultdict(list)
        directory = defaultdict(list)
        grants = defaultdict(list)
        responses = defaultdict(list)

        for event in events:
            source, kind = event.get("source"), event.get("event_type")
            if source == "mshr" and kind in ("allocate", "retire"):
                target = allocs if kind == "allocate" else retires
                target[int(event["slot"])].append(event)
            elif source == "axi" and kind == "read_address":
                line = int(event["address"]) & LINE_MASK
                if line in expected_lines:
                    ar_by_id[int(event["txn_id"])].append(event)
            elif source == "axi" and kind == "read_beat":
                line = int(event["address"]) & LINE_MASK
                if line in expected_lines:
                    r_by_id_line[(int(event["txn_id"]), line)].append(event)
            elif source == "l2" and kind == "line_write_beat":
                line = int(event["address"]) & LINE_MASK
                if line in expected_lines and not event.get("owner_snoop_data", 0):
                    fill_beats[line].append(event)
            elif source == "directory" and kind == "request_accept":
                line = int(event["address"]) & LINE_MASK
                if line in expected_lines:
                    directory[line].append(event)
            elif source == "directory" and kind == "grant_accept":
                line = int(event["address"]) & LINE_MASK
                if line in expected_lines:
                    grants[line].append(event)
            elif source == "cpu" and kind == "response_complete":
                line = int(event["address"]) & LINE_MASK
                if line in expected_lines:
                    responses[line].append(event)

        ar_records = []
        for slot in range(4):
            slot_allocs = allocs[slot]
            slot_retires = retires[slot]
            slot_ars = ar_by_id[slot]
            if not (len(slot_allocs) == len(slot_retires) == len(slot_ars)):
                raise AssertionError(
                    f"MSHR slot {slot} lifecycle count mismatch: "
                    f"alloc={len(slot_allocs)} AR={len(slot_ars)} "
                    f"retire={len(slot_retires)}"
                )
            for index, (allocation, ar, retirement) in enumerate(
                    zip(slot_allocs, slot_ars, slot_retires)):
                if allocation["cycle"] > ar["cycle"] + 1:
                    raise AssertionError(
                        f"MSHR slot {slot} allocation is not correlated with "
                        f"AXI AR ID {slot}: alloc={allocation['cycle']} "
                        f"AR={ar['cycle']}"
                    )
                if retirement["cycle"] + 1 < ar["cycle"]:
                    raise AssertionError(
                        f"MSHR slot {slot} retired before its AXI request "
                        f"(lifecycle {index})"
                    )
                ar_records.append((slot, ar, allocation, retirement))

        observed_lines = [int(ar["address"]) & LINE_MASK
                          for _slot, ar, _alloc, _retire in ar_records]
        if len(observed_lines) != len(expected_lines) or \
                set(observed_lines) != expected_lines:
            raise AssertionError(
                f"refill MSHR/AXI line set mismatch: observed={observed_lines} "
                f"expected={sorted(expected_lines)}"
            )

        for slot, ar, allocation, retirement in ar_records:
            line = int(ar["address"]) & LINE_MASK
            # AXI IDs are reusable once a burst completes. Same-set L2 misses
            # are intentionally serialized by the set interlock, so several
            # complete line fills can legitimately reuse the same MSHR/AXI ID
            # in one observed event window. Correlate by both ID and address.
            beats = sorted(r_by_id_line[(slot, line)], key=lambda item: item["beat"])
            if len(beats) != 8:
                raise AssertionError(
                    f"MSHR slot {slot} line {line:#x}: expected 8 AXI R beats, "
                    f"observed {len(beats)}"
                )
            for beat_index, beat in enumerate(beats):
                if (int(beat["beat"]) != beat_index or
                        (int(beat["address"]) & 0xFFFF_FFFF) !=
                        ((line + beat_index * 8) & 0xFFFF_FFFF) or
                        bool(beat["last"]) != (beat_index == 7) or
                        int(beat["response"]) != 0):
                    raise AssertionError(
                        f"MSHR slot {slot} malformed R beat {beat_index}: {beat}"
                    )

            writes = sorted(fill_beats[line], key=lambda item: item["beat"])
            if len(writes) != 8 or [int(item["beat"]) for item in writes] != list(range(8)):
                raise AssertionError(
                    f"line {line:#x} L2 refill writes are incomplete or duplicated: "
                    f"{[item['beat'] for item in writes]}"
                )
            if writes[-1]["cycle"] > retirement["cycle"] + 1:
                raise AssertionError(
                    f"MSHR slot {slot} retired before L2 accepted its final refill beat"
                )
            if allocation["cycle"] > beats[0]["cycle"] + 1:
                raise AssertionError(
                    f"MSHR slot {slot} line {line:#x} accepted R data before allocation"
                )
            if beats[-1]["cycle"] > retirement["cycle"] + 1:
                raise AssertionError(
                    f"MSHR slot {slot} line {line:#x} retired before final AXI R beat"
                )
            if len(directory[line]) != 1:
                raise AssertionError(
                    f"line {line:#x} expected one accepted Directory miss, "
                    f"observed {len(directory[line])}"
                )
            if not grants[line]:
                raise AssertionError(f"line {line:#x} refill has no accepted Directory grant")
            if not responses[line]:
                raise AssertionError(f"line {line:#x} refill has no completed CPU response")
            request_cycle = int(directory[line][0]["cycle"])
            if request_cycle > int(ar["cycle"]) + 1:
                raise AssertionError(
                    f"line {line:#x} AXI refill started before Directory accepted the miss"
                )
            final_fill_cycle = int(writes[-1]["cycle"])
            if min(int(item["cycle"]) for item in grants[line]) < final_fill_cycle - 1:
                raise AssertionError(
                    f"line {line:#x} Directory grant preceded completed L2 refill"
                )
            if min(int(item["cycle"]) for item in responses[line]) < \
                    min(int(item["cycle"]) for item in grants[line]) - 1:
                raise AssertionError(
                    f"line {line:#x} CPU response preceded accepted Directory grant"
                )

            if line in expected_words:
                expected = int(expected_words[line]) & ((1 << 64) - 1)
                if not any(int(item["data"]) == expected for item in responses[line]):
                    raise AssertionError(
                        f"line {line:#x} CPU response did not return expected "
                        f"word {expected:#018x}"
                    )
            if line in expected_cores:
                expected_core = int(expected_cores[line])
                if not any(int(item["core"]) == expected_core
                           for item in responses[line]):
                    raise AssertionError(
                        f"line {line:#x} response did not route to core{expected_core}"
                    )

        return {
            "refill_lines": sorted(observed_lines),
            "mshr_allocations": len(ar_records),
            "mshr_retirements": sum(len(value) for value in retires.values()),
            "axi_read_beats": sum(
                len(r_by_id_line[(slot, line)])
                for slot, _ar, _alloc, _retire in ar_records
                for line in [int(_ar["address"]) & LINE_MASK]
            ),
            "l2_refill_beats": sum(len(fill_beats[line]) for line in expected_lines),
        }
