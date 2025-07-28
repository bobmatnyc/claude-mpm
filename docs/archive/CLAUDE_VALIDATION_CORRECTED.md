# Agent Template Validation Rules - Corrected Version

Based on the actual claude-mpm implementation, here are the correct validation rules:

## Current Agent Template Structure

### VALIDATION: Every agent template MUST have:
- [ ] **agent_type** field (not agent_id - the ID is derived from filename)
- [ ] **version** field (currently all use version 5)
- [ ] **narrative_fields** object containing:
  - [ ] `when_to_use` array
  - [ ] `specialized_knowledge` array  
  - [ ] `unique_capabilities` array
  - [ ] `instructions` string (the main prompt)
- [ ] **configuration_fields** object containing:
  - [ ] `model` (e.g., "claude-4-sonnet-20250514")
  - [ ] `description` (37-65 chars in current templates)
  - [ ] `tools` array (5-9 tools per agent)
  - [ ] Additional configuration like temperature, timeout, etc.

### Current Implementation Facts:
1. **No agent_id field** - IDs are derived from JSON filenames
2. **AgentValidator checks**: `name`, `role`, `prompt_template` (different from templates)
3. **Description length**: Current templates use 37-65 characters (within suggested 10-100 range)
4. **Tools requirement**: All templates have 5-9 tools ✅
5. **Prompt location**: In `narrative_fields.instructions` (not `prompt_template`)

### Example Valid Agent Template Structure:
```json
{
  "version": 5,
  "agent_type": "engineer",
  "narrative_fields": {
    "when_to_use": ["Implementation tasks", "Bug fixes"],
    "specialized_knowledge": ["Design patterns", "Best practices"],
    "unique_capabilities": ["Code generation", "Refactoring"],
    "instructions": "# Engineer Agent\n\nYour detailed prompt here..."
  },
  "configuration_fields": {
    "model": "claude-4-sonnet-20250514",
    "description": "Research-guided code implementation agent",
    "tags": ["engineering", "implementation"],
    "tools": ["Read", "Write", "Edit", "Bash", "Grep"],
    "temperature": 0.05,
    "timeout": 1200
  }
}
```

### Validation Rules for New Agents:

1. **Filename Convention**: 
   - Format: `{agent_type}_agent.json`
   - Example: `security_agent.json`, `qa_agent.json`

2. **Required Fields Validation**:
   ```python
   # Pseudo-validation
   assert 'agent_type' in template
   assert 'version' in template and template['version'] == 5
   assert 'narrative_fields' in template
   assert 'configuration_fields' in template
   assert len(template['configuration_fields']['tools']) >= 1
   ```

3. **Description Length**:
   - Minimum: 10 characters
   - Maximum: 100 characters
   - Current range: 37-65 characters

4. **Tools Array**:
   - Minimum: 1 tool required
   - Current templates: 5-9 tools
   - Must be valid tool names from the system

### Existing Validation Logic:

The `AgentValidator` class currently validates:
- `name` - Required field
- `role` - Required field  
- `prompt_template` - Required field

Note: This doesn't match the actual template structure, suggesting validation may need updating.

### Recommendations:

1. **Update validation to match templates**:
   - Validate `agent_type` instead of `name`
   - Validate `narrative_fields.instructions` instead of `prompt_template`
   - Validate `configuration_fields.description` for length

2. **Add unique agent_type validation**:
   - Ensure no duplicate agent_type values
   - Validate against existing templates

3. **Standardize the approach**:
   - Either add `agent_id` to templates
   - Or document that IDs come from filenames
   - Update validator to match actual structure