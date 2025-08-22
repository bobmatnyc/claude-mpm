# Fix: Prevent Automatic System Instructions Deployment

## Problem
The system was automatically writing `INSTRUCTIONS.md`, `MEMORY.md`, and `WORKFLOW.md` files to the `.claude/` directory during startup. This should NEVER happen automatically.

## Root Cause
- Line 420 in `/src/claude_mpm/services/agents/deployment/agent_deployment.py` was calling `_deploy_system_instructions()` automatically during `deploy_agents()`
- The `SystemInstructionsDeployer` was writing files to `.claude/` directory

## Solution Implemented

### 1. Disabled Automatic Deployment
**File**: `/src/claude_mpm/services/agents/deployment/agent_deployment.py`
- **Line 419-424**: Commented out the call to `_deploy_system_instructions()`
- Added clear documentation explaining why this is disabled
- The system no longer automatically creates system instructions

### 2. Added Explicit Deployment Method
**File**: `/src/claude_mpm/services/agents/deployment/agent_deployment.py`
- **Lines 624-681**: Added `deploy_system_instructions_explicit()` method
- This method can be called only when user explicitly requests deployment
- Deploys to `.claude-mpm/` directory (not `.claude/`)

### 3. Created Safe Deployment Method
**File**: `/src/claude_mpm/services/agents/deployment/system_instructions_deployer.py`
- **Lines 20-90**: Added `deploy_system_instructions_to_claude_mpm()` method
- Deploys system instructions to `.claude-mpm/` instead of `.claude/`
- Only called when explicitly requested by user

## Framework Loader Configuration
The `FrameworkLoader` already correctly:
- Looks for custom instructions in `.claude-mpm/` directory
- Does NOT look in `.claude/` for instructions
- Priority order:
  1. Project: `./.claude-mpm/INSTRUCTIONS.md`
  2. User: `~/.claude-mpm/INSTRUCTIONS.md`
  3. System: Package defaults

## Testing
Created comprehensive tests to verify the fix:

### Test Scripts
1. `/scripts/test_no_auto_deploy.py` - Standalone verification script
2. `/tests/test_no_auto_instructions_deploy.py` - Pytest test suite

### Test Coverage
- ✅ `deploy_agents()` does NOT create system instructions
- ✅ `_deploy_system_instructions()` is NOT called automatically
- ✅ Explicit deployment works when requested
- ✅ Files deploy to `.claude-mpm/` not `.claude/`
- ✅ Framework loader reads from correct directory

## Correct Behavior After Fix

### During Startup
- System reads instructions from `.claude-mpm/` if they exist
- System NEVER writes to `.claude/` automatically
- No files are auto-generated

### For User-Requested Deployment
- User can explicitly request deployment via agent-manager commands
- Files are deployed to `.claude-mpm/` directory
- This is a manual, intentional action

## Important Notes

1. **Agent Files vs System Instructions**
   - Agent files (Engineer.md, QA.md, etc.) still deploy to `.claude/agents/` - this is correct
   - System instructions (INSTRUCTIONS.md, MEMORY.md, WORKFLOW.md) no longer deploy to `.claude/` - this is the fix

2. **Backward Compatibility**
   - The old `deploy_system_instructions()` method still exists for compatibility
   - But it's never called automatically
   - New explicit method uses `.claude-mpm/` directory

3. **User Experience**
   - No change for users who don't use custom instructions
   - Users who want custom instructions should place them in `.claude-mpm/`
   - Agent manager can be updated to use the explicit deployment method

## Verification
Run the following to verify the fix:
```bash
# Test that startup doesn't create files
python scripts/test_no_auto_deploy.py

# Run pytest tests
pytest tests/test_no_auto_instructions_deploy.py -v

# Manual verification
rm -rf .claude/INSTRUCTIONS.md .claude/MEMORY.md .claude/WORKFLOW.md
claude-mpm run  # Start the system
ls .claude/  # Should NOT contain INSTRUCTIONS.md, MEMORY.md, or WORKFLOW.md
```