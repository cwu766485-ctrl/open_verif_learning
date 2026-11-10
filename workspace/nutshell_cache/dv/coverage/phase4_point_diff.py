"""Compare exact same-top point IDs against the frozen Phase 3 archives."""
from __future__ import annotations
import csv
import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from dv.coverage import rtl_release_gate as gate
from dv.coverage import rtl_coverage_dataset_manifest as manifest
from dv.coverage import coverage_raw_runs as raw


def main():
    root = manifest.ROOT
    current = manifest.build_manifest()
    baseline_dir = root / 'reports/final/risk_closure'
    baseline = json.loads((baseline_dir / 'dataset_manifest.json').read_text())
    before = {}
    comparison = {}
    with tempfile.TemporaryDirectory() as temporary:
        for did, ds in baseline['datasets'].items():
            dat, info = Path(temporary)/f'{did}.dat', Path(temporary)/f'{did}.info'
            dat.write_bytes(gzip.decompress((baseline_dir/'raw'/f'{did}.dat.gz').read_bytes()))
            info.write_bytes(gzip.decompress((baseline_dir/'raw'/f'{did}.info.gz').read_bytes()))
            scoped = dict(baseline, datasets={did: dict(ds, raw_file=str(dat), line_info_file=str(info))})
            before.update({p['point_id']: p for p in gate.current_point_inventory(scoped)})
            old, _ = raw.metric_counts(raw.read_line_info(info), raw.read_points(dat))
            new_ds = current['datasets'][did]
            assert ds['top'] == new_ds['top'], 'Different tops cannot share hit credit'
            new, _ = raw.metric_counts(raw.read_line_info(root/new_ds['line_info_file']), raw.read_points(root/new_ds['raw_file']))
            comparison[did] = {metric: {'before': old[metric], 'after': new[metric]} for metric in raw.POINT_TYPES}
    after = {p['point_id']: p for p in gate.current_point_inventory(current)}
    output = root/'reports/final/phase4';output.mkdir(parents=True, exist_ok=True)
    columns = ['point_id','dataset_id','elaborated_top','source','metric','identity','before_count','after_count','transition','dataset_fingerprint']
    transitions = Counter()
    with gzip.open(output/'point_diff.csv.gz','wt',newline='') as stream:
        writer=csv.DictWriter(stream, fieldnames=columns);writer.writeheader()
        for pid in sorted(before.keys() | after.keys()):
            b,a=before.get(pid),after.get(pid);p=a or b
            transition = ('ADDED_ID' if b is None else 'REMOVED_ID' if a is None else
                          'NEW_RAW_HIT' if b['count']==0<a['count'] else
                          'LOST_RAW_HIT' if a['count']==0<b['count'] else 'UNCHANGED_STATUS')
            transitions[transition]+=1
            writer.writerow({**{k:p[k] for k in columns if k in p},'before_count':b['count'] if b else '',
                'after_count':a['count'] if a else '', 'transition':transition})
    summary={'source_sha':current['repository_head'],'source_fingerprint':current['source_fingerprint'],
             'baseline_source_sha':baseline['repository_head'],'metrics':comparison,'point_transitions':dict(transitions),
             'policy':'Exact same dataset/top/point identity only. No exclusions or cross-top credit.'}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(transitions))

if __name__ == '__main__': main()
