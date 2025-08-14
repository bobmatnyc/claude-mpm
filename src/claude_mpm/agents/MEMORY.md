## Static Memory Management Protocol

### Overview

This system provides **Static Memory** support where you (PM) directly manage memory files for agents. This is the first phase of memory implementation, with **Dynamic mem0AI Memory** coming in future releases.

### PM Memory Update Mechanism

**As PM, you handle memory updates directly by:**

1. **Reading** existing memory files from `.claude-mpm/memories/`
2. **Consolidating** new information with existing knowledge
3. **Saving** updated memory files with enhanced content
4. **Maintaining** 20k token limit (~80KB) per file

### Memory File Format

- **Project Memory Location**: `.claude-mpm/memories/`
  - **PM Memory**: `.claude-mpm/memories/PM.md` (Project Manager's memory)
  - **Agent Memories**: `.claude-mpm/memories/{agent_name}.md` (e.g., engineer.md, qa.md, research.md)
- **Size Limit**: 80KB (~20k tokens) per file
- **Format**: Single-line facts and behaviors in markdown sections
- **Sections**: Project Architecture, Implementation Guidelines, Common Mistakes, etc.
- **Naming**: Use exact agent names (engineer, qa, research, security, etc.) matching agent definitions

### Memory Update Process (PM Instructions)

**When memory indicators detected**:
1. **Identify** which agent should store this knowledge
2. **Read** current memory file: `.claude-mpm/memories/{agent_id}_agent.md`
3. **Consolidate** new information with existing content
4. **Write** updated memory file maintaining structure and limits
5. **Confirm** to user: "Updated {agent} memory with: [brief summary]"

**Memory Trigger Words/Phrases**:
- "remember", "don't forget", "keep in mind", "note that"
- "make sure to", "always", "never", "important" 
- "going forward", "in the future", "from now on"
- "this pattern", "this approach", "this way"
- Project-specific standards or requirements

**Storage Guidelines**:
- Keep facts concise (single-line entries)
- Organize by appropriate sections
- Remove outdated information when adding new
- Maintain readability and structure
- Respect 80KB file size limit

### Agent Memory Routing Matrix

**Engineering Agent Memory**:
- Implementation patterns and anti-patterns
- Code architecture and design decisions
- Performance optimizations and bottlenecks
- Technology stack choices and constraints

**Research Agent Memory**:
- Analysis findings and investigation results
- Domain knowledge and business logic
- Architectural decisions and trade-offs
- Codebase patterns and conventions

**QA Agent Memory**:
- Testing strategies and coverage requirements
- Quality standards and acceptance criteria
- Bug patterns and regression risks
- Test infrastructure and tooling

**Security Agent Memory**:
- Security patterns and vulnerabilities
- Threat models and attack vectors
- Compliance requirements and policies
- Authentication/authorization patterns

**Documentation Agent Memory**:
- Writing standards and style guides
- Content organization patterns
- API documentation conventions
- User guide templates

**Data Engineer Agent Memory**:
- Data pipeline patterns and ETL strategies
- Schema designs and migrations
- Performance tuning techniques
- Data quality requirements

**Ops Agent Memory**:
- Deployment patterns and rollback procedures
- Infrastructure configurations
- Monitoring and alerting strategies
- CI/CD pipeline requirements

**Version Control Agent Memory**:
- Branching strategies and conventions
- Commit message standards
- Code review processes
- Release management patterns