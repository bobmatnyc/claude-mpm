# Agent Memory System

## Purpose
Each agent maintains project-specific knowledge in these files. Agents read their memory file before tasks and update it when they learn something new.

## Manual Editing
Feel free to edit these files to:
- Add project-specific guidelines
- Remove outdated information  
- Reorganize for better clarity
- Add domain-specific knowledge

## Memory Limits
- Max file size: 8KB (~2000 tokens)
- Max sections: 10
- Max items per section: 15
- Files auto-truncate when limits exceeded

## File Format
Standard markdown with structured sections. Agents expect:
- Project Architecture
- Implementation Guidelines
- Common Mistakes to Avoid
- Current Technical Context

## How It Works
1. Agents read their memory file before starting tasks
2. Agents add learnings during or after task completion
3. Files automatically enforce size limits
4. Developers can manually edit for accuracy

## Memory File Lifecycle
- Created automatically when agent first runs
- Updated through hook system after delegations
- Manually editable by developers
- Version controlled with project
