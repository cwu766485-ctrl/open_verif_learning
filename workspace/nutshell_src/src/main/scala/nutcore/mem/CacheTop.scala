/**************************************************************************************
* Copyright (c) 2020 Institute of Computing Technology, CAS
* Copyright (c) 2020 University of Chinese Academy of Sciences
*
* NutShell is licensed under Mulan PSL v2.
* You can use this software according to the terms and conditions of the Mulan PSL v2.
* You may obtain a copy of Mulan PSL v2 at:
*             http://license.coscl.org.cn/MulanPSL2
*
* THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER
* EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR
* FIT FOR A PARTICULAR PURPOSE.
*
* See the Mulan PSL v2 for more details.
***************************************************************************************/

package nutcore

import chisel3._
import chisel3.util._
import chisel3.util.experimental.BoringUtils
import bus.simplebus._
import utils._
import top.Settings

class Cache(implicit val cacheConfig: CacheConfig) extends CacheModule with HasCacheIO {
  override def desiredName: String = cacheRoleName

  // cpu pipeline
  val s1 = Module(new CacheStage1)
  val s2 = Module(new CacheStage2)
  val s3 = Module(new CacheStage3)
  val metaArray = Module(new SRAMTemplateWithArbiter(nRead = 1, new MetaBundle, set = Sets, way = Ways, shouldReset = true))
  val dataArray = Module(new SRAMTemplateWithArbiter(nRead = 2, new DataBundle, set = Sets * LineBeats, way = Ways))

  if (cacheName == "icache") {
    // flush icache when executing fence.i
    val flushICache = WireInit(false.B)
    BoringUtils.addSink(flushICache, "MOUFlushICache")
    metaArray.reset := reset.asBool || flushICache
  }

  val arb = Module(new Arbiter(new SimpleBusReqBundle(userBits = userBits, idBits = idBits), hasCohInt + 1))
  arb.io.in(hasCohInt + 0) <> io.in.req

  s1.io.in <> arb.io.out
  /*
  val s2BlockByPrefetch = if (cacheLevel == 2) {
      s2.io.out.valid && s3.io.in.valid && s3.io.in.bits.req.isPrefetch() && !s3.io.in.ready
    } else { false.B }
  */
  PipelineConnect(s1.io.out, s2.io.in, s2.io.out.fire, io.flush(0))
  PipelineConnect(s2.io.out, s3.io.in, s3.io.isFinish, io.flush(1))
  io.in.resp <> s3.io.out
  s3.io.flush := io.flush(1)
  io.out.mem <> s3.io.mem
  io.mmio <> s3.io.mmio
  io.empty := !s2.io.in.valid && !s3.io.in.valid

  io.in.resp.valid := Mux(s3.io.out.valid && s3.io.out.bits.isPrefetch, false.B, s3.io.out.valid || s3.io.dataReadRespToL1)

  if (hasCoh) {
    val cohReq = io.out.coh.req.bits
    // coh does not have user signal, any better code?
    val coh = Wire(new SimpleBusReqBundle(userBits = userBits, idBits = idBits))
    coh.apply(addr = cohReq.addr, cmd = cohReq.cmd, size = cohReq.size, wdata = cohReq.wdata, wmask = cohReq.wmask)
    arb.io.in(0).bits := coh
    arb.io.in(0).valid := io.out.coh.req.valid
    io.out.coh.req.ready := arb.io.in(0).ready
    io.out.coh.resp <> s3.io.cohResp
  } else {
    io.out.coh.req.ready := true.B
    io.out.coh.resp := DontCare
    io.out.coh.resp.valid := false.B
    s3.io.cohResp.ready := true.B
  }

  metaArray.io.r(0) <> s1.io.metaReadBus
  dataArray.io.r(0) <> s1.io.dataReadBus
  dataArray.io.r(1) <> s3.io.dataReadBus

  metaArray.io.w <> s3.io.metaWriteBus
  dataArray.io.w <> s3.io.dataWriteBus

  s2.io.metaReadResp := s1.io.metaReadBus.resp.data
  s2.io.dataReadResp := s1.io.dataReadBus.resp.data
  s2.io.dataWriteBus := s3.io.dataWriteBus
  s2.io.metaWriteBus := s3.io.metaWriteBus

  if (EnableOutOfOrderExec) {
    BoringUtils.addSource(s3.io.out.fire && s3.io.in.bits.hit, "perfCntCondM" + cacheName + "Hit")
    BoringUtils.addSource(s3.io.in.valid && !s3.io.in.bits.hit, "perfCntCondM" + cacheName + "Loss")
    BoringUtils.addSource(s1.io.in.fire, "perfCntCondM" + cacheName + "Req")
  }
  // io.in.dump(cacheName + ".in")
  Debug("InReq(%d, %d) InResp(%d, %d) \n", io.in.req.valid, io.in.req.ready, io.in.resp.valid, io.in.resp.ready)
  Debug("{IN s1:(%d,%d), s2:(%d,%d), s3:(%d,%d)} {OUT s1:(%d,%d), s2:(%d,%d), s3:(%d,%d)}\n", s1.io.in.valid, s1.io.in.ready, s2.io.in.valid, s2.io.in.ready, s3.io.in.valid, s3.io.in.ready, s1.io.out.valid, s1.io.out.ready, s2.io.out.valid, s2.io.out.ready, s3.io.out.valid, s3.io.out.ready)
  when (s1.io.in.valid) { Debug(p"[${cacheName}.S1]: ${s1.io.in.bits}\n") }
  when (s2.io.in.valid) { Debug(p"[${cacheName}.S2]: ${s2.io.in.bits.req}\n") }
  when (s3.io.in.valid) { Debug(p"[${cacheName}.S3]: ${s3.io.in.bits.req}\n") }
  //s3.io.mem.dump(cacheName + ".mem")
}

class Cache_fake(implicit val cacheConfig: CacheConfig) extends CacheModule with HasCacheIO {
  override def desiredName: String = s"${cacheRoleName}Bypass"

  val s_idle :: s_memReq :: s_memResp :: s_mmioReq :: s_mmioResp :: s_wait_resp :: Nil = Enum(6)
  val state = RegInit(s_idle)

  val ismmio = AddressSpace.isMMIO(io.in.req.bits.addr)
  val ismmioRec = RegEnable(ismmio, io.in.req.fire)
  if (cacheConfig.name == "dcache") {
    BoringUtils.addSource(WireInit(ismmio), "lsuMMIO")
  }

  val needFlush = RegInit(false.B)
  when (io.flush(0) && (state =/= s_idle)) { needFlush := true.B }
  when (state === s_idle && needFlush) { needFlush := false.B }

  val alreadyOutFire = RegEnable(true.B, false.B, io.in.resp.fire)

  switch (state) {
    is (s_idle) {
      alreadyOutFire := false.B
      when (io.in.req.fire && !io.flush(0)) { state := Mux(ismmio, s_mmioReq, s_memReq) }
    }
    is (s_memReq) {
      when (io.out.mem.req.fire) { state := s_memResp }
    }
    is (s_memResp) {
      when (io.out.mem.resp.fire) { state := s_wait_resp }
    }
    is (s_mmioReq) {
      when (io.mmio.req.fire) { state := s_mmioResp }
    }
    is (s_mmioResp) {
      when (io.mmio.resp.fire || alreadyOutFire) { state := s_wait_resp }
    }
    is (s_wait_resp) {
      when (io.in.resp.fire || needFlush || alreadyOutFire) { state := s_idle }
    }
  }

  val reqaddr = RegEnable(io.in.req.bits.addr, io.in.req.fire)
  val cmd = RegEnable(io.in.req.bits.cmd, io.in.req.fire)
  val size = RegEnable(io.in.req.bits.size, io.in.req.fire)
  val wdata = RegEnable(io.in.req.bits.wdata, io.in.req.fire)
  val wmask = RegEnable(io.in.req.bits.wmask, io.in.req.fire)

  io.in.req.ready := (state === s_idle)
  io.in.resp.valid := (state === s_wait_resp) && (!needFlush)

  val mmiordata = RegEnable(io.mmio.resp.bits.rdata, io.mmio.resp.fire)
  val mmiocmd = RegEnable(io.mmio.resp.bits.cmd, io.mmio.resp.fire)
  val memrdata = RegEnable(io.out.mem.resp.bits.rdata, io.out.mem.resp.fire)
  val memcmd = RegEnable(io.out.mem.resp.bits.cmd, io.out.mem.resp.fire)

  io.in.resp.bits.rdata := Mux(ismmioRec, mmiordata, memrdata)
  io.in.resp.bits.cmd := Mux(ismmioRec, mmiocmd, memcmd)

  val memuser = RegEnable(io.in.req.bits.user.getOrElse(0.U), io.in.req.fire)
  io.in.resp.bits.user.zip(if (userBits > 0) Some(memuser) else None).map { case (o,i) => o := i }

  io.out.mem.req.bits.apply(addr = reqaddr,
    cmd = cmd, size = size,
    wdata = wdata, wmask = wmask)
  io.out.mem.req.valid := (state === s_memReq)
  io.out.mem.resp.ready := true.B

  io.mmio.req.bits.apply(addr = reqaddr,
    cmd = cmd, size = size,
    wdata = wdata, wmask = wmask)
  io.mmio.req.valid := (state === s_mmioReq)
  io.mmio.resp.ready := true.B

  io.empty := false.B
  io.out.coh := DontCare

  Debug(io.in.req.fire, p"in.req: ${io.in.req.bits}\n")
  Debug(io.out.mem.req.fire, p"out.mem.req: ${io.out.mem.req.bits}\n")
  Debug(io.out.mem.resp.fire, p"out.mem.resp: ${io.out.mem.resp.bits}\n")
  Debug(io.in.resp.fire, p"in.resp: ${io.in.resp.bits}\n")
}

class Cache_dummy(implicit val cacheConfig: CacheConfig) extends CacheModule with HasCacheIO {
  override def desiredName: String = s"${cacheRoleName}Dummy"


  val needFlush = RegInit(false.B)
  when (io.flush(0)) {
    needFlush := true.B
  }
  when (io.in.req.fire && !io.flush(0)) {
    needFlush := false.B
  }

  io.in.req.ready := io.out.mem.req.ready
  io.in.resp.valid := (io.out.mem.resp.valid && !needFlush) || io.flush(0)

  io.in.resp.bits.rdata := io.out.mem.resp.bits.rdata
  io.in.resp.bits.cmd := io.out.mem.resp.bits.cmd
  val memuser = RegEnable(io.in.req.bits.user.getOrElse(0.U), io.in.req.fire)
  io.in.resp.bits.user.zip(if (userBits > 0) Some(memuser) else None).map { case (o,i) => o := i }

  io.out.mem.req.bits.apply(
    addr = io.in.req.bits.addr,
    cmd = io.in.req.bits.cmd,
    size = io.in.req.bits.size,
    wdata = io.in.req.bits.wdata,
    wmask = io.in.req.bits.wmask
  )
  io.out.mem.req.valid := io.in.req.valid
  io.out.mem.resp.ready := io.in.resp.ready

  io.empty := false.B
  io.mmio := DontCare
  io.out.coh := DontCare
}

object Cache {
  def apply(in: SimpleBusUC, mmio: Seq[SimpleBusUC], flush: UInt, empty: Bool, enable: Boolean = true)(implicit cacheConfig: CacheConfig) = {
    val cache = if (enable) Module(new Cache)
                else (if (Settings.get("IsRV32"))
                        (if (cacheConfig.name == "dcache") Module(new Cache_fake) else Module(new Cache_dummy))
                      else
                        (Module(new Cache_fake)))
    cache.io.flush := flush
    cache.io.in <> in
    mmio(0) <> cache.io.mmio
    empty := cache.io.empty
    cache.io.out
  }
}

