"""Baseline management utilities for benchmark regression checks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class BaselineManager:
    """Manage persisted benchmark baselines."""

    baseline_path: Path

    def load(self) -> dict[str, Any]:
        """Load baseline payload from disk."""
        with self.baseline_path.open(encoding="utf-8") as file:
            return json.load(file)

    def save(self, payload: dict[str, Any]) -> None:
        """Persist baseline payload to disk."""
        self.baseline_path.parent.mkdir(parents=True, exist_ok=True)
        with self.baseline_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)

    def update(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Update baseline with current benchmark payload and metadata."""
        updated_payload = dict(payload)
        metadata = dict(updated_payload.get("metadata", {}))
        metadata["baseline_updated_at"] = datetime.now(UTC).isoformat()
        updated_payload["metadata"] = metadata
        self.save(updated_payload)
        return updated_payload
