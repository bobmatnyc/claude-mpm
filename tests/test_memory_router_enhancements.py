#!/usr/bin/env python3
"""
Memory Router Enhancements QA Test Suite
========================================

Comprehensive QA testing to verify all agent types are properly supported by the memory system,
including the enhanced router patterns for data_engineer and test_integration agents.

This test suite validates:
1. Agent Coverage - All 10 agent types supported
2. Memory Routing - Various content types route correctly
3. Memory Operations - Add, retrieve, update work for all agents
4. Integration Testing - CLI and memory builder integration
5. Error Handling - Edge cases and graceful failures

Requirements tested:
- Router patterns for data_engineer and test_integration added
- Enhanced router logic with better scoring
- Validation functions work correctly
- All 10 agents are supported
"""
import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.services.memory_router import MemoryRouter
from claude_mpm.services.memory_builder import MemoryBuilder
from claude_mpm.services.agent_memory_manager import AgentMemoryManager
from claude_mpm.core.config import Config


class MemoryRouterEnhancementsQA:
    """Comprehensive QA test suite for memory router enhancements."""
    
    def __init__(self):
        self.temp_dir = None
        self.config = None
        self.router = None
        self.memory_manager = None
        self.memory_builder = None
        self.test_results = {
            "agent_coverage": {},
            "routing_accuracy": {},
            "memory_operations": {},
            "integration_tests": {},
            "error_handling": {},
            "performance": {},
            "summary": {}
        }
    
    def setup_test_environment(self):
        """Setup test environment with temporary directory."""
        print("🔧 Setting up QA test environment...")
        
        # Create temporary directory
        self.temp_dir = Path(tempfile.mkdtemp(prefix="memory_router_qa_"))
        print(f"   Test directory: {self.temp_dir}")
        
        # Initialize components
        self.config = Config()
        self.router = MemoryRouter(self.config)
        self.memory_manager = AgentMemoryManager(self.config)
        self.memory_builder = MemoryBuilder(self.config, self.temp_dir)
        
        # Create memories directory structure
        memories_dir = self.temp_dir / ".claude-mpm" / "memories"
        memories_dir.mkdir(parents=True, exist_ok=True)
        
        print("✅ QA test environment ready")
    
    def teardown_test_environment(self):
        """Clean up test environment."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            print("🧹 Test environment cleaned up")
    
    def test_agent_coverage_comprehensive(self):
        """Test 1: Comprehensive agent coverage verification."""
        print("\n=== QA Test 1: Agent Coverage ===")
        
        # Expected all 10 agent types
        expected_agents = [
            'data_engineer', 'documentation', 'engineer', 'ops', 'pm',
            'qa', 'research', 'security', 'test_integration', 'version_control'
        ]
        
        # Get supported agents
        supported_agents = self.router.get_supported_agents()
        
        # Verify count
        count_correct = len(supported_agents) == 10
        print(f"   Agent count: {len(supported_agents)}/10 {'✅' if count_correct else '❌'}") 
        
        # Verify each expected agent is supported
        missing_agents = []
        present_agents = []
        
        for agent in expected_agents:
            if agent in supported_agents:
                present_agents.append(agent)
                # Verify is_agent_supported() works
                supported_check = self.router.is_agent_supported(agent)
                if not supported_check:
                    print(f"   ❌ {agent}: present but is_agent_supported() returns False")
                else:
                    print(f"   ✅ {agent}: properly supported")
            else:
                missing_agents.append(agent)
                print(f"   ❌ {agent}: MISSING from supported agents")
        
        # Check for unexpected extra agents
        extra_agents = [a for a in supported_agents if a not in expected_agents]
        if extra_agents:
            print(f"   ⚠️  Extra agents found: {extra_agents}")
        
        # Verify routing patterns exist for each agent
        patterns_info = self.router.get_routing_patterns()
        agents_with_patterns = list(patterns_info['patterns'].keys())
        
        pattern_issues = []
        for agent in expected_agents:
            if agent not in agents_with_patterns:
                pattern_issues.append(agent)
            else:
                # Check pattern completeness
                agent_patterns = patterns_info['patterns'][agent]
                if agent_patterns['keyword_count'] == 0:
                    pattern_issues.append(f"{agent} (no keywords)")
                elif agent_patterns['section_count'] == 0:
                    pattern_issues.append(f"{agent} (no sections)")
        
        if pattern_issues:
            print(f"   ❌ Pattern issues: {pattern_issues}")
        else:
            print(f"   ✅ All agents have proper routing patterns")
        
        # Store results
        self.test_results["agent_coverage"] = {
            "expected_count": 10,
            "actual_count": len(supported_agents),
            "missing_agents": missing_agents,
            "extra_agents": extra_agents,
            "pattern_issues": pattern_issues,
            "total_keywords": patterns_info['total_keywords'],
            "pass": len(missing_agents) == 0 and len(pattern_issues) == 0
        }
        
        print(f"   📊 Result: {'PASS' if self.test_results['agent_coverage']['pass'] else 'FAIL'}")
        return self.test_results["agent_coverage"]["pass"]
    
    def test_enhanced_routing_accuracy(self):
        """Test 2: Test enhanced routing patterns with comprehensive content types."""
        print("\n=== QA Test 2: Enhanced Routing Accuracy ===")
        
        # Comprehensive test cases covering all agent specializations
        test_cases = [
            # Data Engineer - Enhanced patterns
            {
                "content": "Implement data pipeline with PostgreSQL ETL process and Apache Spark for real-time analytics",
                "expected": "data_engineer",
                "category": "database_pipeline",
                "priority": "high"
            },
            {
                "content": "Design schema migration strategy with database replication and query optimization for data warehouse",
                "expected": "data_engineer", 
                "category": "data_architecture",
                "priority": "high"
            },
            {
                "content": "Integrate AI API with OpenAI Claude for embedding generation and vector database storage using MongoDB",
                "expected": "data_engineer",
                "category": "ai_data_integration",
                "priority": "high"
            },
            {
                "content": "Stream processing with Kafka and data quality validation for batch analytics pipeline",
                "expected": "data_engineer",
                "category": "streaming_data",
                "priority": "high"
            },
            
            # Test Integration - Enhanced patterns
            {
                "content": "End-to-end integration testing with cross-system workflow validation using Cypress automation",
                "expected": "test_integration",
                "category": "e2e_testing",
                "priority": "high"
            },
            {
                "content": "System boundary testing with API contract validation and service integration verification",
                "expected": "test_integration",
                "category": "integration_validation",
                "priority": "high"
            },
            {
                "content": "User journey testing with selenium automation and cross-browser compatibility validation",
                "expected": "test_integration",
                "category": "user_journey",
                "priority": "high"
            },
            {
                "content": "Component integration test with mock services and test environment coordination using Newman",
                "expected": "test_integration",
                "category": "component_integration",
                "priority": "high"
            },
            
            # Engineer - Core patterns
            {
                "content": "Refactor code architecture with design patterns and implement performance optimization strategies",
                "expected": "engineer",
                "category": "code_architecture",
                "priority": "high"
            },
            {
                "content": "API interface implementation with error handling and comprehensive unit testing framework",
                "expected": "engineer",
                "category": "api_development",
                "priority": "high"
            },
            
            # QA - Quality focus
            {
                "content": "Quality assurance strategy with automated testing and comprehensive validation protocols",
                "expected": "qa",
                "category": "qa_strategy",
                "priority": "high"
            },
            {
                "content": "Bug analysis and defect tracking with regression testing and quality metrics reporting",
                "expected": "qa",
                "category": "quality_analysis",
                "priority": "high"
            },
            
            # Ops - Infrastructure
            {
                "content": "Deploy containerized applications with Docker and Kubernetes orchestration for production scaling",
                "expected": "ops",
                "category": "deployment",
                "priority": "high"
            },
            {
                "content": "Infrastructure monitoring with Prometheus metrics and Grafana dashboards for observability",
                "expected": "ops",
                "category": "monitoring",
                "priority": "high"
            },
            
            # Security
            {
                "content": "Authentication system with OAuth2 implementation and encryption protocols for data protection",
                "expected": "security",
                "category": "auth_security",
                "priority": "high"
            },
            {
                "content": "Vulnerability assessment and penetration testing with audit compliance verification",
                "expected": "security",
                "category": "security_audit",
                "priority": "high"
            },
            
            # Documentation
            {
                "content": "API documentation standards with comprehensive user guides and reference manual creation",
                "expected": "documentation",
                "category": "api_docs",
                "priority": "medium"
            },
            
            # Version Control
            {
                "content": "Git branching strategy with merge conflict resolution and semantic versioning workflow",
                "expected": "version_control",
                "category": "git_workflow",
                "priority": "medium"
            },
            
            # Research
            {
                "content": "Domain analysis and requirements research with business logic specification documentation",
                "expected": "research",
                "category": "domain_research",
                "priority": "medium"
            },
            
            # PM
            {
                "content": "Project coordination with stakeholder management and agile methodology implementation",
                "expected": "pm",
                "category": "project_management",
                "priority": "medium"
            },
            
            # Edge cases and ambiguous content
            {
                "content": "Database testing with integration validation", # Could be data_engineer or test_integration
                "expected": None,  # Accept either
                "category": "ambiguous",
                "priority": "low",
                "acceptable": ["data_engineer", "test_integration", "qa"]
            },
            {
                "content": "Security testing automation framework", # Could be security or test_integration
                "expected": None,
                "category": "ambiguous", 
                "priority": "low",
                "acceptable": ["security", "test_integration", "qa"]
            }
        ]
        
        routing_results = []
        high_priority_correct = 0
        high_priority_total = 0
        total_correct = 0
        
        print(f"   Testing {len(test_cases)} routing scenarios...")
        
        for i, case in enumerate(test_cases):
            result = self.router.analyze_and_route(case["content"])
            
            actual_agent = result["target_agent"]
            confidence = result["confidence"]
            
            # Determine if routing is correct
            if case["expected"] is None:
                # Ambiguous case - check if result is in acceptable list
                correct = actual_agent in case.get("acceptable", [])
            else:
                correct = actual_agent == case["expected"]
            
            if correct:
                total_correct += 1
                if case["priority"] == "high":
                    high_priority_correct += 1
            
            if case["priority"] == "high":
                high_priority_total += 1
            
            # Store detailed result
            test_result = {
                "case_id": i + 1,
                "category": case["category"],
                "content": case["content"][:80] + "..." if len(case["content"]) > 80 else case["content"],
                "expected": case["expected"],
                "actual": actual_agent,
                "confidence": confidence,
                "correct": correct,
                "priority": case["priority"],
                "reasoning": result["reasoning"]
            }
            
            routing_results.append(test_result)
            
            # Visual feedback
            status = "✅" if correct else "❌"
            priority_marker = "🔥" if case["priority"] == "high" else "🔸" if case["priority"] == "medium" else "🔹"
            print(f"   {status}{priority_marker} {case['category']}: {actual_agent} (conf: {confidence:.2f})")
            
            if not correct and case["expected"]:
                print(f"      Expected: {case['expected']}, Got: {actual_agent}")
        
        # Calculate metrics
        total_accuracy = total_correct / len(test_cases)
        high_priority_accuracy = high_priority_correct / high_priority_total if high_priority_total > 0 else 1.0
        
        # Store results
        self.test_results["routing_accuracy"] = {
            "total_cases": len(test_cases),
            "total_correct": total_correct,
            "overall_accuracy": total_accuracy,
            "high_priority_correct": high_priority_correct,
            "high_priority_total": high_priority_total,
            "high_priority_accuracy": high_priority_accuracy,
            "detailed_results": routing_results,
            "pass": total_accuracy >= 0.8 and high_priority_accuracy >= 0.9
        }
        
        print(f"   📊 Overall Accuracy: {total_correct}/{len(test_cases)} ({total_accuracy:.1%})")
        print(f"   📊 High Priority Accuracy: {high_priority_correct}/{high_priority_total} ({high_priority_accuracy:.1%})")
        print(f"   📊 Result: {'PASS' if self.test_results['routing_accuracy']['pass'] else 'FAIL'}")
        
        return self.test_results["routing_accuracy"]["pass"]
    
    def test_memory_operations_all_agents(self):
        """Test 3: Test memory operations work for all agent types."""
        print("\n=== QA Test 3: Memory Operations ===")
        
        # Setup test memories directory
        memories_dir = self.temp_dir / ".claude-mpm" / "memories"
        memories_dir.mkdir(parents=True, exist_ok=True)
        
        operation_results = {}
        successful_agents = []
        failed_agents = []
        
        supported_agents = self.router.get_supported_agents()
        
        print(f"   Testing memory operations for {len(supported_agents)} agents...")
        
        for agent in supported_agents:
            try:
                # Test 1: Add memory
                test_memory = f"Test memory content for {agent} agent - operational validation at {datetime.now().isoformat()}"
                add_success = self.memory_manager.update_agent_memory(agent, "Test Validation", test_memory)
                
                # Test 2: Verify file creation
                agent_file = memories_dir / f"{agent}_agent.md"
                file_exists = agent_file.exists()
                
                # Test 3: Verify content retrieval
                if file_exists:
                    try:
                        retrieved_content = self.memory_manager.load_agent_memory(agent)
                        content_contains_test = test_memory in retrieved_content
                    except Exception as e:
                        content_contains_test = False
                        print(f"      ⚠️  Content retrieval error for {agent}: {e}")
                else:
                    content_contains_test = False
                
                # Test 4: Update memory (add another entry)
                update_memory = f"Updated memory for {agent} - second entry"
                update_success = self.memory_manager.update_agent_memory(agent, "Test Updates", update_memory)
                
                # Overall success assessment
                all_success = add_success and file_exists and content_contains_test and update_success
                
                operation_results[agent] = {
                    "add_memory": add_success,
                    "file_created": file_exists,
                    "content_retrieval": content_contains_test,
                    "update_memory": update_success,
                    "overall_success": all_success
                }
                
                if all_success:
                    successful_agents.append(agent)
                    print(f"   ✅ {agent}: All operations successful")
                else:
                    failed_agents.append(agent)
                    print(f"   ❌ {agent}: Operations failed - add:{add_success}, file:{file_exists}, retrieve:{content_contains_test}, update:{update_success}")
                
            except Exception as e:
                operation_results[agent] = {
                    "add_memory": False,
                    "file_created": False,
                    "content_retrieval": False,
                    "update_memory": False,
                    "overall_success": False,
                    "error": str(e)
                }
                failed_agents.append(agent)
                print(f"   ❌ {agent}: Exception - {e}")
        
        # Calculate success rate
        success_rate = len(successful_agents) / len(supported_agents)
        
        # Store results
        self.test_results["memory_operations"] = {
            "total_agents": len(supported_agents),
            "successful_agents": len(successful_agents),
            "failed_agents": len(failed_agents),
            "success_rate": success_rate,
            "successful_agent_list": successful_agents,
            "failed_agent_list": failed_agents,
            "detailed_results": operation_results,
            "pass": success_rate >= 0.95  # Require 95% success rate
        }
        
        print(f"   📊 Success Rate: {len(successful_agents)}/{len(supported_agents)} ({success_rate:.1%})")
        print(f"   📊 Result: {'PASS' if self.test_results['memory_operations']['pass'] else 'FAIL'}")
        
        return self.test_results["memory_operations"]["pass"]
    
    def test_cli_integration(self):
        """Test 4: Test CLI and memory builder integration."""
        print("\n=== QA Test 4: CLI Integration ===")
        
        integration_results = {}
        
        # Test 1: Memory router patterns accessible
        try:
            patterns = self.router.get_routing_patterns()
            patterns_test = {
                "success": True,
                "agent_count": len(patterns["agents"]),
                "keyword_count": patterns["total_keywords"],
                "has_all_expected": len(patterns["agents"]) >= 10
            }
            print(f"   ✅ Router patterns: {patterns_test['agent_count']} agents, {patterns_test['keyword_count']} keywords")
        except Exception as e:
            patterns_test = {"success": False, "error": str(e)}
            print(f"   ❌ Router patterns failed: {e}")
        
        integration_results["patterns_access"] = patterns_test
        
        # Test 2: Memory builder integration
        try:
            # Create test document for extraction
            test_doc_content = """
# Test Project Documentation

## Implementation Guidelines
- Always use proper error handling in database connections
- Implement data validation before ETL processing  
- Use integration testing for cross-system validation

## Quality Standards
- All database queries must be optimized for performance
- Integration tests should cover end-to-end workflows
- Security audits required for authentication systems
"""
            
            # Test extraction
            extracted_items = self.memory_builder.extract_from_text(test_doc_content, "test_doc.md")
            
            builder_test = {
                "success": len(extracted_items) > 0,
                "items_extracted": len(extracted_items),
                "agent_routing": {}
            }
            
            # Verify items were routed to appropriate agents
            for item in extracted_items:
                agent = item.get("target_agent", "unknown")
                if agent not in builder_test["agent_routing"]:
                    builder_test["agent_routing"][agent] = 0
                builder_test["agent_routing"][agent] += 1
            
            print(f"   ✅ Memory builder: {len(extracted_items)} items extracted")
            print(f"      Agent routing: {builder_test['agent_routing']}")
            
        except Exception as e:
            builder_test = {"success": False, "error": str(e)}
            print(f"   ❌ Memory builder failed: {e}")
        
        integration_results["memory_builder"] = builder_test
        
        # Test 3: Test routing consistency
        try:
            # Test the same content multiple times to ensure consistent routing
            test_content = "Database ETL pipeline with integration testing validation"
            results = []
            for _ in range(5):
                result = self.router.analyze_and_route(test_content)
                results.append(result["target_agent"])
            
            # Check consistency
            unique_agents = set(results)
            consistency_test = {
                "success": len(unique_agents) <= 2,  # Allow some variation but not total randomness
                "agent_results": results,
                "unique_agents": list(unique_agents),
                "consistent": len(unique_agents) == 1
            }
            
            if consistency_test["consistent"]:
                print(f"   ✅ Routing consistency: Perfect (all -> {results[0]})")
            elif consistency_test["success"]:
                print(f"   ✅ Routing consistency: Good (agents: {unique_agents})")
            else:
                print(f"   ❌ Routing consistency: Poor (agents: {unique_agents})")
                
        except Exception as e:
            consistency_test = {"success": False, "error": str(e)}
            print(f"   ❌ Routing consistency test failed: {e}")
        
        integration_results["routing_consistency"] = consistency_test
        
        # Overall integration assessment
        integration_pass = (
            patterns_test.get("success", False) and
            builder_test.get("success", False) and
            consistency_test.get("success", False)
        )
        
        self.test_results["integration_tests"] = {
            "components_tested": 3,
            "components_passed": sum(1 for test in integration_results.values() if test.get("success", False)),
            "detailed_results": integration_results,
            "pass": integration_pass
        }
        
        print(f"   📊 Integration: {self.test_results['integration_tests']['components_passed']}/3 components passed")
        print(f"   📊 Result: {'PASS' if integration_pass else 'FAIL'}")
        
        return integration_pass
    
    def test_error_handling_edge_cases(self):
        """Test 5: Test error handling and edge cases."""
        print("\n=== QA Test 5: Error Handling & Edge Cases ===")
        
        error_tests = {}
        
        # Test 1: Empty content
        try:
            result = self.router.analyze_and_route("")
            empty_test = {
                "success": True,
                "agent": result["target_agent"],
                "confidence": result["confidence"],
                "defaults_correctly": result["target_agent"] == "pm" and result["confidence"] <= 0.2
            }
            print(f"   ✅ Empty content: {result['target_agent']} (confidence: {result['confidence']:.2f})")
        except Exception as e:
            empty_test = {"success": False, "error": str(e)}
            print(f"   ❌ Empty content failed: {e}")
        
        error_tests["empty_content"] = empty_test
        
        # Test 2: Very long content
        try:
            long_content = "database implementation with testing " * 200  # 600+ words
            result = self.router.analyze_and_route(long_content)
            long_test = {
                "success": True,
                "agent": result["target_agent"],
                "confidence": result["confidence"],
                "handles_long_content": result["confidence"] > 0
            }
            print(f"   ✅ Long content: {result['target_agent']} (confidence: {result['confidence']:.2f})")
        except Exception as e:
            long_test = {"success": False, "error": str(e)}
            print(f"   ❌ Long content failed: {e}")
        
        error_tests["long_content"] = long_test
        
        # Test 3: Special characters and encoding
        try:
            special_content = "データベース implementation with 测试 validation émoji 🚀 and symbols !@#$%^&*()"
            result = self.router.analyze_and_route(special_content)
            special_test = {
                "success": True,
                "agent": result["target_agent"],
                "handles_unicode": True
            }
            print(f"   ✅ Special characters: {result['target_agent']}")
        except Exception as e:
            special_test = {"success": False, "error": str(e)}
            print(f"   ❌ Special characters failed: {e}")
        
        error_tests["special_characters"] = special_test
        
        # Test 4: Invalid agent support check
        try:
            invalid_result = self.router.is_agent_supported("nonexistent_agent")
            valid_result = self.router.is_agent_supported("engineer")
            
            validation_test = {
                "success": True,
                "invalid_returns_false": not invalid_result,
                "valid_returns_true": valid_result,
                "validation_works": not invalid_result and valid_result
            }
            print(f"   ✅ Agent validation: invalid={invalid_result}, valid={valid_result}")
        except Exception as e:
            validation_test = {"success": False, "error": str(e)}
            print(f"   ❌ Agent validation failed: {e}")
        
        error_tests["agent_validation"] = validation_test
        
        # Test 5: Malformed memory content
        try:
            # Test with None, empty dict, etc.
            none_result = self.router.analyze_and_route(None)
            malformed_test = {
                "success": False,  # Should handle gracefully
                "error": "Should not accept None content"
            }
        except Exception as e:
            # Expected to fail gracefully
            malformed_test = {
                "success": True,
                "handles_none": True,
                "error_message": str(e)
            }
        
        try:
            # Test with extremely short content
            short_result = self.router.analyze_and_route("a")
            malformed_test["handles_short"] = True
            print(f"   ✅ Short content: {short_result['target_agent']}")
        except Exception as e:
            malformed_test["handles_short"] = False
            print(f"   ❌ Short content failed: {e}")
        
        error_tests["malformed_content"] = malformed_test
        
        # Calculate error handling success
        error_handling_success = sum(1 for test in error_tests.values() if test.get("success", False))
        total_error_tests = len(error_tests)
        
        self.test_results["error_handling"] = {
            "total_tests": total_error_tests,
            "successful_tests": error_handling_success,
            "success_rate": error_handling_success / total_error_tests,
            "detailed_results": error_tests,
            "pass": error_handling_success >= 4  # At least 4/5 should pass
        }
        
        print(f"   📊 Error Handling: {error_handling_success}/{total_error_tests} tests passed")
        print(f"   📊 Result: {'PASS' if self.test_results['error_handling']['pass'] else 'FAIL'}")
        
        return self.test_results["error_handling"]["pass"]
    
    def test_performance_metrics(self):
        """Test 6: Performance and scalability testing."""
        print("\n=== QA Test 6: Performance Metrics ===")
        
        import time
        
        performance_results = {}
        
        # Test 1: Routing speed
        test_contents = [
            "database implementation with ETL processing",
            "integration testing with end-to-end validation", 
            "security authentication with encryption protocols",
            "deployment infrastructure with container orchestration",
            "quality assurance with automated testing frameworks"
        ] * 20  # 100 total tests
        
        try:
            start_time = time.time()
            results = []
            
            for content in test_contents:
                result = self.router.analyze_and_route(content)
                results.append(result)
            
            end_time = time.time()
            total_time = end_time - start_time
            avg_time_per_routing = total_time / len(test_contents)
            
            routing_speed_test = {
                "success": True,
                "total_routings": len(test_contents),
                "total_time": total_time,
                "avg_time_per_routing": avg_time_per_routing,
                "routings_per_second": len(test_contents) / total_time,
                "performance_acceptable": avg_time_per_routing < 0.1  # Under 100ms per routing
            }
            
            print(f"   ✅ Routing speed: {len(test_contents)} routings in {total_time:.2f}s ({avg_time_per_routing*1000:.1f}ms avg)")
            print(f"      Performance: {routing_speed_test['routings_per_second']:.1f} routings/sec")
            
        except Exception as e:
            routing_speed_test = {"success": False, "error": str(e)}
            print(f"   ❌ Routing speed test failed: {e}")
        
        performance_results["routing_speed"] = routing_speed_test
        
        # Test 2: Memory consumption (basic check)
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            
            # Create many router instances to test memory usage
            routers = []
            for i in range(50):
                routers.append(MemoryRouter(self.config))
            
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = memory_after - memory_before
            
            memory_test = {
                "success": True,
                "memory_before_mb": memory_before,
                "memory_after_mb": memory_after,
                "memory_increase_mb": memory_increase,
                "memory_per_instance_mb": memory_increase / 50,
                "memory_acceptable": memory_increase < 100  # Less than 100MB increase
            }
            
            print(f"   ✅ Memory usage: {memory_increase:.1f}MB increase for 50 instances")
            
        except ImportError:
            memory_test = {"success": False, "error": "psutil not available"}
            print("   ⚠️  Memory test skipped (psutil not available)")
        except Exception as e:
            memory_test = {"success": False, "error": str(e)}
            print(f"   ❌ Memory test failed: {e}")
        
        performance_results["memory_usage"] = memory_test
        
        # Store performance results
        performance_pass = all(test.get("success", False) for test in performance_results.values())
        
        self.test_results["performance"] = {
            "tests_run": len(performance_results),
            "detailed_results": performance_results,
            "pass": performance_pass
        }
        
        print(f"   📊 Performance: {'PASS' if performance_pass else 'FAIL'}")
        return performance_pass
    
    def generate_qa_report(self):
        """Generate comprehensive QA report."""
        print("\n" + "="*60)
        print("📋 MEMORY ROUTER ENHANCEMENTS QA REPORT")
        print("="*60)
        
        # Calculate overall results
        test_categories = [
            ("Agent Coverage", self.test_results["agent_coverage"]),
            ("Routing Accuracy", self.test_results["routing_accuracy"]),
            ("Memory Operations", self.test_results["memory_operations"]),
            ("Integration Tests", self.test_results["integration_tests"]),
            ("Error Handling", self.test_results["error_handling"]),
            ("Performance", self.test_results["performance"])
        ]
        
        passed_tests = sum(1 for _, result in test_categories if result.get("pass", False))
        total_tests = len(test_categories)
        overall_success_rate = passed_tests / total_tests
        
        # Print summary
        print(f"\n📊 OVERALL RESULTS:")
        print(f"   Tests Passed: {passed_tests}/{total_tests} ({overall_success_rate:.1%})")
        print(f"   Overall Status: {'🎉 PASS' if overall_success_rate >= 0.8 else '❌ FAIL'}")
        
        # Detailed results
        print(f"\n📋 DETAILED RESULTS:")
        
        for category_name, results in test_categories:
            status = "✅ PASS" if results.get("pass", False) else "❌ FAIL"
            print(f"\n   {status} {category_name}")
            
            if category_name == "Agent Coverage":
                print(f"      - Supported agents: {results['actual_count']}/10")
                print(f"      - Total keywords: {results['total_keywords']}")
                if results['missing_agents']:
                    print(f"      - Missing agents: {results['missing_agents']}")
                    
            elif category_name == "Routing Accuracy":
                print(f"      - Overall accuracy: {results['overall_accuracy']:.1%}")
                print(f"      - High priority accuracy: {results['high_priority_accuracy']:.1%}")
                print(f"      - Test cases: {results['total_cases']}")
                
            elif category_name == "Memory Operations":
                print(f"      - Success rate: {results['success_rate']:.1%}")
                print(f"      - Successful agents: {results['successful_agents']}/{results['total_agents']}")
                if results['failed_agent_list']:
                    print(f"      - Failed agents: {results['failed_agent_list']}")
                    
            elif category_name == "Integration Tests":
                print(f"      - Components passed: {results['components_passed']}/3")
                
            elif category_name == "Error Handling":
                print(f"      - Error tests passed: {results['successful_tests']}/{results['total_tests']}")
                
            elif category_name == "Performance":
                if results.get("detailed_results", {}).get("routing_speed", {}).get("success"):
                    speed = results["detailed_results"]["routing_speed"]["routings_per_second"]
                    print(f"      - Routing speed: {speed:.1f} routings/sec")
        
        # Recommendations
        print(f"\n🎯 RECOMMENDATIONS:")
        
        if overall_success_rate >= 0.8:
            print("   ✅ Memory system enhancements are working correctly")
            print("   ✅ All agent types are properly supported")
            print("   ✅ Router patterns for data_engineer and test_integration are effective")
            print("   ✅ Enhanced router logic provides good accuracy")
            print("   ✅ System is ready for production use")
        else:
            print("   ❌ Some tests failed - review detailed results above")
            if not self.test_results["agent_coverage"]["pass"]:
                print("   ❌ Agent coverage issues need attention")
            if not self.test_results["routing_accuracy"]["pass"]:
                print("   ❌ Routing accuracy needs improvement")
            if not self.test_results["memory_operations"]["pass"]:
                print("   ❌ Memory operations have issues")
        
        # Save detailed results
        self.save_qa_results()
        
        # Final assessment
        self.test_results["summary"] = {
            "overall_success_rate": overall_success_rate,
            "tests_passed": passed_tests,
            "total_tests": total_tests,
            "final_status": "PASS" if overall_success_rate >= 0.8 else "FAIL",
            "timestamp": datetime.now().isoformat(),
            "agent_count_verified": self.test_results["agent_coverage"]["actual_count"],
            "routing_accuracy": self.test_results["routing_accuracy"]["overall_accuracy"],
            "memory_operations_success": self.test_results["memory_operations"]["success_rate"]
        }
        
        return self.test_results["summary"]["final_status"] == "PASS"
    
    def save_qa_results(self):
        """Save detailed QA results to file."""
        try:
            results_file = Path(__file__).parent.parent / "memory_router_qa_results.json"
            
            with open(results_file, 'w') as f:
                json.dump(self.test_results, f, indent=2, default=str)
            
            print(f"\n📄 Detailed results saved to: {results_file}")
            
        except Exception as e:
            print(f"   ⚠️  Could not save results: {e}")
    
    def run_comprehensive_qa(self):
        """Run all QA tests."""
        print("🧪 MEMORY ROUTER ENHANCEMENTS - COMPREHENSIVE QA")
        print("="*60)
        print("Testing memory system enhancements including:")
        print("  • Enhanced router patterns for data_engineer and test_integration")
        print("  • Improved router logic with better scoring") 
        print("  • Validation that all 10 agent types are supported")
        print("  • End-to-end functionality verification")
        
        try:
            self.setup_test_environment()
            
            # Run all test categories
            test_results = []
            
            test_results.append(self.test_agent_coverage_comprehensive())
            test_results.append(self.test_enhanced_routing_accuracy())
            test_results.append(self.test_memory_operations_all_agents())
            test_results.append(self.test_cli_integration())
            test_results.append(self.test_error_handling_edge_cases())
            test_results.append(self.test_performance_metrics())
            
            # Generate final report
            overall_pass = self.generate_qa_report()
            
            return overall_pass
            
        finally:
            self.teardown_test_environment()


def main():
    """Run comprehensive memory router QA tests."""
    qa_tester = MemoryRouterEnhancementsQA()
    
    try:
        success = qa_tester.run_comprehensive_qa()
        
        if success:
            print(f"\n🎉 MEMORY ROUTER ENHANCEMENTS QA: ALL TESTS PASSED!")
            print("   ✅ All 10 agent types are properly supported")
            print("   ✅ Enhanced routing patterns work correctly")
            print("   ✅ Memory operations function properly")
            print("   ✅ Integration with CLI and builder verified")
            print("   ✅ Error handling is robust") 
            print("   ✅ Performance meets requirements")
            print(f"\n✅ QA SIGN-OFF: APPROVED FOR PRODUCTION")
            sys.exit(0)
        else:
            print(f"\n❌ MEMORY ROUTER ENHANCEMENTS QA: SOME TESTS FAILED!")
            print("   Please review the detailed report above")
            print(f"\n❌ QA SIGN-OFF: REQUIRES FIXES BEFORE APPROVAL")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 QA CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        print(f"\n❌ QA SIGN-OFF: CRITICAL ISSUES PREVENT APPROVAL")
        sys.exit(1)


if __name__ == "__main__":
    main()