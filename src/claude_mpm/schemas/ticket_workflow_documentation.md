# Ticket Workflow Schema Documentation

## Overview

The Ticket Workflow Schema provides a comprehensive framework for defining and managing ticket workflows in the Claude MPM system. This schema clearly separates the concepts of **Status** (workflow position) and **Resolution** (outcome reasoning), allowing for flexible and powerful ticket management configurations.

## Core Concepts

### Status vs Resolution

The schema enforces a clear separation between two fundamental concepts:

1. **Status**: Tracks the current position of a ticket in the workflow lifecycle
   - Examples: Open, In Progress, Pending, Resolved, Closed
   - Represents WHERE the ticket is in the process
   - Controls workflow transitions and available actions

2. **Resolution**: Tracks the outcome reasoning when a ticket reaches a terminal state
   - Examples: Fixed, Won't Fix, Duplicate, Cannot Reproduce
   - Represents WHY the ticket was closed or resolved
   - Provides context for reporting and metrics

### Valid Combinations

Different status-resolution combinations are valid and meaningful:
- **Status: Closed, Resolution: Fixed** - Successfully completed work
- **Status: Closed, Resolution: Won't Fix** - Deliberate decision not to address
- **Status: Resolved, Resolution: Workaround** - Problem addressed with alternative solution
- **Status: Canceled, Resolution: Duplicate** - Canceled because it duplicates another ticket

## Schema Structure

### 1. Workflow Identification

```json
{
  "schema_version": "1.0.0",
  "workflow_id": "standard_workflow",
  "workflow_version": "1.0.0",
  "metadata": {
    "name": "Standard Support Workflow",
    "description": "Default workflow for support tickets",
    "workflow_type": "support"
  }
}
```

### 2. Status States Definition

Status states are categorized into four types:

- **initial**: Starting states for new tickets (e.g., Open/New)
- **active**: States where work is being performed (e.g., In Progress, Escalated)
- **waiting**: States where external input is needed (e.g., Pending, On Hold)
- **terminal**: End states (e.g., Resolved, Closed, Canceled)

Example status definition:

```json
{
  "status_states": {
    "states": [
      {
        "id": "open",
        "name": "Open",
        "description": "Ticket has been created but not yet assigned",
        "category": "initial",
        "is_default": true,
        "color": "#4CAF50",
        "icon": "circle-o"
      },
      {
        "id": "in_progress",
        "name": "In Progress",
        "description": "Ticket is actively being worked on",
        "category": "active",
        "color": "#2196F3",
        "icon": "spinner"
      }
    ]
  }
}
```

### 3. Resolution Types Definition

Resolution types are categorized by outcome:

- **successful**: Positive outcomes (Fixed, Configuration, Workaround)
- **unsuccessful**: Negative outcomes (Won't Fix, Incomplete)
- **invalid**: Not actual issues (Duplicate, User Error, Works as Designed)
- **deferred**: Postponed for later (Future Release, Backlog)

Example resolution definition:

```json
{
  "resolution_types": {
    "types": [
      {
        "id": "fixed",
        "name": "Fixed",
        "description": "Issue was successfully fixed",
        "category": "successful",
        "requires_comment": false,
        "color": "#4CAF50",
        "icon": "check-circle"
      },
      {
        "id": "wont_fix",
        "name": "Won't Fix",
        "description": "Decision made not to address the issue",
        "category": "unsuccessful",
        "requires_comment": true,
        "color": "#F44336",
        "icon": "times-circle"
      }
    ]
  }
}
```

### 4. State Transitions

Transitions define the valid paths through the workflow:

```json
{
  "transitions": {
    "rules": [
      {
        "from_status": "open",
        "to_status": "in_progress",
        "name": "Start Work",
        "description": "Begin working on the ticket",
        "required_fields": ["assignee"],
        "auto_assign": true
      },
      {
        "from_status": "in_progress",
        "to_status": "resolved",
        "name": "Resolve",
        "description": "Mark work as complete",
        "required_fields": ["resolution"],
        "permissions": ["resolve_ticket"]
      }
    ]
  }
}
```

### 5. Status-Resolution Mapping

This critical section defines which resolutions are valid for each status:

```json
{
  "status_resolution_mapping": {
    "mappings": [
      {
        "status_id": "resolved",
        "allowed_resolutions": ["fixed", "workaround", "configuration", "documentation"],
        "requires_resolution": true,
        "default_resolution": "fixed"
      },
      {
        "status_id": "closed",
        "allowed_resolutions": ["*"],  // All resolutions allowed
        "requires_resolution": true
      },
      {
        "status_id": "canceled",
        "allowed_resolutions": ["duplicate", "wont_fix", "incomplete", "user_error"],
        "requires_resolution": true,
        "default_resolution": "wont_fix"
      }
    ]
  }
}
```

## Implementation Examples

### Example 1: Standard Support Workflow

```json
{
  "workflow_id": "support_workflow",
  "status_states": {
    "states": [
      {"id": "new", "name": "New", "category": "initial"},
      {"id": "assigned", "name": "Assigned", "category": "active"},
      {"id": "in_progress", "name": "In Progress", "category": "active"},
      {"id": "waiting_customer", "name": "Waiting on Customer", "category": "waiting"},
      {"id": "resolved", "name": "Resolved", "category": "terminal"},
      {"id": "closed", "name": "Closed", "category": "terminal"}
    ]
  },
  "transitions": {
    "rules": [
      {"from_status": "new", "to_status": "assigned", "name": "Assign"},
      {"from_status": "assigned", "to_status": "in_progress", "name": "Start"},
      {"from_status": "in_progress", "to_status": "waiting_customer", "name": "Request Info"},
      {"from_status": "waiting_customer", "to_status": "in_progress", "name": "Customer Responded"},
      {"from_status": "in_progress", "to_status": "resolved", "name": "Resolve"},
      {"from_status": "resolved", "to_status": "closed", "name": "Close"}
    ]
  }
}
```

### Example 2: Bug Tracking Workflow

```json
{
  "workflow_id": "bug_tracking_workflow",
  "status_states": {
    "states": [
      {"id": "reported", "name": "Reported", "category": "initial"},
      {"id": "triaged", "name": "Triaged", "category": "active"},
      {"id": "in_development", "name": "In Development", "category": "active"},
      {"id": "in_review", "name": "In Review", "category": "active"},
      {"id": "testing", "name": "Testing", "category": "active"},
      {"id": "verified", "name": "Verified", "category": "terminal"},
      {"id": "closed", "name": "Closed", "category": "terminal"}
    ]
  },
  "resolution_types": {
    "types": [
      {"id": "fixed", "name": "Fixed", "category": "successful"},
      {"id": "cannot_reproduce", "name": "Cannot Reproduce", "category": "invalid"},
      {"id": "duplicate", "name": "Duplicate", "category": "invalid"},
      {"id": "by_design", "name": "By Design", "category": "invalid"},
      {"id": "wont_fix", "name": "Won't Fix", "category": "unsuccessful"}
    ]
  }
}
```

## Business Rules

### Auto-Close Rules

Automatically close resolved tickets after a specified period:

```json
{
  "business_rules": {
    "auto_close": {
      "enabled": true,
      "days_after_resolved": 7,
      "excluded_resolutions": ["wont_fix", "workaround"]
    }
  }
}
```

### Reopen Rules

Control when and how tickets can be reopened:

```json
{
  "business_rules": {
    "reopen_rules": {
      "allow_reopen": true,
      "from_statuses": ["resolved", "closed"],
      "max_reopen_count": 3,
      "reopen_window_days": 30
    }
  }
}
```

### Escalation Rules

Automatically escalate tickets based on conditions:

```json
{
  "business_rules": {
    "escalation_rules": [
      {
        "name": "High Priority SLA",
        "condition": {
          "status": "open",
          "hours_in_status": 4,
          "priority": "high"
        },
        "action": {
          "change_status": "escalated",
          "change_priority": "critical",
          "notify": ["manager", "on_call"]
        }
      }
    ]
  }
}
```

## UI Configuration

### Quick Transitions

Define buttons for common actions:

```json
{
  "ui_configuration": {
    "quick_transitions": [
      {
        "from_status": "open",
        "to_status": "in_progress",
        "button_label": "Start Work",
        "button_style": "primary"
      },
      {
        "from_status": "in_progress",
        "to_status": "resolved",
        "button_label": "Resolve",
        "button_style": "success"
      }
    ]
  }
}
```

## Metrics Configuration

### Cycle Time Tracking

Define which statuses mark the start and end of cycle time:

```json
{
  "metrics": {
    "cycle_time_statuses": {
      "start": ["in_progress", "assigned"],
      "end": ["resolved", "closed", "canceled"]
    }
  }
}
```

### Resolution Metrics

Track success rates by resolution type:

```json
{
  "metrics": {
    "resolution_metrics": [
      {
        "name": "Success Rate",
        "resolution_ids": ["fixed", "configuration", "workaround"],
        "metric_type": "success_rate"
      },
      {
        "name": "Defect Rate",
        "resolution_ids": ["fixed"],
        "metric_type": "defect_rate"
      }
    ]
  }
}
```

## Integration with Claude MPM

### Using with TicketingService

The workflow schema integrates with the existing `TicketingService`:

```python
from claude_mpm.services.ticketing_service import TicketingService
from claude_mpm.schemas import load_workflow_schema

# Load workflow
workflow = load_workflow_schema('standard_workflow')

# Create ticket with workflow
ticketing = TicketingService.get_instance()
ticket = ticketing.create_ticket(
    title="Issue with login",
    description="User cannot log in",
    status=workflow.default_status,
    workflow_id=workflow.workflow_id
)

# Transition ticket
ticketing.transition_ticket(
    ticket_id=ticket.id,
    to_status="in_progress",
    assignee="engineer@example.com"
)

# Resolve with appropriate resolution
ticketing.update_ticket(
    ticket_id=ticket.id,
    status="resolved",
    resolution="fixed",
    resolution_comment="Fixed authentication bug"
)
```

### Validation

The schema provides comprehensive validation:

```python
from claude_mpm.schemas import validate_workflow

# Validate workflow definition
errors = validate_workflow(workflow_config)
if errors:
    print(f"Workflow validation failed: {errors}")
```

### Migration from Existing Systems

For systems that conflate status and resolution:

```python
# Map conflated values to separate status/resolution
MIGRATION_MAP = {
    "fixed": {"status": "closed", "resolution": "fixed"},
    "wontfix": {"status": "closed", "resolution": "wont_fix"},
    "duplicate": {"status": "closed", "resolution": "duplicate"},
    "invalid": {"status": "closed", "resolution": "cannot_reproduce"},
    "worksforme": {"status": "closed", "resolution": "cannot_reproduce"}
}

def migrate_ticket(old_status):
    """Migrate from conflated status to separate status/resolution."""
    if old_status in MIGRATION_MAP:
        return MIGRATION_MAP[old_status]
    else:
        return {"status": old_status, "resolution": None}
```

## Best Practices

### 1. Status Design

- Keep status count manageable (5-10 statuses)
- Use clear, action-oriented names
- Ensure each status has a clear purpose
- Avoid overlapping or ambiguous statuses

### 2. Resolution Design

- Cover all possible outcomes
- Use descriptive names that explain the outcome
- Require comments for negative resolutions
- Group resolutions by category for reporting

### 3. Transition Design

- Keep transitions simple and logical
- Avoid creating too many paths
- Use required fields to ensure data quality
- Consider permissions for sensitive transitions

### 4. Business Rules

- Start simple and add complexity as needed
- Test escalation rules thoroughly
- Monitor auto-close behavior
- Document all custom rules

### 5. Metrics

- Define clear success criteria
- Track both status duration and resolution types
- Use metrics to identify workflow bottlenecks
- Regular review and optimization

## Conclusion

The Ticket Workflow Schema provides a flexible and powerful framework for managing ticket lifecycles in Claude MPM. By clearly separating Status (workflow position) and Resolution (outcome reasoning), it enables sophisticated workflow management while maintaining clarity and simplicity.

The schema's extensibility through business rules, UI configuration, and metrics ensures it can adapt to various use cases while maintaining consistency and predictability in ticket handling.