"""AXI4 memory slave for the integrated CoherentCacheAxiSubsystem top.

Unlike ``Axi4MemoryAgent`` (which checks the standalone adapter's line-side
contract), this agent owns only the five AXI channels. It keeps byte-addressed
backing contents, checks the fixed 64-byte INCR line bursts, permits R
interleaving by ID, preserves the AXI4 global W ordering, and holds R/B
payloads stable until handshake.
"""

from collections import Counter, deque

from toffee import ClockCycles


class Axi4BackingMemoryAgent:
    DATA_MASK = (1 << 64) - 1
    BEATS_PER_LINE = 8

    def __init__(self, dut, *, latency=4, ar_stall_period=5,
                 aw_stall_period=7, w_stall_period=4,
                 r_valid_gap_period=0,
                 read_reorder_window=6,
                 read_error_addrs=None, write_error_addrs=None):
        if latency < 0:
            raise ValueError("latency must be non-negative")
        periods = (ar_stall_period, aw_stall_period, w_stall_period)
        if any(period < 2 for period in periods):
            raise ValueError("AXI stall periods must be at least two")
        if r_valid_gap_period < 0 or r_valid_gap_period == 1:
            raise ValueError("R valid gap period must be zero or at least two")
        if read_reorder_window < 1:
            raise ValueError("read_reorder_window must be positive")
        self.dut = dut
        # Optional passive observation hook.  The agent calls it at the same
        # sampled handshakes it validates, avoiding scheduler-order races when
        # a separate monitor samples the pins on the same edge.
        self.observation_callback = None
        self.latency = latency
        self.read_reorder_window = read_reorder_window
        self.periods = dict(zip(("AR", "AW", "W"), periods))
        # This is source-side response pacing, not receiver backpressure. The
        # integrated DUT currently keeps RREADY asserted outside reset.
        self.r_valid_gap_period = r_valid_gap_period
        self.read_error_addrs = set(read_error_addrs or ())
        self.write_error_addrs = set(write_error_addrs or ())
        self.memory = {}  # aligned byte address -> 64-bit word
        self.seeded_words = {}
        self.cycle = 0
        self.stalls = Counter()
        self.valid_gaps = Counter()
        self.read_addresses = []
        self.read_beats = []
        self.read_completions = []
        self.write_addresses = []
        self.write_beats = []
        self.write_completions = []
        self.peak_reads = 0
        self.peak_writes = 0
        self.reset_cancelled = Counter()
        self.errors = []
        self._read_order = 0
        self._forced_reorder_remaining = 0
        self._forced_reorder_group = []
        self._write_order = 0
        self._held_master_payload = {}
        self._held_slave_payload = {}

    def force_next_reads_out_of_order(self, count=2):
        """Schedule the next accepted read group to complete in reverse order.

        This is a stimulus control for coverage-guided concurrency scenarios.
        It delays group members until all requested AR handshakes have arrived,
        then returns later accepted IDs first. It does not modify DUT state or
        weaken AXI protocol checking.
        """
        if count < 2:
            raise ValueError("out-of-order read group needs at least two IDs")
        if self._forced_reorder_remaining or self._forced_reorder_group:
            raise RuntimeError("an AXI read reorder group is already armed")
        self._forced_reorder_remaining = count

    def seed_word(self, addr, value):
        word = addr & ~0x7
        value &= self.DATA_MASK
        self.memory[word] = value
        self.seeded_words[word] = value

    def read_word(self, addr):
        return self.memory.get(addr & ~0x7, 0)

    @staticmethod
    def _merge_bytes(old, new, strobe):
        value = old
        for lane in range(8):
            if (strobe >> lane) & 1:
                mask = 0xFF << (8 * lane)
                value = (value & ~mask) | (new & mask)
        return value & Axi4BackingMemoryAgent.DATA_MASK

    def _check_master_stability(self, d):
        current = {
            "AR": (int(d.axi_arvalid.value), int(d.axi_arready.value),
                   (int(d.axi_arid.value), int(d.axi_araddr.value),
                    int(d.axi_arlen.value), int(d.axi_arsize.value),
                    int(d.axi_arburst.value))),
            "AW": (int(d.axi_awvalid.value), int(d.axi_awready.value),
                   (int(d.axi_awid.value), int(d.axi_awaddr.value),
                    int(d.axi_awlen.value), int(d.axi_awsize.value),
                    int(d.axi_awburst.value))),
            "W": (int(d.axi_wvalid.value), int(d.axi_wready.value),
                  (int(d.axi_wdata.value), int(d.axi_wstrb.value),
                   int(d.axi_wlast.value))),
        }
        for channel, (valid, ready, payload) in current.items():
            previous = self._held_master_payload.get(channel)
            if previous is not None and (not valid or payload != previous):
                raise AssertionError(
                    f"AXI {channel} payload changed before handshake: "
                    f"held={previous}, now valid={valid} payload={payload}"
                )
            if valid and not ready:
                self._held_master_payload[channel] = payload
            else:
                self._held_master_payload.pop(channel, None)

    def _check_slave_stability(self, d):
        current = {
            "R": (int(d.axi_rvalid.value), int(d.axi_rready.value),
                  (int(d.axi_rid.value), int(d.axi_rdata.value),
                   int(d.axi_rresp.value), int(d.axi_rlast.value))),
            "B": (int(d.axi_bvalid.value), int(d.axi_bready.value),
                  (int(d.axi_bid.value), int(d.axi_bresp.value))),
        }
        for channel, (valid, ready, payload) in current.items():
            previous = self._held_slave_payload.get(channel)
            if previous is not None and (not valid or payload != previous):
                raise AssertionError(
                    f"AXI {channel} payload changed before handshake: "
                    f"held={previous}, now valid={valid} payload={payload}"
                )
            if valid and not ready:
                self._held_slave_payload[channel] = payload
            else:
                self._held_slave_payload.pop(channel, None)

    def _validate_burst(self, channel, txn_id, addr, length, size, burst):
        if (length, size, burst, addr & 0x3F) != (7, 3, 1, 0):
            raise AssertionError(
                f"malformed AXI {channel} line burst: ID={txn_id} "
                f"addr={addr:#x} len={length} size={size} burst={burst}"
            )
        if (addr & 0xFFF) + 64 > 0x1000:
            raise AssertionError(f"AXI {channel} burst crosses 4KiB: {addr:#x}")

    async def run(self):
        d = self.dut
        for name in ("axi_arready", "axi_awready", "axi_wready",
                     "axi_rvalid", "axi_rid", "axi_rdata", "axi_rresp",
                     "axi_rlast", "axi_bvalid", "axi_bid", "axi_bresp"):
            getattr(d, name).value = 0

        reads = {}             # ID -> accepted burst and current R beat
        active_r = None        # (ID, beat), retained during R backpressure
        read_rr = -1
        aw_meta = {}           # ID -> write burst state
        aw_order = deque()     # AXI4 W has no WID: consume AW order
        b_pending = []
        active_b = None

        while True:
            self.cycle += 1
            if int(d.reset.value):
                self.reset_cancelled["reads"] += len(reads)
                self.reset_cancelled["writes"] += len(aw_meta)
                self.reset_cancelled["b_responses"] += len(b_pending)
                self.reset_cancelled["b_responses"] += int(active_b is not None)
                reads.clear()
                aw_meta.clear()
                aw_order.clear()
                b_pending.clear()
                active_r = None
                active_b = None
                read_rr = -1
                self._forced_reorder_remaining = 0
                self._forced_reorder_group.clear()
                self._held_master_payload.clear()
                self._held_slave_payload.clear()
                d.axi_arready.value = 0
                d.axi_awready.value = 0
                d.axi_wready.value = 0
                d.axi_rvalid.value = 0
                d.axi_bvalid.value = 0
                await ClockCycles(d, 1)
                continue

            ar_ready = int(self.cycle % self.periods["AR"] != 0)
            aw_ready = int(self.cycle % self.periods["AW"] != 0)
            w_ready = int(self.cycle % self.periods["W"] != 0)
            d.axi_arready.value = ar_ready
            d.axi_awready.value = aw_ready
            d.axi_wready.value = w_ready

            if active_r is None:
                eligible = [entry for entry in reads.values()
                            if entry["due"] <= self.cycle]
                if eligible:
                    ordered = sorted(eligible, key=lambda entry: entry["order"])
                    selected = next((entry for entry in ordered
                                     if entry["id"] > read_rr), ordered[0])
                    active_r = (selected["id"], selected["beat"])
            if active_r is None:
                d.axi_rvalid.value = 0
            else:
                rid, beat = active_r
                addr = reads[rid]["addr"] + beat * 8
                inject_gap = (
                    self.r_valid_gap_period >= 2 and
                    self.cycle % self.r_valid_gap_period == 0 and
                    "R" not in self._held_slave_payload
                )
                d.axi_rvalid.value = int(not inject_gap)
                if inject_gap:
                    self.valid_gaps["R"] += 1
                d.axi_rid.value = rid
                d.axi_rdata.value = self.read_word(addr)
                d.axi_rresp.value = 2 if addr in self.read_error_addrs else 0
                d.axi_rlast.value = int(beat == self.BEATS_PER_LINE - 1)

            if active_b is None:
                due = [item for item in b_pending if item["due"] <= self.cycle]
                if due:
                    active_b = min(due, key=lambda item: item["due"])
                    b_pending.remove(active_b)
            if active_b is None:
                d.axi_bvalid.value = 0
            else:
                d.axi_bvalid.value = 1
                d.axi_bid.value = active_b["id"]
                d.axi_bresp.value = 2 if active_b["addr"] in self.write_error_addrs else 0

            await ClockCycles(d, 1)
            self._check_master_stability(d)
            self._check_slave_stability(d)

            ar_fire = bool(int(d.axi_arvalid.value) and ar_ready)
            aw_fire = bool(int(d.axi_awvalid.value) and aw_ready)
            w_fire = bool(int(d.axi_wvalid.value) and w_ready)
            r_fire = bool(active_r is not None and int(d.axi_rvalid.value) and
                           int(d.axi_rready.value))
            b_fire = bool(active_b is not None and int(d.axi_bready.value))
            self.stalls["AR"] += int(d.axi_arvalid.value) * (1 - ar_ready)
            self.stalls["AW"] += int(d.axi_awvalid.value) * (1 - aw_ready)
            self.stalls["W"] += int(d.axi_wvalid.value) * (1 - w_ready)
            self.stalls["R"] += int(d.axi_rvalid.value) * (1 - int(d.axi_rready.value))
            self.stalls["B"] += int(d.axi_bvalid.value) * (1 - int(d.axi_bready.value))

            if ar_fire:
                rid, addr = int(d.axi_arid.value), int(d.axi_araddr.value)
                self._validate_burst("AR", rid, addr, int(d.axi_arlen.value),
                                     int(d.axi_arsize.value), int(d.axi_arburst.value))
                if rid in reads:
                    raise AssertionError(f"AXI read ID reused while active: {rid}")
                order = self._read_order
                self._read_order += 1
                reads[rid] = {"id": rid, "addr": addr, "beat": 0,
                              "order": order,
                              "due": self.cycle + self.latency +
                                    (3 - order % 4) * self.read_reorder_window}
                if self._forced_reorder_remaining:
                    # Hold early members until the target batch is complete;
                    # then make the latest accepted ID eligible first.
                    reads[rid]["due"] = float("inf")
                    self._forced_reorder_group.append(rid)
                    self._forced_reorder_remaining -= 1
                    if self._forced_reorder_remaining == 0:
                        for reverse_index, group_id in enumerate(
                                reversed(self._forced_reorder_group)):
                            reads[group_id]["due"] = (
                                self.cycle + self.latency +
                                reverse_index * self.read_reorder_window
                            )
                        self._forced_reorder_group.clear()
                self.read_addresses.append((rid, addr, self.cycle))
                self.peak_reads = max(self.peak_reads, len(reads))
                if self.observation_callback:
                    self.observation_callback("read_address", {
                        "cycle": self.cycle, "txn_id": rid,
                        "address": addr, "length": int(d.axi_arlen.value),
                        "size": int(d.axi_arsize.value),
                        "burst": int(d.axi_arburst.value),
                    })

            if r_fire:
                rid, beat = active_r
                entry = reads[rid]
                addr = entry["addr"] + beat * 8
                payload = (int(d.axi_rid.value), int(d.axi_rdata.value),
                           int(d.axi_rlast.value), int(d.axi_rresp.value))
                expected = (rid, self.read_word(addr),
                            int(beat == self.BEATS_PER_LINE - 1),
                            2 if addr in self.read_error_addrs else 0)
                if payload != expected:
                    raise AssertionError(f"AXI R payload mismatch: {payload} != {expected}")
                if payload[3]:
                    self.errors.append({"channel": "R", "id": rid,
                                        "address": addr,
                                        "response": payload[3]})
                self.read_beats.append((rid, beat, payload[1], self.cycle))
                if self.observation_callback:
                    self.observation_callback("read_beat", {
                        "cycle": self.cycle, "txn_id": rid,
                        "address": addr, "beat": beat, "data": payload[1],
                        "last": payload[2], "response": payload[3],
                    })
                read_rr = rid
                active_r = None
                if beat == self.BEATS_PER_LINE - 1:
                    self.read_completions.append((rid, entry["addr"], self.cycle))
                    del reads[rid]
                else:
                    entry["beat"] += 1
                    entry["due"] = self.cycle

            if aw_fire:
                wid, addr = int(d.axi_awid.value), int(d.axi_awaddr.value)
                self._validate_burst("AW", wid, addr, int(d.axi_awlen.value),
                                     int(d.axi_awsize.value), int(d.axi_awburst.value))
                if wid in aw_meta:
                    raise AssertionError(f"AXI write ID reused while active: {wid}")
                meta = {"id": wid, "addr": addr, "beats": 0,
                        "order": self._write_order, "data": []}
                self._write_order += 1
                aw_meta[wid] = meta
                aw_order.append(wid)
                self.write_addresses.append((wid, addr, self.cycle))
                self.peak_writes = max(self.peak_writes, len(aw_meta))
                if self.observation_callback:
                    self.observation_callback("write_address", {
                        "cycle": self.cycle, "txn_id": wid,
                        "address": addr, "length": int(d.axi_awlen.value),
                        "size": int(d.axi_awsize.value),
                        "burst": int(d.axi_awburst.value),
                    })

            if w_fire:
                if not aw_order:
                    raise AssertionError("AXI W beat accepted before any AW")
                wid = aw_order[0]
                meta = aw_meta[wid]
                beat = meta["beats"]
                data, strobe, last = (int(d.axi_wdata.value),
                                      int(d.axi_wstrb.value),
                                      int(d.axi_wlast.value))
                expected_last = int(beat == self.BEATS_PER_LINE - 1)
                if last != expected_last:
                    raise AssertionError(
                        f"AXI WLAST mismatch ID={wid} beat={beat}: {last}"
                    )
                word_addr = meta["addr"] + beat * 8
                old = self.read_word(word_addr)
                self.memory[word_addr] = self._merge_bytes(old, data, strobe)
                meta["data"].append(data)
                meta["beats"] += 1
                self.write_beats.append((wid, beat, data, strobe, self.cycle))
                if self.observation_callback:
                    self.observation_callback("write_beat", {
                        "cycle": self.cycle, "txn_id": wid,
                        "address": word_addr, "beat": beat, "data": data,
                        "strobe": strobe, "last": last,
                    })
                if expected_last:
                    aw_order.popleft()
                    delay = self.latency + max(0, 12 - (meta["order"] % 4) * 4)
                    b_pending.append({"id": wid, "addr": meta["addr"],
                                      "due": self.cycle + delay})

            if b_fire:
                wid = int(d.axi_bid.value)
                if wid != active_b["id"] or wid not in aw_meta:
                    raise AssertionError(f"AXI B response has no matching AW/W: {wid}")
                if aw_meta[wid]["beats"] != self.BEATS_PER_LINE:
                    raise AssertionError(f"AXI B before final W beat: ID={wid}")
                expected = 2 if aw_meta[wid]["addr"] in self.write_error_addrs else 0
                if int(d.axi_bresp.value) != expected:
                    raise AssertionError(f"AXI BRESP mismatch for ID={wid}")
                if expected:
                    self.errors.append({"channel": "B", "id": wid,
                                        "address": aw_meta[wid]["addr"],
                                        "response": expected})
                self.write_completions.append((wid, aw_meta[wid]["addr"], self.cycle))
                if self.observation_callback:
                    self.observation_callback("write_response", {
                        "cycle": self.cycle, "txn_id": wid,
                        "address": aw_meta[wid]["addr"],
                        "response": int(d.axi_bresp.value),
                    })
                del aw_meta[wid]
                active_b = None
