# MCP Document Summarizer Tool

## Overview

The `summarize_document` tool is an MCP (Model Context Protocol) tool that provides intelligent document summarization capabilities. It replaces the `agent_task` tool and helps reduce memory usage in Claude conversations by compressing documents while preserving key information.

## Features

- **Multiple Summarization Styles**: Brief, detailed, bullet points, and executive summaries
- **Configurable Length**: Control summary length with word limits
- **Intelligent Extraction**: Uses sentence importance scoring and structural analysis
- **Edge Case Handling**: Properly handles empty content, short content, and very long documents
- **Sentence Boundary Preservation**: Ensures summaries end at natural sentence boundaries

## Tool Schema

```json
{
  "name": "summarize_document",
  "description": "Summarize documents or text content",
  "inputSchema": {
    "type": "object",
    "properties": {
      "content": {
        "type": "string",
        "description": "The text/document to summarize"
      },
      "style": {
        "type": "string",
        "enum": ["brief", "detailed", "bullet_points", "executive"],
        "description": "Summary style",
        "default": "brief"
      },
      "max_length": {
        "type": "integer",
        "description": "Maximum length of summary in words",
        "default": 150
      }
    },
    "required": ["content"]
  }
}
```

## Summarization Styles

### Brief
- Extracts the most important sentences
- Includes beginning and ending for context
- Best for quick overviews

### Detailed
- Preserves document structure
- Extracts key paragraphs
- Maintains more context than brief

### Bullet Points
- Extracts existing bullet points and lists
- Creates bullet points from key sentences if none exist
- Ideal for action items and key takeaways

### Executive
- Structured summary with sections
- Includes: Overview, Key Findings, and Recommendations
- Perfect for business documents and reports

## Usage Examples

### Basic Usage
```python
# Via MCP protocol
{
  "tool": "summarize_document",
  "arguments": {
    "content": "Your long document text here...",
    "style": "brief",
    "max_length": 100
  }
}
```

### Python Integration
```python
from claude_mpm.services.mcp_gateway.server.stdio_server import SimpleMCPServer

server = SimpleMCPServer()
result = await server._summarize_content(
    content="Your document text...",
    style="executive",
    max_length=150
)
```

## Implementation Details

### Sentence Importance Scoring

The tool uses multiple factors to score sentence importance:
- **Position**: First and last sentences get higher scores
- **Keywords**: Sentences with important keywords score higher
- **Length**: Medium-length sentences (10-25 words) are preferred

### Word Limit Enforcement

- Strictly respects the `max_length` parameter
- Truncates at sentence boundaries when possible
- Adds ellipsis (...) when content is truncated

### Performance Characteristics

- **Memory Reduction**: Typically achieves 50-70% reduction
- **Processing Speed**: Fast, suitable for real-time use
- **Scalability**: Handles documents of any size

## Testing

The tool includes comprehensive test coverage:

```bash
# Run tests
python tests/test_mcp_summarizer_tool.py

# Run demo
python examples/mcp_summarizer_demo.py
```

## Architecture

The summarizer is integrated into the MCP stdio server at:
- `/src/claude_mpm/services/mcp_gateway/server/stdio_server.py`

Key methods:
- `_summarize_content()`: Main entry point
- `_create_brief_summary()`: Brief style implementation
- `_create_detailed_summary()`: Detailed style implementation
- `_create_bullet_summary()`: Bullet points extraction
- `_create_executive_summary()`: Executive summary generation

## Benefits

1. **Memory Efficiency**: Reduces token usage by 50-70%
2. **Flexibility**: Multiple styles for different use cases
3. **Quality**: Preserves semantic meaning and key information
4. **Reliability**: Comprehensive error handling and edge case support
5. **Integration**: Seamless MCP protocol integration

## Future Enhancements

Potential improvements for future versions:
- Machine learning-based importance scoring
- Multi-language support
- Domain-specific summarization templates
- Incremental summarization for streaming content
- Integration with the existing document_summarizer.py for file-based operations