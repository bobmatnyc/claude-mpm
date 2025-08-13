# Release Notes - v3.7.2

**Release Date**: January 13, 2025  
**Type**: Patch Release (Bugfix)

## 🐛 Bug Fixes

### Agent Deployment System

Fixed critical issues with agent deployment that were causing agents to lose metadata and revert to simplified formats:

#### **Fixed Agent Metadata Handling**
- **Issue**: Agent names were incorrectly using filename stems (e.g., "research") instead of proper agent IDs from templates (e.g., "research_agent")
- **Fix**: Updated `_build_agent_markdown` in `agent_deployment.py` to properly extract `agent_id` from template data
- **Impact**: Agents now deploy with correct identifiers that match their template definitions

#### **Fixed Version Extraction**
- **Issue**: Agent versions were not being properly extracted from the `agent_version` field in templates
- **Fix**: Improved version parsing to correctly handle both `agent_version` and legacy `version` fields
- **Impact**: Agents now display correct semantic versions (e.g., 3.0.0) instead of default values

#### **Fixed Async Deployment Format**
- **Issue**: Async deployment was creating simplified frontmatter with only basic fields (name, version, author)
- **Fix**: Updated `_build_agent_markdown_sync` in `async_agent_deployment.py` to generate complete frontmatter matching synchronous deployment
- **Impact**: Both deployment methods now produce identical, fully-featured agent configurations

#### **Fixed Frontmatter Validator**
- **Issue**: Validator was stripping complex metadata during "correction", reducing agents to minimal fields
- **Fix**: Rewrote validator logic to preserve all valid fields while only fixing actual syntax errors
- **Impact**: Agent metadata is now preserved during validation instead of being simplified

## 📊 Technical Details

### Files Modified
- `src/claude_mpm/services/agents/deployment/agent_deployment.py`
  - Fixed agent_id extraction and frontmatter generation
- `src/claude_mpm/services/agents/deployment/async_agent_deployment.py`
  - Added full metadata support to async deployment
- `src/claude_mpm/agents/frontmatter_validator.py`
  - Implemented field-level corrections instead of full rewrites

### Deployment Improvements
- Agents now correctly maintain:
  - Proper agent IDs (e.g., `engineer_agent`, `research_agent`)
  - Accurate version numbers from templates
  - Complete metadata including description, tools, model, color
  - All custom fields and configurations

## 🔧 Installation

Update to the latest version:
```bash
pip install --upgrade claude-mpm
```

Or install specific version:
```bash
pip install claude-mpm==3.7.2
```

## ✅ Testing

After updating, redeploy your agents to apply the fixes:
```bash
# Force redeploy all agents with corrected metadata
./claude-mpm agents force-deploy
```

Verify deployment:
```bash
# Check agent metadata
head -10 .claude/agents/*.md | grep -E "^name:"
```

## 📝 Notes

- This patch ensures agent deployment consistency across all deployment methods
- Existing agents will be automatically corrected on next deployment
- No breaking changes - fully backward compatible

## 🙏 Acknowledgments

Thanks to users who reported agent deployment issues and helped identify the root causes.

---

For questions or issues, please visit: https://github.com/Anthropic/claude-mpm/issues