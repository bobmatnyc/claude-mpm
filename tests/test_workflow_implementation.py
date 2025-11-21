#!/usr/bin/env python3
"""Test script for workflow implementation in ai-trackdown-pytools."""

import sys

sys.path.insert(0, "/Users/masa/Projects/managed/ai-trackdown-pytools/src")

from datetime import datetime, timezone

from ai_trackdown_pytools.core.models import IssueModel, TaskModel
from ai_trackdown_pytools.core.workflow import (
    ResolutionType,
    UnifiedStatus,
    is_terminal_status,
    requires_resolution,
    workflow_state_machine,
)


def test_state_transitions():
    """Test 1: State Transition Validation"""
    print("Test 1: State Transition Validation")
    print("=====================================")

    # Valid transition
    valid, msg = workflow_state_machine.validate_transition(
        UnifiedStatus.OPEN, UnifiedStatus.IN_PROGRESS
    )
    print(f"OPEN -> IN_PROGRESS: {valid} ({'OK' if valid else msg})")

    # Invalid transition
    valid, msg = workflow_state_machine.validate_transition(
        UnifiedStatus.OPEN, UnifiedStatus.MERGED
    )
    print(f"OPEN -> MERGED: {valid} ({msg if msg else 'OK'})")

    # Transition requiring resolution
    valid, msg = workflow_state_machine.validate_transition(
        UnifiedStatus.IN_PROGRESS, UnifiedStatus.RESOLVED
    )
    print(f"IN_PROGRESS -> RESOLVED (no resolution): {valid} ({msg if msg else 'OK'})")

    valid, msg = workflow_state_machine.validate_transition(
        UnifiedStatus.IN_PROGRESS, UnifiedStatus.RESOLVED, ResolutionType.FIXED
    )
    print(
        f"IN_PROGRESS -> RESOLVED (with resolution): {valid} ({'OK' if valid else msg})"
    )


def test_terminal_states():
    """Test 2: Terminal States & Resolution Requirements"""
    print("\nTest 2: Terminal States & Resolution Requirements")
    print("=================================================")

    terminal_states = [
        UnifiedStatus.COMPLETED,
        UnifiedStatus.RESOLVED,
        UnifiedStatus.CLOSED,
        UnifiedStatus.CANCELLED,
        UnifiedStatus.DONE,
    ]

    for state in terminal_states:
        print(
            f"{state.value}: Terminal={is_terminal_status(state)}, "
            f"Requires Resolution={requires_resolution(state)}"
        )


def test_model_integration():
    """Test 3: Model Integration"""
    print("\nTest 3: Model Integration")
    print("=========================")

    try:
        # Create task with string status
        task = TaskModel(
            id="TSK-001",
            title="Test Task",
            status="open",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        print(
            f"Created task with status: {task.status} (type: {type(task.status).__name__})"
        )

        # Try valid transition
        can_transition, error = task.can_transition_to("in_progress")
        print(f"Can transition to in_progress: {can_transition}")

        # Create issue
        issue = IssueModel(
            id="ISS-001",
            title="Test Issue",
            status=UnifiedStatus.IN_PROGRESS,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Try transition to closed without resolution
        can_transition, error = issue.can_transition_to(UnifiedStatus.CLOSED)
        print(
            f"Can transition to closed without resolution: {can_transition} ({error})"
        )

    except Exception as e:
        print(f"Error in model integration: {type(e).__name__}: {e}")


def test_backward_compatibility():
    """Test 4: Backward Compatibility"""
    print("\nTest 4: Backward Compatibility")
    print("==============================")

    try:
        from ai_trackdown_pytools.core.compatibility import (
            convert_to_legacy_status,
            convert_to_unified_status,
            is_compatible_status,
        )
        from ai_trackdown_pytools.core.models import TaskStatus

        # Test conversion from legacy enum
        unified = convert_to_unified_status(TaskStatus.OPEN)
        print(f"TaskStatus.OPEN -> {unified}")

        # Test compatibility check
        is_compat = is_compatible_status(UnifiedStatus.MERGED, "task")
        print(f"MERGED compatible with task: {is_compat}")

        is_compat = is_compatible_status(UnifiedStatus.MERGED, "pr")
        print(f"MERGED compatible with PR: {is_compat}")

        # Test back conversion
        legacy = convert_to_legacy_status(UnifiedStatus.DRAFT, "pr")
        print(f"UnifiedStatus.DRAFT -> {legacy} (type: {type(legacy).__name__})")

    except Exception as e:
        print(f"Error in backward compatibility: {type(e).__name__}: {e}")


def test_resolution_tracking():
    """Test 5: Resolution Tracking"""
    print("\nTest 5: Resolution Tracking")
    print("===========================")

    try:
        # Create bug and resolve it
        from ai_trackdown_pytools.core.models import BugModel

        bug = BugModel(
            id="BUG-001",
            title="Test Bug",
            status=UnifiedStatus.IN_PROGRESS,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Transition to resolved with resolution
        bug.transition_to(
            UnifiedStatus.RESOLVED,
            resolution=ResolutionType.FIXED,
            resolution_comment="Fixed in commit abc123",
            user="developer",
        )

        print(f"Bug status: {bug.status}")
        print(f"Resolution: {bug.resolution}")
        print(f"Resolution comment: {bug.resolution_comment}")
        print(f"Resolved by: {bug.resolved_by}")
        print(f"Resolved at: {bug.resolved_at}")

    except Exception as e:
        print(f"Error in resolution tracking: {type(e).__name__}: {e}")


def main():
    """Run all tests."""
    print("Testing STATUS and RESOLUTION Implementation")
    print("==========================================\n")

    test_state_transitions()
    test_terminal_states()
    test_model_integration()
    test_backward_compatibility()
    test_resolution_tracking()

    print("\nAll tests completed!")


if __name__ == "__main__":
    main()
