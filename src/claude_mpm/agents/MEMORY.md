## Memory Management Protocol (TBD)

### Memory Evaluation (MANDATORY for ALL user prompts)

**Memory Trigger Words/Phrases**:
- "remember", "don't forget", "keep in mind", "note that"
- "make sure to", "always", "never", "important"
- "going forward", "in the future", "from now on"
- "this pattern", "this approach", "this way"
- Project-specific standards or requirements

**When Memory Indicators Detected**:
1. **Extract Key Information**: Identify facts, patterns, or guidelines to preserve
2. **Determine Agent & Type**:
   - Code patterns/standards → Engineer Agent (type: pattern)
   - Architecture decisions → Research Agent (type: architecture)
   - Testing requirements → QA Agent (type: guideline)
   - Security policies → Security Agent (type: guideline)
   - Documentation standards → Documentation Agent (type: guideline)
   - Deployment patterns → Ops Agent (type: strategy)
   - Data schemas → Data Engineer Agent (type: architecture)
3. **Delegate Storage**: Use memory task format with appropriate agent
4. **Confirm to User**: "Storing this information: [brief summary] for [agent]"

### Memory Storage Task Format

```
Task: Store project-specific memory
Agent: <appropriate agent based on content>
Context:
  Goal: Preserve important project knowledge for future reference
  Memory Request: <user's original request>
  Suggested Format:
    # Add To Memory:
    Type: <pattern|architecture|guideline|mistake|strategy|integration|performance|context>
    Content: <concise summary under 100 chars>
    #
```

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