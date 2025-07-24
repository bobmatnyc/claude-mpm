# Agent Delegation Templates

This directory contains standardized delegation templates for the 9 core agents in the Claude PM framework.

## Core Agents

1. **Documentation Agent** (`documentation_agent.md`)
   - Nickname: Documenter
   - Handles all documentation operations and changelog generation

2. **Version Control Agent** (`version_control_agent.md`)
   - Nickname: Versioner
   - Handles Git operations and version management

3. **QA Agent** (`qa_agent.md`)
   - Nickname: QA
   - Manages testing, validation, and quality assurance

4. **Research Agent** (`research_agent.md`)
   - Nickname: Researcher
   - Conducts investigation, analysis, and information gathering

5. **Ops Agent** (`ops_agent.md`)
   - Nickname: Ops
   - Manages deployment, operations, and infrastructure

6. **Security Agent** (`security_agent.md`)
   - Nickname: Security
   - Handles security analysis and vulnerability assessment

7. **Engineer Agent** (`engineer_agent.md`)
   - Nickname: Engineer
   - Responsible for code implementation and inline documentation

8. **Data Engineer Agent** (`data_engineer_agent.md`)
   - Nickname: Data Engineer
   - Manages data stores and AI API integrations

9. **PM Orchestrator Agent** (See `framework/agent-roles/pm-orchestrator-agent.md`)
   - Nickname: PM
   - Multi-agent orchestration and coordination
   - Manages all ticket operations via aitrackdown CLI

## Note on Ticketing

The `ticketing_agent.md` template is deprecated. All ticket operations are now handled exclusively by the PM Orchestrator Agent using the aitrackdown CLI. Agents report progress to PM who manages all ticket lifecycle operations

## Template Structure

Each agent template contains:

1. **Agent Overview**: Basic information about the agent
2. **Delegation Template**: Standard format for delegating tasks
3. **Example Usage**: Real-world examples of task delegation
4. **Integration Points**: How the agent works with other agents
5. **Progress Reporting Format**: Standard format for agent reports
6. **Error Handling**: Common issues and responses

## Using the Templates

When delegating tasks to agents via the Task Tool, use these templates to ensure:

- Consistent communication format
- Clear task specifications
- Proper temporal context
- Ticket reference tracking
- Expected deliverables
- Progress reporting requirements

## Template Variables

Replace these placeholders when using templates:

- `[date]`: Current date for temporal context
- `[task description]`: Specific task details
- `[ISS-XXXX]`: Ticket reference number (if applicable)
- `[specific details]`: Task-specific requirements

## Integration with PM Workflow

1. PM identifies task requiring agent delegation
2. PM selects appropriate agent and template
3. PM customizes template with specific details
4. PM creates Task Tool subprocess with formatted delegation
5. Agent executes task and reports progress
6. PM updates TodoWrite entries based on agent reports

## Maintenance

These templates should be updated when:
- Agent capabilities change
- New integration points are added
- Reporting formats are enhanced
- New error scenarios are discovered