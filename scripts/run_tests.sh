#!/bin/bash
# Run all tests with coverage

set -e

echo "======================================"
echo "  Better-LLM Test Suite"
echo "======================================"
echo ""

# 의존성 설치 확인
echo "📦 Checking test dependencies..."
if ! pip show pytest-cov > /dev/null 2>&1; then
    echo "Installing test dependencies..."
    pip install -r requirements-dev.txt
fi

echo ""
echo "======================================"
echo "  Running Unit Tests"
echo "======================================"
pytest tests/unit -m "unit" --cov=src --cov-report=term-missing -v

echo ""
echo "======================================"
echo "  Running Integration Tests"
echo "======================================"
pytest tests/integration -m "integration" --cov=src --cov-append -v || true

echo ""
echo "======================================"
echo "  Running E2E Tests"
echo "======================================"
pytest tests/e2e -m "e2e" --cov=src --cov-append -v

echo ""
echo "======================================"
echo "  Generating Coverage Report"
echo "======================================"
coverage html
coverage xml

echo ""
echo "✅ All tests completed!"
echo ""
echo "📊 Coverage report generated:"
echo "   - HTML: htmlcov/index.html"
echo "   - XML:  coverage.xml"
echo ""
