"""Production-style HTML report for RACE dry-run order artifacts."""

from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any


def render_order_html_report(artifact: dict[str, Any]) -> str:
    status = str(artifact.get("validation_status", "UNKNOWN"))
    diagnostic_only = bool(artifact.get("diagnostic_only", True))
    mode_label = "Diagnostic Only" if diagnostic_only else "Manual Review Ready"
    mode_class = "warn" if diagnostic_only else "pass"
    orders = artifact.get("orders") or []
    sleeve_targets = artifact.get("sleeve_targets") or {}
    target_positions = artifact.get("target_positions") or {}
    gate_failures = artifact.get("gate_failures") or {}
    generated_at = _format_timestamp(artifact.get("timestamp"))

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>RACE Dry-Run Report</title>
  <style>
    :root {{
      --bg: #f7f8fa;
      --panel: #ffffff;
      --text: #1f2933;
      --muted: #64748b;
      --line: #d8dee8;
      --blue: #1f6feb;
      --green: #11845b;
      --red: #b42318;
      --amber: #b54708;
      --ink: #111827;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.45;
    }}
    .page {{ max-width: 1180px; margin: 0 auto; padding: 28px; }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 20px;
      align-items: flex-start;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--line);
    }}
    h1 {{ margin: 0 0 6px; font-size: 28px; color: var(--ink); }}
    h2 {{ margin: 0 0 14px; font-size: 18px; color: var(--ink); }}
    .subtle {{ color: var(--muted); font-size: 13px; }}
    .badge {{
      display: inline-block;
      border-radius: 999px;
      padding: 5px 10px;
      font-weight: 700;
      font-size: 12px;
      letter-spacing: .02em;
      text-transform: uppercase;
    }}
    .badge.pass {{ background: #dff7eb; color: var(--green); }}
    .badge.warn {{ background: #fff1d6; color: var(--amber); }}
    .badge.fail {{ background: #fde2df; color: var(--red); }}
    .grid {{ display: grid; gap: 16px; }}
    .kpis {{ grid-template-columns: repeat(5, minmax(0, 1fr)); margin: 22px 0; }}
    .two {{ grid-template-columns: 1fr 1fr; }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      box-shadow: 0 1px 2px rgba(16, 24, 40, .05);
    }}
    .kpi-label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; font-weight: 700; }}
    .kpi-value {{ margin-top: 5px; font-size: 22px; font-weight: 750; color: var(--ink); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ padding: 10px 9px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }}
    td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .buy {{ color: var(--green); font-weight: 700; }}
    .sell {{ color: var(--red); font-weight: 700; }}
    .hold {{ color: var(--muted); font-weight: 700; }}
    .entry-caution {{ color: var(--amber); font-weight: 700; }}
    .stage-entry {{ color: var(--amber); font-weight: 700; }}
    .defer-overbought {{ color: var(--red); font-weight: 700; }}
    .bar {{ height: 8px; background: #e7ecf3; border-radius: 999px; overflow: hidden; }}
    .bar span {{ display: block; height: 100%; background: var(--blue); }}
    .messages {{ margin: 0; padding-left: 18px; }}
    .footer {{ margin-top: 18px; color: var(--muted); font-size: 12px; }}
    @media (max-width: 900px) {{
      .kpis, .two {{ grid-template-columns: 1fr; }}
      header {{ display: block; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <header>
      <div>
        <h1>RACE Dry-Run Report</h1>
        <div class="subtle">Generated {escape(generated_at)} from {escape(str(artifact.get("market_data_source") or "unknown source"))}</div>
      </div>
      <div>
        <span class="badge {_status_class(status)}">{escape(status)}</span>
        <span class="badge {mode_class}">{escape(mode_label)}</span>
      </div>
    </header>

    <section class="grid kpis">
      {_kpi("Regime", artifact.get("confirmed_regime"))}
      {_kpi("Composite Score", _fmt_num(artifact.get("composite_regime_score"), 2))}
      {_kpi("Confidence", _fmt_pct(artifact.get("regime_confidence")))}
      {_kpi("Orders", len(orders))}
      {_kpi("Target Positions", len(target_positions))}
    </section>

    <section class="grid two">
      <div class="panel">
        <h2>Sleeve Targets</h2>
        {_weights_table(sleeve_targets, "Sleeve")}
      </div>
      <div class="panel">
        <h2>Target Positions</h2>
        {_weights_table(target_positions, "Ticker")}
      </div>
    </section>

    <section class="panel" style="margin-top:16px;">
      <h2>Dry-Run Orders</h2>
      {_orders_table(orders)}
    </section>

    <section class="grid two" style="margin-top:16px;">
      <div class="panel">
        <h2>Selected ETFs</h2>
        {_selected_table(artifact.get("selected_etfs") or {})}
      </div>
      <div class="panel">
        <h2>Validation Messages</h2>
        {_messages(artifact.get("validation_messages") or [])}
      </div>
    </section>

    <section class="panel" style="margin-top:16px;">
      <h2>Gate Failures</h2>
      {_gate_table(gate_failures)}
    </section>

    <div class="footer">
      RACE output is dry-run/manual-review only. This report does not transmit orders or call a broker.
    </div>
  </div>
</body>
</html>"""


def write_order_html_report(input_json: str | Path, output_html: str | Path) -> Path:
    input_path = Path(input_json)
    output_path = Path(output_html)
    artifact = json.loads(input_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_order_html_report(artifact), encoding="utf-8")
    return output_path


def _kpi(label: str, value: Any) -> str:
    return f"""<div class="panel"><div class="kpi-label">{escape(label)}</div><div class="kpi-value">{escape(str(value if value is not None else "n/a"))}</div></div>"""


def _weights_table(weights: dict[str, Any], label: str) -> str:
    if not weights:
        return '<div class="subtle">No weights available.</div>'
    rows = []
    for name, weight in sorted(weights.items(), key=lambda item: float(item[1]), reverse=True):
        value = float(weight)
        rows.append(
            f"<tr><td>{escape(str(name))}</td><td class=\"num\">{value:.2f}%</td><td><div class=\"bar\"><span style=\"width:{max(0, min(100, value)):.2f}%\"></span></div></td></tr>"
        )
    return f"<table><thead><tr><th>{escape(label)}</th><th class=\"num\">Weight</th><th>Scale</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _orders_table(orders: list[dict[str, Any]]) -> str:
    if not orders:
        return '<div class="subtle">No dry-run orders generated.</div>'
    rows = []
    for order in orders:
        side = str(order.get("side", "HOLD"))
        entry_status = str(order.get("entry_quality_status", "EXECUTE"))
        entry_reasons = order.get("entry_quality_reasons") or []
        entry_notes = ", ".join(str(reason) for reason in entry_reasons) if entry_reasons else ""
        rows.append(
            "<tr>"
            f"<td>{escape(str(order.get('ticker', '')))}</td>"
            f"<td class=\"{escape(side.lower())}\">{escape(side)}</td>"
            f"<td class=\"num\">{_fmt_num(order.get('target_weight'), 2)}%</td>"
            f"<td class=\"num\">{_fmt_num(order.get('current_weight'), 2)}%</td>"
            f"<td class=\"num\">${_fmt_num(order.get('dollar_change'), 2)}</td>"
            f"<td class=\"num\">{escape(str(order.get('estimated_shares', 0)))}</td>"
            f"<td>{escape(str(order.get('priority', '')))}</td>"
            f"<td>{escape(str(order.get('trade_quality_status', '')))}</td>"
            f"<td class=\"{_entry_status_class(entry_status)}\">{escape(entry_status)}</td>"
            f"<td>{escape(entry_notes)}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Ticker</th><th>Side</th><th class=\"num\">Target</th><th class=\"num\">Current</th><th class=\"num\">Dollar Change</th><th class=\"num\">Shares</th><th>Priority</th><th>Trade Quality</th><th>Entry Quality</th><th>Entry Notes</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _selected_table(selected: dict[str, list[str]]) -> str:
    if not selected:
        return '<div class="subtle">No selections available.</div>'
    rows = "".join(
        f"<tr><td>{escape(str(sleeve))}</td><td>{escape(', '.join(tickers))}</td></tr>"
        for sleeve, tickers in sorted(selected.items())
    )
    return f"<table><thead><tr><th>Sleeve</th><th>Selected ETFs</th></tr></thead><tbody>{rows}</tbody></table>"


def _messages(messages: list[Any]) -> str:
    if not messages:
        return '<div class="subtle">No validation messages.</div>'
    return '<ul class="messages">' + ''.join(f"<li>{escape(str(message))}</li>" for message in messages) + '</ul>'


def _gate_table(gate_failures: dict[str, dict[str, list[str]]]) -> str:
    if not gate_failures:
        return '<div class="subtle">No gate failures.</div>'
    rows = []
    for ticker, gates in sorted(gate_failures.items()):
        reason_text = "; ".join(f"{gate}: {', '.join(reasons)}" for gate, reasons in gates.items())
        rows.append(f"<tr><td>{escape(str(ticker))}</td><td>{escape(reason_text)}</td></tr>")
    return f"<table><thead><tr><th>Ticker</th><th>Reasons</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _format_timestamp(value: Any) -> str:
    if not value:
        return "unknown time"
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return str(value)


def _fmt_num(value: Any, digits: int) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):,.{digits}f}"


def _fmt_pct(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value) * 100:.0f}%"


def _status_class(status: str) -> str:
    lowered = status.lower()
    return "pass" if lowered == "pass" else "fail" if lowered == "fail" else "warn"


def _entry_status_class(status: str) -> str:
    return status.lower().replace("_", "-")
