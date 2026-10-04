import html
import json
from pathlib import Path


def _value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"))
    return str(value)


def write_html_report(input_path, output_path):
    data=json.loads(Path(input_path).read_text())
    rows=[]
    for check in data.get("checks", []):
        rows.append(
            "<tr><td>{}</td><td class='{}'>{}</td><td>{}</td></tr>".format(
                html.escape(str(check.get("name", ""))),
                "pass" if check.get("status") == "PASS" else "fail",
                html.escape(str(check.get("status", ""))),
                html.escape(_value(check.get("details", ""))),
            )
        )
    recommendations="".join(
        f"<li>{html.escape(str(item))}</li>"
        for item in data.get("recommendations", [])
    )
    title="SpatialScan capture report"
    body=f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<style>body{{font:16px system-ui,sans-serif;max-width:1100px;margin:40px auto;padding:0 20px;color:#1f2937}}
h1{{margin-bottom:4px}} .meta{{color:#64748b}} .score{{font-size:42px;font-weight:700}}
table{{border-collapse:collapse;width:100%;margin-top:20px}}th,td{{border-bottom:1px solid #e2e8f0;padding:10px;text-align:left;vertical-align:top}}
.pass{{color:#087f5b;font-weight:700}} .fail{{color:#c92a2a;font-weight:700}}
code{{white-space:pre-wrap}} li{{margin:8px 0}}</style></head>
<body><h1>{title}</h1><p class="meta">Tier: {html.escape(str(data.get('tier','unknown')))} · Input: {html.escape(str(data.get('input','')))}</p>
<div class="score">{html.escape(str(data.get('score', 'n/a')))}<small>/100</small></div>
<p><strong>Readiness:</strong> {html.escape(str(data.get('readiness', data.get('status', 'unknown'))))}</p>
<h2>Checks</h2><table><thead><tr><th>Check</th><th>Status</th><th>Details</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<h2>Recommendations</h2><ul>{recommendations or '<li>No recommendations.</li>'}</ul>
</body></html>"""
    destination=Path(output_path)
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(body,encoding="utf-8")