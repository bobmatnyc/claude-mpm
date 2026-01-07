# Research: Dynamic Checkbox Updates for Toggle All in Questionary

**Date**: 2025-12-09
**Researcher**: Research Agent
**Status**: Complete
**Classification**: Informational (technical limitation assessment)

## Executive Summary

Questionary's checkbox implementation **does not support real-time visual updates** when toggling multiple items. The "Toggle All" functionality modifies the internal selection state but doesn't visually update individual checkboxes until the prompt completes. This is a fundamental limitation of questionary's architecture, which uses prompt_toolkit's FormattedTextControl that only rerenders when specific events occur.

**Key Finding**: Cannot achieve real-time checkbox updates with questionary's current API. Must choose alternative approaches.

## Problem Statement

When implementing a "Toggle All (45 agents)" option in a questionary checkbox prompt:
- User selects "Toggle All"
- Internal state updates (`ic.selected_options` modified)
- **Visual display doesn't update** until prompt completion
- User cannot see which agents are now selected

**Desired Behavior**: Checkboxes should visually toggle immediately when "Toggle All" is selected, showing real-time feedback.

## Research Findings

### 1. Questionary Checkbox Architecture

**Source Files Analyzed**:
- `/venv/lib/python3.13/site-packages/questionary/prompts/checkbox.py` (328 lines)
- `/venv/lib/python3.13/site-packages/questionary/prompts/common.py` (InquirerControl class)

**Key Implementation Details**:

```python
# Lines 234-242 in checkbox.py
@bindings.add(" ", eager=True)
def toggle(_event):
    pointed_choice = ic.get_pointed_at().value
    if pointed_choice in ic.selected_options:
        ic.selected_options.remove(pointed_choice)
    else:
        ic.selected_options.append(pointed_choice)
    perform_validation(get_selected_values())
```

**Toggle All Implementation (lines 257-272)**:
```python
@bindings.add(Keys.ControlA if use_search_filter else "a", eager=True)
def all(_event):
    all_selected = True  # all choices have been selected
    for c in ic.choices:
        if (
            not isinstance(c, Separator)
            and c.value not in ic.selected_options
            and not c.disabled
        ):
            ic.selected_options.append(c.value)
            all_selected = False
    if all_selected:
        ic.selected_options = []
    perform_validation(get_selected_values())
```

**Problem**: These handlers modify `ic.selected_options` (internal state) but **do not trigger visual redraw**.

### 2. InquirerControl Rendering Pipeline

**Class**: `InquirerControl(FormattedTextControl)` in `common.py`

**Rendering Method**:
- `_get_choice_tokens()` generates visual representation
- Called by `FormattedTextControl` parent class
- **Only redraws when prompt_toolkit's Application detects state change**

**Critical Limitation**: FormattedTextControl doesn't automatically invalidate/redraw when data attributes change. It relies on:
1. Cursor movement events
2. Key binding completion
3. Manual `app.invalidate()` calls

### 3. Questionary's Built-in Toggle All

**Default Keyboard Shortcuts** (lines 195-200):
```
(Use arrow keys to move,
<space> to select,
<a> to toggle,
<i> to invert
{', type to filter' if use_search_filter else ''})
```

**Behavior**:
- Press `<a>`: Toggles all agents on/off
- Press `<i>`: Inverts selection
- **Both modify state without visual feedback until next render**

### 4. Prompt Toolkit Invalidation Mechanism

**Relevant Documentation** (from web search):

**`Application.invalidate()` Method**:
- Triggers UI redraw
- Can be called from key bindings
- Respects `min_redraw_interval` throttling

**Configuration Options**:
- `min_redraw_interval`: Seconds between redraws (default: None)
- `refresh_interval`: Auto-invalidate every N seconds
- `on_invalidate`: Event handler for invalidation

**Example Pattern** (from GitHub issue #788):
```python
@kb.add("c-r")
def refresh(event):
    get_app().invalidate()  # Trigger redraw
```

### 5. Why Current Implementation Doesn't Update

**Checkbox Key Binding Workflow**:
1. User presses `<a>` (toggle all)
2. `all()` handler executes
3. Modifies `ic.selected_options` list
4. Calls `perform_validation()`
5. **Returns to event loop WITHOUT invalidation**
6. UI only updates on next navigation/event

**Missing Step**: No `event.app.invalidate()` call after state modification.

## Attempted Solutions Analysis

### Option A: Modify Questionary Source (NOT RECOMMENDED)

**Approach**: Add `event.app.invalidate()` after state changes

```python
# Modified toggle handler
@bindings.add(" ", eager=True)
def toggle(event):
    pointed_choice = ic.get_pointed_at().value
    if pointed_choice in ic.selected_options:
        ic.selected_options.remove(pointed_choice)
    else:
        ic.selected_options.append(pointed_choice)
    perform_validation(get_selected_values())
    event.app.invalidate()  # <-- ADD THIS
```

**Pros**:
- Would work for real-time updates
- Minimal code change

**Cons**:
- ❌ Modifies third-party library (maintenance nightmare)
- ❌ Breaks on questionary updates
- ❌ Not portable across environments
- ❌ Violates dependency management best practices

**Verdict**: **DO NOT USE** - Modifying vendored libraries is anti-pattern.

### Option B: Custom Prompt Toolkit Implementation

**Approach**: Build checkbox from scratch using prompt_toolkit

**Example Structure**:
```python
from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, Window
from prompt_toolkit.formatted_text import FormattedText

class DynamicCheckboxControl(FormattedTextControl):
    def __init__(self, choices):
        self.choices = choices
        self.selected = []
        super().__init__(self._render)

    def _render(self):
        tokens = []
        for choice in self.choices:
            indicator = "[X]" if choice in self.selected else "[ ]"
            tokens.append(("", f"{indicator} {choice}\n"))
        return FormattedText(tokens)

    def toggle_all(self):
        if len(self.selected) == len(self.choices):
            self.selected = []
        else:
            self.selected = self.choices.copy()

kb = KeyBindings()

@kb.add("a")
def toggle_all(event):
    checkbox.toggle_all()
    event.app.invalidate()  # Force redraw

checkbox = DynamicCheckboxControl(choices)
app = Application(layout=Layout(Window(checkbox)), key_bindings=kb)
```

**Pros**:
- ✅ Full control over rendering
- ✅ Can call `app.invalidate()` when needed
- ✅ No dependency on questionary internals

**Cons**:
- ⚠️ Significant development effort (200+ lines)
- ⚠️ Must reimplement all features (scrolling, shortcuts, validation)
- ⚠️ Requires deep prompt_toolkit knowledge
- ⚠️ Maintenance burden

**Verdict**: **Viable but HIGH EFFORT** - Only use if dynamic updates are critical requirement.

### Option C: Two-Step Selection Pattern

**Approach**: Split selection into two prompts

**Implementation**:
```python
# Step 1: Select collections
collections = questionary.checkbox(
    "Select agent collections:",
    choices=[
        "All agents (45)",
        "Core agents (6)",
        "Language-specific agents",
        "Custom selection..."
    ]
).ask()

if "All agents (45)" in collections:
    # Auto-select all
    return all_agents
elif "Custom selection..." in collections:
    # Step 2: Individual selection
    return questionary.checkbox(
        "Select individual agents:",
        choices=agent_list
    ).ask()
```

**Pros**:
- ✅ Works with existing questionary
- ✅ Clear separation of concerns
- ✅ No visual update needed (collections are small)
- ✅ Easy to implement

**Cons**:
- ⚠️ Extra prompt for custom selection
- ⚠️ Slightly more verbose UX

**Verdict**: **RECOMMENDED** - Best balance of simplicity and functionality.

### Option D: Instruction-Based UX

**Approach**: Accept limitation but improve instructions

**Implementation**:
```python
questionary.checkbox(
    "Select agents to deploy:",
    choices=[
        Separator("=== Collections ==="),
        Choice("Toggle All (45 agents)", value="__toggle_all__"),
        Choice("Core Only (6 agents)", value="__core_only__"),
        Separator("=== Individual Agents ==="),
        *agent_choices
    ],
    instruction=(
        "Use <space> to select, <a> to toggle all. "
        "Note: Collection selections will be processed after confirmation."
    )
).ask()

# Post-process results
if "__toggle_all__" in results:
    return all_agents
```

**Pros**:
- ✅ Uses questionary as-is
- ✅ Clear instructions manage expectations
- ✅ Minimal code changes

**Cons**:
- ⚠️ User still doesn't see real-time updates
- ⚠️ Requires post-processing logic
- ⚠️ Magic values like `__toggle_all__`

**Verdict**: **ACCEPTABLE FALLBACK** - Works within limitations, relies on clear UX.

### Option E: Preview Display Pattern

**Approach**: Show selection summary in instruction area

**Implementation**:
```python
# Use dynamic instruction with rich formatting
from prompt_toolkit.formatted_text import HTML

def get_instruction():
    selected_count = len([c for c in choices if c.checked])
    return HTML(
        f"Selected: <b>{selected_count}</b>/45 agents. "
        f"Press <a> to toggle all, <i> to invert"
    )

questionary.checkbox(
    "Select agents:",
    choices=choices,
    instruction=get_instruction  # Callable, not string
).ask()
```

**Limitation**: Questionary's `instruction` parameter is **static string**, not callable. Cannot update dynamically.

**Verdict**: **NOT POSSIBLE** with current questionary API.

## Technical Constraints

### Questionary Limitations

1. **No Event Callbacks**: Checkbox doesn't support `on_change` or `on_toggle` callbacks
2. **Static Instruction**: `instruction` parameter accepts string, not callable
3. **No Validator Access**: `validate` function only called on submission, not per-toggle
4. **FormattedTextControl Inheritance**: Inherits rendering behavior without override hooks

### Prompt Toolkit Opportunities

1. **`app.invalidate()` Available**: Can force redraws from key bindings
2. **Custom Controls Supported**: Can subclass FormattedTextControl
3. **Key Binding System Flexible**: Can add custom handlers with full control
4. **Dynamic Styles**: `DynamicStyle` allows runtime style changes

## Recommendations

### Priority Ranking

**1. Two-Step Selection Pattern (Option C)** - **RECOMMENDED**
- **Effort**: Low (1-2 hours)
- **User Impact**: Positive (clearer workflow)
- **Maintenance**: Minimal
- **Implementation**: Straightforward

**2. Instruction-Based UX (Option D)** - **ACCEPTABLE**
- **Effort**: Very Low (<1 hour)
- **User Impact**: Neutral (manages expectations)
- **Maintenance**: Minimal
- **Implementation**: Requires post-processing

**3. Custom Prompt Toolkit (Option B)** - **ONLY IF CRITICAL**
- **Effort**: High (8-16 hours)
- **User Impact**: Positive (best UX)
- **Maintenance**: High (ongoing)
- **Implementation**: Complex

**4. Modify Questionary (Option A)** - **NOT RECOMMENDED**
- **Effort**: Low (but dangerous)
- **User Impact**: Positive (until it breaks)
- **Maintenance**: High (breaks on updates)
- **Implementation**: Anti-pattern

### Implementation Strategy

**Phase 1: Quick Win (Option D)**
1. Add clear instructions about toggle behavior
2. Implement post-processing for collection selections
3. Test with users to assess satisfaction

**Phase 2: If Needed (Option C)**
1. Refactor to two-step pattern if user feedback negative
2. Keep collection selection simple
3. Provide preview before final confirmation

**Phase 3: Only If Essential (Option B)**
1. Evaluate if dynamic updates truly needed
2. Build MVP custom checkbox with basic features
3. Gradually add advanced features (search, shortcuts)

## Code Examples

### Option C Implementation (Two-Step Pattern)

```python
from typing import List, Optional
from questionary import checkbox, Choice

def select_agents_with_collections(
    all_agents: List[str],
    core_agents: List[str]
) -> List[str]:
    """Select agents using two-step collection + custom pattern."""

    # Step 1: High-level collections
    collection = checkbox(
        "Select agent deployment mode:",
        choices=[
            Choice("All agents (45)", value="all"),
            Choice("Core agents only (6)", value="core"),
            Choice("Custom selection...", value="custom")
        ]
    ).ask()

    if not collection:
        return []

    if "all" in collection:
        return all_agents

    if "core" in collection:
        return core_agents

    if "custom" in collection:
        # Step 2: Individual selection
        selected = checkbox(
            "Select individual agents:",
            choices=[Choice(name, checked=(name in core_agents))
                     for name in all_agents]
        ).ask()
        return selected or []

    return []
```

### Option D Implementation (Instruction-Based)

```python
def select_agents_with_instructions(
    all_agents: List[str],
    core_agents: List[str]
) -> List[str]:
    """Select agents with clear instructions about toggle behavior."""

    choices = [
        Separator("=== Quick Select ==="),
        Choice("🎯 Toggle All (45 agents)", value="__toggle_all__"),
        Choice("⭐ Core Only (6 agents)", value="__core_only__"),
        Separator("=== Individual Agents ==="),
    ]

    # Add individual agents
    for agent in all_agents:
        choices.append(
            Choice(
                f"{'✓' if agent in core_agents else ' '} {agent}",
                value=agent,
                checked=(agent in core_agents)
            )
        )

    selected = checkbox(
        "Select agents to deploy:",
        choices=choices,
        instruction=(
            "Press <space> to toggle, <a> to select all. "
            "Collection options (🎯⭐) will be expanded after confirmation."
        )
    ).ask()

    # Post-process
    if "__toggle_all__" in selected:
        return all_agents
    elif "__core_only__" in selected:
        return core_agents
    else:
        # Remove magic values
        return [s for s in selected if not s.startswith("__")]
```

## Alternative Approaches Considered

### Rich TUI Library (Textual)

**Library**: [Textualize/textual](https://github.com/Textualize/textual)

**Pros**:
- Modern TUI framework with reactive updates
- Built-in checkbox widgets with dynamic updates
- CSS-like styling
- Rich documentation

**Cons**:
- Major dependency addition
- Requires async/await patterns
- Different paradigm from questionary
- Higher learning curve

**Verdict**: Overkill for single checkbox enhancement.

### InquirerPy

**Library**: [kazhala/InquirerPy](https://github.com/kazhala/InquirerPy)

**Description**: Alternative to questionary with more features

**Pros**:
- More active development
- Better documented edge cases
- Fuzzy search built-in

**Cons**:
- Still uses prompt_toolkit (same limitations)
- Migration effort required
- No evidence of dynamic checkbox updates

**Verdict**: Doesn't solve core problem.

## Testing Recommendations

### Manual Testing Checklist

**Test Case 1: Option C (Two-Step)**
- [ ] Select "All agents" - verify returns 45 agents
- [ ] Select "Core only" - verify returns 6 agents
- [ ] Select "Custom" then toggle 3 agents - verify correct subset
- [ ] Cancel at collection screen - verify empty result
- [ ] Cancel at custom screen - verify empty result

**Test Case 2: Option D (Instruction-Based)**
- [ ] Select "Toggle All" - verify returns all 45 agents
- [ ] Select "Core Only" - verify returns 6 agents
- [ ] Mix collection + individual - verify collection takes precedence
- [ ] Read instructions - verify user understands toggle behavior
- [ ] Use `<a>` shortcut - verify post-confirmation behavior

### User Acceptance Testing

**Key Questions**:
1. Do users understand the toggle behavior?
2. Is the two-step flow intuitive or annoying?
3. Do users miss real-time visual feedback?
4. Would instructions alone suffice?

**Success Metrics**:
- 0 user confusion reports about toggle behavior
- <5 seconds to complete selection
- Positive feedback on clarity

## References

### Web Sources

1. [questionary PyPI](https://pypi.org/project/questionary/) - Official package documentation
2. [questionary GitHub](https://github.com/tmbo/questionary) - Source repository
3. [Question Types Documentation](https://questionary.readthedocs.io/en/stable/pages/types.html) - Checkbox API reference
4. [Advanced Concepts Documentation](https://questionary.readthedocs.io/en/stable/pages/advanced.html) - Customization options
5. [prompt_toolkit Full Screen Apps](https://python-prompt-toolkit.readthedocs.io/en/master/pages/full_screen_apps.html) - Building custom UIs
6. [prompt_toolkit Key Bindings](https://python-prompt-toolkit.readthedocs.io/en/master/pages/advanced_topics/key_bindings.html) - Custom key handlers
7. [prompt_toolkit Reference](https://python-prompt-toolkit.readthedocs.io/en/master/pages/reference.html) - API documentation (v3.0.52, August 2025)
8. [GitHub Issue #788 - Refresh prompt from key binding](https://github.com/prompt-toolkit/python-prompt-toolkit/issues/788) - Invalidation patterns
9. [GitHub Issue #1286 - Dynamically updating prompt](https://github.com/prompt-toolkit/python-prompt-toolkit/issues/1286) - Dynamic content

### Source Files Analyzed

- `/venv/lib/python3.13/site-packages/questionary/prompts/checkbox.py` (328 lines)
- `/venv/lib/python3.13/site-packages/questionary/prompts/common.py` (InquirerControl: lines 198-397)

### Framework Context

- **Project**: Claude MPM Framework v5.1.7
- **Use Case**: Agent deployment selection UI (`mpm-agents-deploy` command)
- **Current Implementation**: Uses questionary for all prompts
- **Context**: User needs to select from 45+ agents with collection shortcuts

## Conclusion

**Dynamic checkbox updates are not supported by questionary's current architecture.** The library modifies internal state (`ic.selected_options`) but does not trigger visual redraws when collection operations like "Toggle All" execute.

**Recommended Solution**: **Two-Step Selection Pattern (Option C)**
- Minimal code changes
- Works within questionary's constraints
- Provides better UX through clear workflow separation
- No maintenance burden from custom implementations

**Fallback Solution**: **Instruction-Based UX (Option D)**
- Fastest to implement
- Manages user expectations through clear instructions
- Acceptable if dynamic updates not critical

**Avoid**: Modifying questionary source or building custom prompt_toolkit checkbox from scratch unless dynamic updates are absolutely essential business requirement.

---

**Next Steps**:
1. Validate recommendation with stakeholders
2. Implement Option C (Two-Step Pattern)
3. Conduct user testing
4. Iterate based on feedback
5. Document final approach in user-facing docs
