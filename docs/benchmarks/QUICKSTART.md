# Lightweight SWE Benchmark - Quick Start Guide

**Version:** 1.0.0 | **Status:** Production Ready | **Date:** 2025-10-18

---

## 🚀 30-Second Start

```bash
cd docs/benchmarks
./run_lightweight_benchmark_full.sh
```

That's it! The complete benchmark runs automatically.

---

## 📊 What You Get

### Execution
- **84 tests** across 7 agents (12 tests each)
- **4 dimensions** evaluated per test
- **3 difficulty levels** with weighting
- **~20-25 minutes** execution time (production mode)

### Results (7 files in `results/lightweight/`)

1. **leaderboard.txt** - Quick ASCII view
2. **scoring_report.txt** - Detailed text report  
3. **dashboard.html** - Interactive web dashboard
4. **benchmark_report.md** - Complete markdown report
5. **badges.md** - SVG badges for README
6. **benchmark_results.json** - Raw data
7. **scores.json** - Detailed scoring data

---

## 🎯 Quick Commands

### View Results
```bash
# Quick leaderboard
cat results/lightweight/leaderboard.txt

# Detailed report
less results/lightweight/scoring_report.txt

# Open dashboard
open results/lightweight/dashboard.html
```

### Run Individual Steps
```bash
# 1. Generate test suites (if needed)
python3 scripts/select_lightweight_tests.py

# 2. Run benchmark
python3 scripts/run_lightweight_benchmark.py

# 3. Calculate scores
python3 scripts/score_lightweight_results.py

# 4. Generate displays
python3 scripts/generate_benchmark_display.py
```

### Run Single Agent
```bash
python3 scripts/run_lightweight_benchmark.py --agent python_engineer
```

---

## 📈 Understanding Scores

### Score Components

**Overall Score (0-100%+)**
- Weighted average across all tests
- Can exceed 100% on exceptional hard test performance
- Determines letter grade (A+ through F)

**Pass Rate (0-100%)**
- Percentage of tests that passed
- Binary: test either passed or failed
- Independent of solution quality

**Dimensions (4 total)**
- Correctness (40%): Does it work?
- Idiomaticity (25%): Language-specific patterns?
- Performance (20%): Is it efficient?
- Best Practices (15%): Quality and maintainability?

### Grade Scale
| Grade | Range | Meaning |
|-------|-------|---------|
| A+ | 95%+ | Exceptional |
| A | 90-94% | Excellent |
| B+ | 80-89% | Good |
| B | 75-79% | Above Average |
| C+ | 70-74% | Satisfactory |
| C | 60-69% | Fair/Adequate |
| D | 50-59% | Poor |
| F | <50% | Failing |

---

## 🔧 Customization

### Change Test Distribution

Edit `scripts/select_lightweight_tests.py`:

```python
self.target_counts = {
    "easy": 6,    # Change from 4
    "medium": 4,  # Change from 5
    "hard": 2     # Change from 3
}
```

### Adjust Dimension Weights

Edit `scripts/score_lightweight_results.py`:

```python
DIMENSION_WEIGHTS = {
    "correctness": 0.50,      # Increase from 0.40
    "idiomaticity": 0.20,     # Decrease from 0.25
    "performance": 0.20,      # Same
    "best_practices": 0.10    # Decrease from 0.15
}
```

### Change Difficulty Multipliers

```python
DIFFICULTY_MULTIPLIERS = {
    "easy": 0.8,    # Decrease from 1.0
    "medium": 1.0,  # Decrease from 1.2
    "hard": 2.0     # Increase from 1.5
}
```

---

## 📚 Documentation

**Full Documentation:** `LIGHTWEIGHT_BENCHMARK_README.md` (800+ lines)
- System architecture
- Test selection methodology
- Detailed scoring explanation
- Result interpretation guide
- Customization guide
- Comprehensive FAQ

**Implementation Report:** `LIGHTWEIGHT_BENCHMARK_IMPLEMENTATION_REPORT.md`
- Complete status report
- Deliverables tracking
- Quality metrics
- Validation results

---

## 🎓 Example Output

### Leaderboard
```
1. typescript_engineer    [████████████████████░░░░]  73.7% (B-)
2. ruby_engineer          [███████████████████░░░░░]  72.4% (B-)
3. python_engineer        [███████████████████░░░░░]  71.3% (B-)
```

### Agent Profile
```
Agent: python_engineer
Score: 71.3% (B- - Satisfactory)
Pass Rate: 83.3% (10/12)

Dimensions:
  - Correctness:     78.5% ✓ Good
  - Idiomaticity:    72.1% → Needs improvement
  - Performance:     65.8% ⚠ Focus area
  - Best Practices:  70.2% → Room for growth

Strengths:
  - Excellent easy test performance (100%)
  - Strong correctness across all difficulties

Weaknesses:
  - Performance optimization needs work
  - Idiomaticity could be more language-specific
```

---

## 🐛 Troubleshooting

### "Test suites not found"
```bash
python3 scripts/select_lightweight_tests.py
```

### "benchmark_results.json not found"
```bash
python3 scripts/run_lightweight_benchmark.py
```

### "scores.json not found"
```bash
python3 scripts/score_lightweight_results.py
```

### Permission denied
```bash
chmod +x run_lightweight_benchmark_full.sh
```

---

## 💡 Pro Tips

1. **Run full pipeline first** - Use `./run_lightweight_benchmark_full.sh`
2. **Check HTML dashboard** - Most comprehensive view
3. **Save results** - Copy `results/lightweight/` with timestamps
4. **Compare over time** - Track improvements between runs
5. **Focus on dimensions** - Not just overall score

---

## 🎯 Next Steps

After running the benchmark:

1. **Review leaderboard** - Identify top performers
2. **Examine dimension breakdown** - Find strengths/weaknesses
3. **Read agent profiles** - Understand specific areas for improvement
4. **Set improvement goals** - Target specific dimensions/categories
5. **Re-run periodically** - Track progress over time

---

## 📞 Support

- **Full Guide:** See `LIGHTWEIGHT_BENCHMARK_README.md`
- **Implementation Details:** See implementation report
- **Source Code:** All scripts have detailed comments
- **Results:** Check JSON files for raw data

---

**Quick Start Complete!** 🎉

Run `./run_lightweight_benchmark_full.sh` to begin.

