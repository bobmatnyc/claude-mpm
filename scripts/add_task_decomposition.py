#!/usr/bin/env python3
"""
Add task decomposition protocol to base_agent.json (Ticket 1M-168)
"""

import json
import sys
from pathlib import Path

# Task decomposition content to insert
TASK_DECOMPOSITION_CONTENT = """## 🔨 TASK DECOMPOSITION PROTOCOL (MANDATORY)

**CRITICAL**: Before executing ANY non-trivial task, you MUST decompose it into sub-tasks for self-validation.

### Why Decomposition Matters

**Best Practice from 2025 AI Research** (Anthropic, Microsoft):
> "Asking a model to first break a problem into sub-problems (decomposition) or critique its own answer (self-criticism) can lead to smarter, more accurate outputs."

**Benefits**:
- Catches missing requirements early
- Identifies dependencies before implementation
- Surfaces complexity that wasn't obvious
- Provides self-validation checkpoints
- Improves estimation accuracy

---

### When to Decompose

**ALWAYS decompose when**:
- ✅ Task requires multiple steps (>2 steps)
- ✅ Task involves multiple files/modules
- ✅ Task has dependencies or prerequisites
- ✅ Task complexity is unclear
- ✅ Task acceptance criteria has multiple parts

**CAN SKIP decomposition when**:
- ❌ Single-step trivial task (e.g., "update version number")
- ❌ Task is already decomposed (e.g., "implement step 3 of X")
- ❌ Urgency requires immediate action (rare exceptions only)

---

### Decomposition Process (4 Steps)

**Step 1: Identify Sub-Tasks**

Break the main task into logical sub-tasks:
```
Main Task: "Add user authentication"

Sub-Tasks:
1. Create user model and database schema
2. Implement password hashing service
3. Create login endpoint
4. Create registration endpoint
5. Add JWT token generation
6. Add authentication middleware
7. Write tests for auth flow
```

**Step 2: Order by Dependencies**

Sequence sub-tasks based on dependencies:
```
Order:
1. Create user model and database schema (no dependencies)
2. Implement password hashing service (depends on #1)
3. Add JWT token generation (depends on #1)
4. Create registration endpoint (depends on #2)
5. Create login endpoint (depends on #2, #3)
6. Add authentication middleware (depends on #3)
7. Write tests for auth flow (depends on all above)
```

**Step 3: Validate Completeness**

Self-validation checklist:
- [ ] All acceptance criteria covered by sub-tasks?
- [ ] All dependencies identified?
- [ ] All affected files/modules included?
- [ ] Tests included in decomposition?
- [ ] Documentation updates included?
- [ ] Edge cases considered?

**Step 4: Estimate Complexity**

Rate each sub-task:
- **Simple** (S): 5-15 minutes, straightforward implementation
- **Medium** (M): 15-45 minutes, requires some thought
- **Complex** (C): 45+ minutes, significant complexity

```
Complexity Estimates:
1. Create user model (M) - 20 min
2. Password hashing (S) - 10 min
3. JWT generation (M) - 30 min
4. Registration endpoint (M) - 25 min
5. Login endpoint (M) - 25 min
6. Auth middleware (S) - 15 min
7. Tests (C) - 60 min

Total Estimate: 185 minutes (~3 hours)
```

---

### Decomposition Template

Use this template for decomposing tasks:

```markdown
## Task Decomposition: [Main Task Title]

### Sub-Tasks (Ordered by Dependencies)
1. [Sub-task 1] - Complexity: S/M/C - Est: X min
   Dependencies: None
   Files: [file paths]

2. [Sub-task 2] - Complexity: S/M/C - Est: X min
   Dependencies: #1
   Files: [file paths]

3. [Sub-task 3] - Complexity: S/M/C - Est: X min
   Dependencies: #1, #2
   Files: [file paths]

[... etc ...]

### Validation Checklist
- [ ] All acceptance criteria covered
- [ ] All dependencies identified
- [ ] All files included
- [ ] Tests included
- [ ] Docs included
- [ ] Edge cases considered

### Total Complexity
- Simple: N tasks (X min)
- Medium: N tasks (X min)
- Complex: N tasks (X min)
- **Total Estimate**: X hours

### Risks Identified
- [Risk 1]: [Mitigation]
- [Risk 2]: [Mitigation]
```

---

### Examples

**Example 1: Simple Task (No Decomposition Needed)**

```
Task: "Update version number to 1.2.3 in package.json"

Decision: SKIP decomposition
Reason: Single-step trivial task, no dependencies
Action: Proceed directly to execution
```

**Example 2: Medium Complexity Task (Decomposition Required)**

```
Task: "Add rate limiting to API endpoints"

## Task Decomposition: Add Rate Limiting

### Sub-Tasks (Ordered by Dependencies)
1. Research rate limiting libraries - Complexity: S - Est: 10 min
   Dependencies: None
   Files: package.json

2. Install and configure redis for rate limit storage - Complexity: M - Est: 20 min
   Dependencies: #1
   Files: docker-compose.yml, .env

3. Create rate limit middleware - Complexity: M - Est: 30 min
   Dependencies: #2
   Files: src/middleware/rateLimit.js

4. Apply middleware to API routes - Complexity: S - Est: 15 min
   Dependencies: #3
   Files: src/routes/*.js

5. Add rate limit headers to responses - Complexity: S - Est: 10 min
   Dependencies: #3
   Files: src/middleware/rateLimit.js

6. Write tests for rate limiting - Complexity: M - Est: 40 min
   Dependencies: #3, #4, #5
   Files: tests/middleware/rateLimit.test.js

7. Update API documentation - Complexity: S - Est: 15 min
   Dependencies: All above
   Files: docs/api.md

### Validation Checklist
- [x] All acceptance criteria covered (rate limiting functional)
- [x] All dependencies identified (redis)
- [x] All files included (middleware, routes, tests, docs)
- [x] Tests included (#6)
- [x] Docs included (#7)
- [x] Edge cases considered (burst traffic, distributed systems)

### Total Complexity
- Simple: 4 tasks (50 min)
- Medium: 3 tasks (90 min)
- Complex: 0 tasks (0 min)
- **Total Estimate**: 2.3 hours

### Risks Identified
- Redis dependency: Ensure redis available in all environments
- Distributed rate limiting: May need shared redis for multiple instances
```

**Example 3: Complex Task (Decomposition Critical)**

```
Task: "Implement real-time collaborative editing"

## Task Decomposition: Real-Time Collaborative Editing

### Sub-Tasks (Ordered by Dependencies)
1. Research operational transformation algorithms - Complexity: C - Est: 90 min
2. Set up WebSocket server - Complexity: M - Est: 45 min
3. Implement document versioning - Complexity: C - Est: 120 min
4. Create conflict resolution logic - Complexity: C - Est: 180 min
5. Build client-side WebSocket handler - Complexity: M - Est: 60 min
6. Implement presence indicators - Complexity: M - Est: 45 min
7. Add cursor position synchronization - Complexity: M - Est: 60 min
8. Write comprehensive tests - Complexity: C - Est: 150 min
9. Performance optimization - Complexity: C - Est: 90 min
10. Documentation and deployment guide - Complexity: M - Est: 60 min

### Total Estimate: 15 hours (complex feature)

Decision: Recommend breaking into separate tickets for each sub-task
```

---

### Integration with Execution Workflow

**Full Workflow**:
```
Task Assigned
    ↓
Check if trivial? → YES → Execute directly
    ↓ NO
Decompose Task (4 steps)
    ↓
Validate decomposition (checklist)
    ↓
Estimate complexity
    ↓
    ├─ Simple/Medium → Proceed with execution
    ↓
    └─ Complex → Recommend breaking into sub-tickets
    ↓
Execute sub-tasks in dependency order
    ↓
Validate each sub-task complete before next
    ↓
Final validation against acceptance criteria
```

---

### Reporting Decomposition

Include decomposition in your work report:

```json
{
  "task_decomposition": {
    "decomposed": true,
    "sub_tasks": [
      {"id": 1, "title": "...", "complexity": "M", "completed": true},
      {"id": 2, "title": "...", "complexity": "S", "completed": true}
    ],
    "total_estimate": "2.3 hours",
    "actual_time": "2.1 hours",
    "estimation_accuracy": "91%"
  }
}
```

---

### Success Criteria

This decomposition protocol is successful when:
- ✅ All non-trivial tasks are decomposed before execution
- ✅ Dependencies identified early (avoid implementation order issues)
- ✅ Complexity estimates improve over time (learning)
- ✅ Complex tasks flagged for sub-ticket creation
- ✅ Fewer "missed requirements" discovered during implementation

**Target**: 85% of non-trivial tasks decomposed (up from 70%)

**Violation**: Starting complex implementation without decomposition = high risk of rework


"""


def main():
    # File path
    base_agent_path = (
        Path(__file__).parent.parent
        / "src"
        / "claude_mpm"
        / "agents"
        / "base_agent.json"
    )

    if not base_agent_path.exists():
        print(f"❌ Error: File not found: {base_agent_path}", file=sys.stderr)
        sys.exit(1)

    # Read the JSON file
    print(f"📖 Reading {base_agent_path}...")
    with open(base_agent_path, encoding="utf-8") as f:
        data = json.load(f)

    # Get current instructions
    instructions = data["narrative_fields"]["instructions"]

    # Find the insertion point (before "## Task Execution Protocol")
    insertion_marker = "## Task Execution Protocol"
    if insertion_marker not in instructions:
        print(
            f"❌ Error: Could not find insertion marker: {insertion_marker}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Insert the task decomposition content
    instructions = instructions.replace(
        insertion_marker, TASK_DECOMPOSITION_CONTENT + insertion_marker
    )

    # Update the data
    data["narrative_fields"]["instructions"] = instructions

    # Write back to file with proper formatting
    print(f"💾 Writing updated content back to {base_agent_path}...")
    with open(base_agent_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Count lines added
    lines_added = TASK_DECOMPOSITION_CONTENT.count("\n")

    print("\n✅ Successfully added task decomposition protocol!")
    print(f"📊 Lines added: ~{lines_added}")
    print(f"📁 File: {base_agent_path}")
    print(f"📍 Inserted BEFORE: {insertion_marker}")
    print("\n🔍 Validating JSON...")

    # Validate by re-reading
    try:
        with open(base_agent_path, encoding="utf-8") as f:
            json.load(f)
        print("✅ JSON is valid!")
    except json.JSONDecodeError as e:
        print(f"❌ JSON validation failed: {e}", file=sys.stderr)
        sys.exit(1)

    print(
        "\n✅ Task decomposition protocol successfully implemented for ticket 1M-168!"
    )


if __name__ == "__main__":
    main()
