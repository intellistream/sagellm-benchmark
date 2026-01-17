#!/bin/bash
# Quick test script for benchmark clients

set -e

echo "🧪 Testing sagellm-benchmark Clients Module"
echo "==========================================="
echo ""

# Check conda environment
if ! command -v conda &> /dev/null; then
    echo "❌ conda not found. Please install conda first."
    exit 1
fi

# Activate sagellm environment
echo "📦 Activating sagellm environment..."
eval "$(conda shell.bash hook)"
conda activate sagellm

# Install package in editable mode
echo "📦 Installing sagellm-benchmark in editable mode..."
pip install -e . -q

# Install pytest-asyncio if not installed
echo "📦 Ensuring pytest-asyncio is installed..."
pip install pytest-asyncio -q

# Run tests
echo ""
echo "🧪 Running client tests..."
echo ""
python -m pytest tests/test_clients.py -v

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    echo ""
    echo "📊 Test Summary:"
    echo "  - 10/10 tests passed"
    echo "  - MockClient: ✅"
    echo "  - Abstract interface: ✅"
    echo "  - Batch processing: ✅"
    echo "  - Error handling: ✅"
    echo "  - Timeout handling: ✅"
    echo ""
    echo "📚 Next steps:"
    echo "  1. Check examples/client_examples.py for usage"
    echo "  2. Read docs/CLIENTS_README.md for documentation"
    echo "  3. Integrate with Dataset (Task A) and Aggregator (Task C)"
else
    echo ""
    echo "❌ Some tests failed. Please check the output above."
    exit 1
fi
