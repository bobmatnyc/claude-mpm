#!/usr/bin/env python3
"""
Test Script: Instruction Injection System

Comprehensive testing of the instruction injection and synthesis system including:
1. Multi-agent instruction synthesis
2. Template loading and processing
3. Frontmatter format validation
4. Dynamic capabilities injection
5. Memory and todo integration

Tests different agent types: engineer, qa, research, documentation, security, ops
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
import tempfile
import shutil

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.simple_instructions_synthesizer import SimpleInstructionsSynthesizer
from claude_mpm.services.deployed_agent_discovery import DeployedAgentDiscovery
from claude_mpm.services.agent_deployment import AgentDeploymentService
from claude_mpm.core.config import Config


class InstructionInjectionTester:
    """Test suite for instruction injection and synthesis."""
    
    def __init__(self):
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "errors": [],
            "warnings": [],
            "performance_metrics": {}
        }
        self.temp_dirs = []
        
    def setup_test_environment(self) -> Tuple[Path, Path]:
        """Set up test environment with temp directories."""
        # Create temporary directory for tests
        temp_dir = Path(tempfile.mkdtemp(prefix="instruction_test_"))
        self.temp_dirs.append(temp_dir)
        
        # Create agents directory structure
        agents_dir = temp_dir / "agents"
        agents_dir.mkdir(parents=True)
        
        # Copy existing agent templates for testing
        src_agents = Path(__file__).parent.parent / "src" / "claude_mpm" / "agents"
        if src_agents.exists():
            shutil.copytree(src_agents / "templates", agents_dir / "templates", dirs_exist_ok=True)
            if (src_agents / "base_agent.json").exists():
                shutil.copy2(src_agents / "base_agent.json", agents_dir / "base_agent.json")
            if (src_agents / "INSTRUCTIONS.md").exists():
                shutil.copy2(src_agents / "INSTRUCTIONS.md", agents_dir / "INSTRUCTIONS.md")
            if (src_agents / "MEMORIES.md").exists():
                shutil.copy2(src_agents / "MEMORIES.md", agents_dir / "MEMORIES.md")
            if (src_agents / "TODOWRITE.md").exists():
                shutil.copy2(src_agents / "TODOWRITE.md", agents_dir / "TODOWRITE.md")
        
        return temp_dir, agents_dir
    
    def test_basic_synthesis(self, agents_dir: Path) -> bool:
        """Test basic instruction synthesis functionality."""
        print("Testing basic instruction synthesis...")
        
        try:
            start_time = time.perf_counter()
            
            # Initialize synthesizer
            synthesizer = SimpleInstructionsSynthesizer(agents_dir=agents_dir)
            
            # Perform synthesis
            instructions = synthesizer.synthesize()
            
            end_time = time.perf_counter()
            self.test_results["performance_metrics"]["basic_synthesis_time"] = end_time - start_time
            
            # Validate results
            if not instructions:
                self.test_results["errors"].append("Basic synthesis returned empty instructions")
                return False
                
            if len(instructions) < 100:  # Should be substantial
                self.test_results["warnings"].append(f"Instructions seem short: {len(instructions)} chars")
            
            # Check for key components
            required_components = ["Agent Capabilities", "TodoWrite", "Memory"]
            missing_components = []
            for component in required_components:
                if component not in instructions:
                    missing_components.append(component)
            
            if missing_components:
                self.test_results["errors"].append(f"Missing components: {missing_components}")
                return False
            
            print(f"✓ Basic synthesis successful ({len(instructions)} chars in {end_time - start_time:.3f}s)")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"Basic synthesis failed: {e}")
            return False
    
    def test_agent_specific_injection(self, agents_dir: Path) -> bool:
        """Test agent-specific instruction injection."""
        print("Testing agent-specific instruction injection...")
        
        # Test agents to check
        test_agents = ["engineer", "qa", "research", "documentation", "security", "ops"]
        results = {}
        
        try:
            for agent_name in test_agents:
                start_time = time.perf_counter()
                
                # Check if agent template exists
                template_path = agents_dir / "templates" / f"{agent_name}.json"
                if not template_path.exists():
                    self.test_results["warnings"].append(f"Template not found: {agent_name}")
                    continue
                
                # Load and validate template
                with open(template_path, 'r') as f:
                    template_data = json.load(f)
                
                # Check template structure
                required_fields = ["instructions", "metadata", "capabilities"]
                missing_fields = []
                for field in required_fields:
                    if field not in template_data:
                        missing_fields.append(field)
                
                if missing_fields:
                    self.test_results["errors"].append(f"Template {agent_name} missing fields: {missing_fields}")
                    results[agent_name] = False
                    continue
                
                # Validate instructions content
                instructions = template_data.get("instructions", "")
                if not instructions or len(instructions) < 50:
                    self.test_results["errors"].append(f"Template {agent_name} has insufficient instructions")
                    results[agent_name] = False
                    continue
                
                # Check for agent-specific keywords
                agent_keywords = {
                    "engineer": ["code", "implement", "develop", "debug"],
                    "qa": ["test", "quality", "validate", "coverage"],
                    "research": ["investigate", "analyze", "research", "evaluate"],
                    "documentation": ["document", "write", "changelog", "README"],
                    "security": ["secure", "vulnerability", "audit", "protection"],
                    "ops": ["deploy", "infrastructure", "pipeline", "operations"]
                }
                
                keywords = agent_keywords.get(agent_name, [])
                found_keywords = [kw for kw in keywords if kw.lower() in instructions.lower()]
                
                if len(found_keywords) == 0:
                    self.test_results["warnings"].append(f"Template {agent_name} missing agent-specific keywords")
                
                end_time = time.perf_counter()
                results[agent_name] = True
                
                print(f"✓ {agent_name} template validation passed ({end_time - start_time:.3f}s)")
            
            # Calculate success rate
            successful = sum(1 for result in results.values() if result)
            total = len(results)
            
            if successful == total:
                print(f"✓ All {total} agent templates validated successfully")
                return True
            else:
                self.test_results["errors"].append(f"Only {successful}/{total} agent templates passed validation")
                return False
                
        except Exception as e:
            self.test_results["errors"].append(f"Agent-specific injection test failed: {e}")
            return False
    
    def test_frontmatter_format(self, agents_dir: Path) -> bool:
        """Test frontmatter format validation."""
        print("Testing frontmatter format validation...")
        
        try:
            # Deploy agents first to test frontmatter
            deployment_service = AgentDeploymentService(
                templates_dir=agents_dir / "templates",
                base_agent_path=agents_dir / "base_agent.json"
            )
            
            temp_deploy_dir = self.temp_dirs[0] / "deployed"
            results = deployment_service.deploy_agents(target_dir=temp_deploy_dir)
            
            if results["errors"]:
                self.test_results["errors"].append(f"Deployment failed: {results['errors']}")
                return False
            
            # Check deployed agent files for proper frontmatter
            deployed_dir = temp_deploy_dir / ".claude" / "agents"
            agent_files = list(deployed_dir.glob("*.md"))
            
            if not agent_files:
                self.test_results["errors"].append("No agent files deployed for frontmatter testing")
                return False
            
            frontmatter_errors = []
            for agent_file in agent_files:
                content = agent_file.read_text()
                
                # Check for YAML frontmatter boundaries
                if not content.startswith("---"):
                    frontmatter_errors.append(f"{agent_file.name}: Missing opening frontmatter")
                    continue
                
                # Find closing boundary
                lines = content.split('\n')
                closing_found = False
                frontmatter_lines = []
                
                for i, line in enumerate(lines[1:], 1):
                    if line.strip() == "---":
                        closing_found = True
                        break
                    frontmatter_lines.append(line)
                
                if not closing_found:
                    frontmatter_errors.append(f"{agent_file.name}: Missing closing frontmatter")
                    continue
                
                # Validate required frontmatter fields
                required_fields = ["name:", "description:", "version:", "tools:"]
                frontmatter_content = '\n'.join(frontmatter_lines)
                
                for field in required_fields:
                    if field not in frontmatter_content:
                        frontmatter_errors.append(f"{agent_file.name}: Missing required field {field}")
                
                # Check version format (should be semantic)
                import re
                version_match = re.search(r'version:\s*["\']?([^"\'\n]+)["\']?', frontmatter_content)
                if version_match:
                    version = version_match.group(1)
                    if not re.match(r'^\d+\.\d+\.\d+$', version):
                        frontmatter_errors.append(f"{agent_file.name}: Invalid version format: {version}")
            
            if frontmatter_errors:
                self.test_results["errors"].extend(frontmatter_errors)
                return False
            
            print(f"✓ All {len(agent_files)} agent frontmatter formats validated")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"Frontmatter format test failed: {e}")
            return False
    
    def test_dynamic_capabilities_injection(self, agents_dir: Path) -> bool:
        """Test dynamic capabilities injection."""
        print("Testing dynamic capabilities injection...")
        
        try:
            start_time = time.perf_counter()
            
            # First deploy some agents
            deployment_service = AgentDeploymentService(
                templates_dir=agents_dir / "templates",
                base_agent_path=agents_dir / "base_agent.json"
            )
            
            temp_deploy_dir = self.temp_dirs[0] / "capabilities_test"
            results = deployment_service.deploy_agents(target_dir=temp_deploy_dir)
            
            if results["errors"]:
                self.test_results["errors"].append(f"Failed to deploy agents for capabilities test: {results['errors']}")
                return False
            
            # Now test agent discovery and capabilities generation
            discovery = DeployedAgentDiscovery()
            
            # Mock deployment path
            original_cwd = os.getcwd()
            try:
                os.chdir(str(temp_deploy_dir))
                
                discovered_agents = discovery.discover_deployed_agents()
                
                if not discovered_agents:
                    self.test_results["warnings"].append("No agents discovered for capabilities injection")
                    return True  # Not an error, just no agents to test
                
                # Test synthesizer with discovered agents
                synthesizer = SimpleInstructionsSynthesizer(agents_dir=agents_dir)
                instructions = synthesizer.synthesize()
                
                # Check if capabilities were injected
                if "Agent Capabilities" not in instructions:
                    self.test_results["errors"].append("Dynamic capabilities not injected into instructions")
                    return False
                
                # Check for specific agent mentions
                agent_names = [agent.get("name", "") for agent in discovered_agents]
                found_agents = []
                for agent_name in agent_names:
                    if agent_name.lower() in instructions.lower():
                        found_agents.append(agent_name)
                
                if len(found_agents) < len(agent_names) * 0.5:  # At least 50% should be mentioned
                    self.test_results["warnings"].append(f"Only {len(found_agents)}/{len(agent_names)} agents mentioned in capabilities")
                
                end_time = time.perf_counter()
                self.test_results["performance_metrics"]["capabilities_injection_time"] = end_time - start_time
                
                print(f"✓ Dynamic capabilities injection successful ({len(discovered_agents)} agents, {end_time - start_time:.3f}s)")
                return True
                
            finally:
                os.chdir(original_cwd)
            
        except Exception as e:
            self.test_results["errors"].append(f"Dynamic capabilities injection test failed: {e}")
            return False
    
    def test_memory_integration(self, agents_dir: Path) -> bool:
        """Test memory and todo integration."""
        print("Testing memory and todo integration...")
        
        try:
            # Check if memory and todo files exist
            memories_file = agents_dir / "MEMORIES.md"
            todowrite_file = agents_dir / "TODOWRITE.md"
            
            if not memories_file.exists():
                self.test_results["warnings"].append("MEMORIES.md file not found")
            
            if not todowrite_file.exists():
                self.test_results["warnings"].append("TODOWRITE.md file not found")
            
            # Test synthesis includes memory components
            synthesizer = SimpleInstructionsSynthesizer(agents_dir=agents_dir)
            instructions = synthesizer.synthesize()
            
            # Check for memory integration
            memory_indicators = ["memory", "learning", "knowledge"]
            memory_found = any(indicator in instructions.lower() for indicator in memory_indicators)
            
            if not memory_found:
                self.test_results["warnings"].append("Memory system integration not detected in instructions")
            
            # Check for todo integration
            todo_indicators = ["todo", "task", "tracking"]
            todo_found = any(indicator in instructions.lower() for indicator in todo_indicators)
            
            if not todo_found:
                self.test_results["warnings"].append("Todo system integration not detected in instructions")
            
            print(f"✓ Memory and todo integration tested (memory: {memory_found}, todo: {todo_found})")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"Memory integration test failed: {e}")
            return False
    
    def test_performance_benchmarks(self, agents_dir: Path) -> bool:
        """Test performance benchmarks for instruction synthesis."""
        print("Testing performance benchmarks...")
        
        try:
            synthesizer = SimpleInstructionsSynthesizer(agents_dir=agents_dir)
            
            # Benchmark multiple synthesis runs
            times = []
            instruction_sizes = []
            
            for i in range(5):
                start_time = time.perf_counter()
                instructions = synthesizer.synthesize()
                end_time = time.perf_counter()
                
                times.append(end_time - start_time)
                instruction_sizes.append(len(instructions))
            
            avg_time = sum(times) / len(times)
            avg_size = sum(instruction_sizes) / len(instruction_sizes)
            
            self.test_results["performance_metrics"]["avg_synthesis_time"] = avg_time
            self.test_results["performance_metrics"]["avg_instruction_size"] = avg_size
            self.test_results["performance_metrics"]["synthesis_runs"] = len(times)
            
            # Performance thresholds (reasonable for file I/O operations)
            if avg_time > 2.0:  # Should take less than 2 seconds
                self.test_results["warnings"].append(f"Synthesis performance slow: {avg_time:.3f}s average")
            
            if avg_size < 1000:  # Should generate substantial content
                self.test_results["warnings"].append(f"Generated instructions small: {avg_size} chars average")
            
            print(f"✓ Performance benchmarks completed ({avg_time:.3f}s avg, {avg_size} chars avg)")
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
        """Run all instruction injection tests."""
        print("=" * 60)
        print("INSTRUCTION INJECTION SYSTEM TESTS")
        print("=" * 60)
        
        try:
            # Setup test environment
            temp_dir, agents_dir = self.setup_test_environment()
            
            # Run all tests
            tests = [
                ("Basic Synthesis", lambda: self.test_basic_synthesis(agents_dir)),
                ("Agent-Specific Injection", lambda: self.test_agent_specific_injection(agents_dir)),
                ("Frontmatter Format", lambda: self.test_frontmatter_format(agents_dir)),
                ("Dynamic Capabilities", lambda: self.test_dynamic_capabilities_injection(agents_dir)),
                ("Memory Integration", lambda: self.test_memory_integration(agents_dir)),
                ("Performance Benchmarks", lambda: self.test_performance_benchmarks(agents_dir))
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
        print("INSTRUCTION INJECTION TEST RESULTS")
        print("=" * 60)
        
        total_tests = self.test_results["passed"] + self.test_results["failed"]
        pass_rate = (self.test_results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {self.test_results['passed']}")
        print(f"Failed: {self.test_results['failed']}")
        print(f"Pass Rate: {pass_rate:.1f}%")
        
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
    tester = InstructionInjectionTester()
    results = tester.run_all_tests()
    tester.print_results()
    
    # Exit with appropriate code
    sys.exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()