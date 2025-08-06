# Agent Memory System Documentation

The Agent Memory System in Claude MPM enables agents to learn and apply knowledge over time, creating persistent learnings that improve agent effectiveness across sessions.

Last Updated: 2025-08-06

## Overview

### What is the Memory System?

The memory system allows agents to accumulate project-specific knowledge, patterns, and learnings in persistent memory files. When agents encounter situations they've learned from before, they can apply that knowledge to make better decisions and provide more contextually relevant assistance.

### Why is it Important?

- **Continuity**: Agents remember insights across sessions, building expertise over time
- **Context-Awareness**: Agents learn project-specific patterns, conventions, and requirements
- **Efficiency**: Reduces repetitive explanations and accelerates problem-solving
- **Quality**: Agents learn from mistakes and successful patterns to improve output quality

### How Agents Learn

Agents accumulate knowledge through:
1. **Explicit Memory Commands**: Users say "remember this" or "add to memory"
2. **Auto-Learning**: Automatic extraction from agent outputs (when enabled)
3. **Project-Specific Memory Generation**: Automated analysis of project characteristics and context
4. **Documentation Building**: Enhanced extraction from dynamically discovered documentation
5. **Hook-Based Integration**: Real-time memory injection and learning extraction via hooks
6. **Manual Addition**: Direct memory file editing or CLI commands

### Benefits

**For Users:**
- Agents provide more relevant, project-specific assistance
- Reduced need to repeat context or preferences
- Faster problem resolution based on learned patterns

**For Developers:**
- Agents learn coding patterns and architectural decisions
- Reduced debugging time through learned common mistakes
- Better adherence to project conventions and standards

## Core Features

### Project-Specific Memory Generation

The memory system now automatically analyzes your project to create context-aware memories tailored to your specific codebase, technology stack, and architecture patterns.

**Key Capabilities:**
- **Technology Stack Detection**: Automatically identifies languages, frameworks, and tools from configuration files
- **Architecture Pattern Recognition**: Analyzes directory structure and code patterns to understand project organization
- **Dynamic File Discovery**: Intelligently finds important documentation and configuration files
- **Agent-Specific Customization**: Generates different memory content based on the agent's role and project characteristics

**Example Project Analysis Results:**
```
claude-mpm: python CLI Application
- Main modules: cli, services, core, utils
- Uses: click, pytest, flask
- Testing: pytest fixtures
- Key patterns: Object Oriented, Async Programming
```

**Benefits:**
- **Immediate Context**: New agents start with relevant project knowledge instead of generic templates
- **Consistent Patterns**: All agents understand the same project conventions and architecture
- **Reduced Learning Time**: Agents don't need to rediscover project patterns through trial and error
- **Better Code Quality**: Agents follow established patterns from the start

### Memory Storage

Agents store memories in structured markdown files located in `.claude-mpm/memories/`:

```
.claude-mpm/memories/
├── engineer_agent.md
├── research_agent.md  
├── qa_agent.md
└── documentation_agent.md
```

**Memory Commands Recognized:**
- "remember this for next time"
- "memorize this pattern"
- "add to memory"
- "learn from this mistake"
- "store this insight"

### Show Memories Functionality

View agent memories through:
- **CLI Command**: `claude-mpm memory show [agent_id]`
- **Format Options**: Summary view or full content display
- **Cross-References**: Identify common patterns across agents

### Optimize Memories Capability

Automatic memory maintenance through:
- **Duplicate Removal**: Eliminates redundant entries
- **Consolidation**: Merges similar items for clarity
- **Priority Reordering**: Places important insights first
- **Size Management**: Maintains memory within configured limits

### Enhanced Documentation Processing

Automated knowledge extraction with dynamic discovery:
- **Smart File Discovery**: Automatically finds relevant documentation based on project analysis
- **Configuration Analysis**: Extracts insights from package.json, requirements.txt, and other config files
- **Architecture Documentation**: Processes project-specific structure and pattern documentation
- **Agent-Targeted Content**: Routes documentation insights to the most relevant agents
- **Context-Aware Extraction**: Tailors extracted knowledge to the specific project characteristics

**Dynamic File Discovery Examples:**
- Node.js projects: Prioritizes package.json, webpack configs, and TypeScript documentation
- Python projects: Focuses on requirements.txt, setup.py, and pytest configurations
- Multi-language projects: Analyzes all relevant config files and creates comprehensive memories

## Usage Guide

### Adding Memories

**Natural Language (Recommended):**
```
User: "Remember that we use the src/ layout pattern for this project"
Agent: I'll remember that architectural decision for future reference.
```

**CLI Command:**
```bash
# Initialize project-specific memories (best for new projects)
claude-mpm memory init

# Add a specific learning
claude-mpm memory add engineer pattern "Use src/ layout for Python packages"

# Add a mistake to avoid
claude-mpm memory add qa error "Missing test coverage causes deployment failures"
```

**/mpm Slash Command (in interactive mode):**
```bash
# Initialize memories via PM agent
/mpm memory init

# This will trigger the PM agent to analyze your project and create memories
```

**Memory Categories:**
- `pattern`: Architectural or design patterns
- `error`: Common mistakes to avoid
- `optimization`: Performance or efficiency improvements
- `preference`: User or team preferences
- `context`: Current project state or decisions

### Viewing Memories

**Show All Agent Memories (Summary):**
```bash
claude-mpm memory show
```

**Show Specific Agent Memory:**
```bash
# Summary view
claude-mpm memory show engineer

# Full content view
claude-mpm memory show engineer --format full
```

**Memory Status Overview:**
```bash
claude-mpm memory status
```

Example output:
```
Agent Memory System Status
--------------------------------------------------------------------------------
🧠 Memory System Health: ✅ healthy
📁 Memory Directory: /project/.claude-mpm/memories
🔧 System Enabled: Yes
📚 Auto Learning: No
📊 Total Agents: 4

📋 Agent Memory Details:
   🟢 engineer
      Size: 6.2 KB / 8 KB (77.5%)
      Content: 4 sections, 23 items
      Auto-learning: Off
      Last modified: 2025-01-24 10:30:15
```

### Optimizing Memories

**Optimize Specific Agent:**
```bash
claude-mpm memory optimize engineer
```

**Optimize All Agents:**
```bash
claude-mpm memory optimize
```

**Preview Optimization (Analysis Only):**
```bash
claude-mpm memory analyze engineer
```

Optimization performs:
- Removes exact duplicates
- Consolidates similar items (70%+ similarity)
- Reorders by priority keywords
- Maintains structured format

### Building from Documentation

**Build from All Documentation:**
```bash
claude-mpm memory build
```

**Force Rebuild (Ignore Timestamps):**
```bash
claude-mpm memory build --force-rebuild
```

**Enhanced Processing:**
The system now dynamically discovers and processes files based on project analysis:
- **Configuration Files**: package.json, requirements.txt, pyproject.toml, Cargo.toml
- **Project Documentation**: README.md, CONTRIBUTING.md, architecture docs
- **Framework-Specific Docs**: API documentation, testing guides, deployment instructions
- **Code Pattern Analysis**: Extracts conventions from actual source code

### Memory Generation Examples

**Generic Memory (Old Approach):**
```markdown
## Implementation Guidelines
- Follow coding best practices
- Write comprehensive tests
- Use consistent naming conventions
- Document your code properly
```

**Project-Specific Memory (New Approach):**
```markdown
## Implementation Guidelines - React/TypeScript SPA
- Use functional components with hooks (established pattern in src/components/)
- Follow Material-UI design system conventions
- Implement unit tests with Jest and React Testing Library
- Use ESLint/Prettier configuration from .eslintrc.json
- API calls through axios service layer in src/services/
- State management with Redux Toolkit (configured in src/store/)

## Current Technical Context
- Project uses TypeScript strict mode with custom tsconfig.json
- Testing: Jest with coverage reports, Cypress for E2E
- Build: Vite with custom build configurations for staging/production
- Deployment: Docker containerization with multi-stage builds
```

**Agent-Specific Variations:**

*Engineer Agent Memory:*
```markdown
## React Component Patterns
- Use TypeScript interfaces for all props
- Implement custom hooks for complex state logic
- Follow atomic design principles (atoms/molecules/organisms)
- Use React.memo for performance optimization where needed
```

*QA Agent Memory:*
```markdown
## Testing Strategy - React SPA
- Component testing: @testing-library/react with user-event
- API mocking: MSW (Mock Service Worker) for integration tests
- E2E testing: Cypress with custom commands in cypress/support/
- Coverage requirements: 80% minimum, configured in jest.config.js
```

### PM Agent Memory Command Routing

The PM agent automatically routes memory commands to appropriate agents:

**Test Routing Logic:**
```bash
claude-mpm memory route --content "Use pytest for unit testing"
```

Example output:
```
🎯 Routing Decision:
   Target Agent: qa
   Section: Testing Strategies
   Confidence: 0.87
   Reasoning: Strong match for qa agent; matched keywords: pytest, unit, testing
```

## CLI Commands Reference

### memory init
Initializes project-specific memories by delegating to the PM agent:
- Triggers comprehensive project analysis by PM agent
- PM agent scans documentation, source code, and project structure
- Creates custom memories for each agent type based on findings
- Adds discovered patterns using `memory add` commands
- Best used when starting with a new project or after major refactoring

### memory status
Shows comprehensive memory system status including:
- System health and configuration
- Per-agent memory statistics
- Size utilization and optimization opportunities
- Auto-learning status

### memory show [agent_id] [--format]
Displays agent memories in readable format:
- **No agent_id**: Shows all agents with cross-references
- **With agent_id**: Shows specific agent memory
- **--format summary**: Brief overview (default)
- **--format full**: Complete memory content

### memory optimize [agent_id]
Optimizes memory files by removing duplicates and consolidating:
- **No agent_id**: Optimizes all agent memories
- **With agent_id**: Optimizes specific agent only
- Creates backup before optimization
- Reports size reduction and improvements

### memory build [--force-rebuild]
Builds memories from project documentation:
- **--force-rebuild**: Processes all files regardless of timestamps
- Extracts actionable insights and guidelines
- Routes content to appropriate agents
- Updates last-processed timestamps

### memory route --content "text"
Tests memory command routing logic:
- Analyzes content for agent relevance
- Shows routing decision and reasoning
- Displays agent relevance scores
- Useful for debugging and customization

### memory cross-ref [--query]
Finds cross-references and patterns across memories:
- **No query**: Shows common patterns across all agents
- **With query**: Searches for specific content
- Identifies knowledge correlations
- Helps find knowledge gaps

## Supported Agent Types

The memory system supports 10 specialized agent types, each with dedicated keywords and memory sections optimized for their specific roles:

### Core Agents

**1. Engineer Agent (`engineer`)**
- **Focus**: Implementation, coding patterns, architecture, performance optimization
- **Keywords**: implementation, code, function, performance, algorithm, testing, debug, refactor, API, framework
- **Memory Sections**: Coding Patterns Learned, Implementation Guidelines, Performance Considerations, Integration Points

**2. Research Agent (`research`)**
- **Focus**: Analysis, investigation, domain knowledge, security research
- **Keywords**: research, analysis, investigate, findings, documentation, security, compliance, best practices, standards
- **Memory Sections**: Domain-Specific Knowledge, Research Findings, Security Considerations, Compliance Requirements

**3. QA Agent (`qa`)**
- **Focus**: Quality assurance, testing strategies, validation processes
- **Keywords**: test, testing, quality, bug, validation, coverage, automation, metrics, review, audit
- **Memory Sections**: Quality Standards, Testing Strategies, Common Issues Found, Verification Patterns

**4. Documentation Agent (`documentation`)**
- **Focus**: Technical writing, user guides, API documentation
- **Keywords**: document, readme, guide, manual, tutorial, explanation, reference, examples, usage
- **Memory Sections**: Documentation Patterns, User Guide Standards, Content Organization, Writing Guidelines

**5. PM Agent (`pm`)**
- **Focus**: Project management, coordination, planning, stakeholder management
- **Keywords**: project, management, coordination, planning, stakeholder, workflow, agile, scrum, milestone
- **Memory Sections**: Project Coordination, Team Communication, Process Improvements, Risk Management

### Specialized Agents

**6. Security Agent (`security`)**
- **Focus**: Security analysis, authentication, compliance, threat assessment
- **Keywords**: security, authentication, encryption, vulnerability, firewall, privacy, GDPR, access control
- **Memory Sections**: Security Patterns, Threat Analysis, Compliance Requirements, Access Control Patterns

**7. Data Engineer Agent (`data_engineer`)** *(Recently Enhanced)*
- **Focus**: Data pipelines, databases, analytics, AI API integrations
- **Keywords**: data, database, SQL, pipeline, ETL, analytics, warehouse, streaming, MongoDB, PostgreSQL, Redis, AI API, OpenAI, Claude, LLM, embedding, vector database
- **Memory Sections**: Database Architecture Patterns, Pipeline Design Strategies, Data Quality Standards, Performance Optimization Techniques

**8. Test Integration Agent (`test_integration`)** *(Recently Enhanced)*
- **Focus**: Integration testing, E2E workflows, cross-system validation
- **Keywords**: integration, e2e, end-to-end, system test, workflow test, API test, contract test, Selenium, Cypress, Playwright, Postman
- **Memory Sections**: Integration Test Patterns, Cross-System Validation, Test Environment Management, End-to-End Workflow Testing

**9. Ops Agent (`ops`)**
- **Focus**: Infrastructure, deployment, monitoring, scaling
- **Keywords**: deployment, infrastructure, DevOps, Docker, Kubernetes, monitoring, scaling, cloud, AWS, Azure, GCP
- **Memory Sections**: Deployment Strategies, Infrastructure Patterns, Monitoring and Observability, Scaling and Performance

**10. Version Control Agent (`version_control`)**
- **Focus**: Git workflows, branching strategies, release management
- **Keywords**: git, GitHub, branch, merge, commit, pull request, release, version, workflow, GitFlow
- **Memory Sections**: Branching Strategies, Release Management, Version Control Workflows, Collaboration Patterns

## Recent Enhancements

### Enhanced Agent Support (August 2025)
- **Added data_engineer agent**: Specialized support for data pipelines, AI API integrations, and analytics workflows
- **Added test_integration agent**: Focused on integration testing patterns, E2E workflows, and cross-system validation
- **Expanded keyword coverage**: Enhanced multi-word keyword matching for more accurate content routing

### Improved Routing Algorithm
- **Square root normalization**: Prevents agents with extensive keyword lists from being unfairly penalized during routing
- **Multi-word keyword bonuses**: Keywords containing spaces receive a 1.5x score multiplier for better semantic relevance
- **Enhanced confidence scoring**: Improved confidence calculation with 2x scaling factor for more accurate routing decisions
- **Context-aware adjustments**: Task type hints and agent hints now influence routing decisions with score boosts

### Memory System Architecture Improvements
- **Project-specific memory generation**: Analyzes project characteristics to create contextual, relevant memories from the start
- **Dynamic file discovery**: Intelligently discovers important documentation files based on detected project type and stack
- **Agent-specific customization**: Tailors memory content generation to agent roles and identified project characteristics
- **Enhanced routing precision**: Lowered threshold for routing decisions to handle diverse agent patterns more effectively

## Agent Memory Integration

### How Agents Use Memory

1. **Pre-Task Loading**: Agents load their memory before starting tasks
2. **Context Integration**: Memory content is integrated into agent prompts
3. **Decision Making**: Agents reference learned patterns and guidelines
4. **Post-Task Learning**: New insights are extracted and stored

### Real-Time Memory Updates

The memory system supports dynamic, real-time updates through multiple mechanisms:

**Hook-Based Memory Integration:**
- **PreDelegationHook**: Automatically injects relevant memories before agent execution
- **PostDelegationHook**: Extracts learnings from agent outputs after task completion
- **Context Injection**: Memories are dynamically added to agent context based on task type
- **Learning Extraction**: Agents can mark learnings in their output for automatic capture

**Programmatic Updates:**
```python
# Direct API calls for memory updates
memory_manager.update_agent_memory(agent_id, section, new_item)
memory_manager.add_learning(agent_id, learning_type, content)
```

**CLI-Based Updates:**
```bash
# Add memories on the fly
claude-mpm memory add engineer pattern "Always validate input parameters"
```

**Natural Language Updates:**
Agents recognize memory commands in conversation:
- "Remember this for next time"
- "Add this to your memory"
- "Learn from this mistake"
- "Store this insight"

### Memory Format Specification

Memory files follow a structured markdown format:

```markdown
# Agent Memory: Engineer

<!-- Last Updated: 2025-01-24 10:30:15 | Auto-updated by: system -->

## Memory Usage
- Size: 6.2 KB / 8.0 KB (77.5%)
- Sections: 4 active
- Last optimized: 2025-01-20

## Project Architecture
- Use src/ layout pattern for Python packages
- Follow service-oriented architecture with clear separation
- Store all scripts in /scripts/, never in project root

## Implementation Guidelines  
- All imports use full package name: from claude_mpm.module import ...
- Run E2E tests after significant changes
- Create backups before major optimizations

## Common Mistakes to Avoid
- Don't place test files outside of /tests/ directory
- Never update git config in automated scripts
- Avoid using search commands like find and grep in bash

## Current Technical Context
- Project uses pytest for testing framework
- Memory files limited to 8KB with auto-truncation
- Socket.IO integration optional for notifications
```

### Memory Categories

**Architectural Patterns:**
- Design decisions and structural guidelines
- Component relationships and dependencies
- Technology stack choices and rationale

**Implementation Guidelines:**
- Coding standards and conventions
- Best practices and recommended approaches
- Tool usage and configuration patterns

**Common Mistakes:**
- Known pitfalls and how to avoid them
- Error patterns and their solutions
- Debugging insights and troubleshooting

**Technical Context:**
- Current project state and decisions
- Temporary constraints or considerations
- Environmental or configuration specifics

### Agent-Specific Memory Guidelines

**Engineer Agent:**
- **Project-Specific Implementation**: Learns actual coding patterns from the codebase (e.g., "Use functional components with hooks" for React projects)
- **Framework-Specific Guidelines**: Understands the specific frameworks and libraries used in the project
- **Architecture Adherence**: Follows the detected project architecture (CLI app, web service, SPA, etc.)
- **Build Tool Integration**: Understands the project's build system (webpack, Vite, pytest, cargo, etc.)
- **Error Pattern Learning**: Learns from build errors specific to the project's tech stack

**Research Agent:**
- **Domain-Specific Context**: Understands project terminology and domain concepts
- **Technology Research**: Focuses on research relevant to the project's tech stack
- **Integration Patterns**: Learns about integrations specific to the detected databases and services
- **Best Practices**: Researches practices specific to the project's architecture type

**QA Agent:**
- **Framework-Specific Testing**: Learns testing patterns for the detected testing framework (pytest, Jest, etc.)
- **Project Test Patterns**: Understands the actual test organization from the test directory structure
- **Coverage Standards**: Applies coverage requirements specific to the project configuration
- **Quality Gates**: Learns quality standards from the project's actual CI/CD configuration

**Documentation Agent:**
- **Project Documentation Style**: Learns from existing documentation patterns in the project
- **Technical Writing Context**: Understands the project's documentation structure and conventions
- **Audience Adaptation**: Tailors documentation to the project's user base and technical level
- **Format Consistency**: Follows the project's established documentation formats and standards

## Technical Details

### ProjectAnalyzer Architecture

The `ProjectAnalyzer` class provides intelligent project analysis for context-aware memory generation.

**Core Analysis Capabilities:**

1. **Configuration File Analysis**
   - Detects technology stack from package.json, requirements.txt, pyproject.toml, Cargo.toml
   - Extracts dependencies, frameworks, and build tools
   - Identifies package managers and testing frameworks

2. **Directory Structure Analysis**
   - Maps project organization patterns (src/, lib/, app/, services/)
   - Identifies entry points and main modules
   - Recognizes architectural patterns from folder structure

3. **Source Code Pattern Recognition**
   - Analyzes coding conventions and patterns from actual source files
   - Detects framework usage patterns (Flask routes, React components, etc.)
   - Identifies database integrations and API patterns

4. **Documentation Discovery**
   - Dynamically finds relevant documentation files
   - Prioritizes files based on project type and characteristics
   - Includes configuration files in analysis for memory generation

**API Methods:**

```python
# Core analysis method
def analyze_project(force_refresh: bool = False) -> ProjectCharacteristics

# Get formatted summary for memory templates
def get_project_context_summary() -> str

# Get important files for memory building
def get_important_files_for_context() -> List[str]
```

**ProjectCharacteristics Data Structure:**
```python
@dataclass
class ProjectCharacteristics:
    project_name: str
    primary_language: Optional[str]
    languages: List[str]
    frameworks: List[str]
    architecture_type: str
    main_modules: List[str]
    key_directories: List[str]
    entry_points: List[str]
    testing_framework: Optional[str]
    test_patterns: List[str]
    package_manager: Optional[str]
    build_tools: List[str]
    databases: List[str]
    web_frameworks: List[str]
    api_patterns: List[str]
    key_dependencies: List[str]
    code_conventions: List[str]
    configuration_patterns: List[str]
    project_terminology: List[str]
    documentation_files: List[str]
    important_configs: List[str]
```

**Integration with Memory System:**
- **AgentMemoryManager**: Uses ProjectAnalyzer to create project-specific memory templates
- **MemoryBuilder**: Uses dynamic file discovery for enhanced documentation processing
- **Memory Templates**: Include project context summaries for immediate relevance

### Memory File Structure

```
.claude-mpm/memories/
├── engineer_agent.md          # Engineer-specific memories
├── research_agent.md          # Research findings and insights
├── qa_agent.md               # Quality assurance learnings
├── documentation_agent.md    # Documentation patterns
├── .last_processed.json      # Documentation build timestamps
└── README.md                 # Memory system overview
```

### Memory Routing Algorithm

The routing system uses keyword analysis and pattern matching:

1. **Content Normalization**: Remove noise words, normalize spacing
2. **Agent Scoring**: Calculate relevance scores based on keyword matches
3. **Context Application**: Apply hints from task type or explicit instructions
4. **Target Selection**: Choose highest-scoring agent with confidence threshold
5. **Section Determination**: Map content type to appropriate memory section

**Agent Keyword Patterns:**
- **Engineer**: implementation, code, function, architecture, performance
- **Research**: research, analysis, findings, documentation, security
- **QA**: test, quality, bug, validation, coverage, standards
- **Documentation**: document, readme, guide, explanation, reference

### Optimization Strategies

**Duplicate Detection:**
- Exact content matching (case-insensitive)
- Similarity scoring using SequenceMatcher
- 85% similarity threshold for duplicate removal

**Consolidation Logic:**
- 70% similarity threshold for related items
- Merge strategy preserves most detailed content
- Additional context appended in parentheses

**Priority-Based Reordering:**
- High priority: critical, important, essential, must, always, never
- Medium priority: should, recommended, prefer, avoid, consider
- Low priority: note, tip, hint, example, reference

### Memory Size Management

**Size Limits:**
- Default: 8KB per memory file (~2000 tokens)
- Configurable per agent through overrides
- Auto-truncation when limits exceeded

**Section Limits:**
- Maximum 10 sections per memory file
- Maximum 15 items per section
- Maximum 120 characters per line item

**Optimization Triggers:**
- Manual optimization commands
- Automatic optimization when size limits approached
- Periodic cleanup through scheduled tasks

## Hook System Integration

### Memory Hooks Overview

The memory system integrates seamlessly with the Claude MPM hook system to provide automatic, real-time memory management:

**Available Memory Hooks:**

1. **MemoryPreDelegationHook**
   - Loads agent-specific memories before task execution
   - Injects memories as additional context in agent prompts
   - Ensures agents have access to accumulated knowledge
   - Priority: 20 (runs early in pre-delegation chain)

2. **MemoryPostDelegationHook**
   - Extracts learnings from agent outputs after task completion
   - Looks for explicit learning markers in agent responses
   - Automatically categorizes and stores new insights
   - Only active when auto_learning is enabled

### Hook Configuration

**Enable Memory Hooks:**
```yaml
# In .claude-mpm/config.yml
memory:
  enabled: true
  auto_learning: true  # Enables PostDelegationHook
  
hooks:
  memory_integration: true
```

**Hook Registration (Automatic):**
Memory hooks are automatically registered when:
- Memory system is enabled in configuration
- Claude MPM hook handler is initialized
- Agent delegation occurs

### Custom Hook Development

**Creating Custom Memory Hooks:**
```python
from claude_mpm.hooks.base_hook import PreDelegationHook, HookContext, HookResult
from claude_mpm.services.agent_memory_manager import AgentMemoryManager

class CustomMemoryHook(PreDelegationHook):
    def __init__(self):
        super().__init__(name="custom_memory", priority=25)
        self.memory_manager = AgentMemoryManager()
    
    def execute(self, context: HookContext) -> HookResult:
        agent_id = context.data.get('agent')
        task_type = context.data.get('task_type')
        
        # Load task-specific memories
        if task_type == 'testing':
            qa_memory = self.memory_manager.load_agent_memory('qa')
            context.data['additional_context'] = qa_memory
        
        return HookResult(success=True, modified=True, data=context.data)
```

### Dynamic Context Injection

Hooks can inject various types of context dynamically:

**Project Context Hook Example:**
```python
class ProjectContextHook(PreDelegationHook):
    def execute(self, context: HookContext) -> HookResult:
        # Inject real-time project state
        context.data['project_context'] = {
            'current_branch': get_git_branch(),
            'recent_commits': get_recent_commits(),
            'open_issues': fetch_github_issues(),
            'deployment_status': check_deployment()
        }
        return HookResult(success=True, modified=True, data=context.data)
```

**Time-Based Context Hook:**
```python
class TimeBasedContextHook(PreDelegationHook):
    def execute(self, context: HookContext) -> HookResult:
        current_hour = datetime.now().hour
        
        # Inject time-sensitive information
        if current_hour >= 22 or current_hour < 6:
            context.data['warnings'] = "Late night - avoid production deployments"
        elif current_hour == 12:
            context.data['reminders'] = "Team standup in 30 minutes"
        
        return HookResult(success=True, modified=True, data=context.data)
```

## Best Practices

### Leveraging Project-Specific Memory Generation

**Maximizing Automatic Analysis:**
- Keep configuration files up-to-date (package.json, requirements.txt, etc.)
- Maintain clear directory structure following conventional patterns
- Document architectural decisions in discoverable locations (README.md, docs/)
- Use standard entry point files (main.py, app.js, index.ts)

**Enhancing Project Analysis:**
- Add project-specific documentation that the analyzer can discover
- Use consistent naming conventions that the analyzer can recognize
- Structure code to follow recognizable patterns (MVC, microservices, etc.)
- Include comments that describe architectural decisions and patterns

### When to Add Memories

**High-Value Situations:**
- Architectural decisions and their rationale (beyond what's auto-detected)
- Successful problem-solving patterns specific to your project context
- Common mistakes and their solutions within your tech stack
- Project-specific conventions that aren't automatically discoverable
- Performance optimizations and their impact on your specific architecture
- Integration patterns unique to your project's service combinations

**Avoid Adding:**
- Information already captured by project analysis (language, frameworks, directory structure)
- Temporary workarounds or hacks
- Generic best practices readily available in documentation
- Implementation details already evident from code patterns
- Personal preferences without team consensus

### Memory Size Guidelines

**Optimal Memory Size:**
- Keep individual items under 100 characters
- Aim for 15-20 key insights per section
- Target 70-80% of size limit for growth room
- Regular cleanup maintains relevance

**Content Quality:**
- Focus on actionable insights over descriptions
- Use clear, concise language
- Include context when patterns are non-obvious
- Prioritize learnings with broad applicability

### Categorization Tips

**Use Appropriate Sections:**
- **Architecture**: High-level design decisions
- **Guidelines**: Day-to-day implementation practices
- **Mistakes**: Known pitfalls and their solutions
- **Context**: Current project state and constraints

**Agent Assignment:**
- **Engineer**: Implementation and technical details
- **Research**: Domain knowledge and external insights
- **QA**: Quality standards and testing approaches
- **PM**: Process, coordination, and project management

### Cross-Agent Knowledge Sharing

**Identify Common Patterns:**
- Use `memory cross-ref` to find shared knowledge
- Consolidate duplicate insights across agents
- Ensure consistent terminology and approaches

**Knowledge Distribution:**
- Share architectural decisions across relevant agents
- Duplicate critical safety guidelines
- Maintain agent-specific perspectives on shared concepts

## Troubleshooting

### Common Issues and Solutions

**Memory Files Not Updating:**
```bash
# Check system status
claude-mpm memory status

# Verify configuration
cat .claude-mpm/config.yml

# Check permissions
ls -la .claude-mpm/memories/
```

**Memory Files Growing Too Large:**
```bash
# Check current usage
claude-mpm memory status

# Optimize memories
claude-mpm memory optimize

# Adjust size limits in config
# memory.limits.default_size_kb: 4
```

**Auto-Learning Not Working:**
```bash
# Enable auto-learning in config
# memory.auto_learning: true

# Check agent-specific settings
# memory.agent_overrides.engineer.auto_learning: true

# Verify memory extraction patterns
claude-mpm memory route --content "test content"
```

**Routing to Wrong Agent:**
```bash
# Test routing logic
claude-mpm memory route --content "your content here"

# Review agent patterns in memory_router.py
# Consider adding custom keywords for your domain
```

### Memory File Repair

**Corrupted Memory Files:**
```bash
# Backup existing file
cp .claude-mpm/memories/agent_agent.md agent_backup.md

# Recreate from template
rm .claude-mpm/memories/agent_agent.md
claude-mpm memory add agent context "Rebuilding memory file"
```

**Missing Memory Directory:**
```bash
# Reinitialize memory system
mkdir -p .claude-mpm/memories
claude-mpm memory status
```

### Performance Considerations

**Large Memory Files:**
- Optimize regularly to prevent size bloat
- Use agent-specific size limits for high-volume agents
- Consider memory archiving for historical data

**Slow Memory Operations:**
- Check file system permissions and disk space
- Monitor memory file sizes and section counts
- Use memory analysis to identify optimization opportunities

**Memory Build Performance:**
- Use selective rebuilding (avoid --force-rebuild)
- Process documentation files in priority order
- Monitor last-processed timestamps for efficiency

### Project Analysis Issues

**Incorrect Project Type Detection:**
```bash
# Check what the analyzer detected
python -c "
from claude_mpm.services.project_analyzer import ProjectAnalyzer
analyzer = ProjectAnalyzer()
chars = analyzer.analyze_project()
print(f'Primary Language: {chars.primary_language}')
print(f'Architecture: {chars.architecture_type}')
print(f'Frameworks: {chars.frameworks}')
"

# Force refresh analysis cache
python -c "
from claude_mpm.services.project_analyzer import ProjectAnalyzer
analyzer = ProjectAnalyzer()
chars = analyzer.analyze_project(force_refresh=True)
print(analyzer.get_project_context_summary())
"
```

**Missing Important Files:**
```bash
# Check what files the analyzer found
python -c "
from claude_mpm.services.project_analyzer import ProjectAnalyzer
analyzer = ProjectAnalyzer()
files = analyzer.get_important_files_for_context()
print('Important files found:')
for f in files: print(f'  - {f}')
"

# Ensure your important files are in standard locations
ls -la README.md package.json requirements.txt pyproject.toml
```

**Generic Memories Despite Project Analysis:**
```bash
# Check if project analysis is being used in memory creation
grep -r "project_analyzer\|ProjectAnalyzer" .claude-mpm/memories/

# Rebuild memories with fresh project analysis
claude-mpm memory build --force-rebuild
```

### Configuration Issues

**Default Settings Not Applied:**
```bash
# Verify configuration file location
ls -la .claude-mpm/config.*

# Check configuration syntax
python -c "from claude_mpm.core.config import Config; print(Config().get('memory'))"
```

**Agent-Specific Overrides Not Working:**
```yaml
# Ensure correct agent ID in config
memory:
  agent_overrides:
    engineer:  # Must match exact agent ID
      size_kb: 16
```

**Memory System Disabled:**
```yaml
# Enable in configuration
memory:
  enabled: true  # Must be explicitly true
```

---

For additional configuration options, see [MEMORY_CONFIG.md](MEMORY_CONFIG.md).

For implementation details, see the source code in `src/claude_mpm/services/` and `src/claude_mpm/cli/commands/memory.py`.