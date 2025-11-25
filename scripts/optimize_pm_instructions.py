#!/usr/bin/env python3
"""
Optimize PM_INSTRUCTIONS.md to reduce token count by 20-30%
Target: ~29,433 tokens → ~20,000-24,000 tokens (~9,700 token reduction)
"""

import re
import sys


def optimize_pm_instructions(input_file, output_file):
    """Apply systematic optimizations to PM_INSTRUCTIONS.md"""

    with open(input_file) as f:
        content = f.read()

    original_size = len(content)
    optimizations = []

    # ============================================================================
    # 1. REMOVE DECORATIVE EMOJIS (keep only 🔴, 🚨, ⛔)
    # ============================================================================
    critical_emojis = {"🔴", "🚨", "⛔"}
    lines = content.split("\n")
    cleaned_lines = []
    emoji_removed = 0

    for line in lines:
        cleaned_line = list(line)
        for i, char in enumerate(line):
            if ord(char) > 0x1F300 and char not in critical_emojis:
                cleaned_line[i] = ""
                emoji_removed += 1
        cleaned_lines.append("".join(cleaned_line))

    content = "\n".join(cleaned_lines)
    optimizations.append(f"Removed {emoji_removed} decorative emojis")

    # ============================================================================
    # 2. CONDENSE RESEARCH GATE PROTOCOL (~368 lines → ~80 lines)
    # ============================================================================
    research_gate_start = content.find("### 🔬 RESEARCH GATE PROTOCOL (MANDATORY)")
    research_gate_end = content.find("### 🔥 LOCAL-OPS-AGENT PRIORITY RULE")

    if research_gate_start != -1 and research_gate_end != -1:
        research_gate_condensed = """### 🔬 RESEARCH GATE PROTOCOL (MANDATORY)

**CRITICAL**: PM MUST validate whether research is needed BEFORE delegating implementation.

**When Research Required**: Ambiguous requirements, multiple approaches, unfamiliar areas, unclear dependencies
**When Research NOT Required**: Simple/well-defined task, clear requirements, obvious implementation path

**4-Step Protocol**:
1. **DETERMINE** if research needed
2. **DELEGATE** to Research Agent (if complex/ambiguous)
3. **VALIDATE** Research findings
4. **ENHANCE** delegation with research context

**Decision Rule**: `IF (ambiguous OR multiple_approaches OR unfamiliar) → RESEARCH FIRST`

**Delegation Template**:
```
Task: Implement [feature] based on Research findings
🔬 RESEARCH CONTEXT: [approach, files, dependencies, risks from Research]
📋 REQUIREMENTS: [from Research]
🎯 ACCEPTANCE CRITERIA: [from Research]
Your Task: Implement following Research findings.
```

**Circuit Breaker #7**: Detects Research Gate violations (PM skips research when needed)

**See [templates/research_gate_examples.md](templates/research_gate_examples.md) for examples and decision matrix.**

"""
        content = (
            content[:research_gate_start]
            + research_gate_condensed
            + content[research_gate_end:]
        )
        optimizations.append("Condensed Research Gate Protocol (368→30 lines)")

    # ============================================================================
    # 3. CONDENSE TICKET COMPLETENESS PROTOCOL (~530 lines → ~90 lines)
    # ============================================================================
    ticket_start = content.find("### 🎯 TICKET COMPLETENESS PROTOCOL (MANDATORY)")
    ticket_end = content.find("## PR WORKFLOW DELEGATION")

    if ticket_start != -1 and ticket_end != -1:
        ticket_condensed = """### 🎯 TICKET COMPLETENESS PROTOCOL (MANDATORY)

**CRITICAL**: Before marking ticket work complete, PM MUST ensure ticket contains ALL context for engineer handoff.

**The "Zero PM Context" Test**: Engineer picks up ticket cold without PM:
- Can they understand what to build? (acceptance criteria)
- Do they have research findings and technical context?
- Do they know success criteria and constraints?
- Do they have access to discovered work/follow-ups?

**If ANY NO → Ticket INCOMPLETE → PM VIOLATION**

**5-Point Checklist** (ALL must pass):
1. ✅ **Acceptance Criteria** - Clear "done" definition, measurable success
2. ✅ **Research Findings** - All research outputs, decisions, references
3. ✅ **Technical Context** - Code patterns, dependencies, file locations
4. ✅ **Success Criteria** - Verification steps, performance/security requirements
5. ✅ **Discovered Work** - All follow-ups, related bugs, scope boundaries

**Attachment Rules**:
- Summary (< 500 words) → Ticket comment
- Detailed analysis → docs/research/, link from ticket
- Code/dependencies → Comment with code blocks
- Follow-ups → Subtasks or separate tickets

**Workflow**: Collect artifacts → Run checklist → Attach via ticketing → Verify → Zero PM Test

**Circuit Breaker #6 Extension**: Violations for missing context, incomplete checklist, direct tool use, no verification

**See [templates/ticket_completeness_examples.md](templates/ticket_completeness_examples.md) for complete examples.**

"""
        content = content[:ticket_start] + ticket_condensed + content[ticket_end:]
        optimizations.append("Condensed Ticket Completeness Protocol (530→35 lines)")

    # ============================================================================
    # 4. CONDENSE STRUCTURED QUESTIONS SECTION
    # ============================================================================
    sq_start = content.find("## 📋 STRUCTURED QUESTIONS FOR USER INPUT")
    sq_end = content.find("## CLAUDE MPM SLASH COMMANDS")

    if sq_start != -1 and sq_end != -1:
        sq_condensed = """## 📋 STRUCTURED QUESTIONS FOR USER INPUT

PM uses **AskUserQuestion** tool with pre-built templates for type-safe user input.

**Use For**: PR workflow, project init, ticket prioritization, scope clarification
**Don't Use For**: Permission for obvious steps, standard practices

**Templates** (`claude_mpm.templates.questions`):
- **PRWorkflowTemplate**: PR strategy (main-based/stacked), draft mode, auto-merge
- **ProjectTypeTemplate** / **DevelopmentWorkflowTemplate**: Project setup
- **TicketPrioritizationTemplate** / **TicketScopeTemplate**: Ticket planning
- **ScopeValidationTemplate**: Scope boundaries for discovered work

**Quick Usage**:
```python
from claude_mpm.templates.questions.pr_strategy import PRWorkflowTemplate
template = PRWorkflowTemplate(num_tickets=3, has_ci=True)
# Use template.to_params() with AskUserQuestion tool
```

"""
        content = content[:sq_start] + sq_condensed + content[sq_end:]
        optimizations.append("Condensed Structured Questions section")

    # ============================================================================
    # 5. CONDENSE VIOLATION EXAMPLES
    # ============================================================================
    # Remove redundant Wrong/Correct example blocks (keep reference to templates)
    example_patterns = [
        (
            r"\*\*❌ WRONG - PM searches directly\*\*:.*?\*\*✅ CORRECT - PM delegates search\*\*:.*?\n```\n",
            "**See Circuit Breakers for delegation patterns.**\n\n",
        ),
        (
            r"Example: Bug Fixing.*?Example: Performance Optimization",
            "See [templates/pm_examples.md](templates/pm_examples.md) for concrete examples.\n\n### PM Delegation Scorecard",
        ),
    ]

    for pattern, replacement in example_patterns:
        content = re.sub(pattern, replacement, content, flags=re.DOTALL, count=1)

    optimizations.append("Removed redundant violation examples")

    # ============================================================================
    # 6. CONDENSE GIT FILE TRACKING SECTION
    # ============================================================================
    git_start = content.find("## 🔴 GIT FILE TRACKING PROTOCOL (PM RESPONSIBILITY)")
    git_end = content.find("## SUMMARY: PM AS PURE COORDINATOR")

    if git_start != -1 and git_end != -1:
        git_condensed = """## 🔴 GIT FILE TRACKING PROTOCOL (PM RESPONSIBILITY)

**CRITICAL**: PM MUST track deliverable files in git IMMEDIATELY after agent creates them (NOT at session end).

**When to Track IMMEDIATELY**:
- Agent creates new source files (*.py, *.ts, *.md, etc.)
- Agent creates new config files (.env.example, config.yaml)
- Agent creates new test files (test_*.py)
- Agent creates new docs (docs/*.md)

**When NOT to Track**:
- Temporary files (.pyc, __pycache__, .DS_Store)
- Build artifacts (dist/, build/, *.egg-info)
- IDE files (.vscode/, .idea/)
- Ignored files (per .gitignore)

**Verification Steps** (execute IMMEDIATELY after agent delivers):
1. `git status` - Check for new untracked deliverables
2. `git add [files]` - Track deliverable files only
3. `git commit -m "type: description"` - Commit with conventional format
4. `git log --oneline -1` - Verify commit succeeded

**Commit Format**: `type: description` (feat:, fix:, docs:, test:, chore:, refactor:)

**Before Session End**:
```bash
git status  # Final check for missed files (should be empty)
git log --oneline -5  # Verify all work committed
```

**Circuit Breaker #5**: Detects untracked deliverable files at session end (indicates PM missed immediate tracking)

"""
        content = content[:git_start] + git_condensed + content[git_end:]
        optimizations.append("Condensed Git File Tracking Protocol")

    # ============================================================================
    # 7. REMOVE EXCESSIVE WHITESPACE
    # ============================================================================
    content = re.sub(r"\n{4,}", "\n\n\n", content)  # Max 3 consecutive newlines
    content = re.sub(r" {2,}", " ", content)  # Single spaces only
    optimizations.append("Removed excessive whitespace")

    # ============================================================================
    # 8. CONDENSE DEFAULT BEHAVIOR EXAMPLES SECTION
    # ============================================================================
    default_start = content.find("### Default Behavior Examples:")
    default_end = content.find("### Key Principle:")

    if default_start != -1 and default_end != -1:
        default_condensed = """### Default Behavior Examples:

**✅ CORRECT**: User: "implement auth" → PM delegates full workflow (Research → Engineer → Ops → QA → Docs) → Reports: "Auth complete, QA verified"
**❌ WRONG**: PM asks "Should I proceed?" at each step

"""
        content = content[:default_start] + default_condensed + content[default_end:]
        optimizations.append("Condensed Default Behavior Examples")

    # ============================================================================
    # 9. CONDENSE QUICK DELEGATION MATRIX
    # ============================================================================
    matrix_pattern = r'\| User Says \| PM\'s IMMEDIATE Response \| You MUST Delegate To \|.*?\| "ticket".*?ticketing \(MANDATORY.*?\*\* \|'
    matrix_condensed = """| User Says | Delegate To |
|-----------|-------------|
| "just do it", "handle it" | Full workflow |
| "verify", "check", "test" | Ops/QA |
| "localhost", "local server", "PM2" | **local-ops-agent** (PRIMARY) |
| "stacked PRs", "PR chain" | version-control (with stack params) |
| "ticket", "epic", "Linear", "search ticket" | **ticketing** (MANDATORY) |"""

    content = re.sub(matrix_pattern, matrix_condensed, content, flags=re.DOTALL)
    optimizations.append("Condensed Quick Delegation Matrix")

    # ============================================================================
    # 10. FINAL CLEANUP
    # ============================================================================
    # Remove empty sections
    content = re.sub(r"\n\n\n+", "\n\n", content)

    # Save optimized content
    with open(output_file, "w") as f:
        f.write(content)

    # Calculate results
    new_size = len(content)
    reduction = ((original_size - new_size) / original_size) * 100
    token_original = original_size // 4
    token_new = new_size // 4
    token_savings = token_original - token_new

    print("=" * 70)
    print("PM_INSTRUCTIONS.md OPTIMIZATION COMPLETE")
    print("=" * 70)
    print(f"\nOriginal:   {original_size:,} chars (~{token_original:,} tokens)")
    print(f"Optimized:  {new_size:,} chars (~{token_new:,} tokens)")
    print(f"Reduction:  {original_size - new_size:,} chars (~{token_savings:,} tokens)")
    print(f"Percentage: {reduction:.1f}%")
    print("\nTarget: 20-30% reduction (~5,886-8,829 tokens)")

    if reduction >= 20:
        print(f"✅ SUCCESS: Target achieved! ({reduction:.1f}% reduction)")
    else:
        print(f"⚠️  Need {20 - reduction:.1f}% more to reach minimum target")

    print(f"\nOptimizations Applied ({len(optimizations)}):")
    for i, opt in enumerate(optimizations, 1):
        print(f"  {i}. {opt}")

    return reduction >= 20


if __name__ == "__main__":
    input_file = "src/claude_mpm/agents/PM_INSTRUCTIONS.md"
    output_file = input_file  # Overwrite original

    success = optimize_pm_instructions(input_file, output_file)
    sys.exit(0 if success else 1)
