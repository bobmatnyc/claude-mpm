# Claude MPM 2.1.0 Release Notes

## Release Date: 2025-07-28

## Overview

Claude MPM 2.1.0 introduces significant improvements to the agent system with dynamic capabilities generation, enhanced security through a comprehensive file hook system, and major documentation reorganization. This release focuses on making the framework more intelligent, secure, and maintainable.

## Major Features

### 1. Dynamic Agent Capabilities System

The framework now dynamically generates agent capabilities documentation from deployed agents instead of using static content. This ensures that documentation always reflects the actual deployed agents in any environment.

**Key Benefits:**
- Agent lists are always current and accurate
- Project-specific agents are automatically included
- No manual maintenance required for agent documentation
- Graceful fallback to default content if generation fails

**Implementation Details:**
- New `DeployedAgentDiscovery` service discovers all deployed agents
- New `AgentCapabilitiesGenerator` service generates markdown content
- Enhanced `ContentAssembler` to process `{{capabilities-list}}` placeholders
- Updated INSTRUCTIONS.md template to use dynamic placeholders

### 2. Comprehensive File Security Hook System

Added a robust security layer through file operation hooks that monitor and validate all file system operations.

**Security Features:**
- Pre and post hooks for all file operations (read, write, edit, delete)
- Path validation and sanitization
- Protection against directory traversal attacks
- Audit logging for security events
- Configurable security policies

### 3. Enhanced `/mpm agents` Command

A new unified command for checking deployed agent versions across all interfaces:

**Available In:**
- CLI: `claude-mpm agents` or `claude-mpm --mpm:agents`
- Interactive Mode: `/mpm:agents`
- Claude Code: `/mpm agents`

**Features:**
- Displays all deployed agents with versions
- Shows base agent version
- Consistent formatting across all access methods
- Migration warnings when applicable

### 4. Documentation Reorganization

Major cleanup and restructuring of project documentation:

**Archive System:**
- Created `docs/archive/` for historical documentation
- Moved 19 outdated documents to archive
- Preserves project history while reducing clutter

**Active Documentation:**
- Updated and consolidated current documentation
- Clear separation between active and archived content
- Improved navigation and discoverability

## New Components

### Services
- `src/claude_mpm/services/agent_capabilities_generator.py` - Generates dynamic agent documentation
- `src/claude_mpm/services/deployed_agent_discovery.py` - Discovers deployed agents across tiers

### Utilities
- `src/claude_mpm/utils/framework_detection.py` - Prevents deployment to framework source

### Scripts

**Testing Scripts:**
- `test_dynamic_capabilities.py` - Tests dynamic capability generation
- `test_deployment_dynamic_capabilities.py` - Tests deployment with dynamic content
- `test_real_deployment_capabilities.py` - End-to-end deployment tests
- `test_agents_command.py` - Tests new `/mpm agents` command
- `test_mpm_agents_integration.py` - Integration tests for agent commands
- `test_runtime_capabilities.py` - Runtime capability tests
- `test_semantic_versioning.py` - Agent version testing

**Debug Scripts:**
- `debug_agent_loading.py` - Debugs agent loading process
- `debug_agent_structure.py` - Inspects agent data structures
- `debug_capabilities_generation.py` - Debugs capability generation
- `debug_deployment_logic.py` - Traces deployment decisions
- `debug_migration.py` - Debugs agent migration

**Monitoring Scripts:**
- `monitor_mcp_services.py` - Monitors MCP service health
- `test_mcp_integration.sh` - Tests MCP integration
- `test_mcp_solution.py` - Validates MCP solutions

## Improvements

### Performance
- Optimized agent discovery with caching
- Reduced file I/O for capability generation
- Improved startup time with lazy loading

### Error Handling
- Comprehensive error messages for agent operations
- Graceful degradation for missing components
- Better debugging information in logs

### Testing
- Added 22 new unit tests for dynamic capabilities
- Enhanced integration test coverage
- New debug scripts for troubleshooting

## Bug Fixes

- Fixed setuptools-scm fallback version detection
- Corrected version parsing in deployment manager
- Resolved issues with INSTRUCTIONS.md format detection
- Fixed edge cases in agent discovery

## Documentation Updates

### New Documentation
- `docs/DYNAMIC_AGENT_CAPABILITIES_IMPLEMENTATION.md` - Implementation guide
- `docs/PHASE1_IMPLEMENTATION_SUMMARY.md` - Phase 1 development summary
- `docs/MPM_AGENTS_COMMAND.md` - Command reference
- `docs/design/claude-mpm-dynamic-agent-capabilities-design.md` - Design specification
- `docs/developer/02-core-components/dynamic-agent-capabilities.md` - Developer guide
- `docs/user/03-features/dynamic-agent-capabilities.md` - User guide

### Updated Documentation
- Enhanced structure documentation
- Updated deployment guides
- Improved versioning documentation
- Consolidated agent documentation

## Breaking Changes

None. This release maintains backward compatibility with 2.0.0.

## Migration Guide

No migration required. The dynamic capabilities system works automatically with existing deployments.

### Optional Steps

To take full advantage of dynamic capabilities:

1. Redeploy agents to refresh INSTRUCTIONS.md:
   ```bash
   claude-mpm agents force-deploy
   ```

2. Check agent versions:
   ```bash
   claude-mpm agents
   ```

## Known Issues

- Dynamic capability generation requires all agents to be properly deployed
- Some legacy agent formats may show limited information

## Dependencies

No new dependencies added. All functionality uses existing packages.

## Looking Ahead

Future enhancements planned for 2.2.0:
- Enhanced agent capability extraction
- Agent categorization and grouping
- Tool usage statistics
- Performance metrics dashboard

## Contributors

Thanks to all contributors who made this release possible through testing, feedback, and code contributions.

---

For detailed upgrade instructions, see [docs/DEPLOY.md](../DEPLOY.md).
For questions or issues, please open a GitHub issue.