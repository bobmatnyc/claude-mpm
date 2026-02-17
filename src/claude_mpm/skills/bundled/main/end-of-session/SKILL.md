---
name: end-of-session
description: Captures session learnings into persistent project memory before closing. Updates task files, project knowledge, and configuration so the next session starts with full context instead of from scratch.
version: 1.0.0
when_to_use: when wrapping up a session, when the user says remember everything, save learnings, end of session, wrap up, or commit to memory
progressive_disclosure:
  level: 1
  references: []
  note: Single-file protocol. Value is in the checklist structure.
---

# End-of-Session Protocol

Claude Code sessions are ephemeral. Everything discovered, debugged, decided, or learned during a session disappears when the conversation ends, unless it's written to files that persist. This protocol captures session knowledge systematically so the next session starts with full context.

Run at the end of every session, or when the user asks to "remember everything", "save learnings", "commit to memory", or "wrap up".

## Step 1: Identify What Was Learned

Review the conversation and identify anything worth preserving. Categories:

**Work completed**: Tasks finished, PRs opened, tickets updated, messages sent. Mark these done in any task tracker files.

**Technical discoveries**: Code paths traced, API patterns figured out, configuration gotchas hit, root causes identified. These are the things that took 20 minutes to figure out and would take 20 minutes again without documentation.

**Decisions made**: What was chosen, what was rejected, and why. Include who was involved. Decisions without recorded rationale get relitigated.

**New contacts and references**: User IDs, channel IDs, page IDs, email addresses, API endpoints, repo paths. Anything that was looked up and might be needed again.

**Open threads**: Follow-ups needed, questions unanswered, tasks discovered but not started. These become next-session starting points.

## Step 2: Update Task Files

If the project uses a task tracking file (personal-tasks.md, TODO.md, or similar):

- Mark completed items as done with today's date
- Add new follow-up tasks discovered during the session
- Move blocked items to a blocked section with the reason
- Add a session log entry summarizing what happened:

```markdown
### YYYY-MM-DD (session N)
- Completed: [what was done]
- Key finding: [most important discovery]
- Next: [what should happen next session]
```

Keep session log entries concise. Bullet points, not paragraphs. The goal is scannable context for future sessions, not a narrative.

## Step 3: Update Project Knowledge Files

For each topic area that came up during the session, update the relevant knowledge file:

- Add new findings under the appropriate section
- Mark resolved questions as done, add new open questions
- Update "last updated" dates
- Add "recent activity" entries with specific dates and outcomes

If a topic was explored significantly but has no knowledge file, create one. Structure it with: overview, current state, open questions, recent activity, next steps.

Common knowledge file types:
- Initiative/project state files (one per workstream)
- Architecture or codebase reference docs
- Integration/API reference docs
- Meeting notes or decision logs

## Step 4: Update Project Configuration

Only update CLAUDE.md or project configuration files if something **permanent** was established:

- New MCP server added or configured
- New workflow pattern that should apply to all future sessions
- New convention or rule discovered
- New tool or integration set up

Do not update config for one-off findings. Those go in knowledge files (Step 3).

## Step 5: Commit

Stage and commit all changed files with a descriptive message summarizing what was captured:

```
git add [changed files]
git commit -m "End-of-session: [1-line summary of key learnings]"
```

## Quality Checklist

Before finishing, verify:

- [ ] All completed tasks marked done
- [ ] New follow-up tasks captured (nothing lost from conversation)
- [ ] Technical discoveries documented (code paths, gotchas, API patterns)
- [ ] Decisions recorded with rationale
- [ ] New reference IDs saved (user IDs, page IDs, endpoints)
- [ ] Knowledge files updated for topics discussed
- [ ] Config files updated only for permanent changes
- [ ] Everything committed to git
- [ ] Summary of what was saved presented to the user
