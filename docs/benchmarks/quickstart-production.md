# Production Benchmark System - Quick Start

**Ready to validate Python v2.1.0 improvements with real data!**

---

## 30-Second Quick Test

```bash
cd /Users/masa/Projects/claude-mpm
./docs/benchmarks/scripts/test_production_runner.py
```

**What it does**: Runs one easy Python test through the entire pipeline (task creation → agent invocation → code execution → evaluation)

**Expected time**: 5-15 seconds

**Expected output**:
```
==============================================================================
PRODUCTION BENCHMARK RUNNER - TEST SCRIPT
==============================================================================

Test Selected: Two Sum (python_easy_01)
Difficulty: easy
Category: algorithms
Description: Given an array of integers nums and an integer target, return...

------------------------------------------------------------------------------

Running production execution...
(This will invoke the Python Engineer agent via claude-mpm CLI)

==============================================================================
TEST RESULT
==============================================================================

Status: ✓ PASS
Test ID: python_easy_01
Test Name: Two Sum
Weighted Score: 8.65/10.0
Agent Execution Time: 5.2s

Dimension Scores:
--------------------------------------------------
  correctness         : 9.5/10.0 (weight: 40%, contribution: 3.80)
  idiomaticity        : 8.5/10.0 (weight: 25%, contribution: 2.12)
  performance         : 8.5/10.0 (weight: 20%, contribution: 1.70)
  best_practices      : 7.5/10.0 (weight: 15%, contribution: 1.12)

Test Cases: 3/3 passed

==============================================================================

SUCCESS: Test completed with score 8.65/10.0
```

---

## Common Commands

### Run Specific Test

```bash
./docs/benchmarks/scripts/test_production_runner.py --test-id python_easy_02 --verbose
```

### Run Multiple Tests (Validation)

```bash
./docs/benchmarks/scripts/test_production_runner.py --multiple 5
```

### Full Python Benchmark (All 12 Tests)

```bash
./docs/benchmarks/scripts/production_benchmark_runner.py --agent python_engineer
```

**Time**: 5-8 minutes
**Output**: `docs/benchmarks/results/lightweight/python_engineer_benchmark.json`

### View Results

```bash
# Summary statistics
cat docs/benchmarks/results/lightweight/python_engineer_benchmark.json | \
  jq '.results.python_engineer | {
    passed: .passed_tests,
    total: .total_tests,
    pass_rate: .pass_rate,
    avg_score: .average_score
  }'

# Individual test results
cat docs/benchmarks/results/lightweight/python_engineer_benchmark.json | \
  jq '.results.python_engineer.results[] | {
    name: .test_name,
    passed: .passed,
    score: .weighted_score
  }'
```

---

## Test Options

### Available Test IDs

**Easy Tests** (4):
- `python_easy_01` - Two Sum
- `python_easy_02` - Valid Parentheses
- `python_easy_09` - FizzBuzz
- `python_easy_12` - Single Number

**Medium Tests** (5):
- Various algorithms and data structures

**Hard Tests** (3):
- Advanced problems

To see all available tests:
```bash
cat docs/benchmarks/lightweight/python_mini.json | jq '.tests[] | {id, name, difficulty}'
```

---

## Understanding Results

### Weighted Score Calculation

```
weighted_score = (
  correctness    × 0.40 +    # Test pass rate (most important)
  idiomaticity   × 0.25 +    # Python patterns & conventions
  performance    × 0.20 +    # Execution speed vs expected
  best_practices × 0.15      # Code quality & documentation
)
```

### Dimension Meanings

| Dimension | What It Measures | Good Score |
|-----------|------------------|------------|
| Correctness | Does it work? All tests pass? | 9.0+ |
| Idiomaticity | Uses Python patterns? (list comp, type hints) | 8.0+ |
| Performance | Fast enough? Within expected time? | 8.0+ |
| Best Practices | Well documented? Clean code? | 7.0+ |

### Interpreting Scores

- **9.0-10.0**: Excellent - Production-ready code
- **7.0-8.9**: Good - Minor improvements possible
- **5.0-6.9**: Acceptable - Needs some work
- **Below 5.0**: Needs significant improvement

---

## Troubleshooting

### Problem: "claude-mpm: command not found"

**Solution**: The script uses the full path automatically. If you moved the project, update line ~136 in `production_benchmark_runner.py`:

```python
claude_mpm_path = Path(__file__).parent.parent.parent.parent / "scripts" / "claude-mpm"
```

### Problem: Agent timeout

**Symptom**: Error says "exceeded 120s timeout"

**Solution**: Increase timeout in `production_benchmark_runner.py`:
```python
self.agent_timeout = 300  # 5 minutes instead of 2
```

### Problem: "No solution code found in agent response"

**Possible causes**:
- Agent didn't use code blocks properly
- Agent provided only explanation
- Code extraction regex failed

**Solutions**:
1. Check `execution_details.stderr` in result for agent output
2. Run with `--verbose` to see full output
3. Try a different test to see if it's test-specific

### Problem: Test fails but solution looks correct

**Check**:
1. Test harness generation (look at execution_details)
2. Input/output format matching
3. Data type comparisons (lists vs tuples, etc.)

### Get Help

1. Read full docs: `docs/benchmarks/PRODUCTION_BENCHMARK.md`
2. Check architecture: `docs/benchmarks/ARCHITECTURE_DIAGRAM.md`
3. Review implementation: `/tmp/docs/benchmark_implementation_summary.md`

---

## Next Steps

### Validate MVP

```bash
# 1. Quick smoke test
./docs/benchmarks/scripts/test_production_runner.py

# 2. Test multiple problems
./docs/benchmarks/scripts/test_production_runner.py --multiple 3

# 3. Run full benchmark if above succeed
./docs/benchmarks/scripts/production_benchmark_runner.py --agent python_engineer
```

### Analyze Python v2.1.0 Improvements

Once you have results:

1. **Check pass rate**: How many of 12 tests pass?
2. **Analyze failures**: Which types of problems are challenging?
3. **Review solutions**: Look at `solution` field in results
4. **Compare dimensions**: Where does the agent excel? Where needs work?

### Benchmark Results Path

```
docs/benchmarks/results/lightweight/python_engineer_benchmark.json
```

Contains:
- Overall statistics (pass rate, average score)
- Difficulty breakdown (easy/medium/hard performance)
- Individual test results with full details
- Execution times
- Solution code snippets

---

## File Locations

```
Production System Files:
├── docs/benchmarks/scripts/production_benchmark_runner.py  # Main runner
├── docs/benchmarks/scripts/test_production_runner.py       # Test script
├── docs/benchmarks/PRODUCTION_BENCHMARK.md                 # Full docs
├── docs/benchmarks/ARCHITECTURE_DIAGRAM.md                 # Visual docs
└── docs/benchmarks/QUICK_START.md                          # This file

Test Definitions:
└── docs/benchmarks/lightweight/python_mini.json            # 12 Python tests

Results Output:
└── docs/benchmarks/results/lightweight/                    # All results
    └── python_engineer_benchmark.json                      # Python results

Temporary Files (auto-cleanup):
└── /tmp/claude-mpm-benchmarks/                             # Task files, etc.
```

---

## Tips

1. **Start small**: Test one problem before running full benchmark
2. **Use verbose mode**: Helps understand what's happening
3. **Check results incrementally**: Don't wait for all tests to review results
4. **Monitor execution**: Watch for patterns in successes/failures
5. **Save results**: Results are timestamped, so you can compare runs

---

**Ready?** Run your first test now:

```bash
./docs/benchmarks/scripts/test_production_runner.py
```

🚀 **Good luck validating those Python v2.1.0 improvements!**
