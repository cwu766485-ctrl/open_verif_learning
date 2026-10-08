"""CLI/report helper for Python functional coverage."""

import argparse
import json
from pathlib import Path


def render_html(input_path, output_path):
    data = json.loads(Path(input_path).read_text())
    rows = "\n".join(
        f"<tr><td>{name}</td><td>{count}</td></tr>"
        for name, count in sorted(data.get("bins", {}).items())
    )
    html = ("<html><body><h1>Cache functional coverage</h1>"
            f"<p>Transactions: {data.get('transactions', 0)}</p>"
            "<table border='1'><tr><th>Bin</th><th>Count</th></tr>"
            f"{rows}</table></body></html>")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", default="reports/functional_coverage.json")
    parser.add_argument("output", nargs="?", default="reports/functional_coverage.html")
    args = parser.parse_args()
    render_html(args.input, args.output)
