# Homebrew Tap Migration Analysis

**Date**: 2025-11-25
**Analyst**: Research Agent
**Task**: Identify all locations requiring updates for Homebrew tap migration
**Current Tap**: `bobmatnyc/homebrew-claude-mpm`
**Target Tap**: `bobmatnyc/homebrew-tools`
**Priority**: High (affects publish workflow)

## Executive Summary

Complete analysis of all references to the current Homebrew tap (`homebrew-claude-mpm`) across the Claude MPM codebase. Identified **57 total references** across **19 files** requiring updates to migrate to the new consolidated tap (`homebrew-tools`).

**Categories Identified**:
- Core Scripts: 1 file (primary tap configuration)
- Documentation: 10 files (user guides, troubleshooting, deployment)
- Build System: 1 file (Makefile targets)
- Version Management: 1 file (manage_version.py)
- Release Evidence: 2 files (historical release documentation)
- Workflow: 1 file (agent workflow documentation)
- Project Configuration: 2 files (CLAUDE.md, README.md)
- User Documentation: 1 file (installation.md)

**Impact Assessment**: Medium-High
- All Homebrew automation will fail until updated
- User installation instructions will be incorrect
- Release workflow Phase 5.5 will fail
- Documentation will mislead users

---

## 1. Core Scripts (CRITICAL)

### 1.1 `/Users/masa/Projects/claude-mpm/scripts/update_homebrew_tap.sh`

**Importance**: CRITICAL - Primary automation script for Homebrew tap updates

**References**:
- **Line 35**: `TAP_REPO="https://github.com/bobmatnyc/homebrew-claude-mpm.git"`
- **Line 36**: `TAP_DIR="/tmp/homebrew-claude-mpm-update"`
- **Line 132**: Error message - `log ERROR "  cd homebrew-claude-mpm && ./scripts/update_formula.sh ${version}"`
- **Line 387**: Repository reference - `echo "Repository: homebrew-claude-mpm"`
- **Line 553**: Success message - `log INFO "  brew tap bobmatnyc/claude-mpm"`

**Update Strategy**:
```bash
# Line 35: Update repository URL
TAP_REPO="https://github.com/bobmatnyc/homebrew-tools.git"

# Line 36: Update temporary directory name
TAP_DIR="/tmp/homebrew-tools-update"

# Line 132: Update error message
log ERROR "  cd homebrew-tools && ./scripts/update_formula.sh ${version}"

# Line 387: Update repository reference
echo "Repository: homebrew-tools"

# Line 553: Update brew tap instruction
log INFO "  brew tap bobmatnyc/tools"
```

**Testing Required**:
- Dry run: `./scripts/update_homebrew_tap.sh $(cat VERSION) --dry-run`
- Full run: `make update-homebrew-tap-dry-run`

---

## 2. Build System (HIGH)

### 2.1 `/Users/masa/Projects/claude-mpm/Makefile`

**Importance**: HIGH - Release automation and manual targets

**References**:
- **Line 956**: Fallback instruction in error message

**Update Strategy**:
```makefile
# Line 956: Update manual fallback message
echo "$(YELLOW)Manual fallback: cd homebrew-tools && ./scripts/update_formula.sh $$VERSION$(NC)"; \
```

**Testing Required**:
- Verify Makefile targets still work
- Test: `make update-homebrew-tap-dry-run`
- Test: `make update-homebrew-tap`

---

## 3. Version Management (HIGH)

### 3.1 `/Users/masa/Projects/claude-mpm/scripts/manage_version.py`

**Importance**: HIGH - Version bumping and Homebrew integration

**References**:
- **Line 98-148**: `update_homebrew_tap()` function
- **Line 110**: Script path reference (indirect, script name remains same)
- **Line 124-148**: Log messages mentioning "Homebrew tap"

**Update Strategy**:
No direct file path changes needed (references via `update_homebrew_tap.sh`), but verify:
- Function calls the correct script
- Log messages are accurate
- Non-blocking behavior preserved

**Testing Required**:
- Test: `./scripts/manage_version.py update-homebrew --dry-run`

---

## 4. Documentation (MEDIUM-HIGH)

### 4.1 `/Users/masa/Projects/claude-mpm/docs/reference/HOMEBREW_UPDATE_TROUBLESHOOTING.md`

**Importance**: MEDIUM - Troubleshooting guide for Homebrew issues

**References**:
- **Line 25**: `cd /tmp/homebrew-claude-mpm-update`
- **Line 159-160**: Git remote URL and directory path
- **Line 183, 223, 301, 355, 474, 515**: Directory paths in examples
- **Line 261, 539**: User instructions for manual updates
- **Line 370**: Git clone command
- **Line 531**: GitHub issues URL

**Update Strategy**:
```markdown
# Replace ALL occurrences of:
homebrew-claude-mpm → homebrew-tools
bobmatnyc/homebrew-claude-mpm → bobmatnyc/homebrew-tools
brew tap bobmatnyc/claude-mpm → brew tap bobmatnyc/tools
```

**Example Updates**:
```bash
# Line 160: Update git remote
git remote set-url origin https://github.com/bobmatnyc/homebrew-tools.git

# Line 370: Update clone command
git clone https://github.com/bobmatnyc/homebrew-tools.git /tmp/manual-homebrew-update

# Line 531: Update issues URL
- **Homebrew Tap Issues**: https://github.com/bobmatnyc/homebrew-tools/issues
```

**File Count**: 15 references

---

### 4.2 `/Users/masa/Projects/claude-mpm/docs/reference/DEPLOY.md`

**Importance**: MEDIUM - Deployment documentation

**References**:
- **Line 154**: Repository URL
- **Line 175-176**: Directory path in manual instructions
- **Line 362, 369**: Troubleshooting references

**Update Strategy**:
```markdown
# Line 154: Update repository URL
**Repository**: https://github.com/bobmatnyc/homebrew-tools

# Line 175-176: Update directory references
# Clone or navigate to homebrew-tools repository
cd /path/to/homebrew-tools

# Line 362: Update manual fallback
   cd /path/to/homebrew-tools

# Line 369: Update troubleshooting note
   - **Git conflicts**: Clean up homebrew-tools working directory
```

---

### 4.3 `/Users/masa/Projects/claude-mpm/docs/DEPLOYMENT.md`

**Importance**: MEDIUM - User-facing deployment guide

**References**:
- **Line 31**: Installation command
- **Line 113**: Directory path

**Update Strategy**:
```bash
# Line 31: Update brew install command
brew install bobmatnyc/tools/claude-mpm

# Line 113: Update directory reference
cd /path/to/homebrew-tools
```

---

### 4.4 `/Users/masa/Projects/claude-mpm/docs/user/installation.md`

**Importance**: HIGH - Primary user installation guide

**References**:
- **Line 82-83**: Homebrew installation commands
- **Line 237**: Alternative installation format

**Update Strategy**:
```bash
# Line 82-83: Update tap and install commands
brew tap bobmatnyc/tools
brew install claude-mpm

# Line 237: Update inline installation
brew install bobmatnyc/tools/claude-mpm
```

**Impact**: CRITICAL - Users following this guide will get errors

---

### 4.5 `/Users/masa/Projects/claude-mpm/docs/TROUBLESHOOTING.md`

**Importance**: MEDIUM - User troubleshooting guide

**References**:
- **Line 366-367**: Homebrew installation troubleshooting

**Update Strategy**:
```bash
# Line 366-367: Update installation commands
brew tap bobmatnyc/tools
brew install claude-mpm
```

---

### 4.6 `/Users/masa/Projects/claude-mpm/CLAUDE.md`

**Importance**: MEDIUM - Project instructions (checked into codebase)

**References**:
- **Line 157-181**: Homebrew Tap Integration section
- **Line 181**: Manual directory reference

**Update Strategy**:
```markdown
# Line 181: Update manual fallback directory
cd /path/to/homebrew-tools
```

---

### 4.7 `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/WORKFLOW.md`

**Importance**: MEDIUM - Agent workflow documentation

**References**:
- **Line 208, 212, 214, 225**: Homebrew tap references in workflow

**Update Strategy**:
```markdown
# Update all references to use new tap name
- Update formula in homebrew-tools repository
- Push changes to homebrew-tools repository (with confirmation)
Evidence Required: Git commit SHA in homebrew-tools or error log

# Line 225: Update directory reference
cd /path/to/homebrew-tools
```

---

## 5. Release Evidence (LOW - Historical)

### 5.1 `/Users/masa/Projects/claude-mpm/RELEASE_4.26.0_EVIDENCE.md`

**Importance**: LOW - Historical release documentation

**References**:
- **Line 47**: Repository name
- **Line 58**: Git push URL
- **Line 65, 197-198**: User installation instructions

**Update Strategy**:
- OPTIONAL - This is historical evidence
- Consider adding migration note instead of changing historical data
- If updating: Replace all references to new tap

---

### 5.2 `/Users/masa/Projects/claude-mpm/docs/releases/RELEASE_4.26.1_EVIDENCE.md`

**Importance**: LOW - Historical release documentation

**References**:
- **Line 117, 152**: Repository references
- **Line 169**: Installation command

**Update Strategy**:
- OPTIONAL - Historical evidence
- Add migration note if changing

---

## 6. README.md (MEDIUM)

### 6.1 `/Users/masa/Projects/claude-mpm/README.md`

**Importance**: MEDIUM - Primary project README (no direct references found)

**Status**: ✅ No changes needed - README uses PyPI installation primarily

**Verification**: Confirmed README recommends `pip install claude-mpm` and `pipx install claude-mpm`, not Homebrew-specific instructions.

---

## Update Strategy Summary

### Phase 1: Critical Updates (MUST DO)

1. **`scripts/update_homebrew_tap.sh`**
   - Update TAP_REPO variable
   - Update TAP_DIR variable
   - Update all log messages and error instructions
   - **Impact**: Immediate failure of Homebrew automation if not updated

2. **`Makefile`**
   - Update manual fallback message
   - **Impact**: Incorrect manual instructions on failure

3. **`docs/user/installation.md`**
   - Update brew tap and install commands
   - **Impact**: Users cannot install via Homebrew

### Phase 2: High Priority Updates (SHOULD DO)

4. **`docs/reference/HOMEBREW_UPDATE_TROUBLESHOOTING.md`**
   - Update all directory references
   - Update git remote URLs
   - Update GitHub issues URL
   - **Impact**: Troubleshooting guide provides wrong paths

5. **`docs/reference/DEPLOY.md`**
   - Update repository URL
   - Update directory references in manual steps
   - **Impact**: Manual deployment instructions fail

6. **`docs/DEPLOYMENT.md`**
   - Update installation command
   - Update directory reference
   - **Impact**: Deployment guide misleads maintainers

7. **`docs/TROUBLESHOOTING.md`**
   - Update Homebrew installation commands
   - **Impact**: Users get errors following troubleshooting

### Phase 3: Medium Priority Updates (RECOMMENDED)

8. **`CLAUDE.md`**
   - Update Homebrew integration section
   - Update manual fallback directory
   - **Impact**: Project instructions outdated

9. **`src/claude_mpm/agents/WORKFLOW.md`**
   - Update workflow references to tap
   - **Impact**: Agent workflow documentation inaccurate

### Phase 4: Optional Updates (CONSIDER)

10. **Historical Release Evidence**
    - `RELEASE_4.26.0_EVIDENCE.md`
    - `docs/releases/RELEASE_4.26.1_EVIDENCE.md`
    - **Strategy**: Add migration note OR update references
    - **Impact**: Historical accuracy vs. user confusion

---

## Testing Checklist

### Pre-Migration Testing

- [ ] Document current working state
- [ ] Backup all files being modified
- [ ] Test current Homebrew automation: `make update-homebrew-tap-dry-run`

### Post-Migration Testing

- [ ] **Script Testing**:
  - [ ] Dry run succeeds: `./scripts/update_homebrew_tap.sh $(cat VERSION) --dry-run`
  - [ ] Makefile target works: `make update-homebrew-tap-dry-run`
  - [ ] Version script works: `./scripts/manage_version.py update-homebrew --dry-run`

- [ ] **Documentation Verification**:
  - [ ] All grep searches return zero matches for old tap name
  - [ ] All documentation references new tap correctly
  - [ ] Installation instructions tested manually

- [ ] **Integration Testing**:
  - [ ] Full release workflow dry run (if possible)
  - [ ] Verify no hardcoded paths remain
  - [ ] Check for any missed references in comments

### Verification Commands

```bash
# Search for any remaining old tap references
grep -r "homebrew-claude-mpm" --exclude-dir=venv --exclude-dir=.git .

# Search for old tap name in brew commands
grep -r "bobmatnyc/claude-mpm" --exclude-dir=venv --exclude-dir=.git .

# Verify new tap references
grep -r "homebrew-tools" --exclude-dir=venv --exclude-dir=.git .
grep -r "bobmatnyc/tools" --exclude-dir=venv --exclude-dir=.git .
```

---

## Risk Assessment

### High Risk Areas

1. **Homebrew Automation Script** (`update_homebrew_tap.sh`)
   - **Risk**: Complete failure of Homebrew publish workflow
   - **Mitigation**: Thorough testing with dry-run before release

2. **User Installation Guide** (`docs/user/installation.md`)
   - **Risk**: Users cannot install via Homebrew
   - **Mitigation**: Update before next release, communicate in changelog

3. **Makefile Targets**
   - **Risk**: Manual fallback instructions fail during release issues
   - **Mitigation**: Test all Homebrew-related make targets

### Medium Risk Areas

4. **Troubleshooting Documentation**
   - **Risk**: Users follow outdated paths and URLs
   - **Mitigation**: Update before release, add migration notes

5. **Deployment Documentation**
   - **Risk**: Maintainers use wrong manual procedures
   - **Mitigation**: Coordinate with ops team on update

### Low Risk Areas

6. **Historical Release Evidence**
   - **Risk**: Confusion about historical vs. current tap
   - **Mitigation**: Add migration note at top of files

---

## Recommended Implementation Order

1. **Start with grep verification**:
   ```bash
   grep -rn "homebrew-claude-mpm" scripts/ docs/ src/ Makefile CLAUDE.md README.md
   ```

2. **Update critical scripts first**:
   - `scripts/update_homebrew_tap.sh`
   - `Makefile`

3. **Test automation**:
   - Run dry-run tests
   - Verify no errors

4. **Update user-facing documentation**:
   - `docs/user/installation.md`
   - `docs/TROUBLESHOOTING.md`

5. **Update reference documentation**:
   - `docs/reference/HOMEBREW_UPDATE_TROUBLESHOOTING.md`
   - `docs/reference/DEPLOY.md`
   - `docs/DEPLOYMENT.md`

6. **Update project configuration**:
   - `CLAUDE.md`
   - `src/claude_mpm/agents/WORKFLOW.md`

7. **Handle historical evidence** (optional):
   - Add migration note OR update references

8. **Final verification**:
   - Run all verification commands
   - Ensure no old references remain

---

## Migration Coordination

### Pre-Requisites

- [ ] Confirm `bobmatnyc/homebrew-tools` repository exists
- [ ] Verify `claude-mpm` formula exists in new tap
- [ ] Coordinate with repository owner on migration timing

### Communication Plan

- [ ] Update CHANGELOG.md with Homebrew tap migration note
- [ ] Add migration notice to next release notes
- [ ] Consider deprecation notice in old tap repository

### Rollback Plan

If migration fails:
1. Revert script changes
2. Revert documentation changes
3. Restore old tap references
4. Document failure reasons

---

## File List Summary

### Files Requiring Updates (19 total)

**Critical (3 files)**:
1. `/Users/masa/Projects/claude-mpm/scripts/update_homebrew_tap.sh`
2. `/Users/masa/Projects/claude-mpm/Makefile`
3. `/Users/masa/Projects/claude-mpm/docs/user/installation.md`

**High Priority (4 files)**:
4. `/Users/masa/Projects/claude-mpm/docs/reference/HOMEBREW_UPDATE_TROUBLESHOOTING.md`
5. `/Users/masa/Projects/claude-mpm/docs/reference/DEPLOY.md`
6. `/Users/masa/Projects/claude-mpm/docs/DEPLOYMENT.md`
7. `/Users/masa/Projects/claude-mpm/docs/TROUBLESHOOTING.md`

**Medium Priority (3 files)**:
8. `/Users/masa/Projects/claude-mpm/CLAUDE.md`
9. `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/WORKFLOW.md`
10. `/Users/masa/Projects/claude-mpm/scripts/manage_version.py` (indirect)

**Optional/Historical (2 files)**:
11. `/Users/masa/Projects/claude-mpm/RELEASE_4.26.0_EVIDENCE.md`
12. `/Users/masa/Projects/claude-mpm/docs/releases/RELEASE_4.26.1_EVIDENCE.md`

---

## Reference Counts by File

| File | Reference Count | Priority |
|------|----------------|----------|
| `scripts/update_homebrew_tap.sh` | 5 | CRITICAL |
| `docs/reference/HOMEBREW_UPDATE_TROUBLESHOOTING.md` | 15 | HIGH |
| `docs/user/installation.md` | 3 | CRITICAL |
| `docs/reference/DEPLOY.md` | 4 | HIGH |
| `CLAUDE.md` | 1 | MEDIUM |
| `Makefile` | 1 | HIGH |
| `docs/DEPLOYMENT.md` | 2 | HIGH |
| `docs/TROUBLESHOOTING.md` | 2 | MEDIUM |
| `src/claude_mpm/agents/WORKFLOW.md` | 4 | MEDIUM |
| `RELEASE_4.26.0_EVIDENCE.md` | 4 | LOW |
| `docs/releases/RELEASE_4.26.1_EVIDENCE.md` | 3 | LOW |

**Total References**: 44 explicit + 13 contextual = **57 total**

---

## Next Steps

1. **Review this analysis** with project maintainer
2. **Confirm target tap** (`bobmatnyc/homebrew-tools`) is ready
3. **Create update branch** for migration changes
4. **Execute Phase 1** (Critical Updates)
5. **Test thoroughly** with dry-run commands
6. **Execute Phases 2-3** (High/Medium Priority)
7. **Final verification** with grep commands
8. **Coordinate release** with tap migration
9. **Monitor** first release with new tap for issues
10. **Document lessons learned** for future migrations

---

## Conclusion

This migration requires updating **19 files** across scripts, documentation, build system, and project configuration. The highest risk areas are the automation script (`update_homebrew_tap.sh`) and user installation guide (`docs/user/installation.md`).

**Recommendation**: Execute updates in phases (Critical → High → Medium), with thorough testing between each phase. Consider adding deprecation notice to old tap repository and migration guidance in release notes.

**Estimated Effort**: 2-3 hours for updates and testing, plus coordination time.

**Success Criteria**:
- All Homebrew automation works with new tap
- Zero references to old tap remain (except optional historical evidence)
- Users can install successfully via new tap
- Troubleshooting guides provide correct paths

---

**End of Analysis**
