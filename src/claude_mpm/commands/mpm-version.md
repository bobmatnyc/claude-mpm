# Display Claude MPM Version Information

Show comprehensive version information for Claude MPM project, agents, and skills.

## Usage

```
/mpm-version
```

## Description

Display version information including:
- Project version and build number
- All deployed agents with their versions (grouped by tier: system/user/project)
- All available skills with their versions (grouped by source: bundled/user/project)
- Summary statistics

## Implementation

When you run `/mpm-version`, the PM will:

1. **Collect Version Information**
   - Use VersionService to gather all version data
   - Project version from pyproject.toml
   - Build number from BUILD_NUMBER file
   - Agent versions from AgentRegistry
   - Skills versions from SkillRegistry

2. **Format Output**
   - Hierarchical display: Project → Agents → Skills
   - Grouped by tier/source for clarity
   - Sorted alphabetically within groups
   - Summary statistics at the end

3. **Display Results**
   - Well-formatted tree structure
   - Easy to scan and read
   - Includes totals and counts

## Example Output

```
Claude MPM Version Information
==============================

Project Version: 4.16.3
Build: 481

Agents (35 total)
-----------------

System Agents (30):
  ├─ agent-manager (1.0.0)
  ├─ engineer (3.9.1)
  ├─ research-agent (4.5.1)
  ├─ documentation (2.1.0)
  ├─ qa (2.0.3)
  └─ ... (25 more)

User Agents (3):
  ├─ custom-agent (1.0.0)
  ├─ testing-agent (0.5.0)
  └─ prototype-agent (0.1.0)

Project Agents (2):
  ├─ project-specific (2.0.0)
  └─ domain-expert (1.1.0)

Skills (20 total)
-----------------

Bundled Skills (20):
  ├─ test-driven-development (0.1.0)
  ├─ systematic-debugging (0.1.0)
  ├─ async-testing (0.1.0)
  ├─ performance-profiling (0.1.0)
  ├─ security-scanning (0.1.0)
  └─ ... (15 more)

User Skills (0):
  (none)

Project Skills (0):
  (none)

Summary
-------
• Project: v4.16.3 (build 481)
• Agents: 35 total (30 system, 3 user, 2 project)
• Skills: 20 total (20 bundled, 0 user, 0 project)
```

## PM Implementation Instructions

To execute this command, PM should:

1. Import and use VersionService:
   ```python
   from claude_mpm.services.version_service import VersionService

   service = VersionService()
   summary = service.get_version_summary()
   ```

2. Format output following the example structure above
3. Handle missing data gracefully (show "unknown" for missing versions)
4. Include all tiers/sources even if counts are zero

## Related Commands

- `/mpm-help` - Show all available MPM commands
- `/mpm-status` - Show system status information
