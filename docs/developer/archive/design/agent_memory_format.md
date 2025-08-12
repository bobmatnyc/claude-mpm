# Agent Memory Format Guide

## Overview

Agents can now explicitly add learnings to their memory using a special marker format. This gives agents full control over what knowledge gets preserved for future use.

## Format

To add a learning to memory, use the following format in your response:

```
# Add To Memory:
Type: <type>
Content: <your learning here>
#
```

## Supported Types

- **pattern** - Coding patterns and conventions discovered in the codebase
- **architecture** - Architectural insights and design decisions
- **guideline** - Implementation guidelines and best practices
- **mistake** - Common mistakes to avoid
- **strategy** - Effective problem-solving strategies
- **integration** - Integration points and dependencies
- **performance** - Performance considerations and optimizations
- **context** - Current technical context and environment details

## Examples

### Single Memory Entry

```
I've analyzed the authentication system and discovered an important pattern.

# Add To Memory:
Type: pattern
Content: All API endpoints use JWT tokens with bearer authentication
#

This pattern ensures consistent security across the application.
```

### Multiple Memory Entries

```
After implementing the feature, I learned several things:

# Add To Memory:
Type: architecture
Content: Services communicate through event bus for loose coupling
#

# Add To Memory:
Type: mistake
Content: Never call external APIs without timeout configuration
#

# Add To Memory:
Type: performance
Content: Cache user sessions in Redis for sub-millisecond lookups
#
```

## Guidelines

1. **Be Concise**: Keep content under 100 characters for quick reference
2. **Be Specific**: Focus on actionable insights, not general observations
3. **Choose the Right Type**: Use the most appropriate type for categorization
4. **One Learning Per Block**: Each memory block should contain a single insight

## Notes

- The markers are case-insensitive (`# add to memory:` works too)
- Extra whitespace is automatically trimmed
- Duplicate learnings are automatically filtered out
- Only the first line of multi-line content is preserved
- Memory is only stored when auto_learning is enabled in config