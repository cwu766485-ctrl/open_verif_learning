"""Resource-control overapproximation: retain actual Main/L1/arbiter/bank.

Only array modules are replaced with symbolic output cutpoints. This permits
capacity proofs in an overapproximation, but witnesses need concretization.
No product RTL is edited. Full array semantics are deliberately not claimed.
"""
from pathlib import Path
import re,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def generate():
 out=ROOT/'formal/resource_control';out.mkdir(exist_ok=True);manifest=[]
 for name,path in [('MesiL1Array','rtl/l1/MesiL1Array.sv'),('SharedL2DirectoryArray','rtl/l2/SharedL2DirectoryArray.sv')]:
  src=ROOT/path;s=src.read_text();header=s[:s.index(');')+2]
  outputs=[]
  for z in re.finditer(r'output\s+(?:logic|coherence_protocol_pkg::\w+)\s*(?:\[[^\]]+\])?\s*(\w+)\s*[,\n]',header):outputs.append(z.group(1))
  body='\n'.join('  always_comb '+n+' = $anyseq;' for n in outputs)
  target=out/(name+'.sv');target.write_text(header+'\n'+body+'\nendmodule\n')
  manifest.append(dict(source=path,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),cut_outputs=outputs,artifact=str(target.relative_to(ROOT)),artifact_sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
 retained=['rtl/cluster/DualL1MesiCluster.sv','rtl/l1/MesiL1Controller.sv','rtl/l1/MesiL1SnoopArbiter.sv','rtl/interconnect/CoherenceRequestArbiter.sv','rtl/interconnect/CoherenceRequestArbiterCore.sv','rtl/directory/DirectoryController.sv','rtl/directory/DirectoryMshrBank.sv','rtl/top/CoherentCacheSubsystem.sv']
 return dict(array_cuts=manifest,retained=[dict(source=p,source_sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()) for p in retained],boundary='Overapproximate array outputs, including metadata/ready/streams; no occupancy cap; abstract witness is NOT legal integrated witness; unreachable result would need cutpoint soundness review',independent_approval=None)
if __name__=='__main__':print(json.dumps(generate(),indent=2))
