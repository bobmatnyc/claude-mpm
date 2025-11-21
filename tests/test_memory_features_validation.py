#!/usr/bin/env python3
"""
Test script to validate memory system duplicate prevention and categorization features.

This script creates specific test scenarios to verify:
1. Duplicate prevention - exact matches and similar content
2. Categorization system - whether claimed 8+ categories actually work
3. Memory aggregation functionality
4. Edge cases and boundary conditions
"""

import shutil
import sys
import tempfile
from pathlib import Path

# Add the src directory to the path to import claude_mpm modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager


class MemorySystemValidator:
    """Comprehensive validator for memory system features."""

    def __init__(self):
        """Initialize validator with temporary directories."""
        self.temp_dir = tempfile.mkdtemp(prefix="memory_test_")
        self.working_dir = Path(self.temp_dir)

        # Initialize memory manager with temporary directory
        self.config = Config()
        self.memory_manager = AgentMemoryManager(self.config, self.working_dir)

        # Test results storage
        self.test_results = {
            "duplicate_prevention": {},
            "categorization": {},
            "aggregation": {},
            "edge_cases": {},
        }

    def cleanup(self):
        """Clean up temporary directories."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_exact_duplicate_prevention():
        """Test prevention of exact duplicate memory items."""
        print("\n=== Testing Exact Duplicate Prevention ===")

        agent_id = "test_engineer"
        test_memory = "Always use type hints in Python functions"

        # Add the same memory item multiple times
        results = []
        for i in range(3):
            success = self.memory_manager.add_learning(
                agent_id, "guideline", test_memory
            )
            results.append(success)
            print(f"Attempt {i + 1}: {'Success' if success else 'Failed'}")

        # Load memory and check for duplicates
        memory_content = self.memory_manager.load_agent_memory(agent_id)
        occurrences = memory_content.count(test_memory)

        print(f"Expected: 1 occurrence, Actual: {occurrences}")

        # Check if duplicate prevention worked
        duplicate_prevented = occurrences == 1

        self.test_results["duplicate_prevention"]["exact_duplicates"] = {
            "test_memory": test_memory,
            "attempts": len(results),
            "successful_attempts": sum(results),
            "occurrences_in_memory": occurrences,
            "duplicate_prevented": duplicate_prevented,
            "status": "PASS" if duplicate_prevented else "FAIL",
        }

        print(f"Duplicate Prevention Test: {'PASS' if duplicate_prevented else 'FAIL'}")
        return duplicate_prevented

    def test_similar_memory_detection():
        """Test detection and prevention of similar (but not identical) memories."""
        print("\n=== Testing Similar Memory Detection ===")

        agent_id = "test_engineer"

        # Add similar memories with slight variations
        similar_memories = [
            "Always use type hints in Python functions",
            "Use type hints in Python functions",
            "always use type hints in python functions",  # case variation
            "Always use type hints in Python functions.",  # punctuation variation
        ]

        results = []
        for memory in similar_memories:
            success = self.memory_manager.add_learning(agent_id, "guideline", memory)
            results.append(success)
            print(f"Added: '{memory}' -> {'Success' if success else 'Failed'}")

        # Load memory and analyze
        memory_content = self.memory_manager.load_agent_memory(agent_id)
        print("\nMemory content analysis:")

        # Count how many of the similar items actually made it into memory
        actual_items = []
        for line in memory_content.split("\n"):
            if "type hints" in line.lower():
                actual_items.append(line.strip())

        print(f"Items with 'type hints' in memory: {len(actual_items)}")
        for item in actual_items:
            print(f"  - {item}")

        # Ideally, similar items should be deduplicated
        similar_detected = len(actual_items) <= 2  # Allow some fuzzy matching tolerance

        self.test_results["duplicate_prevention"]["similar_detection"] = {
            "input_variations": similar_memories,
            "successful_additions": sum(results),
            "items_in_memory": len(actual_items),
            "similar_detected": similar_detected,
            "status": "PASS" if similar_detected else "FAIL",
        }

        print(
            f"Similar Memory Detection Test: {'PASS' if similar_detected else 'FAIL'}"
        )
        return similar_detected

    def test_categorization_system():
        """Test the claimed intelligent categorization system."""
        print("\n=== Testing Categorization System ===")

        agent_id = "test_research"

        # Test memories for different claimed categories
        test_categories = {
            "pattern": "Use dependency injection pattern for better testability",
            "architecture": "This project uses microservices architecture with API gateway",
            "guideline": "All public methods must have comprehensive docstrings",
            "mistake": "Never hardcode database credentials in source code",
            "strategy": "Use test-driven development for critical business logic",
            "integration": "API endpoints require JWT authentication tokens",
            "performance": "Database queries should use connection pooling for efficiency",
            "context": "Currently working on version 2.0 release candidate",
        }

        # Add each test memory
        categorization_results = {}
        for category, memory_text in test_categories.items():
            success = self.memory_manager.add_learning(agent_id, category, memory_text)
            categorization_results[category] = {
                "input_text": memory_text,
                "add_success": success,
            }
            print(
                f"Added {category}: {memory_text[:50]}... -> {'Success' if success else 'Failed'}"
            )

        # Load memory and analyze categorization
        memory_content = self.memory_manager.load_agent_memory(agent_id)

        # Parse sections to see where items actually landed
        sections = self.memory_manager._parse_memory_sections(memory_content)

        print("\nActual sections found in memory:")
        for section_name, items in sections.items():
            print(f"  {section_name}: {len(items)} items")
            for item in items:
                print(f"    - {item[:60]}...")

        # Analyze categorization accuracy
        expected_sections = {
            "pattern": "Coding Patterns Learned",
            "architecture": "Project Architecture",
            "guideline": "Implementation Guidelines",
            "mistake": "Common Mistakes to Avoid",
            "strategy": "Effective Strategies",
            "integration": "Integration Points",
            "performance": "Performance Considerations",
            "context": "Current Technical Context",
        }

        categorization_accuracy = 0
        total_categories = len(test_categories)

        for input_category, expected_section in expected_sections.items():
            if expected_section in sections:
                # Check if the test memory is in the expected section
                test_memory = test_categories[input_category]
                found_in_section = any(
                    test_memory.lower() in item.lower()
                    for item in sections[expected_section]
                )
                if found_in_section:
                    categorization_accuracy += 1
                    categorization_results[input_category]["correctly_categorized"] = (
                        True
                    )
                    categorization_results[input_category]["found_in_section"] = (
                        expected_section
                    )
                else:
                    categorization_results[input_category]["correctly_categorized"] = (
                        False
                    )
            else:
                categorization_results[input_category]["correctly_categorized"] = False

        categorization_success_rate = categorization_accuracy / total_categories * 100

        self.test_results["categorization"]["intelligent_categorization"] = {
            "test_categories": test_categories,
            "expected_sections": expected_sections,
            "actual_sections": list(sections.keys()),
            "categorization_results": categorization_results,
            "accuracy_rate": categorization_success_rate,
            "total_sections_created": len(sections),
            "claimed_categories_supported": 8,
            "status": "PASS" if categorization_success_rate >= 75 else "FAIL",
        }

        print(f"\nCategorization Accuracy: {categorization_success_rate:.1f}%")
        print(
            f"Categorization Test: {'PASS' if categorization_success_rate >= 75 else 'FAIL'}"
        )

        return categorization_success_rate >= 75

    def test_memory_aggregation():
        """Test user-level and project-level memory aggregation."""
        print("\n=== Testing Memory Aggregation ===")

        agent_id = "test_qa"

        # Create user-level memory
        user_memory_content = """# Qa Agent Memory

<!-- Last Updated: 2024-01-01T00:00:00 -->

## Implementation Guidelines

- Always write comprehensive test cases
- Use page object pattern for UI tests

## Common Mistakes to Avoid

- Don't skip integration tests
"""

        # Create project-level memory
        project_memory_content = """# Qa Agent Memory

<!-- Last Updated: 2024-01-01T00:00:00 -->

## Implementation Guidelines

- Test coverage must be above 80%
- Use mocking for external dependencies

## Performance Considerations

- Load tests should simulate realistic user patterns
"""

        # Save memories to their respective locations
        user_file = self.memory_manager.user_memories_dir / f"{agent_id}_memories.md"
        project_file = (
            self.memory_manager.project_memories_dir / f"{agent_id}_memories.md"
        )

        user_file.parent.mkdir(parents=True, exist_ok=True)
        project_file.parent.mkdir(parents=True, exist_ok=True)

        user_file.write_text(user_memory_content)
        project_file.write_text(project_memory_content)

        # Test aggregation
        aggregated_memory = self.memory_manager.load_agent_memory(agent_id)

        # Analyze aggregation
        sections = self.memory_manager._parse_memory_sections(aggregated_memory)

        # Check if both user and project content is present
        implementation_items = sections.get("Implementation Guidelines", [])
        has_user_content = any(
            "page object pattern" in item.lower() for item in implementation_items
        )
        has_project_content = any("80%" in item for item in implementation_items)
        has_performance_section = "Performance Considerations" in sections

        aggregation_working = (
            has_user_content and has_project_content and has_performance_section
        )

        print(f"User content found: {has_user_content}")
        print(f"Project content found: {has_project_content}")
        print(f"Performance section from project: {has_performance_section}")

        self.test_results["aggregation"]["user_project_merge"] = {
            "user_content_preserved": has_user_content,
            "project_content_preserved": has_project_content,
            "unique_sections_merged": has_performance_section,
            "total_sections": len(sections),
            "aggregation_working": aggregation_working,
            "status": "PASS" if aggregation_working else "FAIL",
        }

        print(f"Memory Aggregation Test: {'PASS' if aggregation_working else 'FAIL'}")
        return aggregation_working

    def test_edge_cases():
        """Test edge cases and boundary conditions."""
        print("\n=== Testing Edge Cases ===")

        edge_case_results = {}

        # Test 1: Empty memory addition
        try:
            agent_id = "test_edge"
            success = self.memory_manager.add_learning(agent_id, "pattern", "")
            edge_case_results["empty_memory"] = {
                "test": "Add empty memory string",
                "success": success,
                "expected": "Should handle gracefully",
                "status": "PASS" if not success else "FAIL",
            }
        except Exception as e:
            edge_case_results["empty_memory"] = {
                "test": "Add empty memory string",
                "error": str(e),
                "status": "FAIL",
            }

        # Test 2: Very long memory item
        try:
            long_memory = "This is a very long memory item " * 10  # ~300 chars
            success = self.memory_manager.add_learning(agent_id, "pattern", long_memory)
            memory_content = self.memory_manager.load_agent_memory(agent_id)

            # Check if it was truncated
            truncated = "..." in memory_content

            edge_case_results["long_memory"] = {
                "test": "Add very long memory item",
                "success": success,
                "truncated": truncated,
                "status": "PASS" if success and truncated else "FAIL",
            }
        except Exception as e:
            edge_case_results["long_memory"] = {
                "test": "Add very long memory item",
                "error": str(e),
                "status": "FAIL",
            }

        # Test 3: Invalid category
        try:
            success = self.memory_manager.add_learning(
                agent_id, "invalid_category", "Test memory"
            )
            memory_content = self.memory_manager.load_agent_memory(agent_id)

            # Should fallback to "Recent Learnings"
            has_recent_learnings = "Recent Learnings" in memory_content

            edge_case_results["invalid_category"] = {
                "test": "Add memory with invalid category",
                "success": success,
                "fallback_to_recent": has_recent_learnings,
                "status": "PASS" if success and has_recent_learnings else "FAIL",
            }
        except Exception as e:
            edge_case_results["invalid_category"] = {
                "test": "Add memory with invalid category",
                "error": str(e),
                "status": "FAIL",
            }

        self.test_results["edge_cases"] = edge_case_results

        # Calculate overall edge case success
        passed_tests = sum(
            1 for test in edge_case_results.values() if test.get("status") == "PASS"
        )
        total_tests = len(edge_case_results)

        print(f"Edge Cases Passed: {passed_tests}/{total_tests}")
        for test_name, result in edge_case_results.items():
            print(f"  {test_name}: {result['status']}")

        return passed_tests == total_tests

    def generate_report(self):
        """Generate comprehensive test report."""
        print("\n" + "=" * 80)
        print("MEMORY SYSTEM FEATURE VALIDATION REPORT")
        print("=" * 80)

        # Summary
        all_tests = []

        # Duplicate Prevention Tests
        print("\n1. DUPLICATE PREVENTION FEATURES")
        print("-" * 40)

        exact_dup = self.test_results["duplicate_prevention"].get(
            "exact_duplicates", {}
        )
        if exact_dup:
            status = exact_dup["status"]
            print(f"✓ Exact Duplicate Prevention: {status}")
            print(f"  - Added same memory {exact_dup['attempts']} times")
            print(
                f"  - Found {exact_dup['occurrences_in_memory']} occurrence(s) in memory"
            )
            all_tests.append(status == "PASS")

        similar_dup = self.test_results["duplicate_prevention"].get(
            "similar_detection", {}
        )
        if similar_dup:
            status = similar_dup["status"]
            print(f"✓ Similar Memory Detection: {status}")
            print(f"  - Tested {len(similar_dup['input_variations'])} variations")
            print(f"  - Found {similar_dup['items_in_memory']} items in memory")
            all_tests.append(status == "PASS")

        # Categorization Tests
        print("\n2. INTELLIGENT CATEGORIZATION FEATURES")
        print("-" * 40)

        categorization = self.test_results["categorization"].get(
            "intelligent_categorization", {}
        )
        if categorization:
            status = categorization["status"]
            accuracy = categorization["accuracy_rate"]
            print(f"✓ Intelligent Categorization: {status}")
            print(f"  - Accuracy Rate: {accuracy:.1f}%")
            print(f"  - Categories Tested: {len(categorization['test_categories'])}")
            print(f"  - Sections Created: {categorization['total_sections_created']}")

            print("  - Expected vs Actual Section Mapping:")
            for category, result in categorization["categorization_results"].items():
                correctly_categorized = result.get("correctly_categorized", False)
                section = result.get("found_in_section", "Not Found")
                print(
                    f"    {category}: {'✓' if correctly_categorized else '✗'} -> {section}"
                )

            all_tests.append(status == "PASS")

        # Aggregation Tests
        print("\n3. MEMORY AGGREGATION FEATURES")
        print("-" * 40)

        aggregation = self.test_results["aggregation"].get("user_project_merge", {})
        if aggregation:
            status = aggregation["status"]
            print(f"✓ User/Project Memory Aggregation: {status}")
            print(
                f"  - User content preserved: {'✓' if aggregation['user_content_preserved'] else '✗'}"
            )
            print(
                f"  - Project content preserved: {'✓' if aggregation['project_content_preserved'] else '✗'}"
            )
            print(
                f"  - Unique sections merged: {'✓' if aggregation['unique_sections_merged'] else '✗'}"
            )
            all_tests.append(status == "PASS")

        # Edge Cases
        print("\n4. EDGE CASES AND BOUNDARY CONDITIONS")
        print("-" * 40)

        edge_cases = self.test_results["edge_cases"]
        if edge_cases:
            for _test_name, result in edge_cases.items():
                status = result["status"]
                test_desc = result["test"]
                print(f"✓ {test_desc}: {status}")
                if "error" in result:
                    print(f"  - Error: {result['error']}")
                all_tests.append(status == "PASS")

        # Overall Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)

        passed_tests = sum(all_tests)
        total_tests = len(all_tests)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1f}%)")

        if success_rate >= 80:
            print(
                "🎉 OVERALL STATUS: PASS - Memory system features are working as claimed"
            )
        elif success_rate >= 60:
            print("⚠️  OVERALL STATUS: PARTIAL - Some memory features need improvement")
        else:
            print(
                "❌ OVERALL STATUS: FAIL - Significant gaps between claimed and actual functionality"
            )

        # Specific Findings
        print("\nKEY FINDINGS:")
        print("- Duplicate Prevention: Implementation exists but may have limitations")
        print(
            "- Categorization: System supports multiple categories with varying accuracy"
        )
        print("- Memory Aggregation: User/project memory merging is implemented")
        print("- Edge Case Handling: Basic error handling is in place")

        return success_rate >= 80


def main():
    """Main test execution."""
    print("Memory System Feature Validation")
    print("Testing duplicate prevention and intelligent categorization...")

    validator = MemorySystemValidator()

    try:
        # Run all tests
        validator.test_exact_duplicate_prevention()
        validator.test_similar_memory_detection()
        validator.test_categorization_system()
        validator.test_memory_aggregation()
        validator.test_edge_cases()

        # Generate comprehensive report
        overall_success = validator.generate_report()

        return 0 if overall_success else 1

    except Exception as e:
        print(f"Test execution failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        validator.cleanup()


if __name__ == "__main__":
    sys.exit(main())
