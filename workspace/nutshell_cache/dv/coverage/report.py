"""HTML renderer for Python functional coverage."""
import json
from pathlib import Path
from html import escape

def render_html(input_path="reports/functional_coverage.json", output_path="reports/functional_coverage.html"):
    data = json.loads(Path(input_path).read_text())
    rows = "".join(f"<tr><td>{escape(str(k))}</td><td>{v}</td></tr>" for k, v in sorted(data.get("bins", {}).items()))
    summary = data.get("functional_coverage", {})
    out = Path(output_path); out.parent.mkdir(parents=True, exist_ok=True)
    missing = ", ".join(escape(x) for x in summary.get("uncovered", [])) or "None"
    out.write_text(
        "<html><head><meta charset='utf-8'><title>Cache functional coverage</title></head><body>"
        f"<h1>Cache functional coverage</h1><p>Transactions: {data.get('transactions', 0)}</p>"
        f"<p>Goals: {summary.get('covered_goals', 0)}/{summary.get('total_goals', 0)} "
        f"({summary.get('percent', 0)}%)</p><p>Uncovered: {missing}</p>"
        f"<table><thead><tr><th>Bin</th><th>Hits</th></tr></thead><tbody>{rows}</tbody></table></body></html>"
    )
    return out
