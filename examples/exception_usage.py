#!/usr/bin/env python3
"""
Example demonstrating the use of Claude MPM's centralized exception hierarchy.

This example shows how to properly use the exception classes for better error
handling and debugging across the codebase.
"""

import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.exceptions import (
    ALL_MPM_ERRORS,
    CONFIGURATION_ERRORS,
    AgentDeploymentError,
    ConfigurationError,
    ConnectionError,
    HookError,
    MemoryError,
    ServiceNotFoundError,
    SessionError,
    ValidationError,
)


def example_agent_deployment():
    """Example of handling agent deployment errors."""
    print("\n=== Agent Deployment Error Example ===")

    try:
        # Simulate agent deployment failure
        raise AgentDeploymentError(
            "Failed to deploy agent: template file not found",
            context={
                "agent_id": "engineer",
                "template_path": "/agents/engineer.json",
                "deployment_path": ".claude/agents/engineer.md",
            },
        )
    except AgentDeploymentError as e:
        print(f"Deployment failed: {e}")
        print(f"Error code: {e.error_code}")
        print(f"Context: {json.dumps(e.context, indent=2)}")
        print(f"Full error dict: {json.dumps(e.to_dict(), indent=2)}")


def example_configuration_validation():
    """Example of configuration validation with detailed errors."""
    print("\n=== Configuration Validation Example ===")

    try:
        # Simulate configuration validation failure
        raise ConfigurationError(
            "Invalid agent configuration",
            context={
                "config_file": "config.yaml",
                "field": "timeout",
                "expected_type": "int",
                "actual_value": "not_a_number",
            },
        )
    except ConfigurationError as e:
        print(f"Configuration error: {e}")
        # The error message includes helpful context automatically


def example_connection_handling():
    """Example of handling connection errors with retry logic."""
    print("\n=== Connection Error Example ===")

    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Simulate connection attempt
            if retry_count < 2:
                raise ConnectionError(
                    "Failed to connect to Socket.IO server",
                    context={
                        "host": "localhost",
                        "port": 8765,
                        "timeout": 30,
                        "retry_count": retry_count + 1,
                    },
                )
            print("Connection successful!")
            break

        except ConnectionError as e:
            retry_count += 1
            print(f"Connection attempt {retry_count} failed: {e}")
            if retry_count >= max_retries:
                print("Max retries reached, giving up")
                raise


def example_validation_with_schema():
    """Example of validation errors with schema information."""
    print("\n=== Validation Error Example ===")

    try:
        # Simulate schema validation failure
        raise ValidationError(
            "Agent definition missing required fields",
            context={
                "field": "version",
                "constraint": "required field",
                "value": None,
                "schema_path": "/schemas/agent_v2.json",
            },
        )
    except ValidationError as e:
        print(f"Validation failed: {e}")


def example_service_discovery():
    """Example of service discovery errors."""
    print("\n=== Service Discovery Example ===")

    try:
        # Simulate service not found
        raise ServiceNotFoundError(
            "Requested service not registered in container",
            context={
                "service_name": "CustomAnalyzer",
                "service_type": "IAnalyzer",
                "available_services": [
                    "DefaultAnalyzer",
                    "TreeSitterAnalyzer",
                    "RegexAnalyzer",
                    "ASTAnalyzer",
                ],
            },
        )
    except ServiceNotFoundError as e:
        print(f"Service error: {e}")


def example_memory_operations():
    """Example of memory service errors."""
    print("\n=== Memory Service Example ===")

    try:
        # Simulate memory operation failure
        raise MemoryError(
            "Failed to store agent memory: disk quota exceeded",
            context={
                "agent_id": "research",
                "memory_type": "long_term",
                "operation": "write",
                "storage_path": "/data/memories/research",
                "size_mb": 512,
                "quota_mb": 500,
            },
        )
    except MemoryError as e:
        print(f"Memory operation failed: {e}")
        print(f"Context details: {json.dumps(e.context, indent=2)}")


def example_hook_execution():
    """Example of hook execution errors."""
    print("\n=== Hook Execution Example ===")

    try:
        # Simulate hook failure
        raise HookError(
            "Pre-deployment hook failed",
            context={
                "hook_name": "validate_agent",
                "hook_type": "pre",
                "event": "agent_deployment",
                "error_details": "Agent schema validation failed: version field missing",
            },
        )
    except HookError as e:
        print(f"Hook failed: {e}")


def example_session_management():
    """Example of session management errors."""
    print("\n=== Session Management Example ===")

    try:
        # Simulate session error
        raise SessionError(
            "Failed to initialize interactive session",
            context={
                "session_id": "sess_abc123",
                "session_type": "interactive",
                "state": "initializing",
                "operation": "create",
                "reason": "Resource allocation failed",
            },
        )
    except SessionError as e:
        print(f"Session error: {e}")


def example_error_groups():
    """Example of using error groups for catch-all handling."""
    print("\n=== Error Groups Example ===")

    def process_configuration():
        """Function that might raise configuration-related errors."""
        import random

        if random.choice([True, False]):
            raise ConfigurationError("Invalid config file")
        raise ValidationError("Schema validation failed")

    try:
        process_configuration()
    except CONFIGURATION_ERRORS as e:
        # Catches both ConfigurationError and ValidationError
        print(f"Configuration-related error caught: {e}")
        print(f"Error type: {type(e).__name__}")

    # Catch all MPM errors
    try:
        raise HookError("Some hook failed")
    except ALL_MPM_ERRORS as e:
        print(f"MPM error caught: {e}")
        print(f"Error code: {e.error_code}")


def example_error_context_usage():
    """Example showing how to use error context for debugging."""
    print("\n=== Error Context Usage Example ===")

    def deploy_agent(agent_id: str, template_path: str):
        """Deploy an agent with proper error handling."""
        try:
            # Simulate deployment logic
            if not Path(template_path).exists():
                raise AgentDeploymentError(
                    "Template file not found",
                    context={
                        "agent_id": agent_id,
                        "template_path": template_path,
                        "cwd": str(Path.cwd()),
                        "search_paths": [
                            "/agents/templates",
                            "~/.claude-mpm/agents",
                            ".claude-mpm/agents",
                        ],
                    },
                )
        except AgentDeploymentError as e:
            # Log structured error for monitoring
            error_data = e.to_dict()
            print(f"Structured error for logging: {json.dumps(error_data, indent=2)}")

            # Re-raise with additional context if needed
            raise AgentDeploymentError(
                f"Deployment pipeline failed for {agent_id}",
                context={
                    **e.context,  # Keep original context
                    "pipeline_stage": "template_loading",
                    "timestamp": "2024-01-15T10:30:00Z",
                },
            ) from e

    try:
        deploy_agent("custom_agent", "/nonexistent/template.json")
    except AgentDeploymentError as e:
        print(f"Final error: {e}")
        print(f"Full context: {json.dumps(e.context, indent=2)}")


def main():
    """Run all examples."""
    examples = [
        example_agent_deployment,
        example_configuration_validation,
        example_connection_handling,
        example_validation_with_schema,
        example_service_discovery,
        example_memory_operations,
        example_hook_execution,
        example_session_management,
        example_error_groups,
        example_error_context_usage,
    ]

    for example in examples:
        try:
            example()
        except ALL_MPM_ERRORS as e:
            # Catch any MPM errors that weren't handled in the example
            print(f"\nUnhandled MPM error in {example.__name__}: {e}")
        except Exception as e:
            print(f"\nUnexpected error in {example.__name__}: {e}")

    print("\n=== All examples completed ===")


if __name__ == "__main__":
    main()
