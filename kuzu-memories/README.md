# 🧠 Project Memories - claude-mpm

This directory contains the KuzuMemory database for the **claude-mpm** project.

## 📁 What's Here

- **`memories.db`** - Kuzu graph database containing project memories
- **`project_info.md`** - Project context and documentation
- **`.gitignore`** - Git ignore rules for temporary files

## 🎯 Purpose

This memory database stores:
- **Project context** - Architecture, decisions, patterns
- **Team knowledge** - Preferences, conventions, best practices
- **Development history** - Solutions, learnings, gotchas
- **AI context** - Information for enhanced AI assistance

## 🔄 Git Integration

**✅ COMMIT THIS DIRECTORY TO GIT**

The memories database should be committed to your repository so that:
- All team members share the same project context
- AI assistants have consistent project knowledge
- Project memory persists across environments
- New team members get instant project context

## 🚀 Usage

### Store Project Memories
```bash
# Store project information
kuzu-memory remember "We use FastAPI with PostgreSQL for this microservice"

# Store architectural decisions
kuzu-memory remember "We decided to use Redis for caching to improve API response times"

# Store team conventions
kuzu-memory remember "All API endpoints should include request/response examples in docstrings"
```

### Recall Project Context
```bash
# Get relevant project context
kuzu-memory recall "How is the database configured?"

# Find architectural decisions
kuzu-memory recall "What caching strategy do we use?"

# Get AI-enhanced responses
kuzu-memory auggie enhance "How should I structure this API endpoint?"
```

### Project Statistics
```bash
# View memory statistics
kuzu-memory stats

# See project memory summary
kuzu-memory project-info
```

## 🤖 AI Integration

When using AI assistants (like Auggie), the memories in this database automatically enhance prompts with relevant project context, making AI responses more accurate and project-specific.

## 📊 Database Info

- **Type**: Kuzu Graph Database
- **Schema**: Optimized for memory relationships and fast retrieval
- **Performance**: Sub-10ms memory recall for real-time AI integration
- **Size**: Typically 1-10MB for most projects

## 🆘 Troubleshooting

### Database Issues
```bash
# Check database health
kuzu-memory stats

# Reinitialize if corrupted
kuzu-memory init --force
```

### Performance Issues
```bash
# Optimize database
kuzu-memory optimize

# Clean up old memories
kuzu-memory cleanup
```

---

**This directory is managed by KuzuMemory v1.0.0**
Generated on: 1759199065.2696857
