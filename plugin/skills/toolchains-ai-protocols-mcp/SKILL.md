---
name: mcp
description: MCP (Model Context Protocol) - Build AI-native servers with tools, resources, and prompts. TypeScript/Python SDKs for Claude Desktop integration.
version: 1.0.0
category: toolchain
author: Claude MPM Team
license: MIT
progressive_disclosure:
  entry_point:
    summary: "Build MCP servers: expose tools (functions), resources (data), prompts (templates). TypeScript/Python SDKs. Claude Desktop native integration."
    when_to_use: "Creating AI integrations, exposing APIs to LLMs, building Claude Desktop extensions, server-side AI tooling, custom data connectors"
    quick_start: "1. npx @modelcontextprotocol/create-server@latest my-server 2. Define tools/resources 3. Add to Claude Desktop config 4. Restart Claude"
context_limit: 700
tags:
  - mcp
  - model-context-protocol
  - ai
  - llm
  - claude
  - tools
  - resources
  - prompts
  - typescript
  - python
  - integration
requires_tools: []
---

# MCP (Model Context Protocol) - AI-Native Server Development

## Overview

Model Context Protocol (MCP) is an open standard for connecting AI assistants to external data sources and tools. Build servers that expose **tools** (functions LLMs can call), **resources** (data LLMs can read), and **prompts** (templates LLMs can use).

**Key Concepts**:
- **Tools**: Functions LLMs can execute (read files, query APIs, run commands)
- **Resources**: Data sources LLMs can access (files, databases, APIs)
- **Prompts**: Reusable templates with arguments for common tasks
- **Client-Server**: MCP servers expose capabilities, clients (like Claude Desktop) consume them
- **Transport**: STDIO (local), SSE (Server-Sent Events), HTTP (network)

**Official SDKs**:
- TypeScript: `@modelcontextprotocol/sdk`
- Python: `mcp`

**Installation**:
```bash
# TypeScript server
npx @modelcontextprotocol/create-server@latest my-server
cd my-server && npm install

# Python server
pip install mcp
# Or use uv (recommended)
uv pip install mcp
```

## Quick Start - TypeScript Server

### 1. Create Server with CLI

```bash
# Interactive setup
npx @modelcontextprotocol/create-server@latest my-filesystem-server

# Options prompt:
# - Server name: my-filesystem-server
# - Language: TypeScript
# - Include example tools: Yes
```

### 2. Define Tools

```typescript
// src/index.ts
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import * as fs from "fs/promises";
import * as path from "path";

const server = new Server(
  {
    name: "filesystem-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "read_file",
        description: "Read contents of a file",
        inputSchema: {
          type: "object",
          properties: {
            path: {
              type: "string",
              description: "Path to the file to read",
            },
          },
          required: ["path"],
        },
      },
      {
        name: "list_directory",
        description: "List contents of a directory",
        inputSchema: {
          type: "object",
          properties: {
            path: {
              type: "string",
              description: "Directory path to list",
            },
          },
          required: ["path"],
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case "read_file": {
      const filePath = args.path as string;
      const content = await fs.readFile(filePath, "utf-8");
      return {
        content: [{ type: "text", text: content }],
      };
    }

    case "list_directory": {
      const dirPath = args.path as string;
      const entries = await fs.readdir(dirPath, { withFileTypes: true });
      const listing = entries
        .map((entry) => `${entry.isDirectory() ? "📁" : "📄"} ${entry.name}`)
        .join("\n");
      return {
        content: [{ type: "text", text: listing }],
      };
    }

    default:
      throw new Error(`Unknown tool: ${name}`);
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Filesystem MCP server running on stdio");
}

main();
```

### 3. Configure Claude Desktop

```json
// ~/Library/Application Support/Claude/claude_desktop_config.json (macOS)
// %APPDATA%/Claude/claude_desktop_config.json (Windows)
{
  "mcpServers": {
    "filesystem": {
      "command": "node",
      "args": ["/absolute/path/to/my-filesystem-server/build/index.js"]
    }
  }
}
```

### 4. Build and Test

```bash
# Build TypeScript
npm run build

# Restart Claude Desktop (Cmd+Q and reopen)
# Server appears in 🔌 menu
```

## Quick Start - Python Server

### 1. Create Server

```python
# server.py
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import json
import os

# Create server instance
app = Server("filesystem-server")

# Define tools
@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="read_file",
            description="Read contents of a file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"}
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="list_directory",
            description="List directory contents",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path"}
                },
                "required": ["path"],
            },
        ),
    ]

# Handle tool calls
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "read_file":
        file_path = arguments["path"]
        with open(file_path, "r") as f:
            content = f.read()
        return [TextContent(type="text", text=content)]

    elif name == "list_directory":
        dir_path = arguments["path"]
        entries = os.listdir(dir_path)
        listing = "\n".join(
            f"{'📁' if os.path.isdir(os.path.join(dir_path, e)) else '📄'} {e}"
            for e in entries
        )
        return [TextContent(type="text", text=listing)]

    else:
        raise ValueError(f"Unknown tool: {name}")

# Start server
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Configure Claude Desktop

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "python",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}
```

### 3. Test

```bash
# Test server standalone
python server.py

# Restart Claude Desktop
# Tools appear in 🔌 menu
```

## Resources - Exposing Data to LLMs

Resources provide read-only access to data sources.

### TypeScript Resource Example

```typescript
import {
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// List available resources
server.setRequestHandler(ListResourcesRequestSchema, async () => {
  return {
    resources: [
      {
        uri: "file:///docs/readme.md",
        name: "README",
        description: "Project README documentation",
        mimeType: "text/markdown",
      },
      {
        uri: "file:///config/settings.json",
        name: "Settings",
        description: "Application settings",
        mimeType: "application/json",
      },
    ],
  };
});

// Handle resource reads
server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  const uri = request.params.uri;

  if (uri.startsWith("file://")) {
    const filePath = uri.replace("file://", "");
    const content = await fs.readFile(filePath, "utf-8");
    return {
      contents: [
        {
          uri,
          mimeType: "text/plain",
          text: content,
        },
      ],
    };
  }

  throw new Error(`Unknown resource: ${uri}`);
});
```

### Python Resource Example

```python
from mcp.types import Resource, ResourceContent

@app.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri="file:///docs/readme.md",
            name="README",
            description="Project README",
            mimeType="text/markdown",
        ),
        Resource(
            uri="file:///config/settings.json",
            name="Settings",
            description="App settings",
            mimeType="application/json",
        ),
    ]

@app.read_resource()
async def read_resource(uri: str) -> ResourceContent:
    if uri.startswith("file://"):
        file_path = uri.replace("file://", "")
        with open(file_path, "r") as f:
            content = f.read()
        return ResourceContent(uri=uri, mimeType="text/plain", text=content)

    raise ValueError(f"Unknown resource: {uri}")
```

## Prompts - Reusable Templates

Prompts are templates that LLMs can use with arguments.

### TypeScript Prompt Example

```typescript
import {
  ListPromptsRequestSchema,
  GetPromptRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// List prompts
server.setRequestHandler(ListPromptsRequestSchema, async () => {
  return {
    prompts: [
      {
        name: "code_review",
        description: "Review code for best practices",
        arguments: [
          {
            name: "language",
            description: "Programming language",
            required: true,
          },
          {
            name: "code",
            description: "Code to review",
            required: true,
          },
        ],
      },
    ],
  };
});

// Handle prompt requests
server.setRequestHandler(GetPromptRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (name === "code_review") {
    const language = args?.language || "unknown";
    const code = args?.code || "";

    return {
      messages: [
        {
          role: "user",
          content: {
            type: "text",
            text: `Review this ${language} code for best practices, security issues, and improvements:\n\n\`\`\`${language}\n${code}\n\`\`\``,
          },
        },
      ],
    };
  }

  throw new Error(`Unknown prompt: ${name}`);
});
```

### Python Prompt Example

```python
from mcp.types import Prompt, PromptMessage, PromptArgument

@app.list_prompts()
async def list_prompts() -> list[Prompt]:
    return [
        Prompt(
            name="code_review",
            description="Review code for best practices",
            arguments=[
                PromptArgument(
                    name="language", description="Programming language", required=True
                ),
                PromptArgument(name="code", description="Code to review", required=True),
            ],
        )
    ]

@app.get_prompt()
async def get_prompt(name: str, arguments: dict) -> list[PromptMessage]:
    if name == "code_review":
        language = arguments.get("language", "unknown")
        code = arguments.get("code", "")

        return [
            PromptMessage(
                role="user",
                content={
                    "type": "text",
                    "text": f"Review this {language} code:\n\n```{language}\n{code}\n```",
                },
            )
        ]

    raise ValueError(f"Unknown prompt: {name}")
```

## Advanced Patterns

### 1. Error Handling

```typescript
// TypeScript
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  try {
    const { name, arguments: args } = request.params;

    if (name === "risky_operation") {
      // Validate inputs
      if (!args.required_param) {
        throw new Error("Missing required parameter: required_param");
      }

      // Perform operation with proper error handling
      const result = await performRiskyOperation(args.required_param);

      return {
        content: [{ type: "text", text: JSON.stringify(result) }],
      };
    }
  } catch (error) {
    // Return error to LLM with helpful message
    return {
      content: [
        {
          type: "text",
          text: `Error: ${error instanceof Error ? error.message : String(error)}`,
        },
      ],
      isError: true,
    };
  }
});
```

```python
# Python
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "risky_operation":
            if "required_param" not in arguments:
                raise ValueError("Missing required parameter: required_param")

            result = await perform_risky_operation(arguments["required_param"])
            return [TextContent(type="text", text=json.dumps(result))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}", isError=True)]
```

### 2. Async Operations

```typescript
// TypeScript - Async API calls
import axios from "axios";

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (name === "fetch_api_data") {
    const url = args.url as string;
    const response = await axios.get(url);

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(response.data, null, 2),
        },
      ],
    };
  }
});
```

```python
# Python - Async database queries
import aiosqlite

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "query_database":
        query = arguments["query"]

        async with aiosqlite.connect("database.db") as db:
            async with db.execute(query) as cursor:
                rows = await cursor.fetchall()
                result = json.dumps(rows)

        return [TextContent(type="text", text=result)]
```

### 3. Environment Variables & Configuration

```typescript
// TypeScript - Load config from environment
import dotenv from "dotenv";
dotenv.config();

const API_KEY = process.env.API_KEY;
const BASE_URL = process.env.BASE_URL || "https://api.example.com";

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "api_call") {
    const response = await fetch(`${BASE_URL}/endpoint`, {
      headers: { Authorization: `Bearer ${API_KEY}` },
    });
    // ...
  }
});
```

```python
# Python - Load config from environment
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL", "https://api.example.com")

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "api_call":
        headers = {"Authorization": f"Bearer {API_KEY}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/endpoint", headers=headers) as resp:
                data = await resp.json()
                return [TextContent(type="text", text=json.dumps(data))]
```

### 4. Streaming Responses (Large Data)

```typescript
// TypeScript - Stream large file contents
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "read_large_file") {
    const filePath = request.params.arguments.path as string;
    const stream = fs.createReadStream(filePath, { encoding: "utf-8" });

    let content = "";
    for await (const chunk of stream) {
      content += chunk;
      // Could yield chunks incrementally in future MCP versions
    }

    return {
      content: [{ type: "text", text: content }],
    };
  }
});
```

### 5. Dynamic Tool Registration

```typescript
// TypeScript - Register tools from config
interface ToolConfig {
  name: string;
  description: string;
  schema: object;
  handler: (args: any) => Promise<any>;
}

const toolRegistry = new Map<string, ToolConfig>();

function registerTool(config: ToolConfig) {
  toolRegistry.set(config.name, config);
}

// Register custom tools
registerTool({
  name: "custom_tool",
  description: "Dynamically registered tool",
  schema: {
    type: "object",
    properties: {
      input: { type: "string" },
    },
  },
  handler: async (args) => {
    return { result: `Processed: ${args.input}` };
  },
});

// List tools dynamically
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: Array.from(toolRegistry.values()).map((tool) => ({
      name: tool.name,
      description: tool.description,
      inputSchema: tool.schema,
    })),
  };
});

// Call tools dynamically
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const tool = toolRegistry.get(request.params.name);
  if (!tool) {
    throw new Error(`Unknown tool: ${request.params.name}`);
  }

  const result = await tool.handler(request.params.arguments);
  return {
    content: [{ type: "text", text: JSON.stringify(result) }],
  };
});
```

## Transport Types

### 1. STDIO (Local Execution)

Default for Claude Desktop integration. Server runs as subprocess.

```json
// Claude Desktop config
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["/path/to/server/build/index.js"],
      "env": {
        "API_KEY": "your-api-key"
      }
    }
  }
}
```

### 2. SSE (Server-Sent Events)

For long-running servers with HTTP transport.

```typescript
// TypeScript SSE server
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import express from "express";

const app = express();
const server = new Server(/* ... */);

app.get("/sse", async (req, res) => {
  const transport = new SSEServerTransport("/messages", res);
  await server.connect(transport);
});

app.post("/messages", async (req, res) => {
  // Handle incoming messages
});

app.listen(3000, () => {
  console.log("MCP server listening on http://localhost:3000");
});
```

```json
// Claude Desktop config for SSE
{
  "mcpServers": {
    "remote-server": {
      "url": "http://localhost:3000/sse"
    }
  }
}
```

### 3. HTTP (Streamable HTTP)

For REST-style MCP servers.

```python
# Python HTTP server with FastAPI
from fastapi import FastAPI
from mcp.server.fastapi import create_fastapi_app

app = FastAPI()
mcp_app = Server("http-server")

# Define tools/resources/prompts as usual
# ...

# Mount MCP routes
app.mount("/mcp", create_fastapi_app(mcp_app))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Debugging MCP Servers

### 1. Server Logs

```typescript
// TypeScript - Console.error for logs (STDOUT is for MCP protocol)
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  console.error(`Tool called: ${request.params.name}`);
  console.error(`Arguments: ${JSON.stringify(request.params.arguments)}`);
  // ...
});
```

```python
# Python - Use logging module
import logging

logging.basicConfig(level=logging.DEBUG, filename="mcp-server.log")
logger = logging.getLogger(__name__)

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    logger.debug(f"Tool called: {name}")
    logger.debug(f"Arguments: {arguments}")
    # ...
```

### 2. MCP Inspector

```bash
# Install MCP Inspector (browser-based debugging tool)
npm install -g @modelcontextprotocol/inspector

# Run inspector with your server
mcp-inspector node /path/to/server/build/index.js

# Opens browser at http://localhost:6274
# - Test tools manually
# - See request/response payloads
# - Debug JSON schema validation
```

### 3. Claude Desktop Logs

```bash
# macOS
tail -f ~/Library/Logs/Claude/mcp*.log

# Windows
# Check %APPDATA%/Claude/logs/
```

### 4. Test Server Standalone

```typescript
// TypeScript - Add test harness
if (process.argv.includes("--test")) {
  // Simulate tool call
  const testRequest = {
    params: {
      name: "read_file",
      arguments: { path: "./test.txt" },
    },
  };

  server
    .setRequestHandler(CallToolRequestSchema, async (request) => {
      // ... your handler
    })
    .then((handler) => handler(testRequest))
    .then((result) => console.log(JSON.stringify(result, null, 2)))
    .catch((error) => console.error(error));
} else {
  // Normal server startup
  main();
}
```

```bash
# Test without Claude Desktop
node build/index.js --test
```

## Real-World Server Examples

### 1. GitHub Integration Server

```typescript
// github-server/src/index.ts
import { Octokit } from "@octokit/rest";

const octokit = new Octokit({ auth: process.env.GITHUB_TOKEN });

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "list_repos",
        description: "List repositories for a user/org",
        inputSchema: {
          type: "object",
          properties: {
            owner: { type: "string", description: "Username or org name" },
          },
          required: ["owner"],
        },
      },
      {
        name: "create_issue",
        description: "Create a GitHub issue",
        inputSchema: {
          type: "object",
          properties: {
            owner: { type: "string" },
            repo: { type: "string" },
            title: { type: "string" },
            body: { type: "string" },
          },
          required: ["owner", "repo", "title"],
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (name === "list_repos") {
    const { data } = await octokit.repos.listForUser({
      username: args.owner as string,
    });
    const repos = data.map((r) => ({
      name: r.name,
      description: r.description,
      stars: r.stargazers_count,
    }));
    return {
      content: [{ type: "text", text: JSON.stringify(repos, null, 2) }],
    };
  }

  if (name === "create_issue") {
    const { data } = await octokit.issues.create({
      owner: args.owner as string,
      repo: args.repo as string,
      title: args.title as string,
      body: args.body as string,
    });
    return {
      content: [
        { type: "text", text: `Issue created: ${data.html_url}` },
      ],
    };
  }
});
```

### 2. Database Query Server

```python
# database-server/server.py
import asyncpg
import json
from mcp.server import Server
from mcp.types import Tool, TextContent

app = Server("database-server")

async def get_db_pool():
    return await asyncpg.create_pool(
        host="localhost",
        database="mydb",
        user="user",
        password="password"
    )

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="query",
            description="Execute SQL query (SELECT only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL query"},
                },
                "required": ["sql"],
            },
        ),
        Tool(
            name="list_tables",
            description="List all tables in database",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    pool = await get_db_pool()

    if name == "query":
        sql = arguments["sql"]
        # Security: Only allow SELECT
        if not sql.strip().upper().startswith("SELECT"):
            raise ValueError("Only SELECT queries allowed")

        async with pool.acquire() as conn:
            rows = await conn.fetch(sql)
            result = [dict(row) for row in rows]

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "list_tables":
        async with pool.acquire() as conn:
            tables = await conn.fetch("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
            """)
            result = [row["table_name"] for row in tables]

        return [TextContent(type="text", text=json.dumps(result, indent=2))]
```

### 3. Web Scraper Server

```typescript
// scraper-server/src/index.ts
import * as cheerio from "cheerio";
import axios from "axios";

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "scrape_url",
        description: "Scrape content from a URL",
        inputSchema: {
          type: "object",
          properties: {
            url: { type: "string", description: "URL to scrape" },
            selector: {
              type: "string",
              description: "CSS selector for content",
            },
          },
          required: ["url"],
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "scrape_url") {
    const url = request.params.arguments.url as string;
    const selector = request.params.arguments.selector as string;

    const response = await axios.get(url);
    const $ = cheerio.load(response.data);

    let content: string;
    if (selector) {
      content = $(selector).text();
    } else {
      content = $("body").text();
    }

    return {
      content: [
        {
          type: "text",
          text: content.trim(),
        },
      ],
    };
  }
});
```

## Best Practices

### 1. Tool Design

**✅ DO**:
- Use clear, descriptive tool names (`read_file` not `rf`)
- Provide detailed descriptions for LLM understanding
- Define comprehensive JSON schemas with descriptions
- Return structured data (JSON) when possible
- Handle errors gracefully with helpful messages

**❌ DON'T**:
- Create overly broad tools (split complex operations)
- Return massive payloads (paginate large datasets)
- Use ambiguous parameter names
- Assume LLM knows your domain-specific terminology

### 2. Security

**Critical Rules**:
- Validate ALL inputs (type, range, format)
- Sanitize file paths (prevent directory traversal)
- Use allowlists for commands/operations
- Never expose sensitive credentials in responses
- Implement rate limiting for expensive operations
- Use read-only access by default

```typescript
// Example: Path validation
function validatePath(inputPath: string): string {
  const normalized = path.normalize(inputPath);
  const allowed = path.resolve("/safe/directory");

  if (!normalized.startsWith(allowed)) {
    throw new Error("Path outside allowed directory");
  }

  return normalized;
}
```

### 3. Performance

- Cache expensive operations
- Stream large responses when possible
- Use pagination for list operations
- Set reasonable timeouts
- Implement request queuing for rate-limited APIs

### 4. Testing

```bash
# Use MCP Inspector for manual testing
mcp-inspector node build/index.js

# Unit test tool handlers
npm test

# Integration test with Claude Desktop
# 1. Add to config
# 2. Restart Claude
# 3. Test in conversation
```

### 5. Documentation

- Document all tools in code comments
- Provide example usage in descriptions
- Include error scenarios in documentation
- Maintain a CHANGELOG for server updates

## Common Pitfalls

❌ **Writing to STDOUT** (breaks MCP protocol):
```typescript
// WRONG
console.log("Debug message");  // STDOUT is for MCP protocol

// CORRECT
console.error("Debug message");  // STDERR for logs
```

❌ **Not handling errors**:
```typescript
// WRONG - unhandled promise rejection
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const data = await riskyOperation();  // Can throw
  return { content: [{ type: "text", text: data }] };
});

// CORRECT
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  try {
    const data = await riskyOperation();
    return { content: [{ type: "text", text: data }] };
  } catch (error) {
    return {
      content: [{ type: "text", text: `Error: ${error.message}` }],
      isError: true,
    };
  }
});
```

❌ **Blocking operations**:
```python
# WRONG - synchronous file read blocks event loop
@app.call_tool()
async def call_tool(name: str, arguments: dict):
    with open("large_file.txt", "r") as f:  # Blocks!
        content = f.read()
    return [TextContent(type="text", text=content)]

# CORRECT - async file I/O
@app.call_tool()
async def call_tool(name: str, arguments: dict):
    async with aiofiles.open("large_file.txt", "r") as f:
        content = await f.read()
    return [TextContent(type="text", text=content)]
```

❌ **Missing required fields in schema**:
```typescript
// WRONG - missing "required" field
{
  name: "search",
  inputSchema: {
    type: "object",
    properties: {
      query: { type: "string" }
    }
    // Missing: required: ["query"]
  }
}
```

## Resources

- **Official Docs**: https://modelcontextprotocol.io
- **TypeScript SDK**: https://github.com/modelcontextprotocol/typescript-sdk
- **Python SDK**: https://github.com/modelcontextprotocol/python-sdk
- **Server Examples**: https://github.com/modelcontextprotocol/servers
- **MCP Inspector**: https://github.com/modelcontextprotocol/inspector
- **Specification**: https://spec.modelcontextprotocol.io

## Related Skills

When building MCP servers, consider these complementary skills:

- **typescript-core**: TypeScript type safety, tsconfig optimization, and advanced patterns
- **asyncio**: Python async patterns for MCP servers with async/await
- **openrouter**: Alternative LLM API integration for multi-model support

### Quick TypeScript MCP Patterns (Inlined for Standalone Use)

```typescript
// Type-safe MCP server with TypeScript
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod';

// Define tool schemas with runtime validation
const SearchSchema = z.object({
  query: z.string().min(1).max(500),
  limit: z.number().int().min(1).max(100).default(10),
});

type SearchArgs = z.infer<typeof SearchSchema>;

class TypeSafeMCPServer {
  private server: Server;

  constructor() {
    this.server = new Server(
      {
        name: 'typed-search-server',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
  }

  private setupToolHandlers() {
    // List tools with full type inference
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'search',
          description: 'Search with type-safe parameters',
          inputSchema: {
            type: 'object',
            properties: {
              query: { type: 'string', minLength: 1, maxLength: 500 },
              limit: { type: 'number', minimum: 1, maximum: 100, default: 10 },
            },
            required: ['query'],
          },
        },
      ],
    }));

    // Type-safe tool execution
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      if (request.params.name === 'search') {
        // Runtime validation with Zod
        const args = SearchSchema.parse(request.params.arguments);

        // Type-safe implementation
        const results = await this.performSearch(args);

        return {
          content: [{ type: 'text', text: JSON.stringify(results) }],
        };
      }

      throw new Error(`Unknown tool: ${request.params.name}`);
    });
  }

  private async performSearch(args: SearchArgs): Promise<Array<{ title: string; url: string }>> {
    // Implementation with full type safety
    // args.query is string, args.limit is number
    return [];
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
  }
}

// Start server
const server = new TypeSafeMCPServer();
server.run();
```

### Quick Python Async MCP Patterns (Inlined for Standalone Use)

```python
# Async MCP server with Python
import asyncio
import logging
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from pydantic import BaseModel, Field

# Type-safe argument models with Pydantic
class SearchArgs(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(10, ge=1, le=100)

class AsyncMCPServer:
    def __init__(self):
        self.server = Server("async-search-server")
        self.setup_handlers()

    def setup_handlers(self):
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="search",
                    description="Search with async processing",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "minLength": 1, "maxLength": 500},
                            "limit": {"type": "number", "minimum": 1, "maximum": 100, "default": 10},
                        },
                        "required": ["query"],
                    },
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            if name == "search":
                # Validate with Pydantic
                args = SearchArgs(**arguments)

                # Async implementation
                results = await self.perform_search(args)

                return [
                    TextContent(
                        type="text",
                        text=str(results)
                    )
                ]

            raise ValueError(f"Unknown tool: {name}")

    async def perform_search(self, args: SearchArgs) -> list[dict[str, str]]:
        """Async search implementation"""
        # Simulate async I/O
        await asyncio.sleep(0.1)

        # Use validated args (args.query is str, args.limit is int)
        return [
            {"title": f"Result for {args.query}", "url": "https://example.com"}
        ]

async def main():
    """Run async MCP server"""
    logging.basicConfig(level=logging.INFO)
    server = AsyncMCPServer()

    # Use stdio transport for Claude Desktop
    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
```

### Quick Multi-Language MCP Patterns (Inlined for Standalone Use)

**TypeScript vs Python Trade-offs:**

| Feature | TypeScript | Python |
|---------|-----------|--------|
| **Type Safety** | Compile-time + runtime (Zod) | Runtime only (Pydantic) |
| **Performance** | Faster startup, Node.js overhead | Slower startup, better for CPU tasks |
| **Async Support** | Native async/await, event loop | asyncio, great for I/O |
| **Ecosystem** | npm packages, frontend tools | Data science, ML libraries |
| **Best For** | Web APIs, real-time tools | Data processing, ML integration |

**Common Patterns Across Both:**

1. **Input Validation**
   - TypeScript: Zod schemas
   - Python: Pydantic models

2. **Error Handling**
   - Both: Try/catch with specific error types
   - Return error content in MCP response

3. **Resource Management**
   - TypeScript: async/await with try/finally
   - Python: async context managers

4. **Testing**
   - TypeScript: Vitest/Jest with mock transport
   - Python: pytest with pytest-asyncio

**Choosing Implementation Language:**
```typescript
// TypeScript - Best for:
// - File system operations
// - Web scraping/HTTP requests
// - JSON/API manipulation
// - Real-time data streams

// Python - Best for:
// - Data analysis (pandas, numpy)
// - Machine learning (scikit-learn, torch)
// - Database ETL operations
// - Scientific computing
```

[Full TypeScript, Python async, and OpenRouter patterns available in respective skills if deployed together]

## Local MCP Integration Patterns (Your Repos)

### .mcp.json Layout (Project-Scoped)

```json
{
  "mcpServers": {
    "kuzu-memory": {
      "type": "stdio",
      "command": "kuzu-memory",
      "args": ["mcp"]
    },
    "mcp-vector-search": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "mcp-vector-search", "mcp"],
      "env": {
        "MCP_ENABLE_FILE_WATCHING": "true"
      }
    }
  }
}
```

### CLI Conventions

- Provide a `mcp` subcommand for stdio servers.
- Use `setup` for end-to-end init + integration (mcp-vector-search, kuzu-memory).
- Use `install` / `uninstall` to target specific clients (mcp-ticketer).
- Provide `doctor` commands to validate dependencies.

### Environment Conventions

- File watching: `MCP_ENABLE_FILE_WATCHING=true`
- Kuzu memory: `KUZU_MEMORY_PROJECT_ROOT`, `KUZU_MEMORY_DB`
- Ticketer adapters: `MCP_TICKETER_ADAPTER`, `GITHUB_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPO`

### Common Server Names

`kuzu-memory`, `mcp-vector-search`, `mcp-ticketer`, `mcp-skillset`, `mcp-browser`

## Summary

- **MCP** enables AI-native server development with tools, resources, and prompts
- **Tools** are functions LLMs can call (read files, query APIs, run operations)
- **Resources** provide read-only data access (files, databases, documentation)
- **Prompts** are reusable templates with arguments for common tasks
- **SDKs** available for TypeScript and Python with full async support
- **Claude Desktop** integration via JSON config (STDIO transport)
- **Debugging** with MCP Inspector, server logs, and standalone testing
- **Security** critical: validate inputs, sanitize paths, use allowlists
- **Best practices**: Clear naming, comprehensive schemas, error handling, performance optimization
