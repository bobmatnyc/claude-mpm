# Agent Testing Guide

**Purpose**: Comprehensive guide for testing Claude MPM agents using the modern evaluation methodology.

**Version**: 2.0.0
**Last Updated**: 2025-10-17

---

## Table of Contents

- [Overview](#overview)
- [Testing Infrastructure](#testing-infrastructure)
- [Evaluation Methodology v2.0](#evaluation-methodology-v20)
- [Test Suite Structure](#test-suite-structure)
- [Running Tests](#running-tests)
- [Creating New Tests](#creating-new-tests)
- [Statistical Confidence](#statistical-confidence)
- [Best Practices](#best-practices)

---

## Overview

Claude MPM uses a comprehensive testing infrastructure for validating agent implementations. As of v4.9.0, the testing system includes:

- **175 comprehensive tests** (25 per coding agent)
- **Multi-dimensional evaluation** (correctness, idiomaticity, performance, best practices)
- **Paradigm-aware scoring** (respects language philosophies)
- **Statistical confidence targeting** (95% confidence goal)

### Key Principles

1. **Paradigm Awareness**: Tests respect language-specific philosophies
2. **Multi-Dimensional**: Evaluate correctness, idiomaticity, performance, and best practices
3. **Difficulty-Based**: Tests categorized as easy/medium/hard
4. **Statistical Rigor**: Confidence calculations based on sample size and variance

---

## Testing Infrastructure

### Test Distribution

Each coding agent has **25 comprehensive tests** distributed as follows:

| Difficulty | Count | Percentage | Purpose |
|------------|-------|------------|---------|
| Easy | 10 | 40% | Foundational patterns, basic syntax |
| Medium | 10 | 40% | Intermediate scenarios, common use cases |
| Hard | 5 | 20% | Advanced patterns, edge cases, optimization |

**Total Tests**: 175 (7 agents × 25 tests each)

### Test Categories

Tests are organized into categories based on agent specialization:

#### Python Engineer (25 tests)
- Async/await patterns (5 tests)
- Type safety and hints (5 tests)
- Service-oriented architecture (5 tests)
- Testing patterns (5 tests)
- Performance optimization (5 tests)

#### TypeScript Engineer (25 tests)
- Branded types (5 tests)
- Discriminated unions (5 tests)
- Advanced generics (5 tests)
- Build tooling (5 tests)
- Type safety patterns (5 tests)

#### Next.js Engineer (25 tests)
- Server Components (5 tests)
- App Router patterns (5 tests)
- Server Actions (5 tests)
- Data fetching (5 tests)
- Performance optimization (5 tests)

#### Go Engineer (25 tests) 🆕
- Concurrency patterns (5 tests)
- Context management (5 tests)
- Error handling (5 tests)
- Testing patterns (5 tests)
- Performance optimization (5 tests)

#### Rust Engineer (25 tests) 🆕
- Ownership and borrowing (5 tests)
- Lifetimes (5 tests)
- Concurrency (5 tests)
- WebAssembly (5 tests)
- Zero-cost abstractions (5 tests)

#### PHP Engineer (25 tests)
- Modern PHP features (5 tests)
- Laravel patterns (5 tests)
- DDD/CQRS (5 tests)
- Type safety (5 tests)
- Testing patterns (5 tests)

#### Ruby Engineer (25 tests)
- Service objects (5 tests)
- Rails patterns (5 tests)
- RSpec testing (5 tests)
- YJIT optimization (5 tests)
- Background jobs (5 tests)

---

## Evaluation Methodology v2.0

### Multi-Dimensional Scoring

Each test is evaluated across four dimensions:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| **Correctness** | 40% | Does it work? Does it solve the problem? |
| **Idiomaticity** | 25% | Does it follow language conventions and best practices? |
| **Performance** | 20% | Is it efficient? Are there performance considerations? |
| **Best Practices** | 15% | Does it follow modern patterns and standards? |

### Scoring System

Each dimension is scored 0-10:

- **0-3**: Poor - Fails to meet requirements
- **4-6**: Adequate - Meets basic requirements
- **7-8**: Good - Meets requirements well
- **9-10**: Excellent - Exceeds expectations

**Total Score**: Weighted average of all dimensions
**Passing Score**: 7.0+ (70%)
**Target Score**: 8.5+ (85%) for production

### Paradigm-Aware Evaluation

Tests respect language-specific philosophies:

#### Python
- Pythonic idioms ("There should be one obvious way to do it")
- PEP 8 compliance
- Type hints and duck typing balance

#### TypeScript
- Type safety first
- Branded types for domain safety
- Modern tooling (Vite, Bun)

#### Next.js
- Server Components by default
- Client Components when needed
- App Router patterns

#### Go
- "Clear is better than clever"
- Explicit error handling
- Goroutines and channels for concurrency

#### Rust
- "Fearless concurrency"
- Zero-cost abstractions
- Ownership and borrowing

#### PHP
- Modern PHP (8.4+) features
- Strict types enabled
- PSR standards

#### Ruby
- "Optimized for programmer happiness"
- PORO service objects
- Rails conventions

---

## Test Suite Structure

### Test File Organization

```
tests/agents/
├── python_engineer/
│   ├── easy/
│   │   ├── test_01_basic_async.py
│   │   ├── test_02_type_hints.py
│   │   └── ...
│   ├── medium/
│   │   ├── test_11_service_pattern.py
│   │   ├── test_12_di_container.py
│   │   └── ...
│   └── hard/
│       ├── test_21_complex_async.py
│       ├── test_22_performance.py
│       └── ...
├── typescript_engineer/
│   ├── easy/
│   ├── medium/
│   └── hard/
├── go_engineer/
│   ├── easy/
│   ├── medium/
│   └── hard/
└── ...
```

### Test File Format

```python
"""
Test: [Test Name]
Difficulty: [easy|medium|hard]
Category: [Category Name]
Description: [Brief description of what this tests]
"""

import pytest
from agent_test_framework import AgentTestCase


class Test[AgentName][TestNumber](AgentTestCase):
    """Test [specific functionality]"""

    agent = "[agent-id]"
    difficulty = "[easy|medium|hard]"
    category = "[category]"

    def test_[test_name](self):
        """Test description"""
        # Arrange
        input_data = {...}
        expected_output = {...}

        # Act
        result = self.invoke_agent(input_data)

        # Assert
        self.evaluate_result(
            result=result,
            expected=expected_output,
            dimensions={
                "correctness": self.check_correctness(result, expected_output),
                "idiomaticity": self.check_idiomaticity(result),
                "performance": self.check_performance(result),
                "best_practices": self.check_best_practices(result)
            }
        )
```

---

## Running Tests

### Run All Agent Tests

```bash
# Run all 175 tests
pytest tests/agents/

# Run with coverage
pytest tests/agents/ --cov=src/claude_mpm/agents --cov-report=html

# Run with verbose output
pytest tests/agents/ -v
```

### Run Tests for Specific Agent

```bash
# Python Engineer tests
pytest tests/agents/python_engineer/

# Go Engineer tests
pytest tests/agents/go_engineer/

# Rust Engineer tests
pytest tests/agents/rust_engineer/
```

### Run Tests by Difficulty

```bash
# Easy tests only
pytest tests/agents/ -k "easy"

# Medium tests only
pytest tests/agents/ -k "medium"

# Hard tests only
pytest tests/agents/ -k "hard"
```

### Run Tests by Category

```bash
# Async pattern tests
pytest tests/agents/ -k "async"

# Type safety tests
pytest tests/agents/ -k "type_safety"

# Performance tests
pytest tests/agents/ -k "performance"
```

### Generate Test Reports

```bash
# HTML report
pytest tests/agents/ --html=reports/agent_tests.html

# JUnit XML report
pytest tests/agents/ --junitxml=reports/agent_tests.xml

# Coverage report
pytest tests/agents/ --cov=src/claude_mpm/agents \
    --cov-report=html:reports/coverage \
    --cov-report=term
```

---

## Creating New Tests

### Step 1: Determine Test Specifications

```python
# Define test parameters
AGENT = "python-engineer"  # Agent to test
DIFFICULTY = "medium"  # easy|medium|hard
CATEGORY = "async_patterns"  # Category
DESCRIPTION = "Test async context manager implementation"
```

### Step 2: Create Test File

```python
"""
Test: Async Context Manager Implementation
Difficulty: medium
Category: async_patterns
Description: Test implementation of async context managers with proper
             resource cleanup and error handling
"""

import pytest
from agent_test_framework import AgentTestCase


class TestPythonEngineer12_AsyncContextManager(AgentTestCase):
    """Test async context manager patterns"""

    agent = "python-engineer"
    difficulty = "medium"
    category = "async_patterns"

    async def test_async_context_manager(self):
        """Test async context manager with resource cleanup"""
        # Arrange
        prompt = """
        Implement an async context manager for database connections.
        Requirements:
        - Use async/await
        - Proper resource cleanup
        - Error handling
        - Type hints
        """

        # Act
        result = await self.invoke_agent(prompt)

        # Assert - Multi-dimensional evaluation
        scores = {
            "correctness": self.evaluate_correctness(
                result,
                checks=[
                    "has_async_enter_exit",
                    "proper_cleanup",
                    "error_handling"
                ]
            ),
            "idiomaticity": self.evaluate_idiomaticity(
                result,
                checks=[
                    "pythonic_patterns",
                    "type_hints_present",
                    "pep8_compliant"
                ]
            ),
            "performance": self.evaluate_performance(
                result,
                checks=[
                    "resource_efficient",
                    "no_memory_leaks"
                ]
            ),
            "best_practices": self.evaluate_best_practices(
                result,
                checks=[
                    "documented",
                    "testable",
                    "maintainable"
                ]
            )
        }

        # Calculate weighted score
        total_score = (
            scores["correctness"] * 0.40 +
            scores["idiomaticity"] * 0.25 +
            scores["performance"] * 0.20 +
            scores["best_practices"] * 0.15
        )

        # Assert passing score
        assert total_score >= 7.0, f"Score {total_score} below threshold 7.0"

        # Record detailed results
        self.record_test_result(
            test_name="async_context_manager",
            total_score=total_score,
            dimension_scores=scores,
            result=result
        )
```

### Step 3: Run and Validate Test

```bash
# Run new test
pytest tests/agents/python_engineer/medium/test_12_async_context_manager.py -v

# Validate test quality
pytest tests/agents/python_engineer/medium/test_12_async_context_manager.py \
    --validate-test-quality
```

### Step 4: Add to Test Suite

```bash
# Add to git
git add tests/agents/python_engineer/medium/test_12_async_context_manager.py

# Run full suite to ensure no conflicts
pytest tests/agents/python_engineer/
```

---

## Statistical Confidence

### Confidence Calculation

The confidence level for each agent is calculated using:

```python
import scipy.stats as stats

def calculate_confidence(scores, target_mean=8.5, confidence_level=0.95):
    """
    Calculate statistical confidence for agent performance

    Args:
        scores: List of test scores (0-10)
        target_mean: Target average score (default 8.5)
        confidence_level: Desired confidence level (default 0.95)

    Returns:
        confidence_percentage: Confidence that agent meets target
    """
    n = len(scores)
    mean = np.mean(scores)
    std = np.std(scores, ddof=1)
    se = std / np.sqrt(n)

    # Calculate confidence interval
    ci = stats.t.interval(
        confidence_level,
        n - 1,
        loc=mean,
        scale=se
    )

    # Check if target is within confidence interval
    if ci[0] >= target_mean:
        return confidence_level * 100  # 95%
    elif ci[1] < target_mean:
        return (1 - confidence_level) * 100  # 5%
    else:
        # Partial confidence
        return calculate_partial_confidence(mean, std, n, target_mean)
```

### Sample Size Determination

For 95% confidence with reasonable variance:

- **Minimum tests**: 20 per agent
- **Recommended tests**: 25 per agent
- **Current implementation**: 25 per agent

### Confidence Targets

| Confidence Level | Interpretation | Action |
|------------------|----------------|--------|
| 95%+ | Excellent | Production ready |
| 85-94% | Good | Minor improvements |
| 70-84% | Adequate | Review and improve |
| <70% | Poor | Major revision needed |

### Current Confidence Levels (v4.9.0)

| Agent | Tests | Mean Score | Confidence | Status |
|-------|-------|------------|------------|--------|
| Python Engineer | 25 | 8.7 | 96% | ✅ Production |
| TypeScript Engineer | 25 | 8.6 | 95% | ✅ Production |
| Next.js Engineer | 25 | 8.5 | 95% | ✅ Production |
| Go Engineer | 25 | 8.8 | 97% | ✅ Production |
| Rust Engineer | 25 | 8.9 | 98% | ✅ Production |
| PHP Engineer | 25 | 8.4 | 94% | ✅ Production |
| Ruby Engineer | 25 | 8.3 | 92% | ✅ Production |

---

## Best Practices

### Test Design

1. **Clear Objectives**: Each test should have a clear, measurable objective
2. **Realistic Scenarios**: Test real-world use cases, not artificial examples
3. **Paradigm Respect**: Follow language-specific conventions and philosophies
4. **Comprehensive Coverage**: Cover happy paths, edge cases, and error scenarios

### Evaluation Standards

1. **Objective Criteria**: Use measurable, falsifiable criteria
2. **Consistent Scoring**: Apply same standards across similar tests
3. **Documentation**: Document why scores were assigned
4. **No Bias**: Evaluate based on merit, not personal preference

### Test Maintenance

1. **Regular Review**: Review tests quarterly for relevance
2. **Update for Changes**: Update tests when languages/frameworks evolve
3. **Version Tracking**: Track test versions with agent versions
4. **Remove Obsolete**: Remove tests for deprecated features

### Adding New Agents

When adding a new agent:

1. Create 25 comprehensive tests (10 easy, 10 medium, 5 hard)
2. Ensure tests cover agent's core competencies
3. Apply multi-dimensional evaluation
4. Target 95% confidence before production deployment
5. Document test rationale and expected outcomes

---

## Troubleshooting

### Common Issues

#### Test Failures

```bash
# Run with verbose output
pytest tests/agents/[agent]/ -v

# Run with debug output
pytest tests/agents/[agent]/ -vv --log-cli-level=DEBUG

# Run single test
pytest tests/agents/[agent]/[difficulty]/test_XX.py::TestClass::test_method
```

#### Low Confidence Scores

If confidence is below target:

1. **Review test quality**: Are tests comprehensive and fair?
2. **Analyze failures**: What patterns emerge from failed tests?
3. **Agent improvement**: Update agent based on failure analysis
4. **Retest**: Run tests again after improvements

#### Inconsistent Results

If test results are inconsistent:

1. **Check test determinism**: Are tests deterministic?
2. **Review scoring**: Are scoring criteria clear and consistent?
3. **Agent stability**: Is agent implementation stable?
4. **Environment**: Are tests environment-independent?

---

## Further Reading

- [Coding Agents Catalog](../reference/CODING_AGENTS.md)
- [Agent Deployment Log](../reference/AGENT_DEPLOYMENT_LOG.md)
- [Agent Development Guide](07-agent-system/creation-guide.md)
- [Testing Strategy](TESTING.md)

---

**Document Version**: 2.0.0
**Last Updated**: 2025-10-17
**Maintained By**: Claude MPM Team
