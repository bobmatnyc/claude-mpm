# Hierarchical BASE-AGENT.md Example

This directory demonstrates the hierarchical BASE-AGENT.md template inheritance feature.

## Directory Structure

```
examples/hierarchical-base-agents/
├── README.md
├── BASE-AGENT.md                    # Root: Company-wide standards
└── engineering/
    ├── BASE-AGENT.md                # Engineering principles
    ├── python/
    │   ├── BASE-AGENT.md            # Python guidelines
    │   ├── backend/
    │   │   ├── BASE-AGENT.md        # Backend best practices
    │   │   └── fastapi-engineer.md  # Specific agent
    │   └── ml/
    │       ├── BASE-AGENT.md        # ML guidelines
    │       └── pytorch-engineer.md  # Specific agent
    └── javascript/
        ├── BASE-AGENT.md            # JavaScript guidelines
        └── react-engineer.md        # Specific agent
```

## Composition Examples

### FastAPI Engineer (4 levels)

**Deployed content will include:**
1. `fastapi-engineer.md` content (most specific)
2. `engineering/python/backend/BASE-AGENT.md`
3. `engineering/python/BASE-AGENT.md`
4. `engineering/BASE-AGENT.md`
5. `BASE-AGENT.md` (most general)

### PyTorch Engineer (4 levels)

**Deployed content will include:**
1. `pytorch-engineer.md` content (most specific)
2. `engineering/python/ml/BASE-AGENT.md`
3. `engineering/python/BASE-AGENT.md`
4. `engineering/BASE-AGENT.md`
5. `BASE-AGENT.md` (most general)

### React Engineer (3 levels)

**Deployed content will include:**
1. `react-engineer.md` content (most specific)
2. `engineering/javascript/BASE-AGENT.md`
3. `engineering/BASE-AGENT.md`
4. `BASE-AGENT.md` (most general)

## Testing This Example

### 1. Deploy Agents

```bash
# Deploy all agents from this example
cd /path/to/claude-mpm/examples/hierarchical-base-agents

# Deploy FastAPI engineer
claude-mpm agents deploy fastapi-engineer --templates-dir=engineering/python/backend --force

# Deploy PyTorch engineer
claude-mpm agents deploy pytorch-engineer --templates-dir=engineering/python/ml --force

# Deploy React engineer
claude-mpm agents deploy react-engineer --templates-dir=engineering/javascript --force
```

### 2. Verify Composition

```bash
# Check deployed FastAPI engineer
cat ~/.claude/agents/fastapi-engineer.md

# Should contain sections in this order:
# 1. FastAPI-specific instructions
# 2. Backend best practices
# 3. Python guidelines
# 4. Engineering principles
# 5. Company standards

# Verify sections are separated by ---
grep -c "^---$" ~/.claude/agents/fastapi-engineer.md
# Should output: at least 4 (separators between sections)
```

### 3. Verify Content

```bash
# FastAPI should have backend-specific content
grep "Backend Best Practices" ~/.claude/agents/fastapi-engineer.md

# PyTorch should have ML-specific content
grep "Machine Learning Guidelines" ~/.claude/agents/pytorch-engineer.md

# Both Python agents should have Python guidelines
grep "Python Guidelines" ~/.claude/agents/fastapi-engineer.md
grep "Python Guidelines" ~/.claude/agents/pytorch-engineer.md

# All agents should have company standards
grep "Company Standards" ~/.claude/agents/fastapi-engineer.md
grep "Company Standards" ~/.claude/agents/pytorch-engineer.md
grep "Company Standards" ~/.claude/agents/react-engineer.md
```

## Key Benefits Demonstrated

### 1. Code Reuse
- Python guidelines shared between FastAPI and PyTorch
- Engineering principles shared across all agents
- Company standards shared across entire organization

### 2. Specialization Layers
- **Company Level:** Universal values and communication
- **Department Level:** Engineering-specific practices
- **Language Level:** Python/JavaScript-specific guidelines
- **Domain Level:** Backend/ML/Frontend-specific practices
- **Agent Level:** Individual specialization

### 3. Maintainability
- Update Python guidelines once, affects all Python agents
- Update engineering principles once, affects all engineers
- Clear separation of concerns at each level

## Customization

### Adding a New Language

```bash
mkdir -p engineering/rust
cat > engineering/rust/BASE-AGENT.md <<EOF
# Rust Guidelines

## Code Style
- Use rustfmt
- Follow Rust API guidelines
- Write comprehensive tests

## Best Practices
- Use cargo for dependencies
- Leverage type system
- Minimize unsafe blocks
EOF
```

### Adding a New Domain

```bash
mkdir -p engineering/python/data-science
cat > engineering/python/data-science/BASE-AGENT.md <<EOF
# Data Science Guidelines

## Best Practices
- Document data assumptions
- Version datasets
- Reproducible experiments

## Tools
- Jupyter notebooks for exploration
- Production-ready scripts for deployment
EOF
```

## Integration with Git Sources

This example structure works seamlessly with Git agent sources:

```bash
# Add this repository as a Git source
claude-mpm agent-source add github \
  --url https://github.com/your-org/agent-templates \
  --subdirectory examples/hierarchical-base-agents \
  --priority 50

# Sync agents
claude-mpm agent-source sync github

# Deploy agents (will use hierarchical composition)
claude-mpm agents deploy fastapi-engineer
```

## Troubleshooting

### Content Not Appearing

**Issue:** Expected BASE content not in deployed agent

**Debug:**
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Deploy with debug output
claude-mpm agents deploy fastapi-engineer --force 2>&1 | grep "BASE-AGENT"

# Look for discovery messages:
# - "Found BASE-AGENT.md at: ..."
# - "Composed BASE template: ..."
```

### Wrong Composition Order

**Issue:** Sections appear in unexpected order

**Verify:**
```bash
# Extract section headers
grep "^#" ~/.claude/agents/fastapi-engineer.md

# Should see progression from specific to general:
# 1. FastAPI-specific headers
# 2. Backend headers
# 3. Python headers
# 4. Engineering headers
# 5. Company headers
```

### Depth Limit Reached

**Issue:** Warning about depth limit in logs

**Solution:**
- Flatten directory structure
- Move agents closer to root
- Maximum 10 levels supported

## See Also

- [Hierarchical BASE-AGENT.md Documentation](../../docs/features/hierarchical-base-agents.md)
- [Agent Template Format](../../docs/reference/agent-template-format.md)
- [Agent Deployment Guide](../../docs/user/agent-deployment.md)
