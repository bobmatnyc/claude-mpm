# 🎯 PM Instruction Templates Ecosystem

**Version**: 1.0.0
**Last Updated**: 2025-10-21
**Parent Document**: [PM_INSTRUCTIONS.md](../PM_INSTRUCTIONS.md)

Welcome to the PM Template Ecosystem - a modular system of specialized templates that enforce PM delegation discipline through validation, detection, examples, and standardization.

---

## 📚 Quick Navigation

### By Use Case
- **Need to verify work?** → [validation_templates.md](#validation-templates)
- **Detecting violations?** → [circuit_breakers.md](#circuit-breakers)
- **Learning proper behavior?** → [pm_examples.md](#pm-examples)
- **Tracking new files?** → [git_file_tracking.md](#git-file-tracking)
- **Spotting red flags?** → [pm_red_flags.md](#pm-red-flags)
- **Formatting responses?** → [response_format.md](#response-format)

### By Development Phase
- **Phase 1 (Quick Wins)**: [validation_templates](#validation-templates), [circuit_breakers](#circuit-breakers), [pm_examples](#pm-examples)
- **Phase 2 (High Priority)**: [git_file_tracking](#git-file-tracking), [pm_red_flags](#pm-red-flags), [response_format](#response-format)

---

## 🎯 Overview

### Purpose

The PM Template Ecosystem modularizes PM instruction content into specialized, focused templates that:

1. **Enforce Delegation Discipline**: Prevent PM from doing work instead of delegating
2. **Ensure Evidence-Based Assertions**: Require verification for all claims
3. **Standardize Response Format**: Consistent, structured PM outputs
4. **Track File Creation**: Ensure all deliverables are preserved in git
5. **Provide Learning Resources**: Clear examples of correct vs incorrect behavior

### Benefits of Modularization

- **Maintainability**: Each template has a single, focused responsibility
- **Discoverability**: Quick reference tables and navigation guides
- **Consistency**: Standardized validation and detection patterns
- **Extensibility**: Easy to add new templates without affecting existing ones
- **Clarity**: Clear separation of concerns (validation vs detection vs examples)

---

## 📋 Quick Reference Table

| Template | Lines | Purpose | Primary Use Case | Related Templates |
|----------|-------|---------|------------------|-------------------|
| [validation_templates.md](#validation-templates) | 312 | Verification requirements & evidence collection | When PM needs to verify agent work or deployment | circuit_breakers, response_format |
| [circuit_breakers.md](#circuit-breakers) | 638 | Automatic violation detection mechanisms | Real-time detection of PM delegation violations | pm_red_flags, pm_examples |
| [pm_examples.md](#pm-examples) | 474 | Right vs wrong behavior examples | Learning correct PM delegation patterns | circuit_breakers, validation_templates |
| [git_file_tracking.md](#git-file-tracking) | 584 | Complete file tracking protocol | Tracking all new files created during sessions | circuit_breakers, response_format |
| [pm_red_flags.md](#pm-red-flags) | 240 | Violation phrase indicators | Quick detection via language patterns | circuit_breakers, pm_examples |
| [response_format.md](#response-format) | 583 | PM response JSON schemas | Formatting final session summaries | validation_templates, git_file_tracking |

**Total Template Lines**: 2,831 lines of focused, actionable guidance

---

## 📖 Template Descriptions

### Validation Templates

**File**: `validation_templates.md` (312 lines)
**Version**: 1.0.0
**Last Updated**: 2025-10-20

**What It Contains**:
- Required evidence for common assertions
- Deployment verification matrix
- Verification commands reference
- Universal verification requirements
- PM verification checklist
- Local deployment mandatory verification
- Two valid verification patterns

**When to Use It**:
- PM needs to verify agent work before making claims
- Determining what evidence is required for specific assertions
- Planning verification strategy for deployments
- Choosing between delegating verification vs using PM-allowed commands

**Key Sections**:
1. **Required Evidence Table**: Maps assertions to required evidence (e.g., "Feature implemented" requires working demo/test results)
2. **Deployment Verification Matrix**: Comprehensive checklist for deployment verification
3. **Verification Commands Reference**: PM-allowed commands for specific verification tasks
4. **Two Valid Patterns**: Either delegate to QA/Ops OR use PM-allowed verification commands

**Integration with Other Templates**:
- **circuit_breakers.md**: Violations trigger when PM asserts without consulting validation templates
- **response_format.md**: Evidence from validation templates goes in response JSON
- **pm_examples.md**: Examples demonstrate proper use of validation requirements

---

### Circuit Breakers

**File**: `circuit_breakers.md` (638 lines)
**Version**: 1.0.0
**Last Updated**: 2025-10-20

**What It Contains**:
- 5 automatic violation detection mechanisms
- Circuit breaker trigger conditions
- Violation tracking format
- Escalation levels
- Corrective actions for each circuit breaker

**When to Use It**:
- Real-time detection of PM delegation violations
- Understanding why a violation was flagged
- Determining appropriate corrective action
- Tracking violation patterns and escalation

**Key Sections**:
1. **Circuit Breaker #1: Implementation Detection** - Detects when PM implements instead of delegating
2. **Circuit Breaker #2: Investigation Detection** - Detects when PM investigates instead of delegating
3. **Circuit Breaker #3: Unverified Assertion Detection** - Detects when PM makes claims without evidence
4. **Circuit Breaker #4: Implementation Before Delegation Detection** - Detects when PM acts before delegating
5. **Circuit Breaker #5: File Tracking Detection** - Detects when PM fails to track new files in git

**Integration with Other Templates**:
- **pm_red_flags.md**: Red flags feed into circuit breaker detection
- **validation_templates.md**: Circuit Breaker #3 references validation requirements
- **git_file_tracking.md**: Circuit Breaker #5 enforces file tracking protocol
- **pm_examples.md**: Examples show how circuit breakers detect violations

---

### PM Examples

**File**: `pm_examples.md` (474 lines)
**Version**: 1.0.0
**Last Updated**: 2025-10-20

**What It Contains**:
- 5 detailed scenario examples
- Wrong vs correct PM behavior comparisons
- Violation analysis for each example
- Key takeaways and lessons learned
- Quick reference summary table

**When to Use It**:
- Learning proper PM delegation patterns
- Understanding common violation scenarios
- Training new PM instances
- Clarifying ambiguous delegation situations

**Key Sections**:
1. **Example 1: Bug Fixing** - Shows proper delegation to Engineer + QA
2. **Example 2: Question Answering** - Shows proper delegation to Research
3. **Example 3: Deployment** - Shows proper delegation to Ops + verification
4. **Example 4: Local Server Management** - Shows proper use of local-ops-agent
5. **Example 5: Performance Optimization** - Shows proper delegation + evidence collection

**Integration with Other Templates**:
- **circuit_breakers.md**: Examples show what triggers each circuit breaker
- **validation_templates.md**: Examples demonstrate proper evidence collection
- **response_format.md**: Examples include properly formatted JSON responses
- **pm_red_flags.md**: Examples highlight red flag phrases in wrong behavior

---

### Git File Tracking

**File**: `git_file_tracking.md` (584 lines)
**Version**: 1.0.0
**Last Updated**: 2025-10-21

**What It Contains**:
- Complete file tracking protocol
- Tracking decision matrix
- PM verification checklist
- Integration with git commit protocol
- Commit message templates
- Circuit breaker integration
- Session completion checklist

**When to Use It**:
- Any time agents create new files during sessions
- Before completing a session
- Planning git commits for agent work
- Determining which files need tracking vs exclusion

**Key Sections**:
1. **Core Principle**: PM MUST verify and track all new files created by agents
2. **Tracking Decision Matrix**: Determines which files to track, commit immediately, or exclude
3. **PM Verification Checklist**: Step-by-step process for file tracking
4. **Commit Message Template**: Standardized format for commits with file tracking context
5. **Session Completion Checklist**: Ensures no files are forgotten

**Integration with Other Templates**:
- **circuit_breakers.md**: Circuit Breaker #5 enforces this protocol
- **response_format.md**: File tracking information goes in response JSON
- **pm_red_flags.md**: Red flags for missing file tracking
- **validation_templates.md**: File creation verification requirements

---

### PM Red Flags

**File**: `pm_red_flags.md` (240 lines)
**Version**: 1.0.0
**Last Updated**: 2025-10-21

**What It Contains**:
- Quick reference table of violation phrases
- Investigation red flags ("Let me check...")
- Implementation red flags ("Let me fix...")
- Assertion red flags ("It works...")
- Localhost assertion red flags
- File tracking red flags
- Correct PM phrases alternatives

**When to Use It**:
- Quick detection of PM violations through language patterns
- Real-time monitoring of PM responses
- Training PM to avoid violation phrases
- Automated violation detection in PM responses

**Key Sections**:
1. **The "Let Me" Test**: Primary red flag indicator
2. **Quick Reference Table**: All red flag categories with examples
3. **Investigation Red Flags**: Phrases indicating PM is researching instead of delegating
4. **Implementation Red Flags**: Phrases indicating PM is implementing instead of delegating
5. **Assertion Red Flags**: Phrases indicating PM is claiming without evidence
6. **Correct PM Phrases**: Alternative phrases that indicate proper delegation

**Integration with Other Templates**:
- **circuit_breakers.md**: Red flags trigger circuit breakers
- **pm_examples.md**: Examples highlight red flag phrases in wrong behavior
- **response_format.md**: Correct phrases align with proper response structure
- **validation_templates.md**: Assertion red flags link to validation requirements

---

### Response Format

**File**: `response_format.md` (583 lines)
**Version**: 1.0.0
**Last Updated**: 2025-10-21

**What It Contains**:
- Complete JSON schema for PM responses
- Field descriptions and requirements
- Example responses for various scenarios
- Validation checklist
- Common mistakes to avoid
- Integration with other systems

**When to Use It**:
- Formatting final session summaries
- Ensuring all required fields are present
- Structuring delegation tracking information
- Documenting evidence and verification
- Recording file tracking details

**Key Sections**:
1. **Complete JSON Schema**: Full structure for PM session summaries
2. **Field Descriptions**: Detailed explanation of each field and its purpose
3. **Example Responses**: Complete examples for common scenarios
4. **Validation Checklist**: Ensures response meets all requirements
5. **Common Mistakes**: Pitfalls to avoid in response formatting

**Integration with Other Templates**:
- **validation_templates.md**: Evidence and verification details populate response fields
- **git_file_tracking.md**: File tracking information goes in dedicated response section
- **circuit_breakers.md**: Violation tracking information included in responses
- **pm_examples.md**: Examples include properly formatted JSON responses

---

## 🗺️ Template Relationship Diagram

```
                    PM INSTRUCTIONS (Parent)
                              |
                    +---------+---------+
                    |                   |
            DETECTION LAYER      GUIDANCE LAYER
                    |                   |
        +-----------+----------+    +---+---+
        |                      |    |       |
  Circuit Breakers      PM Red Flags  |  Examples
  (Automatic Detection)  (Quick Check) | (Learning)
        |                      |       |
        +----------+-----------+-------+
                   |
            VERIFICATION LAYER
                   |
         +---------+---------+
         |                   |
   Validation Templates  Git File Tracking
   (Evidence Required)   (File Accountability)
         |                   |
         +--------+----------+
                  |
          STANDARDIZATION LAYER
                  |
          Response Format
          (Structured Output)
```

**Layer Descriptions**:

1. **Detection Layer**: Real-time violation detection
   - Circuit Breakers: Comprehensive automatic detection
   - PM Red Flags: Quick language-based detection

2. **Guidance Layer**: Learning and examples
   - PM Examples: Detailed scenarios showing right vs wrong behavior

3. **Verification Layer**: Evidence and accountability
   - Validation Templates: What evidence is required
   - Git File Tracking: Ensuring all deliverables are preserved

4. **Standardization Layer**: Consistent output
   - Response Format: Structured JSON for session summaries

---

## 🔍 Navigation Guide

### Finding What You Need

**Scenario**: "PM made a claim without evidence"
→ Consult: [validation_templates.md](#validation-templates) (what evidence is required?)
→ Then: [circuit_breakers.md](#circuit-breakers) (Circuit Breaker #3 triggered)
→ Refer to: [response_format.md](#response-format) (how to document evidence)

**Scenario**: "PM said 'Let me investigate this...'"
→ Consult: [pm_red_flags.md](#pm-red-flags) (investigation red flag detected)
→ Then: [circuit_breakers.md](#circuit-breakers) (Circuit Breaker #2 triggered)
→ Learn from: [pm_examples.md](#pm-examples) (Example 2: Question Answering)

**Scenario**: "Agent created new files, need to track them"
→ Consult: [git_file_tracking.md](#git-file-tracking) (complete tracking protocol)
→ Use: [response_format.md](#response-format) (file_tracking section)
→ Verify with: [circuit_breakers.md](#circuit-breakers) (Circuit Breaker #5)

**Scenario**: "Session ending, need to create summary"
→ Consult: [response_format.md](#response-format) (JSON schema)
→ Verify: [validation_templates.md](#validation-templates) (all evidence collected?)
→ Check: [git_file_tracking.md](#git-file-tracking) (all files tracked?)

**Scenario**: "Learning proper PM behavior"
→ Start with: [pm_examples.md](#pm-examples) (5 detailed scenarios)
→ Understand: [circuit_breakers.md](#circuit-breakers) (what violations to avoid)
→ Learn: [pm_red_flags.md](#pm-red-flags) (language patterns to avoid)

### Search by Keywords

| Keywords | Templates to Consult |
|----------|---------------------|
| verify, evidence, proof, check | validation_templates, circuit_breakers |
| violation, wrong, mistake, error | circuit_breakers, pm_red_flags, pm_examples |
| example, scenario, case study | pm_examples |
| file, git, commit, track | git_file_tracking, response_format |
| "let me", phrase, language | pm_red_flags, pm_examples |
| JSON, format, structure, output | response_format |
| deployment, localhost, server | validation_templates, pm_examples (Example 3, 4) |
| delegation, assign, coordinate | pm_examples, circuit_breakers |

---

## 📊 Version Information

**Current Ecosystem Version**: 1.0.0
**Release Date**: 2025-10-21
**Total Lines**: 2,831 lines
**Total Templates**: 6 templates

### Template Version Matrix

| Template | Version | Last Updated | Status |
|----------|---------|--------------|--------|
| validation_templates.md | 1.0.0 | 2025-10-20 | Stable |
| circuit_breakers.md | 1.0.0 | 2025-10-20 | Stable |
| pm_examples.md | 1.0.0 | 2025-10-20 | Stable |
| git_file_tracking.md | 1.0.0 | 2025-10-21 | Stable |
| pm_red_flags.md | 1.0.0 | 2025-10-21 | Stable |
| response_format.md | 1.0.0 | 2025-10-21 | Stable |

### Changelog

**v1.0.0 (2025-10-21)**:
- Initial release of Template Ecosystem
- Phase 1 templates: validation_templates, circuit_breakers, pm_examples
- Phase 2 templates: git_file_tracking, pm_red_flags, response_format
- Complete navigation and integration documentation

---

## 🔧 Maintenance Guidelines

### For Developers

**When to Update Templates**:
1. **Bug Fixes**: Errors in validation requirements, detection logic, or examples
2. **New Patterns**: Additional violation patterns or delegation scenarios discovered
3. **Clarifications**: User confusion indicates need for clearer documentation
4. **Integration**: New templates added to ecosystem require relationship updates

**Update Process**:
1. Update template content in specific template file
2. Update template version number and last updated date
3. Update this README.md if:
   - Line counts changed significantly (>10%)
   - New templates added
   - Template relationships changed
   - New sections added to templates
4. Update Version Information section
5. Add entry to Changelog
6. Test all cross-references and links

**Versioning Strategy**:
- **Patch (x.x.X)**: Bug fixes, typos, clarifications
- **Minor (x.X.0)**: New sections, additional examples, enhanced detection
- **Major (X.0.0)**: Breaking changes, template restructuring, schema changes

### For PM Agents

**Regular Review**:
- Review all templates at session start if unfamiliar with ecosystem
- Consult specific templates as needed during sessions
- Reference Quick Reference Table for fast lookup
- Use Navigation Guide for scenario-based lookup

**Integration Checklist**:
- [ ] Validation Templates: Evidence collected for all assertions?
- [ ] Circuit Breakers: No violations triggered during session?
- [ ] PM Examples: Behavior matches correct examples?
- [ ] Git File Tracking: All new files tracked in git?
- [ ] PM Red Flags: No violation phrases in responses?
- [ ] Response Format: Final summary follows JSON schema?

---

## 📚 Additional Resources

### Parent Documentation
- [PM_INSTRUCTIONS.md](../PM_INSTRUCTIONS.md) - Main PM instruction document
- [BASE_PM.md](../BASE_PM.md) - Base PM framework requirements

### Related Documentation
- [CLAUDE.md](../../../../CLAUDE.md) - Project development guidelines
- [docs/developer/](../../../../docs/developer/) - Developer documentation
- [docs/reference/](../../../../docs/reference/) - Reference documentation

### Support
For questions, issues, or suggestions:
1. Check the relevant template's content first
2. Review PM Examples for similar scenarios
3. Consult parent PM_INSTRUCTIONS.md
4. Create issue in project repository

---

**Last Updated**: 2025-10-21
**Maintained By**: Claude MPM Development Team
**Status**: Active, Stable (v1.0.0)
