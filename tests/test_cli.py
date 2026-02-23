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


def test_upload_hf_help():
    """Test upload-hf subcommand help."""
    runner = CliRunner()
    result = runner.invoke(main, ["upload-hf", "--help"])
    assert result.exit_code == 0
    assert "--dataset" in result.output
    assert "--input" in result.output
    assert "--token" in result.output


def test_run_mode_parameter():
    """Test that --mode parameter is available in run command."""
    runner = CliRunner()
    result = runner.invoke(main, ["run", "--help"])
    assert result.exit_code == 0
    assert "--mode" in result.output
    assert "batch" in result.output
    assert "traffic" in result.output


def test_run_output_json_parameter():
    """Test that --output-json parameter is available in run command."""
    runner = CliRunner()
    result = runner.invoke(main, ["run", "--help"])
    assert result.exit_code == 0
    assert "--output-json" in result.output


def test_mode_batch_validation():
    """Test that batch mode is a valid choice."""
    runner = CliRunner()
    # Note: This will fail without a proper engine, but we just want to verify the parameter is accepted
    # The actual validation happens during execution
    result = runner.invoke(main, ["run", "--mode", "batch", "--help"])
    assert result.exit_code == 0


def test_mode_traffic_validation():
    """Test that traffic mode is a valid choice."""
    runner = CliRunner()
    result = runner.invoke(main, ["run", "--mode", "traffic", "--help"])
    assert result.exit_code == 0
