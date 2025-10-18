# Production Benchmark System

**Version**: 1.0.0
**Date**: 2025-10-18
**Status**: MVP - Python support only

## Overview

The Production Benchmark System extends the lightweight benchmark framework with real agent execution capabilities. Instead of mock scoring, it actually invokes Claude MPM agents, executes their solutions, and evaluates performance across multiple dimensions.

## Architecture

### Components

1. **ProductionBenchmarkRunner** (`production_benchmark_runner.py`)
   - Extends `LightweightBenchmarkRunner`
   - Manages agent invocation via subprocess
   - Orchestrates test execution pipeline
   - Performs multi-dimensional evaluation

2. **Task File Generation**
   - Creates formatted markdown files for each test
   - Includes description, signature, test cases, constraints, hints
   - Agent-specific formatting (language syntax highlighting)

3. **Agent Invocation**
   - Uses `claude-mpm run` CLI via subprocess
   - Non-interactive mode with task file input
   - Timeout enforcement (120s default)
   - Output capture for solution extraction

4. **Code Extraction**
   - Regex-based code block extraction
   - Language-specific patterns
   - Fallback to generic code blocks
   - Longest match selection

5. **Solution Execution**
   - Isolated subprocess execution
   - Language-specific test harnesses
   - JSON-based result capture
   - Timeout enforcement (30s default)

6. **Multi-Dimensional Evaluation**
   - **Correctness (40%)**: Test pass rate, syntax validity
   - **Idiomaticity (25%)**: Language-specific patterns and conventions
   - **Performance (20%)**: Execution time vs. expected benchmarks
   - **Best Practices (15%)**: Documentation, security, code quality

### Execution Flow

```
Test Definition (JSON)
    ↓
Task File Creation (.md)
    ↓
Agent Invocation (subprocess: claude-mpm run)
    ↓
Response Capture (stdout/stderr)
    ↓
Code Extraction (regex)
    ↓
Solution Execution (subprocess: python)
    ↓
Test Results (JSON)
    ↓
Multi-Dimensional Evaluation
    ↓
Weighted Score Calculation
    ↓
Result Dictionary
```

## Usage

### Quick Start

Test a single Python problem:

```bash
cd /Users/masa/Projects/claude-mpm
./docs/benchmarks/scripts/test_production_runner.py
```

This will run the first easy Python test and display detailed results.

### Test Specific Problem

```bash
./docs/benchmarks/scripts/test_production_runner.py --test-id python_easy_01 --verbose
```

### Run Multiple Tests

```bash
./docs/benchmarks/scripts/test_production_runner.py --multiple 3
```

### Run Full Agent Benchmark

```bash
# Python Engineer (12 tests)
./docs/benchmarks/scripts/production_benchmark_runner.py --agent python_engineer

# All agents (84 tests) - takes ~15-20 minutes
./docs/benchmarks/scripts/production_benchmark_runner.py
```

### Integrate with Existing Runner

```bash
# Use existing runner with production mode
cd docs/benchmarks/scripts
python run_lightweight_benchmark.py --agent python_engineer --production
```

## Configuration

### Timeouts

Adjust in `ProductionBenchmarkRunner.__init__()`:

```python
self.agent_timeout = 120      # Agent invocation timeout (seconds)
self.execution_timeout = 30   # Solution execution timeout (seconds)
```

### Dimension Weights

Modify in `LightweightBenchmarkRunner.DIMENSION_WEIGHTS`:

```python
DIMENSION_WEIGHTS = {
    "correctness": 0.40,      # 40% - Most important
    "idiomaticity": 0.25,     # 25% - Language-specific quality
    "performance": 0.20,      # 20% - Execution efficiency
    "best_practices": 0.15    # 15% - Code quality & security
}
```

## Evaluation Details

### Correctness (0-10 scale)

- **Full Pass**: 9.5 points
- **Partial Pass**: Proportional to test pass rate (max 4.0)
- **Complete Fail**: 0.0 points

**Evidence**:
- Test execution results (primary)
- JSON output from test harness
- Individual test case pass/fail status

### Idiomaticity (0-10 scale)

**Python Patterns** (MVP):
- Base score: 7.0
- List comprehensions: +1.0
- Dict comprehensions: +0.5
- Context managers (with): +0.5
- Type hints: +0.5
- enumerate usage: +0.5

**Future**: Language-specific linters (pylint, eslint, clippy, etc.)

### Performance (0-10 scale)

**Expected Times by Difficulty**:
- Easy: 100ms
- Medium: 500ms
- Hard: 2s

**Scoring**:
- ≤ 50% expected: 9.5 (Excellent)
- ≤ 100% expected: 8.5 (Good)
- ≤ 200% expected: 6.5 (Acceptable)
- ≤ 500% expected: 4.0 (Poor)
- > 500% expected: 2.0 (Very poor)

### Best Practices (0-10 scale)

**Checks** (MVP):
- Base score: 7.0
- Comments present: +1.0
- Docstrings (Python): +1.0
- Excessive single-char vars: -1.0
- Magic numbers in comparisons: -0.5

**Future**: Security scanning, complexity analysis, deeper static analysis

## Output Format

### Result Dictionary

```json
{
  "test_id": "python_easy_01",
  "test_name": "Two Sum",
  "difficulty": "easy",
  "category": "algorithms",
  "passed": true,
  "dimensions": {
    "correctness": 9.5,
    "idiomaticity": 8.5,
    "performance": 8.5,
    "best_practices": 7.5
  },
  "weighted_score": 8.65,
  "execution_time": 5.2,
  "solution_length": 156,
  "solution": "def two_sum(nums: List[int], target: int) -> List[int]:\n    seen = {}\n    for i, num in enumerate(nums):\n        complement = target - num\n        if complement in seen:\n            return [seen[complement], i]\n        seen[num] = i",
  "execution_details": {
    "test_results": [
      {
        "test_case": 0,
        "passed": true,
        "input": "([2,7,11,15], 9)",
        "expected": "[0,1]",
        "actual": "[0, 1]",
        "error": null
      }
    ],
    "stderr": ""
  }
}
```

## Language Support

### Currently Supported

- **Python** ✅ (Full support)

### Planned

- **TypeScript** (Phase 2)
- **JavaScript/Node.js** (Phase 2)
- **Go** (Phase 3)
- **Rust** (Phase 3)
- **PHP** (Phase 4)
- **Ruby** (Phase 4)

## Security

### Protections

1. **Subprocess Isolation**: Each execution in separate process
2. **Timeouts**: Automatic termination of long-running operations
3. **Temporary Files**: Automatic cleanup after execution
4. **Error Handling**: Graceful degradation on failures

### Future Enhancements

1. **Resource Limits**: CPU, memory, disk constraints
2. **Input Validation**: Block dangerous patterns before execution
3. **Sandboxing**: Docker containers or VMs for execution
4. **Network Isolation**: Prevent network access during execution

## Troubleshooting

### "claude-mpm: command not found"

**Solution**: Ensure claude-mpm is in PATH or use full path:

```python
# In production_benchmark_runner.py, line ~136
claude_mpm_path = Path(__file__).parent.parent.parent.parent / "scripts" / "claude-mpm"
```

### "No solution code found in agent response"

**Causes**:
- Agent didn't use code blocks
- Response format changed
- Agent provided explanation only

**Solutions**:
- Check agent output in stderr
- Adjust task file to emphasize code-only output
- Improve code extraction regex patterns

### Agent timeout

**Causes**:
- Complex problem taking too long
- Agent stuck in thought loop
- Network/API issues

**Solutions**:
- Increase `agent_timeout` value
- Check agent logs for errors
- Retry with simpler test

### Execution timeout

**Causes**:
- Inefficient solution (infinite loop, etc.)
- Test harness issue
- Heavy computation

**Solutions**:
- Increase `execution_timeout` value
- Review solution code for issues
- Check test harness generation

### Test harness parsing errors

**Causes**:
- Complex input/output formats
- Special characters in test data
- Eval limitations

**Solutions**:
- Use `ast.literal_eval()` instead of `eval()`
- Add custom parser for complex types
- Improve test data sanitization

## Performance

### Expected Times

- **Single test**: 2-10 seconds (depending on agent response time)
- **12-test suite**: 3-8 minutes
- **84-test full suite**: 20-50 minutes

### Optimization Tips

1. **Parallel Execution**: Run multiple tests simultaneously (careful with resources)
2. **Caching**: Cache agent responses for retry/debugging
3. **Incremental Testing**: Resume from last completed test
4. **Resource Pooling**: Reuse subprocess environments where safe

## Development

### Adding Language Support

1. **Create executor method**:
   ```python
   def execute_typescript_solution(self, solution: str, test: Dict) -> Dict[str, Any]:
       # Language-specific test harness
       # Subprocess execution
       # Result parsing
   ```

2. **Update language map**:
   ```python
   self.language_map["typescript_engineer"] = "typescript"
   ```

3. **Add to run_single_test**:
   ```python
   elif language == "typescript":
       execution_result = self.execute_typescript_solution(solution, test)
   ```

4. **Implement evaluators**:
   - Language-specific idiomaticity checks
   - Linter integration (eslint, etc.)
   - Pattern matching

### Adding Evaluation Dimensions

To add a new dimension (e.g., "security"):

1. **Add weight**:
   ```python
   DIMENSION_WEIGHTS = {
       # ... existing
       "security": 0.10
   }
   ```

2. **Implement evaluator**:
   ```python
   def evaluate_security(self, solution: str, language: str) -> float:
       # Security checks
       return score
   ```

3. **Add to run_single_test**:
   ```python
   dimensions['security'] = self.evaluate_security(solution, language)
   ```

## Testing

### Unit Tests

```bash
# Test individual components
python -c "
from production_benchmark_runner import ProductionBenchmarkRunner
runner = ProductionBenchmarkRunner(Path('.'))
# Test methods...
"
```

### Integration Tests

```bash
# Test full pipeline
./docs/benchmarks/scripts/test_production_runner.py --test-id python_easy_01
```

### Validation

```bash
# Run multiple tests for consistency
./docs/benchmarks/scripts/test_production_runner.py --multiple 5
```

## Future Enhancements

### Phase 2: TypeScript Support
- TypeScript/JavaScript executor
- Node.js test harness
- ESLint integration
- Jest/Mocha test framework support

### Phase 3: Enhanced Evaluation
- AI-based code review (Claude evaluation)
- AST-based complexity analysis
- Security scanning tools
- Code similarity detection

### Phase 4: Distributed Execution
- Parallel test execution
- Cloud-based execution (AWS Lambda, GCP Functions)
- Result aggregation and reporting
- Real-time progress monitoring

### Phase 5: Advanced Analytics
- Trend analysis over time
- Agent comparison reports
- Performance regression detection
- Interactive dashboard

## References

- Architecture Analysis: `/tmp/docs/benchmark_production_architecture_analysis.md`
- Implementation Guide: `/tmp/docs/benchmark_implementation_quickstart.md`
- Lightweight Tests: `docs/benchmarks/lightweight/*.json`
- Parent Runner: `docs/benchmarks/scripts/run_lightweight_benchmark.py`

## Support

For issues or questions:
1. Check this documentation
2. Review architecture analysis documents
3. Examine test execution logs
4. File issue with reproduction steps

---

**Last Updated**: 2025-10-18
**Maintainer**: Claude MPM Development Team
**Version**: 1.0.0 (MVP - Python only)
