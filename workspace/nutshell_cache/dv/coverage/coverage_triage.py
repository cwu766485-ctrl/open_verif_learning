"""Evidence-first triage; categories never create release dispositions."""
import csv
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from dv.coverage import rtl_coverage_dataset_manifest as manifest
from dv.coverage import rtl_release_gate as gate
from dv.coverage.risk_closure_review import toggle_axes

ROOT = manifest.ROOT
ALIGNED = {'line_addr_q', 'dir_write_line_addr', 'snoop_req_line_addr', 'line_xfer_addr', 'grant_line_addr'}


def classify(point, current):
    if current and int(current['count']) > 0:
        return '1_TESTABLE', 'SAME_TOP_NEW_RAW_HIT', 'New directed block test; execution evidence only, full regression attestation pending'
    signal, bit, _ = toggle_axes(point) if point['metric'] == 'toggle' else ('', '', '')
    if (point['dataset_id'] == 'directory_controller' and point['metric'] == 'toggle'
            and signal in ALIGNED and bit.isdigit() and int(bit) < 6):
        return '2_WAIVER_CANDIDATE', 'INDUCTIVE_CONSTANT_ZERO', 'Directory alignment assertions, arbitrary ports, initial reset; independent approval pending'
    # A default FSM recovery handler is intentional defensive behavior, not dead code.
    if point['source'] == 'rtl/coherence/SharedLineEngine.sv' and point['source_line'] in [366,367,368]:
        return 'REVIEW_REQUIRED', 'DEFENSIVE_FSM_DEFAULT', 'Reachability proof and fault model required; do not delete'
    return 'REVIEW_REQUIRED', 'INSUFFICIENT_POINT_SPECIFIC_EVIDENCE', 'Needs same-top stimulus, structural proof or reachability analysis; low activity is not constant evidence'


def main():
    baseline_dir=ROOT/'reports/final/phase4'
    baseline=json.loads((baseline_dir/'dataset_manifest.json').read_text())
    current=manifest.build_manifest()
    before={}
    import tempfile
    with tempfile.TemporaryDirectory() as temp:
        for did, ds in baseline['datasets'].items():
            files={}
            for key,suffix in [('raw_file','dat'),('line_info_file','info')]:
                p=Path(temp)/f'{did}.{suffix}';p.write_bytes(gzip.decompress((baseline_dir/'raw'/f'{did}.{suffix}.gz').read_bytes()));files[key]=str(p)
            scoped=dict(baseline,datasets={did:dict(ds,**files)})
            before.update({p['point_id']:p for p in gate.current_point_inventory(scoped)})
    after={p['point_id']:p for p in gate.current_point_inventory(current)}
    # Only these block datasets were freshly re-run for this change.
    fresh={'directory_controller','mesi_l1_controller'}
    out=ROOT/'reports/final/triage';out.mkdir(parents=True,exist_ok=True)
    counts=Counter();metrics=Counter();new=Counter()
    columns=['point_id','dataset_id','elaborated_top','source','source_line','metric','identity','category','reason','evidence','baseline_count','current_count','release_disposition']
    with gzip.open(out/'baseline_zero_triage.csv.gz','wt',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader()
        for pid,p in sorted(before.items()):
            if p['count']>0:continue
            a=after.get(pid) if p['dataset_id'] in fresh else None
            category,reason,evidence=classify(p,a)
            counts[category]+=1;metrics[(category,p['metric'])]+=1
            if a and a['count']>0:new[(p['dataset_id'],p['metric'])]+=1
            writer.writerow({**{k:p[k] for k in columns if k in p},'category':category,'reason':reason,'evidence':evidence,'baseline_count':0,'current_count':a['count'] if a else 'NOT_RERUN','release_disposition':'OPEN_PENDING_REGRESSION' if category=='1_TESTABLE' else 'OPEN'})
    summary={'baseline_zero_points':sum(counts.values()),'categories':dict(counts),'category_metric_counts':[dict(category=c,metric=m,count=n) for (c,m),n in sorted(metrics.items())],'new_same_top_hits':[dict(dataset=d,metric=m,count=n) for (d,m),n in sorted(new.items())],'confirmed_deletable_dead_points':0,'approved_waivers':0,'source_sha':current['repository_head'],'source_fingerprint':current['source_fingerprint'],'raw_denominators_unchanged':True,'full_regression_status':'NOT_RERUN_FOR_NEW_TEST_SOURCE','policy':'Category2 is review candidate only; neither exclusions nor automatic waiver. Other tops remain frozen Phase4 evidence.'}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'current_manifest.json').write_text(json.dumps(current,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
