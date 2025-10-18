# Production Benchmark System - Architecture Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Production Benchmark System                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  LightweightBenchmarkRunner (Parent Class)             │    │
│  │  - Mock execution                                       │    │
│  │  - Test loading                                         │    │
│  │  - Result aggregation                                   │    │
│  │  - Dimension weights                                    │    │
│  └────────────────┬───────────────────────────────────────┘    │
│                   │                                              │
│                   │ inherits                                     │
│                   ▼                                              │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  ProductionBenchmarkRunner (Extended)                  │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │  1. Task File Creation                           │  │    │
│  │  │     - Format test as markdown                    │  │    │
│  │  │     - Include examples, hints, constraints       │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │  2. Agent Invocation                             │  │    │
│  │  │     - Subprocess: claude-mpm run                 │  │    │
│  │  │     - Non-interactive mode                       │  │    │
│  │  │     - Timeout enforcement (120s)                 │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │  3. Code Extraction                              │  │    │
│  │  │     - Regex pattern matching                     │  │    │
│  │  │     - Language-specific code blocks              │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │  4. Solution Execution                           │  │    │
│  │  │     - Test harness generation                    │  │    │
│  │  │     - Subprocess execution                       │  │    │
│  │  │     - JSON result capture                        │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │  5. Multi-Dimensional Evaluation                 │  │    │
│  │  │     - Correctness (40%)                          │  │    │
│  │  │     - Idiomaticity (25%)                         │  │    │
│  │  │     - Performance (20%)                          │  │    │
│  │  │     - Best Practices (15%)                       │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Execution Flow

```
┌──────────────────┐
│  User Request    │
│  (Test ID)       │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Load Test Definition                   │
│  - python_mini.json                     │
│  - Test cases, constraints, hints       │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Create Task File                       │
│  - Format as markdown                   │
│  - /tmp/claude-mpm-benchmarks/task_*.md │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Invoke Agent (Subprocess)              │
│                                         │
│  Command:                               │
│    claude-mpm run                       │
│      --non-interactive                  │
│      --input task_file.md               │
│      --no-hooks                         │
│      --launch-method subprocess         │
│                                         │
│  Timeout: 120s                          │
│  Capture: stdout, stderr                │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Extract Solution Code                  │
│  - Regex: ```python\n(.*?)```          │
│  - Fallback: ```\n(.*?)```             │
│  - Select longest match                 │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Generate Test Harness                  │
│                                         │
│  Python Script:                         │
│    1. Import solution code              │
│    2. Parse test cases from JSON        │
│    3. Execute function with inputs      │
│    4. Compare with expected outputs     │
│    5. Output results as JSON            │
│                                         │
│  Timeout: 30s                           │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Execute Solution (Subprocess)          │
│  - Run test harness script              │
│  - Capture JSON results                 │
│  - Measure execution time               │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Parse Test Results                     │
│  - Individual test case outcomes        │
│  - Pass/fail status                     │
│  - Error messages                       │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Multi-Dimensional Evaluation           │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ Correctness (40%)               │   │
│  │ - Test pass rate                │   │
│  │ - 9.5 for full pass             │   │
│  │ - Proportional for partial      │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ Idiomaticity (25%)              │   │
│  │ - List comprehensions           │   │
│  │ - Type hints                    │   │
│  │ - Idiomatic patterns            │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ Performance (20%)               │   │
│  │ - Execution time vs expected    │   │
│  │ - Difficulty-adjusted           │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ Best Practices (15%)            │   │
│  │ - Documentation                 │   │
│  │ - Code quality                  │   │
│  │ - Security patterns             │   │
│  └─────────────────────────────────┘   │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Calculate Weighted Score               │
│                                         │
│  weighted_score = (                     │
│    correctness * 0.40 +                 │
│    idiomaticity * 0.25 +                │
│    performance * 0.20 +                 │
│    best_practices * 0.15                │
│  )                                      │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Return Result Dictionary               │
│  {                                      │
│    "test_id": "python_easy_01",         │
│    "passed": true,                      │
│    "dimensions": {...},                 │
│    "weighted_score": 8.65,              │
│    "execution_time": 5.2,               │
│    "solution": "...",                   │
│    "execution_details": {...}           │
│  }                                      │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Save Results                           │
│  - JSON file in results/lightweight/    │
│  - Aggregate statistics                 │
│  - Dimension breakdown                  │
└─────────────────────────────────────────┘
```

## Component Interactions

```
┌─────────────────────────────────────────────────────────────────┐
│                         Test Infrastructure                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Test Definitions (JSON)                                        │
│  ├── python_mini.json (12 tests)                               │
│  ├── typescript_mini.json (12 tests)                           │
│  └── ... (7 languages × 12 tests = 84 total)                   │
│                                                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Production Runner                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Task File Generator                                            │
│  ├── Markdown formatting                                        │
│  ├── Language-specific syntax                                   │
│  └── Temporary file management                                  │
│                                                                  │
│  Agent Invoker                                                  │
│  ├── Subprocess management                                      │
│  ├── Timeout enforcement                                        │
│  └── Output capture                                             │
│                                                                  │
│  Code Extractor                                                 │
│  ├── Regex patterns                                             │
│  ├── Language detection                                         │
│  └── Validation                                                 │
│                                                                  │
│  Solution Executor                                              │
│  ├── Test harness generation                                    │
│  ├── Subprocess execution                                       │
│  └── Result parsing                                             │
│                                                                  │
│  Evaluator Suite                                                │
│  ├── Correctness evaluator                                      │
│  ├── Idiomaticity evaluator                                     │
│  ├── Performance evaluator                                      │
│  └── Best practices evaluator                                   │
│                                                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      External Systems                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Claude MPM CLI                                                 │
│  ├── scripts/claude-mpm                                         │
│  ├── Agent selection                                            │
│  └── Task execution                                             │
│                                                                  │
│  Python Interpreter                                             │
│  ├── Solution execution                                         │
│  ├── Test harness running                                       │
│  └── Result generation                                          │
│                                                                  │
│  Filesystem                                                     │
│  ├── /tmp/claude-mpm-benchmarks/ (temp files)                  │
│  ├── docs/benchmarks/results/ (results)                        │
│  └── Automatic cleanup                                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Security Layers                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Layer 1: Process Isolation                                     │
│  ├── Agent runs in separate subprocess                          │
│  ├── Solution executes in separate subprocess                   │
│  └── Failures don't affect benchmark runner                     │
│                                                                  │
│  Layer 2: Timeout Enforcement                                   │
│  ├── Agent invocation: 120s max                                 │
│  ├── Solution execution: 30s max                                │
│  └── Automatic termination on timeout                           │
│                                                                  │
│  Layer 3: Temporary File Management                             │
│  ├── All temp files in /tmp/claude-mpm-benchmarks/             │
│  ├── Automatic cleanup after execution                          │
│  └── No persistence of sensitive data                           │
│                                                                  │
│  Layer 4: Error Handling                                        │
│  ├── Graceful degradation on failures                           │
│  ├── Error capture and logging                                  │
│  └── Continue with remaining tests                              │
│                                                                  │
│  Future Enhancements:                                           │
│  ├── Input validation (dangerous patterns)                      │
│  ├── Resource limits (CPU, memory)                              │
│  ├── Docker containerization                                    │
│  └── Network isolation                                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
Test Definition (JSON)
    ↓
Task File (Markdown)
    ↓
Agent Invocation (claude-mpm CLI)
    ↓
Agent Response (Markdown with code blocks)
    ↓
Extracted Code (Python)
    ↓
Test Harness (Python script with embedded solution)
    ↓
Execution Results (JSON)
    ↓
Evaluation Scores (Dict with 4 dimensions)
    ↓
Weighted Score (0-10)
    ↓
Result Object (Complete test result)
    ↓
Benchmark Results (JSON file)
```

## File Organization

```
docs/benchmarks/
├── lightweight/                    # Test definitions
│   ├── python_mini.json
│   ├── typescript_mini.json
│   └── ...
│
├── scripts/                        # Execution scripts
│   ├── production_benchmark_runner.py   # Main production runner
│   ├── run_lightweight_benchmark.py     # Original mock runner
│   ├── test_production_runner.py        # Test/validation script
│   ├── generate_benchmark_display.py
│   ├── score_lightweight_results.py
│   └── README.md
│
├── results/                        # Output directory
│   └── lightweight/
│       ├── benchmark_results.json
│       ├── python_engineer_benchmark.json
│       └── ...
│
├── PRODUCTION_BENCHMARK.md         # Documentation
└── ARCHITECTURE_DIAGRAM.md         # This file

/tmp/claude-mpm-benchmarks/        # Temporary files (auto-cleanup)
    ├── task_python_easy_01.md
    ├── exec_*.py
    └── ... (cleaned after execution)
```

---

**Version**: 1.0.0 (MVP)
**Last Updated**: 2025-10-18
**Status**: Python support implemented
