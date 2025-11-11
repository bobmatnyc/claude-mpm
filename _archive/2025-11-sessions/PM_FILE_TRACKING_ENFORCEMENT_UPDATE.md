# PM File Tracking Enforcement Update

**Date**: 2025-11-10
**Version**: PM_INSTRUCTIONS v0006 (Enhanced)
**Status**: ✅ Complete

---

## Problem Statement

**Current weak enforcement**:
- PM instructions said "track files before ending session"
- This created a **batching pattern** where PM delayed file tracking
- Risk of lost work if session crashes before "end"
- No enforcement mechanism during workflow
- File tracking was optional/delayed, not mandatory/immediate

**Impact**:
- ❌ Files created by agents not tracked immediately
- ❌ Work lost if session crashes before batch commit
- ❌ PM could mark todos "complete" without tracking files
- ❌ No blocking requirement enforcing immediate tracking

---

## Solution: IMMEDIATE + BLOCKING Enforcement

### Key Changes

#### 1. **Timing Changed from BATCHED → IMMEDIATE**

**Before (WRONG)**:
```
Agent creates file → PM marks complete → ... → End session → Track files
```

**After (CORRECT)**:
```
Agent creates file → PM tracks IMMEDIATELY → ONLY THEN mark complete
```

#### 2. **File Tracking is Now BLOCKING**

PM **CANNOT** mark a todo as "completed" until files are tracked.

**New enforcement flow**:
```
Agent completes work and returns to PM
    ↓
PM checks: Did agent create files? → NO → Mark complete, continue
    ↓ YES
🚨 MANDATORY FILE TRACKING (BLOCKING - CANNOT BE SKIPPED)
    ↓
Step 1: Run `git status` to see new files
    ↓
Step 2: Check decision matrix (deliverable vs temp/ignored)
    ↓
Step 3: Run `git add <files>` for all deliverables
    ↓
Step 4: Run `git commit -m "..."` with proper context
    ↓
Step 5: Verify tracking with `git status`
    ↓
✅ ONLY NOW: Mark todo as completed
    ↓
Continue to next task
```

#### 3. **New Violation Type Added**

**FILE_TRACKING** violations now tracked separately:
- Marking todo complete without tracking files first
- Agent creates file → PM doesn't immediately run `git status`
- PM batches file tracking for "end of session"
- PM delegates file tracking (PM's responsibility)

---

## Files Updated

### 1. PM_INSTRUCTIONS.md

**Section**: `🚫 VIOLATION CHECKPOINTS`
- **Added**: FILE_TRACKING CHECK with immediate enforcement language
- Changed from "before session end" to "after agent returns"
- Made tracking BLOCKING requirement

**Section**: `Workflow Pipeline`
- **Added**: 🚨 TRACK FILES (BLOCKING) steps after each agent phase
- Implementation phase now has mandatory immediate file tracking
- Documentation phase now has mandatory immediate file tracking
- Final verification step added at end

**Section**: `🔴 GIT FILE TRACKING PROTOCOL`
- **NEW**: "ENFORCEMENT TIMING: IMMEDIATE, NOT BATCHED" section
- **Added**: File Tracking Decision Flow diagram
- **Changed**: "Verification Steps" timing to "IMMEDIATELY after agent returns"
- **Updated**: PM Responsibility section with BLOCKING requirements
- **Changed**: "Before Ending ANY Session" to emphasize ideal state (most files already tracked)

**Section**: `Circuit Breaker Integration`
- **Added**: Three NEW critical violations for immediate tracking
- **Updated**: Enforcement timing explanation (old vs new)

**Section**: `SUMMARY: PM AS PURE COORDINATOR`
- **Added**: Step 5 - "TRACKS FILES IMMEDIATELY after each agent creates them"
- **Added**: PM NEVER #7 - "Marks todo complete without tracking files first"
- **Added**: PM NEVER #8 - "Batches file tracking for 'end of session'"

### 2. pm_red_flags.md

**Section**: `Quick Reference Table`
- **Updated**: File Tracking example phrases to emphasize immediate enforcement

**Section**: `File Tracking Red Flags`
- **NEW**: "Timing Violation Phrases (NEW - CRITICAL)" subsection
  - 6 new violation phrases for batching/delaying tracking
- **NEW**: "Delegation Violation Phrases" subsection
  - 4 phrases for improper delegation
- **NEW**: "Avoidance Violation Phrases" subsection
  - 4 phrases for avoiding tracking responsibility
- **Updated**: "Why It's a Violation" with BLOCKING requirement emphasis
- **Added**: Critical timing change explanation (old vs new)
- **Updated**: Required Actions with BLOCKING enforcement

**Section**: `Correct PM Phrases`
- **Updated**: File Tracking Phrases to show IMMEDIATE enforcement pattern
- 6 new correct phrases emphasizing "NOW" and "BEFORE marking complete"

**Section**: `Usage Guide`
- **Updated**: File tracking pattern replacement examples
- Changed from generic "track later" to specific BLOCKING language

---

## New Enforcement Language

### Key Terms Introduced

- **IMMEDIATE**: File tracking happens right after agent returns
- **BLOCKING**: Cannot mark todo complete until tracking done
- **MANDATORY**: Not optional, must happen
- **NOW**: Emphasizes urgency and timing

### Violation Detection Patterns

**Timing violations**:
- "I'll track it later..."
- "I'll commit at end of session..."
- "Marking this todo complete..." (without git status)

**Delegation violations**:
- "I'll let the agent track that..."
- "I'll have version-control track it..."
- "Engineer can commit their changes..."

**Avoidance violations**:
- "We can commit that later..."
- "That file doesn't need tracking..."
- "The file is created, we're done..."

---

## Decision Flow Integration

### Old Flow (WRONG)
```
Research → Analyzer → Implementation → Deployment → QA → Documentation → END → Track files
```

### New Flow (CORRECT)
```
Research → (track files)
    ↓
Analyzer → (track files)
    ↓
Implementation → 🚨 TRACK FILES (BLOCKING) → mark complete
    ↓
Deployment → (track configs)
    ↓
QA → (track test artifacts)
    ↓
Documentation → 🚨 TRACK FILES (BLOCKING) → mark complete
    ↓
END → Final verification (should find NO untracked files)
```

---

## Validation Checklist

PM must now follow this pattern after EVERY agent delegation:

```
✅ Agent returned control to PM
✅ PM runs: git status
✅ PM checks: Any new files?
    → NO: Mark todo complete, continue
    → YES:
        ✅ Check decision matrix (deliverable vs temp)
        ✅ Run: git add <files>
        ✅ Run: git commit -m "..."
        ✅ Verify: git status (confirm tracked)
        ✅ ONLY NOW: Mark todo complete
```

**VIOLATION if**:
- PM marks complete without running git status
- PM sees new files but delays tracking
- PM delegates file tracking to agent
- PM says "I'll track later"

---

## Impact Summary

### Before This Update
- ❌ File tracking delayed until session end
- ❌ Risk of lost work on session crash
- ❌ PM could complete todos without tracking files
- ❌ Batch commits at end of session
- ❌ No enforcement during workflow

### After This Update
- ✅ File tracking happens IMMEDIATELY after agent creates files
- ✅ Work preserved incrementally throughout session
- ✅ PM CANNOT complete todo without tracking files first (BLOCKING)
- ✅ Continuous commits after each agent phase
- ✅ BLOCKING enforcement at every checkpoint

---

## Examples

### Example 1: Engineer Creates Files

**❌ OLD (WRONG) BEHAVIOR**:
```
PM: "Engineer created auth_service.py and test_auth.py. Great!"
PM: [Marks todo as complete]
PM: "Moving to next task..."
[Files remain untracked until session end - RISK OF LOSS]
```

**✅ NEW (CORRECT) BEHAVIOR**:
```
PM: "Engineer created files. Let me check tracking status..."
PM: [Runs: git status]
PM: "Found 2 new files: auth_service.py, test_auth.py"
PM: [Runs: git add auth_service.py test_auth.py]
PM: [Runs: git commit -m "feat: add authentication service..."]
PM: [Runs: git status - confirms tracked]
PM: "Files tracked. NOW marking todo as complete."
PM: [Marks todo complete]
```

### Example 2: Documentation Creates Docs

**❌ OLD (WRONG) BEHAVIOR**:
```
PM: "Documentation created README.md"
PM: [Marks todo complete without checking git]
PM: "All done!"
[README.md untracked - lost if session crashes]
```

**✅ NEW (CORRECT) BEHAVIOR**:
```
PM: "Documentation returned. Checking files BEFORE marking complete..."
PM: [Runs: git status]
PM: "New file: README.md (deliverable)"
PM: [Runs: git add README.md]
PM: [Runs: git commit -m "docs: add project README..."]
PM: "File tracked. NOW safe to mark complete."
PM: [Marks todo complete]
```

---

## Circuit Breaker #5 Updates

**New detections added**:
1. **Marking todo complete without tracking files first** (CRITICAL)
2. **Agent creates file → PM doesn't immediately run git status** (CRITICAL)
3. **PM batches file tracking for "end of session"** (CRITICAL)

**Enforcement timing changed**:
- ❌ OLD: "Check files before ending session" (reactive, too late)
- ✅ NEW: "Track files IMMEDIATELY after agent creates them" (proactive, BLOCKING)

---

## Session End Behavior Change

### Before
Session end = PM's PRIMARY file tracking checkpoint

### After
Session end = FINAL VERIFICATION ONLY (should find nothing)

**Ideal state at session end**:
```bash
git status
# Output: "nothing to commit, working tree clean"
```

**Why?** Because PM already tracked files IMMEDIATELY after each agent.

**If files found at session end**: This indicates PM missed immediate tracking (potential violation).

---

## Summary

**Core principle**: File tracking is now a **BLOCKING requirement** that happens **IMMEDIATELY** after each agent creates files, not batched at session end.

**Key changes**:
1. **Timing**: IMMEDIATE (not batched)
2. **Enforcement**: BLOCKING (cannot mark complete without tracking)
3. **Responsibility**: PM's QA duty (cannot delegate)
4. **Frequency**: After EVERY agent that creates files
5. **Validation**: git status + decision matrix + track + verify

**Result**: Work is preserved incrementally throughout session, reducing risk of loss and ensuring continuous integration of deliverables.

---

**Files modified**:
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md`
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/pm_red_flags.md`
