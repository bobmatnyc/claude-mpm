#!/usr/bin/env python3
"""
Comprehensive test script to verify agent functionality after JSON schema fixes.
Tests all aspects of the agent system to ensure full restoration of functionality.
"""

import json
import os
import sys
import traceback
from datetime import datetime, timezone

# Add src to path
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)

from claude_mpm.agents.agent_loader import AgentLoader
from claude_mpm.validation.agent_validator import AgentValidator


class TestResult:
    """Test result container"""

    def __init__(self, name, passed, details="", error=None):
        self.name = name
        self.passed = passed
        self.details = details
        self.error = error
        self.timestamp = datetime.now(timezone.utc)


class AgentFunctionalityTester:
    """Comprehensive agent functionality tester"""

    def __init__(self):
        self.results = []
        self.agent_loader = None
        self.validator = None

    def run_all_tests(self):
        """Run all test suites"""
        print("=== Claude MPM Agent Functionality Test Suite ===")
        print(f"Started at: {datetime.now(timezone.utc)}\n")

        # Test 1: AgentLoader initialization
        self.test_agent_loader_initialization()

        # Test 2: Load all agent templates
        self.test_load_all_templates()

        # Test 3: Validate agent schemas
        self.test_agent_validation()

        # Test 4: Test agent operations
        self.test_agent_operations()

        # Test 5: Test for regressions
        self.test_no_regressions()

        # Generate report
        self.generate_report()

    def test_agent_loader_initialization():
        """Test 1: Verify AgentLoader can initialize without errors"""
        print("\n[TEST 1] Testing AgentLoader initialization...")

        try:
            # Test AgentLoader initialization
            self.agent_loader = AgentLoader()
            self.results.append(
                TestResult(
                    "AgentLoader initialization",
                    True,
                    "Successfully initialized AgentLoader",
                )
            )

            # Verify metrics are available
            if hasattr(self.agent_loader, "get_metrics"):
                metrics = self.agent_loader.get_metrics()
                self.results.append(
                    TestResult(
                        "AgentLoader metrics",
                        True,
                        f"Metrics available: {metrics.get('agents_loaded', 0)} agents loaded",
                    )
                )
            else:
                self.results.append(
                    TestResult("AgentLoader metrics", False, "Metrics not available")
                )

        except Exception as e:
            self.results.append(
                TestResult(
                    "AgentLoader initialization",
                    False,
                    "Failed to initialize AgentLoader",
                    str(e),
                )
            )
            traceback.print_exc()

    def test_load_all_templates():
        """Test 2: Verify all agent templates can be loaded successfully"""
        print("\n[TEST 2] Testing loading of all agent templates...")

        if not self.agent_loader:
            self.results.append(
                TestResult("Load all templates", False, "AgentLoader not initialized")
            )
            return

        agent_types = [
            "engineer_agent",
            "qa_agent",
            "documentation_agent",
            "research_agent",
            "security_agent",
            "ops_agent",
            "data_engineer_agent",
            "version_control_agent",
        ]

        loaded_agents = []
        failed_agents = []

        for agent_type in agent_types:
            try:
                # Load agent template
                agent_data = self.agent_loader.get_agent(agent_type)

                if agent_data:
                    loaded_agents.append(agent_type)

                    # Verify essential fields
                    essential_fields = [
                        "agent_id",
                        "agent_version",
                        "metadata",
                        "capabilities",
                        "instructions",
                    ]
                    missing_fields = [
                        f for f in essential_fields if f not in agent_data
                    ]

                    if missing_fields:
                        self.results.append(
                            TestResult(
                                f"Load {agent_type} agent",
                                False,
                                f"Missing essential fields: {missing_fields}",
                            )
                        )
                    else:
                        self.results.append(
                            TestResult(
                                f"Load {agent_type} agent",
                                True,
                                f"Successfully loaded with version {agent_data.get('agent_version', 'N/A')}",
                            )
                        )
                else:
                    failed_agents.append(agent_type)
                    self.results.append(
                        TestResult(
                            f"Load {agent_type} agent",
                            False,
                            "Failed to load agent data",
                        )
                    )

            except Exception as e:
                failed_agents.append(agent_type)
                self.results.append(
                    TestResult(
                        f"Load {agent_type} agent",
                        False,
                        "Exception during loading",
                        str(e),
                    )
                )

        # Summary
        self.results.append(
            TestResult(
                "Agent loading summary",
                len(failed_agents) == 0,
                f"Loaded: {len(loaded_agents)}/{len(agent_types)} agents. Failed: {failed_agents if failed_agents else 'None'}",
            )
        )

    def test_agent_validation():
        """Test 3: Check that agent validation works correctly"""
        print("\n[TEST 3] Testing agent validation...")

        try:
            # Initialize validator
            self.validator = AgentValidator()
            self.results.append(
                TestResult(
                    "AgentValidator initialization",
                    True,
                    "Successfully initialized AgentValidator",
                )
            )

            # Test validation with a valid agent
            if self.agent_loader:
                try:
                    engineer_data = self.agent_loader.get_agent("engineer_agent")
                    if engineer_data:
                        result = self.validator.validate_agent(engineer_data)
                        self.results.append(
                            TestResult(
                                "Validate valid agent (engineer)",
                                result.is_valid,
                                f"Validation {'passed' if result.is_valid else 'failed'}: {result.errors if result.errors else 'No errors'}",
                            )
                        )
                except Exception as e:
                    self.results.append(
                        TestResult(
                            "Validate valid agent",
                            False,
                            "Exception during validation",
                            str(e),
                        )
                    )

            # Test validation with invalid data
            invalid_agent = {
                "agent_id": "test_invalid",
                # Missing required fields
            }

            result = self.validator.validate_agent(invalid_agent)
            self.results.append(
                TestResult(
                    "Validate invalid agent",
                    not result.is_valid,  # Should be invalid
                    f"Correctly identified as invalid. Errors: {result.errors}",
                )
            )

        except Exception as e:
            self.results.append(
                TestResult(
                    "Agent validation", False, "Failed to test validation", str(e)
                )
            )
            traceback.print_exc()

    def test_agent_operations():
        """Test 4: Run basic agent operations for end-to-end functionality"""
        print("\n[TEST 4] Testing agent operations...")

        if not self.agent_loader:
            self.results.append(
                TestResult("Agent operations", False, "AgentLoader not initialized")
            )
            return

        try:
            # Test listing available agents
            available_agents = self.agent_loader.list_agents()
            self.results.append(
                TestResult(
                    "List available agents",
                    len(available_agents) > 0,
                    f"Found {len(available_agents)} available agents: {', '.join([a.get('id', 'unknown') for a in available_agents[:3]])}...",
                )
            )

            # Test getting agent metadata
            if available_agents:
                agent_type = available_agents[0].get("id", "unknown")
                metadata = self.agent_loader.get_agent_metadata(agent_type)
                self.results.append(
                    TestResult(
                        f"Get metadata for {agent_type}",
                        metadata is not None,
                        f"Retrieved metadata: {metadata.get('name', 'N/A') if metadata else 'None'}",
                    )
                )

            # Test getting agent prompt
            if available_agents:
                agent_type = available_agents[0].get("id")
                prompt = self.agent_loader.get_agent_prompt(agent_type)
                self.results.append(
                    TestResult(
                        f"Get prompt for {agent_type}",
                        prompt is not None,
                        f"Retrieved prompt of length: {len(prompt) if prompt else 0}",
                    )
                )

        except Exception as e:
            self.results.append(
                TestResult(
                    "Agent operations", False, "Failed during operations test", str(e)
                )
            )
            traceback.print_exc()

    def test_no_regressions():
        """Test 5: Ensure no regression in other parts of the system"""
        print("\n[TEST 5] Testing for regressions...")

        try:
            # Test import of key modules
            modules_to_test = [
                ("claude_mpm.agents.agent_loader", "AgentLoader module"),
                ("claude_mpm.validation.agent_validator", "AgentValidator module"),
                ("claude_mpm.services.agent_deployment", "AgentDeployment service"),
                (
                    "claude_mpm.services.agent_lifecycle_manager",
                    "AgentLifecycleManager",
                ),
                (
                    "claude_mpm.services.agent_capabilities_generator",
                    "AgentCapabilitiesGenerator",
                ),
            ]

            for module_name, description in modules_to_test:
                try:
                    __import__(module_name)
                    self.results.append(
                        TestResult(
                            f"Import {description}",
                            True,
                            f"Successfully imported {module_name}",
                        )
                    )
                except ImportError as e:
                    self.results.append(
                        TestResult(
                            f"Import {description}",
                            False,
                            f"Failed to import {module_name}",
                            str(e),
                        )
                    )

            # Test JSON schema file accessibility
            schema_files = [
                "/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/schema/agent_schema.json",
                "/Users/masa/Projects/claude-mpm/src/claude_mpm/schemas/agent_schema.json",
            ]

            for schema_file in schema_files:
                if os.path.exists(schema_file):
                    try:
                        with schema_file.open() as f:
                            schema_data = json.load(f)
                        self.results.append(
                            TestResult(
                                f"Load schema: {os.path.basename(os.path.dirname(schema_file))}/agent_schema.json",
                                True,
                                f"Successfully loaded schema with version {schema_data.get('version', 'N/A')}",
                            )
                        )
                    except Exception as e:
                        self.results.append(
                            TestResult(
                                f"Load schema: {os.path.basename(schema_file)}",
                                False,
                                "Failed to load schema",
                                str(e),
                            )
                        )

        except Exception as e:
            self.results.append(
                TestResult(
                    "Regression tests",
                    False,
                    "Failed during regression testing",
                    str(e),
                )
            )

    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 80)
        print("TEST REPORT SUMMARY")
        print("=" * 80)

        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests

        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests} ({passed_tests / total_tests * 100:.1f}%)")
        print(f"Failed: {failed_tests} ({failed_tests / total_tests * 100:.1f}%)")

        # Group results by test category
        categories = {
            "Initialization": [],
            "Template Loading": [],
            "Validation": [],
            "Operations": [],
            "Regressions": [],
        }

        for result in self.results:
            if "initialization" in result.name.lower():
                categories["Initialization"].append(result)
            elif "load" in result.name.lower() and "agent" in result.name.lower():
                categories["Template Loading"].append(result)
            elif "validat" in result.name.lower():
                categories["Validation"].append(result)
            elif (
                "operation" in result.name.lower()
                or "metadata" in result.name.lower()
                or "list" in result.name.lower()
            ):
                categories["Operations"].append(result)
            else:
                categories["Regressions"].append(result)

        # Print detailed results by category
        for category, results in categories.items():
            if results:
                print(f"\n{category}:")
                print("-" * 40)
                for result in results:
                    status = "✓ PASS" if result.passed else "✗ FAIL"
                    print(f"{status} {result.name}")
                    if result.details:
                        print(f"   Details: {result.details}")
                    if result.error and not result.passed:
                        print(f"   Error: {result.error}")

        # Overall assessment
        print("\n" + "=" * 80)
        print("OVERALL ASSESSMENT:")
        print("=" * 80)

        if failed_tests == 0:
            print("✓ ALL TESTS PASSED - Agent functionality is fully restored!")
            print("  - AgentLoader initializes without errors")
            print("  - All agent templates load successfully")
            print("  - Agent validation works correctly")
            print("  - Basic agent operations function properly")
            print("  - No regressions detected in the system")
        else:
            print("✗ SOME TESTS FAILED - Issues detected:")
            for result in self.results:
                if not result.passed:
                    print(f"  - {result.name}: {result.error or result.details}")

        print("\nTest completed at:", datetime.now(timezone.utc))


if __name__ == "__main__":
    tester = AgentFunctionalityTester()
    tester.run_all_tests()
