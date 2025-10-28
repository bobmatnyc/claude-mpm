# Skills Selector - Quick Start Guide

## 🚀 Quick Start

### Step 1: Access Skills Management

```bash
claude-mpm configure
```

Select option **[2] Skills Management**

### Step 2: Choose an Operation

```
[1] View Available Skills     - See all 15 bundled skills
[2] Configure Skills           - Customize skills per agent
[3] View Current Mappings      - See what's configured
[4] Auto-Link Skills           - Let MPM decide (recommended)
```

### Step 3: Auto-Link (Recommended)

For most users, option **[4] Auto-Link Skills to Agents** is the best choice:

1. Automatically assigns skills based on agent types
2. Provides intelligent defaults
3. Can be customized later

## 📋 Available Skills (15 Total)

### Engineering Skills
- `test-driven-development` - TDD practices and patterns
- `systematic-debugging` - Debug-first methodology
- `async-testing` - Async/await test patterns
- `code-review` - Code review best practices
- `refactoring-patterns` - Refactoring techniques
- `git-workflow` - Git branching and workflows

### Operations Skills
- `docker-containerization` - Docker best practices
- `database-migration` - Schema migration patterns
- `security-scanning` - OWASP and security checks

### Performance & Analysis
- `performance-profiling` - Profiling and optimization

### Documentation
- `api-documentation` - API docs and OpenAPI

### Data Processing
- `imagemagick` - Image processing
- `json-data-handling` - JSON manipulation
- `pdf` - PDF processing
- `xlsx` - Excel file handling

## 🔗 Auto-Linking Examples

### Python Engineer
**Auto-linked skills:**
- test-driven-development
- systematic-debugging
- code-review
- refactoring-patterns
- git-workflow
- async-testing

### React Engineer
**Auto-linked skills:**
- test-driven-development
- systematic-debugging
- code-review
- refactoring-patterns
- git-workflow
- async-testing
- performance-profiling

### Ops Agent
**Auto-linked skills:**
- docker-containerization
- database-migration
- security-scanning
- systematic-debugging

### QA Agent
**Auto-linked skills:**
- test-driven-development
- systematic-debugging
- async-testing
- performance-profiling

## 🎯 Custom Skills

### Add Your Own Skills

1. Create a `.claude/skills/` directory in your project or home directory
2. Add `.md` files with your custom skills
3. Restart `claude-mpm` to auto-discover

**Example:**

```bash
mkdir -p .claude/skills
cat > .claude/skills/my-custom-skill.md << 'EOF'
# My Custom Skill

Description of what this skill provides.

## Usage
How to use this skill...

## Examples
Examples of using this skill...
EOF
```

### Auto-Discovery

Skills in `.claude/skills/` are automatically:
- Discovered at startup
- Linked to appropriate agents based on content
- Available immediately without restart

## 🔧 Configuration File

Skills mappings are saved to:
```
.claude-mpm/skills_config.json
```

Example format:
```json
{
  "python-engineer": [
    "test-driven-development",
    "systematic-debugging",
    "async-testing"
  ],
  "qa": [
    "test-driven-development",
    "systematic-debugging",
    "async-testing",
    "performance-profiling"
  ]
}
```

## 💡 Tips

1. **Start with Auto-Link** - Let MPM configure skills automatically first
2. **Customize Later** - Use option [2] to fine-tune selections
3. **Check Mappings** - Use option [3] to review current configuration
4. **Add Custom Skills** - Place .md files in `.claude/skills/` for project-specific skills
5. **Version Control** - Add `skills_config.json` to git for team consistency

## 🐛 Troubleshooting

### Skills not showing up?
```bash
# Check bundled skills are loaded
python -c "from src.claude_mpm.skills.registry import get_registry; print(len(get_registry().list_skills(source='bundled')))"
```

### Custom skills not discovered?
- Ensure `.md` extension is used
- Check directory is `.claude/skills/` not `.claude/skill/`
- Restart `claude-mpm` after adding skills

### Configuration not persisting?
- Ensure `.claude-mpm/` directory exists
- Check write permissions
- Verify you're saving changes in configurator

## 📚 Related Commands

```bash
# Open configurator
claude-mpm configure

# View agent configuration
claude-mpm agents list

# Check current configuration
cat .claude-mpm/skills_config.json

# View bundled skills
ls src/claude_mpm/skills/bundled/
```

## 🎓 Learning Path

1. ✅ **Auto-link skills** (2 min) - Get started quickly
2. ✅ **View available skills** (5 min) - Explore what's available
3. ✅ **Check mappings** (2 min) - See what's configured
4. ✅ **Customize** (10 min) - Fine-tune for your needs
5. ✅ **Add custom skills** (15 min) - Create project-specific skills

---

**Need help?** Open an issue or check the full documentation in `SKILLS_SELECTOR_INTEGRATION.md`
