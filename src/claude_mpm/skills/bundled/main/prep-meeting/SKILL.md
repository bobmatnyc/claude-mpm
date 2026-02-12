---
name: prep-meeting
description: Prepares for meetings by gathering context about attendees, topics, and relevant data across connected tools. Produces an agenda with talking points, supporting data, and anticipated questions.
version: 1.0.0
when_to_use: when preparing for a meeting, creating an agenda, getting ready for a call, or when the user mentions an upcoming meeting they want to be prepared for
progressive_disclosure:
  level: 1
  references: []
  note: Single-file workflow. Intentionally linear, not reference-heavy.
---

# Meeting Prep

Gather context and produce a structured agenda with talking points before a meeting. The goal is to walk in prepared: knowing what each attendee cares about, having data to support your points, and anticipating questions.

## When to Activate

Trigger phrases: "prep for my meeting with", "agenda for", "get ready for the call with", "meeting with X tomorrow", "what should I bring to", "prepare for".

## Step 1: Identify Meeting Details

Gather the basics before researching:
- **Who is attending?** Names and roles. Check calendar events if a Calendar MCP is available.
- **What is the topic?** If unclear, infer from the invite title, recent project context, or ask.
- **What is the format?** 1:1 vs group, decision meeting vs status update, internal vs external.
- **What does the user want from this meeting?** A decision? Alignment? Information? Approval? This shapes the agenda structure.

## Step 2: Gather Attendee Context

For each key attendee, pull recent context from connected tools:

| Source | What to Look For |
|--------|-----------------|
| Chat history (Slack, Teams) | Recent conversations with or about this person. Open threads, unanswered questions, pending requests. |
| Issue tracker (Jira, Linear) | Tickets they own or are blocked on. Shared projects. |
| Email | Recent exchanges, especially unresolved items. |
| Project knowledge files | Their role, relationship, past interactions. Stakeholder notes if they exist. |

Focus on: What have they been working on? What do they care about? What's their likely agenda coming into this meeting?

## Step 3: Pull Topic Context

Based on the meeting topic, gather supporting material:

- **Project status**: Current state from knowledge files, recent commits, ticket boards
- **Data points**: Relevant metrics or query results from databases or analytics tools
- **Documents**: Related PRDs, design docs, roadmap pages, decision records
- **Recent discussions**: Slack/Teams threads where this topic was debated
- **Blockers**: Anything stuck that might come up

Pull specific data, not vague summaries. "Acceptance rate is 31% higher in test group (p=0.03)" is preparation. "Metrics look good" is not.

## Step 4: Draft Agenda

Structure the agenda based on meeting type:

**Decision meeting:**
```
Context: [2-3 sentences on why we're here]

1. [Decision needed] - [supporting data point]
2. [Decision needed] - [supporting data point]

Options:
A. [Option] - [tradeoffs]
B. [Option] - [tradeoffs]

Recommendation: [your position and why]
```

**Status/sync meeting:**
```
Context: [what happened since last sync]

1. Progress: [what shipped or moved forward]
2. In flight: [what's actively being worked]
3. Blockers: [what needs help]
4. Next steps: [what happens after this meeting]
```

**Exploratory/brainstorm meeting:**
```
Context: [the problem or opportunity]

1. What we know: [facts and data]
2. What we don't know: [open questions]
3. Options to discuss: [2-3 approaches with tradeoffs]
```

## Step 5: Prepare Talking Points

For each agenda item, prepare:
- **Lead with data**: The strongest number or fact that supports your point
- **Your position**: What you think should happen and why, stated plainly
- **Anticipated pushback**: What objections might come up and how to address them
- **Fallback**: If your preferred outcome isn't accepted, what's the next-best option?

## Step 6: Deliver

Present the agenda and talking points to the user for review. Then offer to:
- Add the agenda to the calendar event (via Calendar MCP if available)
- Send a pre-read message to attendees via chat
- Pull additional data on any agenda item that needs more support
