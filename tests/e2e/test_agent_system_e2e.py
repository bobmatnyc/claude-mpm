#!/usr/bin/env python3
"""
Comprehensive End-to-End Tests for the Claude MPM Agent System

This test suite validates the complete agent system lifecycle including:
- Agent discovery and loading
- Multi-agent interactions and handoffs
- Real file operations (not mocked)
- Performance under concurrent operations
- Integration with the hook system

WHY: E2E tests ensure the entire agent system works cohesively in real-world
scenarios, catching integration issues that unit tests might miss. These tests
use actual file I/O and system resources to validate production behavior.

DESIGN DECISIONS:
1. No mocking - Tests use real file operations to catch actual I/O issues
2. Isolation - Each test creates its own temporary environment
3. Performance validation - Includes concurrent operation tests
4. Full lifecycle coverage - Tests complete workflows from discovery to cleanup

METRICS TRACKED:
- Agent discovery and loading times
- Cache hit rates during operations
- Memory usage patterns
- Concurrent operation performance
- Error rates and types
"""

import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from claude_mpm.agents.agent_loader import (
    AgentLoader,
    clear_agent_cache,
    get_agent_prompt_with_model_info,
    validate_agent_files,
)
from claude_mpm.services.agents.deployment import AgentDeploymentService
from claude_mpm.services.agents.registry import DeployedAgentDiscovery

# Skip AgentLifecycleManager due to missing dependencies
# from claude_mpm.services.agents.deployment import AgentLifecycleManager
from claude_mpm.services.memory.cache.shared_prompt_cache import SharedPromptCache
from claude_mpm.validation.agent_validator import AgentValidator

# Test logger
logger = logging.getLogger(__name__)


class TestAgentSystemE2E:
    """Comprehensive E2E tests for the agent system."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """
        Set up test environment with temporary directories and clean state.

        WHY: Each test needs an isolated environment to ensure:
        - No interference between tests
        - Clean state for predictable results
        - Easy cleanup after test completion
        """
        # Create temporary directories for testing
        self.test_dir = tmp_path / "agent_test"
        self.test_dir.mkdir()

        self.agents_dir = self.test_dir / "agents"
        self.agents_dir.mkdir()

        self.templates_dir = self.test_dir / "templates"
        self.templates_dir.mkdir()

        self.claude_dir = self.test_dir / ".claude"
        self.claude_agents_dir = self.claude_dir / "agents"
        self.claude_agents_dir.mkdir(parents=True)

        # Clear any existing cache to ensure clean state
        cache = SharedPromptCache.get_instance()
        cache.clear()

        # Store original environment for restoration
        self.original_env = os.environ.copy()

        # Performance tracking for tests
        self.performance_metrics = {
            "test_start_time": time.time(),
            "operation_times": {},
            "memory_snapshots": [],
            "error_counts": {},
        }

        yield

        # Cleanup after test
        os.environ.clear()
        os.environ.update(self.original_env)

        # Record test duration
        self.performance_metrics["test_duration"] = (
            time.time() - self.performance_metrics["test_start_time"]
        )

    def create_test_agent(
        self, agent_id: str, name: str, category: str = "engineering"
    ) -> Dict[str, Any]:
        """
        Create a test agent JSON template.

        WHY: We need realistic agent configurations for testing that:
        - Follow the actual schema
        - Include all required fields
        - Can be customized for specific test scenarios
        """
        agent_data = {
            "schema_version": "1.2.0",
            "agent_id": agent_id,
            "agent_version": "1.0.0",
            "agent_type": "engineer",
            "metadata": {
                "name": name,
                "description": f"Test agent for {name}",
                "category": category,
                "display_name": name,
                "tags": ["test"],
                "status": "active",
            },
            "capabilities": {
                "model": "claude-sonnet-4-20250514",
                "resource_tier": "standard",
                "tools": ["Read", "Write", "Grep"],
                "output_formats": ["markdown", "json"],
                "context_window": 200000,
                "supports_streaming": True,
                "supports_images": False,
                "supports_artifacts": True,
                "features": ["code_generation", "testing"],
            },
            "instructions": f"You are a test {name} agent designed for E2E testing of the Claude MPM agent system. "
            f"Your primary purpose is to validate agent loading, discovery, and lifecycle management. "
            f"When activated, respond with 'Test {agent_id} active'. "
            f"This agent is part of the comprehensive test suite ensuring system reliability.",
            "knowledge": {"domain_expertise": ["testing"], "required_context": []},
            "interactions": {
                "user_interaction": "batch",
                "requires_approval": False,
                "interaction_style": "concise",
            },
        }

        # Write to templates directory
        template_path = self.templates_dir / f"{agent_id}.json"
        with open(template_path, "w") as f:
            json.dump(agent_data, f, indent=2)

        return agent_data

    def test_agent_discovery_and_loading():
        """
        Test complete agent discovery and loading lifecycle.

        VALIDATES:
        - Agent discovery from template directory
        - Schema validation during loading
        - Registry population
        - Error handling for invalid agents
        """
        start_time = time.time()

        # Create test agents
        self.create_test_agent("test_agent_1", "Test Agent 1")
        self.create_test_agent("test_agent_2", "Test Agent 2", "research")

        # Create an invalid agent to test error handling
        invalid_agent = {
            "agent_id": "invalid_agent",
            # Missing required fields to trigger validation error
            "metadata": {"name": "Invalid"},
        }
        with open(self.templates_dir / "invalid_agent.json", "w") as f:
            json.dump(invalid_agent, f)

        # Create a custom loader that uses our test directory
        class TestAgentLoader(AgentLoader):
            def _load_agents(self):
                """Override to use test templates directory."""
                logger.info(f"Loading agents from {self.templates_dir}")

                for json_file in self.templates_dir.glob("*.json"):
                    # Skip the schema definition file itself
                    if json_file.name == "agent_schema.json":
                        continue

                    try:
                        with open(json_file) as f:
                            agent_data = json.load(f)

                        # Validate against schema to ensure consistency
                        validation_result = self.validator.validate_agent(agent_data)

                        if validation_result.is_valid:
                            agent_id = agent_data.get("agent_id")
                            if agent_id:
                                self._agent_registry[agent_id] = agent_data
                                # METRICS: Track successful agent load
                                self._metrics["agents_loaded"] += 1
                                logger.debug(f"Loaded agent: {agent_id}")
                        else:
                            # Log validation errors but continue loading other agents
                            # METRICS: Track validation failure
                            self._metrics["validation_failures"] += 1
                            logger.warning(
                                f"Invalid agent in {json_file.name}: {validation_result.errors}"
                            )

                    except Exception as e:
                        # Log loading errors but don't crash - system should be resilient
                        logger.error(f"Failed to load {json_file.name}: {e}")

        # Initialize test loader
        loader = TestAgentLoader.__new__(TestAgentLoader)
        loader.templates_dir = self.templates_dir
        loader.validator = AgentValidator()
        loader.cache = SharedPromptCache.get_instance()
        loader._agent_registry = {}
        loader._metrics = {
            "agents_loaded": 0,
            "validation_failures": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "initialization_time_ms": 0,
            "usage_counts": {},
            "load_times": {},
            "prompt_sizes": {},
            "model_selections": {},
            "complexity_scores": [],
            "error_types": {},
        }

        # Test discovery
        loader._load_agents()

        # Validate results
        assert (
            loader._metrics["agents_loaded"] == 2
        ), f"Should load 2 valid agents, but loaded {loader._metrics['agents_loaded']}"
        assert (
            loader._metrics["validation_failures"] == 1
        ), "Should have 1 validation failure"
        assert "test_agent_1" in loader._agent_registry
        assert "test_agent_2" in loader._agent_registry
        assert "invalid_agent" not in loader._agent_registry

        # Test agent retrieval
        agent1 = loader.get_agent("test_agent_1")
        assert agent1 is not None
        assert agent1["metadata"]["name"] == "Test Agent 1"

        # Test listing agents
        agents = loader.list_agents()
        assert len(agents) == 2
        assert any(a["id"] == "test_agent_1" for a in agents)

        # Record performance
        self.performance_metrics["operation_times"]["discovery_and_loading"] = (
            time.time() - start_time
        )
        logger.info(
            f"Agent discovery completed in {self.performance_metrics['operation_times']['discovery_and_loading']:.3f}s"
        )

    def test_agent_prompt_caching_and_performance():
        """
        Test agent prompt caching mechanism and performance.

        VALIDATES:
        - Cache miss on first access
        - Cache hit on subsequent access
        - Force reload functionality
        - Performance improvement with caching
        """
        # Create test agent
        self.create_test_agent("cache_test_agent", "Cache Test")

        # Initialize loader
        loader = AgentLoader.__new__(AgentLoader)
        loader.templates_dir = self.templates_dir
        loader.validator = AgentValidator()
        loader.cache = SharedPromptCache.get_instance()
        loader._agent_registry = {}
        loader._metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "usage_counts": {},
            "load_times": {},
            "prompt_sizes": {},
        }
        loader._load_agents()

        # First access - cache miss
        start_time = time.time()
        prompt1 = loader.get_agent_prompt("cache_test_agent")
        first_load_time = time.time() - start_time

        assert prompt1 is not None
        assert loader._metrics["cache_misses"] == 1
        assert loader._metrics["cache_hits"] == 0

        # Second access - cache hit
        start_time = time.time()
        prompt2 = loader.get_agent_prompt("cache_test_agent")
        cached_load_time = time.time() - start_time

        assert prompt2 == prompt1
        assert loader._metrics["cache_hits"] == 1
        assert cached_load_time < first_load_time, "Cached access should be faster"

        # Force reload
        prompt3 = loader.get_agent_prompt("cache_test_agent", force_reload=True)
        assert prompt3 == prompt1
        assert loader._metrics["cache_misses"] == 2

        # Performance metrics
        logger.info(
            f"First load: {first_load_time:.6f}s, Cached load: {cached_load_time:.6f}s"
        )
        logger.info(f"Cache speedup: {first_load_time/cached_load_time:.2f}x")

    def test_multi_agent_deployment_lifecycle():
        """
        Test complete lifecycle of deploying multiple agents.

        VALIDATES:
        - Agent template to Markdown conversion
        - Deployment to .claude/agents directory
        - Version tracking and updates
        - Cleanup operations
        """
        # Create multiple test agents
        agents = [
            ("deploy_agent_1", "Deploy Test 1"),
            ("deploy_agent_2", "Deploy Test 2"),
            ("deploy_agent_3", "Deploy Test 3"),
        ]

        for agent_id, name in agents:
            self.create_test_agent(agent_id, name)

        # Initialize deployment service
        deployment_service = AgentDeploymentService(
            templates_dir=self.templates_dir,
            base_agent_path=None,  # Will use test agents only
        )

        # Deploy agents
        start_time = time.time()
        results = deployment_service.deploy_agents(
            target_dir=self.claude_agents_dir, force_rebuild=False
        )
        deployment_time = time.time() - start_time

        # Validate deployment results
        assert len(results["deployed"]) == 3
        assert len(results["errors"]) == 0
        assert results["total"] == 3

        # Verify files were created
        for agent_id, _ in agents:
            md_path = self.claude_agents_dir / f"{agent_id}.md"
            assert md_path.exists(), f"Agent {agent_id} Markdown should exist"

            # Validate Markdown structure
            with open(md_path) as f:
                yaml_data = yaml.safe_load(f)
                assert "name" in yaml_data
                assert "instructions" in yaml_data

        # Test redeployment (should skip unchanged agents)
        results2 = deployment_service.deploy_agents(
            target_dir=self.claude_agents_dir, force_rebuild=False
        )
        assert len(results2["skipped"]) == 3
        assert len(results2["deployed"]) == 0

        # Record performance
        self.performance_metrics["operation_times"]["deployment"] = deployment_time
        logger.info(f"Deployed {len(agents)} agents in {deployment_time:.3f}s")

    def test_concurrent_agent_operations():
        """
        Test agent system under concurrent load.

        VALIDATES:
        - Thread safety of agent loading
        - Cache consistency under concurrent access
        - Performance under parallel operations
        - No race conditions or deadlocks
        """
        # Create test agents
        num_agents = 10
        for i in range(num_agents):
            self.create_test_agent(f"concurrent_agent_{i}", f"Concurrent Test {i}")

        # Initialize shared loader
        loader = AgentLoader.__new__(AgentLoader)
        loader.templates_dir = self.templates_dir
        loader.validator = AgentValidator()
        loader.cache = SharedPromptCache.get_instance()
        loader._agent_registry = {}
        loader._metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "usage_counts": {},
            "load_times": {},
            "prompt_sizes": {},
        }
        loader._load_agents()

        # Concurrent access test
        def access_agent(agent_id: str, iterations: int = 5):
            """Access agent multiple times to test caching."""
            results = []
            for i in range(iterations):
                start = time.time()
                prompt = loader.get_agent_prompt(agent_id)
                duration = time.time() - start
                results.append(
                    {
                        "agent_id": agent_id,
                        "iteration": i,
                        "duration": duration,
                        "prompt_length": len(prompt) if prompt else 0,
                    }
                )
            return results

        # Run concurrent operations
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(num_agents):
                agent_id = f"concurrent_agent_{i}"
                future = executor.submit(access_agent, agent_id)
                futures.append(future)

            # Collect results
            all_results = []
            for future in as_completed(futures):
                all_results.extend(future.result())

        concurrent_duration = time.time() - start_time

        # Validate results
        assert len(all_results) == num_agents * 5

        # Check cache effectiveness
        cache_hit_rate = loader._metrics["cache_hits"] / (
            loader._metrics["cache_hits"] + loader._metrics["cache_misses"]
        )
        assert (
            cache_hit_rate > 0.7
        ), f"Cache hit rate {cache_hit_rate:.2%} should be > 70%"

        # Performance analysis
        avg_duration = sum(r["duration"] for r in all_results) / len(all_results)
        logger.info(f"Concurrent test: {num_agents} agents, 5 iterations each")
        logger.info(f"Total duration: {concurrent_duration:.3f}s")
        logger.info(f"Average access time: {avg_duration:.6f}s")
        logger.info(f"Cache hit rate: {cache_hit_rate:.2%}")

    def test_agent_lifecycle_manager_integration():
        """
        Test the complete agent lifecycle management.

        VALIDATES:
        - Agent versioning and updates
        - Migration between versions
        - Rollback capabilities
        - State consistency
        """
        # Skip this test due to missing AgentLifecycleManager dependencies
        pytest.skip("AgentLifecycleManager has missing dependencies")

        # # Create initial agent version
        # agent_v1 = self.create_test_agent("lifecycle_agent", "Lifecycle Test")
        #
        # # Initialize lifecycle manager
        # lifecycle_manager = AgentLifecycleManager()
        #
        # # Deploy initial version
        # deployment_service = AgentDeploymentService(
        #     templates_dir=self.templates_dir
        # )
        # deployment_service.deploy_agents(self.claude_agents_dir)
        #
        # # Update agent version
        # agent_v1["version"] = "1.1.0"
        # agent_v1["instructions"] = "Updated instructions for v1.1.0"
        # with open(self.templates_dir / "lifecycle_agent.json", 'w') as f:
        #     json.dump(agent_v1, f, indent=2)
        #
        # # Deploy update
        # update_results = deployment_service.deploy_agents(self.claude_agents_dir)
        # assert len(update_results['updated']) == 1
        #
        # # Verify version update
        # yaml_path = self.claude_agents_dir / "lifecycle_agent.yaml"
        # with open(yaml_path, 'r') as f:
        #     yaml_data = yaml.safe_load(f)
        #     assert "v1.1.0" in yaml_data.get('instructions', '')

    def test_agent_discovery_service_integration():
        """
        Test deployed agent discovery service.

        VALIDATES:
        - Discovery of deployed agents
        - Agent metadata extraction
        - Filtering and search capabilities
        - Performance with many agents
        """
        # Deploy multiple agents
        num_discovery_agents = 15
        for i in range(num_discovery_agents):
            category = "analysis" if i % 3 == 0 else "test"
            self.create_test_agent(
                f"discovery_agent_{i}", f"Discovery Test {i}", category
            )

        # Deploy all agents
        deployment_service = AgentDeploymentService(templates_dir=self.templates_dir)
        deployment_service.deploy_agents(self.claude_agents_dir)

        # Initialize discovery service
        discovery_service = DeployedAgentDiscovery(agents_dir=self.claude_agents_dir)

        # Test discovery
        start_time = time.time()
        discovered_agents = discovery_service.discover_agents()
        discovery_time = time.time() - start_time

        # Validate discovery results
        assert len(discovered_agents) == num_discovery_agents

        # Test filtering by category
        analysis_agents = [
            a for a in discovered_agents if a.get("category") == "analysis"
        ]
        assert len(analysis_agents) == 5  # 15 agents, every 3rd is 'analysis'

        # Performance check
        assert (
            discovery_time < 1.0
        ), f"Discovery of {num_discovery_agents} agents took {discovery_time:.3f}s (should be < 1s)"
        logger.info(
            f"Discovered {num_discovery_agents} agents in {discovery_time:.3f}s"
        )

    def test_error_handling_and_recovery():
        """
        Test error handling and recovery mechanisms.

        VALIDATES:
        - Graceful handling of corrupted agents
        - Recovery from partial deployments
        - Logging of errors
        - System stability under errors
        """
        # Create corrupted agent file
        corrupted_path = self.templates_dir / "corrupted.json"
        with open(corrupted_path, "w") as f:
            f.write("{ invalid json")

        # Create agent with missing required fields
        incomplete_agent = {"agent_id": "incomplete"}
        with open(self.templates_dir / "incomplete.json", "w") as f:
            json.dump(incomplete_agent, f)

        # Create valid agent
        self.create_test_agent("valid_agent", "Valid Agent")

        # Test loader resilience
        loader = AgentLoader.__new__(AgentLoader)
        loader.templates_dir = self.templates_dir
        loader.validator = AgentValidator()
        loader.cache = SharedPromptCache.get_instance()
        loader._agent_registry = {}
        loader._metrics = {"agents_loaded": 0, "validation_failures": 0}

        # Should not crash on corrupted files
        loader._load_agents()

        # Valid agent should still be loaded
        assert "valid_agent" in loader._agent_registry
        assert loader._metrics["agents_loaded"] == 1

        # Test deployment resilience
        deployment_service = AgentDeploymentService(templates_dir=self.templates_dir)
        results = deployment_service.deploy_agents(self.claude_agents_dir)

        # Should deploy valid agent despite errors
        assert len(results["deployed"]) >= 1
        assert len(results["errors"]) >= 2

    def test_agent_handoff_simulation():
        """
        Test multi-agent handoff scenarios.

        VALIDATES:
        - Agent communication patterns
        - State preservation during handoffs
        - Performance of multi-agent workflows

        WHY: While agents don't directly communicate in the current system,
        this test simulates workflow patterns where one agent's output
        feeds into another agent's input.
        """
        # Create specialized agents for a workflow
        agents_workflow = [
            ("research_test", "Research", "analysis"),
            ("engineer_test", "Engineer", "implementation"),
            ("qa_test", "QA", "validation"),
        ]

        for agent_id, name, category in agents_workflow:
            self.create_test_agent(agent_id, name, category)

        # Initialize system
        loader = AgentLoader.__new__(AgentLoader)
        loader.templates_dir = self.templates_dir
        loader.validator = AgentValidator()
        loader.cache = SharedPromptCache.get_instance()
        loader._agent_registry = {}
        loader._metrics = {
            "usage_counts": {},
            "cache_hits": 0,
            "cache_misses": 0,
            "model_selections": {},
        }
        loader._load_agents()

        # Simulate workflow: Research -> Engineer -> QA
        workflow_start = time.time()
        workflow_results = []

        # Step 1: Research agent analyzes requirements
        (
            research_prompt,
            research_model,
            research_config,
        ) = get_agent_prompt_with_model_info(
            "research_test",
            task_description="Analyze codebase for optimization opportunities",
            context_size=5000,
        )
        workflow_results.append(
            {
                "agent": "research_test",
                "prompt_size": len(research_prompt),
                "model": research_model,
            }
        )

        # Step 2: Engineer agent implements based on research
        (
            engineer_prompt,
            engineer_model,
            engineer_config,
        ) = get_agent_prompt_with_model_info(
            "engineer_test",
            task_description="Implement performance optimizations identified by research",
            context_size=10000,
        )
        workflow_results.append(
            {
                "agent": "engineer_test",
                "prompt_size": len(engineer_prompt),
                "model": engineer_model,
            }
        )

        # Step 3: QA agent validates implementation
        qa_prompt, qa_model, qa_config = get_agent_prompt_with_model_info(
            "qa_test",
            task_description="Validate performance improvements and test coverage",
            context_size=3000,
        )
        workflow_results.append(
            {"agent": "qa_test", "prompt_size": len(qa_prompt), "model": qa_model}
        )

        workflow_duration = time.time() - workflow_start

        # Validate workflow execution
        assert len(workflow_results) == 3
        for result in workflow_results:
            assert result["prompt_size"] > 0
            assert result["model"] is not None

        # Check usage tracking
        assert loader._metrics["usage_counts"].get("research_test", 0) >= 1
        assert loader._metrics["usage_counts"].get("engineer_test", 0) >= 1
        assert loader._metrics["usage_counts"].get("qa_test", 0) >= 1

        logger.info(f"Workflow simulation completed in {workflow_duration:.3f}s")
        logger.info(f"Workflow steps: {[r['agent'] for r in workflow_results]}")

    def test_memory_and_resource_usage():
        """
        Test memory and resource usage patterns.

        VALIDATES:
        - Memory efficiency with many agents
        - Cache memory management
        - Resource cleanup

        WHY: Important for production deployments where memory
        constraints and resource leaks can impact stability.
        """
        import gc

        import psutil

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create many agents to test memory scaling
        num_memory_agents = 50
        for i in range(num_memory_agents):
            agent_data = self.create_test_agent(f"memory_test_{i}", f"Memory Test {i}")
            # Add large instructions to increase memory usage
            agent_data["instructions"] = "x" * 10000  # 10KB per agent
            with open(self.templates_dir / f"memory_test_{i}.json", "w") as f:
                json.dump(agent_data, f)

        # Load all agents
        loader = AgentLoader.__new__(AgentLoader)
        loader.templates_dir = self.templates_dir
        loader.validator = AgentValidator()
        loader.cache = SharedPromptCache.get_instance()
        loader._agent_registry = {}
        loader._load_agents()

        loaded_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Access all agents to populate cache
        for i in range(num_memory_agents):
            loader.get_agent_prompt(f"memory_test_{i}")

        cached_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Clear cache and force garbage collection
        clear_agent_cache()
        gc.collect()

        cleared_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Analyze memory usage
        load_increase = loaded_memory - initial_memory
        cache_increase = cached_memory - loaded_memory
        cleanup_reduction = cached_memory - cleared_memory

        logger.info(f"Memory usage analysis ({num_memory_agents} agents):")
        logger.info(f"  Initial: {initial_memory:.1f} MB")
        logger.info(
            f"  After loading: {loaded_memory:.1f} MB (+{load_increase:.1f} MB)"
        )
        logger.info(
            f"  After caching: {cached_memory:.1f} MB (+{cache_increase:.1f} MB)"
        )
        logger.info(
            f"  After cleanup: {cleared_memory:.1f} MB (-{cleanup_reduction:.1f} MB)"
        )

        # Validate reasonable memory usage
        avg_memory_per_agent = (cached_memory - initial_memory) / num_memory_agents
        assert (
            avg_memory_per_agent < 1.0
        ), f"Average memory per agent {avg_memory_per_agent:.2f} MB is too high"

    def test_production_readiness_checks():
        """
        Comprehensive production readiness validation.

        VALIDATES:
        - System stability over time
        - Error recovery mechanisms
        - Performance consistency
        - Logging and monitoring
        """
        # Create production-like agent set
        prod_agents = [
            ("prod_research", "Research Agent", "analysis"),
            ("prod_engineer", "Engineer Agent", "implementation"),
            ("prod_qa", "QA Agent", "validation"),
            ("prod_security", "Security Agent", "security"),
            ("prod_ops", "Ops Agent", "operations"),
        ]

        for agent_id, name, category in prod_agents:
            self.create_test_agent(agent_id, name, category)

        # Test repeated operations for stability
        operation_count = 100
        errors = []
        durations = []

        loader = AgentLoader.__new__(AgentLoader)
        loader.templates_dir = self.templates_dir
        loader.validator = AgentValidator()
        loader.cache = SharedPromptCache.get_instance()
        loader._agent_registry = {}
        loader._metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "usage_counts": {},
            "error_types": {},
        }
        loader._load_agents()

        for i in range(operation_count):
            try:
                start = time.time()

                # Simulate production operations
                agent_id = prod_agents[i % len(prod_agents)][0]
                loader.get_agent_prompt(agent_id)

                # Validate agent files periodically
                if i % 20 == 0:
                    validate_agent_files()

                # Simulate cache clearing (like during deployments)
                if i % 50 == 0:
                    clear_agent_cache(agent_id)

                duration = time.time() - start
                durations.append(duration)

            except Exception as e:
                errors.append((i, str(e)))
                loader._metrics["error_types"][type(e).__name__] = (
                    loader._metrics["error_types"].get(type(e).__name__, 0) + 1
                )

        # Analyze results
        error_rate = len(errors) / operation_count
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)

        # Get final metrics
        final_metrics = loader.get_metrics()

        logger.info(
            f"Production readiness test results ({operation_count} operations):"
        )
        logger.info(f"  Error rate: {error_rate:.2%}")
        logger.info(f"  Average duration: {avg_duration:.6f}s")
        logger.info(f"  Max duration: {max_duration:.6f}s")
        logger.info(f"  Cache hit rate: {final_metrics['cache_hit_rate_percent']:.1f}%")
        logger.info(f"  Error types: {final_metrics['error_types']}")

        # Production criteria
        assert error_rate < 0.01, f"Error rate {error_rate:.2%} exceeds 1% threshold"
        assert (
            avg_duration < 0.1
        ), f"Average duration {avg_duration:.3f}s exceeds 100ms threshold"
        assert final_metrics["cache_hit_rate_percent"] > 80, "Cache hit rate below 80%"


def test_hook_system_integration():
    """
    Test integration between agent system and hook system.

    VALIDATES:
    - Hook system can discover deployed agents
    - Agent commands work through hooks
    - Performance impact of hook integration

    WHY: The hook system is a key integration point that allows
    Claude Code to interact with the agent system.
    """
    with tmp_path as temp_dir:
        temp_path = Path(temp_dir)
        claude_dir = temp_path / ".claude"
        agents_dir = claude_dir / "agents"
        agents_dir.mkdir(parents=True)

        # Create and deploy test agents
        templates_dir = temp_path / "templates"
        templates_dir.mkdir()

        # Create test agent
        agent_data = {
            "agent_id": "hook_test_agent",
            "version": "1.0.0",
            "metadata": {
                "name": "Hook Test Agent",
                "description": "Agent for hook system testing",
                "category": "test",
            },
            "capabilities": {
                "model": "claude-sonnet-4-20250514",
                "resource_tier": "standard",
                "tools": ["code_analysis"],
            },
            "instructions": "Test agent for hook system integration.",
            "knowledge": {"domain_expertise": ["testing"]},
            "interactions": {"user_interaction": "batch"},
        }

        with open(templates_dir / "hook_test_agent.json", "w") as f:
            json.dump(agent_data, f)

        # Deploy agent
        deployment_service = AgentDeploymentService(templates_dir=templates_dir)
        deployment_results = deployment_service.deploy_agents(agents_dir)

        assert len(deployment_results["deployed"]) == 1

        # Simulate hook system discovering agents
        # In real system, this would be done by ClaudeHookHandler
        md_files = list(agents_dir.glob("*.md"))
        assert len(md_files) == 1

        # Verify agent Markdown is readable by hook system
        with open(md_files[0]) as f:
            yaml_content = yaml.safe_load(f)
            assert yaml_content["name"] == "Hook Test Agent"
            assert "instructions" in yaml_content


if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([__file__, "-v", "-s", "--tb=short"])
