"""Passive transaction and gray-box event monitor for the AXI cache top."""

from collections import Counter
from collections import deque

from toffee import ClockCycles


def _bits(value):
    return int(value.value)


class FullSystemMonitor:
    """Collect only handshakes and existing read-only RTL observations."""

    def __init__(self, dut):
        self.dut = dut
        self.cycle = 0
        self.reset_epoch = 0
        self.events = []
        self.counts = Counter()
        self.stall_cycles = Counter()
        self.mshr_occupancy_histogram = Counter()
        self.directory_context_histogram = Counter()
        self.max_mshr_occupancy = 0
        self.max_directory_contexts = 0
        self._axi_reads = {}
        self._axi_writes = {}
        self._axi_write_order = deque()
        self._mmio_requests = deque()
        self._reset_active = False
        # These are observation shadows, updated only by the existing commit
        # probes. They annotate transitions; they are not expected-state
        # sources for the architectural scoreboard.
        self._l1_committed_state = {}
        self._directory_committed_state = {}
        self._last_mshr_bitmap = 0
        self._last_directory_bitmap = 0
        self._last_l2_fill_active = 0
        self._last_victim_valid = 0

    def _event(self, source, kind, **fields):
        event = {"cycle": self.cycle, "reset_epoch": self.reset_epoch,
                 "source": source,
                 "event_type": kind, **fields}
        self.events.append(event)
        self.counts[f"{source}.{kind}"] += 1

    def record_apb_access(self, transaction):
        """Record the APB Master's sampled PREADY handshake.

        Toffee may resume the driver and passive monitor in different scheduler
        groups on the same edge. The APB driver calls this only after sampling
        PREADY in Access, so the event cannot be lost when pins are retired.
        """
        self._event("apb", "access_complete", address=transaction["addr"],
                    payload={"write": transaction["write"],
                             "read_data": transaction["rdata"],
                             "slverr": transaction["slverr"]},
                    outcome="error" if transaction["slverr"] else "ok")

    def record_mmio_event(self, event_type, transaction):
        """Record the MMIO slave's sampled request/response handshakes."""
        if event_type == "request_accept":
            request = transaction
            address = request["addr"]
            self._mmio_requests.append(request)
            payload = {"write": request["write"], "size": request["size"],
                       "mask": request["mask"], "write_data": request["wdata"]}
        elif event_type == "response_complete":
            request = transaction["request"]
            address = request["addr"]
            if self._mmio_requests:
                self._mmio_requests.popleft()
            payload = {"write": request["write"], "read_data": transaction["data"]}
        else:
            raise ValueError(f"unsupported MMIO event {event_type!r}")
        self._event("mmio", event_type, address=address, payload=payload)

    def record_axi_event(self, event_type, transaction):
        """Record AXI handshakes sampled by the protocol-checking memory agent.

        Verilator/Toffee can schedule the passive pin sampler before or after
        the slave agent on the same clock edge. The agent's callback preserves
        the exact handshake already used for protocol checking, while this
        monitor remains responsible for RTL-internal observations and sampled
        stall/valid-gap signals.
        """
        cycle = transaction["cycle"]
        txn_id = transaction["txn_id"]
        if event_type == "read_address":
            self._axi_reads[txn_id] = {
                "address": transaction["address"], "beat": 0,
            }
            self._event("axi", event_type, cycle=cycle, txn_id=txn_id,
                        address=transaction["address"],
                        length=transaction["length"],
                        payload={"size": transaction["size"],
                                 "burst": transaction["burst"]})
        elif event_type == "read_beat":
            self._event("axi", event_type, cycle=cycle, txn_id=txn_id,
                        address=transaction["address"],
                        beat=transaction["beat"], data=transaction["data"],
                        last=transaction["last"],
                        response=transaction["response"])
            if transaction["last"]:
                self._axi_reads.pop(txn_id, None)
            elif txn_id in self._axi_reads:
                self._axi_reads[txn_id]["beat"] += 1
        elif event_type == "write_address":
            self._axi_writes[txn_id] = {
                "address": transaction["address"], "beat": 0,
            }
            self._axi_write_order.append(txn_id)
            self._event("axi", event_type, cycle=cycle, txn_id=txn_id,
                        address=transaction["address"],
                        length=transaction["length"],
                        payload={"size": transaction["size"],
                                 "burst": transaction["burst"]})
        elif event_type == "write_beat":
            self._event("axi", event_type, cycle=cycle, txn_id=txn_id,
                        address=transaction["address"],
                        beat=transaction["beat"], data=transaction["data"],
                        strobe=transaction["strobe"], last=transaction["last"])
            if transaction["last"]:
                if self._axi_write_order:
                    self._axi_write_order.popleft()
            elif txn_id in self._axi_writes:
                self._axi_writes[txn_id]["beat"] += 1
        elif event_type == "write_response":
            context = self._axi_writes.pop(txn_id, None)
            self._event("axi", event_type, cycle=cycle, txn_id=txn_id,
                        address=(context["address"] if context else
                                 transaction["address"]),
                        response=transaction["response"])
        else:
            raise ValueError(f"unsupported AXI observation {event_type!r}")

    def sample_once(self):
        d = self.dut
        if _bits(d.reset):
            if not self._reset_active:
                cancelled = {
                    "axi_reads": len(self._axi_reads),
                    "axi_writes": len(self._axi_writes),
                    "mmio_requests": len(self._mmio_requests),
                }
                if any(cancelled.values()):
                    self._event("system", "reset_cancel", payload=cancelled)
                self._axi_reads.clear()
                self._axi_writes.clear()
                self._axi_write_order.clear()
                self._mmio_requests.clear()
                self._l1_committed_state.clear()
                self._directory_committed_state.clear()
                self._last_mshr_bitmap = 0
                self._last_directory_bitmap = 0
                self._last_l2_fill_active = 0
                self._last_victim_valid = 0
                self._reset_active = True
                self.reset_epoch += 1
            return
        self._reset_active = False

        req_valid, req_ready = _bits(d.cpu_req_valid), _bits(d.cpu_req_ready)
        req_write, req_addr = _bits(d.cpu_req_write), _bits(d.cpu_req_addr)
        req_wdata, req_wmask = _bits(d.cpu_req_wdata), _bits(d.cpu_req_wmask)
        resp_valid, resp_ready = _bits(d.cpu_resp_valid), _bits(d.cpu_resp_ready)
        resp_addr, resp_write = _bits(d.cpu_resp_addr), _bits(d.cpu_resp_write)
        resp_data, resp_id = _bits(d.cpu_resp_rdata), _bits(d.cpu_resp_txn_id)
        victim_targets = _bits(d.monitor_victim_pending_targets)
        victim_addr = _bits(d.monitor_victim_addr) & 0xFFFF_FFC0
        for core in range(2):
            bit = 1 << core
            if req_valid & req_ready & bit:
                self._event("cpu", "request_accept", core=core,
                            address=(req_addr >> (32 * core)) & 0xFFFF_FFFF,
                            write=(req_write >> core) & 1,
                            payload={"write_data": (req_wdata >> (64 * core)) &
                                     ((1 << 64) - 1),
                                     "write_mask": (req_wmask >> (8 * core)) & 0xFF})
            if resp_valid & resp_ready & bit:
                self._event("cpu", "response_complete", core=core,
                            address=(resp_addr >> (32 * core)) & 0xFFFF_FFFF,
                            write=(resp_write >> core) & 1,
                            data=(resp_data >> (64 * core)) & ((1 << 64) - 1),
                            txn_id=(resp_id >> (3 * core)) & 0x7)

            if (_bits(d.monitor_l1_commit_valid) >> core) & 1:
                address = ((_bits(d.monitor_l1_commit_addr) >> (32 * core))
                           & 0xFFFF_FFFF)
                line = address & 0xFFFF_FFC0
                new_state = (_bits(d.monitor_l1_commit_state) >> (2 * core)) & 3
                old_state = self._l1_committed_state.get((core, line), 0)
                is_snoop = (_bits(d.monitor_l1_commit_is_snoop) >> core) & 1
                self._event("l1", "metadata_commit", core=core,
                            address=address, old_state=old_state,
                            new_state=new_state,
                            cause="snoop" if is_snoop else "non_snoop",
                            is_snoop=is_snoop)
                self._l1_committed_state[(core, line)] = new_state
            if (_bits(d.monitor_snoop_accept_valid) >> core) & 1:
                snoop_addr = ((_bits(d.monitor_snoop_accept_addr) >> (32 * core))
                              & 0xFFFF_FFFF)
                self._event("snoop", "accept", core=core,
                            address=snoop_addr,
                            opcode=(_bits(d.monitor_snoop_accept_opcode) >> (2 * core)) & 3,
                            txn_id=(_bits(d.monitor_snoop_accept_txn_id) >> (3 * core)) & 7)
                if (victim_targets & (1 << core) and
                        snoop_addr & 0xFFFF_FFC0 == victim_addr):
                    self._event("l2_victim", "snoop_accept", core=core,
                                address=victim_addr)
            if (_bits(d.monitor_snoop_rsp_valid) >> core) & 1 and \
                    (_bits(d.monitor_snoop_rsp_ready) >> core) & 1:
                self._event("snoop", "response", core=core,
                            txn_id=(_bits(d.monitor_snoop_rsp_txn_id) >> (3 * core)) & 7,
                            opcode=(_bits(d.monitor_snoop_rsp_opcode) >> (2 * core)) & 3)

        if _bits(d.monitor_dir_req_accept_valid):
            self._event("directory", "request_accept",
                        address=_bits(d.monitor_dir_req_accept_addr),
                        source_id=_bits(d.monitor_dir_req_accept_src_id),
                        opcode=_bits(d.monitor_dir_req_accept_opcode),
                        txn_id=_bits(d.monitor_dir_req_accept_txn_id))
        if (_bits(d.monitor_dir_req_live_valid) and
                not _bits(d.monitor_dir_req_live_ready)):
            self.stall_cycles["directory_request"] += 1
            self._event("directory", "request_stall",
                        address=_bits(d.monitor_dir_req_live_addr))
        if (_bits(d.monitor_dir_xfer_live_valid) and
                not _bits(d.monitor_dir_xfer_live_ready)):
            self.stall_cycles["directory_transfer"] += 1
            self._event("directory", "transfer_stall")
        if _bits(d.monitor_dir_grant_accept_valid):
            self._event("directory", "grant_accept",
                        address=_bits(d.monitor_dir_grant_accept_addr),
                        destination=_bits(d.monitor_dir_grant_accept_dst),
                        opcode=_bits(d.monitor_dir_grant_accept_opcode),
                        txn_id=_bits(d.monitor_dir_grant_accept_txn_id))
        if _bits(d.monitor_dir_commit_valid):
            address = _bits(d.monitor_dir_commit_addr)
            new_entry = {
                "state": _bits(d.monitor_dir_commit_state),
                "sharers": _bits(d.monitor_dir_commit_sharers),
                "owner": _bits(d.monitor_dir_commit_owner),
            }
            old_entry = self._directory_committed_state.get(
                address & 0xFFFF_FFC0,
                {"state": 0, "sharers": 0, "owner": 0},
            )
            self._event("directory", "metadata_commit",
                        address=address, old_state=old_entry["state"],
                        old_sharers=old_entry["sharers"],
                        old_owner=old_entry["owner"], **new_entry)
            self._directory_committed_state[address & 0xFFFF_FFC0] = new_entry
        if _bits(d.monitor_owner_data_valid):
            self._event("coherence", "owner_data_beat",
                        core=_bits(d.monitor_owner_data_core),
                        address=_bits(d.monitor_owner_data_addr),
                        beat=_bits(d.monitor_owner_data_beat_idx),
                        data=_bits(d.monitor_owner_data),
                        last=_bits(d.monitor_owner_data_last))
        if _bits(d.monitor_l2_lookup_valid):
            self._event("l2", "lookup", address=_bits(d.monitor_l2_lookup_addr),
                        hit=_bits(d.monitor_l2_lookup_hit))
        fill_active = _bits(d.monitor_l2_fill_active)
        if fill_active != self._last_l2_fill_active:
            self._event("l2", "refill_start" if fill_active else "refill_end")
            self._last_l2_fill_active = fill_active
        if _bits(d.monitor_l2_line_wr_valid) and _bits(d.monitor_l2_line_wr_ready):
            self._event("l2", "line_write_beat",
                        address=_bits(d.monitor_l2_line_wr_addr),
                        beat=_bits(d.monitor_l2_line_wr_beat),
                        owner_snoop_data=_bits(d.monitor_dir_snoop_data_to_l2))
        victim_valid = _bits(d.monitor_l2_victim_valid)
        new_victims = victim_valid & ~self._last_victim_valid
        if new_victims:
            # These wrapper probes describe one shared L2 victim. The valid
            # vector is a widened scalar, while address/state/owner/dirty are
            # scalar fields and sharers is the actual two-core bitmap. Do not
            # decode them as per-core packed arrays.
            self._event(
                "l2_victim", "select",
                address=_bits(d.monitor_l2_victim_addr) & 0xFFFF_FFFF,
                directory_state=_bits(d.monitor_l2_victim_dir_state) & 3,
                sharers=_bits(d.monitor_l2_victim_sharers) & 3,
                owner=_bits(d.monitor_l2_victim_owner_id) & 1,
                dirty=_bits(d.monitor_l2_victim_dirty) & 1)
        self._last_victim_valid = victim_valid
        if _bits(d.monitor_dir_snoop_valid):
            self._event("directory", "snoop_offer",
                        data_to_l2=_bits(d.monitor_dir_snoop_data_to_l2))
        if _bits(d.monitor_snoop_set_conflict):
            self._event("directory", "same_set_conflict")

        mshr = _bits(d.monitor_mem_mshr_valid).bit_count()
        contexts = _bits(d.monitor_directory_active_contexts).bit_count()
        mshr_bitmap = _bits(d.monitor_mem_mshr_valid)
        directory_bitmap = _bits(d.monitor_directory_active_contexts)
        for slot in range(4):
            bit = 1 << slot
            if (mshr_bitmap ^ self._last_mshr_bitmap) & bit:
                self._event("mshr", "allocate" if mshr_bitmap & bit else "retire",
                            slot=slot, occupancy=mshr)
            if (directory_bitmap ^ self._last_directory_bitmap) & bit:
                self._event("directory_context",
                            "allocate" if directory_bitmap & bit else "retire",
                            context=slot, occupancy=contexts)
        self._last_mshr_bitmap = mshr_bitmap
        self._last_directory_bitmap = directory_bitmap
        self.mshr_occupancy_histogram[mshr] += 1
        self.directory_context_histogram[contexts] += 1
        self.max_mshr_occupancy = max(self.max_mshr_occupancy, mshr)
        self.max_directory_contexts = max(self.max_directory_contexts, contexts)
        for channel, valid_name, ready_name, payload_names, outstanding in (
            ("AR", "axi_arvalid", "axi_arready",
             ("axi_arid", "axi_araddr", "axi_arlen"), len(self._axi_reads)),
            ("R", "axi_rvalid", "axi_rready",
             ("axi_rid", "axi_rdata", "axi_rlast"), len(self._axi_reads)),
            ("AW", "axi_awvalid", "axi_awready",
             ("axi_awid", "axi_awaddr", "axi_awlen"), len(self._axi_writes)),
            ("W", "axi_wvalid", "axi_wready",
             ("axi_wdata", "axi_wstrb", "axi_wlast"), len(self._axi_writes)),
            ("B", "axi_bvalid", "axi_bready",
             ("axi_bid", "axi_bresp"), len(self._axi_writes)),
        ):
            if _bits(getattr(d, valid_name)) and not _bits(getattr(d, ready_name)):
                self.stall_cycles[channel] += 1
                self._event("axi", "stall", channel=channel,
                            outstanding=outstanding,
                            payload=[_bits(getattr(d, name))
                                     for name in payload_names])
        if not _bits(d.axi_rvalid) and self._axi_reads:
            self._event("axi", "read_valid_gap",
                        outstanding=len(self._axi_reads))

    async def run(self):
        while True:
            await ClockCycles(self.dut, 1)
            self.cycle += 1
            self.sample_once()
