# Memory Builder Service

## Overview

The Memory Builder service (`src/claude_mpm/services/memory/builder.py`) is responsible for processing documentation and generating memory content for agents. It transforms raw documentation into structured memories that agents can use for learning and decision-making.

## Purpose

**WHY**: Agents need contextual knowledge about projects to make informed decisions. The Memory Builder processes various documentation sources to create agent-specific memories that enhance their capabilities.

**DESIGN DECISION**: Uses template-based generation rather than AI processing to ensure consistent, predictable memory generation that can be version-controlled and debugged.

## Key Responsibilities

1. **Documentation Processing**: Parse and analyze project documentation
2. **Memory Generation**: Create agent-specific memory content
3. **Context Integration**: Incorporate project context into memories
4. **Template Management**: Apply memory templates for consistency

## API Reference

### MemoryBuilder Class

```python
from claude_mpm.services.memory.builder import MemoryBuilder

# Initialize with configuration
builder = MemoryBuilder(config, working_directory)

# Build memory from documentation
memory_content = builder.build_memory_from_docs(
    agent_id="engineer",
    doc_files=["README.md", "ARCHITECTURE.md"],
    project_context=context
)

# Process specific documentation
processed = builder.process_documentation(
    content="Implementation guide content...",
    doc_type="implementation"
)
```

### Key Methods

#### `build_memory_from_docs(agent_id, doc_files, project_context)`
Builds comprehensive memory content from documentation files.

**Parameters:**
- `agent_id`: Target agent identifier
- `doc_files`: List of documentation file paths
- `project_context`: Project characteristics and context

**Returns:** Generated memory content string

#### `process_documentation(content, doc_type)`
Processes raw documentation content based on type.

**Parameters:**
- `content`: Raw documentation text
- `doc_type`: Type of documentation (e.g., "api", "implementation", "architecture")

**Returns:** Processed documentation suitable for memory storage

#### `apply_memory_template(agent_id, raw_content)`
Applies agent-specific templates to raw content.

**Parameters:**
- `agent_id`: Target agent identifier
- `raw_content`: Unformatted memory content

**Returns:** Formatted memory content with appropriate structure

## Memory Generation Process

1. **Documentation Discovery**: Identify relevant documentation files
2. **Content Extraction**: Parse and extract key information
3. **Context Analysis**: Analyze project characteristics
4. **Template Application**: Apply agent-specific formatting
5. **Optimization**: Compress and optimize for storage

## Supported Documentation Types

- **README Files**: Project overview and setup instructions
- **Architecture Docs**: System design and structure
- **API Documentation**: Endpoint and interface specifications
- **Configuration Docs**: Settings and environment setup
- **Development Guides**: Coding standards and practices

## Integration Examples

### Building Memory from Project Docs

```python
# Analyze project for documentation
doc_files = project_analyzer.find_documentation_files()

# Build memory for engineer agent
engineer_memory = builder.build_memory_from_docs(
    agent_id="engineer",
    doc_files=doc_files,
    project_context=project_analyzer.get_context()
)

# Save to memory system
memory_manager.save_memory("engineer", engineer_memory)
```

### Processing Custom Documentation

```python
# Process architecture documentation
arch_content = read_file("ARCHITECTURE.md")
processed = builder.process_documentation(
    content=arch_content,
    doc_type="architecture"
)

# Add to existing memory
memory_manager.update_agent_memory(
    "engineer",
    "Architecture Patterns",
    processed
)
```

## Best Practices

1. **Incremental Building**: Build memories incrementally as documentation changes
2. **Context Awareness**: Always provide project context for accurate generation
3. **Template Consistency**: Use standardized templates for predictable output
4. **Size Management**: Monitor generated memory sizes and optimize as needed
5. **Validation**: Validate generated memories before storage

## Performance Considerations

- **Caching**: Cache processed documentation to avoid redundant processing
- **Batch Processing**: Process multiple documents together for efficiency
- **Lazy Loading**: Load documentation on-demand rather than eagerly
- **Compression**: Compress large memory blocks for storage efficiency

## Error Handling

The Memory Builder handles various error conditions:

- **Missing Documentation**: Gracefully handles missing or empty files
- **Invalid Format**: Validates documentation format before processing
- **Template Errors**: Falls back to default templates on errors
- **Size Limits**: Enforces maximum memory size constraints

## Testing

Unit tests for the Memory Builder are located in:
- `tests/services/test_memory_builder.py`

Integration tests:
- `tests/integration/test_memory_building.py`

## Related Services

- [Memory Router](router.md) - Routes memory commands to agents
- [Memory Optimizer](optimizer.md) - Optimizes generated memories
- [Project Analyzer](../02-core-components/memory-system.md#projectanalyzer) - Provides project context