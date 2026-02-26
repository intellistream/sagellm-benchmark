"""Reporters 模块 - 报告生成器。

此模块提供：
- JSONReporter: 输出 JSON 格式报告
- MarkdownReporter: 输出 Markdown 格式报告
- TableReporter: 输出终端表格（Rich）
- HTMLReporter: 输出交互式 HTML 报告（含 Chart.js 可视化）
"""

from __future__ import annotations

from .html_reporter import HTMLReporter
from .json_reporter import JSONReporter
from .markdown_reporter import MarkdownReporter
from .table_reporter import TableReporter

__all__ = [
    "HTMLReporter",
    "JSONReporter",
    "MarkdownReporter",
    "TableReporter",
]
