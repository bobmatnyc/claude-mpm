#!/usr/bin/env python3
"""
Add semantic workflow state intelligence to ticketing agent template.
Part of ticket 1M-163: Prompt/Instruction Reinforcement/Hydration
"""

import json
import sys
from pathlib import Path

SEMANTIC_STATE_SECTION = """

## 🔄 SEMANTIC WORKFLOW STATE INTELLIGENCE

**CRITICAL**: When transitioning ticket states, you MUST understand the semantic context and select the most appropriate state from available options.

### Context-Aware State Selection

Different workflow contexts require different states. You must identify the context and choose states that accurately reflect the situation.

---

### Workflow Context Types

#### 1. **Clarification Context** (Waiting for User Input)

**When this applies**:
- Agent or PM requests clarification on requirements
- Ticket has ambiguous acceptance criteria
- Questions posted, waiting for user response
- Work is paused pending user input

**Semantic Intent**: "Work paused, user input needed"

**Preferred States** (in priority order):
1. "Clarify" or "Clarification Needed"
2. "Waiting" or "Waiting for Input"
3. "In Progress" (keep current if no better option)
4. "Blocked" (if clarification is blocking)

**States to AVOID**:
- ❌ "Open" (implies work hasn't started)
- ❌ "Done" or "Closed" (implies complete)
- ❌ "In Review" (implies work is complete and ready for review)

**Example**:
```
Scenario: Research agent posts clarification questions to ticket
Current State: "In Progress"
Available States: ["Open", "In Progress", "Clarify", "Done", "In Review"]

Decision Process:
1. Context identified: Clarification (agent asking user questions)
2. Check preferred states:
   - "Clarify" → ✅ Available (best match)
   - "Waiting" → Not available
3. Selected: "Clarify"

Action: Transition ticket to "Clarify"
```

---

#### 2. **Review Context** (Work Complete, Needs Validation)

**When this applies**:
- Implementation is complete
- QA testing passed
- Work ready for user acceptance testing (UAT)
- Waiting for user to validate/approve

**Semantic Intent**: "Work done, needs user validation"

**Preferred States** (in priority order):
1. "In Review" or "Review" or "Under Review"
2. "UAT" or "User Acceptance Testing"
3. "Ready" or "Ready for Review"
4. "Tested" (if no review state available)
5. "Done" (fallback if no review-specific state)

**States to AVOID**:
- ❌ "In Progress" (implies still working)
- ❌ "Open" (implies not started)
- ❌ "Clarify" (implies waiting for requirements)

**Example**:
```
Scenario: Engineer completes feature, QA passes, ready for user
Current State: "In Progress"
Available States: ["Open", "In Progress", "UAT", "Done", "Closed"]

Decision Process:
1. Context identified: Review (work complete, needs validation)
2. Check preferred states:
   - "In Review" → Not available
   - "UAT" → ✅ Available (best match)
3. Selected: "UAT"

Action: Transition ticket to "UAT"
```

---

#### 3. **Implementation Context** (Active Development)

**When this applies**:
- Agent begins work on ticket
- Implementation is actively in progress
- Not yet ready for review

**Semantic Intent**: "Work actively being developed"

**Preferred States** (in priority order):
1. "In Progress" or "Working"
2. "Started" or "Active"
3. "Development"

**States to AVOID**:
- ❌ "Open" (implies hasn't started)
- ❌ "Done" or "Closed" (implies complete)
- ❌ "In Review" (implies ready for validation)

**Example**:
```
Scenario: Engineer starts implementation
Current State: "Open"
Available States: ["Open", "In Progress", "Done", "Closed"]

Decision Process:
1. Context identified: Implementation (agent starting work)
2. Check preferred states:
   - "In Progress" → ✅ Available (best match)
3. Selected: "In Progress"

Action: Transition ticket to "In Progress"
```

---

#### 4. **Blocked Context** (Work Cannot Proceed)

**When this applies**:
- Agent encounters blocker
- External dependency missing
- Requires unblocking before work continues

**Semantic Intent**: "Work stopped, blocker must be resolved"

**Preferred States** (in priority order):
1. "Blocked"
2. "Waiting" (if no "Blocked" state)
3. "Paused"

**Example**:
```
Scenario: Agent discovers missing API credentials
Current State: "In Progress"
Available States: ["Open", "In Progress", "Blocked", "Done"]

Decision Process:
1. Context identified: Blocked (missing dependency)
2. Check preferred states:
   - "Blocked" → ✅ Available (best match)
3. Selected: "Blocked"

Action: Transition ticket to "Blocked"
```

---

### Semantic State Matching Algorithm

**Step 1: Identify Context**

Analyze the situation:
```
if "clarification" in action_description or "question" in action_description:
    context = "clarification"
elif "complete" in action_description or "ready for review" in action_description:
    context = "review"
elif "start" in action_description or "begin" in action_description:
    context = "implementation"
elif "blocked" in action_description or "blocker" in action_description:
    context = "blocked"
```

**Step 2: Get Available States**

Query ticket system for valid workflow states:
```
available_states = get_workflow_states_for_ticket(ticket_id)
# Example: ["Open", "In Progress", "UAT", "Done", "Closed"]
```

**Step 3: Fuzzy Match Preferred States**

For each preferred state in context, check if similar state available:
```
state_preferences = {
    "clarification": ["clarify", "waiting", "in_progress", "blocked"],
    "review": ["in_review", "uat", "ready", "tested", "done"],
    "implementation": ["in_progress", "working", "started"],
    "blocked": ["blocked", "waiting", "paused"]
}

for preferred in state_preferences[context]:
    for available in available_states:
        if semantic_similarity(preferred, available) > 0.8:
            return available
```

**Step 4: Semantic Similarity Function**

Fuzzy match state names:
```
def semantic_similarity(preferred, available):
    \"\"\"
    Calculate similarity between preferred and available state names.

    Returns: 0.0-1.0 similarity score
    \"\"\"
    # Normalize: lowercase, remove punctuation/spaces
    preferred_norm = normalize(preferred)
    available_norm = normalize(available)

    # Exact match
    if preferred_norm == available_norm:
        return 1.0

    # Contains match
    if preferred_norm in available_norm or available_norm in preferred_norm:
        return 0.9

    # Semantic equivalence
    equivalents = {
        "clarify": ["clarification", "clarify", "clarification_needed"],
        "in_review": ["review", "in_review", "under_review", "uat", "user_acceptance"],
        "in_progress": ["in_progress", "working", "active", "started"],
        "blocked": ["blocked", "blocker", "blocked_on"],
        "waiting": ["waiting", "wait", "pending", "on_hold"]
    }

    for key, variants in equivalents.items():
        if preferred_norm in variants and available_norm in variants:
            return 0.85

    # No match
    return 0.0
```

---

### Implementation Examples

**Example 1: Clarification Needed**

```
Task: Transition ticket 1M-163 to clarification state

Current State: "In Progress"
Available States: ["Open", "In Progress", "Clarification Needed", "Done", "Closed"]

Step 1: Identify context
→ Context: "clarification" (agent posted questions)

Step 2: Get preferred states for clarification
→ ["clarify", "waiting", "in_progress", "blocked"]

Step 3: Fuzzy match against available states
→ "clarify" matches "Clarification Needed" (similarity: 0.9)

Step 4: Select best match
→ Selected: "Clarification Needed"

Action: mcp__mcp-ticketer__ticket_update(
    ticket_id="1M-163",
    state="Clarification Needed"
)
```

**Example 2: Ready for UAT**

```
Task: Mark ticket complete and ready for user testing

Current State: "In Progress"
Available States: ["Open", "In Progress", "UAT", "Done", "Closed"]

Step 1: Identify context
→ Context: "review" (work complete, needs validation)

Step 2: Get preferred states for review
→ ["in_review", "uat", "ready", "tested", "done"]

Step 3: Fuzzy match against available states
→ "uat" matches "UAT" (similarity: 1.0)

Step 4: Select best match
→ Selected: "UAT"

Action: mcp__mcp-ticketer__ticket_update(
    ticket_id="1M-163",
    state="UAT"
)
```

**Example 3: No Perfect Match (Fallback)**

```
Task: Start implementation

Current State: "Open"
Available States: ["Open", "Done", "Closed"]

Step 1: Identify context
→ Context: "implementation" (agent starting work)

Step 2: Get preferred states for implementation
→ ["in_progress", "working", "started"]

Step 3: Fuzzy match against available states
→ No matches found (no "In Progress" or equivalent)

Step 4: Fallback strategy
→ Keep current state "Open" (work will transition when first commit made)
→ OR create comment explaining state limitation

Action: Keep state as "Open" + Add comment:
"Implementation started. Note: No 'In Progress' state available in workflow."
```

---

### Cross-Platform State Mapping

Different platforms have different state names. Map semantically equivalent states:

**Linear Common States**:
- Backlog, Triage, Todo → "Open"
- In Progress, Started → "In Progress"
- In Review, Review → "In Review"
- Done, Completed → "Done"
- Canceled → "Closed"

**GitHub Issues States**:
- Open → "Open"
- Closed → "Done"
- (Custom states via projects)

**JIRA Common States**:
- To Do, Open → "Open"
- In Progress → "In Progress"
- In Review, Code Review → "In Review"
- Done, Closed → "Done"
- Blocked, On Hold → "Blocked"

---

### When to Update States

**ALWAYS update state when**:
- Agent posts clarification questions → "Clarify" or "Waiting"
- Agent completes implementation + QA passes → "In Review" or "UAT"
- Agent starts work on ticket → "In Progress"
- Agent encounters blocker → "Blocked"

**NEVER update state when**:
- Just reading ticket for context (no work done)
- Adding informational comments (not changing workflow)
- Ticket already in appropriate state

---

### Reporting State Transitions

When transitioning states, ALWAYS report:

```json
{
  "state_transition": {
    "ticket_id": "1M-163",
    "previous_state": "In Progress",
    "new_state": "Clarification Needed",
    "context": "clarification",
    "reason": "Agent posted clarification questions to ticket",
    "semantic_match_score": 0.9,
    "available_states_checked": ["Open", "In Progress", "Clarification Needed", "Done"],
    "preferred_states_order": ["clarify", "waiting", "in_progress", "blocked"]
  }
}
```

---

### Success Criteria

This semantic state intelligence is successful when:
- ✅ States accurately reflect workflow status (not just literal names)
- ✅ Clarification tickets are identifiable (not stuck in "In Progress")
- ✅ Completed work transitions to review states (not "Done" prematurely)
- ✅ Cross-platform state mapping works (Linear, GitHub, JIRA)
- ✅ Fuzzy matching handles variant state names

**Violation**: Using literal state names without considering semantic context
"""


def main():
    """Add semantic state intelligence section to ticketing agent."""

    # File path
    template_path = Path("/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/ticketing.json")

    if not template_path.exists():
        print(f"❌ Error: Template file not found: {template_path}")
        sys.exit(1)

    # Read existing JSON
    print(f"📖 Reading {template_path}...")
    with open(template_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Get current instructions
    current_instructions = data.get('instructions', '')
    current_length = len(current_instructions)

    # Check if already added (avoid duplicates)
    if "SEMANTIC WORKFLOW STATE INTELLIGENCE" in current_instructions:
        print("⚠️  Semantic state intelligence section already exists!")
        print("   Skipping duplicate addition.")
        sys.exit(0)

    # Append new section
    print("✏️  Appending semantic state intelligence section...")
    data['instructions'] = current_instructions + SEMANTIC_STATE_SECTION

    new_length = len(data['instructions'])
    lines_added = SEMANTIC_STATE_SECTION.count('\n')

    # Write updated JSON
    print(f"💾 Writing updated template...")
    with open(template_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Validation
    print("✅ Validating JSON structure...")
    with open(template_path, 'r', encoding='utf-8') as f:
        json.load(f)  # Will raise exception if invalid

    # Report results
    print("\n" + "="*60)
    print("✅ SUCCESS: Semantic state intelligence added!")
    print("="*60)
    print(f"📄 File: {template_path}")
    print(f"📏 Original length: {current_length:,} characters")
    print(f"📏 New length: {new_length:,} characters")
    print(f"➕ Characters added: {new_length - current_length:,}")
    print(f"📝 Lines added: {lines_added}")
    print(f"🎯 Ticket: 1M-163")
    print("\n🔍 Section includes:")
    print("   - 4 workflow context types (clarification, review, implementation, blocked)")
    print("   - Semantic matching algorithm with fuzzy logic")
    print("   - 3 detailed implementation examples")
    print("   - Cross-platform state mapping (Linear, GitHub, JIRA)")
    print("   - State transition reporting format")
    print("   - Success criteria and violation warnings")
    print("\n✅ JSON validation: PASSED")


if __name__ == '__main__':
    main()
