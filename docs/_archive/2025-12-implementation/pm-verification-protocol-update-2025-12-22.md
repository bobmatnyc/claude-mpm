# PM Verification Protocol Update - 2025-12-22

## Overview

This document summarizes the mandatory verification protocol additions to PM instructions, reinforcing that PM **MUST verify everything** with agents - especially local server deployments.

## Problem Addressed

PM agents were claiming local servers were "running" or "accessible" without actually verifying that content was accessible. The PM would see an ops agent start a process and immediately report success, without delegating to web-qa to verify the page actually loads.

**Critical Issue**: Process running ≠ Server working ≠ Content accessible

## Changes Made

### 1. New "MANDATORY VERIFICATION PROTOCOL" Section

**Location**: `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md` (after line 393)

**Key Additions**:
- Universal Verification Rule table mapping change types to required agents and evidence
- Local Server Verification (CRITICAL) section with:
  - Required verification steps (HTTP response + actual content)
  - Forbidden assertions without verification
  - REQUIRED pattern for server verification
  - Example comparisons (WRONG vs CORRECT)

**Required Pattern for Local Servers**:
1. Delegate to local-ops to start server
2. Delegate to web-qa to verify with actual fetch/browser test
3. ONLY THEN report: "Verified running - web-qa confirmed [specific content]"

### 2. Enhanced "ASSERTION VIOLATIONS" Section

**Location**: `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md` (line 126-145)

**New Subsection**: "LOCAL SERVER ASSERTION VIOLATIONS (CRITICAL - MOST COMMON)"

**Forbidden Assertions Added**:
- "Running on localhost:XXXX" without web-qa verification
- "Server started successfully" without web-qa verification
- "Application available at..." without web-qa verification
- "You can now access..." without web-qa verification
- "Site is running on..." without web-qa verification
- "Development server started" without web-qa verification
- "Server is up" without web-qa verification

**Key Reminder**: Process running ≠ Server working. PM MUST verify with web-qa that content is actually accessible.

### 3. Enhanced "VIOLATION CHECKPOINTS" Section

**Location**: `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md` (line 775-800)

**New Subsection**: "LOCAL SERVER VERIFICATION CHECK (CRITICAL)"

**Checkpoint Questions**:
12. Am I about to claim "server is running"? → STOP, need web-qa verification with actual content
13. Did ops agent just start a server? → STOP, MUST delegate to web-qa for content verification
14. Am I reporting a localhost URL? → STOP, MUST verify with web-qa that content is accessible
15. Am I about to say "available at localhost:..."? → STOP, need HTTP response + content evidence from web-qa

### 4. Updated "PM MINDSET TRANSFORMATION" Section

**Location**: `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md` (line 915-941)

**New Wrong Thinking Patterns**:
- "The server started, so it's running..." → NO!
- "The process is up, so users can access it..." → NO!

**New Correct Thinking Patterns**:
- "Ops started server - now web-qa must verify content" → Delegate verification!
- "Process running - but does the page load?" → Delegate to web-qa!

**New PM Thought**:
6. **For local servers: Did web-qa confirm actual content is accessible?**

### 5. Updated Workflow Pipeline

**Location**: `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md` (line 809-817)

**Pipeline Updated**:
```
START → [DELEGATE Research] → [DELEGATE Code Analyzer] → [DELEGATE Implementation] →
🚨 TRACK FILES (BLOCKING) → [DELEGATE Deployment] → 🚨 VERIFY DEPLOYMENT (web-qa/api-qa) →
[DELEGATE QA] → 🚨 TRACK FILES (BLOCKING) → [DELEGATE Documentation] → 🚨 TRACK FILES (FINAL) → END
```

**New PM Role Component**: MANDATORY verification for all deployments/servers

**Critical Addition**: After ANY server start or deployment → MUST verify with QA agent that content is actually accessible

### 6. Enhanced Red Flags File

**Location**: `.claude-mpm/templates/pm-red-flags.md` (line 106-140)

**Section Updated**: "Localhost Assertion Red Flags"

**Key Changes**:
- Rule updated to emphasize web-qa verification showing actual content
- Added new violation phrases (9 total)
- Added "CRITICAL DISTINCTION" table showing insufficient vs sufficient evidence
- Added "Required Evidence from web-qa" list
- Added "Correct Flow" 4-step process

**Critical Distinction Table**:
- ❌ Process running (lsof shows port binding) → NOT SUFFICIENT
- ❌ HTTP 200 response → NOT SUFFICIENT (could be error page)
- ✅ web-qa verified: HTTP 200 + actual page content visible → SUFFICIENT

**Correct Flow**:
1. local-ops starts server → Process running
2. PM delegates to web-qa: "Verify localhost:3000 shows homepage content"
3. web-qa returns: "HTTP 200, homepage visible with 'Welcome to App' heading"
4. PM reports: "Verified running - web-qa confirmed homepage content at localhost:3000"

### 7. Enhanced "Correct PM Phrases" Section

**Location**: `.claude-mpm/templates/pm-red-flags.md` (line 257-268)

**New Subsection**: "Verification Phrases (Local Servers - MUST delegate to web-qa)"

**Added Phrases**:
- "I'll have web-qa verify the page loads with content..."
- "Delegating to web-qa to check localhost:3000 accessibility..."
- "web-qa confirmed HTTP 200 with homepage content visible"
- "According to web-qa's verification, the page shows 'Welcome' heading"
- "web-qa tested the endpoint and confirmed actual content is accessible"

**Clarification**: PM can still verify non-local deployments directly with curl/fetch

## Summary Table

| File Updated | Section Added/Modified | Key Change |
|--------------|------------------------|------------|
| PM_INSTRUCTIONS_DEPLOYED.md | New: MANDATORY VERIFICATION PROTOCOL | Universal verification rule + local server verification |
| PM_INSTRUCTIONS_DEPLOYED.md | Enhanced: ASSERTION VIOLATIONS | New subsection for local server assertions |
| PM_INSTRUCTIONS_DEPLOYED.md | Enhanced: VIOLATION CHECKPOINTS | 4 new local server verification checkpoints |
| PM_INSTRUCTIONS_DEPLOYED.md | Updated: PM MINDSET TRANSFORMATION | Added server verification thinking patterns |
| PM_INSTRUCTIONS_DEPLOYED.md | Updated: Workflow Pipeline | Added VERIFY DEPLOYMENT step after deployment |
| pm-red-flags.md | Enhanced: Localhost Assertion Red Flags | CRITICAL DISTINCTION table + correct flow |
| pm-red-flags.md | Enhanced: Correct PM Phrases | New local server verification phrases |

## Expected Impact

### PM Behavior Changes

**Before**:
```
❌ PM: local-ops started server
❌ PM: "Server is running on localhost:3000"
❌ PM: "You can access the site now"
```

**After**:
```
✅ PM: local-ops started server
✅ PM: "Now delegating to web-qa to verify content is accessible..."
✅ web-qa: "HTTP 200, homepage visible with 'Welcome' heading"
✅ PM: "Verified running - web-qa confirmed homepage content at localhost:3000"
```

### Violation Detection

PM will now fail verification checks if:
- Claims server is running without web-qa evidence
- Reports localhost URL without content verification
- Says "available at..." without actual page content confirmation
- Marks deployment complete without QA verification step

## Implementation Notes

1. **BLOCKING Requirement**: PM CANNOT claim server is running until web-qa verifies content
2. **Evidence Required**: HTTP 200 + actual page content (not just process running)
3. **Agent Routing**: Always use web-qa for local server verification
4. **Verification Timing**: After deployment step, before claiming success

## Testing Scenarios

### Scenario 1: Local Development Server

**User Request**: "Start the development server"

**Expected PM Flow**:
1. Delegate to local-ops: "Start development server"
2. local-ops returns: "Server started on localhost:3000"
3. PM delegates to web-qa: "Verify localhost:3000 shows homepage content"
4. web-qa returns: "HTTP 200, homepage visible with 'Welcome to App' heading"
5. PM reports: "Verified running - web-qa confirmed homepage with 'Welcome to App' heading at localhost:3000"

**Violation if**:
- PM skips step 3-4 and goes straight to reporting
- PM claims "running" based only on local-ops response
- PM doesn't delegate to web-qa for content verification

### Scenario 2: PM2 Application

**User Request**: "Deploy the app with PM2"

**Expected PM Flow**:
1. Delegate to local-ops: "Deploy app with PM2"
2. local-ops returns: "PM2 process started, running on port 8080"
3. PM delegates to web-qa: "Verify localhost:8080 shows API health endpoint"
4. web-qa returns: "HTTP 200, health endpoint returns {\"status\": \"ok\"}"
5. PM reports: "Verified running - web-qa confirmed health endpoint at localhost:8080"

**Violation if**:
- PM reports "deployed successfully" without web-qa verification
- PM relies only on PM2 process status
- PM doesn't verify actual endpoint accessibility

## Related Files

- `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md` - Main PM instructions
- `.claude-mpm/templates/pm-red-flags.md` - PM violation phrase indicators
- `.claude-mpm/templates/validation-templates.md` - Evidence requirements (referenced)
- `.claude-mpm/templates/circuit-breakers.md` - Enforcement system (referenced)

## Version

- **Update Date**: 2025-12-22
- **PM Instructions Version**: 0006 (maintained - updates are additions)
- **Red Flags Version**: 1.0.0 (maintained - enhancements to localhost section)

## Conclusion

These updates enforce the critical principle: **PM MUST verify everything, especially local servers**. Process running ≠ Server working. PM cannot claim a server is accessible without web-qa verification showing actual content.

This eliminates the common violation pattern where PM reports "running on localhost:XXXX" without actual evidence that users can access the content.
