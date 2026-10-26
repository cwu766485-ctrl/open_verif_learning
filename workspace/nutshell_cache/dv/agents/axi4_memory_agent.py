"""AXI4 five-channel memory model for the line-to-AXI adapter tests."""

from collections import Counter

from toffee import ClockCycles


class Axi4MemoryAgent:
    """Backpressure-capable AXI RAM with ID-routed, out-of-order responses.

    AR/AW/W ready and R/B consumer stalls are independently scheduled. Read
    bursts may interleave beats across IDs; B responses may complete out of
    order across IDs. Edge-sampled RTL wrapper taps check payload stability
    without racing Python against simulator scheduling.
    """

    BEATS = 8
    MASK64 = (1 << 64) - 1

    def __init__(self, dut, *, ar_stall_period=4, aw_stall_period=5,
                 w_stall_period=3, r_consumer_stall_period=6,
                 b_consumer_stall_period=7, read_error_beats=None,
                 write_error_ids=()):
        self.dut = dut
        self.periods = {
            "ar": ar_stall_period,
            "aw": aw_stall_period,
            "w": w_stall_period,
            "r_consumer": r_consumer_stall_period,
            "b_consumer": b_consumer_stall_period,
        }
        if any(period < 2 for period in self.periods.values()):
            raise ValueError("all AXI stall periods must be at least two")
        self.read_error_beats = dict(read_error_beats or {})
        self.write_error_ids = set(write_error_ids)
        self.cycle = 0
        self.stalls = Counter()
        self.read_accepts = []
        self.read_beat_accepts = []
        self.read_completion_order = []
        self.write_address_accepts = []
        self.write_beat_accepts = []
        self.write_completion_order = []
        self.line_read_errors = []
        self.line_write_errors = []
        self.reset_cancelled = {"reads": 0, "writes": 0}
        self.read_words = {}
        self.line_read_addr = {}
        self.line_read_next_beat = {}
        self._last_line_r_tap = None
        self.expected_write_words = {}
        self.write_rsp_by_id = {}
        self.peak_reads = 0
        self.peak_writes = 0
        self.errors = []

    @classmethod
    def read_word(cls, addr, beat):
        line = addr & ~0x3F
        return (0xA5A5000000000000 ^ (line << 8) ^ beat) & cls.MASK64

    @classmethod
    def write_word(cls, txn_id, beat):
        return (0xD17A000000000000 ^ (txn_id << 12) ^ (beat * 0x101)) & cls.MASK64

    async def run(self):
        d = self.dut
        for name in ("axi_arready", "axi_awready", "axi_wready",
                     "axi_rvalid", "axi_rid", "axi_rdata", "axi_rresp",
                     "axi_rlast", "axi_bvalid", "axi_bid", "axi_bresp",
                     "line_rd_data_ready", "line_wr_rsp_ready"):
            getattr(d, name).value = 0
        reads = {}
        read_order = 0
        read_rr = 0
        active_r = None
        aw_order = []
        aw_meta = {}
        w_id = None
        w_beat = 0
        active_b = None
        b_pending = []

        while True:
            self.cycle += 1
            if int(d.reset.value):
                self.reset_cancelled["reads"] += len(reads)
                self.reset_cancelled["writes"] += len(aw_meta)
                reads.clear()
                read_order = 0
                read_rr = 0
                active_r = None
                aw_order.clear()
                aw_meta.clear()
                w_id = None
                w_beat = 0
                active_b = None
                b_pending.clear()
                self.line_read_addr.clear()
                self.line_read_next_beat.clear()
                d.axi_arready.value = 0
                d.axi_awready.value = 0
                d.axi_wready.value = 0
                d.axi_rvalid.value = 0
                d.axi_bvalid.value = 0
                d.line_rd_data_ready.value = 0
                d.line_wr_rsp_ready.value = 0
                await ClockCycles(d, 1)
                continue

            ar_ready = int(self.cycle % self.periods["ar"] != 0)
            aw_ready = int(self.cycle % self.periods["aw"] != 0)
            w_ready = int(self.cycle % self.periods["w"] != 0)
            r_consumer_ready = int(
                self.cycle % self.periods["r_consumer"] != 0)
            b_consumer_ready = int(
                self.cycle % self.periods["b_consumer"] != 0)
            d.axi_arready.value = ar_ready
            d.axi_awready.value = aw_ready
            d.axi_wready.value = w_ready
            d.line_rd_data_ready.value = r_consumer_ready
            d.line_wr_rsp_ready.value = b_consumer_ready

            # Preserve an offered R/B payload until its corresponding READY.
            if active_r is None:
                eligible = [item for item in reads.values()
                            if item["due"] <= self.cycle]
                if eligible:
                    ordered = sorted(eligible, key=lambda item: item["order"])
                    pick = next((item for item in ordered
                                 if item["id"] > read_rr), ordered[0])
                    active_r = (pick["id"], pick["beat"])
            if active_r is None:
                d.axi_rvalid.value = 0
            else:
                txn_id, beat = active_r
                addr = reads[txn_id]["addr"]
                d.axi_rvalid.value = 1
                d.axi_rid.value = txn_id
                d.axi_rdata.value = self.read_words.get(
                    (addr, beat), self.read_word(addr, beat))
                d.axi_rresp.value = (
                    2 if self.read_error_beats.get(txn_id) == beat else 0
                )
                d.axi_rlast.value = int(beat == self.BEATS - 1)

            if active_b is None:
                ready_b = [item for item in b_pending if item["due"] <= self.cycle]
                if ready_b:
                    active_b = min(ready_b, key=lambda item: item["due"])
                    b_pending.remove(active_b)
            if active_b is None:
                d.axi_bvalid.value = 0
            else:
                d.axi_bvalid.value = 1
                d.axi_bid.value = active_b["id"]
                d.axi_bresp.value = 2 if active_b["id"] in self.write_error_ids else 0

            # ClockCycles returns on the active edge before nonblocking state
            # updates, so the live pins still describe that edge's transfer.
            await ClockCycles(d, 1)

            ar_payload = (
                int(d.axi_arid.value), int(d.axi_araddr.value),
                int(d.axi_arlen.value), int(d.axi_arsize.value),
                int(d.axi_arburst.value),
            )
            ar_fire = bool(int(d.axi_arvalid.value) and ar_ready)
            aw_payload = (
                int(d.axi_awid.value), int(d.axi_awaddr.value),
                int(d.axi_awlen.value), int(d.axi_awsize.value),
                int(d.axi_awburst.value),
            )
            aw_fire = bool(int(d.axi_awvalid.value) and aw_ready)
            w_payload = (
                int(d.axi_wdata.value), int(d.axi_wstrb.value),
                int(d.axi_wlast.value),
            )
            w_fire = bool(int(d.axi_wvalid.value) and w_ready)
            r_payload = None
            r_fire = bool(active_r is not None and int(d.axi_rready.value))
            if active_r is not None:
                r_payload = (
                    active_r[0], active_r[1], int(d.axi_rdata.value),
                    int(d.axi_rlast.value), int(d.axi_rresp.value),
                )
            line_r_payload = (
                int(d.line_rd_data_id.value), int(d.line_rd_data_beat.value),
                int(d.line_rd_data.value), int(d.line_rd_data_last.value),
                int(d.line_rd_data_error.value),
            )
            line_r_fire = bool(
                int(d.line_rd_data_valid.value) and r_consumer_ready
            )
            b_payload = None if active_b is None else active_b["id"]
            b_fire = bool(active_b is not None and int(d.axi_bready.value))
            line_b_payload = (
                int(d.line_wr_rsp_id.value), int(d.line_wr_rsp_error.value),
            )
            line_b_fire = bool(
                int(d.line_wr_rsp_valid.value) and b_consumer_ready
            )
            self.stalls["AR"] += int(d.axi_arvalid.value) * (1 - ar_ready)
            self.stalls["AW"] += int(d.axi_awvalid.value) * (1 - aw_ready)
            self.stalls["W"] += int(d.axi_wvalid.value) * (1 - w_ready)
            self.stalls["R"] += int(d.axi_rvalid.value) * (1 - int(d.axi_rready.value))
            self.stalls["B"] += int(d.axi_bvalid.value) * (1 - int(d.axi_bready.value))

            if ar_fire:
                txn_id, addr, arlen, arsize, arburst = ar_payload
                shape = (arlen, arsize, arburst, addr & 0x3F)
                if shape != (7, 3, 1, 0):
                    raise AssertionError(f"malformed AXI AR burst: {shape}, addr={addr:#x}")
                if (addr & 0xFFF) + 64 > 0x1000:
                    raise AssertionError(f"AXI AR burst crosses 4 KiB: addr={addr:#x}")
                if txn_id in reads:
                    raise AssertionError(
                        f"read ID {txn_id} reused while outstanding at cycle "
                        f"{self.cycle}, addr={addr:#x}, prior={reads[txn_id]}, "
                        f"accepted={self.read_accepts}"
                    )
                reads[txn_id] = {
                    "id": txn_id, "addr": addr, "beat": 0,
                    "order": read_order,
                    # Delay earlier requests longer so four IDs return out of order.
                    "due": self.cycle + 30 - 6 * read_order,
                }
                self.line_read_addr[txn_id] = addr
                self.line_read_next_beat[txn_id] = 0
                read_order += 1
                self.read_accepts.append((txn_id, addr, self.cycle))
                self.peak_reads = max(self.peak_reads, len(reads))

            if r_fire and r_payload is not None:
                txn_id, beat, data, r_last, r_resp = r_payload
                r_id = txn_id
                data &= self.MASK64
                addr = reads[txn_id]["addr"]
                expected = self.read_words.get((addr, beat), self.read_word(addr, beat))
                expected_resp = 2 if self.read_error_beats.get(txn_id) == beat else 0
                if (r_id != txn_id or data != expected or
                        r_last != int(beat == 7) or r_resp != expected_resp):
                    raise AssertionError(
                        f"R payload mismatch ID={r_id} beat={beat}: "
                        f"data={data:#x}/{expected:#x}, last={r_last}, "
                        f"resp={r_resp}/{expected_resp}"
                    )
                self.read_beat_accepts.append((txn_id, beat, data, self.cycle))
                if beat == 7:
                    self.read_completion_order.append(txn_id)
                    del reads[txn_id]
                else:
                    reads[txn_id]["beat"] = beat + 1
                    reads[txn_id]["due"] = self.cycle
                read_rr = txn_id
                active_r = None

            if line_r_fire:
                line_id, line_beat, line_data, line_last, line_error = line_r_payload
                if line_id not in self.line_read_addr:
                    raise AssertionError(f"line R response for unknown ID={line_id}")
                addr = self.line_read_addr[line_id]
                expected_beat = self.line_read_next_beat[line_id]
                expected = self.read_words.get(
                    (addr, expected_beat), self.read_word(addr, expected_beat)
                )
                expected_error = int(
                    self.read_error_beats.get(line_id) == expected_beat
                )
                expected_last = int(expected_error or expected_beat == 7)
                if (line_beat, line_data, line_last, line_error) != (
                        expected_beat, expected, expected_last, expected_error):
                    raise AssertionError(
                        f"line R routing mismatch ID={line_id}: got "
                        f"{(line_beat, line_data, line_last, line_error)}, "
                        f"expected {(expected_beat, expected, expected_last, expected_error)}"
                    )
                if expected_error:
                    self.line_read_errors.append((line_id, expected_beat, self.cycle))
                    del self.line_read_addr[line_id]
                    del self.line_read_next_beat[line_id]
                elif expected_last:
                    del self.line_read_addr[line_id]
                    del self.line_read_next_beat[line_id]
                else:
                    self.line_read_next_beat[line_id] = expected_beat + 1

            if aw_fire:
                txn_id, addr, awlen, awsize, awburst = aw_payload
                shape = (awlen, awsize, awburst, addr & 0x3F)
                if shape != (7, 3, 1, 0):
                    raise AssertionError(f"malformed AXI AW burst: {shape}, addr={addr:#x}")
                if (addr & 0xFFF) + 64 > 0x1000:
                    raise AssertionError(f"AXI AW burst crosses 4 KiB: addr={addr:#x}")
                if txn_id in aw_meta:
                    raise AssertionError(f"write ID {txn_id} reused while outstanding")
                aw_meta[txn_id] = {"addr": addr, "order": len(aw_order), "beats": 0}
                aw_order.append(txn_id)
                self.write_address_accepts.append((txn_id, addr, self.cycle))
                self.peak_writes = max(self.peak_writes, len(aw_meta))

            if w_fire:
                if not aw_order:
                    raise AssertionError("W beat arrived before any AW handshake")
                txn_id = aw_order[0]
                meta = aw_meta[txn_id]
                beat = meta["beats"]
                data = w_payload[0] & self.MASK64
                expected = self.expected_write_words[txn_id][beat]
                last = w_payload[2]
                strb = w_payload[1]
                if (data != expected or strb != 0xFF or last != int(beat == 7)):
                    raise AssertionError(
                        f"W burst mismatch ID={txn_id} beat={beat}: "
                        f"data={data:#x}/{expected:#x}, strb={strb:#x}, last={last}"
                    )
                self.write_beat_accepts.append((txn_id, beat, data, self.cycle))
                meta["beats"] += 1
                if beat == 7:
                    self.read_words.update({
                        (meta["addr"], index): value
                        for index, value in enumerate(self.expected_write_words[txn_id])
                    })
                    aw_order.pop(0)
                    # Later AWs get earlier due times, exercising ID-based B routing.
                    b_pending.append({
                        "id": txn_id,
                        "due": self.cycle + 220 - 50 * meta["order"],
                    })
                
            if b_fire and b_payload is not None:
                txn_id = b_payload
                if txn_id != active_b["id"]:
                    raise AssertionError(
                        f"B response ID changed: got {txn_id}, expected {active_b['id']}"
                    )
                if txn_id not in aw_meta or aw_meta[txn_id]["beats"] != 8:
                    raise AssertionError(f"B response before complete W burst: ID={txn_id}")
                expected_error = int(txn_id in self.write_error_ids)
                if not line_b_fire or line_b_payload != (txn_id, expected_error):
                    raise AssertionError(
                        f"line B response was not correctly routed for ID={txn_id}"
                    )
                if expected_error:
                    self.line_write_errors.append((txn_id, self.cycle))
                self.write_rsp_by_id[txn_id] = self.cycle
                self.write_completion_order.append(txn_id)
                del aw_meta[txn_id]
                active_b = None


