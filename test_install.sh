#!/bin/bash
# Test script for sagellm-benchmark

set -e

echo "======================================"
echo "  Testing sageLLM Benchmark Package"
echo "======================================"
echo ""

cd /home/shuhao/sagellm-benchmark

echo "[1/5] Installing package in development mode..."
pip install -e . -q

echo "[2/5] Testing CLI help..."
sagellm-benchmark --help

echo ""
echo "[3/5] Testing run command help..."
sagellm-benchmark run --help

echo ""
echo "[4/5] Testing report command help..."
sagellm-benchmark report --help

echo ""
echo "[5/5] Running unit tests..."
pytest tests/test_cli.py -v

echo ""
echo "✓ All tests passed!"
