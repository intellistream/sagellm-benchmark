"""Tests for CLI functionality."""

from __future__ import annotations

from click.testing import CliRunner

from sagellm_benchmark.cli import main


def test_cli_version():
    """Test CLI version command."""
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_help():
    """Test CLI help command."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "sageLLM Benchmark Suite" in result.output
    assert "run" in result.output
    assert "report" in result.output


def test_run_help():
    """Test run subcommand help."""
    runner = CliRunner()
    result = runner.invoke(main, ["run", "--help"])
    assert result.exit_code == 0
    assert "--workload" in result.output
    assert "--backend" in result.output
    assert "--model" in result.output
    assert "--output" in result.output


def test_report_help():
    """Test report subcommand help."""
    runner = CliRunner()
    result = runner.invoke(main, ["report", "--help"])
    assert result.exit_code == 0
    assert "--input" in result.output
    assert "--format" in result.output
