#!/bin/bash
#
# Test entrypoint script for LPCPU container testing
#

set -e

echo "=========================================="
echo "LPCPU Container Test Runner"
echo "=========================================="
echo "Distribution: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "Python version: $(python3 --version)"
echo "=========================================="
echo ""

# Change to the lpcpu directory
cd /lpcpu

# Run pytest with verbose output
echo "Running pytest test suite..."
echo "=========================================="

pytest tests/ -v --tb=short --color=yes

TEST_EXIT_CODE=$?

echo ""
echo "=========================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✓ All tests passed!"
    echo "=========================================="
    exit 0
else
    echo "✗ Some tests failed (exit code: $TEST_EXIT_CODE)"
    echo "=========================================="
    exit $TEST_EXIT_CODE
fi

# Made with Bob
