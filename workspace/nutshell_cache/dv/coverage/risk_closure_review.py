"""Produce dataset-scoped worklists; classifications never approve exclusions."""
from __future__ import annotations
import csv
import gzip
import json
import re
from collections import Counter
from pathlib import Path
from dv.coverage import rtl_release_gate as gate
from dv.coverage import rtl_coverage_dataset_manifest as manifest_lib
from dv.coverage import coverage_raw_runs as raw
from dv.coverage import coherence_gap_review as audit

ROOT = audit.ROOT


def fields(line):
    return dict(part.split('\x02', 1) for part in line.split("'", 2)[1].split('\x01') if '\x02' in part)


def toggle_axes(point):
    # Existing stable identities retain the entire native signal and direction.
    name = point['identity'].split('|')[2]
    signal, sep, direction = name.rpartition(':')
    if not sep or direction not in {'0->1', '1->0'}:
        return name, '', 'UNRESOLVED'
    match = re.search(r'\[([0-9]+)\]$', signal)
    return signal[:match.start()] if match else signal, match.group(1) if match else 'scalar', direction


def render(manifest):
    rows = gate.current_point_inventory(manifest)
    out = ROOT / 'reports/final/risk_closure'
    out.mkdir(parents=True, exist_ok=True)
    metadata = {}
    for did, ds in manifest['datasets'].items():
        for line in (ROOT / ds['raw_file']).read_text().splitlines():
            if not line.startswith('C '): continue
            f = fields(line)
            identity = '|'.join(f.get(k, '') for k in ('l','n','o','page','S'))
            metadata[(did, audit.canonical_path(f.get('f','')), f.get('t'), identity)] = f
    summary = {}
    columns = ['point_id','dataset','top','module','source','source_line','metric','zero_point','required_behavior','reachability','root_cause','test_or_proof','status','instance','signal','bit','direction','source_sha256','dataset_fingerprint']
    groups = Counter()
    with gzip.open(out/'zero_point_review.csv.gz','wt',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader()
        for p in rows:
            if p['count'] > 0: continue
            ds=manifest['datasets'][p['dataset_id']]
            native=metadata.get((p['dataset_id'],p['source'],p['metric'],p['identity']),{})
            signal,bit,direction=toggle_axes(p) if p['metric']=='toggle' else ('','','')
            # Text identifies the exact condition; it does not prove reachability.
            source_lines=(ROOT/p['source']).read_text().splitlines()
            n=p['source_line']
            text=source_lines[n-1].strip() if isinstance(n,int) and 0<n<=len(source_lines) else 'Native FSM point; inspect state/arc identity'
            if p['metric']=='toggle':
                cause='UNREVIEWED_SIGNAL_BIT: constant/range/protocol/data causes require individual evidence'
                behavior=f'{signal}[{bit}] {direction}'
                proof='Same-top address/data/mask/ID stimulus or constant propagation/reachability proof; no automatic waiver'
            else:
                cause='UNREVIEWED_CONTROL_CONDITION'
                behavior=text
                proof='Same-top directed test with independent checker, port fault injection, or unconstrained-input reachability proof'
            row=dict(point_id=p['point_id'],dataset=p['dataset_id'],top=ds['top'],module=Path(p['source']).stem,source=p['source'],source_line=n,metric=p['metric'],zero_point=p['identity'],required_behavior=behavior,reachability='NOT_PROVEN',root_cause=cause,test_or_proof=proof,status='OPEN',instance=native.get('h','UNRESOLVED_LINE_AGGREGATE'),signal=signal,bit=bit,direction=direction,source_sha256=p['source_sha256'],dataset_fingerprint=p['dataset_fingerprint'])
            writer.writerow(row)
            groups[(p['dataset_id'],p['metric'],row['module'])]+=1
    summary['source_sha']=manifest['repository_head'];summary['source_fingerprint']=manifest['source_fingerprint']
    summary['groups']=[dict(dataset=d,metric=m,module=s,open=n) for (d,m,s),n in sorted(groups.items())]
    summary['policy']='All group labels are worklists, not reviewed dispositions. Raw denominators and required obligations unchanged.'
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(f'Wrote {sum(groups.values())} individually identified OPEN points to {out}')


def main():
    render(manifest_lib.build_manifest())

if __name__=='__main__': main()
