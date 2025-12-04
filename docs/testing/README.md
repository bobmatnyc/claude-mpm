# Testing & QA Documentation

Unified testing, QA, and verification documentation for Claude MPM framework.

## Purpose

This directory contains all testing-related documentation including:
- Test reports and execution results
- QA certification and verification reports
- Testing standards and best practices
- Verification procedures and results

## Directory Structure

### `/reports/` - Test Reports & QA Documentation

Test execution reports, QA reports, and certification documents. Contains:

- **Agent Testing**: Agent deployment, dependency, and functionality tests
- **Feature Testing**: Structured questions, fallback mechanisms, output styles
- **QA Reports**: Quality assurance certification and verification reports
- **Integration Testing**: Cache consolidation, git workflow, unified config tests
- **Release Testing**: Phase-based test reports (Phase 1-3)

Key files:
- **[QA_TEST_INDEX.md](./QA_TEST_INDEX.md)** - Master index of all QA test reports
- **[QA_CERTIFICATION_REPORT.md](./reports/QA_CERTIFICATION_REPORT.md)** - Overall QA certification status
- **[QA_EXECUTIVE_SUMMARY.md](./reports/QA_EXECUTIVE_SUMMARY.md)** - Executive summary of QA status
- **[TEST_EXECUTION_REPORT.md](./reports/TEST_EXECUTION_REPORT.md)** - Test execution results

### `/verification/` - Verification Reports

Detailed verification reports for specific features and fixes:

- **[qa-report-1M-446.md](./verification/qa-report-1M-446.md)** - Ticket 1M-446 QA verification
- **[qa-report-git-sources-verification.md](./verification/qa-report-git-sources-verification.md)** - Git sources verification
- **[auto-save-verification.md](./verification/auto-save-verification.md)** - Auto-save functionality verification
- **[monitor-verification.md](./verification/monitor-verification.md)** - Monitor command verification
- **[resume-log-verification.md](./verification/resume-log-verification.md)** - Resume log verification
- **[skills-version-tracking.md](./verification/skills-version-tracking.md)** - Skills version tracking verification
- **[agent-name-parsing-fix.md](./verification/agent-name-parsing-fix.md)** - Agent name parsing fix verification
- **[README.md](./verification/README.md)** - Verification reports index

### `/summaries/` - Test Summaries

Concise summaries of testing phases and major test initiatives:

- **[phase3-git-sync-summary.md](./summaries/phase3-git-sync-summary.md)** - Phase 3 git sync testing summary

### `/guides/` - Testing Guides

Testing best practices, standards, and how-to guides (to be populated).

### `/standards/` - Testing Standards

Testing standards, conventions, and requirements (to be populated).

## Quick Links

### Most Important Documents

1. **[QA_TEST_INDEX.md](./QA_TEST_INDEX.md)** - Start here: master index of all tests
2. **[QA_CERTIFICATION_REPORT.md](./reports/QA_CERTIFICATION_REPORT.md)** - Overall certification status
3. **[QA_EXECUTIVE_SUMMARY.md](./reports/QA_EXECUTIVE_SUMMARY.md)** - High-level QA summary

### By Testing Phase

- **Phase 1-2**: [1M-502-phase-1-2-test-report.md](./reports/1M-502-phase-1-2-test-report.md)
- **Phase 3**: [phase3-git-sync-qa-report.md](./reports/phase3-git-sync-qa-report.md), [phase3-git-sync-summary.md](./summaries/phase3-git-sync-summary.md)

### By Feature

- **Agent System**: [AGENT_DEPLOYMENT_TEST_REPORT.md](./reports/AGENT_DEPLOYMENT_TEST_REPORT.md), [agent-dependency-yaml-qa-report-2025-11-29.md](./reports/agent-dependency-yaml-qa-report-2025-11-29.md)
- **Cache System**: [QA_CACHE_CONSOLIDATION_REPORT.md](./reports/QA_CACHE_CONSOLIDATION_REPORT.md), [QA_REPORT_CACHE_GIT_WORKFLOW.md](./reports/QA_REPORT_CACHE_GIT_WORKFLOW.md)
- **Configuration**: [QA_TEST_REPORT_UNIFIED_CONFIG.md](./reports/QA_TEST_REPORT_UNIFIED_CONFIG.md), [QA_SUMMARY_UNIFIED_CONFIG.md](./reports/QA_SUMMARY_UNIFIED_CONFIG.md)
- **CLI/UX**: [QA_FINAL_REPORT_AGENTS_CLI_REDESIGN.md](./reports/QA_FINAL_REPORT_AGENTS_CLI_REDESIGN.md), [QA_PROGRESS_INDICATORS_TEST_REPORT.md](./reports/QA_PROGRESS_INDICATORS_TEST_REPORT.md)

## Related Documentation

- **[../reports/](../reports/README.md)** - General project reports (implementation, status, updates)
- **[../developer/](../developer/README.md)** - Developer documentation
- **[../user/](../user/README.md)** - User-facing documentation

## Consolidated Directories

This directory consolidates testing/QA documentation from:
- `docs/qa/` (deprecated, moved 2025-12-04)
- `docs/reports/qa/` (deprecated, moved 2025-12-04)
- `docs/developer/verification-reports/` (moved 2025-12-04)
- `docs/testing/` (original location, reorganized 2025-12-04)

See [MIGRATION_LOG.md](../MIGRATION_LOG.md) for consolidation details.

---

**Last Updated**: 2025-12-04 (Phase 2 Consolidation)
