# Claude MPM PDF Documentation

This directory contains PDF versions of the Claude Multi-Agent Project Manager documentation.

## Available PDFs

### User Documentation
- **claude-mpm-user-guide.pdf** (176KB) - Complete user guide with all features and workflows
- **getting-started.pdf** (50KB) - Quick start guide for new users

### Developer Documentation
- **architecture.pdf** (70KB) - System architecture and design overview
- **api-reference.pdf** (64KB) - API documentation and reference

### Agent Documentation
- **creating-agents.pdf** (81KB) - Guide to creating custom agents
- **agent-patterns.pdf** (61KB) - Best practices and patterns for agent development

## Generation

These PDFs were generated using:
1. **pandoc** - Markdown to HTML conversion with table of contents
2. **weasyprint** - HTML to PDF rendering

All PDFs include:
- Table of contents
- Proper formatting and styling
- Code syntax highlighting
- Professional layout

## Regeneration

To regenerate the PDFs:

```bash
# Install dependencies
brew install pandoc
pip3 install weasyprint

# Create output directory
mkdir -p docs/pdf

# Convert markdown to HTML
pandoc docs/user/user-guide.md -o docs/pdf/claude-mpm-user-guide.html --toc --toc-depth=3 --standalone --embed-resources

# Convert HTML to PDF
weasyprint docs/pdf/claude-mpm-user-guide.html docs/pdf/claude-mpm-user-guide.pdf

# Clean up intermediate files
rm docs/pdf/*.html
```

## File Sizes

All PDFs are optimized and kept under 200KB for easy distribution and viewing.

---

Generated on: October 28, 2025
