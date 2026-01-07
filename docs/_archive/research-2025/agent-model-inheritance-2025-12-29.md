# Agent Model Inheritance Analysis

**Date**: 2025-12-29
**Author**: Research Agent
**Context**: Remove hardcoded model specifications from agents to let Claude Code choose the best model dynamically

## Executive Summary

All agents currently hardcode the `model` field in their frontmatter (86 with "sonnet", 4 with "sonnet|opus|haiku"). The system does NOT currently support model inheritance. Removing hardcoded models would require Claude Code to provide a default model when the field is missing.

## Current State Analysis

### Model Field Usage

**Agents Analyzed**: 88 total agents with model specifications
- **86 agents**: Use `model: sonnet` (fixed to Sonnet 4.5)
- **4 agents**: Use `model: sonnet|opus|haiku` (multi-model support)

**Example from `/Users/masa/.claude-mpm/cache/agents/engineer/core/engineer.md`:**
```yaml
model: sonnet
resource_tier: intensive
```

**Example from `/Users/masa/.claude-mpm/cache/agents/documentation/documentation.md`:**
```yaml
model: sonnet
resource_tier: lightweight
```

### Model Field Definition

**Schema Location**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/schemas/agent_schema.json`

**Current Schema (Lines 192-200)**:
```json
"model": {
  "type": "string",
  "enum": [
    "opus",
    "sonnet",
    "haiku"
  ],
  "description": "Claude model tier to use for this agent. Choose based on task complexity and performance requirements: opus (most capable), sonnet (balanced), haiku (fastest)."
}
```

**Key Finding**: Model field is defined under `capabilities.model` and is **required** in the schema (`required: ["model", "resource_tier"]`).

### Base Agent Template

**Location**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/base_agent.json`

**Current Configuration (Lines 8-19)**:
```json
"configuration_fields": {
  "model": "sonnet",
  "file_access": "project",
  "dangerous_tools": false,
  "review_required": false,
  "team": "mpm-framework",
  "project": "claude-mpm",
  "priority": "high",
  "timeout": 300,
  "memory_limit": 1024,
  "context_isolation": "moderate",
  "preserve_context": true
}
```

**Key Finding**: Base agent hardcodes `model: sonnet` as default.

### Agent Definition Model

**Location**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/models/agent_definition.py`

**Current Implementation (Lines 99-100)**:
```python
class AgentMetadata:
    type: AgentType
    model_preference: str = "claude-3-sonnet"
    version: str = "1.0.0"
    # ...
```

**Key Finding**: The Python model uses `model_preference` (not `model`) with default value `"claude-3-sonnet"`.

## How Model Selection Works

### Current Workflow

1. **Agent Definition**: Each agent specifies `model: sonnet|opus|haiku` in frontmatter
2. **Agent Loading**: AgentLoader reads YAML frontmatter and extracts model field
3. **Model Mapping**: Schema definitions map full model names to tiers:
   - `claude-3-5-sonnet-20241022` → `sonnet`
   - `claude-4-opus-20250514` → `opus`
   - `claude-3-haiku-20240307` → `haiku`
4. **Task Tool**: When PM delegates to agent via Task tool, model preference is passed
5. **Claude Code Execution**: Task tool uses agent's model preference for execution

### Model Inheritance Behavior

**CRITICAL FINDING**: The system does NOT support model inheritance currently.

**Evidence**:
- Schema requires `model` field (line 188: `required: ["model", "resource_tier"]`)
- No "inherit" or "auto" option in model enum
- No fallback logic in agent loader for missing model field
- Base agent specifies explicit model value

**What happens if model field is removed?**
- Agent validation would FAIL (schema violation)
- Agent deployment would be blocked
- System would not use parent/default model automatically

## Options Analysis

### Option 1: Remove Model Field Entirely ❌

**Approach**: Delete `model` field from all agents

**Pros**:
- Forces Claude Code to choose model dynamically
- Reduces agent configuration complexity
- Aligns with user's stated goal

**Cons**:
- **BREAKS schema validation** (model is required field)
- Requires schema changes to make model optional
- Requires AgentLoader changes to handle missing model
- Requires default model fallback logic
- **High risk**: Could break existing agent loading

**Recommendation**: **NOT RECOMMENDED** - Too risky without schema changes first

### Option 2: Change Model to "auto" or "inherit" ❌

**Approach**: Set `model: auto` or `model: inherit` in all agents

**Pros**:
- Signals intent to let Claude Code choose
- Explicit opt-in to dynamic model selection
- Easy to identify agents using dynamic models

**Cons**:
- **BREAKS schema validation** ("auto"/"inherit" not in enum)
- Requires schema changes to add new enum values
- Requires AgentLoader logic to interpret "auto"/"inherit"
- Requires fallback model selection logic
- **Medium risk**: Schema change needed

**Recommendation**: **NOT RECOMMENDED** - Requires schema changes

### Option 3: Make Model Field Optional in Schema ✅

**Approach**: Update schema to make model optional, provide default

**Implementation**:
1. **Schema Change** (`agent_schema.json`):
   ```json
   "capabilities": {
     "type": "object",
     "required": ["resource_tier"],  // Remove "model" from required
     "properties": {
       "model": {
         "type": "string",
         "enum": ["opus", "sonnet", "haiku"],
         "default": "sonnet",
         "description": "Claude model tier (optional - defaults to sonnet if not specified)"
       }
     }
   }
   ```

2. **Agent Changes**: Remove `model` field from agent frontmatter
   - Let schema default kick in (`"sonnet"`)
   - Or let Claude Code Task tool choose based on task complexity

3. **AgentLoader Changes**: Handle missing model gracefully
   ```python
   model = frontmatter.get("model", "sonnet")  # Default to sonnet
   ```

**Pros**:
- **Backward compatible**: Existing agents with model field continue working
- **Forward compatible**: New agents can omit model field
- **Low risk**: Gradual migration possible
- Aligns with user's goal of dynamic model selection
- Schema validation still works

**Cons**:
- Requires schema update
- Requires AgentLoader update
- Migration path needed for existing agents

**Recommendation**: ✅ **RECOMMENDED** - Safe, backward compatible approach

### Option 4: Keep Model Field but Document as Optional 🔶

**Approach**: Update documentation to indicate model is optional/can be omitted

**Pros**:
- No code changes needed
- No schema changes needed
- Zero risk

**Cons**:
- **Does not solve the problem** - agents still hardcode model
- Schema still requires model field
- Does not enable dynamic model selection

**Recommendation**: 🔶 **FALLBACK OPTION** - Only if schema changes are blocked

## Recommended Implementation Plan

### Phase 1: Schema and Code Updates ✅

**Files to Modify**:

1. **`src/claude_mpm/schemas/agent_schema.json`**
   - Remove `"model"` from `capabilities.required` array (line 188)
   - Add `"default": "sonnet"` to `capabilities.properties.model` (line 192)

2. **`src/claude_mpm/agents/agent_loader.py`** (or relevant loader)
   - Add default fallback: `model = frontmatter.get("model", "sonnet")`
   - Ensure missing model field doesn't cause validation errors

3. **`src/claude_mpm/models/agent_definition.py`**
   - Verify `model_preference` has default value (already has `"claude-3-sonnet"`)

**Testing**:
- Create test agent without model field
- Verify agent loads successfully
- Verify default model is used
- Verify existing agents with model field still work

### Phase 2: Agent Migration (Optional) 🔄

**Approach**: Gradual migration, not forced

**Option A - Remove Model from All Agents**:
```bash
# Find all agents with model field
find ~/.claude-mpm/cache/agents/ -name "*.md" -type f -exec grep -l "^model:" {} \;

# Remove model field (automated script)
for file in $(find ~/.claude-mpm/cache/agents/ -name "*.md"); do
  sed -i '' '/^model:/d' "$file"
done
```

**Option B - Leave Existing Agents Unchanged**:
- Keep existing agents with `model: sonnet`
- Document that new agents can omit model field
- Let Claude Code choose model dynamically for new agents

**Recommendation**: **Option B** - Leave existing agents unchanged, let new agents omit model

### Phase 3: Documentation Updates 📝

**Files to Update**:

1. **Agent Schema Documentation** (`docs/developer/10-schemas/agent_schema_documentation.md`):
   ```markdown
   ### Model Field (Optional)

   The `model` field specifies which Claude model tier to use for this agent.

   **Default**: `sonnet` (if not specified)

   **Options**:
   - `opus`: Most capable, for complex reasoning and long tasks
   - `sonnet`: Balanced performance and cost (default)
   - `haiku`: Fastest, for simple tasks

   **Note**: If omitted, the system defaults to `sonnet`. In future versions,
   Claude Code may choose the optimal model based on task complexity.
   ```

2. **Agent Development Guide** (`docs/guides/agent-development.md`):
   - Add section on model field being optional
   - Explain when to specify model vs. letting system choose

## Impact Analysis

### Breaking Changes: ❌ NONE

**Backward Compatibility**:
- Existing agents with `model: sonnet` continue working
- No agent files require modification
- Schema validation continues to work

### Required Changes: ✅ LOW RISK

**Code Changes**:
- Schema: 2 lines (remove from required, add default)
- AgentLoader: 1 line (add default fallback)
- Documentation: 2 files

**Testing Requirements**:
- Test agent loading with missing model field
- Test agent loading with existing model field
- Verify default model is applied correctly

### User Impact: ✅ POSITIVE

**Benefits**:
- Agents can now omit model field
- Simpler agent configuration
- Future: Claude Code can choose optimal model dynamically
- Aligns with user's stated goal

## Example Agent Before/After

### Before (Current)

```yaml
---
name: Engineer
description: Clean architecture specialist
version: 3.9.1
agent_type: engineer
model: sonnet                    # ← Hardcoded
resource_tier: intensive
tags:
- engineering
---
```

### After (With Optional Model)

```yaml
---
name: Engineer
description: Clean architecture specialist
version: 3.9.1
agent_type: engineer
# model field removed - defaults to sonnet
resource_tier: intensive
tags:
- engineering
---
```

**Result**: Same behavior, less configuration

## Implementation Checklist

- [ ] **Schema Update**: Make model field optional in `agent_schema.json`
- [ ] **AgentLoader Update**: Add default fallback for missing model field
- [ ] **Testing**: Verify agents load with/without model field
- [ ] **Documentation**: Update schema docs and agent development guide
- [ ] **Optional**: Remove model field from base_agent.json
- [ ] **Optional**: Remove model field from existing agents (can defer)
- [ ] **Validation**: Run agent validation tests
- [ ] **Deployment**: Deploy updated schema and loader

## Conclusion

**Recommended Approach**: Make model field optional in schema (Option 3)

**Key Benefits**:
- Backward compatible (existing agents work unchanged)
- Forward compatible (new agents can omit model)
- Low risk implementation (2 files, 3 lines changed)
- Aligns with user goal of removing hardcoded models
- Future-proof for Claude Code dynamic model selection

**Next Steps**:
1. Update schema to make model optional with default value
2. Update AgentLoader to handle missing model field
3. Test with agents that have/don't have model field
4. Document the change in agent development guides
5. Optionally remove model from base_agent.json template
6. Optionally migrate existing agents (can defer)

**Timeline Estimate**:
- Schema + Code Changes: 30 minutes
- Testing: 1 hour
- Documentation: 1 hour
- **Total**: ~2.5 hours

**Risk Level**: 🟢 LOW (backward compatible, minimal changes)
