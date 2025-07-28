# Claude Code tools mastery guide

Claude Code tools transform AI-assisted development through **YAML-based agent configurations** that define specialized AI assistants with granular tool permissions, enabling secure multi-agent workflows while maintaining strict security boundaries. The system uses **hierarchical settings files** across user, project, and enterprise levels, with agents defined as **Markdown files with YAML frontmatter** in `.claude/agents/` directories that specify tool arrays, permissions, and behavioral patterns.

## How tools shape agent capabilities through YAML

Claude Code agents live as Markdown files with YAML frontmatter in two key locations: **`~/.claude/agents/`** for user-level agents available across all projects, and **`.claude/agents/`** for project-specific agents that can be version-controlled and shared with teams. The YAML configuration structure determines everything about how an agent operates:

```yaml
---
name: security-reviewer
description: "Specialized code reviewer focusing on security vulnerabilities. MUST BE USED for security reviews."
tools: Read, Grep, Glob, Bash
priority: high
---
# System prompt content follows here
You are a security-focused code reviewer...
```

The **tools field** accepts a comma-separated list of available tools. When omitted, agents inherit all tools from the main thread, including any **MCP (Model Context Protocol) tools** prefixed with `mcp__server_name__tool_name`. This inheritance pattern enables powerful delegation where specialized agents maintain full capabilities unless explicitly restricted.

Tool specification follows precise naming conventions. Core tools include **file operations** (Read, Write, Edit, MultiEdit, Glob, Grep, LS), **execution tools** (Bash, Agent, Task), **web tools** (WebFetch, WebSearch), **notebook tools** (NotebookRead, NotebookEdit), and **task management** (TodoRead, TodoWrite). Each tool serves specific purposes - for instance, **MultiEdit** performs multiple atomic edits to a single file, while **Edit** handles single find-and-replace operations.

## Security through hierarchical permission layers

Claude Code implements a sophisticated permission system through **hierarchical settings.json files** that cascade from enterprise to user to project levels. The hierarchy follows this precedence order: enterprise policy settings override everything, followed by command line arguments, then `.claude/settings.local.json` (local project), `.claude/settings.json` (shared project), and finally `~/.claude/settings.json` (user settings).

Permission rules use a **Tool(specifier)** format enabling fine-grained control:

```json
{
  "permissions": {
    "allow": [
      "Bash(git:*)",              // Git commands only
      "Edit(src/**/*.js)",        // JavaScript files in src
      "Read(~/.zshrc)",           // Specific home directory file
      "WebFetch(domain:github.com)" // Domain-restricted web access
    ],
    "deny": [
      "Bash(rm:*)",               // Block dangerous deletions
      "Write(*.env)",             // Protect environment files
      "Edit(node_modules/**)"     // Prevent dependency modifications
    ]
  }
}
```

The permission system supports **gitignore-style patterns** for file operations, **prefix matching** for commands like `Bash(npm run test:*)`, and **exact matching** for specific operations. Critically, **deny rules always take precedence** over allow rules, creating a secure-by-default configuration model.

Security configurations can be managed interactively through the **`/permissions` command**, which provides a real-time UI for adjusting tool access without restarting Claude Code. For repeated permission patterns, the **`/allowed-tools` command** enables quick modifications during active sessions.

## Tool behaviors that define agent performance

Each Claude Code tool exhibits unique operational characteristics that significantly impact agent behavior and performance. Understanding these behaviors enables optimal tool selection and configuration.

The **Task tool** stands out for its ability to spawn up to **10 concurrent subagents**, each with approximately **19,900 tokens** of overhead but providing parallel processing capabilities. These subagents inherit all parent tools except the Task tool itself, preventing recursive spawning. In contrast, the **Agent tool** launches specialized search agents with predefined tool sets, ideal for keyword searches but inefficient for specific file operations.

**Bash maintains persistent shell sessions** across all commands in a conversation, preserving environment variables and working directory state. However, it operates with a **2-minute default timeout** (configurable up to 10 minutes) and cannot handle interactive commands. The tool adds **245 input tokens** to each API call, making command batching important for token efficiency.

File operation tools demonstrate distinct atomic versus batch behaviors. **Edit requires unique string matching** for replacements and fails if the target string appears multiple times. **MultiEdit applies sequential edits atomically** - either all succeed or none apply. The **Read tool limits output to 2,000 lines** by default with lines truncated at 2,000 characters, while **Write completely overwrites files** requiring prior reads for safety.

Web tools face geographic and security restrictions. **WebSearch costs $10 per 1,000 searches** and only operates in US locations. **WebFetch converts HTML to markdown** using Claude 3.5 Haiku for processing, implementing a **15-minute cache** for repeated accesses. Both tools support domain filtering through `allowed_domains` and `blocked_domains` parameters.

## Real-world configurations reveal practical patterns

Production Claude Code deployments demonstrate sophisticated configuration patterns that balance capability with security. A typical full-stack development team configuration illustrates multi-agent orchestration:

```yaml
version: 1
swarm:
  name: "Full Stack Development Team"
  main: architect
  
instances:
  frontend_dev:
    description: "Frontend developer specializing in React and TypeScript"
    directory: ./frontend
    model: opus
    tools:
      - Read
      - Edit
      - Write
      - Bash
      - WebFetch
    allowed_tools:
      - "Edit(src/**/*.{js,jsx,ts,tsx,css,scss})"
      - "Bash(npm:*)"
      - "Bash(yarn:*)"
    disallowed_tools:
      - "Bash(rm:*)"
      - "Write(*.env)"
```

This configuration demonstrates key patterns: **directory-specific contexts** isolate agents to relevant codebases, **model selection** optimizes cost versus capability, and **granular tool permissions** prevent accidental damage while enabling necessary operations.

Enterprise deployments often implement **hook-based security validation**:

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit|MultiEdit",
      "hooks": [{
        "type": "command",
        "command": ".claude/hooks/security-scan.sh",
        "async": false,
        "description": "Run security scan after file modifications"
      }]
    }]
  }
}
```

These hooks enable automated security scanning, code formatting, and compliance checking without manual intervention.

## Optimal tool selection transforms agent effectiveness

Successful Claude Code configuration requires matching tool combinations to specific use cases. For **code review agents**, the combination of `Read, Grep, Glob` provides comprehensive analysis capabilities without modification risks. **Testing agents** benefit from `Read, Edit, Bash(npm test:*)` to run tests and fix failures automatically. **DevOps agents** require `Read, Edit, Bash(terraform:*), Bash(kubectl:*), mcp__aws__*` for infrastructure management with appropriate safety constraints.

The most effective agents follow the principle of **least privilege** - starting with minimal tools and adding based on demonstrated need. A **security-first progression** begins with read-only access (`Read, View`), adds safe development tools (`Edit, Bash(git commit:*)`), then incorporates testing capabilities (`Bash(npm run test:*)`), and finally enables production tools with strict specifiers.

Performance optimization relies on understanding tool costs. **Parallel tool calls** should be used whenever possible, with the Task tool enabling concurrent operations for independent subtasks. **Context preservation** through strategic `/clear` commands prevents performance degradation in long sessions. **Token optimization** involves batching related operations and using MultiEdit instead of multiple Edit calls for the same file.

Common configuration anti-patterns include **over-permissioning** with unrestricted Bash access, **under-specifying** agent descriptions leading to poor task matching, **ignoring context management** causing token waste, and **redundant tool sets** that complicate agent behavior without adding value.

## Conclusion

Claude Code's YAML-based tool configuration system provides unprecedented control over AI agent behavior through hierarchical permissions, specialized tool characteristics, and sophisticated security patterns. Success requires understanding the **interplay between tool capabilities, security constraints, and performance characteristics**. The most effective configurations start conservatively with minimal permissions, measure actual usage patterns, and iteratively expand capabilities based on demonstrated value while maintaining security boundaries. By mastering these configuration patterns, development teams can create powerful, secure, and efficient AI-assisted workflows that significantly enhance productivity while minimizing risks.