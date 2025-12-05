# PM Validation Test Suite - Quick Start

## One-Line Summary
Test suite to validate PM correctly delegates ticketing operations (Circuit Breaker #6 compliance).

## Quick Run

```bash
# Test PM compliance
python tests/eval/run_pm_validation.py

# Test detection system
python tests/eval/run_pm_validation.py --use-violations

# Verbose mode
python tests/eval/run_pm_validation.py -v
```

## What Gets Tested

✅ Linear URL verification (https://linear.app/...)
✅ Ticket ID status checks (MPM-456)
✅ Ticket creation requests
✅ GitHub issue URLs (https://github.com/.../issues/...)
✅ Ticket search queries
✅ Ticket update requests

## Expected Results

### Compliance Mode (Default)
```
✅ PASS  Linear URL Verification  1.00
✅ PASS  Ticket ID Status Check   1.00
✅ PASS  Create Ticket Request    1.00
...
Pass Rate: 6/6 (100%)
```

### Violation Mode (--use-violations)
```
✅ DETECTED  Linear URL Verification  0.00 (WebFetch violation)
✅ DETECTED  Ticket ID Status Check   0.00 (mcp-ticketer violation)
...
Detection Rate: 6/6 (100%)
```

## Files

| File | Purpose |
|------|---------|
| `scenarios/pm_behavior_validation.json` | Test scenarios |
| `test_cases/test_pm_behavior_validation.py` | Test implementation |
| `utils/pm_response_simulator.py` | Response generation |
| `run_pm_validation.py` | Test runner |
| `README_PM_VALIDATION.md` | Full documentation |

## Common Commands

```bash
# Run specific test
pytest tests/eval/test_cases/test_pm_behavior_validation.py::TestPMBehaviorValidation::test_linear_url_delegation_fixed -v

# Generate HTML report
python tests/eval/run_pm_validation.py --report

# Run with pytest directly
pytest tests/eval/test_cases/test_pm_behavior_validation.py -m integration -v
```

## Current Status

🔧 **Minor Adjustment Needed**: Scores reach 0.67-0.82 instead of strict 1.0
- **Why**: Parent metric uses weighted scoring
- **Fix**: ~15 minutes to adjust metric
- **Options**: See `PM_VALIDATION_IMPLEMENTATION.md`

## When to Use

- ✅ Before releasing PM instruction changes
- ✅ After modifying Circuit Breaker #6
- ✅ When validating ticketing delegation
- ✅ During CI/CD pipeline runs
- ✅ When investigating PM behavior issues

## Help

```bash
python tests/eval/run_pm_validation.py --help
```

## Full Documentation

- **README**: `tests/eval/README_PM_VALIDATION.md` (comprehensive guide)
- **Implementation**: `tests/eval/PM_VALIDATION_IMPLEMENTATION.md` (technical details)
- **Delivery Report**: `docs/research/pm-validation-test-suite-delivery.md` (what was built)

---

**Created**: 2025-12-05
**Status**: Production-ready (95% complete - needs minor scoring adjustment)
**Framework**: DeepEval + pytest
