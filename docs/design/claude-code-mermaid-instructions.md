# Claude Code Instructions: Add Mermaid Diagramming to Code Analyst Agent

## Overview

Enhance the existing Code Analyzer Agent in Claude MPM to generate Mermaid diagrams showing relationships between entry points, files, and functions. This builds on the existing tree-sitter integration and follows the established service-oriented architecture.

## Current State Analysis

The project already has:
- ✅ Code Analyzer Agent (released in v3.7.1)
- ✅ Tree-sitter integration (TreeSitterAnalyzer class)
- ✅ Existing mermaid diagrams in documentation
- ✅ Agent registry and deployment system
- ✅ Service-oriented architecture patterns

## Implementation Plan

### Step 1: Enhance TreeSitterAnalyzer Service

**File**: `src/claude_mpm/services/agent_modification_tracker/tree_sitter_analyzer.py`

Add mermaid generation capabilities to the existing TreeSitterAnalyzer:

```python
def generate_entry_point_diagram(self, analysis_results: Dict) -> str:
    """Generate Mermaid diagram showing entry points -> files -> functions"""
    mermaid_lines = ["graph TD"]
    
    # Process entry points from existing analysis
    entry_points = analysis_results.get('entry_points', [])
    functions = analysis_results.get('functions', [])
    
    for entry_point in entry_points:
        ep_name = self._sanitize_mermaid_id(entry_point['file'])
        mermaid_lines.append(f"    EP_{ep_name}[{entry_point['name']}] --> FILE_{ep_name}")
        
        # Map entry point to its functions
        for func in functions:
            if func['file'] == entry_point['file']:
                func_id = self._sanitize_mermaid_id(f"{func['file']}_{func['name']}")
                mermaid_lines.append(f"    FILE_{ep_name} --> FUNC_{func_id}[{func['name']}()]")
    
    return "\n".join(mermaid_lines)

def generate_module_dependency_diagram(self, analysis_results: Dict) -> str:
    """Generate Mermaid diagram showing module dependencies"""
    # Implementation based on existing dependency analysis
    pass

def generate_class_hierarchy_diagram(self, analysis_results: Dict) -> str:
    """Generate Mermaid diagram showing class inheritance"""
    # Implementation based on existing class analysis
    pass

def _sanitize_mermaid_id(self, text: str) -> str:
    """Sanitize text for use as Mermaid node ID"""
    import re
    return re.sub(r'[^\w]', '_', text).strip('_')
```

### Step 2: Create Mermaid Generation Service

**File**: `src/claude_mpm/services/visualization/mermaid_generator.py`

```python
from enum import Enum
from typing import Dict, List, Optional
from claude_mpm.core.base_service import EnhancedBaseService

class DiagramType(Enum):
    ENTRY_POINTS = "entry_points"
    MODULE_DEPS = "module_deps"  
    CLASS_HIERARCHY = "class_hierarchy"
    CALL_GRAPH = "call_graph"

class MermaidGeneratorService(EnhancedBaseService):
    """Service for generating Mermaid diagrams from code analysis"""
    
    def __init__(self):
        super().__init__()
        self._diagram_generators = {
            DiagramType.ENTRY_POINTS: self._generate_entry_points_diagram,
            DiagramType.MODULE_DEPS: self._generate_module_deps_diagram,
            DiagramType.CLASS_HIERARCHY: self._generate_class_hierarchy_diagram,
            DiagramType.CALL_GRAPH: self._generate_call_graph_diagram
        }
    
    async def generate_diagram(
        self, 
        analysis_results: Dict, 
        diagram_type: DiagramType,
        title: Optional[str] = None
    ) -> str:
        """Generate Mermaid diagram of specified type"""
        generator = self._diagram_generators.get(diagram_type)
        if not generator:
            raise ValueError(f"Unsupported diagram type: {diagram_type}")
        
        mermaid_content = generator(analysis_results)
        
        if title:
            mermaid_content = f"---\ntitle: {title}\n---\n{mermaid_content}"
        
        return mermaid_content
    
    def _generate_entry_points_diagram(self, analysis_results: Dict) -> str:
        """Generate entry points -> files -> functions diagram"""
        # Implementation here
        pass
    
    # Additional generator methods...
```

### Step 3: Enhance Code Analyzer Agent Instructions

**File**: `src/claude_mpm/agents/templates/code_analyzer_agent.md`

Add mermaid generation capabilities to the agent instructions:

```markdown
## Enhanced Capabilities

### Mermaid Diagram Generation

You can now generate visual diagrams to complement your code analysis:

**Available Diagram Types:**
- `entry_points`: Shows entry points → files → functions relationships  
- `module_deps`: Displays module dependency graphs
- `class_hierarchy`: Shows class inheritance and composition
- `call_graph`: Maps function call relationships

**Mermaid Generation Commands:**
```python
from claude_mpm.services.visualization.mermaid_generator import MermaidGeneratorService, DiagramType

# Generate entry points diagram
generator = MermaidGeneratorService()
mermaid_content = await generator.generate_diagram(
    analysis_results, 
    DiagramType.ENTRY_POINTS,
    title="Entry Points Analysis"
)

# Save diagram to file
with open("entry_points_diagram.mmd", "w") as f:
    f.write(mermaid_content)
```

**When to Generate Diagrams:**
- User requests "show relationships", "visualize", "diagram" 
- Complex codebases with multiple entry points
- Architecture analysis requests
- Documentation generation tasks

**Output Format:**
Always provide both the analysis text AND the mermaid diagram code in separate code blocks.
```

### Step 4: Update Agent Schema Configuration

**File**: `src/claude_mpm/agents/templates/code_analyzer_agent.json` (if exists)

```json
{
  "capabilities": {
    "unique_capabilities": [
      "Generate comprehensive code quality reports with AST analysis",
      "Create visual Mermaid diagrams showing code relationships", 
      "Produce entry point → function flow diagrams",
      "Generate module dependency visualizations",
      "Create class hierarchy and inheritance diagrams"
    ]
  },
  "configuration": {
    "tools": ["Read", "Write", "Grep", "Glob", "LS", "WebSearch", "WebFetch", "TodoWrite"],
    "dependencies": [
      "tree-sitter>=0.21.0",
      "tree-sitter-language-pack>=0.8.0"
    ]
  }
}
```

### Step 5: Add CLI Support for Mermaid Generation

**File**: `src/claude_mpm/cli/commands/analyze.py` (new command)

```python
async def analyze_command(args):
    """Handle code analysis with optional mermaid generation"""
    
    if args.mermaid:
        # Generate analysis + mermaid diagrams
        prompt = f"""
        Analyze the codebase and generate both a comprehensive report and Mermaid diagrams showing:
        1. Entry points to functions relationships
        2. Module dependencies  
        3. Class hierarchies (if applicable)
        
        Target: {args.target or '.'}
        Diagram types requested: {', '.join(args.mermaid_types or ['entry_points'])}
        """
        
        result = await claude_session.run_with_agent(
            agent_name="code_analyzer", 
            prompt=prompt
        )
        
        # Parse and save any mermaid diagrams found in response
        save_mermaid_diagrams(result)
    else:
        # Standard analysis without diagrams
        pass

def save_mermaid_diagrams(response_text: str):
    """Extract and save mermaid diagrams from agent response"""
    import re
    
    # Find mermaid code blocks
    mermaid_pattern = r'```mermaid\n(.*?)\n```'
    diagrams = re.findall(mermaid_pattern, response_text, re.DOTALL)
    
    for i, diagram in enumerate(diagrams):
        filename = f"analysis_diagram_{i+1}.mmd"
        with open(filename, 'w') as f:
            f.write(diagram.strip())
        print(f"Saved diagram: {filename}")
```

**Update**: `src/claude_mpm/cli/parser.py`

```python
# Add analyze subcommand
analyze_parser = subparsers.add_parser('analyze', help='Analyze codebase with optional mermaid diagrams')
analyze_parser.add_argument('--mermaid', action='store_true', help='Generate mermaid diagrams')
analyze_parser.add_argument('--mermaid-types', nargs='+', 
                           choices=['entry_points', 'module_deps', 'class_hierarchy', 'call_graph'],
                           default=['entry_points'],
                           help='Types of diagrams to generate')
analyze_parser.add_argument('--target', help='Target directory/file to analyze', default='.')
```

## Usage Examples

### CLI Usage

```bash
# Standard analysis with entry points diagram
claude-mpm analyze --mermaid

# Multiple diagram types
claude-mpm analyze --mermaid --mermaid-types entry_points module_deps class_hierarchy

# Analyze specific directory
claude-mpm analyze --target src/ --mermaid
```

### Interactive Usage

```bash
# Start interactive session with code analyzer
claude-mpm run -a code_analyzer

# Then prompt with:
"Analyze this codebase and create a Mermaid diagram showing how the entry points connect to the main functions. Focus on the CLI entry points and their function call chains."
```

### Expected Output

The enhanced agent will generate responses like:

```markdown
# Code Analysis Report

## Entry Points Analysis
- Found 4 entry points: cli_main.py, cli.py, __main__.py, test_cli.py
- Main execution flows through SubprocessOrchestrator
- 1,349 total functions analyzed

## Mermaid Diagram: Entry Points → Functions

```mermaid
graph TD
    EP_cli_main[CLI Main] --> FILE_cli_main
    EP_cli[CLI Interface] --> FILE_cli
    EP_main[Module Main] --> FILE_main
    EP_test_cli[Test CLI] --> FILE_test_cli
    
    FILE_cli_main --> FUNC_main_run_session[run_session()]
    FILE_cli_main --> FUNC_main_handle_args[handle_args()]
    
    FUNC_main_run_session --> FUNC_orchestrator_start[start_orchestrator()]
    FUNC_main_run_session --> FUNC_hooks_initialize[initialize_hooks()]
```

## Key Functions by Entry Point
...rest of analysis...
```

## Testing the Implementation

### Unit Tests

**File**: `tests/unit/test_mermaid_generator.py`

```python
import pytest
from claude_mpm.services.visualization.mermaid_generator import MermaidGeneratorService, DiagramType

@pytest.mark.asyncio
async def test_entry_points_diagram_generation():
    generator = MermaidGeneratorService()
    
    # Mock analysis results
    analysis_results = {
        'entry_points': [
            {'name': 'CLI Main', 'file': 'cli_main.py'},
            {'name': 'CLI', 'file': 'cli.py'}
        ],
        'functions': [
            {'name': 'main', 'file': 'cli_main.py'},
            {'name': 'run_session', 'file': 'cli_main.py'}
        ]
    }
    
    diagram = await generator.generate_diagram(
        analysis_results, 
        DiagramType.ENTRY_POINTS
    )
    
    assert 'graph TD' in diagram
    assert 'EP_cli_main' in diagram
    assert 'FUNC_main' in diagram
```

### Integration Test

```bash
# Test the full pipeline
claude-mpm analyze --mermaid --target tests/fixtures/sample_project/
```

## Migration Notes

- This enhancement is **additive** - existing code analysis functionality remains unchanged
- New mermaid generation is **optional** - triggered only when requested  
- Follows existing **service patterns** - uses EnhancedBaseService base class
- Compatible with **current agent system** - extends existing code_analyzer agent
- **Backward compatible** - all existing commands work exactly as before

## Success Criteria

✅ **Generated diagrams accurately represent code structure**  
✅ **Integration with existing tree-sitter analysis**  
✅ **CLI support for generating diagrams**  
✅ **Agent can respond to diagram requests**  
✅ **Follows established architectural patterns**  
✅ **Comprehensive test coverage**

The enhanced Code Analyzer Agent will provide powerful visualization capabilities while maintaining the robust analysis features that already exist in Claude MPM.