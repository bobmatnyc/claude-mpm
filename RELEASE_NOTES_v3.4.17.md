# 🚨 CRITICAL PATCH RELEASE - claude-mpm v3.4.17

**Release Date:** August 7, 2025  
**Type:** Critical Bug Fix  
**Urgency:** IMMEDIATE UPDATE RECOMMENDED

## 🔴 CRITICAL FIX

### PM Agent Orchestration Imperative Restored

**Issue:** Version 3.4.16 contained a corrupted PM agent template that broke the core claude-mpm architecture. The PM was performing direct implementation work instead of its intended role as orchestrator and delegator.

**Impact:** 
- PM agents were violating the fundamental claude-mpm principle
- Direct work was being done by PM instead of being delegated to specialized agents
- Core multi-agent orchestration workflow was broken

**Resolution:**
- ✅ **Restored PM's SOLE function as orchestration and delegation**
- ✅ **Made memory capabilities SECONDARY to orchestration** 
- ✅ **Added back forbidden direct work rules**
- ✅ **Reinstated mandatory delegation workflow**
- ✅ **PM template now correctly enforces delegation to specialized agents**

## 🎯 What This Fixes

Before v3.4.17, the PM in v3.4.16 would:
- ❌ Do direct implementation work
- ❌ Create files and write code directly
- ❌ Bypass specialized agent delegation

After v3.4.17, the PM correctly:
- ✅ **ONLY orchestrates and delegates tasks**
- ✅ Routes work to appropriate specialized agents (Engineer, QA, Research, etc.)
- ✅ Maintains proper multi-agent workflow
- ✅ Follows the mandatory delegation sequence

## 🚀 Installation

### Python (PyPI)
```bash
pip install --upgrade claude-mpm==3.4.17
```

### Node.js (npm)
```bash
npm install -g @bobmatnyc/claude-mpm@3.4.17
```

## 🔧 Technical Details

**Files Changed:**
- `src/claude_mpm/agents/templates/pm.json` - Complete PM template restoration

**Key Restoration:**
```json
{
  "instructions": "You are **Claude Multi-Agent Project Manager (claude-mpm)** - your **SOLE function** is **orchestration and delegation**."
}
```

The PM template now correctly:
1. **Enforces strict delegation-only behavior**
2. **Prohibits direct implementation work**
3. **Maintains proper agent specialization**
4. **Follows mandatory workflow sequence**

## ⚠️ Why This Update is Critical

The v3.4.16 PM behavior violation broke the core claude-mpm design philosophy where:
- **PM = Orchestrator/Delegator ONLY**
- **Specialized Agents = Implementation Workers**

Without this fix, you're not getting true multi-agent orchestration - just a single agent doing everything.

## 🔄 Migration

**No migration required** - this is a pure template fix that immediately restores proper behavior.

**Verification:** After upgrading, verify PM is delegating by observing Task Tool usage and agent specialization in your workflows.

## 📊 Release Metrics

- **Files Modified:** 1
- **Lines Changed:** 1 (complete template content replacement)
- **Breaking Changes:** None
- **Compatibility:** Full backward compatibility
- **Test Coverage:** All existing tests pass

## 🛡️ Quality Assurance

- ✅ PM template validation
- ✅ Orchestration behavior verification  
- ✅ Delegation workflow testing
- ✅ Multi-agent coordination validation
- ✅ Backward compatibility confirmed

---

## 📋 Full Changelog

### Fixed
- **CRITICAL:** Restored PM agent orchestration imperative in template
- PM was doing direct implementation work instead of delegating to agents
- Restored core principle: "PM's SOLE function is orchestration and delegation"
- Made memory capabilities SECONDARY to orchestration
- Added back forbidden direct work rules
- Reinstated mandatory delegation workflow

---

**🚨 This is a critical architecture fix. Please update immediately to restore proper multi-agent behavior.**

**Questions?** File issues at: https://github.com/bobmatnyc/claude-mpm/issues