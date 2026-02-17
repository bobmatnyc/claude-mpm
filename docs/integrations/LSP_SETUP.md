# MCP LSP Setup Guide

Enable Language Server Protocol (LSP) integration for Claude Code, providing code intelligence features like go-to-definition, find references, hover documentation, and more.

## Overview

The `mcp-lsp` server bridges LSP capabilities to Claude Code via MCP, enabling 40+ code intelligence tools.

### Features

| Category | Tools |
|----------|-------|
| **Navigation** | Go to definition, find references, implementations, type hierarchy |
| **Analysis** | Hover docs, completions, signatures, diagnostics |
| **Refactoring** | Code actions, formatting, rename symbols |
| **Workspace** | Symbol search, document outline, call graphs |

### Supported Languages

Any language with an LSP server: TypeScript, Python, Go, Rust, Java, C#, Kotlin, etc.

## Prerequisites

- Node.js 18+
- Language servers installed for your languages (e.g., `typescript-language-server`, `pyright`, `gopls`)

## Step 1: Install Language Servers

Install the language servers you need:

```bash
# TypeScript/JavaScript
npm install -g typescript-language-server typescript

# Python
pip install pyright
# or
pip install python-lsp-server

# Go
go install golang.org/x/tools/gopls@latest

# Rust
rustup component add rust-analyzer
```

## Step 2: Create LSP Configuration

Create `lsp.json` in your project or home directory:

```json
{
  "servers": {
    "typescript": {
      "command": "typescript-language-server",
      "args": ["--stdio"],
      "extensions": [".ts", ".tsx", ".js", ".jsx"],
      "projects": ["/path/to/your/project"]
    },
    "python": {
      "command": "pyright-langserver",
      "args": ["--stdio"],
      "extensions": [".py"],
      "projects": ["/path/to/your/project"]
    },
    "go": {
      "command": "gopls",
      "args": ["serve"],
      "extensions": [".go"],
      "projects": ["/path/to/your/project"]
    }
  }
}
```

## Step 3: Configure Environment

Add to `.env.local` (or export):

```bash
LSP_FILE_PATH=/path/to/lsp.json
```

## Step 4: Add to Claude Code

Use the `claude mcp add` command:

```bash
claude mcp add -e LSP_FILE_PATH=/path/to/lsp.json mcp-lsp -- npx -y @axivo/mcp-lsp
```

Or for project-specific configuration, add to `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "mcp-lsp": {
      "command": "npx",
      "args": ["-y", "@axivo/mcp-lsp"],
      "env": {
        "LSP_FILE_PATH": "/path/to/lsp.json"
      }
    }
  }
}
```

Verify it's configured:

```bash
claude mcp list
```

## Available Tools

Once configured, these tools become available:

### Navigation
- `lsp_goto_definition` - Jump to symbol definition
- `lsp_find_references` - Find all references to a symbol
- `lsp_goto_implementation` - Jump to interface implementations
- `lsp_goto_type_definition` - Jump to type definition
- `lsp_call_hierarchy` - Show incoming/outgoing calls

### Analysis
- `lsp_hover` - Get documentation for symbol under cursor
- `lsp_completion` - Get code completions
- `lsp_signature_help` - Get function signature help
- `lsp_diagnostics` - Get errors and warnings
- `lsp_document_symbols` - List symbols in document
- `lsp_workspace_symbols` - Search symbols across workspace

### Refactoring
- `lsp_code_action` - Get available code actions/fixes
- `lsp_format` - Format document
- `lsp_rename` - Rename symbol across codebase

## Example Usage

Once configured, Claude can use LSP tools naturally:

```
User: "Find all references to the `UserService` class"
Claude: [uses lsp_find_references]

User: "What does the `authenticate` function do?"
Claude: [uses lsp_hover to get documentation]

User: "Rename `getData` to `fetchUserData` across the codebase"
Claude: [uses lsp_rename]
```

## Troubleshooting

### "Language server not found"
Ensure the language server binary is in your PATH:
```bash
which typescript-language-server
which pyright-langserver
which gopls
```

### "No projects configured"
Update `lsp.json` with correct project paths that contain the source files.

### Server not starting
Check MCP debug output:
```bash
claude --debug mcp
```

## See Also

- [@axivo/mcp-lsp on npm](https://www.npmjs.com/package/@axivo/mcp-lsp)
- [LSP Specification](https://microsoft.github.io/language-server-protocol/)
