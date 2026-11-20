"""Independent checker for L1 miss-context and owner-snoop overlap."""

from collections import defaultdict


LINE_MASK = 0xFFFF_FFC0


class L1MshrCollisionChecker:
    """Check the externally observed owner-snoop/data evidence.

    ``expect_putm`` is reserved for scenarios that deliberately overlap a
    victim writeback with the snoop. The default checks the common legal case
    where a resident M owner supplies a remote GetS while independent misses
    remain outstanding at that L1.
    """

    @staticmethod
    def check(events, *, dirty_line, owner_core, requester_core,
              expected_owner_words, expect_putm=False, max_event_skew=80,
              concurrent_miss_lines=(), concurrent_miss_core=None,
              putm_line=None):
        line = int(dirty_line) & LINE_MASK
        victim_line = line if putm_line is None else int(putm_line) & LINE_MASK
        miss_core = (int(owner_core) if concurrent_miss_core is None else
                     int(concurrent_miss_core))
        putm = [event for event in events
                if event.get("source") == "directory" and
                event.get("event_type") == "request_accept" and
                int(event.get("source_id", -1)) == int(owner_core) and
                int(event.get("opcode", -1)) == 0b101 and
                int(event.get("address", -1)) & LINE_MASK == victim_line]
        snoop_requests = [event for event in events
                          if event.get("source") == "snoop" and
                          event.get("event_type") == "accept" and
                          int(event.get("core", -1)) == int(owner_core) and
                          int(event.get("address", -1)) & LINE_MASK == line]
        expected_putm_count = 1 if expect_putm else 0
        if len(putm) != expected_putm_count:
            raise AssertionError(
                f"expected {expected_putm_count} owner PutM requests for "
                f"{line:#x}, observed {len(putm)}"
            )
        if len(snoop_requests) != 1:
            raise AssertionError(
                f"expected one owner snoop for {line:#x}, "
                f"observed {len(snoop_requests)}"
            )

        snoop = snoop_requests[0]
        snoop_responses = [event for event in events
                           if event.get("source") == "snoop" and
                           event.get("event_type") == "response" and
                           int(event.get("core", owner_core)) == int(owner_core) and
                           int(event.get("txn_id", -1)) ==
                           int(snoop.get("txn_id", -2))]
        if len(snoop_responses) != 1:
            raise AssertionError(
                f"owner snoop txn {snoop.get('txn_id')} has "
                f"{len(snoop_responses)} responses"
            )

        skew = None
        if expect_putm:
            skew = abs(int(putm[0]["cycle"]) - int(snoop["cycle"]))
            if skew > int(max_event_skew):
                raise AssertionError(
                    f"PutM and owner snoop fell outside one race window: "
                    f"skew={skew}"
                )

        beats = defaultdict(list)
        for event in events:
            if (event.get("source") == "coherence" and
                    event.get("event_type") == "owner_data_beat" and
                    int(event.get("core", -1)) == int(owner_core) and
                    int(event.get("address", -1)) & LINE_MASK == line):
                beats[int(event["beat"])].append(event)
        if sorted(beats) != list(range(8)) or any(len(value) != 1
                                                  for value in beats.values()):
            raise AssertionError(
                f"owner data stream is not exactly eight beats: "
                f"{dict(beats)}"
            )
        for index, expected in enumerate(expected_owner_words):
            event = beats[index][0]
            if (int(event["data"]) != int(expected) or
                    bool(event["last"]) != (index == 7)):
                raise AssertionError(
                    f"owner beat {index} mismatch: observed={event}, "
                    f"expected_data={int(expected):#x}"
                )

        if concurrent_miss_lines:
            first_beat = min(int(event["cycle"])
                             for beat_events in beats.values()
                             for event in beat_events)
            last_beat = max(int(event["cycle"])
                            for beat_events in beats.values()
                            for event in beat_events)
            for miss_line in concurrent_miss_lines:
                miss_line = int(miss_line) & LINE_MASK
                allocations = [event for event in events
                               if event.get("source") == "l1_mshr" and
                               event.get("event_type") == "allocate" and
                               int(event.get("core", -1)) == miss_core and
                               int(event.get("address", -1)) & LINE_MASK == miss_line]
                retirements = [event for event in events
                               if event.get("source") == "l1_mshr" and
                               event.get("event_type") == "retire" and
                               int(event.get("core", -1)) == miss_core and
                               int(event.get("address", -1)) & LINE_MASK == miss_line]
                directory = [event for event in events
                             if event.get("source") == "directory" and
                             event.get("event_type") == "request_accept" and
                             int(event.get("source_id", -1)) == miss_core and
                             int(event.get("address", -1)) & LINE_MASK == miss_line]
                if len(allocations) != 1 or len(directory) != 1:
                    raise AssertionError(
                        f"miss {miss_line:#x} must have one L1 allocation and "
                        f"Directory request; got {len(allocations)}/"
                        f"{len(directory)}"
                    )
                alloc_cycle = int(allocations[0]["cycle"])
                dir_cycle = int(directory[0]["cycle"])
                if alloc_cycle > first_beat or dir_cycle > first_beat:
                    raise AssertionError(
                        f"miss {miss_line:#x} was not live at owner-data beat 0: "
                        f"alloc={alloc_cycle}, directory={dir_cycle}, "
                        f"first_beat={first_beat}"
                    )
                if any(int(event["cycle"]) < last_beat for event in retirements):
                    raise AssertionError(
                        f"miss {miss_line:#x} retired before owner-data stream ended"
                    )

        # Directory/Snoop event routing identifies the requester. The snoop
        # monitor records the target core; the matching CPU miss is checked by
        # the caller's lifecycle checker and response scoreboard.
        return {
            "dirty_line": line,
            "putm_victim_line": victim_line if putm else None,
            "owner_core": int(owner_core),
            "requester_core": int(requester_core),
            "putm_cycle": int(putm[0]["cycle"]) if putm else None,
            "snoop_cycle": int(snoop["cycle"]),
            "snoop_txn_id": int(snoop["txn_id"]),
            "owner_data_beats": 8,
            "putm_snoop_cycle_skew": skew,
            "concurrent_miss_core": miss_core,
            "concurrent_miss_lines": [int(value) & LINE_MASK
                                       for value in concurrent_miss_lines],
        }
