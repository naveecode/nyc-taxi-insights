"""Build the static Plotly dashboard in site/index.html."""

from __future__ import annotations

import html

import plotly.graph_objects as go
from plotly.offline import get_plotlyjs

from taxi_insights.figures import build_figures, chart_title
from taxi_insights.format import commas, money, mph, pct
from taxi_insights.narrative import (
    Finding,
    build_findings,
    build_headlines,
    load_frames,
    save_headlines,
)
from taxi_insights.paths import SITE_DIR


def _div(fig: go.Figure, key: str) -> str:
    return fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        div_id=f"chart-{key}",
        config={"displayModeBar": False, "responsive": True},
    )


def _section(index: int, finding: Finding, charts: dict[str, str]) -> str:
    chart_html = "\n".join(
        f'<figure class="chart">{charts[key]}<figcaption>{html.escape(chart_title(key))}</figcaption></figure>'
        for key in finding.charts
    )
    queries = ", ".join(f"<code>{html.escape(path)}</code>" for path in finding.queries)
    return f"""
    <section id="{html.escape(finding.slug)}">
      <p class="kicker">{index:02d}</p>
      <h2>{html.escape(finding.title)}</h2>
      <p class="question">{html.escape(finding.question)}</p>
      <p class="answer">{html.escape(finding.headline)}</p>
      {chart_html}
      <p class="detail">{html.escape(finding.detail)}</p>
      <p class="recommendation"><span>Recommendation.</span> {html.escape(finding.recommendation)}</p>
      <p class="query">Query {queries}</p>
    </section>
    """


def render_page(
    findings: list[Finding],
    headlines: dict[str, object],
    charts: dict[str, str],
    plotly_js: str,
) -> str:
    sections = "\n".join(
        _section(index, finding, charts) for index, finding in enumerate(findings, start=1)
    )
    nav = "\n".join(
        f'<a href="#{html.escape(finding.slug)}">{index:02d} {html.escape(finding.title)}</a>'
        for index, finding in enumerate(findings, start=1)
    )
    population = commas(float(headlines["population_trips"]))
    published = commas(float(headlines["published_rows"]))
    excluded = pct(float(headlines["excluded_rate"]))
    peak = html.escape(str(headlines["peak_hour_label"]))
    peak_share = pct(float(headlines["peak_share"]))
    card_tip = pct(float(headlines["card_median_tip_pct"]))
    jfk_fare = money(float(headlines["jfk_flat_fare"]))
    slow = (
        f"{html.escape(str(headlines['slowest_borough']))} "
        f"{html.escape(str(headlines['slowest_hour_label']))}"
    )
    slow_mph = mph(float(headlines["slowest_mph"]))
    top_zone = html.escape(str(headlines["top_zone"]))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NYC yellow taxi, 2024</title>
  <meta name="description" content="A year of NYC yellow taxi trips: demand, zones, tips, airport fares, speed, and data quality.">
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='4' fill='%231a1814'/%3E%3Crect x='6' y='12' width='20' height='10' rx='2' fill='%23d4920a'/%3E%3C/svg%3E">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,560;9..144,640&family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400&display=swap" rel="stylesheet">
  <style>
    :root {{
      --paper: #f3efe6;
      --ink: #1a1814;
      --muted: #5c564c;
      --line: #e3dac8;
      --card: #fffdf8;
      --amber: #d4920a;
      --teal: #1e4d5c;
      --rose: #8d3b3b;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: "Source Sans 3", "Segoe UI", sans-serif;
      font-size: 18px;
      line-height: 1.55;
    }}
    a {{ color: var(--teal); }}
    header, main, footer {{ width: min(1080px, calc(100% - 32px)); margin: 0 auto; }}
    header {{ padding: 48px 0 12px; }}
    .eyebrow {{
      margin: 0 0 12px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      font-size: 12px;
      font-weight: 700;
      color: var(--muted);
    }}
    h1 {{
      margin: 0;
      font-family: Fraunces, Georgia, serif;
      font-weight: 560;
      font-size: clamp(40px, 6vw, 68px);
      line-height: 1.02;
      letter-spacing: -0.03em;
    }}
    h1 em {{ font-style: italic; color: var(--teal); }}
    .lede {{ max-width: 42rem; font-size: 20px; color: var(--muted); }}
    .rule {{ height: 8px; width: 96px; background: var(--amber); border: 0; margin: 28px 0; }}
    nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px 14px;
      padding-bottom: 8px;
    }}
    nav a {{
      color: var(--ink);
      text-decoration: none;
      font-size: 14px;
      border-bottom: 1px solid var(--line);
    }}
    nav a:hover {{ border-color: var(--amber); }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      margin: 12px 0 28px;
    }}
    .kpi {{
      background: var(--card);
      border: 1px solid var(--line);
      padding: 16px 16px 14px;
    }}
    .kpi-label {{
      margin: 0;
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      font-weight: 700;
    }}
    .kpi-value {{
      margin: 6px 0 0;
      font-family: Fraunces, Georgia, serif;
      font-size: 32px;
      line-height: 1.1;
      letter-spacing: -0.03em;
    }}
    .kpi-note {{ margin: 4px 0 0; color: var(--muted); font-size: 14px; }}
    section {{
      padding: 28px 0 12px;
      border-top: 1px solid var(--line);
    }}
    .kicker {{
      margin: 0;
      color: var(--amber);
      font-weight: 700;
      letter-spacing: 0.12em;
      font-size: 13px;
    }}
    h2 {{
      margin: 4px 0 8px;
      font-family: Fraunces, Georgia, serif;
      font-weight: 560;
      font-size: clamp(28px, 4vw, 40px);
      letter-spacing: -0.03em;
      line-height: 1.1;
    }}
    .question {{ margin: 0; color: var(--muted); }}
    .answer {{
      font-family: Fraunces, Georgia, serif;
      font-size: 26px;
      line-height: 1.25;
      margin: 16px 0;
    }}
    .chart {{
      background: var(--card);
      border: 1px solid var(--line);
      padding: 8px 8px 4px;
      margin: 12px 0;
    }}
    figcaption {{
      color: var(--muted);
      font-size: 13px;
      padding: 0 8px 8px;
    }}
    .detail {{ max-width: 46rem; }}
    .recommendation {{
      max-width: 46rem;
      border-left: 3px solid var(--amber);
      padding: 4px 0 4px 14px;
    }}
    .recommendation span {{ font-weight: 700; }}
    .query {{ color: var(--muted); font-size: 14px; }}
    code {{ font-size: 13px; }}
    footer {{
      padding: 28px 0 64px;
      color: var(--muted);
      font-size: 15px;
      border-top: 1px solid var(--line);
      margin-top: 24px;
    }}
    footer h2 {{ font-size: 22px; }}
    @media (max-width: 800px) {{
      .kpis {{ grid-template-columns: 1fr 1fr; }}
      body {{ font-size: 16px; }}
    }}
    @media (max-width: 520px) {{
      .kpis {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body
  data-peak-hour="{int(headlines["peak_hour"])}"
  data-population-trips="{int(headlines["population_trips"])}"
  data-top-zone="{top_zone}"
  data-card-tip="{card_tip}"
  data-jfk-fare="{jfk_fare}"
  data-slowest-borough="{html.escape(str(headlines["slowest_borough"]))}"
  data-busiest-month="{html.escape(str(headlines["busiest_month_name"]))}"
>
  <header>
    <p class="eyebrow">NYC Taxi &amp; Limousine Commission · Yellow cab · 2024</p>
    <h1>A year of yellow cabs, <em>told from the file.</em></h1>
    <hr class="rule">
    <p class="lede">
      {population} in-policy trips, from {published} published rows.
      DuckDB reads the TLC Parquet in place. The charts are the aggregates,
      and every sentence is computed from them.
    </p>
    <nav>{nav}</nav>
    <div class="kpis">
      <article class="kpi">
        <p class="kpi-label">In-policy trips</p>
        <p class="kpi-value">{population}</p>
        <p class="kpi-note">{excluded} of published rows excluded</p>
      </article>
      <article class="kpi">
        <p class="kpi-label">Peak hour</p>
        <p class="kpi-value">{peak}</p>
        <p class="kpi-note">{peak_share} of in-policy trips</p>
      </article>
      <article class="kpi">
        <p class="kpi-label">Median card tip</p>
        <p class="kpi-value">{card_tip}</p>
        <p class="kpi-note">of the pre-tip bill</p>
      </article>
      <article class="kpi">
        <p class="kpi-label">Slowest stable hour</p>
        <p class="kpi-value">{slow_mph}</p>
        <p class="kpi-note">{slow}</p>
      </article>
    </div>
  </header>
  <main>
    {sections}
  </main>
  <footer>
    <h2>How the numbers were made</h2>
    <p>
      Source: NYC TLC yellow trip records, January–December 2024, plus
      <code>taxi_zone_lookup.csv</code>. Files are the public CloudFront Parquet
      distribution. No warehouse copy: each query is a DuckDB scan of the files.
    </p>
    <p>
      In-policy trips, used for demand, zones, tips, airports, speed, and month,
      have a pickup in calendar 2024, a duration from 1 second through 3 hours,
      distance in (0, 100] miles, fare in (0, 300], and a positive total.
      Data-quality and anomaly rates use every published row.
      Speed medians further require 0.5–80 mph. The slowest-hour callout
      requires at least 1,000 trips in that borough-hour.
      Tip percent is tip divided by total minus tip.
      The JFK flat fare is rate code 2. Airports are zones 132 (JFK), 138 (LaGuardia), and 1 (Newark).
    </p>
    <p>
      Stack: DuckDB, pandas, Plotly. The same figures are written to
      <code>docs/figures/</code> for the insight write-up. Busiest pickup zone on this cut: {top_zone}.
    </p>
  </footer>
  <script>{plotly_js}</script>
</body>
</html>
"""


def main() -> None:
    frames = load_frames()
    headlines = build_headlines(frames)
    findings = build_findings(frames)
    save_headlines(headlines)
    charts = {key: _div(fig, key) for key, fig in build_figures(frames).items()}
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    destination = SITE_DIR / "index.html"
    destination.write_text(
        render_page(findings, headlines, charts, get_plotlyjs()),
        encoding="utf-8",
    )
    print(f"wrote {destination} ({destination.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
