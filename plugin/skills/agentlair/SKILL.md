---
name: agentlair
description: >
  Send and receive async messages between Claude MPM instances across machines
  using AgentLair (https://agentlair.dev). Use when you need cross-machine
  agent communication beyond localhost SQLite messaging.
user-invocable: true
version: "1.0.0"
category: communication
tags: [communication, async, cross-machine, agentlair]
---

# AgentLair Cross-Machine Messaging

AgentLair gives each Claude MPM instance a persistent ``@agentlair.dev`` inbox
that works across machines, networks, and sessions — no shared filesystem required.

> **When to use AgentLair vs built-in MPM messaging**
>
> | Scenario | Use |
> |---|---|
> | Same machine, same user | `claude-mpm message` (SQLite, instant) |
> | Different machines / CI/CD | AgentLair (REST, async, persistent) |
> | Cross-team or cross-org agents | AgentLair |

## Prerequisites

Set ``AGENTLAIR_API_KEY`` in your environment.  Get a free key at
https://agentlair.dev (no account required — self-service via the API).

```bash
# Quick self-service key (no signup required)
curl -s -X POST https://agentlair.dev/v1/auth/keys | jq -r '.api_key'
# → al_live_...

export AGENTLAIR_API_KEY="al_live_..."
```

Confirm availability:

```python
from claude_mpm.services.agents.agentlair_agent import is_agentlair_available
print(is_agentlair_available())  # True when AGENTLAIR_API_KEY is set
```

## Claim an inbox

Each MPM instance claims a unique ``@agentlair.dev`` address.  Use a name that
reflects the project or machine so senders know where to route tasks.

```python
import asyncio
from claude_mpm.services.agents.agentlair_agent import claim_inbox

result = asyncio.run(claim_inbox("myproject@agentlair.dev"))
print(result.success)  # True
print(result.data)     # {"claimed": true, "address": "myproject@agentlair.dev"}
```

## Send a message to another MPM instance

```python
import asyncio
from claude_mpm.services.agents.agentlair_agent import send_message

result = asyncio.run(send_message(
    from_address="sender@agentlair.dev",
    to_address="receiver@agentlair.dev",
    subject="Delegation request",
    body="Please summarise the last 5 git commits in /repo/foo",
))
print(result.data)  # {"id": "out_...", "status": "sent", ...}
```

## Check inbox for incoming messages

```python
import asyncio
from claude_mpm.services.agents.agentlair_agent import receive_messages

messages = asyncio.run(receive_messages(
    "myproject@agentlair.dev",
    unread_only=True,
))
for msg in messages:
    print(f"[{msg.received_at}] {msg.from_address}: {msg.subject}")
```

## Read full message body

```python
import asyncio
from claude_mpm.services.agents.agentlair_agent import read_message

result = asyncio.run(read_message(
    address="myproject@agentlair.dev",
    message_id=msg.message_id,  # angle brackets stripped automatically
))
text_body = result.data.get("text", "")
```

## Full async workflow example

```python
import asyncio
from claude_mpm.services.agents.agentlair_agent import (
    claim_inbox, send_message, receive_messages, read_message,
)

async def main():
    # 1. Ensure this instance has an inbox
    await claim_inbox("worker@agentlair.dev")

    # 2. Notify another instance that a task is ready
    await send_message(
        from_address="worker@agentlair.dev",
        to_address="orchestrator@agentlair.dev",
        subject="Task complete",
        body="Benchmark run finished. Results at /results/bench-2026-04-10.json",
    )

    # 3. Poll for replies
    messages = await receive_messages("worker@agentlair.dev", unread_only=True)
    for msg in messages:
        full = await read_message("worker@agentlair.dev", msg.message_id)
        print(full.data.get("text", ""))

asyncio.run(main())
```

## Limitations

- Messages are delivered asynchronously — not real-time.  Poll with
  `receive_messages()` on a schedule or at session start.
- ``AGENTLAIR_API_KEY`` must be present in the environment on both sender and
  receiver instances (they may use different keys from separate accounts).
- Daily send quota applies (see ``rate_limit.daily_remaining`` in send response).

## Architecture note

AgentLair messaging is a **transport layer** — it replaces the shared SQLite
database for cross-machine scenarios but does not change how the MPM PM decides
what to do with incoming messages.  The PM still reads the body, decides
locally what tasks to create, and replies via the same channel.

This complements rather than replaces the built-in `claude-mpm message` CLI:
use SQLite for fast local work, AgentLair for distributed deployments.

---

**Version**: 1.0.0
**Requires**: `httpx` (`pip install httpx`), `AGENTLAIR_API_KEY` env var
**Module**: `claude_mpm.services.agents.agentlair_agent`
