"""Tests for workload definitions and selectors."""

from __future__ import annotations

from sagellm_benchmark.workloads import (
    M1_WORKLOADS,
    TPCH_WORKLOADS,
    WorkloadQuery,
    WorkloadType,
    get_workloads_by_selector,
)


def test_tpch_workloads_have_q1_q8_names() -> None:
    """TPCH workload names should be Q1~Q8."""
    names = [workload.name for workload in TPCH_WORKLOADS]
    assert names == [query.value for query in WorkloadQuery]


def test_tpch_workloads_use_query_type() -> None:
    """All TPCH workloads should use QUERY workload type."""
    assert all(workload.workload_type == WorkloadType.QUERY for workload in TPCH_WORKLOADS)


def test_selector_all_returns_all_query_workloads() -> None:
    """Selector 'all' returns all query workloads."""
    selected = get_workloads_by_selector("all")
    assert len(selected) == len(TPCH_WORKLOADS)
    assert [workload.name for workload in selected] == [
        workload.name for workload in TPCH_WORKLOADS
    ]


def test_selector_q1_returns_single_workload() -> None:
    """Selector Q1 should return only Q1 workload."""
    selected = get_workloads_by_selector("Q1")
    assert len(selected) == 1
    assert selected[0].name == "Q1"


def test_selector_legacy_m1_is_compatible() -> None:
    """Legacy selector m1 should still work."""
    selected = get_workloads_by_selector("m1")
    assert selected == M1_WORKLOADS
