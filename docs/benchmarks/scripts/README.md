# Benchmark Scripts

This directory contains scripts for running SWE benchmarks on Claude MPM agents.

## Quick Start

### Test Production System (Single Test)

```bash
./test_production_runner.py
```

This runs a single Python test with real agent execution and displays detailed results.

### Run Full Python Benchmark

```bash
./production_benchmark_runner.py --agent python_engineer
```

This runs all 12 Python tests and saves results to `docs/benchmarks/results/lightweight/`.

## Scripts

### `run_lightweight_benchmark.py`

Original benchmark runner with mock execution.

**Usage**:
```bash
# Mock mode (default)
python run_lightweight_benchmark.py

# Production mode (delegates to production_benchmark_runner)
python run_lightweight_benchmark.py --production --agent python_engineer
```

### `production_benchmark_runner.py`

Production benchmark runner with real agent execution.

**Features**:
- Real agent invocation via claude-mpm CLI
- Code extraction from agent responses
- Safe solution execution in subprocesses
- Multi-dimensional evaluation

**Usage**:
```bash
# Single agent (12 tests)
./production_benchmark_runner.py --agent python_engineer

# All agents (84 tests) - ~20-50 minutes
./production_benchmark_runner.py

# Mock mode (for testing)
./production_benchmark_runner.py --agent python_engineer --mock
```

### `test_production_runner.py`

Test script for validating production benchmark system.

**Usage**:
```bash
# Quick test (first easy problem)
./test_production_runner.py

# Specific test
./test_production_runner.py --test-id python_easy_01

# Verbose output (includes solution code)
./test_production_runner.py --verbose

# Multiple tests for validation
./test_production_runner.py --multiple 3
```

### `generate_benchmark_display.py`

Generates visual leaderboard from benchmark results.

**Usage**:
```bash
python generate_benchmark_display.py
```

### `score_lightweight_results.py`

Scores and analyzes benchmark results.

**Usage**:
```bash
python score_lightweight_results.py
```

### `select_lightweight_tests.py`

Utility for selecting test subsets from full benchmark suite.

**Usage**:
```bash
python select_lightweight_tests.py
```

## Language Support

| Language | Status | Script Support |
|----------|--------|----------------|
| Python | ✅ Full | production_benchmark_runner.py |
| TypeScript | 🚧 Planned | Coming in Phase 2 |
| JavaScript | 🚧 Planned | Coming in Phase 2 |
| Go | 🚧 Planned | Coming in Phase 3 |
| Rust | 🚧 Planned | Coming in Phase 3 |
| PHP | 🚧 Planned | Coming in Phase 4 |
| Ruby | 🚧 Planned | Coming in Phase 4 |

## Documentation

See [PRODUCTION_BENCHMARK.md](../PRODUCTION_BENCHMARK.md) for comprehensive documentation:
- Architecture details
- Evaluation methodology
- Configuration options
- Troubleshooting guide
- Development guidelines

## Common Tasks

### Validate MVP Implementation

```bash
# Test single problem
./test_production_runner.py --test-id python_easy_01 --verbose

# Test multiple problems for consistency
./test_production_runner.py --multiple 5
```

### Run Production Benchmark

```bash
# Python only (12 tests, ~5 minutes)
./production_benchmark_runner.py --agent python_engineer

# View results
cat ../results/lightweight/python_engineer_benchmark.json | jq '.results.python_engineer | {passed_tests, total_tests, average_score}'
```

### Compare Mock vs Production

```bash
# Mock mode
python run_lightweight_benchmark.py --agent python_engineer > mock_results.txt

# Production mode
./production_benchmark_runner.py --agent python_engineer > prod_results.txt

# Compare
diff mock_results.txt prod_results.txt
```

## Troubleshooting

### Script not executable

```bash
chmod +x *.py
```

### Import errors

Make sure you're running from the project root or the scripts directory:

```bash
cd /Users/masa/Projects/claude-mpm/docs/benchmarks/scripts
./test_production_runner.py
```

### claude-mpm not found

The production runner uses the full path to claude-mpm. If you moved the project, update line ~136 in `production_benchmark_runner.py`:

```python
claude_mpm_path = Path(__file__).parent.parent.parent.parent / "scripts" / "claude-mpm"
```

### Agent timeout

Increase timeout in `production_benchmark_runner.py`:

```python
self.agent_timeout = 300  # 5 minutes instead of 2
```

## Development

### Adding Language Support

See [PRODUCTION_BENCHMARK.md](../PRODUCTION_BENCHMARK.md#adding-language-support) for detailed instructions.

### Running Tests

```bash
# Unit tests (if implemented)
pytest test_*.py

# Integration test
./test_production_runner.py --multiple 3
```

## Results

Benchmark results are saved to:

```
docs/benchmarks/results/lightweight/
├── benchmark_results.json          # All agents
├── python_engineer_benchmark.json  # Python only
├── typescript_engineer_benchmark.json
└── ...
```

## Support

- Documentation: [PRODUCTION_BENCHMARK.md](../PRODUCTION_BENCHMARK.md)
- Architecture: `/tmp/docs/benchmark_production_architecture_analysis.md`
- Issues: Check logs and error messages

---

**Last Updated**: 2025-10-18
