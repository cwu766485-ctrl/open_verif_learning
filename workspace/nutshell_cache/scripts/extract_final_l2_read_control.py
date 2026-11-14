"""Extract busy/beat control only, fail if source dependencies change.

No product source is rewritten. The generated cone is a proof artifact, not a
replacement implementation. Tag/data hit is universally quantified externally.
"""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def extract():
 p=ROOT/'rtl/l2/SharedL2DirectoryArray.sv';s=p.read_text()
 start=s.index('      if (line_rd_valid && line_rd_ready) begin')
 end=s.index('\n      end',s.index('line_rd_beat_q <= line_rd_beat_q +',start))+len('\n      end')
 cone=s[start:end]
 removed=[]
 for pattern in [r'        line_rd_set_q <= rd_set;\n',r'        for \(j = 0; j < WAYS; j = j \+ 1\)\n.*?line_rd_way_q <= WAY_WIDTH\'\(j\);\n']:
  match=re.search(pattern,cone,re.S)
  if match:removed.append(match.group());cone=cone.replace(match.group(),'')
 assert 'line_rd_way_q' not in cone and 'line_rd_set_q' not in cone
 expected={'if','else','begin','end','line_rd_valid','line_rd_ready','line_rd_busy_q','line_rd_hit','line_rd_beat_q','line_data_valid','line_data_ready','d7','b0','b1'}
 assert set(re.findall(r'\b[a-zA-Z_]\w*',cone))<=expected
 # Verify actual reset/outputs rather than assuming their correspondence.
 checks=["line_rd_busy_q <= 1'b0;","line_rd_beat_q <= '0;",'line_rd_ready = !line_rd_busy_q;','line_data_valid = line_rd_busy_q;','line_data_beat_idx = line_rd_beat_q;',"line_data_last = (line_rd_beat_q == 3'd7);"]
 assert all(x in s for x in checks)
 # Global write-site closure: fail if another process starts driving control.
 busy_writes=re.findall(r"line_rd_busy_q\s*<=\s*([^;]+);",s)
 beat_writes=re.findall(r"line_rd_beat_q\s*<=\s*([^;]+);",s)
 assert busy_writes==["1'b0",'line_rd_hit',"1'b0"]
 assert beat_writes==["'0","'0","'0","line_rd_beat_q + 1'b1"]
 text='''// Generated source control slice; see extraction manifest and scope.
module FinalL2ReadControl(input logic clock,reset,line_rd_valid,line_rd_hit,line_data_ready,
output logic line_rd_ready,line_data_valid,line_data_last,output logic [2:0] line_data_beat_idx);
logic line_rd_busy_q;logic [2:0] line_rd_beat_q;
assign line_rd_ready=!line_rd_busy_q;assign line_data_valid=line_rd_busy_q;
assign line_data_last=line_rd_beat_q==7;assign line_data_beat_idx=line_rd_beat_q;
always @(posedge clock) begin
if(reset) begin line_rd_busy_q<=0;line_rd_beat_q<=0;end else begin
'''+cone+'\nend end\nendmodule\n'
 return text,dict(source=str(p.relative_to(ROOT)),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),retained_control=cone,removed_data_only=removed,checked_reset_and_output_statements=checks,boundary='No claim of automatic full-cone equivalence; extraction and noninterference require independent review; hit unconstrained')
if __name__=='__main__':
 import sys
 text,m=extract();out=ROOT/'formal/final_l2_read_control_extracted.sv'
 if '--check' in sys.argv:assert out.read_text()==text
 else:out.write_text(text)
 print(json.dumps(m,indent=2))
