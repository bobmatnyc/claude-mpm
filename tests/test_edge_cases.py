#!/usr/bin/env python3
"""Test edge cases and error handling for workflow implementation."""

import sys
sys.path.insert(0, '/Users/masa/Projects/managed/ai-trackdown-pytools/src')

from ai_trackdown_pytools.core.workflow import (
    UnifiedStatus, ResolutionType, workflow_state_machine,
    resolution_requires_comment
)
from ai_trackdown_pytools.core.models import IssueModel, BugModel
from datetime import datetime

def test_resolution_comment_requirements():
    """Test resolution types that require comments."""
    print('Test 1: Resolution Comment Requirements')
    print('=======================================')
    
    resolutions_requiring_comments = [
        ResolutionType.WORKAROUND,
        ResolutionType.WONT_FIX,
        ResolutionType.INCOMPLETE,
        ResolutionType.DUPLICATE,
    ]
    
    for resolution in resolutions_requiring_comments:
        requires_comment = resolution_requires_comment(resolution)
        print(f'{resolution.value}: Requires comment = {requires_comment}')
    
    # Test creating issue with resolution requiring comment
    try:
        issue = IssueModel(
            id='ISS-001',
            title='Test Issue',
            status=UnifiedStatus.CLOSED,
            resolution=ResolutionType.WONT_FIX,
            # Missing resolution_comment
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        print('ERROR: Created issue without required comment!')
    except ValueError as e:
        print(f'✓ Correctly blocked: {e}')


def test_invalid_state_transitions():
    """Test invalid state transitions are blocked."""
    print('\nTest 2: Invalid State Transitions')
    print('=================================')
    
    invalid_transitions = [
        (UnifiedStatus.OPEN, UnifiedStatus.MERGED),
        (UnifiedStatus.COMPLETED, UnifiedStatus.IN_PROGRESS),
        (UnifiedStatus.CANCELLED, UnifiedStatus.OPEN),
        (UnifiedStatus.MERGED, UnifiedStatus.DRAFT),
    ]
    
    for from_status, to_status in invalid_transitions:
        valid, error = workflow_state_machine.validate_transition(from_status, to_status)
        print(f'{from_status.value} -> {to_status.value}: {valid} ({error})')


def test_resolution_validation():
    """Test resolution validation for different states."""
    print('\nTest 3: Resolution Validation')
    print('=============================')
    
    # Test allowed resolutions for different transitions
    transition = workflow_state_machine.get_transition(
        UnifiedStatus.OPEN, UnifiedStatus.CANCELLED
    )
    if transition:
        print(f'OPEN -> CANCELLED allowed resolutions: {[r.value for r in transition.allowed_resolutions]}')
    
    # Test invalid resolution type
    valid, error = workflow_state_machine.validate_transition(
        UnifiedStatus.IN_PROGRESS,
        UnifiedStatus.RESOLVED,
        ResolutionType.DUPLICATE  # Not allowed for IN_PROGRESS -> RESOLVED
    )
    print(f'IN_PROGRESS -> RESOLVED with DUPLICATE: {valid} ({error})')


def test_reopen_functionality():
    """Test reopening tickets."""
    print('\nTest 4: Reopen Functionality')
    print('============================')
    
    try:
        bug = BugModel(
            id='BUG-001',
            title='Test Bug',
            status=UnifiedStatus.RESOLVED,
            resolution=ResolutionType.FIXED,
            resolution_comment='Fixed',
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Check if can reopen
        can_reopen, error = bug.can_transition_to(UnifiedStatus.REOPENED)
        print(f'Can reopen resolved bug: {can_reopen}')
        
        # Actually reopen
        if can_reopen:
            original_resolution = bug.resolution
            bug.status = UnifiedStatus.REOPENED
            bug.reopen_count += 1
            print(f'Bug reopened. Reopen count: {bug.reopen_count}')
            print(f'Resolution still present: {bug.resolution is not None}')
            
    except Exception as e:
        print(f'Error testing reopen: {type(e).__name__}: {e}')


def test_terminal_state_enforcement():
    """Test that terminal states cannot transition further (except reopen)."""
    print('\nTest 5: Terminal State Enforcement')
    print('==================================')
    
    terminal_states = [
        UnifiedStatus.COMPLETED,
        UnifiedStatus.CANCELLED,
        UnifiedStatus.MERGED,
        UnifiedStatus.ARCHIVED,
    ]
    
    for terminal in terminal_states:
        transitions = workflow_state_machine.get_valid_transitions(terminal)
        valid_to = [t.to_status.value for t in transitions]
        print(f'{terminal.value} can transition to: {valid_to}')


def test_schema_alignment():
    """Test alignment with ai-trackdown schema."""
    print('\nTest 6: Schema Alignment Check')
    print('==============================')
    
    # States from ai-trackdown schema
    ai_trackdown_states = [
        "open", "new", "in_progress", "assigned", "pending", "waiting",
        "resolved", "closed", "reopened", "on_hold", "escalated", "canceled",
        "blocked", "ready_for_engineering", "ready_for_qa", "ready_for_deployment",
        "ready_for_review", "in_review", "review_approved", "planning",
        "done", "won't_do", "duplicate", "obsolete"
    ]
    
    # Check which states are supported
    supported = 0
    unsupported = []
    
    for state in ai_trackdown_states:
        try:
            unified = UnifiedStatus(state)
            supported += 1
        except ValueError:
            unsupported.append(state)
    
    print(f'Supported states: {supported}/{len(ai_trackdown_states)}')
    if unsupported:
        print(f'Unsupported states: {unsupported}')
    
    # Check resolution types from schema
    ai_trackdown_resolutions = [
        "fixed", "resolved", "won't_fix", "duplicate", "cannot_reproduce",
        "works_as_designed", "incomplete", "user_error", "configuration",
        "workaround", "documentation", "invalid", "by_design",
        "external_dependency", "out_of_scope"
    ]
    
    supported_res = 0
    unsupported_res = []
    
    for res in ai_trackdown_resolutions:
        try:
            resolution = ResolutionType(res)
            supported_res += 1
        except ValueError:
            unsupported_res.append(res)
    
    print(f'\nSupported resolutions: {supported_res}/{len(ai_trackdown_resolutions)}')
    if unsupported_res:
        print(f'Unsupported resolutions: {unsupported_res}')


def main():
    """Run all edge case tests."""
    print('Testing Edge Cases and Error Handling')
    print('====================================\n')
    
    test_resolution_comment_requirements()
    test_invalid_state_transitions()
    test_resolution_validation()
    test_reopen_functionality()
    test_terminal_state_enforcement()
    test_schema_alignment()
    
    print('\nEdge case testing completed!')


if __name__ == '__main__':
    main()