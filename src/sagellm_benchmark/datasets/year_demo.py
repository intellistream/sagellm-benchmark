"""Year Demo Workload 生成器。

提供 Year1/Year2/Year3 预置 Workload 规格，用于 Demo Contract 验证。
包含 SHORT、LONG、STRESS 三种标准场景。
"""

from __future__ import annotations

from sagellm_benchmark.types import WorkloadSpec, WorkloadType

# ============================================================================
# Year 1 Demo Workloads
# 验证基础功能：短输入、长输入、压力测试
# ============================================================================

YEAR1_SHORT = WorkloadSpec(
    name="year1_short",
    workload_type=WorkloadType.SHORT,
    prompt_len=128,  # 128 tokens prompt
    output_len=128,  # 128 tokens output
    num_requests=5,
    concurrent=False,
)

YEAR1_LONG = WorkloadSpec(
    name="year1_long",
    workload_type=WorkloadType.LONG,
    prompt_len=2048,  # 2048 tokens prompt
    output_len=512,  # 512 tokens output
    num_requests=3,
    concurrent=False,
)

YEAR1_STRESS = WorkloadSpec(
    name="year1_stress",
    workload_type=WorkloadType.STRESS,
    prompt_len=256,
    output_len=256,
    num_requests=10,
    concurrent=True,
    kv_budget_tokens=4096,  # 触发 KV 驱逐
)

YEAR1_WORKLOADS: list[WorkloadSpec] = [
    YEAR1_SHORT,
    YEAR1_LONG,
    YEAR1_STRESS,
]


# ============================================================================
# Year 2 Demo Workloads
# 验证进阶功能：更长上下文、更高并发、前缀缓存命中
# ============================================================================

YEAR2_SHORT = WorkloadSpec(
    name="year2_short",
    workload_type=WorkloadType.SHORT,
    prompt_len=256,
    output_len=256,
    num_requests=10,
    concurrent=False,
)

YEAR2_LONG = WorkloadSpec(
    name="year2_long",
    workload_type=WorkloadType.LONG,
    prompt_len=8192,  # 8K context
    output_len=1024,
    num_requests=5,
    concurrent=False,
)

YEAR2_STRESS = WorkloadSpec(
    name="year2_stress",
    workload_type=WorkloadType.STRESS,
    prompt_len=512,
    output_len=512,
    num_requests=50,
    concurrent=True,
    kv_budget_tokens=16384,
)

YEAR2_WORKLOADS: list[WorkloadSpec] = [
    YEAR2_SHORT,
    YEAR2_LONG,
    YEAR2_STRESS,
]


# ============================================================================
# Year 3 Demo Workloads
# 验证极限性能：超长上下文、极高并发、推测解码
# ============================================================================

YEAR3_SHORT = WorkloadSpec(
    name="year3_short",
    workload_type=WorkloadType.SHORT,
    prompt_len=512,
    output_len=512,
    num_requests=20,
    concurrent=False,
)

YEAR3_LONG = WorkloadSpec(
    name="year3_long",
    workload_type=WorkloadType.LONG,
    prompt_len=32768,  # 32K context
    output_len=2048,
    num_requests=10,
    concurrent=False,
)

YEAR3_STRESS = WorkloadSpec(
    name="year3_stress",
    workload_type=WorkloadType.STRESS,
    prompt_len=1024,
    output_len=1024,
    num_requests=100,
    concurrent=True,
    kv_budget_tokens=65536,
)

YEAR3_WORKLOADS: list[WorkloadSpec] = [
    YEAR3_SHORT,
    YEAR3_LONG,
    YEAR3_STRESS,
]


# ============================================================================
# 辅助函数
# ============================================================================


def get_year1_workloads() -> list[WorkloadSpec]:
    """获取 Year 1 Demo 所需的所有 Workload 规格。

    Returns:
        包含 SHORT、LONG、STRESS 三个 WorkloadSpec 的列表。

    Example:
        >>> workloads = get_year1_workloads()
        >>> len(workloads)
        3
        >>> workloads[0].name
        'year1_short'
    """
    return YEAR1_WORKLOADS.copy()


def get_year2_workloads() -> list[WorkloadSpec]:
    """获取 Year 2 Demo 所需的所有 Workload 规格。

    Returns:
        包含 SHORT、LONG、STRESS 三个 WorkloadSpec 的列表。
    """
    return YEAR2_WORKLOADS.copy()


def get_year3_workloads() -> list[WorkloadSpec]:
    """获取 Year 3 Demo 所需的所有 Workload 规格。

    Returns:
        包含 SHORT、LONG、STRESS 三个 WorkloadSpec 的列表。
    """
    return YEAR3_WORKLOADS.copy()


def get_workloads_by_year(year: int) -> list[WorkloadSpec]:
    """根据年份获取 Demo Workload 规格。

    Args:
        year: Demo 年份（1、2 或 3）。

    Returns:
        对应年份的 WorkloadSpec 列表。

    Raises:
        ValueError: 当 year 不是 1、2、3 时。

    Example:
        >>> workloads = get_workloads_by_year(1)
        >>> len(workloads)
        3
    """
    if year == 1:
        return get_year1_workloads()
    elif year == 2:
        return get_year2_workloads()
    elif year == 3:
        return get_year3_workloads()
    else:
        raise ValueError(f"Invalid year: {year}. Must be 1, 2, or 3.")


def get_workload_by_type(
    year: int,
    workload_type: WorkloadType,
) -> WorkloadSpec:
    """根据年份和类型获取单个 Workload 规格。

    Args:
        year: Demo 年份（1、2 或 3）。
        workload_type: Workload 类型（SHORT、LONG、STRESS）。

    Returns:
        匹配的 WorkloadSpec。

    Raises:
        ValueError: 当找不到匹配的 Workload 时。

    Example:
        >>> spec = get_workload_by_type(1, WorkloadType.SHORT)
        >>> spec.name
        'year1_short'
    """
    workloads = get_workloads_by_year(year)
    for spec in workloads:
        if spec.workload_type == workload_type:
            return spec
    raise ValueError(f"No workload found for year={year}, type={workload_type}")


def create_custom_workload(
    name: str,
    workload_type: WorkloadType,
    prompt_len: int,
    output_len: int,
    num_requests: int,
    *,
    concurrent: bool = False,
    kv_budget_tokens: int | None = None,
) -> WorkloadSpec:
    """创建自定义 Workload 规格。

    提供便捷的工厂函数，避免直接实例化 WorkloadSpec。

    Args:
        name: Workload 名称。
        workload_type: Workload 类型。
        prompt_len: 期望的 prompt 长度（tokens）。
        output_len: 期望的输出长度（tokens）。
        num_requests: 请求数量。
        concurrent: 是否并发执行。
        kv_budget_tokens: KV 缓存预算。

    Returns:
        配置好的 WorkloadSpec。

    Raises:
        ValueError: 当参数无效时。

    Example:
        >>> spec = create_custom_workload(
        ...     name="my_workload",
        ...     workload_type=WorkloadType.SHORT,
        ...     prompt_len=100,
        ...     output_len=50,
        ...     num_requests=10,
        ... )
    """
    # Fail-fast: 参数校验
    if prompt_len <= 0:
        raise ValueError(f"prompt_len must be positive, got {prompt_len}")
    if output_len <= 0:
        raise ValueError(f"output_len must be positive, got {output_len}")
    if num_requests <= 0:
        raise ValueError(f"num_requests must be positive, got {num_requests}")
    if kv_budget_tokens is not None and kv_budget_tokens <= 0:
        raise ValueError(f"kv_budget_tokens must be positive, got {kv_budget_tokens}")

    return WorkloadSpec(
        name=name,
        workload_type=workload_type,
        prompt_len=prompt_len,
        output_len=output_len,
        num_requests=num_requests,
        concurrent=concurrent,
        kv_budget_tokens=kv_budget_tokens,
    )
