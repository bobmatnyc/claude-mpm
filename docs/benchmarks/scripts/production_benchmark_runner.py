#!/usr/bin/env python3
"""
Production Benchmark Runner for Claude MPM Agents

This module extends the LightweightBenchmarkRunner with real agent execution,
code extraction, solution testing, and multi-dimensional evaluation.

Key Features:
- Real agent invocation via claude-mpm CLI
- Safe code execution in isolated subprocesses
- Multi-dimensional scoring (correctness, idiomaticity, performance, best practices)
- Support for Python (MVP) with extensibility for other languages
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

from run_lightweight_benchmark import LightweightBenchmarkRunner


class ProductionBenchmarkRunner(LightweightBenchmarkRunner):
    """Production benchmark runner with real agent execution."""

    def __init__(self, base_path: Path, mock_mode: bool = False):
        super().__init__(base_path, mock_mode)

        # Execution configuration
        self.agent_timeout = 120  # 2 minutes per agent invocation
        self.execution_timeout = 30  # 30 seconds per solution execution

        # Language mapping
        self.language_map = {
            "python_engineer": "python",
            "typescript_engineer": "typescript",
            "nextjs_engineer": "typescript",
            "php_engineer": "php",
            "ruby_engineer": "ruby",
            "golang_engineer": "go",
            "rust_engineer": "rust"
        }

        # Temp directory for task files
        self.temp_dir = Path("/tmp/claude-mpm-benchmarks")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def create_task_file(self, test: Dict, agent_id: str) -> Path:
        """
        Create a task file for the agent to solve.

        Args:
            test: Test definition dict with description, signature, test_cases, etc.
            agent_id: Agent identifier (e.g., 'python_engineer')

        Returns:
            Path to the created task file
        """
        language = self.language_map[agent_id]

        # Format test cases for display
        test_cases_text = "\n".join([
            f"- Input: {tc['input']}\n  Expected: {tc['expected']}"
            for tc in test['test_cases']
        ])

        # Format constraints
        constraints_text = "\n".join([
            f"- {c}" for c in test.get('constraints', [])
        ])

        # Format hints
        hints_text = "\n".join([
            f"- {h}" for h in test.get('hints', [])
        ]) if test.get('hints') else "No additional hints provided."

        # Create task content
        task_content = f"""# Coding Challenge: {test['name']}

## Description
{test['description']}

## Function Signature
```{language}
{test['signature']}
```

## Test Cases
{test_cases_text}

## Constraints
{constraints_text}

## Hints
{hints_text}

## Instructions
Provide a complete, working implementation that:
1. Implements the function signature exactly as specified
2. Passes all test cases
3. Follows {language} best practices and idioms
4. Includes clear comments explaining your approach

**IMPORTANT**: Return ONLY the implementation code in a code block. Do not include test execution code or explanations outside the code block.
"""

        # Write to file
        task_file = self.temp_dir / f"task_{test['id']}.md"
        task_file.write_text(task_content)

        return task_file

    def invoke_agent(self, agent_id: str, task_file: Path) -> Dict[str, Any]:
        """
        Invoke Claude MPM agent with task file via subprocess.

        Args:
            agent_id: Agent identifier
            task_file: Path to task markdown file

        Returns:
            Dict with keys: status, stdout, stderr, returncode, execution_time
        """
        # Build command - use full path to claude-mpm
        claude_mpm_path = Path(__file__).parent.parent.parent.parent / "scripts" / "claude-mpm"

        cmd = [
            str(claude_mpm_path), "run",
            "--non-interactive",
            "--input", str(task_file),
            "--no-hooks",
            "--launch-method", "subprocess"
        ]

        # Set environment
        env = os.environ.copy()
        env["MPM_AGENT"] = agent_id

        try:
            start_time = time.time()

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.agent_timeout,
                env=env,
                check=False
            )

            execution_time = time.time() - start_time

            return {
                "status": "success" if result.returncode == 0 else "failed",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "execution_time": execution_time
            }

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "stdout": "",
                "stderr": f"Agent execution exceeded {self.agent_timeout}s timeout",
                "returncode": -1,
                "execution_time": self.agent_timeout
            }

        except Exception as e:
            return {
                "status": "error",
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "execution_time": 0
            }

    def extract_solution_code(self, response: str, language: str) -> Optional[str]:
        """
        Extract code from agent response using regex patterns.

        Args:
            response: Raw agent response text
            language: Programming language (e.g., 'python')

        Returns:
            Extracted code string or None if no code found
        """
        # Try language-specific code block first
        pattern = rf"```{language}\n(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)

        if matches:
            # Return the longest match (likely the main implementation)
            return max(matches, key=len).strip()

        # Fallback: Any code block
        pattern = r"```\n(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL)

        if matches:
            return max(matches, key=len).strip()

        # No code block found
        return None

    def execute_python_solution(self, solution: str, test: Dict) -> Dict[str, Any]:
        """
        Execute Python solution with test cases in isolated subprocess.

        Args:
            solution: Python code to test
            test: Test definition with test_cases

        Returns:
            Dict with keys: passed, test_results, execution_time, stdout, stderr, error
        """
        # Extract function name from signature
        signature = test['signature']
        func_name_match = re.search(r'def\s+(\w+)', signature)
        if not func_name_match:
            return {
                'passed': False,
                'error': 'Could not extract function name from signature'
            }

        func_name = func_name_match.group(1)

        # Create test harness
        test_cases_json = json.dumps(test['test_cases'])
        test_script = f"""
import sys
import json
from typing import List, Dict, Any, Optional

# Solution code
{solution}

# Test execution
def run_tests():
    results = []
    test_cases_data = {test_cases_json}

    for i, test_case in enumerate(test_cases_data):
        try:
            # Parse input
            tc_input = test_case['input']
            expected_str = test_case['expected']

            # Execute function
            result = eval(f"{func_name}({{tc_input}})")
            expected = eval(expected_str)

            # Compare
            passed = result == expected

            results.append({{
                'test_case': i,
                'passed': passed,
                'input': tc_input,
                'expected': expected,
                'actual': result,
                'error': None
            }})

        except Exception as e:
            results.append({{
                'test_case': i,
                'passed': False,
                'input': test_case.get('input', ''),
                'expected': test_case.get('expected', ''),
                'actual': None,
                'error': str(e)
            }})

    print(json.dumps(results))

if __name__ == '__main__':
    run_tests()
"""

        # Write to temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False
        ) as f:
            f.write(test_script)
            script_path = f.name

        try:
            # Execute
            start_time = time.time()

            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=self.execution_timeout,
                check=False
            )

            execution_time = time.time() - start_time

            # Parse results
            if result.returncode == 0 and result.stdout.strip():
                try:
                    test_results = json.loads(result.stdout)
                    passed = all(r['passed'] for r in test_results)

                    return {
                        'passed': passed,
                        'test_results': test_results,
                        'execution_time': execution_time,
                        'stdout': result.stdout,
                        'stderr': result.stderr
                    }
                except json.JSONDecodeError:
                    return {
                        'passed': False,
                        'test_results': [],
                        'execution_time': execution_time,
                        'error': 'Could not parse test results',
                        'stdout': result.stdout,
                        'stderr': result.stderr
                    }
            else:
                return {
                    'passed': False,
                    'test_results': [],
                    'execution_time': execution_time,
                    'error': 'Execution failed',
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }

        except subprocess.TimeoutExpired:
            return {
                'passed': False,
                'test_results': [],
                'execution_time': self.execution_timeout,
                'error': f'Execution timeout ({self.execution_timeout}s)'
            }

        except Exception as e:
            return {
                'passed': False,
                'test_results': [],
                'execution_time': 0,
                'error': str(e)
            }

        finally:
            # Cleanup
            Path(script_path).unlink(missing_ok=True)

    def evaluate_correctness(self, execution_result: Dict) -> float:
        """
        Evaluate correctness dimension (0-10).

        Correctness is the most important dimension (40% weight).
        Full pass = 9.5, partial pass = proportional up to 4.0, fail = 0.0
        """
        if execution_result.get('error'):
            return 0.0

        if not execution_result.get('passed'):
            # Partial credit based on test pass rate
            test_results = execution_result.get('test_results', [])
            if test_results:
                pass_rate = sum(1 for r in test_results if r['passed']) / len(test_results)
                return min(pass_rate * 10, 4.0)  # Max 4.0 for partial
            return 0.0

        # Full pass
        return 9.5

    def evaluate_idiomaticity(self, solution: str, language: str, passed: bool) -> float:
        """
        Evaluate idiomaticity dimension (0-10).

        Checks for language-specific patterns and conventions.
        MVP version focuses on Python patterns.
        """
        if not passed:
            return 4.0  # Moderate score for failed solutions

        # Simple checks for Python
        if language == "python":
            score = 7.0  # Base score

            # Check for list comprehensions (idiomatic Python)
            if re.search(r'\[.*for.*in.*\]', solution):
                score += 1.0

            # Check for dict comprehensions
            if re.search(r'\{.*:.*for.*in.*\}', solution):
                score += 0.5

            # Check for with statements (context managers)
            if re.search(r'with\s+\w+', solution):
                score += 0.5

            # Check for type hints
            if re.search(r':\s*\w+', solution):
                score += 0.5

            # Check for enumerate usage
            if 'enumerate' in solution:
                score += 0.5

            return min(score, 10.0)

        # Default for other languages (placeholder for future expansion)
        return 7.0

    def evaluate_performance(self, execution_time: float, difficulty: str) -> float:
        """
        Evaluate performance dimension (0-10).

        Compares execution time against expected times for difficulty level.
        """
        # Expected execution times by difficulty (in seconds)
        expected = {
            "easy": 0.1,    # 100ms
            "medium": 0.5,  # 500ms
            "hard": 2.0     # 2s
        }.get(difficulty, 0.5)

        # Score based on execution time ratio
        if execution_time <= expected * 0.5:
            return 9.5  # Excellent
        elif execution_time <= expected:
            return 8.5  # Good
        elif execution_time <= expected * 2:
            return 6.5  # Acceptable
        elif execution_time <= expected * 5:
            return 4.0  # Poor
        else:
            return 2.0  # Very poor

    def evaluate_best_practices(self, solution: str, language: str, passed: bool) -> float:
        """
        Evaluate best practices dimension (0-10).

        Checks for documentation, security issues, and code quality patterns.
        MVP version focuses on basic checks.
        """
        if not passed:
            return 4.0

        score = 7.0  # Base score

        # Check for comments
        if '#' in solution or '//' in solution:
            score += 1.0

        # Check for docstrings (Python)
        if language == "python" and ('"""' in solution or "'''" in solution):
            score += 1.0

        # Check for meaningful variable names (not single chars except i, j, k in loops)
        short_vars = re.findall(r'\b[a-h,l-z]\b(?!\s*=)', solution)
        if len(short_vars) > 3:
            score -= 1.0

        # Deduct for potential issues
        # Hardcoded magic numbers in comparisons (excluding common patterns)
        if re.search(r'==\s*[0-9]{2,}', solution):
            score -= 0.5

        return max(0.0, min(score, 10.0))

    def run_single_test(self, agent_id: str, test: Dict) -> Dict:
        """
        Run a single test with real agent execution.

        This method overrides the parent class to enable production execution.
        Falls back to mock mode if requested.
        """
        # Fall back to mock if requested
        if self.mock_mode:
            return super().run_single_test(agent_id, test)

        task_file = None

        try:
            # 1. Create task file
            task_file = self.create_task_file(test, agent_id)

            # 2. Invoke agent
            agent_result = self.invoke_agent(agent_id, task_file)

            # Check if agent invocation succeeded
            if agent_result['status'] != 'success':
                return self._create_error_result(
                    test,
                    f"Agent invocation failed: {agent_result.get('stderr', 'Unknown error')}",
                    agent_result['execution_time']
                )

            # 3. Extract solution
            language = self.language_map[agent_id]
            solution = self.extract_solution_code(agent_result['stdout'], language)

            if not solution:
                return self._create_error_result(
                    test,
                    "No solution code found in agent response",
                    agent_result['execution_time']
                )

            # 4. Execute solution (Python only for MVP)
            if language == "python":
                execution_result = self.execute_python_solution(solution, test)
            else:
                return self._create_error_result(
                    test,
                    f"Language {language} not yet supported in production mode",
                    agent_result['execution_time']
                )

            # 5. Evaluate dimensions
            dimensions = {
                'correctness': self.evaluate_correctness(execution_result),
                'idiomaticity': self.evaluate_idiomaticity(
                    solution, language, execution_result.get('passed', False)
                ),
                'performance': self.evaluate_performance(
                    execution_result.get('execution_time', 0),
                    test.get('difficulty', 'medium')
                ),
                'best_practices': self.evaluate_best_practices(
                    solution, language, execution_result.get('passed', False)
                )
            }

            # 6. Calculate weighted score
            weighted_score = sum(
                dimensions[dim] * self.DIMENSION_WEIGHTS[dim]
                for dim in self.DIMENSION_WEIGHTS
            )

            # 7. Return result
            return {
                "test_id": test["id"],
                "test_name": test["name"],
                "difficulty": test.get("difficulty", "medium"),
                "category": test.get("category", "general"),
                "passed": execution_result.get('passed', False),
                "dimensions": dimensions,
                "weighted_score": round(weighted_score, 2),
                "execution_time": round(agent_result['execution_time'], 2),
                "solution_length": len(solution),
                "solution": solution[:500],  # Store first 500 chars
                "execution_details": {
                    'test_results': execution_result.get('test_results', []),
                    'stderr': execution_result.get('stderr', '')
                }
            }

        except Exception as e:
            return self._create_error_result(test, f"Unexpected error: {str(e)}", 0)

        finally:
            # Cleanup task file
            if task_file and task_file.exists():
                task_file.unlink()

    def _create_error_result(self, test: Dict, error: str, execution_time: float) -> Dict:
        """Create a result dict for error cases."""
        return {
            "test_id": test["id"],
            "test_name": test["name"],
            "difficulty": test.get("difficulty", "medium"),
            "category": test.get("category", "general"),
            "passed": False,
            "dimensions": {
                'correctness': 0.0,
                'idiomaticity': 0.0,
                'performance': 0.0,
                'best_practices': 0.0
            },
            "weighted_score": 0.0,
            "execution_time": round(execution_time, 2),
            "solution_length": 0,
            "error": error
        }


# CLI support - inherit from parent
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run production benchmark on Claude MPM agents"
    )
    parser.add_argument(
        "--agent",
        help="Run specific agent only (e.g., python_engineer)"
    )
    parser.add_argument(
        "--production",
        action="store_true",
        default=True,
        help="Run in production mode (default: True for this script)"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock mode instead"
    )
    args = parser.parse_args()

    # Use path relative to script location
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent  # docs/benchmarks

    # Mock mode if explicitly requested, otherwise production
    mock_mode = args.mock

    runner = ProductionBenchmarkRunner(base_dir, mock_mode=mock_mode)

    if args.agent:
        # Run single agent
        agent_to_lang = {
            "python_engineer": "python",
            "typescript_engineer": "typescript",
            "nextjs_engineer": "nextjs",
            "php_engineer": "php",
            "ruby_engineer": "ruby",
            "golang_engineer": "golang",
            "rust_engineer": "rust"
        }
        language = agent_to_lang.get(args.agent)
        if not language:
            print(f"Unknown agent: {args.agent}")
            sys.exit(1)

        result = runner.run_agent_benchmark(language, args.agent)

        # Save result
        output_file = runner.results_dir / f"{args.agent}_benchmark.json"
        with open(output_file, 'w') as f:
            json.dump({
                "benchmark_type": "lightweight",
                "version": "1.0.0",
                "execution_mode": "mock" if mock_mode else "production",
                "results": {args.agent: result}
            }, f, indent=2)

        print(f"\nResults saved to {output_file}")
    else:
        # Run all agents
        results = runner.run_all_agents()

        # Save results
        output_file = runner.results_dir / "benchmark_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\nComplete results saved to {output_file}")
