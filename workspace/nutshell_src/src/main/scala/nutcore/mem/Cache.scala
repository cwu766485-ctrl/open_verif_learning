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

/**
 * Cache implementation entrypoint.
 *
 * The implementation is intentionally split by responsibility:
 *   - CacheTypes.scala: configuration, address geometry and shared bundles
 *   - CacheStage1.scala: array read/request admission
 *   - CacheStage2.scala: tag compare, hit and victim selection
 *   - CacheStage3.scala: hit response, write-back/refill, MMIO and coherence
 *   - CacheTop.scala: array/pipeline wiring and disabled-cache fallbacks
 *
 * Keeping these files separate does not change the generated hardware; it makes
 * the Chisel source and split-Verilog output easier to review and maintain.
 */

private[nutcore] object CacheSourceLayout {
  val description = "Cache implementation is split across CacheTypes, CacheStage1/2/3 and CacheTop"
}
