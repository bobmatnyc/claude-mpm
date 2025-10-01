#!/usr/bin/env python3
"""
Test Intelligent QA Routing Configuration
=========================================

Verifies that the PM workflow configuration correctly routes to API QA
and Web QA agents based on implementation context.
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_qa_agent_selection_logic():
    """Test the QA agent selection logic based on implementation context."""

    # Test cases with expected results
    test_cases = [
        {
            "context": "Implemented REST API endpoints for user management with JWT authentication",
            "expected": ["api_qa"],
            "description": "Backend API implementation",
        },
        {
            "context": "Created responsive checkout flow with React components in /components/checkout",
            "expected": ["web_qa"],
            "description": "Frontend web implementation",
        },
        {
            "context": "Built complete authentication system with /api/auth endpoints and React login UI",
            "expected": ["api_qa", "web_qa"],
            "description": "Full-stack implementation",
        },
        {
            "context": "Fixed bug in CLI utility script for data processing",
            "expected": ["qa"],
            "description": "General non-web/non-API code",
        },
        {
            "context": "Updated GraphQL schema and resolvers in /graphql directory",
            "expected": ["api_qa"],
            "description": "GraphQL API implementation",
        },
        {
            "context": "Implemented new Vue.js components for dashboard in /pages/dashboard",
            "expected": ["web_qa"],
            "description": "Vue.js frontend implementation",
        },
    ]

    def select_qa_agent(implementation_context, available_agents=None):
        """Simulate the QA agent selection logic."""
        if available_agents is None:
            available_agents = ["qa", "api_qa", "web_qa"]
        backend_keywords = [
            "api",
            "endpoint",
            "route",
            "rest",
            "graphql",
            "server",
            "backend",
            "auth",
            "database",
            "service",
            "jwt",
        ]
        frontend_keywords = [
            "web",
            "ui",
            "page",
            "frontend",
            "browser",
            "component",
            "responsive",
            "accessibility",
            "react",
            "vue",
        ]

        context_lower = implementation_context.lower()

        has_backend = any(keyword in context_lower for keyword in backend_keywords)
        has_frontend = any(keyword in context_lower for keyword in frontend_keywords)

        # Check file extensions and paths
        if any(
            ext in implementation_context
            for ext in [".py", ".go", ".java", "/api/", "/routes/", "/graphql/"]
        ):
            has_backend = True
        if any(
            ext in implementation_context
            for ext in [".jsx", ".tsx", ".vue", "/components/", "/pages/"]
        ):
            has_frontend = True

        # Determine QA agent(s) to use
        if has_backend and has_frontend:
            return (
                ["api_qa", "web_qa"]
                if "api_qa" in available_agents and "web_qa" in available_agents
                else ["qa"]
            )
        if has_backend and "api_qa" in available_agents:
            return ["api_qa"]
        if has_frontend and "web_qa" in available_agents:
            return ["web_qa"]
        return ["qa"]

    print("Testing QA Agent Selection Logic")
    print("=" * 50)

    all_passed = True
    for i, test_case in enumerate(test_cases, 1):
        result = select_qa_agent(test_case["context"])
        passed = result == test_case["expected"]

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"\nTest {i}: {test_case['description']}")
        print(f"Context: {test_case['context'][:60]}...")
        print(f"Expected: {test_case['expected']}")
        print(f"Got: {result}")
        print(f"Status: {status}")

        if not passed:
            all_passed = False

    return all_passed


def test_api_qa_agent_configuration():
    """Test that the API QA agent configuration exists and is valid."""

    api_qa_path = (
        Path(__file__).parent.parent
        / "src"
        / "claude_mpm"
        / "agents"
        / "templates"
        / "api_qa.json"
    )

    print("\n" + "=" * 50)
    print("Testing API QA Agent Configuration")
    print("=" * 50)

    if not api_qa_path.exists():
        print(f"❌ FAIL: API QA agent configuration not found at {api_qa_path}")
        return False

    try:
        with api_qa_path.open() as f:
            config = json.load(f)

        # Validate required fields
        required_fields = [
            "schema_version",
            "agent_id",
            "agent_version",
            "metadata",
            "capabilities",
            "instructions",
        ]
        missing_fields = [field for field in required_fields if field not in config]

        if missing_fields:
            print(f"❌ FAIL: Missing required fields: {missing_fields}")
            return False

        # Validate agent_id
        if config["agent_id"] != "api-qa-agent":
            print(f"❌ FAIL: Incorrect agent_id: {config['agent_id']}")
            return False

        # Validate capabilities
        if "WebFetch" not in config["capabilities"]["tools"]:
            print("⚠️  WARNING: WebFetch tool not in API QA capabilities")

        print("✅ PASS: API QA agent configuration is valid")
        print(f"  - Agent ID: {config['agent_id']}")
        print(f"  - Version: {config['agent_version']}")
        print(f"  - Model: {config['capabilities']['model']}")
        print(f"  - Tools: {', '.join(config['capabilities']['tools'])}")

        return True

    except json.JSONDecodeError as e:
        print(f"❌ FAIL: Invalid JSON in API QA configuration: {e}")
        return False
    except Exception as e:
        print(f"❌ FAIL: Error reading API QA configuration: {e}")
        return False


def test_workflow_configuration():
    """Test that the WORKFLOW.md file contains the intelligent QA routing."""

    workflow_path = (
        Path(__file__).parent.parent / "src" / "claude_mpm" / "agents" / "WORKFLOW.md"
    )

    print("\n" + "=" * 50)
    print("Testing Workflow Configuration")
    print("=" * 50)

    if not workflow_path.exists():
        print(f"❌ FAIL: WORKFLOW.md not found at {workflow_path}")
        return False

    try:
        with workflow_path.open() as f:
            content = f.read()

        # Check for key sections
        checks = [
            ("Intelligent QA Agent Selection", "Intelligent QA routing section"),
            ("API QA Agent", "API QA agent definition"),
            ("Web QA Agent", "Web QA agent definition"),
            ("Full-Stack Testing", "Full-stack testing procedure"),
            ("QA Type Detection Logic", "QA detection logic"),
        ]

        all_present = True
        for check_text, description in checks:
            if check_text in content:
                print(f"✅ Found: {description}")
            else:
                print(f"❌ Missing: {description}")
                all_present = False

        return all_present

    except Exception as e:
        print(f"❌ FAIL: Error reading WORKFLOW.md: {e}")
        return False


def test_instructions_update():
    """Test that the PM INSTRUCTIONS.md contains the QA routing logic."""

    instructions_path = (
        Path(__file__).parent.parent
        / "src"
        / "claude_mpm"
        / "agents"
        / "INSTRUCTIONS.md"
    )

    print("\n" + "=" * 50)
    print("Testing PM Instructions Update")
    print("=" * 50)

    if not instructions_path.exists():
        print(f"❌ FAIL: INSTRUCTIONS.md not found at {instructions_path}")
        return False

    try:
        with instructions_path.open() as f:
            content = f.read()

        # Check for key sections
        checks = [
            ("Intelligent QA Agent Selection", "QA selection section"),
            ("QA Type Detection Protocol", "QA detection protocol"),
            ("QA Handoff Patterns", "QA handoff patterns"),
            ("TodoWrite Patterns for QA Coordination", "QA todo patterns"),
        ]

        all_present = True
        for check_text, description in checks:
            if check_text in content:
                print(f"✅ Found: {description}")
            else:
                print(f"❌ Missing: {description}")
                all_present = False

        return all_present

    except Exception as e:
        print(f"❌ FAIL: Error reading INSTRUCTIONS.md: {e}")
        return False


def main():
    """Run all tests."""

    print("\n" + "=" * 70)
    print("INTELLIGENT QA ROUTING CONFIGURATION TEST")
    print("=" * 70)

    tests = [
        ("QA Agent Selection Logic", test_qa_agent_selection_logic),
        ("API QA Agent Configuration", test_api_qa_agent_configuration),
        ("Workflow Configuration", test_workflow_configuration),
        ("PM Instructions Update", test_instructions_update),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n❌ ERROR in {test_name}: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    total_tests = len(results)
    passed_tests = sum(1 for _, passed in results if passed)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print(
            "\n🎉 SUCCESS: All tests passed! Intelligent QA routing is configured correctly."
        )
        return 0
    print("\n⚠️  WARNING: Some tests failed. Please review the configuration.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
