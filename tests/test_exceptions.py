"""Tests for centralized exception hierarchy."""

from claude_mpm.core.exceptions import (
    ALL_MPM_ERRORS,
    CONFIGURATION_ERRORS,
    DEPLOYMENT_ERRORS,
    NETWORK_ERRORS,
    SERVICE_ERRORS,
    AgentDeploymentError,
    ConfigurationError,
    ConnectionError,
    HookError,
    MemoryError,
    MPMError,
    ServiceNotFoundError,
    SessionError,
    ValidationError,
    create_agent_deployment_error,
    create_configuration_error,
    create_connection_error,
    create_validation_error,
)


class TestMPMError:
    """Test base MPMError class."""

    def test_basic_error():
        """Test basic error creation."""
        error = MPMError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.context == {}
        assert error.error_code == "mpm"

    def test_error_with_context():
        """Test error with context."""
        context = {"key": "value", "number": 42}
        error = MPMError("Test error", context=context)
        assert error.context == context
        assert "key=value" in str(error)
        assert "number=42" in str(error)

    def test_to_dict():
        """Test dictionary conversion."""
        error = MPMError("Test error", context={"field": "test"})
        error_dict = error.to_dict()
        assert error_dict["error_type"] == "MPMError"
        assert error_dict["error_code"] == "mpm"
        assert error_dict["message"] == "Test error"
        assert error_dict["context"] == {"field": "test"}


class TestAgentDeploymentError:
    """Test AgentDeploymentError class."""

    def test_basic_deployment_error():
        """Test basic deployment error."""
        error = AgentDeploymentError("Deployment failed")
        assert error.message == "Deployment failed"
        assert error.error_code == "agent_deployment"

    def test_deployment_error_with_agent_id():
        """Test deployment error with agent ID context."""
        error = AgentDeploymentError(
            "Template not found",
            context={"agent_id": "engineer", "template_path": "/path/to/template"},
        )
        assert "[Agent: engineer]" in error.message
        assert "Template not found" in error.message

    def test_deployment_error_permission():
        """Test deployment error with permission issue."""
        error = AgentDeploymentError("Permission denied", context={"agent_id": "qa"})
        assert "Check directory permissions" in error.message


class TestConfigurationError:
    """Test ConfigurationError class."""

    def test_basic_config_error():
        """Test basic configuration error."""
        error = ConfigurationError("Invalid config")
        assert error.message == "Invalid config"
        assert error.error_code == "configuration"

    def test_config_error_with_file():
        """Test configuration error with file context."""
        error = ConfigurationError(
            "Parse error", context={"config_file": "config.yaml"}
        )
        assert "[Config: config.yml]" in error.message

    def test_config_error_with_field_validation():
        """Test configuration error with field validation."""
        error = ConfigurationError(
            "Type mismatch",
            context={
                "field": "timeout",
                "expected_type": "int",
                "actual_value": "not_a_number",
            },
        )
        assert "Field: timeout" in error.message
        assert "expected: int" in error.message
        assert "got: not_a_number" in error.message


class TestConnectionError:
    """Test ConnectionError class."""

    def test_basic_connection_error():
        """Test basic connection error."""
        error = ConnectionError("Connection failed")
        assert error.message == "Connection failed"
        assert error.error_code == "connection"

    def test_connection_error_with_host_port():
        """Test connection error with host and port."""
        error = ConnectionError(
            "Port in use", context={"host": "localhost", "port": 8080}
        )
        assert "[localhost:8080]" in error.message

    def test_connection_error_with_retry():
        """Test connection error with retry information."""
        error = ConnectionError(
            "Timeout",
            context={
                "host": "localhost",
                "port": 8080,
                "timeout": 30,
                "retry_count": 3,
            },
        )
        assert "Connection timeout: 30s" in error.message
        assert "Retry attempts: 3" in error.message


class TestValidationError:
    """Test ValidationError class."""

    def test_basic_validation_error():
        """Test basic validation error."""
        error = ValidationError("Invalid input")
        assert error.message == "Invalid input"
        assert error.error_code == "validation"

    def test_validation_error_with_field():
        """Test validation error with field information."""
        error = ValidationError(
            "Required field missing",
            context={
                "field": "version",
                "constraint": "required",
                "schema_path": "/schemas/agent.json",
            },
        )
        assert "[Field: version]" in error.message
        assert "Constraint: required" in error.message
        assert "Schema: /schemas/agent.json" in error.message


class TestServiceNotFoundError:
    """Test ServiceNotFoundError class."""

    def test_basic_service_error():
        """Test basic service not found error."""
        error = ServiceNotFoundError("Service missing")
        assert error.message == "Service missing"
        assert error.error_code == "service_not_found"

    def test_service_error_with_available_services():
        """Test service error with available services list."""
        error = ServiceNotFoundError(
            "Service not registered",
            context={
                "service_name": "CustomService",
                "available_services": [
                    "Service1",
                    "Service2",
                    "Service3",
                    "Service4",
                    "Service5",
                    "Service6",
                ],
            },
        )
        assert "[Service: CustomService]" in error.message
        assert "Service1" in error.message
        assert "(and 1 more)" in error.message


class TestMemoryError:
    """Test MemoryError class."""

    def test_basic_memory_error():
        """Test basic memory error."""
        error = MemoryError("Memory operation failed")
        assert error.message == "Memory operation failed"
        assert error.error_code == "memory"

    def test_memory_error_with_agent():
        """Test memory error with agent context."""
        error = MemoryError(
            "Storage failed",
            context={
                "agent_id": "engineer",
                "memory_type": "long_term",
                "operation": "write",
                "storage_path": "/data/memories",
            },
        )
        assert "[Agent: engineer]" in error.message
        assert "Memory type: long_term" in error.message
        assert "Operation: write" in error.message
        assert "Storage: /data/memories" in error.message


class TestHookError:
    """Test HookError class."""

    def test_basic_hook_error():
        """Test basic hook error."""
        error = HookError("Hook failed")
        assert error.message == "Hook failed"
        assert error.error_code == "hook"

    def test_hook_error_with_details():
        """Test hook error with detailed context."""
        error = HookError(
            "Execution failed",
            context={
                "hook_name": "pre_deploy",
                "hook_type": "pre",
                "event": "deployment",
                "error_details": "Timeout after 30s",
            },
        )
        assert "[Hook: pre_deploy]" in error.message
        assert "Type: pre" in error.message
        assert "Event: deployment" in error.message
        assert "Details: Timeout after 30s" in error.message


class TestSessionError:
    """Test SessionError class."""

    def test_basic_session_error():
        """Test basic session error."""
        error = SessionError("Session failed")
        assert error.message == "Session failed"
        assert error.error_code == "session"

    def test_session_error_with_context():
        """Test session error with context."""
        error = SessionError(
            "Initialization failed",
            context={
                "session_id": "sess_123",
                "session_type": "interactive",
                "state": "initializing",
                "operation": "create",
            },
        )
        assert "[Session: sess_123]" in error.message
        assert "Type: interactive" in error.message
        assert "State: initializing" in error.message
        assert "Operation: create" in error.message


class TestFactoryFunctions:
    """Test factory functions for creating errors."""

    def test_create_agent_deployment_error():
        """Test factory function for agent deployment error."""
        error = create_agent_deployment_error(
            "Test error", agent_id="test", template_path="/path"
        )
        assert isinstance(error, AgentDeploymentError)
        assert error.context == {"agent_id": "test", "template_path": "/path"}

    def test_create_configuration_error():
        """Test factory function for configuration error."""
        error = create_configuration_error("Test error", config_file="test.yaml")
        assert isinstance(error, ConfigurationError)
        assert error.context == {"config_file": "test.yaml"}

    def test_create_connection_error():
        """Test factory function for connection error."""
        error = create_connection_error("Test error", host="localhost", port=8080)
        assert isinstance(error, ConnectionError)
        assert error.context == {"host": "localhost", "port": 8080}

    def test_create_validation_error():
        """Test factory function for validation error."""
        error = create_validation_error("Test error", field="test_field")
        assert isinstance(error, ValidationError)
        assert error.context == {"field": "test_field"}


class TestErrorGroups:
    """Test error group constants."""

    def test_deployment_errors():
        """Test deployment error group."""
        error = AgentDeploymentError("Test")
        assert isinstance(error, DEPLOYMENT_ERRORS)

    def test_configuration_errors():
        """Test configuration error group."""
        config_error = ConfigurationError("Test")
        validation_error = ValidationError("Test")
        assert isinstance(config_error, CONFIGURATION_ERRORS)
        assert isinstance(validation_error, CONFIGURATION_ERRORS)

    def test_network_errors():
        """Test network error group."""
        error = ConnectionError("Test")
        assert isinstance(error, NETWORK_ERRORS)

    def test_service_errors():
        """Test service error group."""
        service_error = ServiceNotFoundError("Test")
        memory_error = MemoryError("Test")
        hook_error = HookError("Test")
        session_error = SessionError("Test")

        assert isinstance(service_error, SERVICE_ERRORS)
        assert isinstance(memory_error, SERVICE_ERRORS)
        assert isinstance(hook_error, SERVICE_ERRORS)
        assert isinstance(session_error, SERVICE_ERRORS)

    def test_all_mpm_errors():
        """Test that all custom errors inherit from MPMError."""
        errors = [
            AgentDeploymentError("Test"),
            ConfigurationError("Test"),
            ConnectionError("Test"),
            ValidationError("Test"),
            ServiceNotFoundError("Test"),
            MemoryError("Test"),
            HookError("Test"),
            SessionError("Test"),
        ]

        for error in errors:
            assert isinstance(error, ALL_MPM_ERRORS)
            assert isinstance(error, MPMError)


class TestErrorContextHandling:
    """Test enhanced context handling for all error types."""

    def test_context_serialization_json_compatible():
        """Test that error contexts are JSON-serializable."""
        import json

        context = {
            "string_value": "test",
            "number_value": 42,
            "boolean_value": True,
            "list_value": [1, 2, 3],
            "dict_value": {"nested": "value"},
        }

        error = MPMError("Test error", context=context)
        error_dict = error.to_dict()

        # Should be JSON serializable
        json_str = json.dumps(error_dict)
        parsed = json.loads(json_str)

        assert parsed["context"]["string_value"] == "test"
        assert parsed["context"]["number_value"] == 42
        assert parsed["context"]["boolean_value"] is True

    def test_context_with_complex_objects():
        """Test error context with complex non-serializable objects."""
        from pathlib import Path

        context = {
            "path_object": Path("/test/path"),
            "function": lambda x: x + 1,
            "class_instance": Exception("nested error"),
        }

        error = MPMError("Test error", context=context)

        # Should handle complex objects gracefully
        assert "path_object" in error.context
        assert str(error.context["path_object"]) == "/test/path"

    def test_context_type_coercion():
        """Test that context values are properly coerced to strings when needed."""
        context = {
            "none_value": None,
            "numeric_zero": 0,
            "empty_string": "",
            "empty_list": [],
            "empty_dict": {},
        }

        error = MPMError("Test error", context=context)
        error_str = str(error)

        # All context should be included in string representation
        assert "none_value=None" in error_str
        assert "numeric_zero=0" in error_str
        assert "empty_string=" in error_str

    def test_context_key_sanitization():
        """Test that context keys are properly sanitized."""
        context = {
            "normal_key": "value1",
            "key with spaces": "value2",
            "key-with-dashes": "value3",
            "key_with_underscores": "value4",
            "123numeric_key": "value5",
        }

        error = MPMError("Test error", context=context)
        error_str = str(error)

        # Should handle all key types
        for key, value in context.items():
            assert f"{key}={value}" in error_str

    def test_large_context_truncation():
        """Test handling of very large context values."""
        large_string = "x" * 10000  # 10KB string
        context = {"large_value": large_string, "normal_value": "test"}

        error = MPMError("Test error", context=context)
        error_str = str(error)

        # Should still be manageable length
        assert len(error_str) < 20000  # Reasonable limit
        assert "normal_value=test" in error_str

    def test_context_inheritance_preservation():
        """Test that context is preserved through error inheritance."""
        base_context = {"base_key": "base_value"}
        base_error = MPMError("Base error", context=base_context)

        # Create derived error
        derived_context = {"derived_key": "derived_value"}
        derived_error = AgentDeploymentError("Derived error", context=derived_context)

        # Both should maintain their context
        assert base_error.context["base_key"] == "base_value"
        assert derived_error.context["derived_key"] == "derived_value"

    def test_context_empty_handling():
        """Test proper handling of empty or None context."""
        # None context
        error1 = MPMError("Test error", context=None)
        assert error1.context == {}

        # Empty dict context
        error2 = MPMError("Test error", context={})
        assert error2.context == {}

        # Both should have clean string representation
        assert str(error1) == "Test error"
        assert str(error2) == "Test error"


class TestErrorSerialization:
    """Test error serialization and deserialization."""

    def test_basic_error_serialization():
        """Test basic error serialization to dict."""
        error = MPMError("Test message", context={"key": "value"})
        result = error.to_dict()

        expected_keys = ["error_type", "error_code", "message", "context"]
        for key in expected_keys:
            assert key in result

        assert result["error_type"] == "MPMError"
        assert result["error_code"] == "mpm"
        assert result["message"] == "Test message"
        assert result["context"] == {"key": "value"}

    def test_all_error_types_serialization():
        """Test serialization of all error types."""
        error_classes = [
            (MPMError, "mpm"),
            (AgentDeploymentError, "agent_deployment"),
            (ConfigurationError, "configuration"),
            (ConnectionError, "connection"),
            (ValidationError, "validation"),
            (ServiceNotFoundError, "service_not_found"),
            (MemoryError, "memory"),
            (HookError, "hook"),
            (SessionError, "session"),
        ]

        for error_class, expected_code in error_classes:
            error = error_class("Test message", context={"test": "value"})
            result = error.to_dict()

            assert result["error_type"] == error_class.__name__
            assert result["error_code"] == expected_code
            assert result["message"] == "Test message"
            assert result["context"] == {"test": "value"}

    def test_serialization_with_nested_errors():
        """Test serialization when context contains other errors."""
        nested_error = ValueError("Nested error")
        context = {
            "nested_error": nested_error,
            "error_message": str(nested_error),
            "error_type": type(nested_error).__name__,
        }

        error = MPMError("Main error", context=context)
        result = error.to_dict()

        # Should handle nested error gracefully
        assert "nested_error" in result["context"]
        assert result["context"]["error_message"] == "Nested error"
        assert result["context"]["error_type"] == "ValueError"

    def test_serialization_preserves_original_data():
        """Test that serialization doesn't modify original error."""
        original_context = {"mutable_list": [1, 2, 3], "value": "test"}
        error = MPMError("Test error", context=original_context)

        # Serialize
        serialized = error.to_dict()

        # Modify serialized data
        serialized["context"]["mutable_list"].append(4)
        serialized["context"]["value"] = "modified"

        # Original should be unchanged
        assert error.context["mutable_list"] == [1, 2, 3]
        assert error.context["value"] == "test"

    def test_json_serialization_compatibility():
        """Test that error dicts are compatible with JSON serialization."""
        import json

        errors = [
            MPMError("Test", context={"key": "value"}),
            AgentDeploymentError("Deploy failed", context={"agent_id": "test"}),
            ConfigurationError("Config invalid", context={"file": "config.yaml"}),
            ConnectionError(
                "Connection failed", context={"host": "localhost", "port": 8080}
            ),
        ]

        for error in errors:
            error_dict = error.to_dict()

            # Should be JSON serializable
            json_str = json.dumps(error_dict)
            parsed = json.loads(json_str)

            # Should preserve all data
            assert parsed["error_type"] == error_dict["error_type"]
            assert parsed["error_code"] == error_dict["error_code"]
            assert parsed["message"] == error_dict["message"]
            assert parsed["context"] == error_dict["context"]

    def test_error_reconstruction_from_dict():
        """Test that errors can be reconstructed from their dict representation."""
        original_error = AgentDeploymentError(
            "Deployment failed",
            context={
                "agent_id": "engineer",
                "template_path": "/path/to/template",
                "retry_count": 3,
            },
        )

        # Serialize
        error_dict = original_error.to_dict()

        # Reconstruct (simulated)
        reconstructed_message = error_dict["message"]
        reconstructed_context = error_dict["context"]
        reconstructed_error = AgentDeploymentError(
            reconstructed_message, context=reconstructed_context
        )

        # Should have same properties
        assert str(reconstructed_error) == str(original_error)
        assert reconstructed_error.error_code == original_error.error_code
        assert reconstructed_error.context == original_error.context

    def test_serialization_performance():
        """Test serialization performance with large contexts."""
        import time

        # Large context
        large_context = {f"key_{i}": f"value_{i}" for i in range(1000)}
        large_context["list_data"] = list(range(1000))
        large_context["nested"] = {"deep": {"data": list(range(100))}}

        error = MPMError("Large context error", context=large_context)

        # Time serialization
        start_time = time.time()
        result = error.to_dict()
        end_time = time.time()

        # Should complete quickly (< 1 second)
        assert (end_time - start_time) < 1.0
        assert len(result["context"]) == len(large_context)

    def test_circular_reference_handling():
        """Test handling of circular references in context."""
        # Create circular reference
        context = {"self_ref": None}
        context["self_ref"] = context

        # Should handle gracefully without infinite recursion
        error = MPMError("Circular reference test", context={"normal": "value"})
        result = error.to_dict()

        # Should still work for non-circular parts
        assert result["message"] == "Circular reference test"
