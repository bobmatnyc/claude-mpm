# Research Documentation

Active research, analysis, and investigation documents for Claude MPM framework development.

## Purpose

This directory contains:
- Feature analysis and design research
- Problem investigation and root cause analysis
- Architecture decisions and trade-off analysis
- Performance and optimization research
- Integration and migration studies

## Active Research Topics

### Agent System
- Agent deployment, synchronization, and lifecycle
- Agent discovery and configuration
- Agent-skill integration and workflows
- Agent instruction optimization

### Configuration & CLI
- Configuration interface design
- CLI structure and user experience
- Command organization and discoverability
- Startup performance optimization

### Cache Architecture
- Cache directory structure and organization
- Git-based agent synchronization
- Update workflows and ETag optimization
- Flat vs nested cache strategies

### Framework Design
- MCP integration patterns
- Memory management with KuzuMemory
- Ticketing system integration
- Multi-agent orchestration

## Archive

Completed research and older analysis can be found in:
- **[../_archive/research/completed-tickets/](../_archive/research/completed-tickets/)** - Completed ticket research
- **[../_archive/research/2025-11/](../_archive/research/2025-11/)** - November 2025 archives

## Research Guidelines

### When to Create Research Documents

Create research documents for:
- Non-trivial feature design decisions
- Architecture changes affecting multiple components
- Performance investigations requiring analysis
- Migration strategies for breaking changes
- Integration points with external systems

### Document Naming

Use descriptive names with dates:
- `{topic}-analysis-YYYY-MM-DD.md` - General analysis
- `{ticket-id}-{topic}-research.md` - Ticket-specific research
- `{feature}-design-YYYY-MM-DD.md` - Design documents
- `{problem}-investigation-YYYY-MM-DD.md` - Problem investigations

### Research Document Structure

Recommended sections:
1. **Context**: Background and motivation
2. **Problem Statement**: Clear problem definition
3. **Analysis**: Investigation findings
4. **Options**: Alternative approaches considered
5. **Recommendation**: Chosen approach with rationale
6. **Impact**: Expected changes and risks
7. **References**: Related tickets, docs, or code

## Archival Policy

Research documents are archived when:
- Associated ticket is completed and closed
- Analysis is superseded by newer research
- Topic is no longer relevant to active development
- File is older than 6 months without updates

Active research (last 4-6 weeks) remains in this directory.

## Related Documentation

- **[../developer/](../developer/README.md)** - Developer documentation and guides
- **[../design/](../design/)** - Architecture and design decisions
- **[../reports/implementation/](../reports/implementation/)** - Implementation reports

---

**Last Updated**: 2025-12-04
**Active Research Files**: 84
**Archived Files**: 6
