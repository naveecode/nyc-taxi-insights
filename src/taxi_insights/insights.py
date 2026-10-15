"""Write INSIGHTS.md from the aggregate extracts."""

from __future__ import annotations

from taxi_insights.narrative import (
    DASHBOARD_URL,
    Finding,
    build_findings,
    build_headlines,
    load_frames,
    save_headlines,
)
from taxi_insights.paths import ROOT


def _queries(finding: Finding) -> str:
    return ", ".join(f"[`{path}`]({path})" for path in finding.queries)


def _charts(finding: Finding) -> str:
    blocks = []
    for chart in finding.charts:
        path = f"docs/figures/{chart}.png"
        blocks.append(f"![{finding.title}]({path})")
    return "\n\n".join(blocks)


def render(findings: list[Finding], headlines: dict[str, object]) -> str:
    rows = "\n".join(
        f"| {index} | {finding.title} | {finding.headline} |"
        for index, finding in enumerate(findings, start=1)
    )
    sections = []
    for index, finding in enumerate(findings, start=1):
        sections.append(
            "\n".join(
                [
                    f"## {index}. {finding.title}",
                    "",
                    f"**Question.** {finding.question}",
                    "",
                    f"**Query.** {_queries(finding)}",
                    "",
                    "**Chart.**",
                    "",
                    _charts(finding),
                    "",
                    f"**Number.** {finding.headline}",
                    "",
                    finding.detail,
                    "",
                    f"**Recommendation.** {finding.recommendation}",
                ]
            )
        )
    population = int(headlines["population_trips"])
    published = int(headlines["published_rows"])
    body = "\n\n".join(sections)
    return f"""# Insights: NYC yellow taxi, 2024

These eight findings are computed from the TLC yellow trip records for calendar year 2024. DuckDB reads the monthly Parquet files directly. The SQL is in [`sql/`](sql/). Every count, rate, and dollar figure below is taken from that output. Nothing here is a placeholder.

The in-policy population is defined in [`sql/00_population.sql`](sql/00_population.sql): a 2024 pickup, a completed trip of at most three hours, distance between 0 and 100 miles, fare between $0 and $300, and a positive total. That keeps **{population:,}** trips out of **{published:,}** published rows. The same population sits behind the [live dashboard]({DASHBOARD_URL}).

Reproduce the extracts with `make data && make report`.

| # | Finding | Number |
| --- | --- | --- |
{rows}

{body}
"""


def main() -> None:
    frames = load_frames()
    headlines = build_headlines(frames)
    findings = build_findings(frames)
    save_headlines(headlines)
    destination = ROOT / "INSIGHTS.md"
    destination.write_text(render(findings, headlines), encoding="utf-8")
    print(f"wrote {destination}")


if __name__ == "__main__":
    main()
