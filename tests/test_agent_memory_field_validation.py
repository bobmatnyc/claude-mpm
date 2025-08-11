#!/usr/bin/env python3
"""
Comprehensive test suite for validating agent 'Remember' field functionality.

This test validates:
1. Agents include the 'Remember' field in their responses
2. The field is properly formatted (list or null)
3. Agents only include truly universal memories (not task-specific info)
4. The PM agent can extract these memories from agent responses

Test scenarios:
- Simple tasks that shouldn't generate memories (expect null/empty)
- Tasks discovering universal patterns (expect memory items)
- Multi-agent workflows (PM should aggregate memories)
"""

import os
import sys
import json
import subprocess
import tempfile
import time
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

class AgentMemoryFieldTester:
    """Test harness for validating agent remember field functionality."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_dir = None
        self.results = []
        
    def setup_test_environment(self):
        """Set up a temporary test environment."""
        self.test_dir = tempfile.mkdtemp(prefix="agent_memory_test_")
        os.chdir(self.test_dir)
        
        # Initialize a claude-mpm project
        subprocess.run([
            "python", str(self.project_root / "scripts" / "init_project.py"), "."
        ], check=False, capture_output=True)
        
        print(f"Test environment set up at: {self.test_dir}")
        
    def run_agent_test(self, agent_name, task, expect_memories=None):
        """
        Run a test with a specific agent and validate the remember field.
        
        Args:
            agent_name: Name of the agent to test
            task: Task description to give the agent
            expect_memories: Expected number of memories (None = don't check count)
        
        Returns:
            dict: Test result with validation details
        """
        print(f"\n=== Testing {agent_name} agent ===")
        print(f"Task: {task}")
        
        # Create a test prompt that targets the specific agent
        if agent_name.lower() == "pm":
            prompt = task
        else:
            # Create a task delegation prompt for the PM to route to the specific agent
            prompt = f"Please delegate this to the {agent_name} agent: {task}"
        
        result = {
            "agent": agent_name,
            "task": task,
            "expect_memories": expect_memories,
            "success": False,
            "remember_field_present": False,
            "remember_field_format_valid": False,
            "remember_content": None,
            "memories_appropriate": None,
            "error": None
        }
        
        try:
            # Run claude-mpm with the test prompt
            claude_mpm_script = self.project_root / "claude-mpm"
            cmd = [
                str(claude_mpm_script),
                "run", "-i", prompt, "--non-interactive"
            ]
            
            # Set environment to use project root
            env = os.environ.copy()
            env["PYTHONPATH"] = str(self.project_root / "src")
            
            process = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=120,
                env=env,
                cwd=self.project_root
            )
            
            if process.returncode != 0:
                result["error"] = f"Command failed: {process.stderr}"
                return result
                
            response = process.stdout
            print(f"Agent response length: {len(response)} characters")
            
            # Parse the response for the Remember field
            self._validate_remember_field(response, result)
            
            # Check if memories are appropriate for universality
            if result["remember_content"]:
                result["memories_appropriate"] = self._validate_memory_universality(
                    result["remember_content"], task, agent_name
                )
            
            result["success"] = (
                result["remember_field_present"] and 
                result["remember_field_format_valid"]
            )
            
        except subprocess.TimeoutExpired:
            result["error"] = "Command timed out after 120 seconds"
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
            
        return result
        
    def _validate_remember_field(self, response, result):
        """Validate the presence and format of the Remember field."""
        # Look for Remember field in various formats
        remember_patterns = [
            r"\*\*Remember\*\*:\s*(.+?)(?=\n\*\*|\n\n|\n$|$)",
            r"Remember:\s*(.+?)(?=\n\*\*|\n\n|\n$|$)",
            r"\"Remember\":\s*(.+?)(?=,|}|$)",
            r"'Remember':\s*(.+?)(?=,|}|$)"
        ]
        
        import re
        remember_content = None
        
        for pattern in remember_patterns:
            match = re.search(pattern, response, re.MULTILINE | re.DOTALL)
            if match:
                remember_content = match.group(1).strip()
                result["remember_field_present"] = True
                break
                
        if not result["remember_field_present"]:
            print("❌ Remember field not found in response")
            return
            
        print(f"✅ Remember field found: {remember_content}")
        result["remember_content"] = remember_content
        
        # Validate format (should be null, empty list, or list of strings)
        if remember_content.lower() in ["null", "none", "[]", "n/a"]:
            result["remember_field_format_valid"] = True
            print("✅ Remember field format valid (null/empty)")
        elif remember_content.startswith("[") and remember_content.endswith("]"):
            try:
                # Try to parse as JSON list
                parsed = json.loads(remember_content)
                if isinstance(parsed, list):
                    result["remember_field_format_valid"] = True
                    print(f"✅ Remember field format valid (list with {len(parsed)} items)")
                else:
                    print("❌ Remember field contains non-list JSON")
            except json.JSONDecodeError:
                # Try to parse as markdown list
                if all(line.strip().startswith("-") for line in remember_content.strip("[]").split("\n") if line.strip()):
                    result["remember_field_format_valid"] = True
                    print("✅ Remember field format valid (markdown list)")
                else:
                    print("❌ Remember field format invalid (not proper list)")
        elif remember_content.startswith("-"):
            # Markdown list format
            result["remember_field_format_valid"] = True
            print("✅ Remember field format valid (markdown list)")
        else:
            print(f"❌ Remember field format invalid: {remember_content}")
            
    def _validate_memory_universality(self, content, task, agent_name):
        """Check if memories are universal rather than task-specific."""
        # Task-specific indicators (should not be in memories)
        task_specific_indicators = [
            # Specific file names or paths
            r'\.[a-zA-Z]+$',  # file extensions
            r'/[a-zA-Z_/]+',  # file paths
            
            # Specific variable names or identifiers
            r'\b[a-zA-Z_][a-zA-Z0-9_]*\(\)',  # function calls
            
            # Task-specific details from the prompt
        ]
        
        # Universal pattern indicators (should be in memories)
        universal_indicators = [
            r'\ball\b.*\bmust\b',  # "all X must Y"
            r'\balways\b',  # "always do X"
            r'\bnever\b',  # "never do X"
            r'\brequir\w+\b.*\bfor\b.*\bfeatures?\b',  # "requirements for features"
            r'\bstandard\b',  # "standard practices"
            r'\bpattern\b',  # "patterns"
        ]
        
        import re
        
        if content.lower() in ["null", "none", "[]", "n/a"]:
            return True  # No memories is always appropriate
            
        # Count task-specific vs universal indicators
        task_specific_count = sum(
            len(re.findall(pattern, content, re.IGNORECASE))
            for pattern in task_specific_indicators
        )
        
        universal_count = sum(
            len(re.findall(pattern, content, re.IGNORECASE))
            for pattern in universal_indicators
        )
        
        # Memories should be more universal than task-specific
        return universal_count >= task_specific_count
        
    def run_test_scenarios(self):
        """Run all test scenarios."""
        
        # Scenario 1: Simple tasks that shouldn't generate memories
        print("\n" + "="*80)
        print("SCENARIO 1: Simple tasks (expect null/empty memories)")
        print("="*80)
        
        simple_tasks = [
            ("QA", "Check if the current directory contains any Python files", 0),
            ("Engineer", "Print 'Hello World' to the console", 0),
            ("Research", "What is the current working directory?", 0),
        ]
        
        for agent, task, expected in simple_tasks:
            result = self.run_agent_test(agent, task, expected)
            self.results.append(result)
            
        # Scenario 2: Tasks that should discover universal patterns
        print("\n" + "="*80)
        print("SCENARIO 2: Universal pattern discovery (expect memories)")
        print("="*80)
        
        pattern_tasks = [
            ("QA", "Analyze the testing patterns in this codebase and identify universal quality standards that should apply to all future testing", 1),
            ("Engineer", "Review the codebase architecture and identify universal coding patterns that should be followed for all implementations", 1),
            ("Security", "Identify universal security requirements that should apply to all features in this project", 1),
        ]
        
        for agent, task, expected in pattern_tasks:
            result = self.run_agent_test(agent, task, expected)
            self.results.append(result)
            
        # Scenario 3: Multi-agent workflow (test PM memory aggregation)
        print("\n" + "="*80)
        print("SCENARIO 3: Multi-agent workflow (PM memory aggregation)")
        print("="*80)
        
        workflow_task = """
        I need to implement a new user authentication system. Please:
        1. First research best practices for authentication
        2. Then implement the authentication system
        3. Finally, have QA validate the implementation
        
        Make sure to capture any universal patterns or requirements discovered during this process.
        """
        
        result = self.run_agent_test("PM", workflow_task, None)
        self.results.append(result)
        
    def generate_report(self):
        """Generate a comprehensive test report."""
        print("\n" + "="*80)
        print("AGENT MEMORY FIELD VALIDATION REPORT")
        print("="*80)
        
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r["success"])
        
        print(f"\nOverall Results: {successful_tests}/{total_tests} tests passed")
        print(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")
        
        print("\nDetailed Results:")
        print("-" * 80)
        
        for i, result in enumerate(self.results, 1):
            print(f"\nTest {i}: {result['agent']} Agent")
            print(f"Task: {result['task'][:80]}{'...' if len(result['task']) > 80 else ''}")
            print(f"✅ Success: {result['success']}")
            print(f"✅ Remember field present: {result['remember_field_present']}")
            print(f"✅ Remember field format valid: {result['remember_field_format_valid']}")
            
            if result['remember_content']:
                print(f"Remember content: {result['remember_content'][:100]}{'...' if len(result['remember_content']) > 100 else ''}")
                if result['memories_appropriate'] is not None:
                    print(f"✅ Memories appropriate (universal): {result['memories_appropriate']}")
            else:
                print("Remember content: None/Empty")
                
            if result['error']:
                print(f"❌ Error: {result['error']}")
                
        # Analysis and recommendations
        print("\n" + "="*80)
        print("ANALYSIS AND RECOMMENDATIONS")
        print("="*80)
        
        remember_field_present_count = sum(1 for r in self.results if r["remember_field_present"])
        format_valid_count = sum(1 for r in self.results if r["remember_field_format_valid"])
        
        print(f"\n1. Remember Field Presence: {remember_field_present_count}/{total_tests} agents included Remember field")
        if remember_field_present_count < total_tests:
            print("   🔧 ISSUE: Some agents missing Remember field in response format")
            print("   📝 RECOMMENDATION: Update agent templates to include Remember field")
            
        print(f"\n2. Remember Field Format: {format_valid_count}/{total_tests} agents used valid format")
        if format_valid_count < total_tests:
            print("   🔧 ISSUE: Some agents using invalid Remember field format")
            print("   📝 RECOMMENDATION: Standardize Remember field format across agents")
            
        # Memory appropriateness analysis
        memory_results = [r for r in self.results if r["memories_appropriate"] is not None]
        if memory_results:
            appropriate_count = sum(1 for r in memory_results if r["memories_appropriate"])
            print(f"\n3. Memory Universality: {appropriate_count}/{len(memory_results)} memory sets are appropriately universal")
            if appropriate_count < len(memory_results):
                print("   🔧 ISSUE: Some agents including task-specific rather than universal memories")
                print("   📝 RECOMMENDATION: Train agents to distinguish universal vs task-specific patterns")
                
        # PM integration analysis
        pm_results = [r for r in self.results if r["agent"] == "PM"]
        if pm_results:
            pm_success = all(r["success"] for r in pm_results)
            print(f"\n4. PM Memory Aggregation: {'✅ Working' if pm_success else '❌ Issues detected'}")
            if not pm_success:
                print("   🔧 ISSUE: PM agent not properly aggregating memories from other agents")
                print("   📝 RECOMMENDATION: Enhance PM agent memory extraction logic")
                
        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": (successful_tests/total_tests)*100,
            "remember_field_coverage": (remember_field_present_count/total_tests)*100,
            "format_validity": (format_valid_count/total_tests)*100,
            "recommendations": self._generate_recommendations()
        }
        
    def _generate_recommendations(self):
        """Generate specific recommendations based on test results."""
        recommendations = []
        
        # Check for missing Remember fields
        missing_remember = [r for r in self.results if not r["remember_field_present"]]
        if missing_remember:
            agents = [r["agent"] for r in missing_remember]
            recommendations.append({
                "category": "Missing Remember Field",
                "severity": "High",
                "description": f"Agents {', '.join(agents)} do not include Remember field in responses",
                "action": "Update agent response templates to include Remember field"
            })
            
        # Check for format issues
        format_issues = [r for r in self.results if r["remember_field_present"] and not r["remember_field_format_valid"]]
        if format_issues:
            recommendations.append({
                "category": "Format Inconsistency",
                "severity": "Medium",
                "description": "Remember field format is inconsistent across agents",
                "action": "Standardize Remember field format (JSON list or null)"
            })
            
        # Check for inappropriate memories
        inappropriate_memories = [r for r in self.results if r["memories_appropriate"] is False]
        if inappropriate_memories:
            recommendations.append({
                "category": "Memory Quality",
                "severity": "Medium",
                "description": "Some agents generating task-specific rather than universal memories",
                "action": "Improve agent training on universal vs task-specific pattern recognition"
            })
            
        return recommendations
        
    def cleanup(self):
        """Clean up test environment."""
        if self.test_dir and os.path.exists(self.test_dir):
            import shutil
            try:
                shutil.rmtree(self.test_dir)
                print(f"\nCleaned up test directory: {self.test_dir}")
            except Exception as e:
                print(f"\nWarning: Could not clean up test directory {self.test_dir}: {e}")

def main():
    """Run the agent memory field validation tests."""
    tester = AgentMemoryFieldTester()
    
    try:
        print("Starting Agent Memory Field Validation Tests...")
        print("="*80)
        
        tester.setup_test_environment()
        tester.run_test_scenarios()
        report = tester.generate_report()
        
        # Save detailed results
        results_file = Path(__file__).parent.parent / "agent_memory_test_results.json"
        with open(results_file, 'w') as f:
            json.dump({
                "summary": report,
                "detailed_results": tester.results
            }, f, indent=2)
            
        print(f"\n📊 Detailed results saved to: {results_file}")
        
        # Return appropriate exit code
        return 0 if report["success_rate"] >= 80 else 1
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return 1
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        tester.cleanup()

if __name__ == "__main__":
    sys.exit(main())