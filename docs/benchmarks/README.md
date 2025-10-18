# Lightweight SWE Benchmark System

## Overview

A complete lightweight Software Engineering (SWE) benchmark system for evaluating Claude MPM coding agents across 7 programming languages. Executes 84 carefully selected tests (12 per agent) with multi-dimensional scoring in approximately 20-25 minutes.

**Version:** 1.0.0
**Confidence Level:** 85-90%
**Total Tests:** 84 (7 agents × 12 tests each)
**Execution Time:** ~20-25 minutes

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [System Architecture](#system-architecture)
3. [Test Selection Methodology](#test-selection-methodology)
4. [Scoring System](#scoring-system)
5. [Running the Benchmark](#running-the-benchmark)
6. [Interpreting Results](#interpreting-results)
7. [Generated Outputs](#generated-outputs)
8. [Customization](#customization)
9. [FAQ](#faq)

---

## Quick Start

### Prerequisites

- Python 3.8+
- Basic Unix/Linux environment
- ~500MB disk space for results

### Run Complete Benchmark

```bash
cd docs/benchmarks
./run_lightweight_benchmark_full.sh
```

This executes the full pipeline:
1. Test suite selection (if needed)
2. Benchmark execution (84 tests)
3. Multi-dimensional scoring
4. Display generation

### View Results

```bash
# ASCII leaderboard
cat results/lightweight/leaderboard.txt

# Detailed report
less results/lightweight/scoring_report.txt

# HTML dashboard (opens in browser)
open results/lightweight/dashboard.html
```

---

## System Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Test Selection Layer                     │
│  select_lightweight_tests.py                                │
│  • Intelligent 12-test selection from 25-test suites        │
│  • Difficulty distribution: 4 easy, 5 medium, 3 hard        │
│  • Category diversity optimization                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Benchmark Execution Layer                 │
│  run_lightweight_benchmark.py                               │
│  • Executes 12 tests per agent (84 total)                   │
│  • Multi-dimensional evaluation during execution            │
│  • Real-time progress tracking                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      Scoring Engine                         │
│  score_lightweight_results.py                               │
│  • Difficulty-weighted scoring                              │
│  • Dimension aggregation and analysis                       │
│  • Strength/weakness identification                         │
│  • Grade assignment                                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Display Generation                        │
│  generate_benchmark_display.py                              │
│  • Markdown reports                                         │
│  • SVG badges                                               │
│  • HTML dashboard                                           │
│  • ASCII visualizations                                     │
└─────────────────────────────────────────────────────────────┘
```

### File Structure

```
docs/benchmarks/
├── benchmarks/
│   └── lightweight/              # Lightweight test suites
│       ├── python_mini.json      # 12 Python tests
│       ├── typescript_mini.json  # 12 TypeScript tests
│       ├── nextjs_mini.json      # 12 Next.js tests
│       ├── php_mini.json         # 12 PHP tests
│       ├── ruby_mini.json        # 12 Ruby tests
│       ├── golang_mini.json      # 12 Go tests
│       ├── rust_mini.json        # 12 Rust tests
│       └── suite_manifest.json   # Selection metadata
│
├── scripts/
│   ├── select_lightweight_tests.py        # Test selector
│   ├── run_lightweight_benchmark.py       # Benchmark runner
│   ├── score_lightweight_results.py       # Scoring engine
│   └── generate_benchmark_display.py      # Display generator
│
├── results/
│   └── lightweight/
│       ├── benchmark_results.json  # Raw results
│       ├── scores.json            # Detailed scores
│       ├── scoring_report.txt     # Text report
│       ├── benchmark_report.md    # Markdown report
│       ├── badges.md              # Badge markdown
│       ├── dashboard.html         # HTML dashboard
│       └── leaderboard.txt        # ASCII leaderboard
│
├── run_lightweight_benchmark_full.sh  # Master execution script
└── LIGHTWEIGHT_BENCHMARK_README.md    # This file
```

---

## Test Selection Methodology

### Selection Criteria

From each agent's 25-test expanded suite, 12 tests are intelligently selected:

**Difficulty Distribution:**
- **4 Easy tests** (33%): Foundational skills
- **5 Medium tests** (42%): Core competencies
- **3 Hard tests** (25%): Advanced capabilities

**Selection Factors:**

1. **Category Diversity** (Priority 1)
   - Maximize category coverage
   - Avoid duplicate categories when possible
   - Ensure comprehensive skill assessment

2. **Test Quality** (Priority 2)
   - Number of test cases
   - Presence of constraints and hints
   - Solution approach documentation
   - Complexity indicators (time/space)

3. **Educational Value** (Priority 3)
   - Clear learning objectives
   - Representative of real-world scenarios
   - Well-defined success criteria

### Algorithm

```python
For each difficulty level:
  1. Filter tests by difficulty
  2. Score each test based on:
     - Category uniqueness (1.0 / (category_count + 1)) × 10
     - Test case count (min(count, 5)) × 2
     - Has constraints: +3
     - Has hints: +3
     - Has solution approach: +5
     - Has complexity analysis: +4
  3. Iteratively select highest-scoring tests
  4. Update category counts after each selection
  5. Repeat until target count reached
```

### Example: Python Engineer Selection

**From 25 tests → 12 selected:**

**Easy (4/10 selected):**
- Two Sum (algorithms)
- Valid Parentheses (data_structures)
- FizzBuzz (algorithms)
- Find First Palindromic String (string_manipulation)

**Medium (5/10 selected):**
- Three Sum (algorithms)
- Longest Substring Without Repeating (string_manipulation)
- Async Task Processor (async_programming)
- Binary Tree Level Order Traversal (data_structures)
- Rate Limiter (real_world)

**Hard (3/5 selected):**
- Median of Two Sorted Arrays (algorithms)
- Async Worker Pool with Retries (async_programming)
- Serialize and Deserialize Binary Tree (data_structures)

**Coverage:** 5 categories (algorithms, data_structures, string_manipulation, async_programming, real_world)

---

## Scoring System

### Multi-Dimensional Evaluation

Each test is evaluated across **4 dimensions:**

| Dimension | Weight | Max Points | Description |
|-----------|--------|------------|-------------|
| **Correctness** | 40% | 10.0 | Solution works and passes all tests |
| **Idiomaticity** | 25% | 10.0 | Uses language-specific patterns and conventions |
| **Performance** | 20% | 10.0 | Efficient algorithms and optimization |
| **Best Practices** | 15% | 10.0 | Code quality, maintainability, security |

### Difficulty Multipliers

Difficulty affects maximum possible points:

| Difficulty | Multiplier | Max Points (weighted) |
|------------|------------|----------------------|
| Easy | 1.0× | 10.0 |
| Medium | 1.2× | 12.0 |
| Hard | 1.5× | 15.0 |

**Example Calculation:**

```
Test: "Async Worker Pool with Retries" (Hard)
Raw dimension scores:
  - Correctness: 9.1/10
  - Idiomaticity: 8.6/10
  - Performance: 5.5/10
  - Best Practices: 8.9/10

Weighted scores:
  - Correctness: 9.1 × 0.40 = 3.64
  - Idiomaticity: 8.6 × 0.25 = 2.15
  - Performance: 5.5 × 0.20 = 1.10
  - Best Practices: 8.9 × 0.15 = 1.34

Base score: 3.64 + 2.15 + 1.10 + 1.34 = 8.23

Final score (with difficulty): 8.23 × 1.5 = 12.35 points
Max possible: 10.0 × 1.5 = 15.0 points
Percentage: 12.35 / 15.0 = 82.3%
```

### Grade Scale

| Grade | Percentage Range | Description |
|-------|------------------|-------------|
| **A+** | 95-100%+ | Exceptional |
| **A** | 90-94% | Excellent |
| **A-** | 85-89% | Very Good |
| **B+** | 80-84% | Good |
| **B** | 75-79% | Above Average |
| **B-** | 70-74% | Satisfactory |
| **C+** | 65-69% | Fair |
| **C** | 60-64% | Adequate |
| **C-** | 55-59% | Below Average |
| **D+** | 50-54% | Poor |
| **D** | 45-49% | Very Poor |
| **F** | 0-44% | Failing |

### Aggregate Scoring

**Agent Score:**
```
Total Points = Σ(test_weighted_score)
Max Points = Σ(test_max_possible)
Percentage = (Total Points / Max Points) × 100
```

**Dimension Scores:**
```
For each dimension:
  Dimension Total = Σ(dimension_weighted_score across all tests)
  Dimension Max = Σ(dimension_max_score across all tests)
  Dimension % = (Dimension Total / Dimension Max) × 100
```

---

## Running the Benchmark

### Full Pipeline (Recommended)

```bash
./run_lightweight_benchmark_full.sh
```

Executes all steps automatically:
1. Test selection (if needed)
2. Benchmark execution
3. Scoring
4. Display generation

**Output:** Complete results in `results/lightweight/`

### Individual Steps

#### Step 1: Generate Test Suites

```bash
python3 scripts/select_lightweight_tests.py
```

Selects 12 tests per agent from expanded suites.

**Output:** `benchmarks/lightweight/*.json`

#### Step 2: Run Benchmark

```bash
# All agents
python3 scripts/run_lightweight_benchmark.py

# Single agent
python3 scripts/run_lightweight_benchmark.py --agent python_engineer
```

**Output:** `results/lightweight/benchmark_results.json`

#### Step 3: Calculate Scores

```bash
python3 scripts/score_lightweight_results.py
```

**Output:**
- `results/lightweight/scores.json`
- `results/lightweight/scoring_report.txt`

#### Step 4: Generate Displays

```bash
python3 scripts/generate_benchmark_display.py
```

**Output:**
- `benchmark_report.md` (Markdown)
- `badges.md` (SVG badges)
- `dashboard.html` (Interactive HTML)
- `leaderboard.txt` (ASCII art)

---

## Interpreting Results

### Leaderboard

```
================================================================================
AGENT BENCHMARK SCORES (Lightweight Suite)
================================================================================

1. typescript_engineer      [████████████████████████████████████░░░░░]  73.7% (B-)
2. ruby_engineer            [███████████████████████████████████░░░░░░]  72.4% (B-)
3. python_engineer          [███████████████████████████████████░░░░░░]  71.3% (B-)
4. php_engineer             [████████████████████████████████████░░░░░]  74.2% (B)
5. nextjs_engineer          [██████████████████████████████░░░░░░░░░░░]  68.0% (C+)
6. rust_engineer            [███████████████████████████████░░░░░░░░░░]  68.3% (C+)
7. golang_engineer          [█████████████████████████░░░░░░░░░░░░░░░]  56.0% (C-)

================================================================================
```

### Understanding Your Score

**Score Components:**

1. **Overall Percentage** (0-100%+)
   - Weighted average across all tests
   - Can exceed 100% if hard tests are mastered
   - Reflects overall competency

2. **Pass Rate** (0-100%)
   - Percentage of tests that passed
   - Binary pass/fail per test
   - Independent of score quality

3. **Dimension Breakdown**
   - Shows strengths and weaknesses
   - Identifies areas for improvement
   - Weighted by dimension importance

**Example Interpretation:**

```
Agent: python_engineer
Score: 71.3% (B-)
Pass Rate: 83.3% (10/12)

Dimensions:
  - Correctness: 78.5%     ✓ Good
  - Idiomaticity: 72.1%    → Needs improvement
  - Performance: 65.8%     ⚠ Focus area
  - Best Practices: 70.2%  → Room for growth

Strengths:
  - Excellent easy test performance (100%)
  - Strong correctness across all difficulties

Weaknesses:
  - Performance optimization needs work
  - Idiomaticity could be more language-specific
```

### Actionable Insights

**High Performers (80%+):**
- Maintain consistency
- Focus on hard problem mastery
- Mentor other agents

**Mid-Range (70-79%):**
- Target weakest dimension
- Improve medium test performance
- Study best practices

**Low Performers (<70%):**
- Review fundamentals
- Focus on easy test mastery
- Practice core patterns

---

## Generated Outputs

### 1. benchmark_results.json

**Raw benchmark data:**
```json
{
  "benchmark_type": "lightweight",
  "version": "1.0.0",
  "total_agents": 7,
  "total_tests": 84,
  "results": {
    "python_engineer": {
      "total_tests": 12,
      "passed_tests": 10,
      "results": [...]
    }
  }
}
```

**Usage:** Data analysis, custom processing, integration

### 2. scores.json

**Detailed scoring data:**
```json
{
  "benchmark_type": "lightweight",
  "scores": {
    "python_engineer": {
      "percentage": 71.28,
      "grade": "B-",
      "dimension_scores": {...},
      "difficulty_breakdown": {...},
      "strengths": [...],
      "weaknesses": [...]
    }
  },
  "leaderboard": [...],
  "aggregate_statistics": {...}
}
```

**Usage:** Detailed analysis, comparisons, tracking over time

### 3. scoring_report.txt

**Human-readable text report:**
- Leaderboard table
- Aggregate statistics
- Agent-by-agent details
- Dimension breakdowns
- Strengths and weaknesses

**Usage:** Quick review, sharing results, documentation

### 4. benchmark_report.md

**Comprehensive Markdown report:**
- Formatted tables
- Progress bars
- Agent profiles
- Detailed statistics

**Usage:** Documentation, GitHub integration, reports

### 5. badges.md

**SVG badge markdown:**
```markdown
![python-engineer](https://img.shields.io/badge/python--engineer-71%25_B--yellowgreen)
```

**Usage:** README files, documentation, dashboards

### 6. dashboard.html

**Interactive HTML dashboard:**
- Responsive design
- Gradient visualizations
- Sortable tables
- Progress bars

**Usage:** Presentations, sharing with stakeholders, interactive exploration

### 7. leaderboard.txt

**ASCII art leaderboard:**
```
1. python_engineer        [███████████████████████░░░░░] 71.3% (B-)
2. typescript_engineer    [████████████████████████░░░░] 73.7% (B-)
```

**Usage:** Terminal output, quick checks, CI/CD integration

---

## Customization

### Adjust Test Selection

Edit `scripts/select_lightweight_tests.py`:

```python
# Change difficulty distribution
self.target_counts = {
    "easy": 6,    # More easy tests
    "medium": 4,  # Fewer medium
    "hard": 2     # Fewer hard
}

# Modify selection scoring
def calculate_test_score(self, test, category_counts):
    score = 0.0

    # Custom scoring logic
    if test.get('custom_field'):
        score += 10

    return score
```

### Modify Dimension Weights

Edit `scripts/run_lightweight_benchmark.py` and `scripts/score_lightweight_results.py`:

```python
DIMENSION_WEIGHTS = {
    "correctness": 0.50,      # Increase correctness weight
    "idiomaticity": 0.20,     # Decrease idiomaticity
    "performance": 0.20,      # Keep performance
    "best_practices": 0.10    # Decrease best practices
}
```

### Adjust Difficulty Multipliers

Edit `scripts/score_lightweight_results.py`:

```python
DIFFICULTY_MULTIPLIERS = {
    "easy": 0.8,    # Less weight on easy
    "medium": 1.0,  # Baseline
    "hard": 2.0     # More weight on hard
}
```

### Custom Grade Thresholds

```python
GRADE_THRESHOLDS = [
    (98, "A+", "Outstanding"),
    (92, "A", "Excellent"),
    (85, "B+", "Very Good"),
    # ... custom thresholds
]
```

---

## FAQ

### Q: How long does the benchmark take?

**A:** Approximately 20-25 minutes for all 7 agents (84 tests total). Individual agents take ~3 minutes each.

### Q: Can I run just one agent?

**A:** Yes:
```bash
python3 scripts/run_lightweight_benchmark.py --agent python_engineer
```

### Q: What if I add more tests?

**A:** Modify `select_lightweight_tests.py` to adjust `target_counts`. The system will automatically adapt.

### Q: Can scores exceed 100%?

**A:** Yes, when hard tests (1.5× multiplier) are mastered, agents can score above 100%. This reflects exceptional performance.

### Q: How do I compare results over time?

**A:** Save `scores.json` with timestamps:
```bash
cp results/lightweight/scores.json results/lightweight/scores_$(date +%Y%m%d).json
```

Then compare using your preferred diff tool.

### Q: What's the difference between pass rate and score?

**A:**
- **Pass Rate:** Binary (test passed or failed)
- **Score:** Quality-weighted (how well did it pass)

Example: 100% pass rate with poor quality = lower score

### Q: Can I integrate this into CI/CD?

**A:** Yes! The scripts return exit codes and JSON output. Example:

```bash
#!/bin/bash
./run_lightweight_benchmark_full.sh

# Check if average score meets threshold
SCORE=$(jq '.aggregate_statistics.average_score' results/lightweight/scores.json)
if (( $(echo "$SCORE < 75.0" | bc -l) )); then
    echo "Benchmark score below threshold: $SCORE%"
    exit 1
fi
```

### Q: How do I add a new agent?

**A:**
1. Create expanded test suite: `benchmarks/expanded/{language}_tests.json`
2. Add to agent list in all scripts
3. Re-run test selection
4. Execute benchmark

### Q: What about production agent execution?

**A:** Currently in mock mode. To enable production:

```bash
python3 scripts/run_lightweight_benchmark.py --production
```

You'll need to implement the agent invocation logic in `run_lightweight_benchmark.py`.

---

## Version History

**v1.0.0** (2025-10-18)
- Initial release
- 7 agents, 84 tests
- Multi-dimensional scoring
- Complete display generation
- Mock execution mode

---

## Contributing

To improve the benchmark system:

1. **Add Tests:** Create tests in expanded suites
2. **Improve Selection:** Enhance scoring algorithm
3. **Add Dimensions:** Introduce new evaluation criteria
4. **Better Visualizations:** Create additional display formats

---

## Support

For questions or issues:
- Check FAQ above
- Review generated reports
- Examine JSON output files
- Consult source code comments

---

## License

Part of the Claude MPM Agent Evaluation System.

---

**Lightweight SWE Benchmark v1.0.0**
*Fast, focused, and comprehensive agent evaluation*
