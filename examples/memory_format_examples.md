# Memory Format Examples

The claude-mpm memory system now supports multiple formats for storing agent memories. You can use whichever format best suits your needs.

## Simple Bullet-Point Format (Recommended for Quick Notes)

Create a file at `.claude-mpm/memories/PM_memories.md` with simple bullets:

```markdown
- This project uses Python 3.11 with strict type checking
- All API endpoints require JWT authentication
- Database queries must use parameterized statements
- Follow PEP 8 style guidelines
- Minimum test coverage is 80%
```

## Sectioned Format (Good for Organized Knowledge)

You can also organize memories into sections:

```markdown
## Code Standards
- Use 4 spaces for indentation
- Maximum line length is 100 characters
- All functions need docstrings

## Architecture Decisions  
- Using FastAPI for the backend
- PostgreSQL for the database
- Redis for caching

## Testing Requirements
- All tests must pass before merging
- Use pytest for testing
- Mock external API calls
```

## Mixed Format (Best of Both Worlds)

You can combine both approaches:

```markdown
- Quick reminder: Deploy only on Tuesdays
- Important: Always backup before migrations

## Development Process
- Create feature branches from main
- Open PR when ready for review
- Squash commits before merging

## Production Notes
- Server restarts every Sunday at 3 AM
- Monitor logs for error spikes

- Another quick note at the end
```

## Memory Aggregation

When you have memories at both user level (`~/.claude-mpm/memories/`) and project level (`./.claude-mpm/memories/`), they are automatically aggregated:

1. **User memories** provide defaults across all projects
2. **Project memories** override or extend user memories
3. **Duplicates** are automatically removed (project takes precedence)
4. **All formats** are supported and can be mixed

## Benefits of the New System

- **Flexibility**: Use sections when you need organization, use bullets for quick notes
- **Simplicity**: No need to create sections if you don't want them
- **Compatibility**: Existing sectioned memories continue to work
- **Deduplication**: Automatic handling of duplicate entries
- **Aggregation**: Seamless merging of user and project memories