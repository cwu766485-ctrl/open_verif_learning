"""Produce dataset-scoped worklists; classifications never approve exclusions."""
from __future__ import annotations
import csv
import gzip
import json
import re
import tempfile
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
    source_cache = {}
    summary = {}
    comparison = {}
    archive = ROOT / 'reports/final/rtl_coverage_raw'
    for did, ds in manifest['datasets'].items():
        with tempfile.TemporaryDirectory() as tmp:
            dat, info = Path(tmp)/'before.dat', Path(tmp)/'before.info'
            dat.write_bytes(gzip.decompress((archive/f'{did}.dat.gz').read_bytes()))
            info.write_bytes(gzip.decompress((archive/f'{did}.info.gz').read_bytes()))
            before_points = raw.read_points(dat)
            before, _ = raw.metric_counts(raw.read_line_info(info), before_points)
            after_points = raw.read_points(ROOT/ds['raw_file'])
            after, _ = raw.metric_counts(raw.read_line_info(ROOT/ds['line_info_file']), after_points)
            comparison[did] = {metric: dict(before_hit=before[metric][0], before_total=before[metric][1],
                after_hit=after[metric][0], after_total=after[metric][1],
                delta_hit=after[metric][0]-before[metric][0],
                newly_hit_native_points=sum(count>0 and key in before_points and before_points[key]==0
                    for key,count in after_points.items() if key[1]==metric),
                scope='Exact dataset only; baseline archive retained, no cross-top credit')
                for metric in raw.POINT_TYPES}
    summary['raw_comparison'] = comparison
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
            if p['source'] not in source_cache:
                source_cache[p['source']] = (ROOT/p['source']).read_text().splitlines()
            source_lines=source_cache[p['source']]
            n=p['source_line']
            text=source_lines[n-1].strip() if isinstance(n,int) and 0<n<=len(source_lines) else 'Native FSM point; inspect state/arc identity'
            if p['metric']=='toggle':
                cause='UNREVIEWED_SIGNAL_BIT: constant/range/protocol/data causes require individual evidence'
                # Group only by observed signal role. These are prioritization
                # categories, never constant/unreachable conclusions.
                low = signal.lower()
                if 'addr' in low or 'tag' in low:
                    cause='ADDRESS_RANGE_REVIEW: determine routing/alignment/tag constraints per bit'
                elif 'mask' in low:
                    cause='BYTE_MASK_REVIEW: exercise individual byte lanes and combinations'
                elif 'txn' in low or '_id' in low or 'context' in low or '_sel' in low:
                    cause='ID_CONTEXT_REVIEW: allocation, wrap and resource contention'
                elif 'data' in low:
                    cause='DATA_PATTERN_REVIEW: ones/zeros/walking patterns with checked readback'
                elif 'state' in low:
                    cause='STATE_ENCODING_REVIEW: reset, protocol error and reachability evidence'
                behavior=f'{signal}[{bit}] {direction}'
                proof='Same-top address/data/mask/ID stimulus or constant propagation/reachability proof; no automatic waiver'
            else:
                cause='UNREVIEWED_CONTROL_CONDITION'
                if p['metric']=='fsm_arc' and '->' in p['identity']:
                    arc = p['identity'].split('|')[2].split('::')[-1]
                    if arc.endswith('->DIR_IDLE') and not arc.startswith('DIR_FINISH'):
                        cause='RESET_ARC: source reset assignment at DirectoryController; observe source state then reset'
                    elif arc.endswith('->CPU_IDLE') and not arc.startswith('CPU_RESP'):
                        cause='RESET_ARC: source reset assignment at MesiL1Controller; observe source state then reset'
                behavior=text
                proof='Same-top directed test with independent checker, port fault injection, or unconstrained-input reachability proof'
            row=dict(point_id=p['point_id'],dataset=p['dataset_id'],top=ds['top'],module=Path(p['source']).stem,source=p['source'],source_line=n,metric=p['metric'],zero_point=p['identity'],required_behavior=behavior,reachability='NOT_PROVEN',root_cause=cause,test_or_proof=proof,status='OPEN',instance=native.get('h','UNRESOLVED_LINE_AGGREGATE'),signal=signal,bit=bit,direction=direction,source_sha256=p['source_sha256'],dataset_fingerprint=p['dataset_fingerprint'])
            writer.writerow(row)
            groups[(p['dataset_id'],p['metric'],row['module'])]+=1
    summary['source_sha']=manifest['repository_head'];summary['source_fingerprint']=manifest['source_fingerprint']
    summary['groups']=[dict(dataset=d,metric=m,module=s,open=n) for (d,m,s),n in sorted(groups.items())]
    summary['policy']='All group labels are worklists, not reviewed dispositions. Raw denominators and required obligations unchanged.'
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    md = ['# Risk-Based RTL Closure', '', '**Decision: OPEN.** Required zero points remain; no waiver or independent approval is inferred.', '',
          f"Tested source SHA: `{manifest['repository_head']}`", f"Source fingerprint: `{manifest['source_fingerprint']}`", '',
          '| Dataset | Metric | Before | After | Delta hits |', '| --- | --- | ---: | ---: | ---: |']
    for did, metrics in comparison.items():
        for metric, item in metrics.items():
            md.append(f"| {did} | {metric} | {item['before_hit']}/{item['before_total']} | {item['after_hit']}/{item['after_total']} | {item['delta_hit']:+d} |")
    md += ['', 'All zero points retain individual IDs in `risk_closure/zero_point_review.csv.gz`.',
           'Toggle axes retain native signal/array/bit/direction and instance. Unclassified bits remain OPEN; none are called constant or noncritical without proof.',
           'Reviewed Eligible Coverage is not available until independent review completes. The raw denominator and coverage plan are unchanged.', '']
    (ROOT/'reports/final/risk_based_closure_report.md').write_text('\n'.join(md))
    print(f'Wrote {sum(groups.values())} individually identified OPEN points to {out}')


def main():
    render(manifest_lib.build_manifest())

if __name__=='__main__': main()
