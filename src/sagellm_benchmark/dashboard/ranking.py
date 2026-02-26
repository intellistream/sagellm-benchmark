"""Ranking Dashboard — generate an interactive HTML leaderboard from benchmark results.

Loads JSON results from benchmark_results/ or user-specified paths, groups
them by dataset/workload, and renders a sortable HTML ranking table.

Usage (CLI)::

    sagellm-benchmark dashboard --results ./benchmark_results --output dashboard.html

Usage (Python)::

    from sagellm_benchmark.dashboard import RankingDashboard

    db = RankingDashboard(results_dir="./benchmark_results")
    html = db.generate(output_path="dashboard.html")
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Chart.js CDN
_CHARTJS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"

# SortableJS for interactive tables
_SORTABLE_CDN = "https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js"


@dataclass
class LeaderboardEntry:
    """A single row in the ranking leaderboard.

    Attributes:
        model: Model name / identifier.
        scenario: Benchmark scenario / workload name.
        backend: Backend/engine that ran this benchmark (inferred from file).
        hardware: Hardware tag (if present in result data).
        ttft_ms: Time-To-First-Token in milliseconds.
        tbt_ms: Time-Between-Tokens in milliseconds.
        throughput_tps: Output token throughput (tokens/s).
        latency_p50_ms: P50 end-to-end latency (ms).
        latency_p99_ms: P99 end-to-end latency (ms).
        memory_mb: Peak memory (MB).
        source_file: Source JSON filename.
        extra: Any additional fields from the JSON.
    """

    model: str
    scenario: str
    backend: str = "unknown"
    hardware: str = "unknown"
    ttft_ms: float = 0.0
    tbt_ms: float = 0.0
    throughput_tps: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p99_ms: float = 0.0
    memory_mb: float = 0.0
    source_file: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


class RankingDashboard:
    """Generate an interactive HTML ranking leaderboard from benchmark results.

    Loads all ``*.json`` result files from a directory, extracts row-level
    results, and constructs a sortable ranking table grouped by scenario.

    Args:
        results_dir: Directory containing JSON result files. Defaults to
            ``./benchmark_results``.
        extra_files: Additional JSON files to include.
    """

    def __init__(
        self,
        results_dir: str | Path = "./benchmark_results",
        extra_files: list[str | Path] | None = None,
    ) -> None:
        self.results_dir = Path(results_dir)
        self.extra_files: list[Path] = [Path(f) for f in (extra_files or [])]
        self._entries: list[LeaderboardEntry] = []

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load all JSON result files from ``results_dir`` and ``extra_files``."""
        self._entries.clear()
        files: list[Path] = []
        if self.results_dir.is_dir():
            files.extend(sorted(self.results_dir.glob("*.json")))
        files.extend(self.extra_files)

        if not files:
            logger.warning(f"No JSON result files found in {self.results_dir}")
            return

        for f in files:
            self._load_file(f)

        logger.info(f"Loaded {len(self._entries)} result row(s) from {len(files)} file(s)")

    def _load_file(self, path: Path) -> None:
        """Load a single JSON result file."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Skipping {path.name}: {exc}")
            return

        stem = path.stem  # used as default backend label

        # Support the "rows" format (perf_results.json style)
        if "rows" in data and isinstance(data["rows"], list):
            for row in data["rows"]:
                entry = self._parse_row(row, source=path.name, backend=stem)
                if entry:
                    self._entries.append(entry)
            return

        # Support the aggregated "metrics" format (JSONReporter output)
        if "metrics" in data and isinstance(data["metrics"], dict):
            entry = self._parse_metrics(data, source=path.name, backend=stem)
            if entry:
                self._entries.append(entry)
            return

        logger.debug(f"Unrecognized format in {path.name}, skipping")

    def _parse_row(self, row: dict[str, Any], source: str, backend: str) -> LeaderboardEntry | None:
        """Parse a single row from the 'rows' array."""
        model = row.get("model", "unknown")
        scenario = row.get("scenario", "unknown")
        return LeaderboardEntry(
            model=model,
            scenario=scenario,
            backend=row.get("backend", backend),
            hardware=row.get("hardware", "unknown"),
            ttft_ms=float(row.get("ttft_ms", 0)),
            tbt_ms=float(row.get("tbt_ms", 0)),
            throughput_tps=float(row.get("throughput_tps", 0)),
            latency_p50_ms=float(row.get("latency_p50_ms", 0)),
            latency_p99_ms=float(row.get("latency_p99_ms", 0)),
            memory_mb=float(row.get("memory_mb", 0)),
            source_file=source,
            extra={
                k: v
                for k, v in row.items()
                if k
                not in {
                    "model",
                    "scenario",
                    "backend",
                    "hardware",
                    "ttft_ms",
                    "tbt_ms",
                    "throughput_tps",
                    "latency_p50_ms",
                    "latency_p99_ms",
                    "memory_mb",
                }
            },
        )

    def _parse_metrics(
        self, data: dict[str, Any], source: str, backend: str
    ) -> LeaderboardEntry | None:
        """Parse aggregated metrics from JSONReporter format."""
        m = data["metrics"]
        model = data.get("model", source.replace(".json", ""))
        scenario = data.get("workload", data.get("scenario", "aggregated"))
        return LeaderboardEntry(
            model=model,
            scenario=scenario,
            backend=data.get("backend", backend),
            hardware=data.get("hardware", "unknown"),
            ttft_ms=float(m.get("avg_ttft_ms", 0)),
            tbt_ms=float(m.get("avg_tbt_ms", 0)),
            throughput_tps=float(m.get("output_throughput_tps", 0)),
            latency_p50_ms=float(m.get("p50_ttft_ms", 0)),
            latency_p99_ms=float(m.get("p99_ttft_ms", 0)),
            memory_mb=float(m.get("peak_mem_mb", 0)),
            source_file=source,
        )

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(
        self,
        output_path: str | Path | None = None,
        title: str = "SageLLM Performance Leaderboard",
        sort_by: str = "throughput_tps",
        descending: bool = True,
    ) -> str:
        """Generate the HTML ranking dashboard.

        Args:
            output_path: If provided, write the HTML to this path.
            title: Page title.
            sort_by: Default sort column (throughput_tps, ttft_ms, latency_p99_ms).
            descending: Sort in descending order by default.

        Returns:
            HTML string.
        """
        if not self._entries:
            self.load()

        entries = sorted(
            self._entries,
            key=lambda e: getattr(e, sort_by, 0),
            reverse=descending,
        )

        html = self._build_html(entries, title=title)

        if output_path:
            Path(output_path).write_text(html, encoding="utf-8")
            logger.info(f"Dashboard written to {output_path}")

        return html

    def _build_html(self, entries: list[LeaderboardEntry], title: str) -> str:
        """Build the complete HTML."""
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Unique scenarios for tab navigation
        scenarios = list(dict.fromkeys(e.scenario for e in entries))

        # Build table rows per scenario
        def _rows_for_scenario(sc: str) -> str:
            rows = ""
            rank = 1
            for e in entries:
                if e.scenario != sc:
                    continue
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, str(rank))
                rows += f"""
                <tr>
                    <td>{medal}</td>
                    <td class="model-col">{e.model}</td>
                    <td>{e.backend}</td>
                    <td>{e.hardware}</td>
                    <td>{e.ttft_ms:.1f}</td>
                    <td>{e.tbt_ms:.2f}</td>
                    <td><b>{e.throughput_tps:.1f}</b></td>
                    <td>{e.latency_p50_ms:.1f}</td>
                    <td>{e.latency_p99_ms:.1f}</td>
                    <td>{e.memory_mb:.0f}</td>
                </tr>"""
                rank += 1
            return rows

        # Build tabs
        tabs_html = ""
        panels_html = ""
        for i, sc in enumerate(scenarios):
            active = "active" if i == 0 else ""
            tabs_html += f'<button class="tab-btn {active}" onclick="showTab(\'{sc}\')" id="tab-{sc}">{sc}</button>\n'
            panels_html += f"""
            <div class="tab-panel" id="panel-{sc}" {"style='display:block'" if i == 0 else "style='display:none'"}>
                <table id="table-{sc}" class="ranking-table sortable">
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th onclick="sortTable('table-{sc}', 1)">Model ▲▼</th>
                            <th onclick="sortTable('table-{sc}', 2)">Backend ▲▼</th>
                            <th onclick="sortTable('table-{sc}', 3)">Hardware ▲▼</th>
                            <th onclick="sortTable('table-{sc}', 4)">TTFT (ms) ▲▼</th>
                            <th onclick="sortTable('table-{sc}', 5)">TBT (ms) ▲▼</th>
                            <th onclick="sortTable('table-{sc}', 6)">Throughput (tok/s) ▲▼</th>
                            <th onclick="sortTable('table-{sc}', 7)">P50 Lat (ms) ▲▼</th>
                            <th onclick="sortTable('table-{sc}', 8)">P99 Lat (ms) ▲▼</th>
                            <th onclick="sortTable('table-{sc}', 9)">Mem (MB) ▲▼</th>
                        </tr>
                    </thead>
                    <tbody>
                        {_rows_for_scenario(sc)}
                    </tbody>
                </table>
            </div>"""

        total_entries = len(entries)
        total_models = len({e.model for e in entries})
        total_scenarios = len(scenarios)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f2f5;
            margin: 0;
            color: #222;
        }}
        header {{
            background: linear-gradient(135deg, #0d1b2a 0%, #1b2838 50%, #0f3460 100%);
            color: #fff;
            padding: 2rem 2.5rem;
            text-align: center;
        }}
        header h1 {{ margin: 0 0 0.5rem; font-size: 2rem; }}
        header p {{ margin: 0; opacity: 0.75; font-size: 0.9rem; }}
        .stats-bar {{
            display: flex;
            justify-content: center;
            gap: 2rem;
            padding: 1.2rem;
            background: #1b2838;
            color: #ddd;
            font-size: 0.9rem;
        }}
        .stats-bar span b {{ color: #4fc3f7; font-size: 1.3rem; }}
        .container {{ max-width: 1300px; margin: 0 auto; padding: 1.5rem; }}
        .tabs {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 1rem;
        }}
        .tab-btn {{
            padding: 0.5rem 1.2rem;
            border: 2px solid #0f3460;
            background: #fff;
            color: #0f3460;
            border-radius: 20px;
            cursor: pointer;
            font-size: 0.85rem;
            transition: all 0.2s;
        }}
        .tab-btn.active, .tab-btn:hover {{
            background: #0f3460;
            color: #fff;
        }}
        .tab-panel {{ display: none; }}
        .ranking-table {{
            width: 100%;
            border-collapse: collapse;
            background: #fff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            font-size: 0.88rem;
        }}
        .ranking-table thead tr {{
            background: #0f3460;
            color: #fff;
        }}
        .ranking-table th {{
            padding: 0.75rem 1rem;
            text-align: left;
            cursor: pointer;
            white-space: nowrap;
            user-select: none;
        }}
        .ranking-table th:hover {{ background: #1a4a80; }}
        .ranking-table td {{ padding: 0.6rem 1rem; border-bottom: 1px solid #eee; }}
        .ranking-table tbody tr:hover td {{ background: #f0f4ff; }}
        .model-col {{ font-weight: 600; color: #0f3460; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        footer {{ text-align: center; color: #999; font-size: 0.8rem; padding: 2rem; }}
    </style>
</head>
<body>
<header>
    <h1>🏆 {title}</h1>
    <p>Generated: {generated_at}</p>
</header>

<div class="stats-bar">
    <span>Results: <b>{total_entries}</b></span>
    <span>Models: <b>{total_models}</b></span>
    <span>Scenarios: <b>{total_scenarios}</b></span>
</div>

<div class="container">
    <div class="tabs">
        {tabs_html}
    </div>
    {panels_html}
</div>

<footer>Generated by sagellm-benchmark dashboard &nbsp;|&nbsp; {generated_at}</footer>

<script>
function showTab(sc) {{
    document.querySelectorAll('.tab-panel').forEach(p => p.style.display = 'none');
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    const panel = document.getElementById('panel-' + sc);
    const btn = document.getElementById('tab-' + sc);
    if (panel) panel.style.display = 'block';
    if (btn) btn.classList.add('active');
}}

function sortTable(tableId, col) {{
    const table = document.getElementById(tableId);
    if (!table) return;
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const asc = table.dataset.sortCol == col && table.dataset.sortDir !== 'asc';
    table.dataset.sortCol = col;
    table.dataset.sortDir = asc ? 'asc' : 'desc';
    rows.sort((a, b) => {{
        const av = a.cells[col]?.innerText.trim() ?? '';
        const bv = b.cells[col]?.innerText.trim() ?? '';
        const an = parseFloat(av), bn = parseFloat(bv);
        const na = isNaN(an), nb = isNaN(bn);
        let cmp = na || nb ? av.localeCompare(bv) : an - bn;
        return asc ? cmp : -cmp;
    }});
    rows.forEach(r => tbody.appendChild(r));
}}
</script>
</body>
</html>
"""
