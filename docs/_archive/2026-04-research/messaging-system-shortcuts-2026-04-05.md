# MPM Messaging System Research
**Date**: 2026-04-05
**Scope**: mpm-message skill, MCP messaging server, and shortcuts system

---

## 1. How the `mpm-message` Skill Works

**File**: `/Users/masa/Projects/claude-mpm/.claude/skills/mpm-message/SKILL.md`

The skill is a PM-facing instruction layer. It does not implement logic itself — it tells the PM how to use the underlying `MessageService` and CLI.

Key behaviors:
- **Send**: `claude-mpm message send <project-path> --body ... --subject ...`
- **Python API**: `MessageService(Path.cwd()).send_message(to_project=..., ...)`
- **Destination**: Uses a full absolute path OR a shortcut name (e.g. `my-project`)
- The skill explicitly warns against querying `messaging.db` directly

Important gotcha documented in the skill:
- When **reading** a `Message` object: field is `msg.type`
- When **sending**: parameter is `message_type=` (matches DB column)
- Confusing these causes `AttributeError`

The skill also documents that the architecture separates **messages** (peer-to-peer) from **tasks** (local PM decisions). The sending project should not inject tasks into the receiving project.

---

## 2. How the MCP Messaging Server Works

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/mcp/messaging_server.py`

The `MessagingMCPServer` class wraps two services:
- `MessageService` — handles message CRUD in the shared SQLite DB
- `ShortcutsService` — handles project path aliases

It exposes **10 MCP tools** via the `mpm-messaging` MCP server name:

### Message Tools
| Tool | Description |
|------|-------------|
| `message_send` | Send to another project (resolves shortcut for `to_project`) |
| `message_list` | List messages, filterable by status/agent |
| `message_read` | Read a message by ID (auto-marks as read) |
| `message_archive` | Archive a message |
| `message_reply` | Reply to an existing message |
| `message_check` | Get unread count + high-priority messages |

### Shortcut Tools
| Tool | Description |
|------|-------------|
| `shortcut_add` | Add/update a project path shortcut |
| `shortcut_list` | List all shortcuts |
| `shortcut_remove` | Remove a shortcut by name |
| `shortcut_resolve` | Resolve a shortcut name to absolute path |

**Shortcut resolution in `message_send`**: If `to_project` does not start with `/`, the server automatically calls `shortcuts.resolve_shortcut(to_project)` before sending. This means you can pass a shortcut name like `"claude-mpm"` instead of `/Users/masa/Projects/claude-mpm`.

All MessageService calls are blocking SQLite operations wrapped in `asyncio.to_thread()` to avoid blocking the async event loop.

---

## 3. Shortcuts System — Full Implementation

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/communication/shortcuts_service.py`

### Storage Location
```
~/.claude-mpm/shortcuts.json
```

### Data Format
Simple JSON key-value mapping:
```json
{
  "my-project": "/Users/masa/Projects/my-project",
  "claude-mpm": "/Users/masa/Projects/claude-mpm"
}
```

### Operations
- `add_shortcut(name, path)` — validates name (alphanumeric + `_` + `-`) and path (must exist and be a directory)
- `remove_shortcut(name)` — deletes entry
- `list_shortcuts()` — returns dict copy
- `resolve_shortcut(name_or_path)` — returns path if name is known shortcut, else resolves path directly
- `is_shortcut(name)` — boolean check
- `get_shortcut_path(name)` — returns path or `None`

### Caching
Shortcuts are cached in memory (`_shortcuts_cache`). Cache is invalidated only if `clear_cache()` is called explicitly. There is **no automatic cache invalidation** when the file changes on disk from another process.

---

## 4. Current State of Shortcuts Registry

**Result**: `~/.claude-mpm/shortcuts.json` exists but is **empty** (`{}`).

No project shortcuts are currently configured. The file was created by the `ShortcutsService` initializer (which calls `mkdir(parents=True, exist_ok=True)`) but no shortcuts have been added.

---

## 5. CLI Support for Shortcuts

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/messages.py`

Full CLI shortcut management is implemented:
```bash
claude-mpm message shortcut add <name> <path>
claude-mpm message shortcut list
claude-mpm message shortcut remove <name>
claude-mpm message shortcut resolve <name>
```

The `message send` CLI command also resolves shortcuts: if `to_project` is not an absolute path, it calls `shortcuts_service.get_shortcut_path(to_project)`. If not found, it errors with a clear message.

---

## 6. Is There Auto-Population on Startup?

**No.** There is no startup-time auto-registration of project shortcuts. The shortcuts file starts empty and must be populated manually via:
- CLI: `claude-mpm message shortcut add <name> <path>`
- MCP tool: `shortcut_add`
- Python: `ShortcutsService().add_shortcut(name, path)`

No code was found that auto-populates shortcuts from a project registry, git config, or any startup hook.

---

## 7. Key Architecture Summary

```
~/.claude-mpm/messaging.db          # Single shared SQLite DB for all messages
~/.claude-mpm/shortcuts.json        # Project path aliases (currently empty {})

MessageService(project_root)        # CRUD for messages
ShortcutsService()                  # CRUD for shortcuts

MessagingMCPServer                  # Wraps both, exposes 10 MCP tools
  - mpm-messaging MCP server name
  - Tools: message_send/list/read/archive/reply/check
           shortcut_add/list/remove/resolve
```

---

## 8. Answering the Key Question

**Do shortcuts already exist and just need to be populated on startup, or do we need to build the whole thing?**

**Shortcuts ALREADY EXIST as a complete implementation.** The infrastructure is fully built:
- `ShortcutsService` — complete CRUD service
- `shortcuts.json` — storage file exists (but is empty)
- CLI commands — `claude-mpm message shortcut add/list/remove/resolve`
- MCP tools — `shortcut_add`, `shortcut_list`, `shortcut_remove`, `shortcut_resolve`
- Auto-resolution in `message_send` — shortcut names work transparently

The **only missing piece** is that the shortcuts file is empty — no shortcuts have been registered. The system needs to be **populated**, not built.

To register the current project as a shortcut:
```bash
claude-mpm message shortcut add claude-mpm /Users/masa/Projects/claude-mpm
```

Or via MCP tool `shortcut_add` with `name="claude-mpm"` and `path="/Users/masa/Projects/claude-mpm"`.

---

## Related Files
- `/Users/masa/Projects/claude-mpm/.claude/skills/mpm-message/SKILL.md`
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/mcp/messaging_server.py`
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/communication/shortcuts_service.py`
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/communication/message_service.py`
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/messages.py`
- `~/.claude-mpm/shortcuts.json` (currently `{}`)
- `~/.claude-mpm/messaging.db` (shared message database)
