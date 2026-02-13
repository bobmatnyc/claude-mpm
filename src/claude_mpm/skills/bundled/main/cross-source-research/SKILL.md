---
name: cross-source-research
description: Multi-source investigation workflow for researching topics across configured MCP tools (Slack, Confluence, Jira, GitHub, Drive, databases, analytics). Enforces depth over breadth by requiring content to be read, not just referenced.
version: 1.0.0
when_to_use: when researching a topic, gathering context across tools, investigating current state of a project or feature, or answering questions that span multiple information sources
progressive_disclosure:
  level: 1
  references: []
  note: Single-file skill. The workflow itself is the deliverable.
---

# Cross-Source Research

Structured workflow for investigating topics across multiple MCP-connected sources. The goal is synthesis, not citation. Research is not complete until you can explain the topic conversationally, not just list where you found mentions of it.

## When to Activate

Trigger phrases: "research", "investigate", "what's the current state of", "pull context on", "what do we know about", "gather context on", "find out about".

## Research Depth Standards

These rules apply to every step below. They exist because the default AI research behavior is shallow: find a reference, summarize the title, move on. That is not research.

1. **Read the content, not just the metadata.** Open the page, read the body. Open the file, read the code. Open the thread, read the messages. A Confluence page title tells you nothing about the decision that was made inside it.
2. **Extract the "why", not just the "what."** If a feature was built, find out why. If a decision was made, find who made it and what they rejected.
3. **Trace outcomes.** If something was proposed, did it ship? If it shipped, is it still live? If it was deprecated, why? Follow the full lifecycle, not just the announcement.
4. **Look for contradictions.** Different sources often disagree. A Slack thread might say "we decided X" while a Jira ticket still tracks Y. Flag these.
5. **Stop when you can teach it.** If you can only say "I found 3 mentions of X in Slack and a Confluence page about it," you are not done. You are done when you can explain what X is, why it exists, what state it's in, and what should happen next.

## Step 1: Define the Question

Before searching anything, clarify:
- What specifically are we trying to understand?
- What would a good answer look like? (a timeline? a decision? a metric? a status?)
- What sources are most likely to have the answer?

Do not skip this step. Unfocused research produces unfocused results.

## Step 2: Check Local Knowledge First

Before hitting external tools, check what's already known:
- Project knowledge base (CLAUDE.md, docs/, any knowledge/ directories)
- Recent conversation history (was this discussed earlier in the session?)
- Task/todo files (is there already an open item tracking this?)

This avoids redundant searches and gives you baseline context to make external searches more targeted.

## Step 3: Search Across Sources

Use the Task tool to dispatch parallel searches where sources are independent. Common source types and what to look for:

| Source Type | What to Search For | MCP Tools |
|-------------|-------------------|-----------|
| **Chat/messaging** (Slack, Teams) | Discussions, decisions, announcements, debates | Channel history, thread replies, search |
| **Documentation** (Confluence, Notion, Wiki) | PRDs, design docs, roadmaps, meeting notes, decision records | Page search, space listing, page content |
| **Issue tracking** (Jira, Linear, GitHub Issues) | Ticket status, blockers, engineering context, sprint progress | Issue search, issue details, epic contents |
| **Code** (GitHub, GitLab) | Implementations, PRs, code reviews, architectural decisions in comments | Code search, PR search, file contents |
| **Drive/docs** (Google Drive, SharePoint) | Decks, meeting transcripts, strategy docs, shared spreadsheets | File search, file content, folder listing |
| **Analytics** (databases, BI tools) | Quantitative evidence, metrics, usage data | SQL queries, saved reports |
| **Product analytics** (Pendo, Amplitude, Mixpanel) | Feature adoption, user behavior, survey responses | Usage queries, guide metrics, segments |

Not every source applies to every question. Pick the 2-4 most relevant sources, not all of them.

## Step 4: Read and Extract

For each result found in Step 3:

**Chat threads**: Read the full thread, not just the first message. Decisions often happen 15 messages deep. Note who said what and when.

**Documentation pages**: Read the body content, not just the title and last-modified date. Look for: stated goals, success criteria, status sections, inline comments, unresolved questions.

**Tickets/issues**: Check status, assignee, linked PRs, comments, and blockers. A ticket marked "In Progress" for 3 months is not the same as one created yesterday.

**Code**: Read the actual implementation, not just the PR title. Check test coverage. Read review comments for context on why choices were made.

**Data**: Run queries to validate claims. "We have high adoption" means nothing without a number. "Override rates are high" needs a percentage and a baseline.

## Step 5: Synthesize

Produce a structured summary. This is the deliverable. It should answer the original question from Step 1.

**Required sections:**

- **Key findings**: What do we now know? State facts, not opinions. Include specific numbers, dates, names.
- **Decisions found**: What was decided, by whom, and when? Link to the source.
- **Contradictions or gaps**: Where do sources disagree? What's still unknown?
- **Recommendations**: Based on the findings, what should happen next? Be specific. "Follow up with X about Y" is better than "more research needed."

**Quality check for synthesis:**
- Does it answer the original question directly?
- Could someone who wasn't in this session understand the findings?
- Are claims backed by specific sources (not "according to Slack" but "per [name] in #channel on [date]")?
- Are recommendations actionable (who, what, by when)?

## Step 6: Persist

Save findings so they're available in future sessions:
- Update relevant project knowledge files with new findings
- Add follow-up items to task lists
- If findings change the project's understanding of something, update CLAUDE.md or project docs

Research that isn't persisted will be re-done. Capture it once, reference it forever.
