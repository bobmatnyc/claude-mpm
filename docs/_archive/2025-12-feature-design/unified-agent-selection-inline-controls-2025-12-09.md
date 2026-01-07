# Research: Unified Agent Selection UI Inline Controls

**Date**: 2025-12-09
**Researcher**: Research Agent
**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure.py`
**Method**: `_deploy_agents_unified()`

## Executive Summary

The unified agent selection UI uses **questionary.checkbox()** which is a **one-shot, non-interactive control pattern**. When users select inline controls like "[Select all from MPM Agents]" or "[Select recommended]", the checkboxes do NOT visually toggle in real-time. Instead, the special control values are processed AFTER the user presses Enter, at which point the system calculates the final selection set.

**Current Behavior**: User sees checkboxes → selects controls → presses Enter → system processes special values → applies changes
**User Experience**: No immediate visual feedback when selecting inline controls
**Limitation**: Questionary checkbox is fundamentally one-shot - cannot loop back to re-display with updated selections

## Detailed Analysis

### 1. Implementation Architecture

**File Location**: `src/claude_mpm/cli/commands/configure.py`
**Method**: `_deploy_agents_unified()` (lines 1189-1529)

**Flow**:
```python
# 1. Build checkbox choices with inline controls
choices = []
for collection_id in sorted(collections.keys()):
    # Add collection header
    choices.append(Separator(...))

    # Add inline controls
    choices.append(Choice(
        f"  [Select all from {collection_id}]",
        value=f"__SELECT_ALL_{collection_id}__",
        checked=False,
    ))

    choices.append(Choice(
        f"  [Select recommended ({len(recommended_in_collection)} agents)]",
        value=f"__SELECT_REC_{collection_id}__",
        checked=False,
    ))

    # Add individual agents
    for agent in agents_in_category:
        choices.append(Choice(
            title=choice_text,
            value=agent.name,
            checked=is_selected,
        ))

# 2. Display questionary checkbox (ONE-SHOT)
selected_values = questionary.checkbox(
    "Select agents:",
    choices=choices,
    instruction="(Space to toggle, Enter to continue)",
    style=self.QUESTIONARY_STYLE,
).ask()

# 3. Process special inline control selections AFTER user presses Enter
final_selection = set()
for value in selected_values:
    if value.startswith("__SELECT_ALL_"):
        # Extract collection ID and add all agents
        collection_id = value.replace("__SELECT_ALL_", "").replace("__", "")
        for agent in collections[collection_id]:
            final_selection.add(agent.name)
    elif value.startswith("__SELECT_REC_"):
        # Extract collection ID and add only recommended agents
        collection_id = value.replace("__SELECT_REC_", "").replace("__", "")
        for agent in collections[collection_id]:
            if any(...):
                final_selection.add(agent.name)
    else:
        # Regular agent selection
        final_selection.add(value)
```

### 2. Special Control Values

**Pattern**: Special values use double underscore prefix/suffix to avoid collisions with agent IDs

**Select All Control**:
- Display: `"  [Select all from {collection_id}]"`
- Value: `f"__SELECT_ALL_{collection_id}__"`
- Example: `"__SELECT_ALL_MPM Agents__"`

**Select Recommended Control**:
- Display: `"  [Select recommended ({count} agents)]"`
- Value: `f"__SELECT_REC_{collection_id}__"`
- Example: `"__SELECT_REC_MPM Agents__"`

**Processing Logic** (lines 1401-1422):
```python
# Extract collection ID by removing prefix/suffix
collection_id = value.replace("__SELECT_ALL_", "").replace("__", "")
collection_id = value.replace("__SELECT_REC_", "").replace("__", "")
```

### 3. UI Interaction Model

**Questionary Checkbox Behavior**:
- **One-shot interaction**: User navigates and toggles → presses Enter → returns selected values
- **No state updates during interaction**: Cannot loop back to re-display with updated selections
- **Visual indicators**: Uses `[✓]` for checked, `[ ]` for unchecked (lines 1369-1370)

**User Flow**:
```
1. Display checkbox UI with:
   - Collection headers
   - Inline controls (unchecked)
   - Individual agents (checked if deployed)

2. User navigates with arrow keys

3. User presses space on "[Select all from MPM Agents]"
   → Checkbox shows [✓] for that control item
   → Individual agent checkboxes DO NOT update visually

4. User presses Enter

5. System processes selected_values:
   - Detects "__SELECT_ALL_MPM Agents__" in selected_values
   - Adds all agents from "MPM Agents" collection to final_selection
   - Ignores individual agent selections for that collection

6. Applies changes based on final_selection
```

### 4. Limitation Analysis

**Questionary Library Constraint**:
- Questionary checkbox is **fundamentally one-shot**
- No built-in support for dynamic state updates
- Cannot re-display UI with updated checkbox states mid-interaction

**Why Looping Doesn't Work**:
```python
# ❌ This pattern would NOT work:
while True:
    selected_values = questionary.checkbox(...).ask()

    # Process special controls
    if any(v.startswith("__SELECT_ALL_") for v in selected_values):
        # Update current_selection
        current_selection.update(...)
        # Loop back to re-display
        continue  # ❌ User sees a NEW checkbox UI, loses previous selections

    break
```

**User Experience Problem**:
- User selects "[Select all from MPM Agents]"
- Presses Enter expecting to see all agents checked
- Instead, sees confirmation screen: "Install 45 agents?"
- No visual feedback that control worked until after confirmation

### 5. Alternative Approaches

#### Option A: Two-Step Process (Recommended)

**Advantages**:
- Works within questionary constraints
- Clear user feedback
- Separates control selection from agent selection

**Implementation**:
```python
# Step 1: Select control action
action = questionary.select(
    "Quick actions:",
    choices=[
        "Select all from MPM Agents",
        "Select recommended agents",
        "Manual agent selection",
    ]
).ask()

# Step 2: If manual, show checkbox with updated selections
if action == "Manual agent selection":
    selected_values = questionary.checkbox(
        "Select agents:",
        choices=choices,
        # Pre-checked based on previous quick action
    ).ask()
```

**User Flow**:
1. User selects "Select all from MPM Agents" from menu
2. System applies selection logic
3. Shows checkbox UI with all MPM agents pre-checked
4. User can adjust individual selections
5. Presses Enter to confirm

#### Option B: Prompt Toolkit with Live Updates (Complex)

**Advantages**:
- Real-time visual feedback
- Interactive state updates

**Disadvantages**:
- Requires custom prompt_toolkit implementation
- Significantly more complex than questionary
- May have terminal compatibility issues

**Example**:
```python
from prompt_toolkit.application import Application
from prompt_toolkit.layout import Layout
from prompt_toolkit.widgets import CheckboxList

# Custom event handlers for inline controls
# Update checkbox states in real-time
```

#### Option C: Keep Current Approach with Better Documentation

**Advantages**:
- No code changes
- Works with current questionary implementation

**Improvements**:
- Add help text explaining inline controls
- Show preview before confirmation
- Clearer user instructions

**Enhanced Instructions**:
```python
self.console.print("[dim]INLINE CONTROLS:[/dim]")
self.console.print("[dim]  [Select all from X] - Marks all agents in collection X[/dim]")
self.console.print("[dim]  [Select recommended] - Marks only recommended agents[/dim]")
self.console.print("[dim]  Inline controls override individual selections in their collection[/dim]")
self.console.print("[dim]  Press Enter after selecting controls to apply[/dim]\n")
```

### 6. Related Code: `_deploy_agents_individual()` (Deprecated)

**Location**: Lines 1530-1983
**Status**: Deprecated, kept for backward compatibility
**Design**: Multi-step process with collection selection → individual fine-tuning
**Key Difference**: Uses sequential prompts instead of nested checkboxes

**Pattern**:
```python
while True:
    # Step 1: Collection-level selection
    selected_collections = questionary.checkbox(
        "Select agent collections:",
        choices=collection_choices,
    ).ask()

    # Step 2: Individual fine-tuning (optional)
    if "__INDIVIDUAL__" in selected_collections:
        selected_agent_ids = questionary.checkbox(
            "Select individual agents:",
            choices=agent_choices,
        ).ask()

    # Step 3: Confirm, adjust, or cancel
    action = questionary.select(
        "What would you like to do?",
        choices=["Apply", "Adjust", "Cancel"]
    ).ask()

    if action == "adjust":
        continue  # Loop back to step 1
    break
```

**Why It Works**:
- Each loop iteration shows a FRESH checkbox UI
- User sees updated selections after "Adjust"
- Separates control actions into discrete steps

## Recommendations

### Recommended Solution: Two-Step Process (Option A)

**Rationale**:
1. **Works within constraints**: No questionary hacks required
2. **Clear user feedback**: User sees effect of quick actions immediately
3. **Maintains flexibility**: User can still fine-tune individual selections
4. **Consistent with deprecated approach**: Similar to `_deploy_agents_individual()` pattern

**Implementation Plan**:

**Step 1**: Add quick action menu before checkbox UI
```python
def _deploy_agents_unified(self, agents: List[AgentConfig]) -> None:
    # ... existing setup code ...

    # NEW: Quick action menu
    self.console.print("\n[bold cyan]Quick Agent Selection[/bold cyan]\n")
    quick_action = questionary.select(
        "Choose a quick action:",
        choices=[
            "Select all agents",
            "Select recommended agents",
            "Select agents by collection",
            "Manual selection (show all)",
            "← Back",
        ],
        style=self.QUESTIONARY_STYLE,
    ).ask()

    if quick_action == "← Back":
        return

    # Apply quick action to current_selection
    if quick_action == "Select all agents":
        current_selection = {a.name for a in agents}
    elif quick_action == "Select recommended agents":
        current_selection = {a.name for a in agents if is_recommended(a)}
    elif quick_action == "Select agents by collection":
        # Show collection-level selection
        ...
    # else: Manual selection (use existing checkbox)
```

**Step 2**: Show checkbox UI with pre-selections
```python
    # Build choices with current_selection pre-checked
    choices = []
    for agent in agents:
        choices.append(Choice(
            title=agent_display_text,
            value=agent.name,
            checked=(agent.name in current_selection),  # Pre-checked
        ))

    # User can adjust individual selections
    selected_values = questionary.checkbox(
        "Select agents (pre-selected based on quick action):",
        choices=choices,
        style=self.QUESTIONARY_STYLE,
    ).ask()
```

**Step 3**: Show confirmation and apply
```python
    # ... existing confirmation and deployment code ...
```

### Alternative: Enhance Current Approach (Option C)

**If two-step process is too disruptive**:

**Enhancement 1**: Better instructions
```python
self.console.print("\n[bold yellow]Inline Controls:[/bold yellow]")
self.console.print("[dim]  • [Select all from X] - Marks ALL agents in collection X[/dim]")
self.console.print("[dim]  • [Select recommended] - Marks ONLY recommended agents[/dim]")
self.console.print("[dim]  • Inline controls OVERRIDE individual selections in their collection[/dim]")
self.console.print("[dim]  • Press Enter to apply selections[/dim]\n")
```

**Enhancement 2**: Preview before confirmation
```python
# After processing selected_values
self.console.print("\n[bold]You selected:[/bold]")
if any(v.startswith("__SELECT_ALL_") for v in selected_values):
    for value in selected_values:
        if value.startswith("__SELECT_ALL_"):
            collection_id = value.replace("__SELECT_ALL_", "").replace("__", "")
            count = len(collections[collection_id])
            self.console.print(f"  • ALL agents from {collection_id} ({count} agents)")

# Then show final confirmation
confirm = Confirm.ask("Apply these selections?", default=True)
```

## Testing Recommendations

### Manual Testing Scenarios

**Scenario 1**: Select all from single collection
1. Navigate to "[Select all from MPM Agents]"
2. Press space
3. Press Enter
4. Verify: All MPM agents are added to final_selection

**Scenario 2**: Select recommended
1. Navigate to "[Select recommended (5 agents)]"
2. Press space
3. Press Enter
4. Verify: Only 5 recommended agents are added

**Scenario 3**: Mixed selection
1. Check individual agent "python-engineer"
2. Navigate to "[Select all from MPM Agents]"
3. Press space
4. Press Enter
5. Verify: ALL MPM agents are added (not just python-engineer)

**Scenario 4**: Cancellation
1. Select controls
2. Press Ctrl+C or select cancel
3. Verify: No changes applied

### Unit Testing

**Test Case 1**: Special value parsing
```python
def test_select_all_value_parsing():
    value = "__SELECT_ALL_MPM Agents__"
    collection_id = value.replace("__SELECT_ALL_", "").replace("__", "")
    assert collection_id == "MPM Agents"
```

**Test Case 2**: Final selection calculation
```python
def test_final_selection_with_select_all():
    selected_values = [
        "__SELECT_ALL_MPM Agents__",
        "some-other-agent",
    ]

    collections = {
        "MPM Agents": [agent1, agent2, agent3],
        "Local Agents": [agent4],
    }

    final_selection = process_selections(selected_values, collections)

    assert agent1.name in final_selection
    assert agent2.name in final_selection
    assert agent3.name in final_selection
    assert "some-other-agent" in final_selection
    assert agent4.name not in final_selection
```

## Conclusion

**Current Implementation**: Works correctly but lacks immediate visual feedback due to questionary's one-shot nature.

**Root Cause**: Questionary checkbox cannot loop back with updated state - it's fundamentally a one-time interaction.

**Recommendation**: Implement **Two-Step Process (Option A)** to provide clear visual feedback:
1. Quick action menu (select all, recommended, etc.)
2. Checkbox UI with pre-selections based on quick action
3. User can adjust individual selections
4. Confirmation and deployment

**Fallback**: If two-step is too disruptive, enhance current approach with better instructions and preview (Option C).

**Do NOT pursue**: Option B (prompt_toolkit) - too complex, terminal compatibility issues, not worth the effort for this use case.

## References

- **Main Implementation**: `src/claude_mpm/cli/commands/configure.py:1189-1529`
- **Deprecated Approach**: `src/claude_mpm/cli/commands/configure.py:1530-1983`
- **Questionary Documentation**: https://github.com/tmbo/questionary
- **Special Control Pattern**: Lines 1296-1318 (inline control creation)
- **Processing Logic**: Lines 1401-1422 (special value handling)
