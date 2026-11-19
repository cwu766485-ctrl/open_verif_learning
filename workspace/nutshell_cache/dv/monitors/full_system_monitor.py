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
        # The L1 CPU miss queue is a different resource from the downstream
        # refill MSHR bank and the Directory transaction contexts. Keep each
        # population separate so queued CPU misses are not reported as AXI
        # requests that have already been issued.
        self.l1_mshr_occupancy_histogram = Counter()
        self.l1_mshr_active_histogram = Counter()
        self.l1_mshr_issued_histogram = Counter()
        self.l1_mshr_per_core_histogram = {
            0: Counter(), 1: Counter(),
        }
        self.l1_mshr_active_per_core_histogram = {
            0: Counter(), 1: Counter(),
        }
        self.l1_mshr_issued_per_core_histogram = {
            0: Counter(), 1: Counter(),
        }
        self.max_mshr_occupancy = 0
        self.max_directory_contexts = 0
        self.max_l1_mshr_occupancy = 0
        self.max_l1_mshr_active = 0
        self.max_l1_mshr_issued = 0
        self.max_l1_mshr_per_core = {0: 0, 1: 0}
        self.max_l1_mshr_active_per_core = {0: 0, 1: 0}
        self.max_l1_mshr_issued_per_core = {0: 0, 1: 0}
        self._axi_reads = {}
        self._axi_writes = {}
        self._axi_write_order = deque()
        # CPU drivers sample ready/valid from active coroutines.  The passive
        # pin sampler may observe the same edge one scheduler tick later, so
        # use driver observations as the handshake authority and reconcile
        # nearby passive samples by full response identity.
        self._cpu_driver_responses = deque(maxlen=16)
        self._mmio_requests = deque()
        self._reset_active = False
        self._fatal_active = False
        # These are observation shadows, updated only by the existing commit
        # probes. They annotate transitions; they are not expected-state
        # sources for the architectural scoreboard.
        self._l1_committed_state = {}
        self._directory_committed_state = {}
        self._last_mshr_bitmap = 0
        self._last_directory_bitmap = 0
        self._last_l1_mshr_bitmap = 0
        self._last_l1_mshr_active_bitmap = 0
        self._last_l1_mshr_issued_bitmap = 0
        self._last_l1_mshr_addr = [0] * 4
        self._last_l1_mshr_txn_id = [0] * 4
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

    def record_cpu_request_accept(self, core, address, write, *, cycle=None):
        """Record a CPU driver's sampled ready/valid acceptance.

        Most CPU handshakes are also seen by ``sample_once``. A few directed
        tests intentionally drive a lane directly while holding another miss
        open; Toffee may resume that driver before the passive sampler on the
        same edge. Preserve the handshake observed by the driver and suppress
        a duplicate if the passive sample has already recorded it.
        """
        accepted_cycle = self.cycle if cycle is None else int(cycle)
        address = int(address) & 0xFFFF_FFFF
        write = int(bool(write))
        if any(event.get("source") == "cpu" and
               event.get("event_type") == "request_accept" and
               event.get("cycle") == accepted_cycle and
               event.get("core") == int(core) and
               event.get("address") == address and
               event.get("write") == write for event in self.events):
            return
        self._event("cpu", "request_accept", cycle=accepted_cycle,
                    core=int(core), address=address, write=write,
                    payload={"observed_by": "cpu_driver"})

    def record_cpu_response_complete(self, core, address, write, data, txn_id,
                                     *, cycle=None):
        """Record a CPU driver's sampled response ready/valid handshake.

        The passive sampler can run on either side of the same Toffee edge.
        Remove an already-seen matching pin sample, and suppress a matching
        late pin sample for the next two monitor cycles. Distinct driver
        handshakes are never merged, even when their payloads are identical.
        """
        completed_cycle = self.cycle if cycle is None else int(cycle)
        fields = {
            "core": int(core),
            "address": int(address) & 0xFFFF_FFFF,
            "write": int(bool(write)),
            "data": int(data) & ((1 << 64) - 1),
            "txn_id": int(txn_id) & 0x7,
        }
        self._cpu_driver_responses.append((completed_cycle, fields.copy()))
        retained = []
        removed = Counter()
        for event in self.events:
            payload = event.get("payload", {})
            same_response = (
                event.get("source") == "cpu" and
                event.get("event_type") == "response_complete" and
                payload.get("observed_by") == "passive_pin" and
                abs(int(event.get("cycle", -1000)) - completed_cycle) <= 2 and
                all(event.get(key) == value for key, value in fields.items())
            )
            if same_response:
                removed[f"{event['source']}.{event['event_type']}"] += 1
            else:
                retained.append(event)
        if removed:
            self.events = retained
            self.counts.subtract(removed)
            self.counts += Counter()  # discard zero/negative bookkeeping keys
        self._event("cpu", "response_complete", cycle=completed_cycle,
                    **fields, payload={"observed_by": "cpu_driver"})

    def _cpu_response_has_driver_observation(self, fields, cycle):
        """Return whether an active driver already recorded this handshake."""
        while (self._cpu_driver_responses and
               self._cpu_driver_responses[0][0] < cycle - 2):
            self._cpu_driver_responses.popleft()
        return any(
            abs(int(driver_cycle) - int(cycle)) <= 2 and
            all(driver_fields.get(key) == value
                for key, value in fields.items())
            for driver_cycle, driver_fields in self._cpu_driver_responses
        )

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
                    "l1_mshr_entries": self._last_l1_mshr_bitmap.bit_count(),
                }
                # Keep reset as an explicit, traceable lifecycle event even
                # when the failing AXI beat was the last beat and no bus
                # transaction remains outstanding to cancel.
                self._event("system", "reset_assert", state="asserted",
                            payload=cancelled)
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
                self._last_l1_mshr_bitmap = 0
                self._last_l1_mshr_active_bitmap = 0
                self._last_l1_mshr_issued_bitmap = 0
                self._last_l1_mshr_addr = [0] * 4
                self._last_l1_mshr_txn_id = [0] * 4
                self._last_l2_fill_active = 0
                self._last_victim_valid = 0
                self._fatal_active = False
                self._reset_active = True
                self.reset_epoch += 1
            return
        self._reset_active = False

        fatal_error = _bits(d.fatal_error)
        if fatal_error and not self._fatal_active:
            self._event("system", "fatal_error", state="asserted",
                        payload={"protocol_error": _bits(d.protocol_error)})
        self._fatal_active = bool(fatal_error)

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
                response_fields = {
                    "core": core,
                    "address": (resp_addr >> (32 * core)) & 0xFFFF_FFFF,
                    "write": (resp_write >> core) & 1,
                    "data": (resp_data >> (64 * core)) & ((1 << 64) - 1),
                    "txn_id": (resp_id >> (3 * core)) & 0x7,
                }
                if not self._cpu_response_has_driver_observation(
                        response_fields, self.cycle):
                    self._event("cpu", "response_complete",
                                payload={"observed_by": "passive_pin"},
                                **response_fields)

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
            incoming_addr = _bits(d.monitor_dir_req_live_addr)
            active_addr = _bits(d.monitor_engine_addr)
            self.stall_cycles["directory_request"] += 1
            active_refills = _bits(d.monitor_mem_mshr_valid).bit_count()
            incoming_set = (incoming_addr >> 6) & 0x1FF
            active_set = (active_addr >> 6) & 0x1FF
            self._event("directory", "request_stall", address=incoming_addr)
            # A same-set Directory lookup can be held off before its Snoop
            # becomes valid. During the memory wait, SharedLineEngine is
            # idle while the refill MSHR retains the active line address.
            # Looking only at dir_snoop_valid && snoop_set_conflict misses
            # this admission conflict because no Snoop is offered yet.
            if (active_refills and incoming_set == active_set):
                self._event(
                    "directory", "same_set_conflict",
                    address=incoming_addr, active_address=active_addr,
                    set_index=incoming_set, conflict_source="refill_lookup",
                    active_mshr_count=active_refills)
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
        # Preserve observability of a Snoop blocked by an active refill. This
        # differs from a Directory lookup conflict, where the request is held
        # before any Snoop offer exists.
        if (_bits(d.monitor_dir_snoop_valid) and
                _bits(d.monitor_snoop_set_conflict)):
            self._event("directory", "snoop_set_conflict")

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

        l1_mshr_bitmap = _bits(d.monitor_l1_mshr_valid)
        l1_mshr_active_bitmap = _bits(d.monitor_l1_mshr_active)
        l1_mshr_issued_bitmap = _bits(d.monitor_l1_mshr_issued)
        l1_mshr_slot_mask = (1 << 4) - 1
        if l1_mshr_active_bitmap & ~l1_mshr_bitmap & l1_mshr_slot_mask:
            raise AssertionError(
                "L1 MSHR controller ownership without a live allocation"
            )
        if l1_mshr_issued_bitmap & ~l1_mshr_active_bitmap & l1_mshr_slot_mask:
            raise AssertionError(
                "L1 MSHR Directory issue without controller ownership"
            )
        l1_mshr_occupancy = l1_mshr_bitmap.bit_count()
        l1_mshr_active = (l1_mshr_bitmap & l1_mshr_active_bitmap).bit_count()
        l1_mshr_issued = (l1_mshr_bitmap & l1_mshr_issued_bitmap).bit_count()
        packed_l1_mshr_addr = _bits(d.monitor_l1_mshr_addr)
        packed_l1_mshr_txn_id = _bits(d.monitor_l1_mshr_txn_id)
        per_core_occupancy = {}
        for core in range(2):
            core_bitmap = (l1_mshr_bitmap >> (2 * core)) & 0x3
            core_active = (l1_mshr_active_bitmap >> (2 * core)) & 0x3
            core_issued = (l1_mshr_issued_bitmap >> (2 * core)) & 0x3
            occupancy = core_bitmap.bit_count()
            active = (core_bitmap & core_active).bit_count()
            issued = (core_bitmap & core_issued).bit_count()
            per_core_occupancy[core] = occupancy
            self.l1_mshr_per_core_histogram[core][occupancy] += 1
            self.l1_mshr_active_per_core_histogram[core][active] += 1
            self.l1_mshr_issued_per_core_histogram[core][issued] += 1
            self.max_l1_mshr_per_core[core] = max(
                self.max_l1_mshr_per_core[core], occupancy
            )
            self.max_l1_mshr_active_per_core[core] = max(
                self.max_l1_mshr_active_per_core[core], active
            )
            self.max_l1_mshr_issued_per_core[core] = max(
                self.max_l1_mshr_issued_per_core[core], issued
            )
            for entry in range(2):
                slot = core * 2 + entry
                bit = 1 << slot
                address = (packed_l1_mshr_addr >> (32 * slot)) & 0xFFFF_FFFF
                txn_id = (packed_l1_mshr_txn_id >> (3 * slot)) & 0x7
                slot_valid_changed = bool(
                    (l1_mshr_bitmap ^ self._last_l1_mshr_bitmap) & bit
                )
                slot_identity_changed = bool(
                    (l1_mshr_bitmap & bit) and
                    (self._last_l1_mshr_bitmap & bit) and
                    address != self._last_l1_mshr_addr[slot]
                )
                if slot_valid_changed:
                    kind = "allocate" if l1_mshr_bitmap & bit else "retire"
                    self._event(
                        "l1_mshr", kind, core=core, entry=entry, slot=slot,
                        address=address if kind == "allocate" else
                        self._last_l1_mshr_addr[slot],
                        txn_id=txn_id if kind == "allocate" else
                        self._last_l1_mshr_txn_id[slot],
                        active=bool(l1_mshr_active_bitmap & bit),
                        issued=bool(l1_mshr_issued_bitmap & bit),
                        occupancy=l1_mshr_occupancy,
                        core_occupancy=occupancy,
                    )
                elif slot_identity_changed:
                    # A response can retire an entry on the same edge that a
                    # queued CPU miss reuses its slot. The valid bitmap then
                    # stays high, so track an address change as two ordered
                    # lifecycle events. Txn ID can be assigned after allocation
                    # and is not part of slot identity.
                    self._event(
                        "l1_mshr", "retire", core=core, entry=entry, slot=slot,
                        address=self._last_l1_mshr_addr[slot],
                        txn_id=self._last_l1_mshr_txn_id[slot],
                        active=False, issued=False,
                        occupancy=l1_mshr_occupancy,
                        core_occupancy=occupancy,
                    )
                    self._event(
                        "l1_mshr", "allocate", core=core, entry=entry, slot=slot,
                        address=address, txn_id=txn_id,
                        active=bool(l1_mshr_active_bitmap & bit),
                        issued=bool(l1_mshr_issued_bitmap & bit),
                        occupancy=l1_mshr_occupancy,
                        core_occupancy=occupancy,
                    )
                if (l1_mshr_issued_bitmap ^
                        self._last_l1_mshr_issued_bitmap) & bit:
                    self._event(
                        "l1_mshr",
                        "dispatch" if l1_mshr_issued_bitmap & bit else "deactivate",
                        core=core, entry=entry, slot=slot, address=address,
                        txn_id=txn_id, occupancy=l1_mshr_issued,
                    )
                if (l1_mshr_bitmap & bit and
                        txn_id != self._last_l1_mshr_txn_id[slot]):
                    self._event("l1_mshr", "txn_assign", core=core,
                                entry=entry, slot=slot, address=address,
                                txn_id=txn_id)
                self._last_l1_mshr_addr[slot] = address
                self._last_l1_mshr_txn_id[slot] = txn_id
        self._last_l1_mshr_bitmap = l1_mshr_bitmap
        self._last_l1_mshr_active_bitmap = l1_mshr_active_bitmap
        self._last_l1_mshr_issued_bitmap = l1_mshr_issued_bitmap
        self.l1_mshr_occupancy_histogram[l1_mshr_occupancy] += 1
        self.l1_mshr_active_histogram[l1_mshr_active] += 1
        self.l1_mshr_issued_histogram[l1_mshr_issued] += 1
        self.max_l1_mshr_occupancy = max(
            self.max_l1_mshr_occupancy, l1_mshr_occupancy
        )
        self.max_l1_mshr_active = max(self.max_l1_mshr_active, l1_mshr_active)
        self.max_l1_mshr_issued = max(self.max_l1_mshr_issued, l1_mshr_issued)
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
