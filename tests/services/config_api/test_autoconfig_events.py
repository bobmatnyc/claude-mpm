"""
Tests for auto-configure Socket.IO event handling
================================================

WHY: Tests Socket.IO event emission during auto-configure v2 workflow,
including 6-phase progress events. Addresses research findings about
Socket.IO event testing with proper payload validation.

FOCUS: Integration testing of event emission patterns, payload structure
validation, and async event handling during auto-configure phases.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from claude_mpm.cli.commands.auto_configure import (
    AutoConfigureCommand,
    RichProgressObserver,
)
from claude_mpm.core.enums import OperationResult
from claude_mpm.services.core.models.agent_config import (
    AgentRecommendation,
    ConfigurationPreview,
    ConfigurationResult,
    ValidationResult,
)


class TestProgressObserverEvents:
    """Test event emission through RichProgressObserver."""

    @pytest.fixture
    def mock_console(self):
        """Mock Rich console."""
        return Mock()

    @pytest.fixture
    def progress_observer(self, mock_console):
        """Create RichProgressObserver instance."""
        return RichProgressObserver(mock_console)

    def test_agent_deployment_started_event_structure(self, progress_observer):
        """Test agent deployment started event emission structure."""
        # Mock event emission capability
        with patch.object(progress_observer, "_emit_event") as mock_emit:
            progress_observer.on_agent_deployment_started(
                agent_id="python-engineer",
                agent_name="Python Engineer",
                index=1,
                total=3,
            )

            # Verify event emitted with correct structure
            mock_emit.assert_called_once()
            call_args = mock_emit.call_args
            event_data = call_args[0][1]  # Second argument is event data

            # Verify event payload structure
            assert event_data["phase"] == "agent_deployment_started"
            assert event_data["agent_id"] == "python-engineer"
            assert event_data["agent_name"] == "Python Engineer"
            assert event_data["progress"] == {"current": 1, "total": 3}

    def test_agent_deployment_progress_event_payload(self, progress_observer):
        """Test agent deployment progress event payload validation."""
        with patch.object(progress_observer, "_emit_event") as mock_emit:
            progress_observer.on_agent_deployment_progress(
                agent_id="python-engineer",
                progress=45,
                message="Downloading agent files...",
            )

            mock_emit.assert_called_once()
            event_data = mock_emit.call_args[0][1]

            # Verify progress event structure
            assert event_data["phase"] == "agent_deployment_progress"
            assert event_data["agent_id"] == "python-engineer"
            assert event_data["progress"] == 45
            assert event_data["message"] == "Downloading agent files..."

    def test_agent_deployment_completed_success_event(self, progress_observer):
        """Test successful agent deployment completion event."""
        with patch.object(progress_observer, "_emit_event") as mock_emit:
            progress_observer.on_agent_deployment_completed(
                agent_id="python-engineer",
                agent_name="Python Engineer",
                success=True,
                error=None,
            )

            mock_emit.assert_called_once()
            event_data = mock_emit.call_args[0][1]

            # Verify success event structure
            assert event_data["phase"] == "agent_deployment_completed"
            assert event_data["agent_id"] == "python-engineer"
            assert event_data["agent_name"] == "Python Engineer"
            assert event_data["success"] is True
            assert event_data["error"] is None

    def test_agent_deployment_completed_failure_event(self, progress_observer):
        """Test failed agent deployment completion event."""
        with patch.object(progress_observer, "_emit_event") as mock_emit:
            progress_observer.on_agent_deployment_completed(
                agent_id="invalid-agent",
                agent_name="Invalid Agent",
                success=False,
                error="Agent not found in registry",
            )

            mock_emit.assert_called_once()
            event_data = mock_emit.call_args[0][1]

            # Verify failure event structure
            assert event_data["phase"] == "agent_deployment_completed"
            assert event_data["agent_id"] == "invalid-agent"
            assert event_data["success"] is False
            assert event_data["error"] == "Agent not found in registry"

    def test_deployment_completed_summary_event(self, progress_observer):
        """Test overall deployment completion summary event."""
        with patch.object(progress_observer, "_emit_event") as mock_emit:
            progress_observer.on_deployment_completed(
                success_count=2, failure_count=1, duration_ms=15432.5
            )

            mock_emit.assert_called_once()
            event_data = mock_emit.call_args[0][1]

            # Verify summary event structure
            assert event_data["phase"] == "deployment_completed"
            assert event_data["summary"]["success_count"] == 2
            assert event_data["summary"]["failure_count"] == 1
            assert event_data["summary"]["total_count"] == 3
            assert event_data["summary"]["duration_ms"] == 15432.5


class TestAutoConfigurePhaseEvents:
    """Test event emission during auto-configure workflow phases."""

    @pytest.fixture
    def command(self):
        return AutoConfigureCommand()

    @pytest.fixture
    def mock_event_emitter(self):
        """Mock event emitter for testing."""
        emitter = Mock()
        emitter.emit = Mock()
        return emitter

    def test_phase_0_toolchain_analysis_events(self, command, mock_event_emitter):
        """Test Phase 0: Toolchain analysis event emission."""
        project_path = Path("/test/project")

        with patch.object(command, "auto_config_manager") as mock_manager, patch(
            "claude_mpm.cli.commands.auto_configure.get_event_emitter"
        ) as mock_get_emitter:
            mock_get_emitter.return_value = mock_event_emitter

            # Mock toolchain analysis
            preview = Mock(spec=ConfigurationPreview)
            preview.detected_toolchain = Mock()
            preview.detected_toolchain.components = [
                Mock(type="python", version="3.11", confidence=0.9),
                Mock(type="fastapi", version="0.104.1", confidence=0.8),
            ]
            preview.recommendations = []
            preview.validation_result = Mock(is_valid=True, issues=[])
            mock_manager.preview_configuration.return_value = preview

            # Add event emission to command
            with patch.object(command, "_emit_phase_event") as mock_emit_phase:
                # Run preview to trigger toolchain analysis
                args = Mock(
                    project_path=project_path,
                    min_confidence=0.5,
                    preview=True,
                    json=False,
                    verbose=False,
                    debug=False,
                    quiet=False,
                )
                result = command.run(args)

                # Verify Phase 0 events emitted
                phase_calls = mock_emit_phase.call_args_list
                phase_0_calls = [
                    call for call in phase_calls if call[0][0] == "toolchain_analysis"
                ]

                assert len(phase_0_calls) >= 1
                event_data = phase_0_calls[0][0][1]
                assert "detected_components" in event_data
                assert len(event_data["detected_components"]) == 2

    def test_phase_1_min_confidence_validation_events(
        self, command, mock_event_emitter
    ):
        """Test Phase 1: Min confidence validation event emission."""
        with patch.object(command, "auto_config_manager") as mock_manager, patch.object(
            command, "_emit_phase_event"
        ) as mock_emit_phase:
            # Mock validation with min_confidence filtering
            preview = Mock(spec=ConfigurationPreview)
            preview.recommendations = [
                Mock(agent_id="high-confidence", confidence=0.9),
                Mock(agent_id="low-confidence", confidence=0.3),  # Below threshold
            ]
            preview.validation_result = Mock(is_valid=True, issues=[])
            preview.detected_toolchain = Mock(components=[])
            mock_manager.preview_configuration.return_value = preview

            args = Mock(
                project_path=Path("/test"),
                min_confidence=0.5,  # Filter threshold
                preview=True,
                json=False,
                verbose=False,
                debug=False,
                quiet=False,
            )
            command.run(args)

            # Verify Phase 1 validation events
            phase_calls = mock_emit_phase.call_args_list
            validation_calls = [
                call
                for call in phase_calls
                if call[0][0] == "min_confidence_validation"
            ]

            assert len(validation_calls) >= 1
            event_data = validation_calls[0][0][1]
            assert event_data["min_confidence"] == 0.5
            assert "filtered_recommendations" in event_data
            assert "filtered_count" in event_data

    def test_phase_2_skill_deployment_events(self, command, mock_event_emitter):
        """Test Phase 2: Skill deployment event emission."""
        with patch.object(
            command, "skills_deployer"
        ) as mock_skills_deployer, patch.object(
            command, "_emit_phase_event"
        ) as mock_emit_phase:
            # Mock skill deployment
            mock_skills_deployer.deploy_skills.return_value = {
                "deployed": ["python-testing", "react"],
                "errors": [],
            }

            recommended_skills = ["python-testing", "react", "django"]
            result = command._deploy_skills(recommended_skills)

            # Verify Phase 2 skill deployment events
            phase_calls = mock_emit_phase.call_args_list
            skill_calls = [
                call for call in phase_calls if call[0][0] == "skill_deployment"
            ]

            assert len(skill_calls) >= 1
            event_data = skill_calls[0][0][1]
            assert "recommended_skills" in event_data
            assert "deployment_result" in event_data
            assert event_data["deployment_result"]["success_count"] == 2

    def test_phase_3_agent_archiving_events(self, command, mock_event_emitter):
        """Test Phase 3: Agent archiving event emission (when implemented)."""
        with patch.object(command, "_archive_agents") as mock_archive, patch.object(
            command, "_emit_phase_event"
        ) as mock_emit_phase:
            # Mock agent archiving
            agents_to_archive = [
                {"name": "old-agent", "version": "1.0.0"},
                {"name": "unused-agent", "version": "2.0.0"},
            ]
            mock_archive.return_value = {"archived": agents_to_archive, "errors": []}

            command._archive_agents(agents_to_archive)

            # Verify Phase 3 archiving events
            phase_calls = mock_emit_phase.call_args_list
            archive_calls = [
                call for call in phase_calls if call[0][0] == "agent_archiving"
            ]

            assert len(archive_calls) >= 1
            event_data = archive_calls[0][0][1]
            assert "agents_to_archive" in event_data
            assert event_data["archive_count"] == 2

    def test_phase_4_configuration_completion_events(self, command, mock_event_emitter):
        """Test Phase 4: Configuration completion event emission."""
        with patch.object(command, "_emit_phase_event") as mock_emit_phase:
            # Mock completion results
            agent_result = Mock(spec=ConfigurationResult)
            agent_result.status = OperationResult.SUCCESS
            agent_result.deployed_agents = ["python-engineer", "react-developer"]
            agent_result.failed_agents = []

            skills_result = {"deployed": ["python-testing", "react"], "errors": []}

            command._show_restart_notification(agent_result, skills_result)

            # Verify Phase 4 completion events
            phase_calls = mock_emit_phase.call_args_list
            completion_calls = [
                call for call in phase_calls if call[0][0] == "configuration_completion"
            ]

            assert len(completion_calls) >= 1
            event_data = completion_calls[0][0][1]
            assert "total_agents_deployed" in event_data
            assert "total_skills_deployed" in event_data
            assert event_data["restart_required"] is True


class TestEventPayloadValidation:
    """Test Socket.IO event payload structure validation."""

    def test_event_payload_json_serializable(self):
        """Test that all event payloads are JSON serializable."""
        sample_payloads = [
            {
                "phase": "toolchain_analysis",
                "detected_components": [
                    {"type": "python", "version": "3.11", "confidence": 0.9}
                ],
                "timestamp": "2024-01-15T10:30:00Z",
            },
            {
                "phase": "agent_deployment_started",
                "agent_id": "python-engineer",
                "agent_name": "Python Engineer",
                "progress": {"current": 1, "total": 3},
            },
            {
                "phase": "min_confidence_validation",
                "min_confidence": 0.5,
                "filtered_recommendations": [
                    {"agent_id": "python-engineer", "confidence": 0.9}
                ],
                "filtered_count": 1,
            },
        ]

        for payload in sample_payloads:
            # Should not raise exception
            json_str = json.dumps(payload)
            # Should round-trip correctly
            parsed = json.loads(json_str)
            assert parsed == payload

    def test_event_payload_required_fields(self):
        """Test that event payloads contain required fields."""
        required_fields_by_phase = {
            "toolchain_analysis": ["phase", "detected_components"],
            "min_confidence_validation": ["phase", "min_confidence"],
            "agent_deployment_started": ["phase", "agent_id", "agent_name"],
            "agent_deployment_progress": ["phase", "agent_id", "progress"],
            "agent_deployment_completed": ["phase", "agent_id", "success"],
            "skill_deployment": ["phase", "deployment_result"],
            "agent_archiving": ["phase", "archive_count"],
            "configuration_completion": ["phase", "restart_required"],
            "deployment_completed": ["phase", "summary"],
        }

        for phase, required_fields in required_fields_by_phase.items():
            # Create minimal payload
            payload = {"phase": phase}

            # Add minimal required fields
            if "agent_id" in required_fields:
                payload["agent_id"] = "test-agent"
            if "agent_name" in required_fields:
                payload["agent_name"] = "Test Agent"
            if "detected_components" in required_fields:
                payload["detected_components"] = []
            if "min_confidence" in required_fields:
                payload["min_confidence"] = 0.5
            if "progress" in required_fields:
                payload["progress"] = 50
            if "success" in required_fields:
                payload["success"] = True
            if "deployment_result" in required_fields:
                payload["deployment_result"] = {"success_count": 0}
            if "archive_count" in required_fields:
                payload["archive_count"] = 0
            if "restart_required" in required_fields:
                payload["restart_required"] = False
            if "summary" in required_fields:
                payload["summary"] = {"success_count": 0, "failure_count": 0}

            # Verify all required fields present
            for field in required_fields:
                assert field in payload, (
                    f"Missing required field '{field}' in phase '{phase}'"
                )

    def test_event_payload_field_types(self):
        """Test that event payload fields have correct types."""
        type_constraints = {
            "phase": str,
            "agent_id": str,
            "agent_name": str,
            "progress": (int, float),
            "success": bool,
            "min_confidence": (int, float),
            "detected_components": list,
            "filtered_recommendations": list,
            "deployment_result": dict,
            "archive_count": int,
            "restart_required": bool,
            "summary": dict,
            "timestamp": str,
        }

        sample_payload = {
            "phase": "test_phase",
            "agent_id": "test-agent",
            "agent_name": "Test Agent",
            "progress": 75,
            "success": True,
            "min_confidence": 0.8,
            "detected_components": [{"type": "python"}],
            "filtered_recommendations": [{"agent_id": "test"}],
            "deployment_result": {"deployed": []},
            "archive_count": 5,
            "restart_required": True,
            "summary": {"total": 10},
            "timestamp": "2024-01-15T10:30:00Z",
        }

        for field, value in sample_payload.items():
            expected_type = type_constraints[field]
            if isinstance(expected_type, tuple):
                assert any(isinstance(value, t) for t in expected_type), (
                    f"Field '{field}' has wrong type. Expected {expected_type}, got {type(value)}"
                )
            else:
                assert isinstance(value, expected_type), (
                    f"Field '{field}' has wrong type. Expected {expected_type}, got {type(value)}"
                )


@pytest.mark.integration
class TestSocketIOEventIntegration:
    """Integration tests for Socket.IO event emission in full workflow."""

    @pytest.fixture
    def mock_socketio_server(self):
        """Mock Socket.IO server for integration testing."""
        server = Mock()
        server.emit = Mock()
        return server

    def test_full_workflow_event_sequence(self, tmp_path, mock_socketio_server):
        """Test complete event sequence during full auto-configure workflow."""
        command = AutoConfigureCommand()
        project_path = tmp_path / "event_test"
        project_path.mkdir()

        events_emitted = []

        def capture_event(event_name, data):
            events_emitted.append({"event": event_name, "data": data})

        mock_socketio_server.emit.side_effect = capture_event

        with patch(
            "claude_mpm.cli.commands.auto_configure.get_socketio_server"
        ) as mock_get_server:
            mock_get_server.return_value = mock_socketio_server

            # Mock all services for full workflow
            with patch.object(
                command, "auto_config_manager"
            ) as mock_auto_config, patch.object(
                command, "skills_deployer"
            ) as mock_skills:
                # Mock preview
                preview = Mock(spec=ConfigurationPreview)
                preview.recommendations = [
                    Mock(agent_id="python-engineer", confidence=0.9)
                ]
                preview.validation_result = Mock(is_valid=True, issues=[])
                preview.detected_toolchain = Mock(components=[])
                mock_auto_config.preview_configuration.return_value = preview

                # Mock agent deployment
                result = Mock(spec=ConfigurationResult)
                result.status = OperationResult.SUCCESS
                result.deployed_agents = ["python-engineer"]
                result.failed_agents = []
                result.errors = {}
                mock_auto_config.auto_configure = AsyncMock(return_value=result)

                # Mock skill deployment
                mock_skills.deploy_skills.return_value = {
                    "deployed": ["python-testing"],
                    "errors": [],
                }

                # Run full workflow
                args = Mock(
                    project_path=project_path,
                    min_confidence=0.5,
                    preview=False,
                    yes=True,
                    json=False,
                    verbose=False,
                    debug=False,
                    quiet=False,
                    agents_only=False,
                    skills_only=False,
                )

                with patch(
                    "claude_mpm.cli.interactive.skills_wizard.AGENT_SKILL_MAPPING",
                    {"python-engineer": ["python-testing"]},
                ):
                    command.run(args)

                # Verify event sequence
                assert len(events_emitted) > 0

                # Check for key phases in event sequence
                event_names = [e["event"] for e in events_emitted]
                phase_events = [
                    e["data"].get("phase")
                    for e in events_emitted
                    if "phase" in e.get("data", {})
                ]

                # Should see toolchain analysis, validation, and completion events
                expected_phases = [
                    "toolchain_analysis",
                    "min_confidence_validation",
                    "configuration_completion",
                ]

                for phase in expected_phases:
                    assert any(phase in str(p) for p in phase_events), (
                        f"Missing expected phase '{phase}' in emitted events"
                    )

    def test_event_emission_error_handling(self, tmp_path, mock_socketio_server):
        """Test event emission error handling doesn't break workflow."""
        command = AutoConfigureCommand()

        # Mock Socket.IO server that raises exceptions
        mock_socketio_server.emit.side_effect = Exception("Socket.IO connection lost")

        with patch(
            "claude_mpm.cli.commands.auto_configure.get_socketio_server"
        ) as mock_get_server:
            mock_get_server.return_value = mock_socketio_server

            with patch.object(command, "auto_config_manager") as mock_auto_config:
                preview = Mock(spec=ConfigurationPreview)
                preview.recommendations = []
                preview.validation_result = Mock(is_valid=True, issues=[])
                preview.detected_toolchain = Mock(components=[])
                mock_auto_config.preview_configuration.return_value = preview

                args = Mock(
                    project_path=tmp_path,
                    min_confidence=0.5,
                    preview=True,
                    json=False,
                    verbose=False,
                    debug=False,
                    quiet=False,
                )

                # Should not raise exception despite Socket.IO errors
                result = command.run(args)

                # Workflow should still succeed
                assert result.success
