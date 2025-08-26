# Code Analysis with Mermaid Diagrams

The `analyze` command provides powerful code analysis capabilities with integrated mermaid diagram generation, allowing you to visualize and understand your codebase architecture.

## Quick Start

```bash
# Basic code analysis of current directory
claude-mpm analyze

# Analysis with mermaid diagram generation
claude-mpm analyze --mermaid

# Analyze specific directory with multiple diagram types
claude-mpm analyze --target ./src --mermaid --mermaid-types class_diagram flowchart

# Save diagrams to files
claude-mpm analyze --mermaid --save-diagrams --diagram-output ./diagrams
```

## Features

### Code Analysis

The analyze command leverages the Code Analyzer agent to provide:

- **Multi-language support**: Analyzes Python, JavaScript, TypeScript, Go, and more
- **Architecture visualization**: Generate diagrams of your code structure
- **Pattern detection**: Identify design patterns and anti-patterns
- **Dependency analysis**: Map module and package dependencies
- **Security scanning**: Identify potential security issues
- **Performance analysis**: Find performance bottlenecks

### Mermaid Diagram Generation

Generate various types of diagrams directly from your code:

#### Supported Diagram Types

- **entry_points**: Map all entry points in the codebase (default)
- **class_diagram**: UML class diagrams showing relationships
- **sequence**: Sequence diagrams for key workflows
- **flowchart**: Flowcharts for main processes
- **state**: State diagrams for stateful components
- **entity_relationship**: Database entity relationships
- **component**: High-level component architecture
- **dependency_graph**: Module and package dependencies
- **call_graph**: Function/method call relationships
- **architecture**: Overall system architecture

### Output Formats

- **text**: Human-readable terminal output (default)
- **json**: Structured JSON for programmatic use
- **markdown**: Formatted markdown with embedded diagrams

## Command Options

### Analysis Options

```bash
--target PATH           # Directory or file to analyze (default: current dir)
--recursive            # Recursively analyze subdirectories (default: True)
--agent AGENT_ID       # Agent to use for analysis (default: code-analyzer)
--prompt TEXT          # Additional instructions for the analysis
--focus AREAS          # Focus areas: security, performance, architecture, quality, documentation
```

### Mermaid Options

```bash
--mermaid              # Enable mermaid diagram generation
--mermaid-types TYPES  # Types of diagrams to generate (space-separated)
--save-diagrams        # Save diagrams to files
--diagram-output PATH  # Directory to save diagrams (default: ./diagrams/)
```

### Session Options

```bash
--session-id ID        # Use specific session ID for analysis
--no-session          # Run without session management
```

### Output Options

```bash
--format FORMAT       # Output format: text, json, markdown
--output PATH        # Save analysis output to file
--verbose           # Show detailed analysis progress
```

## Examples

### Basic Analysis

```bash
# Analyze current directory
claude-mpm analyze

# Analyze specific project
claude-mpm analyze --target ~/projects/my-app
```

### Generate Architecture Diagrams

```bash
# Generate entry points and architecture diagrams
claude-mpm analyze --mermaid --mermaid-types entry_points architecture

# Save all diagram types to files
claude-mpm analyze --mermaid \
  --mermaid-types class_diagram flowchart component \
  --save-diagrams \
  --diagram-output ./docs/diagrams
```

### Security-Focused Analysis

```bash
# Security and performance analysis with diagrams
claude-mpm analyze \
  --focus security performance \
  --mermaid \
  --mermaid-types dependency_graph call_graph \
  --prompt "Identify security vulnerabilities and performance bottlenecks"
```

### Export Analysis Results

```bash
# Export as markdown with embedded diagrams
claude-mpm analyze \
  --mermaid \
  --format markdown \
  --output analysis_report.md

# Export as JSON for programmatic processing
claude-mpm analyze \
  --format json \
  --output analysis_data.json
```

### Using Sessions

```bash
# Create analysis session for iterative analysis
claude-mpm analyze --session-id my-analysis-session

# Continue analysis in same session
claude-mpm analyze --session-id my-analysis-session \
  --prompt "Now focus on the database layer"
```

## Output Examples

### Text Output

```
Code Analysis Report
==================================================

Target: /Users/developer/projects/my-app

📊 Extracted 3 mermaid diagrams:
  • class_relationships
  • component_architecture
  • data_flow

💾 Saved diagrams to:
  • ./diagrams/20240126_143022_class_relationships.mermaid
  • ./diagrams/20240126_143022_component_architecture.mermaid
  • ./diagrams/20240126_143022_data_flow.mermaid

--------------------------------------------------
Analysis Results:
--------------------------------------------------
[Detailed analysis output...]
```

### Saved Mermaid Files

Generated diagram files include:
- Timestamp for versioning
- Source metadata
- Clean mermaid syntax ready for rendering

Example saved file:

```mermaid
// Generated by Claude MPM Code Analyzer
// Timestamp: 20240126_143022
// Target: /Users/developer/projects/my-app
// Title: class_relationships

classDiagram
    class UserService {
        +getUser(id: string)
        +updateUser(data: object)
        -validateUser(user: object)
    }
    class UserRepository {
        +findById(id: string)
        +save(user: object)
    }
    UserService --> UserRepository : uses
```

## Best Practices

1. **Start Simple**: Begin with basic analysis before adding diagram generation
2. **Focus Analysis**: Use `--focus` to target specific aspects
3. **Save Diagrams**: Always use `--save-diagrams` for important analysis
4. **Use Sessions**: Leverage sessions for iterative analysis
5. **Custom Prompts**: Add specific instructions via `--prompt` for targeted insights

## Integration with CI/CD

The analyze command can be integrated into CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Code Analysis
  run: |
    claude-mpm analyze \
      --mermaid \
      --save-diagrams \
      --diagram-output ./artifacts/diagrams \
      --format json \
      --output ./artifacts/analysis.json
```

## Troubleshooting

### Common Issues

1. **No diagrams extracted**: Ensure the agent is generating mermaid blocks
2. **Timeout errors**: Large codebases may need more time, adjust timeout
3. **Agent deployment fails**: Check agent availability with `claude-mpm agents list`

### Debug Mode

Run with verbose logging for troubleshooting:

```bash
claude-mpm analyze --verbose --logging DEBUG
```

## Related Commands

- `claude-mpm agents list` - View available analysis agents
- `claude-mpm agent-manager show code-analyzer` - View analyzer agent details
- `claude-mpm doctor` - Diagnose system issues