# Mermaid Visualization Troubleshooting

This guide helps resolve common issues when using Mermaid diagram generation with the Code Analyzer agent in Claude MPM.

## Quick Diagnostics

### Check System Status

First, verify your system setup:

```bash
# Check Claude MPM version (requires 4.0.25+)
claude-mpm --version

# Check if Code Analyzer agent is available (requires v2.6.0+)
claude-mpm agents list | grep code_analyzer

# Test basic analyze command
claude-mpm analyze --help | grep mermaid
```

### Enable Debug Logging

For detailed troubleshooting information:

```bash
export CLAUDE_MPM_LOG_LEVEL=DEBUG
claude-mpm analyze . --mermaid
```

This provides:
- Service initialization details  
- File discovery and processing steps
- Diagram generation progress
- Error details with stack traces

## Common Issues

### 1. No Diagrams Generated

#### Symptoms
- Command completes successfully
- No diagrams appear in output
- `--save-diagrams` creates empty directory

#### Diagnosis Commands
```bash
# Test with minimal example
echo 'class TestClass: pass' > test.py
claude-mpm analyze test.py --mermaid-types class_hierarchy

# Check if analysis finds code structures
claude-mpm analyze . --format json | grep -E "classes|functions|modules"

# Test different diagram types
claude-mpm analyze . --mermaid-types entry_points
```

#### Common Causes & Solutions

**a) No analyzable code structures**
```bash
# Solution: Check target contains Python files
find . -name "*.py" | head -5

# Solution: Try different diagram types
claude-mpm analyze . --mermaid-types module_deps  # Often works when others don't
```

**b) Analysis scope too narrow**
```bash
# Solution: Remove focus restrictions
claude-mpm analyze . --mermaid  # Without --focus

# Solution: Try broader focus
claude-mpm analyze . --mermaid --focus "main,core,app,src"
```

**c) Dynamic code structures**
```bash
# Solution: Look for static structures
claude-mpm analyze . --mermaid-types class_hierarchy --focus "model,class,service"
```

### 2. Empty or Minimal Diagrams

#### Symptoms  
- Diagrams generated but very simple
- Only one or two nodes
- Missing expected relationships

#### Diagnosis
```bash
# Check analysis depth
claude-mpm analyze . --format json > analysis.json
python3 -c "
import json
with open('analysis.json', 'r') as f:
    data = json.load(f)
print('Modules found:', len(data.get('modules', [])))
print('Classes found:', len(data.get('classes', [])))
print('Functions found:', len(data.get('functions', [])))
"
```

#### Solutions

**a) Increase analysis scope**
```bash
# Analyze larger directory scope
claude-mpm analyze ./src --mermaid  # Instead of single files

# Remove external filtering
claude-mpm analyze . --mermaid  # Let service decide what to include
```

**b) Try different diagram types**
```bash
# Entry points often work for simple projects
claude-mpm analyze . --mermaid-types entry_points

# Module dependencies show file relationships
claude-mpm analyze . --mermaid-types module_deps
```

**c) Focus on specific code patterns**
```bash
# Target object-oriented code
claude-mpm analyze . --mermaid-types class_hierarchy --focus "class"

# Target import relationships  
claude-mpm analyze . --mermaid-types module_deps --focus "import"
```

### 3. Invalid Mermaid Syntax

#### Symptoms
- Diagrams don't render in Mermaid viewers
- Syntax errors in generated .mmd files
- GitHub/GitLab don't display diagrams

#### Diagnosis
```bash
# Validate generated diagrams
npm install -g @mermaid-js/mermaid-cli
mmdc -i diagram.mmd -o test.png

# Check for special characters
grep -n '[^a-zA-Z0-9_\-\. ]' diagram.mmd
```

#### Solutions

**a) Handle special characters**
```bash
# Focus on simpler identifiers
claude-mpm analyze . --mermaid --focus "main,core"  # Avoid complex names

# Regenerate with different focus
claude-mpm analyze . --mermaid --focus "service,manager,handler"
```

**b) Reduce diagram complexity**
```bash
# Limit scope to reduce complexity
claude-mpm analyze ./single_module --mermaid-types class_hierarchy

# Use specific diagram types
claude-mpm analyze . --mermaid-types entry_points  # Usually simpler syntax
```

### 4. Performance Issues

#### Symptoms
- Analysis takes very long (>5 minutes)
- High memory usage
- System becomes unresponsive

#### Immediate Solutions
```bash
# Cancel current analysis
Ctrl+C

# Use focused analysis
claude-mpm analyze . --focus "main,core" --mermaid-types entry_points

# Analyze smaller chunks
claude-mpm analyze ./src/core --mermaid-types class_hierarchy
```

#### Long-term Optimizations
```bash
# Exclude test files and vendor code
claude-mpm analyze ./src --mermaid  # Only production code

# Use specific diagram types
claude-mpm analyze . --mermaid-types module_deps  # Faster than all types

# Incremental analysis
claude-mpm analyze ./new_feature --mermaid --save-diagrams
```

### 5. File Permission Errors

#### Symptoms
```
Error: Cannot create diagram output directory: Permission denied
Error: Failed to save diagram: Permission denied
```

#### Solutions
```bash
# Check current permissions
ls -la ./diagrams

# Use absolute path with write permissions  
claude-mpm analyze . --save-diagrams --diagram-output /tmp/diagrams

# Create directory manually
mkdir -p ./docs/diagrams
chmod 755 ./docs/diagrams
claude-mpm analyze . --save-diagrams --diagram-output ./docs/diagrams

# Use user home directory
claude-mpm analyze . --save-diagrams --diagram-output ~/project-diagrams
```

### 6. Service Initialization Errors

#### Symptoms
```
Error: MermaidGeneratorService initialization failed
Error: Service not available
```

#### Diagnosis
```bash
# Test service directly
python3 -c "
from claude_mpm.services.visualization import MermaidGeneratorService
service = MermaidGeneratorService()
print('Initialization:', service.initialize())
service.shutdown()
"
```

#### Solutions
```bash
# Reinstall Claude MPM
pip install --upgrade claude-mpm

# Clear cache
rm -rf ~/.claude-mpm/cache

# Verify Python version (requires 3.8+)
python3 --version
```

### 7. Agent Not Found

#### Symptoms
```
Error: Code Analyzer agent not found
Error: Agent version too old
```

#### Solutions
```bash
# Check agent availability
claude-mpm agents list | grep code_analyzer

# Deploy latest agent
claude-mpm agents deploy code_analyzer

# Verify agent version
claude-mpm agents view code_analyzer | grep version
# Should show v2.6.0 or higher
```

## Edge Cases

### Very Large Codebases

**Issue**: Analysis fails or takes too long on large projects (1000+ files)

**Solutions**:
```bash
# Analyze by component
claude-mpm analyze ./src/auth --mermaid --save-diagrams
claude-mpm analyze ./src/api --mermaid --save-diagrams
claude-mpm analyze ./src/database --mermaid --save-diagrams

# Use module dependencies for overview
claude-mpm analyze . --mermaid-types module_deps --save-diagrams

# Focus on core architecture
claude-mpm analyze . --focus "main,core,app" --mermaid-types entry_points
```

### Monorepo Projects

**Issue**: Too many unrelated modules in diagrams

**Solutions**:
```bash
# Analyze services separately
for service in services/*/; do
  claude-mpm analyze "$service" --mermaid --save-diagrams \
    --diagram-output "./diagrams/$(basename $service)"
done

# Focus on specific service
claude-mpm analyze ./services/user-service --mermaid --save-diagrams
```

### Dynamic/Runtime Code

**Issue**: Missing relationships in frameworks like Django, Flask

**Solutions**:
```bash
# Focus on static definitions
claude-mpm analyze . --focus "model,view,serializer" --mermaid-types class_hierarchy

# Analyze configuration files  
claude-mpm analyze . --focus "config,settings" --mermaid-types module_deps

# Look for explicit imports
claude-mpm analyze . --focus "import,from" --mermaid-types module_deps
```

### Generated Code

**Issue**: Diagrams include auto-generated files

**Solutions**:
```bash
# Exclude generated directories
claude-mpm analyze ./src --mermaid  # Avoid analyzing ./build, ./dist

# Focus on source code
claude-mpm analyze . --focus "src,app,core" --mermaid

# Analyze specific directories
claude-mpm analyze ./application --mermaid --save-diagrams
```

## Validation and Testing

### Verify Generated Diagrams

```bash
# Test Mermaid syntax
for file in diagrams/*.mmd; do
  echo "Testing $file"
  mmdc -i "$file" -o "${file%.mmd}.png" 2>&1 | grep -E "error|Error" || echo "✓ Valid"
done
```

### Test Different Scenarios

```bash
# Test all diagram types
claude-mpm analyze test_project/ --mermaid-types entry_points --save-diagrams
claude-mpm analyze test_project/ --mermaid-types module_deps --save-diagrams  
claude-mpm analyze test_project/ --mermaid-types class_hierarchy --save-diagrams
claude-mpm analyze test_project/ --mermaid-types call_graph --save-diagrams

# Test output formats
claude-mpm analyze test_project/ --mermaid --format text
claude-mpm analyze test_project/ --mermaid --format json
claude-mpm analyze test_project/ --mermaid --format markdown
```

## Recovery Procedures

### Reset Service State

```bash
# Clear any cached state
rm -rf ~/.claude-mpm/cache/mermaid*

# Restart with clean session  
claude-mpm analyze . --mermaid --no-session
```

### Rebuild Analysis

```bash
# Force fresh analysis
rm -rf ./diagrams/
claude-mpm analyze . --mermaid --save-diagrams --diagram-output ./diagrams

# Verify all diagram types
ls -la ./diagrams/
```

### Service Diagnostic

```bash
# Test service components
python3 << 'EOF'
from claude_mpm.services.visualization import (
    DiagramConfig, 
    DiagramType, 
    MermaidGeneratorService
)

# Test initialization
service = MermaidGeneratorService()
print("Service init:", service.initialize())

# Test configuration
config = DiagramConfig(title="Test", direction="TB")
print("Config created:", config is not None)

# Test diagram types
for dtype in DiagramType:
    print(f"Diagram type {dtype.value}: available")

service.shutdown()
print("Service shutdown: complete")
EOF
```

## Getting Help

### Log Collection

When reporting issues, include:

```bash
# Environment info
claude-mpm --version
python3 --version
uname -a

# Debug logs
export CLAUDE_MPM_LOG_LEVEL=DEBUG
claude-mpm analyze . --mermaid 2>&1 | tee debug.log

# Sample code structure
find . -name "*.py" | head -10
```

### Minimal Reproduction

Create minimal test case:

```python
# test_case.py
class TestClass:
    def __init__(self):
        self.data = []
    
    def process(self):
        return len(self.data)

class SubClass(TestClass):
    pass
```

```bash
# Test with minimal case
claude-mpm analyze test_case.py --mermaid-types class_hierarchy
```

### Support Resources

- **Documentation**: [Mermaid Visualization Guide](../03-features/mermaid-visualization.md)
- **CLI Reference**: [Analyze Command](../../reference/cli/analyze-command.md)
- **Best Practices**: [Code Visualization Guide](../../developer/02-core-components/code-visualization-guide.md)
- **GitHub Issues**: Report bugs with logs and minimal reproduction
- **Community**: GitHub Discussions for questions and tips

## Prevention Tips

### Development Best Practices

1. **Start Small**: Test mermaid generation on small modules first
2. **Use Focus**: Always use `--focus` for large codebases  
3. **Incremental**: Generate diagrams incrementally during development
4. **Validate**: Check generated diagrams with mermaid-cli
5. **Version Control**: Track diagrams to see architectural evolution

### CI/CD Integration

```yaml
# .github/workflows/diagrams.yml
name: Generate Diagrams
on: [push]
jobs:
  diagrams:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Generate Architecture Diagrams
        run: |
          # Test first with basic diagram
          claude-mpm analyze . --mermaid-types entry_points --save-diagrams || echo "Entry points failed"
          
          # Then try more complex diagrams
          claude-mpm analyze . --mermaid-types module_deps --save-diagrams || echo "Module deps failed"
          
          # Only commit if successful
          if [ -n "$(ls -A diagrams/ 2>/dev/null)" ]; then
            git add diagrams/
            git commit -m "Update diagrams" || true
          fi
```

This troubleshooting guide should help you resolve most issues with Mermaid diagram generation. Remember to start with simple test cases and gradually increase complexity to isolate problems.