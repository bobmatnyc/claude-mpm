# Clarification Needed: Dynamic Domain Authority Instructions

**Date:** 2025-11-30
**Context:** BASE-AGENT.md optional implementation verification
**Status:** ⏳ Awaiting user clarification

---

## Background

While verifying the BASE-AGENT.md optional implementation (✅ COMPLETE), you mentioned:

> **"Dynamic domain authority instructions should be pulled from .claude/agents AFTER deployment"**

We need clarification on this requirement before implementing.

---

## Questions for User

### 1. What is "Dynamic Domain Authority"?

Please choose the closest match or describe your vision:

**A. Agent Capability Indexing**
- Extract agent specializations from deployed markdown files
- Build searchable index of agent expertise
- Use for intelligent agent routing/selection
- Example: Index shows "fastapi-engineer" has expertise in ["async", "REST API", "Python", "Pydantic"]

**B. Runtime Instruction Loading**
- Read deployed agent instructions during execution
- Apply domain-specific rules at runtime
- Enable hot-reloading of agent behavior
- Example: PM reads agent capabilities from `~/.claude/agents/` to route tasks

**C. Post-Deployment Analysis**
- Analyze deployed agents for patterns
- Generate metadata about agent capabilities
- Create discovery/search index
- Example: `claude-mpm agents capabilities` shows all agent skills

**D. Something else?**
- Please describe your vision

---

### 2. When Should This Happen?

Please choose timing preference:

- [ ] **Immediately after each agent deployment**
  - Pros: Always up-to-date
  - Cons: Deployment overhead

- [ ] **During CLI startup (lazy loading)**
  - Pros: Zero deployment impact
  - Cons: Startup delay

- [ ] **When agent is first invoked**
  - Pros: On-demand, no waste
  - Cons: First-use latency

- [ ] **On-demand via CLI command**
  - Example: `claude-mpm agents index`
  - Pros: User control
  - Cons: Manual step

- [ ] **Periodic background task**
  - Example: Every hour or on file changes
  - Pros: Fresh without blocking
  - Cons: Complexity

- [ ] **Other:** _______________

---

### 3. What Should Be Done With The Instructions?

Please select all that apply:

- [ ] **Store in SQLite index for fast lookups**
- [ ] **Generate agent capability manifest (JSON)**
- [ ] **Enable semantic search across agents**
- [ ] **Power agent auto-selection during delegation**
- [ ] **Display in `claude-mpm agents list --detailed`**
- [ ] **Feed into PM routing logic**
- [ ] **Provide API for external tools**
- [ ] **Other:** _______________

---

### 4. What Information Should Be Extracted?

Please select all that apply:

- [ ] **Agent specialization keywords** (e.g., "FastAPI", "async", "REST")
- [ ] **Domain expertise markers** (e.g., "security", "performance")
- [ ] **Skill level indicators** (e.g., "expert", "intermediate")
- [ ] **Example use cases** from agent descriptions
- [ ] **Technology stack proficiency** (e.g., "Python 3.12", "TypeScript")
- [ ] **Anti-patterns** (what NOT to use agent for)
- [ ] **Agent relationships** (similar agents, alternatives)
- [ ] **Other:** _______________

---

### 5. Deployment Location Questions

**You mentioned `.claude/agents`** - please clarify:

- Did you mean `~/.claude/agents/` (user tier deployed agents)?
- Should we also scan `.claude-mpm/agents/` (project tier)?
- What about system agents in package installation?
- Should there be a merge/precedence rule?

**Scanning Scope:**
- [ ] Only `~/.claude/agents/` (user tier)
- [ ] Only `.claude-mpm/agents/` (project tier)
- [ ] Both with precedence (which wins?)
- [ ] All tiers including system agents
- [ ] Other: _______________

---

### 6. Integration Points

**Where does this fit in the system?**

- [ ] **Part of agent deployment service**
  - Integrated into existing `AgentDeploymentService`

- [ ] **New service: `AgentCapabilityIndexer`**
  - Standalone service called after deployment

- [ ] **Extension to agent discovery**
  - Enhance existing discovery to include capabilities

- [ ] **PM delegation logic enhancement**
  - PM uses this to route tasks to appropriate agents

- [ ] **Standalone CLI command**
  - Example: `claude-mpm agents capabilities`

- [ ] **Other:** _______________

---

## Use Case Examples (Help Us Understand)

Please provide 2-3 examples of how you envision using this feature:

### Example 1: [Your scenario]
**User Action:**
[What does the user do?]

**System Behavior:**
[What should the system do?]

**End Result:**
[What value does user get?]

---

### Example 2: [Your scenario]
**User Action:**
[What does the user do?]

**System Behavior:**
[What should the system do?]

**End Result:**
[What value does user get?]

---

### Example 3: [Your scenario]
**User Action:**
[What does the user do?]

**System Behavior:**
[What should the system do?]

**End Result:**
[What value does user get?]

---

## Proposed Implementation (After Clarification)

Once we understand your requirements, we can implement:

### Option A: Agent Capability Indexer

```python
class AgentCapabilityIndexer:
    """Extract and index agent capabilities from deployed markdown files."""

    def scan_deployed_agents(self, tier: str = "all") -> Dict[str, AgentCapability]:
        """Scan deployed agents and extract domain expertise."""
        pass

    def extract_capabilities(self, agent_markdown: str) -> AgentCapability:
        """Parse agent markdown to identify specializations."""
        pass

    def build_searchable_index(self, capabilities: Dict) -> None:
        """Create fast lookup index for agent routing."""
        pass

    def find_agents_by_capability(self, capability: str) -> List[str]:
        """Find all agents with specific capability."""
        pass
```

**Usage:**
```bash
# Index all deployed agents
claude-mpm agents index

# Search by capability
claude-mpm agents find --capability "async-api"

# Show agent capabilities
claude-mpm agents capabilities fastapi-engineer
```

---

### Option B: Runtime Instruction Loader

```python
class DynamicInstructionLoader:
    """Load and apply agent instructions at runtime."""

    def load_deployed_instructions(self, agent_name: str) -> str:
        """Read instructions from ~/.claude/agents/"""
        pass

    def merge_with_base_instructions(self, agent_instructions: str) -> str:
        """Combine with BASE-AGENT.md from deployed location."""
        pass

    def refresh_agent_cache(self) -> None:
        """Reload all agent instructions."""
        pass
```

**Usage:**
```python
# In PM delegation logic
loader = DynamicInstructionLoader()
agent_instructions = loader.load_deployed_instructions("fastapi-engineer")
# Route task based on current agent capabilities
```

---

### Option C: Capability Discovery Service

```python
class AgentCapabilityDiscovery:
    """Discover and manage agent capabilities."""

    def discover_all_capabilities(self) -> CapabilityIndex:
        """Build comprehensive capability index."""
        pass

    def suggest_agents_for_task(self, task_description: str) -> List[AgentMatch]:
        """Suggest best agents for a given task."""
        pass

    def get_agent_specializations(self, agent_name: str) -> List[str]:
        """Get list of agent specializations."""
        pass
```

**Usage:**
```bash
# Get agent suggestions
claude-mpm agents suggest "implement async REST API"
# Returns: [fastapi-engineer (95%), python-engineer (80%), ...]

# Show all capabilities
claude-mpm agents capabilities --all
```

---

## Questions Summary (For Quick Reference)

1. **What is dynamic domain authority?** [A/B/C/D/describe]
2. **When should it run?** [immediate/startup/on-demand/periodic/other]
3. **What to do with data?** [index/search/route/display/other]
4. **What to extract?** [keywords/expertise/use-cases/tech-stack/other]
5. **Where to scan?** [user/project/all-tiers/other]
6. **How to integrate?** [deployment/standalone/discovery/PM/other]
7. **Use case examples?** [provide 2-3 scenarios]

---

## Next Steps

**Once you provide clarification:**

1. ✅ Design system architecture
2. ✅ Create implementation plan
3. ✅ Write comprehensive tests
4. ✅ Implement feature
5. ✅ Update documentation
6. ✅ Verify integration with existing systems

**Estimated effort** (after clarification):
- Simple capability extraction: 4-6 hours
- Full indexing system: 8-12 hours
- Advanced semantic search: 16-24 hours

---

## Contact

Please provide clarification via:
- Reply in this session
- Update this document with answers
- Schedule discussion if complex

**We're ready to implement as soon as we understand your vision!**

---

**Status:** ⏳ Awaiting user response
**Blocking:** Dynamic domain authority implementation
**Non-blocking:** BASE-AGENT.md optional behavior (✅ COMPLETE)
