"""JSON 报告生成器 - 输出 JSON 格式的聚合指标与 Contract 验证结果。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sagellm_benchmark.types import AggregatedMetrics, ContractResult


class JSONReporter:
    """JSON 格式报告生成器。

    输出格式：
    ```json
    {
      "metrics": {...},
      "contract": {...},
      "timestamp": "2026-01-17T10:30:00",
      "version": "0.1.0.2"
    }
    ```
    """

    @staticmethod
    def generate(
        metrics: AggregatedMetrics,
        contract: ContractResult | None = None,
        output_path: Path | str | None = None,
        **extra_fields: Any,
    ) -> str:
        """生成 JSON 报告。

        Args:
            metrics: 聚合指标。
            contract: Contract 验证结果（可选）。
            output_path: 输出文件路径（None 则不保存）。
            **extra_fields: 额外字段（如 version, timestamp 等）。

        Returns:
            JSON 字符串。
        """
        from dataclasses import asdict

        report: dict[str, Any] = {
            "metrics": asdict(metrics),
        }

        if contract:
            report["contract"] = asdict(contract)

        # 添加额外字段
        report.update(extra_fields)

        # 生成 JSON 字符串
        json_str = json.dumps(report, indent=2, ensure_ascii=False)

        # 保存到文件
        if output_path:
            Path(output_path).write_text(json_str, encoding="utf-8")

        return json_str

    @staticmethod
    def load(file_path: Path | str) -> dict[str, Any]:
        """从 JSON 文件加载报告。

        Args:
            file_path: JSON 文件路径。

        Returns:
            解析后的字典。
        """
        return json.loads(Path(file_path).read_text(encoding="utf-8"))
