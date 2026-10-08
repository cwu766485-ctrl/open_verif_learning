# Cache interface contracts

The DUT exposes four interface groups.  They are documented here rather than
wrapped in new Verilog modules in the baseline pass, so the generated port
names and handshake timing remain unchanged.

## CPU-side request/response (`io_in`)

The NutShell L1 DCache LSU sends single-beat `READ` (`CMD_READ=0`) and
`WRITE` (`CMD_WRITE=1`) requests with physical address, size, write mask and
data. A request transfers on `valid && ready`; each request retires with one
response. `READBST`/`WRITEBST` are not legal commands on this L1 DCache CPU
port. The shared CacheStage3 source contains burst-related logic for other
cache-hierarchy configurations, but the upstream LSU does not issue those
commands to this instance.

## Downstream memory (`io_out_mem`)

Used for cacheable-memory refill and dirty-victim writeback. A cache-line
transfer contains eight 64-bit beats. Refill uses a read-burst command; dirty
writeback uses write-burst beats terminated by write-last. This interface is
a memory-hierarchy contract, not necessarily a direct DDR connection.

## MMIO bypass (`io_mmio`)

MMIO requests bypass the tag/data arrays and are forwarded to the SoC MMIO
crossbar and peripherals.

## Coherence probe/release (`io_out_coh`)

An external coherence source can probe a line.  A hit returns a probe-hit
response followed by an eight-beat line release; a miss returns probe-miss.

## Control/status

`clock`, `reset` and `io_flush` are inputs. `io_empty` and victim-way status
are outputs.  The current writable DCache configuration does not permit the
ICache-only flush path; this is enforced by an RTL assertion.
