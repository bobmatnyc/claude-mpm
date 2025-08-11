#!/usr/bin/env python3
"""
Test Script: Agent Deployment Workflow

Comprehensive testing of the agent deployment system including:
1. Template to deployed agent workflow
2. Version management and semantic versioning
3. Deployment metrics collection
4. Agent discovery mechanism
5. Environment configuration
6. Migration and update handling

Tests complete deployment pipeline from JSON templates to deployed agents.
"""

import os
import sys
import time
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agent_deployment import AgentDeploymentService
from claude_mpm.services.deployed_agent_discovery import DeployedAgentDiscovery
from claude_mpm.core.config import Config


class DeploymentWorkflowTester:
    """Test suite for agent deployment workflow."""
    
    def __init__(self):
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "errors": [],
            "warnings": [],
            "performance_metrics": {},
            "deployment_stats": {}
        }
        self.temp_dirs = []
        
    def setup_test_environment(self) -> Tuple[Path, Path, Path]:
        """Set up test environment with templates and deployment directories."""
        # Create temporary directory structure
        temp_root = Path(tempfile.mkdtemp(prefix="deployment_test_"))
        self.temp_dirs.append(temp_root)
        
        # Create templates directory
        templates_dir = temp_root / "templates"
        templates_dir.mkdir(parents=True)
        
        # Create deployment target directory
        deployment_dir = temp_root / "deployment"
        deployment_dir.mkdir(parents=True)
        
        # Copy existing templates and base agent
        src_agents = Path(__file__).parent.parent / "src" / "claude_mpm" / "agents"
        if src_agents.exists():
            # Copy templates
            if (src_agents / "templates").exists():
                shutil.copytree(src_agents / "templates", templates_dir, dirs_exist_ok=True)
            
            # Copy base agent
            if (src_agents / "base_agent.json").exists():
                shutil.copy2(src_agents / "base_agent.json", temp_root / "base_agent.json")
        
        # Create test templates if none exist
        if not list(templates_dir.glob("*.json")):
            self._create_test_templates(templates_dir)
        
        return temp_root, templates_dir, deployment_dir
    
    def _create_test_templates(self, templates_dir: Path):
        """Create test agent templates."""
        test_agents = {
            "test_engineer": {
                "agent_version": "2.1.0",
                "metadata": {
                    "description": "Test engineering agent",
                    "tags": ["engineer", "test", "development"]
                },
                "capabilities": {
                    "tools": ["Read", "Write", "Edit", "Bash", "Grep"],
                    "model": "sonnet",
                    "temperature": 0.2
                },
                "instructions": "You are a test engineering agent for deployment testing."
            },
            "test_qa": {
                "agent_version": "1.5.0",
                "metadata": {
                    "description": "Test QA agent",
                    "tags": ["qa", "test", "validation"]
                },
                "capabilities": {
                    "tools": ["Read", "Write", "Bash", "Grep"],
                    "model": "sonnet",
                    "temperature": 0.1
                },
                "instructions": "You are a test QA agent for deployment testing."
            }
        }
        
        for agent_name, template_data in test_agents.items():
            template_file = templates_dir / f"{agent_name}.json"
            with open(template_file, 'w') as f:
                json.dump(template_data, f, indent=2)
    
    def test_basic_deployment(self, templates_dir: Path, deployment_dir: Path, base_agent_path: Path) -> bool:
        """Test basic agent deployment functionality."""
        print("Testing basic agent deployment...")
        
        try:
            start_time = time.perf_counter()
            
            # Initialize deployment service
            deployment_service = AgentDeploymentService(
                templates_dir=templates_dir,
                base_agent_path=base_agent_path
            )
            
            # Perform deployment
            results = deployment_service.deploy_agents(
                target_dir=deployment_dir,
                force_rebuild=False
            )
            
            end_time = time.perf_counter()
            self.test_results["performance_metrics"]["basic_deployment_time"] = end_time - start_time
            
            # Validate results structure
            required_keys = ["target_dir", "deployed", "errors", "skipped", "updated", "total"]
            missing_keys = [key for key in required_keys if key not in results]
            
            if missing_keys:
                self.test_results["errors"].append(f"Deployment results missing keys: {missing_keys}")
                return False
            
            # Check for errors
            if results["errors"]:
                self.test_results["errors"].extend([f"Deployment error: {error}" for error in results["errors"]])
                return False
            
            # Validate files were created
            agents_dir = deployment_dir / ".claude" / "agents"
            if not agents_dir.exists():
                self.test_results["errors"].append("Agents directory not created")
                return False
            
            deployed_files = list(agents_dir.glob("*.md"))
            if not deployed_files:
                self.test_results["errors"].append("No agent files deployed")
                return False
            
            # Store deployment stats
            self.test_results["deployment_stats"]["total_agents"] = results["total"]
            self.test_results["deployment_stats"]["deployed_count"] = len(results["deployed"])
            self.test_results["deployment_stats"]["files_created"] = len(deployed_files)
            
            print(f"✓ Basic deployment successful ({len(deployed_files)} files, {end_time - start_time:.3f}s)")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"Basic deployment failed: {e}")
            return False
    
    def test_version_management(self, templates_dir: Path, deployment_dir: Path, base_agent_path: Path) -> bool:
        """Test version management and semantic versioning."""
        print("Testing version management...")
        
        try:
            deployment_service = AgentDeploymentService(
                templates_dir=templates_dir,
                base_agent_path=base_agent_path
            )
            
            # First deployment
            results1 = deployment_service.deploy_agents(
                target_dir=deployment_dir,
                force_rebuild=True
            )
            
            if results1["errors"]:
                self.test_results["errors"].append(f"First deployment failed: {results1['errors']}")
                return False
            
            # Second deployment (should skip unchanged agents)
            start_time = time.perf_counter()
            results2 = deployment_service.deploy_agents(
                target_dir=deployment_dir,
                force_rebuild=False
            )
            end_time = time.perf_counter()
            
            self.test_results["performance_metrics"]["incremental_deployment_time"] = end_time - start_time
            
            # Should have skipped agents on second run
            if not results2["skipped"]:
                self.test_results["warnings"].append("No agents skipped on second deployment (version checking may not work)")
            
            # Test force rebuild
            results3 = deployment_service.deploy_agents(
                target_dir=deployment_dir,
                force_rebuild=True
            )
            
            # Should have updated/deployed agents on force rebuild
            total_processed = len(results3["deployed"]) + len(results3["updated"])
            if total_processed == 0:
                self.test_results["errors"].append("Force rebuild did not update any agents")
                return False
            
            # Check version formats in deployed files
            agents_dir = deployment_dir / ".claude" / "agents"
            version_errors = []
            
            for agent_file in agents_dir.glob("*.md"):
                content = agent_file.read_text()
                
                # Extract version from YAML frontmatter
                import re
                version_match = re.search(r'version:\s*["\']?([^"\'\n]+)["\']?', content)
                if version_match:
                    version = version_match.group(1)
                    
                    # Check semantic version format
                    if not re.match(r'^\d+\.\d+\.\d+$', version):
                        version_errors.append(f"{agent_file.name}: Invalid version format: {version}")
                else:
                    version_errors.append(f"{agent_file.name}: No version found in frontmatter")
            
            if version_errors:
                self.test_results["errors"].extend(version_errors)
                return False
            
            print(f"✓ Version management successful (skipped: {len(results2['skipped'])}, rebuilt: {total_processed})")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"Version management test failed: {e}")
            return False
    
    def test_deployment_metrics(self, templates_dir: Path, deployment_dir: Path, base_agent_path: Path) -> bool:
        """Test deployment metrics collection."""
        print("Testing deployment metrics collection...")
        
        try:
            deployment_service = AgentDeploymentService(
                templates_dir=templates_dir,
                base_agent_path=base_agent_path
            )
            
            # Clear any existing metrics
            deployment_service.reset_metrics()
            
            # Perform deployment
            start_time = time.perf_counter()
            results = deployment_service.deploy_agents(
                target_dir=deployment_dir,
                force_rebuild=True
            )
            end_time = time.perf_counter()
            
            # Get metrics
            metrics = deployment_service.get_deployment_metrics()
            
            # Validate metrics structure
            expected_metrics = [
                "total_deployments", "successful_deployments", "failed_deployments",
                "success_rate_percent", "average_deployment_time_ms"
            ]
            
            missing_metrics = [m for m in expected_metrics if m not in metrics]
            if missing_metrics:
                self.test_results["errors"].append(f"Missing deployment metrics: {missing_metrics}")
                return False
            
            # Validate metrics make sense
            if metrics["total_deployments"] == 0:
                self.test_results["errors"].append("Deployment metrics show no deployments")
                return False
            
            if metrics["success_rate_percent"] < 0 or metrics["success_rate_percent"] > 100:
                self.test_results["errors"].append(f"Invalid success rate: {metrics['success_rate_percent']}%")
                return False
            
            # Check timing metrics in results
            if "metrics" in results:
                result_metrics = results["metrics"]
                if "duration_ms" not in result_metrics:
                    self.test_results["warnings"].append("Deployment duration not tracked in results")
                
                if "agent_timings" in result_metrics:
                    agent_timings = result_metrics["agent_timings"]
                    if not agent_timings:
                        self.test_results["warnings"].append("No individual agent timings collected")
            
            # Store metrics for reporting
            self.test_results["deployment_stats"]["metrics"] = metrics
            
            print(f"✓ Metrics collection successful (success rate: {metrics['success_rate_percent']:.1f}%)")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"Deployment metrics test failed: {e}")
            return False
    
    def test_agent_discovery(self, deployment_dir: Path) -> bool:
        """Test agent discovery mechanism."""
        print("Testing agent discovery mechanism...")
        
        try:
            # Change to deployment directory for discovery
            original_cwd = os.getcwd()
            
            try:
                os.chdir(str(deployment_dir))
                
                discovery = DeployedAgentDiscovery()
                
                start_time = time.perf_counter()
                discovered_agents = discovery.discover_deployed_agents()
                end_time = time.perf_counter()
                
                self.test_results["performance_metrics"]["agent_discovery_time"] = end_time - start_time
                
                # Validate discovery results
                if not discovered_agents:
                    self.test_results["warnings"].append("No agents discovered (may be expected if none deployed)")
                    return True
                
                # Check agent data structure
                required_fields = ["name", "path", "type"]
                for i, agent in enumerate(discovered_agents):
                    missing_fields = [field for field in required_fields if field not in agent]
                    if missing_fields:
                        self.test_results["warnings"].append(f"Agent {i} missing fields: {missing_fields}")
                
                # Validate paths exist
                invalid_paths = []
                for agent in discovered_agents:
                    agent_path = Path(agent.get("path", ""))
                    if not agent_path.exists():
                        invalid_paths.append(str(agent_path))
                
                if invalid_paths:
                    self.test_results["errors"].append(f"Discovered agents with invalid paths: {invalid_paths}")
                    return False
                
                # Test discovery precedence (project > user > system)
                precedence_test = discovery.get_precedence_order()
                if not precedence_test:
                    self.test_results["warnings"].append("Discovery precedence order not available")
                
                self.test_results["deployment_stats"]["discovered_agents"] = len(discovered_agents)
                
                print(f"✓ Agent discovery successful ({len(discovered_agents)} agents, {end_time - start_time:.3f}s)")
                return True
                
            finally:
                os.chdir(original_cwd)
            
        except Exception as e:
            self.test_results["errors"].append(f"Agent discovery test failed: {e}")
            return False
    
    def test_environment_configuration(self, deployment_dir: Path, base_agent_path: Path) -> bool:
        """Test environment configuration for agent discovery."""
        print("Testing environment configuration...")
        
        try:
            deployment_service = AgentDeploymentService(base_agent_path=base_agent_path)
            
            # Test environment variable setting
            config_dir = deployment_dir / ".claude"
            env_vars = deployment_service.set_claude_environment(config_dir)
            
            # Validate environment variables were set
            expected_vars = ["CLAUDE_CONFIG_DIR", "CLAUDE_MAX_PARALLEL_SUBAGENTS", "CLAUDE_TIMEOUT"]
            missing_vars = []
            
            for var in expected_vars:
                if var not in env_vars:
                    missing_vars.append(var)
                elif var not in os.environ:
                    missing_vars.append(f"{var} (not in os.environ)")
            
            if missing_vars:
                self.test_results["errors"].append(f"Environment variables not set: {missing_vars}")
                return False
            
            # Test deployment verification
            verification_results = deployment_service.verify_deployment(config_dir)
            
            # Check verification structure
            required_keys = ["config_dir", "agents_found", "environment", "warnings"]
            missing_keys = [key for key in required_keys if key not in verification_results]
            
            if missing_keys:
                self.test_results["errors"].append(f"Verification results missing keys: {missing_keys}")
                return False
            
            # Store verification results
            self.test_results["deployment_stats"]["verification"] = {
                "agents_found": len(verification_results["agents_found"]),
                "warnings": len(verification_results["warnings"]),
                "env_vars_set": len(verification_results["environment"])
            }
            
            print(f"✓ Environment configuration successful ({len(env_vars)} vars set)")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"Environment configuration test failed: {e}")
            return False
    
    def test_migration_handling(self, templates_dir: Path, deployment_dir: Path, base_agent_path: Path) -> bool:
        """Test migration and update handling."""
        print("Testing migration and update handling...")
        
        try:
            deployment_service = AgentDeploymentService(
                templates_dir=templates_dir,
                base_agent_path=base_agent_path
            )
            
            # First deployment
            results1 = deployment_service.deploy_agents(
                target_dir=deployment_dir,
                force_rebuild=True
            )
            
            if results1["errors"]:
                self.test_results["errors"].append(f"Initial deployment failed: {results1['errors']}")
                return False
            
            # Create an old-format agent file to test migration
            agents_dir = deployment_dir / ".claude" / "agents"
            if agents_dir.exists():
                old_agent_file = agents_dir / "old_format_test.md"
                old_content = """---
name: old_format_test
description: "Test agent with old version format"
version: "0002-0005"
tools: ["Read", "Write"]
---

This is an old format test agent."""
                
                old_agent_file.write_text(old_content)
            
            # Second deployment should detect and migrate old format
            results2 = deployment_service.deploy_agents(
                target_dir=deployment_dir,
                force_rebuild=False
            )
            
            # Check for migrations
            if "migrated" in results2 and results2["migrated"]:
                print(f"✓ Migration detected and handled ({len(results2['migrated'])} agents)")
            else:
                self.test_results["warnings"].append("No migrations detected (may be expected)")
            
            # Test single agent deployment
            if templates_dir.exists():
                template_files = list(templates_dir.glob("*.json"))
                if template_files:
                    test_agent = template_files[0].stem
                    single_deploy_result = deployment_service.deploy_agent(
                        agent_name=test_agent,
                        target_dir=deployment_dir,
                        force_rebuild=True
                    )
                    
                    if not single_deploy_result:
                        self.test_results["errors"].append("Single agent deployment failed")
                        return False
            
            print("✓ Migration handling successful")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"Migration handling test failed: {e}")
            return False
    
    def test_performance_benchmarks(self, templates_dir: Path, deployment_dir: Path, base_agent_path: Path) -> bool:
        """Test performance benchmarks for deployment operations."""
        print("Testing deployment performance benchmarks...")
        
        try:
            deployment_service = AgentDeploymentService(
                templates_dir=templates_dir,
                base_agent_path=base_agent_path
            )
            
            # Benchmark multiple deployment runs
            times = []
            agent_counts = []
            
            for i in range(3):  # 3 runs for average
                # Clean deployment directory
                if deployment_dir.exists():
                    shutil.rmtree(deployment_dir)
                deployment_dir.mkdir(parents=True)
                
                start_time = time.perf_counter()
                results = deployment_service.deploy_agents(
                    target_dir=deployment_dir,
                    force_rebuild=True
                )
                end_time = time.perf_counter()
                
                if not results["errors"]:
                    times.append(end_time - start_time)
                    agent_counts.append(results["total"])
            
            if not times:
                self.test_results["errors"].append("No successful deployment runs for benchmarking")
                return False
            
            avg_time = sum(times) / len(times)
            avg_agents = sum(agent_counts) / len(agent_counts)
            
            self.test_results["performance_metrics"]["avg_full_deployment_time"] = avg_time
            self.test_results["performance_metrics"]["avg_agents_deployed"] = avg_agents
            self.test_results["performance_metrics"]["deployment_runs"] = len(times)
            
            # Performance thresholds
            if avg_time > 5.0:  # Should take less than 5 seconds for typical deployments
                self.test_results["warnings"].append(f"Deployment performance slow: {avg_time:.3f}s average")
            
            if avg_agents == 0:
                self.test_results["errors"].append("No agents deployed in performance test")
                return False
            
            print(f"✓ Performance benchmarks completed ({avg_time:.3f}s avg, {avg_agents} agents avg)")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"Performance benchmark test failed: {e}")
            return False
    
    def cleanup_test_environment(self):
        """Clean up temporary directories."""
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all deployment workflow tests."""
        print("=" * 60)
        print("AGENT DEPLOYMENT WORKFLOW TESTS")
        print("=" * 60)
        
        try:
            # Setup test environment
            temp_root, templates_dir, deployment_dir = self.setup_test_environment()
            base_agent_path = temp_root / "base_agent.json"
            
            # Run all tests
            tests = [
                ("Basic Deployment", lambda: self.test_basic_deployment(templates_dir, deployment_dir, base_agent_path)),
                ("Version Management", lambda: self.test_version_management(templates_dir, deployment_dir, base_agent_path)),
                ("Deployment Metrics", lambda: self.test_deployment_metrics(templates_dir, deployment_dir, base_agent_path)),
                ("Agent Discovery", lambda: self.test_agent_discovery(deployment_dir)),
                ("Environment Configuration", lambda: self.test_environment_configuration(deployment_dir, base_agent_path)),
                ("Migration Handling", lambda: self.test_migration_handling(templates_dir, deployment_dir, base_agent_path)),
                ("Performance Benchmarks", lambda: self.test_performance_benchmarks(templates_dir, deployment_dir, base_agent_path))
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
        """Print test results summary."""
        print("\n" + "=" * 60)
        print("DEPLOYMENT WORKFLOW TEST RESULTS")
        print("=" * 60)
        
        total_tests = self.test_results["passed"] + self.test_results["failed"]
        pass_rate = (self.test_results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {self.test_results['passed']}")
        print(f"Failed: {self.test_results['failed']}")
        print(f"Pass Rate: {pass_rate:.1f}%")
        
        if self.test_results["deployment_stats"]:
            print(f"\nDeployment Statistics:")
            for stat, value in self.test_results["deployment_stats"].items():
                if isinstance(value, dict):
                    print(f"  {stat}:")
                    for sub_key, sub_value in value.items():
                        print(f"    {sub_key}: {sub_value}")
                else:
                    print(f"  {stat}: {value}")
        
        if self.test_results["performance_metrics"]:
            print(f"\nPerformance Metrics:")
            for metric, value in self.test_results["performance_metrics"].items():
                if isinstance(value, float):
                    print(f"  {metric}: {value:.3f}s" if "time" in metric else f"  {metric}: {value:.1f}")
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


def main():
    """Main test execution."""
    tester = DeploymentWorkflowTester()
    results = tester.run_all_tests()
    tester.print_results()
    
    # Exit with appropriate code
    sys.exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()