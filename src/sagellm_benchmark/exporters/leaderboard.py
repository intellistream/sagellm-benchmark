"""Export benchmark results to sageLLM website leaderboard format."""

from __future__ import annotations

import json
import os
import platform
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sagellm_benchmark.types import AggregatedMetrics


# Workload 映射表（根据 Year1 Demo Contract）
WORKLOAD_SPECS = {
    "short_input": {"input_length": 128, "output_length": 128},
    "long_input": {"input_length": 2048, "output_length": 512},  # Year1 Demo Contract
    "stress_test": {"input_length": 256, "output_length": 256},
}


class LeaderboardExporter:
    """Export benchmark results to leaderboard format.

    Converts internal benchmark metrics to the format required by
    sagellm-website leaderboard (leaderboard_v1.schema.json).
    """

    @staticmethod
    def detect_hardware_info() -> dict[str, Any]:
        """Detect hardware information from system.

        Returns:
            Dictionary with hardware fields
        """
        # Detect CPU model and vendor
        cpu_model = platform.processor() or "unknown"
        if not cpu_model or cpu_model == "unknown":
            # platform.processor() is often empty on Linux; fall back to /proc/cpuinfo
            try:
                with open("/proc/cpuinfo") as f:
                    for line in f:
                        if line.startswith("model name"):
                            cpu_model = line.split(":", 1)[1].strip()
                            break
            except OSError:
                pass
            if not cpu_model or cpu_model == "unknown":
                cpu_model = platform.machine() or "CPU"

        # Detect CPU vendor from model string
        cpu_vendor = "Unknown"
        cpu_lower = cpu_model.lower()
        if "intel" in cpu_lower:
            cpu_vendor = "Intel"
        elif "amd" in cpu_lower or "ryzen" in cpu_lower or "epyc" in cpu_lower:
            cpu_vendor = "AMD"
        elif "apple" in cpu_lower or "m1" in cpu_lower or "m2" in cpu_lower or "m3" in cpu_lower:
            cpu_vendor = "Apple"
        elif "arm" in cpu_lower or "aarch" in cpu_lower:
            cpu_vendor = "ARM"

        # Detect system memory
        total_memory_gb = 0.0
        try:
            import psutil

            total_memory_gb = round(psutil.virtual_memory().total / (1024**3), 2)
        except ImportError:
            # Fallback: parse /proc/meminfo on Linux
            try:
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            kb = int(line.split()[1])
                            total_memory_gb = round(kb / (1024**2), 2)
                            break
            except OSError:
                pass

        # CPU core count
        cpu_count = os.cpu_count() or 1

        # Default to CPU
        hardware = {
            "vendor": cpu_vendor,
            "chip_model": cpu_model,
            "chip_count": 1,
            "interconnect": "None",  # Required by schema
            "chips_per_node": 1,  # Added for clarity
            "intra_node_interconnect": "None",  # Match example format
            "memory_per_chip_gb": total_memory_gb,  # For CPU, system memory
            "total_memory_gb": total_memory_gb,
        }

        # Try to detect GPU if available
        try:
            import torch

            if torch.cuda.is_available():
                hardware["vendor"] = "NVIDIA"
                hardware["chip_model"] = torch.cuda.get_device_name(0)

                # 支持通过环境变量强制单卡配置
                force_single_chip = (
                    os.getenv("SAGELLM_FORCE_SINGLE_CHIP", "false").lower() == "true"
                )

                if force_single_chip:
                    hardware["chip_count"] = 1
                    hardware["chips_per_node"] = 1
                else:
                    hardware["chip_count"] = torch.cuda.device_count()
                    hardware["chips_per_node"] = torch.cuda.device_count()

                hardware["memory_per_chip_gb"] = round(
                    torch.cuda.get_device_properties(0).total_memory / (1024**3), 2
                )
                hardware["total_memory_gb"] = round(
                    hardware["memory_per_chip_gb"] * hardware["chip_count"], 2
                )
                # Detect interconnect
                if hardware["chip_count"] > 1:
                    # Simple heuristic: assume NVLink for multi-GPU
                    hardware["interconnect"] = "NVLink"
                    hardware["intra_node_interconnect"] = "NVLink"
                else:
                    hardware["interconnect"] = "None"
                    hardware["intra_node_interconnect"] = "None"
        except ImportError:
            pass

        # Try to detect Ascend NPU
        try:
            import torch_npu

            if torch_npu.npu.is_available():
                hardware["vendor"] = "Huawei"
                hardware["chip_model"] = "Ascend 910B"  # Default
                hardware["chip_count"] = torch_npu.npu.device_count()
                hardware["chips_per_node"] = torch_npu.npu.device_count()
                if hardware["chip_count"] > 1:
                    hardware["interconnect"] = "HCCS"
                    hardware["intra_node_interconnect"] = "HCCS"
                else:
                    hardware["interconnect"] = "None"
                    hardware["intra_node_interconnect"] = "None"
        except ImportError:
            pass

        return hardware

    @staticmethod
    def detect_environment() -> dict[str, Any]:
        """Detect environment information.

        Returns:
            Dictionary with environment fields
        """
        env = {
            "os": f"{platform.system()} {platform.release()}",
            "python_version": platform.python_version(),
            "pytorch_version": "",
            "cuda_version": "",
            "cann_version": "",
            "driver_version": "",
        }

        # Detect PyTorch version
        try:
            import torch

            env["pytorch_version"] = torch.__version__
            if torch.cuda.is_available():
                env["cuda_version"] = torch.version.cuda
        except ImportError:
            pass

        # Detect NVIDIA driver
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                env["driver_version"] = result.stdout.strip().split("\n")[0]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return env

    @staticmethod
    def infer_config_type(chip_count: int, has_cluster: bool) -> str:
        """Infer configuration type from chip count and cluster info.

        Args:
            chip_count: Number of chips/GPUs
            has_cluster: Whether cluster configuration exists

        Returns:
            One of: "single_gpu", "multi_gpu", "multi_node"
        """
        if has_cluster:
            return "multi_node"
        elif chip_count > 1:
            return "multi_gpu"
        else:
            return "single_gpu"

    @staticmethod
    def _resolve_version(
        versions: dict[str, Any],
        aliases: tuple[str, ...],
        default: str = "N/A",
    ) -> str:
        """Resolve component version from metadata keys with alias fallback."""
        for key in aliases:
            value = versions.get(key)
            if value:
                return str(value)
        return default

    @staticmethod
    def export_to_leaderboard(
        metrics: AggregatedMetrics,
        config: dict[str, Any],
        workload_name: str,
        output_path: Path,
        custom_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Export metrics to leaderboard format.

        Args:
            metrics: Aggregated metrics from benchmark
            config: Run configuration dict
            workload_name: Name of the workload (e.g., "short_input")
            output_path: Path to save the leaderboard entry JSON
            custom_metadata: Optional custom metadata to include

        Returns:
            The leaderboard entry dictionary
        """
        # Detect hardware and environment
        hardware = LeaderboardExporter.detect_hardware_info()
        environment = LeaderboardExporter.detect_environment()

        # Infer config_type
        config_type = LeaderboardExporter.infer_config_type(
            hardware["chip_count"], has_cluster=False
        )

        # Extract model info from config (优先使用 model_path，去掉路径部分)
        model_path = config.get("model_path", config.get("model", "unknown"))
        # 提取模型名称（处理路径和 HF 格式）
        if "/" in model_path:
            model_name = model_path.split("/")[-1]  # HF: "sshleifer/tiny-gpt2" → "tiny-gpt2"
        else:
            model_name = model_path  # 本地模型："gpt2" → "gpt2"

        model_info = {
            "name": model_name,
            "parameters": "unknown",  # TODO: Extract from model name
            "precision": "FP32",  # Default
            "quantization": "None",
        }

        # Extract workload info (根据 workload_name 映射)
        workload_spec = WORKLOAD_SPECS.get(
            workload_name, {"input_length": 128, "output_length": 128}
        )
        workload_info = {
            "input_length": workload_spec["input_length"],
            "output_length": workload_spec["output_length"],
            "batch_size": 1,
            "concurrent_requests": 1,
            "dataset": config.get("dataset", "default"),
        }

        # Map metrics to leaderboard format
        leaderboard_metrics = {
            "ttft_ms": metrics.avg_ttft_ms,
            "tbt_ms": metrics.avg_tbt_ms,
            "tpot_ms": metrics.avg_tpot_ms,
            "throughput_tps": metrics.avg_throughput_tps,
            "peak_mem_mb": metrics.peak_mem_mb,
            "error_rate": metrics.error_rate,
            "prefix_hit_rate": metrics.avg_prefix_hit_rate,
            "kv_used_tokens": metrics.total_kv_used_tokens,
            "kv_used_bytes": metrics.total_kv_used_bytes,
            "evict_count": metrics.total_evict_count,
            "evict_ms": metrics.total_evict_ms,
            "spec_accept_rate": metrics.avg_spec_accept_rate
            if metrics.avg_spec_accept_rate > 0
            else None,
        }

        # Build leaderboard entry
        config_versions = config.get("versions", {})
        component_versions = {
            "protocol": LeaderboardExporter._resolve_version(
                config_versions, ("sagellm_protocol", "protocol")
            ),
            "backend": LeaderboardExporter._resolve_version(
                config_versions, ("sagellm_backend", "backend")
            ),
            "core": LeaderboardExporter._resolve_version(config_versions, ("sagellm_core", "core")),
            "control_plane": LeaderboardExporter._resolve_version(
                config_versions, ("sagellm_control_plane", "control_plane")
            ),
            "gateway": LeaderboardExporter._resolve_version(
                config_versions, ("sagellm_gateway", "gateway")
            ),
            "kv_cache": LeaderboardExporter._resolve_version(
                config_versions, ("sagellm_kv_cache", "kv_cache")
            ),
            "comm": LeaderboardExporter._resolve_version(config_versions, ("sagellm_comm", "comm")),
            "compression": LeaderboardExporter._resolve_version(
                config_versions, ("sagellm_compression", "compression")
            ),
            "benchmark": LeaderboardExporter._resolve_version(
                config_versions, ("sagellm_benchmark", "benchmark")
            ),
        }

        entry = {
            "entry_id": str(uuid.uuid4()),
            "sagellm_version": LeaderboardExporter._resolve_version(
                config_versions, ("sagellm", "sagellm_benchmark", "benchmark")
            ),
            "config_type": config_type,
            "hardware": hardware,
            "model": model_info,
            "workload": workload_info,
            "metrics": leaderboard_metrics,
            "cluster": None,  # Single-node for now
            "versions": component_versions,
            "environment": environment,
            "kv_cache_config": {
                "enabled": True,
                "eviction_policy": "LRU",
                "budget_tokens": 8192,
                "prefix_cache_enabled": True,
            },
            "metadata": {
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "submitter": "sagellm-benchmark automated run",
                "data_source": "automated-benchmark",
                "reproducible_cmd": f"sagellm-benchmark run --workload {config.get('workload')} --backend {config.get('backend')} --model {config.get('model')}",
                "git_commit": None,
                "release_date": config.get("timestamp", "").split("T")[0]
                if config.get("timestamp")
                else None,
                "changelog_url": "https://github.com/intellistream/sagellm/blob/main/CHANGELOG.md",
                "notes": f"Benchmark run: {workload_name}",
                "verified": False,
            },
        }

        # Merge custom metadata if provided
        if custom_metadata:
            entry["metadata"].update(custom_metadata)

        # Save to file
        with open(output_path, "w") as f:
            json.dump(entry, f, indent=2)

        return entry
