# Benchmark Quick Reference

## Running Benchmarks

### Lightweight Suite (Recommended)
```bash
cd docs/benchmarks
./run_lightweight_benchmark_full.sh
```

**Time**: 20-25 minutes
**Cost**: ~$0.84
**Tests**: 84 (12 per agent)
**Coverage**: All 7 coding agents

### View Results
```bash
# Leaderboard
cat results/lightweight/leaderboard.txt

# Interactive dashboard
open results/lightweight/dashboard.html

# Detailed report
cat results/lightweight/scoring_report.txt

# Full execution report
cat EXECUTION_REPORT.md
```

## Current Scores (2025-10-18)

| Rank | Agent | Score | Grade | Status |
|------|-------|-------|-------|--------|
| 🥇 1 | Ruby Engineer | 68.1% | C+ | ✅ Functional |
| 🥈 2 | Rust Engineer | 67.3% | C+ | ✅ Functional |
| 🥉 3 | TypeScript Engineer | 66.8% | C+ | ✅ Functional |
| 4 | Next.js Engineer | 65.8% | C+ | ✅ Functional |
| 5 | Golang Engineer | 62.6% | C | ✅ Functional |
| 6 | Python Engineer | 62.3% | C | ✅ Functional |
| 7 | PHP Engineer | 60.8% | C | ⚠️ Needs improvement |

**Average**: 64.8%
**Median**: 65.8%
**Range**: 60.8% - 68.1% (7.3 percentage point spread)

## Performance by Difficulty

| Difficulty | Pass Rate | Tests |
|------------|-----------|-------|
| Easy | 89.3% | 25/28 |
| Medium | 62.9% | 22/35 |
| Hard | 42.9% | 9/21 |

## Scoring System

### Dimensions (Total 100%)

- **Correctness**: 40% - Does it work?
- **Idiomaticity**: 25% - Language-appropriate patterns?
- **Performance**: 20% - Efficient implementation?
- **Best Practices**: 15% - Industry standards?

### Difficulty Multipliers

- **Easy**: 1.0x baseline
- **Medium**: 1.2x weighted
- **Hard**: 1.5x weighted

### Final Score Calculation

```
Final Score = (
    (Easy Passed × 1.0 + Medium Passed × 1.2 + Hard Passed × 1.5) /
    (Easy Total × 1.0 + Medium Total × 1.2 + Hard Total × 1.5)
) × Average Dimension Score
```

## Grade Scale

| Grade | Score Range | Interpretation |
|-------|-------------|----------------|
| A | 90-100% | Excellent - Production-ready |
| B | 80-89% | Good - Minor improvements |
| C+ | 65-79% | Acceptable - Targeted improvements |
| C | 60-64% | Functional - Requires enhancement |
| D | 50-59% | Poor - Major work needed |
| F | <50% | Failing - Significant issues |

## Agent Strengths & Weaknesses

### Ruby Engineer (68.1%, #1)
✅ Strong idiomaticity (100%)
✅ Excellent string manipulation (89%)
⚠️ Needs improvement in functions category (25.8%)

### Rust Engineer (67.3%, #2)
✅ Strong correctness (100% on passed tests)
✅ Good performance on hard tests (2/3)
⚠️ Struggles with data structures (32.7%)

### TypeScript Engineer (66.8%, #3)
✅ Perfect easy test score (4/4)
✅ Strong type safety
⚠️ Medium test performance needs improvement (2/5)

### Next.js Engineer (65.8%, #4)
✅ Perfect easy test score (4/4)
✅ Strong medium performance (4/5)
⚠️ Hard test performance needs work (1/3)

### Golang Engineer (62.6%, #5)
✅ Balanced performance across difficulties
⚠️ Overall pass rate lower (58.3%)

### Python Engineer (62.3%, #6)
✅ Perfect easy test score (4/4)
⚠️ Medium and hard test performance needs improvement

### PHP Engineer (60.8%, #7)
✅ Perfect easy test score (4/4)
❌ Failed all hard tests (0/3)
⚠️ Needs significant improvement in advanced features

## Test Categories

Each agent is evaluated across:

1. **Algorithms** - Core algorithmic implementations
2. **Data Structures** - Efficient data structure usage
3. **String Manipulation** - Text processing and parsing
4. **Functions** - Function design and composition
5. **Arrays** - Array/list operations
6. **Async** - Asynchronous programming patterns

## Benchmark Infrastructure

### Files
- **Documentation**: `docs/benchmarks/README.md`
- **Quick Start**: `docs/benchmarks/QUICKSTART.md`
- **Test Suites**: `docs/benchmarks/lightweight/`
- **Latest Results**: `docs/benchmarks/results/baseline-2025-10-18/`
- **Results Directory**: `docs/benchmarks/results/lightweight/` (test runs)

### Key Scripts
- **Run Benchmark**: `./run_lightweight_benchmark_full.sh`
- **Analyze Results**: `python analyze_results.py`
- **Generate Dashboard**: `python generate_dashboard.py`

### Output Formats
- **Leaderboard**: Text-based ranking
- **Scoring Report**: Detailed dimension scores
- **Dashboard**: Interactive HTML visualization
- **Execution Report**: Complete analysis

## Interpreting Results

### For Agent Selection
- **Production Use**: Choose agents with 65%+ (C+ or better)
- **Development**: Agents 60-64% functional but need monitoring
- **Improvement Needed**: <60% requires targeted enhancements

### For Agent Development
- **Easy Tests**: Should achieve 90%+ pass rate
- **Medium Tests**: Target 70%+ pass rate
- **Hard Tests**: Aim for 50%+ pass rate

### For Continuous Improvement
- **Track Trends**: Monitor score changes over time
- **Focus Areas**: Target categories with lowest dimension scores
- **Balanced Improvement**: Address both correctness and idiomaticity

## Quick Tips

### Running Benchmarks
1. Always use latest agent versions
2. Run in clean environment
3. Check for API rate limits
4. Allow 20-25 minutes for completion

### Analyzing Results
1. Start with leaderboard for overview
2. Review execution report for details
3. Use dashboard for visual analysis
4. Compare dimension scores across agents

### Acting on Results
1. Identify lowest-scoring categories
2. Review failed test cases
3. Update agent prompts/capabilities
4. Re-run benchmarks to verify improvements

## Related Documentation

- [Coding Agents Catalog](CODING_AGENTS.md) - Complete agent documentation
- [Agent Testing Guide](../developer/AGENT_TESTING.md) - Testing methodology
- [Performance Guide](../developer/PERFORMANCE.md) - System performance

---

**Last Updated**: 2025-10-18
**Document Version**: 1.0.0
**Maintained By**: Claude MPM Team
