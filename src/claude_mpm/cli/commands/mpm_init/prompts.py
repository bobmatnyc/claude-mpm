"""
Prompt building functions for MPM-Init command.

This module contains pure functions that generate prompts for different
initialization and update modes. All prompts are constructed as standalone
functions with no external dependencies.
"""

from pathlib import Path
from typing import Any, Dict, Optional

__all__ = [
    "build_enhanced_update_prompt",
    "build_initialization_prompt",
    "build_prompt_engineer_optimization_prompt",
    "build_research_context_prompt",
    "build_update_prompt",
]


def build_initialization_prompt(
    project_path: Path,
    project_type: Optional[str] = None,
    framework: Optional[str] = None,
    ast_analysis: bool = True,
) -> str:
    """
    Build the initialization prompt for the agent.

    Args:
        project_path: Path to the project directory
        project_type: Type of project (web, api, cli, library, etc.)
        framework: Specific framework if applicable
        ast_analysis: Enable AST analysis for enhanced documentation

    Returns:
        Formatted prompt string for agent delegation
    """
    base_prompt = f"""Please delegate this task to the Agentic Coder Optimizer agent:

Initialize this project for optimal use with Claude Code and Claude MPM.

Project Path: {project_path}
"""

    if project_type:
        base_prompt += f"Project Type: {project_type}\n"

    if framework:
        base_prompt += f"Framework: {framework}\n"

    base_prompt += """
Please perform the following initialization tasks:

1. **Analyze Current State**:
   - Scan project structure and existing configurations
   - Identify project type, language, and frameworks
   - Check for existing documentation and tooling

2. **Create/Update CLAUDE.md**:
   - Project overview and purpose
   - Architecture and key components
   - Development guidelines
   - ONE clear way to: build, test, deploy, lint, format
   - Links to all relevant documentation
   - Common tasks and workflows

3. **Establish Single-Path Standards**:
   - ONE command for each operation (build, test, lint, etc.)
   - Clear documentation of THE way to do things
   - Remove ambiguity in workflows

4. **Configure Development Tools**:
   - Set up or verify linting configuration
   - Configure code formatting standards
   - Establish testing framework
   - Add pre-commit hooks if needed

5. **Create Project Structure Documentation**:
   - Document folder organization
   - Explain where different file types belong
   - Provide examples of proper file placement

6. **Set Up GitHub Integration** (if applicable):
   - Create/update .github/workflows
   - Add issue and PR templates
   - Configure branch protection rules documentation

7. **Initialize Memory System**:
   - Create .claude-mpm/memories/ directory
   - Add initial memory files for key project knowledge
   - Document memory usage patterns

8. **Generate Quick Start Guide**:
   - Step-by-step setup instructions
   - Common commands reference
   - Troubleshooting guide
"""

    if ast_analysis:
        base_prompt += """
9. **Perform AST Analysis** (using Code Analyzer agent if needed):
   - Parse code files to extract structure (classes, functions, methods)
   - Generate comprehensive API documentation
   - Create code architecture diagrams
   - Document function signatures and dependencies
   - Extract docstrings and inline comments
   - Map code relationships and inheritance hierarchies
   - Generate developer documentation with:
     * Module overview and purpose
     * Class hierarchies and relationships
     * Function/method documentation
     * Type annotations and parameter descriptions
     * Code complexity metrics
     * Dependency graphs
   - Create DEVELOPER.md with technical architecture details
   - Add CODE_STRUCTURE.md with AST-derived insights
"""

    base_prompt += """

10. **Holistic CLAUDE.md Organization** (CRITICAL - Do this LAST):
   After completing all initialization tasks, take a holistic look at the CLAUDE.md file and:

   a) **Reorganize Content by Priority**:
      - CRITICAL instructions (security, data handling, core business rules) at the TOP
      - Project overview and purpose
      - Key architectural decisions and constraints
      - Development guidelines and standards
      - Common tasks and workflows
      - Links to additional documentation
      - Nice-to-have or optional information at the BOTTOM

   b) **Rank Instructions by Importance**:
      - Use clear markers:
        * 🔴 CRITICAL: Security, data handling, breaking changes, core business rules
        * 🟡 IMPORTANT: Key workflows, architecture decisions, performance requirements
        * 🟢 STANDARD: Common operations, coding standards, best practices
        * ⚪ OPTIONAL: Nice-to-have features, experimental code, future considerations
      - Group related instructions together
      - Ensure no contradictory instructions exist
      - Remove redundant or outdated information
      - Add a "Priority Index" at the top listing all CRITICAL and IMPORTANT items

   c) **Optimize for AI Agent Understanding**:
      - Use consistent formatting and structure
      - Provide clear examples for complex instructions
      - Include "WHY" explanations for critical rules
      - Add quick reference sections for common operations
      - Ensure instructions are actionable and unambiguous

   d) **Validate Completeness**:
      - Ensure ALL critical project knowledge is captured
      - Verify single-path principle (ONE way to do each task)
      - Check that all referenced documentation exists
      - Confirm all tools and dependencies are documented
      - Test that a new AI agent could understand the project from CLAUDE.md alone

   e) **Add Meta-Instructions Section**:
      - Include a section about how to maintain CLAUDE.md
      - Document when and how to update instructions
      - Provide guidelines for instruction priority levels
      - Add a changelog or last-updated timestamp

   f) **Follow This CLAUDE.md Template Structure**:
      ```markdown
      # Project Name - CLAUDE.md

      ## 🎯 Priority Index
      ### 🔴 CRITICAL Instructions
      - [List all critical items with links to their sections]

      ### 🟡 IMPORTANT Instructions
      - [List all important items with links to their sections]

      ## 📋 Project Overview
      [Brief description and purpose]

      ## 🔴 CRITICAL: Security & Data Handling
      [Critical security rules and data handling requirements]

      ## 🔴 CRITICAL: Core Business Rules
      [Non-negotiable business logic and constraints]

      ## 🟡 IMPORTANT: Architecture & Design
      [Key architectural decisions and patterns]

      ## 🟡 IMPORTANT: Development Workflow
      ### ONE Way to Build
      ### ONE Way to Test
      ### ONE Way to Deploy

      ## 🟢 STANDARD: Coding Guidelines
      [Standard practices and conventions]

      ## 🟢 STANDARD: Common Tasks
      [How to perform routine operations]

      ## 📚 Documentation Links
      [Links to additional resources]

      ## ⚪ OPTIONAL: Future Enhancements
      [Nice-to-have features and ideas]

      ## 📝 Meta: Maintaining This Document
      - Last Updated: [timestamp]
      - Update Frequency: [when to update]
      - Priority Guidelines: [how to assign priorities]
      ```

Please ensure all documentation is clear, concise, and optimized for AI agents to understand and follow.
Focus on establishing ONE clear way to do ANYTHING in the project.
The final CLAUDE.md should be a comprehensive, well-organized guide that any AI agent can follow to work effectively on this project.
"""

    return base_prompt


def build_update_prompt(
    project_path: Path,
    doc_analysis: Dict[str, Any],
    project_type: Optional[str] = None,
    framework: Optional[str] = None,
    ast_analysis: bool = True,
    preserve_custom: bool = True,
) -> str:
    """
    Build prompt for update mode.

    Args:
        project_path: Path to the project directory
        doc_analysis: Analysis results from DocumentationManager
        project_type: Type of project (web, api, cli, library, etc.)
        framework: Specific framework if applicable
        ast_analysis: Enable AST analysis for enhanced documentation
        preserve_custom: Preserve custom sections when updating

    Returns:
        Formatted prompt string for update mode
    """
    prompt = f"""Please delegate this task to the Agentic Coder Optimizer agent:

UPDATE existing CLAUDE.md documentation for this project.

Project Path: {project_path}
Update Mode: Smart merge with existing content
"""
    if project_type:
        prompt += f"Project Type: {project_type}\n"
    if framework:
        prompt += f"Framework: {framework}\n"

    prompt += f"""
Existing Documentation Analysis:
- Current CLAUDE.md: {doc_analysis.get("size", 0):,} characters, {doc_analysis.get("lines", 0)} lines
- Has Priority Index: {"Yes" if doc_analysis.get("has_priority_index") else "No"}
- Custom Sections: {len(doc_analysis.get("custom_sections", []))} found
"""
    if preserve_custom and doc_analysis.get("custom_sections"):
        prompt += f"- Preserve Custom Sections: {', '.join(doc_analysis['custom_sections'][:5])}\n"

    prompt += """
Please perform the following UPDATE tasks:

1. **Review Existing Content**:
   - Analyze current CLAUDE.md structure and content
   - Identify outdated or missing information
   - Preserve valuable custom sections and project-specific knowledge

2. **Smart Content Merge**:
   - Update project overview if needed
   - Refresh architecture documentation
   - Update development workflows to ensure single-path principle
   - Merge new standard sections while preserving custom content
   - Remove duplicate or contradictory information

3. **Update Priority Organization**:
   - Reorganize content with priority markers (🔴🟡🟢⚪)
   - Ensure critical instructions are at the top
   - Update priority index with all important items
   - Validate instruction clarity and completeness

4. **Refresh Technical Content**:
   - Update build/test/deploy commands
   - Verify tool configurations are current
   - Update dependency information
   - Refresh API documentation if applicable
"""
    if ast_analysis:
        prompt += """
5. **Update Code Documentation** (using Code Analyzer agent):
   - Re-analyze code structure for changes
   - Update API documentation
   - Refresh architecture diagrams
   - Update function/class documentation
"""
    prompt += """
6. **Final Optimization**:
   - Ensure single-path principle throughout
   - Validate all links and references
   - Add/update timestamp in meta section
   - Verify AI agent readability

IMPORTANT: This is an UPDATE operation. Intelligently merge new content with existing,
preserving valuable project-specific information while refreshing standard sections.
"""
    return prompt


def build_enhanced_update_prompt(
    project_path: Path,
    doc_analysis: Dict[str, Any],
    git_insights: Dict[str, Any],
    log_insights: Dict[str, Any],
    memory_insights: Dict[str, Any],
    project_type: Optional[str] = None,
    framework: Optional[str] = None,
    ast_analysis: bool = True,
    preserve_custom: bool = True,
) -> str:
    """
    Build enhanced update prompt with extracted knowledge from multiple sources.

    This is the AUTO-DETECTED update mode that enriches CLAUDE.md with:
    - Git history insights (architectural decisions, tech changes, workflows)
    - Session log learnings (completed work, patterns)
    - Memory file knowledge (accumulated project wisdom)

    Args:
        project_path: Path to the project directory
        doc_analysis: Analysis results from DocumentationManager
        git_insights: Extracted git history insights
        log_insights: Extracted session log insights
        memory_insights: Extracted memory file insights
        project_type: Type of project (web, api, cli, library, etc.)
        framework: Specific framework if applicable
        ast_analysis: Enable AST analysis for enhanced documentation
        preserve_custom: Preserve custom sections when updating

    Returns:
        Formatted prompt string for enhanced update mode
    """
    prompt = f"""Please delegate this task to the Agentic Coder Optimizer agent:

ENHANCED UPDATE of existing CLAUDE.md documentation with extracted project knowledge.

Project Path: {project_path}
Update Mode: Knowledge-enriched smart merge
"""
    if project_type:
        prompt += f"Project Type: {project_type}\n"
    if framework:
        prompt += f"Framework: {framework}\n"

    prompt += f"""
Existing Documentation Analysis:
- Current CLAUDE.md: {doc_analysis.get("size", 0):,} characters, {doc_analysis.get("lines", 0)} lines
- Has Priority Index: {"Yes" if doc_analysis.get("has_priority_index") else "No"}
- Custom Sections: {len(doc_analysis.get("custom_sections", []))} found
"""
    if preserve_custom and doc_analysis.get("custom_sections"):
        prompt += f"- Preserve Custom Sections: {', '.join(doc_analysis['custom_sections'][:5])}\n"

    # Add extracted knowledge sections
    prompt += "\n## Extracted Project Knowledge\n\n"

    # Git insights
    if git_insights.get("available"):
        prompt += "### From Git History (last 90 days):\n\n"

        if git_insights.get("architectural_decisions"):
            prompt += "**Architectural Patterns Detected:**\n"
            for decision in git_insights["architectural_decisions"][:10]:
                prompt += f"- {decision}\n"
            prompt += "\n"

        if git_insights.get("tech_stack_changes"):
            prompt += "**Tech Stack Changes:**\n"
            for change in git_insights["tech_stack_changes"][:10]:
                prompt += f"- {change}\n"
            prompt += "\n"

        if git_insights.get("workflow_patterns"):
            prompt += "**Common Workflows:**\n"
            for workflow in git_insights["workflow_patterns"][:8]:
                prompt += f"- {workflow}\n"
            prompt += "\n"

        if git_insights.get("hot_files"):
            prompt += "**Hot Files (frequently modified):**\n"
            for file_info in git_insights["hot_files"][:10]:
                prompt += (
                    f"- {file_info['path']} ({file_info['modifications']} changes)\n"
                )
            prompt += "\n"

    # Session log insights
    if log_insights.get("available") and log_insights.get("learnings"):
        prompt += "### From Session Logs:\n\n"
        prompt += "**Recent Learnings from PM Summaries:**\n"
        for learning in log_insights["learnings"][:10]:
            source = learning.get("source", "unknown")
            content = learning.get("content", "")
            # Truncate long content
            if len(content) > 200:
                content = content[:200] + "..."
            prompt += f"- [{source}] {content}\n"
        prompt += "\n"

        if log_insights.get("common_patterns"):
            prompt += "**Common Task Patterns:**\n"
            prompt += f"- {', '.join(log_insights['common_patterns'][:10])}\n\n"

    # Memory insights
    if memory_insights.get("available"):
        has_content = False

        if memory_insights.get("architectural_knowledge"):
            has_content = True
            prompt += "### From Agent Memories:\n\n"
            prompt += "**Architectural Knowledge:**\n"
            for item in memory_insights["architectural_knowledge"][:8]:
                prompt += f"- {item}\n"
            prompt += "\n"

        if memory_insights.get("implementation_guidelines"):
            if not has_content:
                prompt += "### From Agent Memories:\n\n"
                has_content = True
            prompt += "**Implementation Guidelines:**\n"
            for item in memory_insights["implementation_guidelines"][:8]:
                prompt += f"- {item}\n"
            prompt += "\n"

        if memory_insights.get("common_mistakes"):
            if not has_content:
                prompt += "### From Agent Memories:\n\n"
                has_content = True
            prompt += "**Common Mistakes to Avoid:**\n"
            for item in memory_insights["common_mistakes"][:8]:
                prompt += f"- {item}\n"
            prompt += "\n"

        if memory_insights.get("technical_context"):
            if not has_content:
                prompt += "### From Agent Memories:\n\n"
            prompt += "**Current Technical Context:**\n"
            for item in memory_insights["technical_context"][:8]:
                prompt += f"- {item}\n"
            prompt += "\n"

    # Add update instructions
    prompt += """
## UPDATE Tasks with Knowledge Integration:

1. **Review Existing Content**:
   - Analyze current CLAUDE.md structure and content
   - Identify outdated or missing information
   - Preserve valuable custom sections and project-specific knowledge

2. **Integrate Extracted Knowledge**:
   - Merge architectural decisions from git history into Architecture section
   - Add tech stack changes to Technology/Dependencies sections
   - Update workflow patterns in Development Guidelines
   - Incorporate session learnings into relevant sections
   - Merge memory insights into appropriate documentation areas
   - Highlight hot files as critical components

3. **Smart Content Merge**:
   - Update project overview with recent developments
   - Refresh architecture documentation with detected patterns
   - Update development workflows with discovered common patterns
   - Ensure single-path principle (ONE way to do each task)
   - Remove duplicate or contradictory information

4. **Update Priority Organization**:
   - Reorganize content with priority markers (🔴🟡🟢⚪)
   - Ensure critical instructions are at the top
   - Update priority index with all important items
   - Promote frequently-modified files to IMPORTANT sections

5. **Refresh Technical Content**:
   - Update build/test/deploy commands based on workflow patterns
   - Verify tool configurations match tech stack changes
   - Update dependency information with detected changes
   - Refresh API documentation if applicable
"""
    if ast_analysis:
        prompt += """
6. **Update Code Documentation** (using Code Analyzer agent):
   - Re-analyze code structure for changes
   - Update API documentation
   - Refresh architecture diagrams
   - Document hot files and critical components
"""
    prompt += """
7. **Final Optimization**:
   - Ensure single-path principle throughout
   - Validate all links and references
   - Add/update timestamp in meta section
   - Add "Last Updated" note mentioning knowledge extraction
   - Verify AI agent readability

IMPORTANT: This is an ENHANCED UPDATE operation with extracted knowledge.
Intelligently merge insights from git history, session logs, and agent memories
into the existing CLAUDE.md while preserving valuable custom content.
The goal is to create a living document that reflects actual project evolution.
"""
    return prompt


def build_research_context_prompt(git_analysis: Dict[str, Any], days: int) -> str:
    """
    Build structured Research agent delegation prompt from git analysis.

    Args:
        git_analysis: Git analysis data from EnhancedProjectAnalyzer
        days: Number of days analyzed

    Returns:
        Formatted research prompt for context analysis
    """
    # Extract key data
    commits = git_analysis.get("commits", [])
    branches = git_analysis.get("branches", [])
    contributors = git_analysis.get("contributors", {})
    file_changes = git_analysis.get("file_changes", {})

    # Build prompt following Prompt Engineer's template
    prompt = f"""# Project Context Analysis Mission

You are Research agent analyzing git history to provide PM with intelligent project context for resuming work.

## Analysis Scope
- **Time Range**: Last {days} days"""

    # Add adaptive mode note if applicable
    if git_analysis.get("adaptive_mode"):
        actual_days = git_analysis.get("actual_time_span", "extended period")
        prompt += f""" (adaptive: {actual_days} days analyzed)
- **Note**: {git_analysis.get("reason", "Analysis window adjusted to ensure meaningful context")}"""

    prompt += f"""
- **Commits Analyzed**: {len(commits)} commits
- **Branches**: {", ".join(branches[:5]) if branches else "main"}
- **Contributors**: {", ".join(contributors.keys()) if contributors else "Unknown"}

## Your Mission

Analyze git history to answer these questions for PM:

1. **What was being worked on?** (Active work streams)
2. **Why was this work happening?** (Intent and motivation)
3. **What's the natural next step?** (Continuation recommendations)
4. **What needs attention?** (Risks, stalls, conflicts)

## Git Data Provided

### Recent Commits ({min(len(commits), 10)} most recent):
"""

    # Add recent commits
    for commit in commits[:10]:
        author = commit.get("author", "Unknown")
        timestamp = commit.get("timestamp", "Unknown date")
        message = commit.get("message", "No message")
        files = commit.get("files", [])

        prompt += f"\n- **{timestamp}** by {author}"
        prompt += f"\n  {message}"
        prompt += f"\n  Files changed: {len(files)}\n"

    # Add file change summary
    if file_changes:
        # Sort by modifications count
        sorted_files = sorted(
            file_changes.items(),
            key=lambda x: x[1].get("modifications", 0),
            reverse=True,
        )
        prompt += "\n### Most Changed Files:\n"
        for file_path, file_data in sorted_files[:10]:
            modifications = file_data.get("modifications", 0)
            file_contributors = file_data.get("contributors", [])
            prompt += f"- {file_path}: {modifications} changes ({len(file_contributors)} contributor{'s' if len(file_contributors) != 1 else ''})\n"

    # Add contributor summary
    if contributors:
        prompt += "\n### Contributors:\n"
        sorted_contributors = sorted(
            contributors.items(),
            key=lambda x: x[1].get("commits", 0),
            reverse=True,
        )
        for name, info in sorted_contributors[:5]:
            commit_count = info.get("commits", 0)
            prompt += (
                f"- {name}: {commit_count} commit{'s' if commit_count != 1 else ''}\n"
            )

    # Add analysis instructions
    prompt += """

## Analysis Instructions

### Phase 1: Work Stream Identification
Group related commits into thematic work streams. For each stream:
- **Name**: Infer from commit messages (e.g., "Authentication refactor")
- **Status**: ongoing/completed/stalled
- **Commits**: Count of commits in this stream
- **Intent**: WHY this work (from commit bodies/messages)
- **Key Files**: Most changed files in this stream

### Phase 2: Risk Detection
Identify:
- **Stalled Work**: Work streams with no activity >3 days
- **Anti-Patterns**: WIP commits, temp commits, debug commits
- **Documentation Lag**: Code changes without doc updates
- **Conflicts**: Merge conflicts or divergent branches

### Phase 3: Recommendations
Based on analysis:
1. **Primary Focus**: Most active/recent work to continue
2. **Quick Wins**: Small tasks that could be finished
3. **Blockers**: Issues preventing progress
4. **Next Steps**: Logical continuation points

## Output Format

Provide a clear markdown summary with:

1. **Active Work Streams** (What was being worked on)
2. **Intent Summary** (Why this work matters)
3. **Risks Detected** (What needs attention)
4. **Recommended Next Actions** (What to work on)

Keep it concise (<1000 words) but actionable.

## Success Criteria
- Work streams accurately reflect development themes
- Intent captures the "why" not just "what"
- Recommendations are specific and actionable
- Risks are prioritized by impact
"""

    return prompt


def build_prompt_engineer_optimization_prompt(
    content: str, estimated_tokens: int
) -> str:
    """
    Build prompt for prompt-engineer to optimize CLAUDE.md.

    Args:
        content: Current CLAUDE.md content to optimize
        estimated_tokens: Estimated token count of current content

    Returns:
        Formatted prompt string for prompt-engineer optimization
    """
    return f"""Please delegate this task to the Prompt Engineer agent:

Optimize this CLAUDE.md file for conciseness, clarity, and token efficiency while preserving all critical information.

## Current CLAUDE.md Statistics
- Estimated tokens: {estimated_tokens:,}
- Target reduction: 20-30% if possible
- Priority: Preserve ALL CRITICAL (🔴) and IMPORTANT (🟡) information

## Optimization Goals

1. **Remove Redundancy**:
   - Eliminate duplicate information across sections
   - Consolidate similar instructions
   - Remove verbose explanations where brevity suffices

2. **Tighten Language**:
   - Use fewer words to convey the same meaning
   - Replace wordy phrases with concise alternatives
   - Remove filler words and unnecessary qualifiers

3. **Improve Structure**:
   - Ensure clear hierarchical organization
   - Use priority markers (🔴 🟡 🟢 ⚪) effectively
   - Group related information logically
   - Maintain scannable headings

4. **Preserve Critical Content**:
   - Keep ALL security and data handling rules (🔴)
   - Maintain core business logic and constraints (🔴)
   - Preserve architectural decisions (🟡)
   - Keep essential workflows intact (🟡)

5. **Apply Claude Best Practices**:
   - Use high-level guidance over prescriptive checklists
   - Provide context for WHY, not just WHAT
   - Ensure instructions are actionable and unambiguous
   - Optimize for AI agent understanding

## Current CLAUDE.md Content

{content}

## Output Requirements

Return ONLY the optimized CLAUDE.md content with NO additional explanations.
The optimized version should:
- Reduce token count by 20-30% if feasible
- Maintain all CRITICAL and IMPORTANT instructions
- Improve clarity and scannability
- Follow the same structural template (Priority Index, sections with markers)

## Quality Criteria

✅ All 🔴 CRITICAL items preserved
✅ All 🟡 IMPORTANT items preserved
✅ No contradictory instructions
✅ Clear, concise language throughout
✅ Logical organization maintained
✅ Token count reduced meaningfully
"""
