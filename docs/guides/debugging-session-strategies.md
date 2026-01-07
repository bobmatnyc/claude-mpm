# Debugging Session Strategies: Controlling Commit Behavior

## The Problem: Spaghettified Git History

During debugging sessions with Claude MPM, you might end up with git history like this:

```
* fix: try different error handling approach
* fix: update error message format
* fix: revert previous change, try alternative
* fix: adjust validation logic
* fix: another attempt at fixing validation
* fix: initial fix attempt for validation issue
```

This "spaghettified" history happens when agents make multiple commits while iterating on a solution. While this tracks the debugging process, it creates messy git history that's hard to review in pull requests.

**Good news:** This is completely controllable through prompting! Claude Code doesn't auto-commit—agents commit based on instructions, and you can tell them not to.

## Understanding How Commits Work

### Agents Commit, Not Claude Code

Claude Code CLI is a shell environment. It doesn't automatically commit anything. Instead:

1. **You give a prompt** → "Add authentication to the API"
2. **PM agent delegates** → Research → Backend Engineer → QA
3. **Backend Engineer implements** → Makes code changes
4. **Backend Engineer's instructions say** → "Commit changes with clear message"
5. **Backend Engineer commits** → `git commit -m "feat: add JWT authentication"`

The agent follows its instructions to commit. You control this behavior by being explicit in your prompts.

### Default Behavior

By default, agents are instructed to:
- Commit working implementations
- Write clear commit messages following conventional commits format
- Keep commits atomic (one logical change per commit)

This default is good for:
- ✅ Tracking AI-generated changes
- ✅ Easy reversion if something breaks
- ✅ Showing feature progression

But problematic for:
- ❌ Debugging sessions with multiple iterations
- ❌ Experimental changes
- ❌ Clean pull request history

## Prompting Techniques to Control Commits

### Strategy 1: Explicit "Do Not Commit" Instructions

Tell agents explicitly to hold off on commits:

```
Fix the validation error in auth.py. Do not commit yet - I want to test it first.
```

```
Add error handling to the API endpoint. Make changes without committing - this is a debugging session.
```

```
Try a different approach to the database query. Don't commit until we verify this works.
```

**Key phrases:**
- "Do not commit yet"
- "Make changes without committing"
- "This is a debugging session"
- "Hold off on commits"
- "Don't commit until I tell you"

### Strategy 2: Debugging Session Declaration

At the start of a debugging session, set expectations:

```
I'm debugging the authentication flow. For this session, don't commit any changes until I explicitly ask you to. I'll tell you when we have a working solution.
```

This sets the context for the entire session. Agents will iterate without committing until you say:

```
This looks good! Now commit these changes with a clear message about what was fixed.
```

### Strategy 3: Iterative Testing Instructions

Use language that implies iteration:

```
Let's iterate on this validation logic until it works correctly. Make each change but don't commit - we'll commit once when we have the final solution.
```

```
Try different approaches to fix this race condition. We'll test each one and commit only the working solution.
```

### Strategy 4: Feature Branch + Explicit Control

Combine branching with explicit commit control:

```
Create a feature branch called 'fix/auth-validation' and make your changes there. Don't commit until we verify the fix works in all scenarios.
```

## PM Agent Guidance During Debugging

The PM agent orchestrates other agents. Here's how to guide PM during debugging:

### Example: Controlled Debugging Session

**Your prompt:**
```
I'm debugging a null pointer exception in TodoList.tsx line 42. This is an iterative debugging session - agents should make changes without committing until we identify and verify the fix.

The error occurs when the todos array is empty on initial load. Let's investigate and fix this systematically.
```

**What PM will do:**
1. **Understand context** → "This is a debugging session, no commits until verified"
2. **Delegate to Research** → "Analyze the issue without making changes"
3. **Delegate to Frontend Engineer** → "Implement fix, do not commit"
4. **Verify with user** → "Fix implemented, please test"
5. **When confirmed working** → "Now commit with clear message"

### Example: Multiple Fix Attempts

**Your prompt:**
```
The database migration is failing. This might take several attempts to fix. Don't commit anything during debugging - I'll ask for a commit once we have the working solution.
```

**What happens:**
- Backend Engineer tries fix #1 → No commit
- You test → "Still broken, error shows..."
- Backend Engineer tries fix #2 → No commit
- You test → "Better but another issue..."
- Backend Engineer tries fix #3 → No commit
- You test → "Perfect! This works!"
- You say → "Great, commit this fix"
- Backend Engineer → `git commit -m "fix: resolve migration constraint issue"`

**Result:** Clean history with one commit for the final working fix.

## Post-Session Cleanup Strategies

Even with good prompting, you might accumulate commits during debugging. Here's how to clean up:

### Strategy 1: Interactive Rebase

Squash multiple commits into one:

```bash
# View last 5 commits
git log --oneline -5

# Interactive rebase last 5 commits
git rebase -i HEAD~5
```

In the editor, change `pick` to `squash` (or `s`) for commits you want to combine:

```
pick abc1234 fix: initial validation fix attempt
squash def5678 fix: adjust validation logic
squash ghi9012 fix: handle edge case in validation
squash jkl3456 fix: final validation improvement
```

Result: One commit with all changes.

### Strategy 2: Soft Reset and Recommit

Undo commits but keep changes, then make one new commit:

```bash
# Undo last 5 commits, keep changes staged
git reset --soft HEAD~5

# Create single commit with clear message
git commit -m "fix: resolve validation error in auth.py

- Added null checks for empty arrays
- Improved error messages
- Added edge case handling for initial load
"
```

### Strategy 3: Feature Branch Squash

Work on a feature branch, squash when merging:

```bash
# Create feature branch
git checkout -b fix/validation-error

# Let MPM make multiple commits during debugging
# ... (agents work and commit freely)

# When done, merge with squash
git checkout main
git merge --squash fix/validation-error
git commit -m "fix: resolve validation error with proper null checking"
```

**Result:** Main branch has clean history, feature branch preserves detailed debugging history.

### Strategy 4: Cherry-Pick Approach

Use an experiment branch for messy debugging:

```bash
# Create experiment branch
git checkout -b experiment/auth-fix

# Let agents commit freely during debugging
# ... (multiple commits as you iterate)

# When you find working solution, cherry-pick just that commit
git log --oneline  # Find the commit hash of working fix

git checkout main
git cherry-pick abc1234  # Just the working commit

# Optionally delete experiment branch
git branch -D experiment/auth-fix
```

**When to use:** Trying multiple different approaches where most won't work.

## Best Practices: When to Commit vs Iterate

### Commit Immediately

- ✅ Working implementations of complete features
- ✅ Successful bug fixes (verified working)
- ✅ Completed refactorings
- ✅ Test additions (when tests pass)
- ✅ Documentation updates

### Hold Off on Commits

- ⏸️ Experimental changes ("let's try this approach...")
- ⏸️ Debugging iterations ("still investigating...")
- ⏸️ Unverified fixes ("made a change, please test...")
- ⏸️ Partial implementations ("work in progress...")
- ⏸️ Multiple competing approaches ("trying solution A vs solution B...")

### Guidelines

**Quick feature additions:**
```
Add a delete button to the todo item component. Include a confirmation dialog.
```
→ Let agent commit (it's complete and working)

**Debugging a tricky issue:**
```
The WebSocket connection keeps dropping. This is a debugging session - don't commit until we identify and fix the root cause.
```
→ Hold commits until solution verified

**Experimental refactoring:**
```
Let's experiment with extracting the validation logic to a separate service. Don't commit yet - I want to see if this approach improves testability.
```
→ Hold commits until approach validated

## Example: Complete Debugging Session

### The Session

**You:** "I'm debugging a performance issue in the search endpoint. This might take several iterations. Don't commit anything during debugging - we'll commit once when we have the optimized solution."

**PM Agent:** "Understood. Starting analysis of search endpoint performance. No commits until solution is verified."

**Research Agent:** "Analyzing search endpoint... Found potential issues:
1. N+1 query problem in user lookup
2. Missing database index on search fields
3. Inefficient JSON serialization"

**Backend Engineer:** "Implementing fix #1: Adding query optimization with join. Not committing yet per your instructions."

**You:** "Test that please."

**You:** "Still slow. What about the index?"

**Backend Engineer:** "Adding database index on frequently searched fields. Still not committing."

**You:** "Much better! But let's also fix the serialization issue."

**Backend Engineer:** "Optimizing JSON serialization with field selection. All three fixes now implemented, awaiting your verification."

**You:** "Perfect! Performance is now 10x better. Commit these changes with a clear message."

**Backend Engineer:**
```bash
git commit -m "perf: optimize search endpoint performance

- Added query optimization with joins to eliminate N+1 queries
- Added database index on title and description fields
- Optimized JSON serialization with field selection
- Performance improved from 2s to 200ms average response time
"
```

### Result

**Clean history:** One commit with comprehensive description
**Fast iteration:** Three fixes tried and tested quickly
**Good documentation:** Commit message explains all improvements

## Integration with Workflow

### Regular Development

```bash
# Start MPM
claude-mpm run --monitor

# Default behavior - agents commit working changes
"Add user profile endpoint with validation"
# → Agent implements and commits

"Add tests for the profile endpoint"
# → Agent implements tests and commits
```

### Debugging Session

```bash
# Start MPM
claude-mpm run --monitor

# Set debugging context
"I'm debugging the login flow. Don't commit during this session."

# Iterate freely
"Check if the token validation is working"
"Try adding better error logging"
"Adjust the timeout settings"

# When solution found
"Great! This works. Now commit with a clear message about the fix."
```

### Experimental Features

```bash
# Create experiment branch first
git checkout -b experiment/new-architecture

# Start MPM
claude-mpm run --monitor

# Experiment freely
"Let's try restructuring the service layer. Don't commit yet."
"See if this approach works better"
"Make adjustments as needed"

# If approach works
"This architecture is better. Commit it."

# If approach doesn't work
git checkout main
git branch -D experiment/new-architecture
```

## Advanced: Custom Agent Instructions

For projects with frequent debugging, you can customize agent instructions:

### Update Agent Configuration

Edit `.claude/agents/engineer.md` to include debugging-aware behavior:

```markdown
## Commit Behavior

- Commit working implementations by default
- BUT watch for debugging context in user prompts:
  - "debugging session" → Hold commits
  - "don't commit" → Hold commits
  - "experimental" → Hold commits
  - "trying" → Hold commits
- When in doubt, ask: "Should I commit this?"
```

This makes agents more sensitive to debugging context automatically.

## Troubleshooting

### "Agent committed even though I said not to"

**Cause:** Instruction was unclear or agent missed context

**Fix:** Be more explicit:
```
IMPORTANT: Do not commit any changes during this debugging session. I will explicitly tell you when to commit.
```

### "I forgot to say 'don't commit' and now have 10 commits"

**Fix:** Use interactive rebase to squash:
```bash
git rebase -i HEAD~10
# Squash all commits into one
```

### "How do I know if agent will commit?"

**Ask directly:**
```
Before you make changes, confirm: will you be committing this change or waiting for my instruction?
```

Agents will clarify their intention.

## Summary

### Key Takeaways

1. **Agents commit based on instructions** - Claude Code doesn't auto-commit
2. **You control commits through prompts** - Be explicit about when to commit
3. **Use "do not commit" during debugging** - Prevents spaghettified history
4. **Clean up with git rebase** - Squash multiple commits after debugging
5. **Feature branches help** - Isolate messy history from main branch

### Quick Reference

**Starting a debugging session:**
```
"This is a debugging session - don't commit until we verify the solution."
```

**Iterating without commits:**
```
"Make changes without committing - I'll tell you when to commit."
```

**Committing after verification:**
```
"Perfect! Now commit this with a clear message about what was fixed."
```

**Cleaning up history:**
```bash
git rebase -i HEAD~5  # Squash last 5 commits
```

### Related Documentation

- [Quickstart Guide](../getting-started/quickstart.md) - See "Auto-Commit Behavior" section
- [PM Workflow Guide](../agents/pm-workflow.md) - How PM agent coordinates other agents
- [Git Best Practices](../developer/git-workflow.md) - General git hygiene tips

---

**Remember:** You're in control! Agents commit when you want them to, not automatically. Be explicit in your prompts and you'll maintain clean git history even during complex debugging sessions.
