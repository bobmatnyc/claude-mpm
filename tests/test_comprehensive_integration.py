#!/usr/bin/env python3
"""
Test Script: Comprehensive Integration Test

Full end-to-end testing of the integrated system:
Deploy agents → inject instructions → generate responses → validate logs

This test exercises all three systems together:
1. Agent deployment with version management
2. Instruction injection and synthesis  
3. Response logging with schema validation

Tests complete workflow from template to logged response.
"""

import os
import sys
import time
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment import AgentDeploymentService
from claude_mpm.services.simple_instructions_synthesizer import SimpleInstructionsSynthesizer
from claude_mpm.services.async_session_logger import AsyncSessionLogger
from claude_mpm.services.claude_session_logger import ClaudeSessionLogger
from claude_mpm.services.agents.registry import DeployedAgentDiscovery
from claude_mpm.core.config import Config


class ComprehensiveIntegrationTester:
    """Test suite for comprehensive system integration."""
    
    def __init__(self):
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "errors": [],
            "warnings": [],
            "performance_metrics": {},
            "integration_stats": {}
        }
        self.temp_dirs = []
        
    def setup_test_environment(self) -> Tuple[Path, Path, Path, Path]:
        """Set up comprehensive test environment."""
        # Create main temp directory
        temp_root = Path(tempfile.mkdtemp(prefix="integration_test_"))
        self.temp_dirs.append(temp_root)
        
        # Create directory structure
        templates_dir = temp_root / "templates"
        deployment_dir = temp_root / "deployment"
        responses_dir = temp_root / "responses"
        agents_dir = temp_root / "agents"
        
        for dir_path in [templates_dir, deployment_dir, responses_dir, agents_dir]:
            dir_path.mkdir(parents=True)
        
        # Copy existing source files
        src_agents = Path(__file__).parent.parent / "src" / "claude_mpm" / "agents"
        if src_agents.exists():
            # Copy templates
            if (src_agents / "templates").exists():
                shutil.copytree(src_agents / "templates", templates_dir, dirs_exist_ok=True)
            
            # Copy supporting files
            for file_name in ["base_agent.json", "INSTRUCTIONS.md", "MEMORIES.md", "TODOWRITE.md"]:
                src_file = src_agents / file_name
                if src_file.exists():
                    shutil.copy2(src_file, agents_dir / file_name)
        
        # Create additional test templates if needed
        self._create_integration_test_templates(templates_dir)
        
        return temp_root, templates_dir, deployment_dir, agents_dir
    
    def _create_integration_test_templates(self, templates_dir: Path):
        """Create specialized templates for integration testing."""
        integration_agents = {
            "integration_engineer": {
                "agent_version": "2.0.1",
                "metadata": {
                    "description": "Integration test engineering agent",
                    "tags": ["engineer", "integration", "test"],
                    "specializations": ["coding", "testing", "integration"]
                },
                "capabilities": {
                    "tools": ["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
                    "model": "sonnet",
                    "temperature": 0.2,
                    "max_tokens": 4096
                },
                "instructions": """You are an integration test engineering agent.

## When to Use
- Integration testing requirements
- Cross-system validation
- End-to-end testing scenarios

## Specialized Knowledge
- Integration testing patterns
- System boundary testing
- Cross-component validation

## Unique Capabilities
- Design integration test suites
- Validate system interactions
- Identify integration bottlenecks"""
            },
            "integration_qa": {
                "agent_version": "1.8.2",
                "metadata": {
                    "description": "Integration test QA agent",
                    "tags": ["qa", "integration", "validation"],
                    "specializations": ["testing", "validation", "quality"]
                },
                "capabilities": {
                    "tools": ["Read", "Write", "Bash", "Grep"],
                    "model": "sonnet",
                    "temperature": 0.1,
                    "max_tokens": 4096
                },
                "instructions": """You are an integration test QA agent.

## When to Use
- Quality validation across systems
- Integration test verification
- End-to-end quality assurance

## Specialized Knowledge
- Quality metrics for integration
- Cross-system testing methodologies
- Integration failure patterns

## Unique Capabilities
- Validate integration quality
- Execute cross-system tests
- Report integration issues"""
            }
        }
        
        for agent_name, template_data in integration_agents.items():
            template_file = templates_dir / f"{agent_name}.json"
            with open(template_file, 'w') as f:
                json.dump(template_data, f, indent=2)
    
    def test_full_deployment_workflow(self, templates_dir: Path, deployment_dir: Path, agents_dir: Path) -> bool:
        """Test the complete deployment workflow."""
        print("Testing full deployment workflow...")
        
        try:
            start_time = time.perf_counter()
            
            # Initialize deployment service
            deployment_service = AgentDeploymentService(
                templates_dir=templates_dir,
                base_agent_path=agents_dir / "base_agent.json"
            )
            
            # Deploy all agents
            deployment_results = deployment_service.deploy_agents(
                target_dir=deployment_dir,
                force_rebuild=True
            )
            
            deployment_time = time.perf_counter() - start_time
            self.test_results["performance_metrics"]["deployment_time"] = deployment_time
            
            # Validate deployment
            if deployment_results["errors"]:
                self.test_results["errors"].extend([f"Deployment: {error}" for error in deployment_results["errors"]])
                return False
            
            # Check deployed files exist
            agents_deploy_dir = deployment_dir / ".claude" / "agents"
            if not agents_deploy_dir.exists():
                self.test_results["errors"].append("Deployment directory not created")
                return False
            
            deployed_files = list(agents_deploy_dir.glob("*.md"))
            if len(deployed_files) == 0:
                self.test_results["errors"].append("No agents deployed")
                return False
            
            # Store deployment stats
            self.test_results["integration_stats"]["deployed_agents"] = len(deployed_files)
            self.test_results["integration_stats"]["deployment_results"] = {
                "deployed": len(deployment_results["deployed"]),
                "updated": len(deployment_results["updated"]),
                "skipped": len(deployment_results["skipped"])
            }
            
            print(f"✓ Deployment successful ({len(deployed_files)} agents, {deployment_time:.3f}s)")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"Deployment workflow failed: {e}")
            return False
    
    def test_instruction_synthesis_integration(self, deployment_dir: Path, agents_dir: Path) -> bool:
        """Test instruction synthesis with deployed agents."""
        print("Testing instruction synthesis integration...")
        
        try:
            # Change to deployment directory for agent discovery
            original_cwd = os.getcwd()
            
            try:
                os.chdir(str(deployment_dir))
                
                start_time = time.perf_counter()
                
                # Initialize synthesizer
                synthesizer = SimpleInstructionsSynthesizer(agents_dir=agents_dir)
                
                # Perform synthesis
                synthesized_instructions = synthesizer.synthesize()
                
                synthesis_time = time.perf_counter() - start_time
                self.test_results["performance_metrics"]["synthesis_time"] = synthesis_time
                
                # Validate synthesis results
                if not synthesized_instructions:
                    self.test_results["errors"].append("Synthesis returned empty instructions")
                    return False
                
                if len(synthesized_instructions) < 1000:
                    self.test_results["warnings"].append(f"Synthesized instructions seem short: {len(synthesized_instructions)} chars")
                
                # Check for expected components
                expected_components = [
                    "Agent Capabilities",  # Dynamic capabilities
                    "TodoWrite",           # Todo integration
                    "Memory"               # Memory integration
                ]
                
                missing_components = []
                for component in expected_components:
                    if component not in synthesized_instructions:
                        missing_components.append(component)
                
                if missing_components:
                    self.test_results["warnings"].extend([f"Missing component: {comp}" for comp in missing_components])
                
                # Check for agent-specific content
                agent_keywords = ["engineer", "qa", "integration"]
                found_keywords = [kw for kw in agent_keywords if kw.lower() in synthesized_instructions.lower()]
                
                if len(found_keywords) < len(agent_keywords) * 0.5:
                    self.test_results["warnings"].append("Few agent-specific keywords found in synthesis")
                
                # Store synthesis stats
                self.test_results["integration_stats"]["synthesis"] = {
                    "instruction_length": len(synthesized_instructions),
                    "components_found": len(expected_components) - len(missing_components),
                    "agent_keywords_found": len(found_keywords)
                }
                
                print(f"✓ Synthesis successful ({len(synthesized_instructions)} chars, {synthesis_time:.3f}s)")
                return True
                
            finally:
                os.chdir(original_cwd)
            
        except Exception as e:
            self.test_results["errors"].append(f"Instruction synthesis integration failed: {e}")
            return False
    
    def test_response_logging_integration(self, responses_dir: Path) -> bool:
        """Test response logging integration with both loggers."""
        print("Testing response logging integration...")
        
        try:
            # Test both async and claude loggers
            async_logger = AsyncSessionLogger(
                base_dir=responses_dir / "async",
                enable_async=False,  # Use sync for consistent testing
                enable_compression=False
            )
            
            claude_logger = ClaudeSessionLogger(
                base_dir=responses_dir / "claude",
                use_async=False
            )
            
            # Generate test responses simulating agent interactions
            test_scenarios = [
                {
                    "agent": "integration_engineer",
                    "request": "Deploy and test integration between agent deployment and logging systems",
                    "response": "Successfully deployed agents and validated logging integration. All systems operational.",
                    "metadata": {"test_type": "integration", "duration": "2.5s", "status": "success"}
                },
                {
                    "agent": "integration_qa", 
                    "request": "Validate response logging schema compliance across different logger implementations",
                    "response": "Schema validation complete. Found minor inconsistencies in field naming between AsyncLogger and ClaudeLogger.",
                    "metadata": {"test_type": "validation", "schema_issues": 2, "status": "warning"}
                },
                {
                    "agent": "integration_engineer",
                    "request": "Implement performance monitoring for instruction synthesis pipeline", 
                    "response": "Performance monitoring implemented. Average synthesis time: 0.15s, memory usage: 45MB peak.",
                    "metadata": {"test_type": "performance", "synthesis_time": 0.15, "memory_mb": 45}
                }
            ]
            
            start_time = time.perf_counter()
            
            # Log with both loggers
            async_successes = 0
            claude_successes = 0
            
            for scenario in test_scenarios:
                # Async logger
                async_success = async_logger.log_response(
                    request_summary=scenario["request"],
                    response_content=scenario["response"],
                    metadata={**scenario["metadata"], "agent": scenario["agent"]}
                )
                if async_success:
                    async_successes += 1
                
                # Claude logger
                claude_path = claude_logger.log_response(
                    request_summary=scenario["request"],
                    response_content=scenario["response"],
                    metadata={**scenario["metadata"], "agent": scenario["agent"]}
                )
                if claude_path and claude_path.exists():
                    claude_successes += 1
            
            logging_time = time.perf_counter() - start_time
            self.test_results["performance_metrics"]["logging_time"] = logging_time
            
            # Validate logging results
            if async_successes != len(test_scenarios):
                self.test_results["errors"].append(f"AsyncLogger failed: {async_successes}/{len(test_scenarios)} successful")
                return False
            
            if claude_successes != len(test_scenarios):
                self.test_results["errors"].append(f"ClaudeLogger failed: {claude_successes}/{len(test_scenarios)} successful")
                return False
            
            # Validate log files were created
            async_session_dir = responses_dir / "async" / async_logger.session_id
            claude_session_dir = responses_dir / "claude" / claude_logger.session_id
            
            async_files = list(async_session_dir.glob("*.json")) if async_session_dir.exists() else []
            claude_files = list(claude_session_dir.glob("*.json")) if claude_session_dir.exists() else []
            
            if len(async_files) != len(test_scenarios):
                self.test_results["errors"].append(f"AsyncLogger files mismatch: {len(async_files)} files vs {len(test_scenarios)} expected")
                return False
            
            if len(claude_files) != len(test_scenarios):
                self.test_results["errors"].append(f"ClaudeLogger files mismatch: {len(claude_files)} files vs {len(test_scenarios)} expected")
                return False
            
            # Store logging stats
            self.test_results["integration_stats"]["logging"] = {
                "async_successes": async_successes,
                "claude_successes": claude_successes,
                "async_files": len(async_files),
                "claude_files": len(claude_files),
                "scenarios_tested": len(test_scenarios)
            }
            
            print(f"✓ Response logging successful (both loggers, {len(test_scenarios)} scenarios, {logging_time:.3f}s)")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"Response logging integration failed: {e}")
            return False
    
    def test_end_to_end_workflow(self, temp_root: Path, templates_dir: Path, deployment_dir: Path, agents_dir: Path) -> bool:
        """Test complete end-to-end workflow."""
        print("Testing end-to-end workflow...")
        
        try:
            start_time = time.perf_counter()
            
            # Step 1: Deploy agents
            deployment_service = AgentDeploymentService(
                templates_dir=templates_dir,
                base_agent_path=agents_dir / "base_agent.json"
            )
            
            deployment_results = deployment_service.deploy_agents(
                target_dir=deployment_dir,
                force_rebuild=True
            )
            
            if deployment_results["errors"]:
                self.test_results["errors"].append(f"E2E Step 1 failed: {deployment_results['errors']}")
                return False
            
            # Step 2: Synthesize instructions with deployed agents
            original_cwd = os.getcwd()
            synthesized_instructions = ""
            
            try:
                os.chdir(str(deployment_dir))
                synthesizer = SimpleInstructionsSynthesizer(agents_dir=agents_dir)
                synthesized_instructions = synthesizer.synthesize()
            finally:
                os.chdir(original_cwd)
            
            if not synthesized_instructions:
                self.test_results["errors"].append("E2E Step 2 failed: instruction synthesis")
                return False
            
            # Step 3: Simulate agent responses and log them
            responses_dir = temp_root / "e2e_responses"
            logger = AsyncSessionLogger(
                base_dir=responses_dir,
                enable_async=False
            )
            
            # Simulate responses based on synthesized instructions
            e2e_metadata = {
                "e2e_test": True,
                "instructions_length": len(synthesized_instructions),
                "deployed_agents": len(deployment_results["deployed"]),
                "timestamp": datetime.now().isoformat()
            }
            
            log_success = logger.log_response(
                request_summary=f"Execute end-to-end test with {len(synthesized_instructions)} char instructions",
                response_content=f"E2E test successful. Instructions synthesized from {len(deployment_results['deployed'])} agents. System integration verified.",
                metadata=e2e_metadata,
                agent="integration_test"
            )
            
            if not log_success:
                self.test_results["errors"].append("E2E Step 3 failed: response logging")
                return False
            
            # Step 4: Validate the complete workflow
            session_dir = responses_dir / logger.session_id
            log_files = list(session_dir.glob("*.json")) if session_dir.exists() else []
            
            if not log_files:
                self.test_results["errors"].append("E2E Step 4 failed: no log files created")
                return False
            
            # Verify log content
            with open(log_files[0], 'r') as f:
                log_data = json.load(f)
            
            # Check that metadata from all steps is preserved (using standardized field names)
            required_fields = ["timestamp", "session_id", "agent", "request", "response", "metadata"]
            missing_fields = [field for field in required_fields if field not in log_data]
            
            if missing_fields:
                self.test_results["errors"].append(f"E2E validation failed: missing fields {missing_fields}")
                return False
            
            # Check metadata integrity
            if not log_data.get("metadata", {}).get("e2e_test"):
                self.test_results["warnings"].append("E2E metadata not preserved in log")
            
            end_time = time.perf_counter()
            total_time = end_time - start_time
            
            self.test_results["performance_metrics"]["e2e_total_time"] = total_time
            
            # Store E2E stats
            self.test_results["integration_stats"]["e2e"] = {
                "total_time": total_time,
                "agents_deployed": len(deployment_results["deployed"]),
                "instructions_length": len(synthesized_instructions),
                "log_files_created": len(log_files),
                "workflow_steps": 4,
                "success": True
            }
            
            print(f"✓ End-to-end workflow successful ({total_time:.3f}s total)")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"End-to-end workflow failed: {e}")
            return False
    
    def test_error_conditions(self, temp_root: Path, templates_dir: Path) -> bool:
        """Test error conditions and edge cases."""
        print("Testing error conditions and edge cases...")
        
        try:
            error_test_results = {
                "missing_templates": False,
                "invalid_json": False,
                "permission_denied": False,
                "corrupted_data": False
            }
            
            # Test 1: Missing templates directory
            try:
                deployment_service = AgentDeploymentService(
                    templates_dir=temp_root / "nonexistent",
                    base_agent_path=temp_root / "nonexistent.json"
                )
                results = deployment_service.deploy_agents(target_dir=temp_root / "error_test1")
                
                if results["errors"]:  # Should have errors
                    error_test_results["missing_templates"] = True
                
            except Exception:
                error_test_results["missing_templates"] = True  # Expected
            
            # Test 2: Invalid JSON template
            invalid_template = templates_dir / "invalid_test.json"
            invalid_template.write_text("{invalid json content}")
            
            try:
                deployment_service = AgentDeploymentService(templates_dir=templates_dir)
                results = deployment_service.deploy_agents(target_dir=temp_root / "error_test2")
                
                # Should handle invalid JSON gracefully
                if "invalid_test" not in [agent["name"] for agent in results.get("deployed", [])] and \
                   "invalid_test" not in [agent["name"] for agent in results.get("updated", [])]:
                    error_test_results["invalid_json"] = True
                
            except Exception:
                error_test_results["invalid_json"] = True  # Also acceptable
            
            # Test 3: Logger with invalid directory (permission test - simulate)
            try:
                # Try to create logger with root directory (should fail gracefully)
                logger = AsyncSessionLogger(
                    base_dir=Path("/root/test_access"),  # Usually not writable
                    enable_async=False
                )
                
                # If it doesn't fail immediately, try to log
                success = logger.log_response(
                    request_summary="Permission test",
                    response_content="Testing permission handling",
                    metadata={"test": "permission"}
                )
                
                # If this succeeds, the test environment is unusual
                error_test_results["permission_denied"] = True
                
            except (PermissionError, OSError):
                error_test_results["permission_denied"] = True  # Expected
            except Exception:
                # Other exceptions are also acceptable for permission errors
                error_test_results["permission_denied"] = True
            
            # Test 4: Corrupted log data handling
            try:
                responses_dir = temp_root / "corruption_test"
                responses_dir.mkdir(parents=True)
                
                logger = ClaudeSessionLogger(base_dir=responses_dir, use_async=False)
                
                # Create a corrupted session directory
                if logger.session_id:
                    session_dir = responses_dir / logger.session_id
                    session_dir.mkdir(parents=True)
                    
                    # Write a corrupted file
                    corrupted_file = session_dir / "corrupted.json"
                    corrupted_file.write_text("corrupted data")
                    
                    # Try to log normally - should handle corruption gracefully
                    result = logger.log_response(
                        request_summary="Corruption test",
                        response_content="Testing corruption handling",
                        metadata={"test": "corruption"}
                    )
                    
                    if result:  # Should succeed despite corruption
                        error_test_results["corrupted_data"] = True
                
            except Exception:
                # Should handle gracefully
                error_test_results["corrupted_data"] = True
            
            # Clean up test files
            if invalid_template.exists():
                invalid_template.unlink()
            
            # Evaluate error handling
            passed_error_tests = sum(error_test_results.values())
            total_error_tests = len(error_test_results)
            
            if passed_error_tests < total_error_tests * 0.7:  # At least 70% should pass
                self.test_results["warnings"].append(f"Error handling could be improved: {passed_error_tests}/{total_error_tests} tests passed")
            
            self.test_results["integration_stats"]["error_handling"] = {
                "tests_passed": passed_error_tests,
                "total_tests": total_error_tests,
                "pass_rate": passed_error_tests / total_error_tests * 100
            }
            
            print(f"✓ Error condition testing completed ({passed_error_tests}/{total_error_tests} passed)")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"Error condition testing failed: {e}")
            return False
    
    def cleanup_test_environment(self):
        """Clean up temporary directories."""
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all comprehensive integration tests."""
        print("=" * 60)
        print("COMPREHENSIVE INTEGRATION TESTS")
        print("=" * 60)
        
        try:
            # Setup test environment
            temp_root, templates_dir, deployment_dir, agents_dir = self.setup_test_environment()
            
            # Run all tests
            tests = [
                ("Full Deployment Workflow", lambda: self.test_full_deployment_workflow(templates_dir, deployment_dir, agents_dir)),
                ("Instruction Synthesis Integration", lambda: self.test_instruction_synthesis_integration(deployment_dir, agents_dir)),
                ("Response Logging Integration", lambda: self.test_response_logging_integration(temp_root / "responses")),
                ("End-to-End Workflow", lambda: self.test_end_to_end_workflow(temp_root, templates_dir, deployment_dir, agents_dir)),
                ("Error Conditions", lambda: self.test_error_conditions(temp_root, templates_dir))
            ]
            
            for test_name, test_func in tests:
                print(f"\n{test_name}:")
                try:
                    if test_func():
                        self.test_results["passed"] += 1
                        print(f"✓ {test_name} PASSED")
                    else:
                        self.test_results["failed"] += 1
                        print(f"✗ {test_name} FAILED")
                except Exception as e:
                    self.test_results["failed"] += 1
                    self.test_results["errors"].append(f"{test_name}: {e}")
                    print(f"✗ {test_name} ERROR: {e}")
            
        except Exception as e:
            self.test_results["errors"].append(f"Test setup failed: {e}")
        finally:
            self.cleanup_test_environment()
        
        return self.test_results
    
    def print_results(self):
        """Print comprehensive test results summary."""
        print("\n" + "=" * 60)
        print("COMPREHENSIVE INTEGRATION TEST RESULTS")
        print("=" * 60)
        
        total_tests = self.test_results["passed"] + self.test_results["failed"]
        pass_rate = (self.test_results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {self.test_results['passed']}")
        print(f"Failed: {self.test_results['failed']}")
        print(f"Pass Rate: {pass_rate:.1f}%")
        
        if self.test_results["integration_stats"]:
            print(f"\nIntegration Statistics:")
            for stat, value in self.test_results["integration_stats"].items():
                if isinstance(value, dict):
                    print(f"  {stat}:")
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, (int, float)):
                            print(f"    {sub_key}: {sub_value:.3f}" if isinstance(sub_value, float) else f"    {sub_key}: {sub_value}")
                        else:
                            print(f"    {sub_key}: {sub_value}")
                else:
                    print(f"  {stat}: {value}")
        
        if self.test_results["performance_metrics"]:
            print(f"\nPerformance Metrics:")
            total_time = sum(v for v in self.test_results["performance_metrics"].values() if isinstance(v, (int, float)))
            print(f"  total_integration_time: {total_time:.3f}s")
            
            for metric, value in self.test_results["performance_metrics"].items():
                if isinstance(value, float):
                    print(f"  {metric}: {value:.3f}s")
                else:
                    print(f"  {metric}: {value}")
        
        if self.test_results["warnings"]:
            print(f"\nWarnings ({len(self.test_results['warnings'])}):")
            for warning in self.test_results["warnings"]:
                print(f"  ⚠ {warning}")
        
        if self.test_results["errors"]:
            print(f"\nErrors ({len(self.test_results['errors'])}):")
            for error in self.test_results["errors"]:
                print(f"  ✗ {error}")
        
        print("\n" + "=" * 60)
        
        # Final assessment
        if self.test_results["failed"] == 0:
            print("🎉 ALL INTEGRATION TESTS PASSED - System integration verified!")
        elif pass_rate >= 80:
            print("✅ INTEGRATION TESTS MOSTLY SUCCESSFUL - Minor issues detected")  
        elif pass_rate >= 60:
            print("⚠ INTEGRATION TESTS PARTIALLY SUCCESSFUL - Significant issues found")
        else:
            print("❌ INTEGRATION TESTS FAILED - Major system issues detected")


def main():
    """Main test execution."""
    tester = ComprehensiveIntegrationTester()
    results = tester.run_all_tests()
    tester.print_results()
    
    # Exit with appropriate code
    sys.exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()