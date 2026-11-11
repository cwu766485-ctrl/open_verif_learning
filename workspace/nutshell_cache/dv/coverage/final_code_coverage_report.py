"""Dataset-scoped uncovered-code inventory; never approves exclusions.

The live raw manifest is authoritative. Exact IDs, source hashes and raw hashes
are emitted for every zero point; module tables and line ranges are summaries.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from dv.coverage import rtl_coverage_dataset_manifest as manifest_lib
from dv.coverage import rtl_release_gate as gate

ROOT = manifest_lib.ROOT
OUT = ROOT / "reports/final/code_coverage"
METRICS = ("line", "branch", "toggle", "fsm_state", "fsm_arc")


def line_ranges(numbers):
    values = sorted(set(numbers))
    ranges = []
    for value in values:
        if ranges and value == ranges[-1][1] + 1:
            ranges[-1][1] = value
        else:
            ranges.append([value, value])
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in ranges)


def summarize(points):
    """Count point identities independently in each dataset/source/metric."""
    groups = defaultdict(lambda: Counter(total=0, hit=0, zero=0))
    seen = set()
    for p in points:
        if p["point_id"] in seen:
            raise ValueError(f"duplicate Point ID: {p['point_id']}")
        seen.add(p["point_id"])
        group = groups[(p["dataset_id"], p["source"], p["metric"])]
        group["total"] += 1
        group["hit" if p["count"] > 0 else "zero"] += 1
    return groups


def main():
    manifest = manifest_lib.build_manifest()
    points = gate.current_point_inventory(manifest)
    groups = summarize(points)
    OUT.mkdir(parents=True, exist_ok=True)
    zeros = [p for p in points if p["count"] == 0]
    lines = defaultdict(list)
    source_cache = {}
    fields = ["point_id", "dataset_id", "elaborated_top", "source", "source_line",
              "metric", "identity", "count", "rtl_condition", "classification",
              "remaining_action", "status", "source_sha256", "dataset_fingerprint",
              "raw_coverage_sha256", "line_info_sha256"]
    rows = []
    for p in zeros:
        source = source_cache.setdefault(p["source"], (ROOT / p["source"]).read_text().splitlines())
        n = p["source_line"]
        condition = source[n - 1].strip() if isinstance(n, int) and 0 < n <= len(source) else p["identity"]
        category = "UNRESOLVED"
        action = "Determine same-top reachability; add checked test or reproducible proof; no automatic waiver"
        # Explicit error assignments are defensive behavior. Guard lines alone
        # are not evidence that every alternative is illegal or unreachable.
        if p["metric"] != "toggle" and any(token in condition for token in
                ("<= ENGINE_ERROR", "<= DIR_ERROR", "protocol_error <= 1'b1", "memory_adapter_protocol_error <= 1'b1")):
            category = "ILLEGAL_PROTOCOL_OR_DEFENSIVE"
            action = "Point-specific port fault test or internal producer invariant; retain intentional defensive logic"
        if p["metric"] == "toggle":
            action = "Review signal/instance/bit/direction; structural constant proof or meaningful protocol stimulus required"
        rows.append({**{k:p[k] for k in fields if k in p}, "rtl_condition": condition,
                     "classification": category, "remaining_action": action, "status": "OPEN"})
        if p["metric"] == "line":
            lines[(p["dataset_id"], p["source"])].append(n)
    for name, selected in [("uncovered_points.csv.gz", rows),
                           ("uncovered_control_points.csv", [p for p in rows if p["metric"] != "toggle"]),
                           ("main_uncovered_control_points.csv", [p for p in rows if p["metric"] != "toggle" and p["dataset_id"] == "main_subsystem"])]:
        path = OUT / name
        opener = gzip.open if name.endswith(".gz") else open
        with opener(path, "wt", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader(); writer.writerows(selected)
    module_rows = []
    for (dataset, source, metric), values in sorted(groups.items()):
        module_rows.append(dict(dataset=dataset, source=source, module=Path(source).stem,
                                metric=metric, **values))
    (OUT / "module_summary.json").write_text(json.dumps(module_rows, indent=2) + "\n")
    (OUT / "dataset_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    counts = Counter(p["metric"] for p in zeros)
    summary = dict(source_sha=manifest["repository_head"], source_fingerprint=manifest["source_fingerprint"],
                   point_count=len(points), raw_hits=len(points)-len(zeros), zero_points=len(zeros),
                   zero_by_metric=dict(counts), approved_exclusions=0,
                   scope="Independent dataset obligations; no pooled cross-top percentage; raw denominator unchanged")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    md = ["# NutShell Cache v1.1 代码覆盖率报告", "", "**Full RTL Code Coverage Sign-off: OPEN。**",
          f"Source Commit：`{manifest['repository_head']}`；Source Fingerprint：`{manifest['source_fingerprint']}`。", "",
          f"Raw Point总数{len(points)}；命中{summary['raw_hits']}；未命中{len(zeros)}。这是独立Top覆盖义务的统计，不是去重后的源码行数或合并覆盖率。", "",
          f"未命中指标：`{dict(counts)}`。没有改变分母，没有已批准排除；Reviewed Eligible Coverage未计算。", "",
          "## 各独立数据集 Raw Coverage", "",
          "| Dataset / Top | Line | Branch | Toggle | FSM State | FSM Arc |",
          "| --- | --- | --- | --- | --- | --- |"]
    for did, ds in manifest["datasets"].items():
        values = [f"{ds['metrics'][metric]['hit']}/{ds['metrics'][metric]['total']}" for metric in METRICS]
        md.append(f"| {did} / {ds['top']} | " + " | ".join(values) + " |")
    md += ["", "## Main Top未覆盖代码按模块统计", "",
           "下表每项为零点数，模块名相同但实例不同的FSM/Branch义务仍保留在CSV中。", "",
           "| RTL Source | Line | Branch | Toggle | FSM State | FSM Arc |",
           "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for source in sorted({p['source'] for p in points if p['dataset_id']=='main_subsystem'}):
        values = [str(groups[("main_subsystem",source,metric)]["zero"]) for metric in METRICS]
        md.append("| " + source + " | " + " | ".join(values) + " |")
    md += ["", "## 哪些源码行没有执行", "",
           "以下范围均是LCOV零命中行，仅适用于列出的Dataset。Branch/FSM缺口另有原生Point ID，不能从行覆盖推断关闭。", "",
           "| Dataset | RTL Source | 未覆盖源码行 |", "| --- | --- | --- |"]
    for (did, source), numbers in sorted(lines.items()):
        md.append(f"| {did} | {source} | {line_ranges(numbers)} |")
    md += ["", "## 处置边界", "",
           "- Legal Reachable：必须由实际同Top刺激、DUT事件与独立Checker证明；未决点不自动归为不可测。",
           "- Illegal Protocol/Defensive：明确错误赋值已单列，仍需逐路径Fault Injection或Producer Safety；不能删除防御逻辑。",
           "- Structurally Unreachable：L1 ID/编码/Reset和读端口组合证明的具体边界见final_verification_report.md；证明候选与审批分开，不自动减分母。",
           "- Tool Limited：实际L2+Engine Formal因数组混合赋值前端限制无法展开，保留配置及失败日志；不等于不可达。",
           "- Unresolved：Context2/3、剩余Producer与FSM源状态保持OPEN；Toggle不要求无依据地全部翻转。", "",
           "60个Directory低位候选的当前哈希及独立审批状态见`../final_freeze/waiver_review_submission.json`；未批准。", "",
           "## 逐点文件与证据", "",
           "- `code_coverage/main_uncovered_control_points.csv`：Main每个Line/Branch/FSM缺口，包含源码条件、原生身份、Point ID与哈希。",
           "- `code_coverage/uncovered_control_points.csv`：全部8个Dataset的非Toggle零点。",
           "- `code_coverage/uncovered_points.csv.gz`：全部零点，包含Toggle原生实例/信号/位/方向身份。",
           "- `code_coverage/module_summary.json`：每Dataset×Source×Metric的分子、分母和零点数。",
           "- `code_coverage/dataset_manifest.json`：Source/Top/Dataset/Raw Hash与验证契约。",
           "- `final_verification_report.md`及`remaining_risks.md`：当前签核、五类边界证据和最小剩余任务。", "",
           "本报告只统计当前Raw事实和待办，不冒充独立审查批准。Raw Hit核验和回归状态以当前Release Gate证据为准。"]
    (ROOT / "reports/final/code_coverage_report.md").write_text("\n".join(md) + "\n")
    hashes = [{"path": str(p.relative_to(ROOT)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
              for p in sorted(OUT.iterdir()) if p.is_file() and p.name != "evidence_hashes.json"]
    (OUT / "evidence_hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
