# Skills vs. Commands: Terminology Fix Summary

**Date:** 2026-01-07
**Status:** Documented

## Purpose

Summarize the terminology issue where \"skills\" were conflated with user slash commands, and point to the canonical architecture note.

## Problem

- **Framework skills** are loaded context for agents (not invokable tools).
- **Slash commands** are user-invoked operations (e.g., `/mpm-init`).

The PM should describe slash commands, not attempt to invoke them.

## Canonical Reference

- **Detailed architecture note:** [skills-vs-commands-clarification.md](skills-vs-commands-clarification.md)

## Implementation Targets (Pending)

- Update PM instructions: `src/claude_mpm/agents/PM_INSTRUCTIONS.md` and `src/claude_mpm/agents/WORKFLOW.md`.
- Clarify the Skill tool description in the system prompt.
- Add a short \"Skills vs. Commands\" section in `docs/guides/skills-system.md` and `docs/user/skills-guide.md`.
