#!/bin/bash
# Rename template files from underscores to dashes for consistency with repository standard

set -e

cd "$(dirname "$0")/../src/claude_mpm/agents/templates"

echo "🔄 Renaming template files to use dashes instead of underscores..."

# Agent files
mv api_qa.md api-qa.md 2>/dev/null || true
mv code_analyzer.md code-analyzer.md 2>/dev/null || true
mv dart_engineer.md dart-engineer.md 2>/dev/null || true
mv data_engineer.md data-engineer.md 2>/dev/null || true
mv gcp_ops_agent.md gcp-ops.md 2>/dev/null || true
mv golang_engineer.md golang-engineer.md 2>/dev/null || true
mv java_engineer.md java-engineer.md 2>/dev/null || true
mv javascript_engineer_agent.md javascript-engineer.md 2>/dev/null || true
mv local_ops_agent.md local-ops.md 2>/dev/null || true
mv memory_manager.md memory-manager.md 2>/dev/null || true
mv nextjs_engineer.md nextjs-engineer.md 2>/dev/null || true
mv product_owner.md product-owner.md 2>/dev/null || true
mv project_organizer.md project-organizer.md 2>/dev/null || true
mv python_engineer.md python-engineer.md 2>/dev/null || true
mv react_engineer.md react-engineer.md 2>/dev/null || true
mv refactoring_engineer.md refactoring-engineer.md 2>/dev/null || true
mv rust_engineer.md rust-engineer.md 2>/dev/null || true
mv tauri_engineer.md tauri-engineer.md 2>/dev/null || true
mv typescript_engineer.md typescript-engineer.md 2>/dev/null || true
mv vercel_ops_agent.md vercel-ops.md 2>/dev/null || true
mv version_control.md version-control.md 2>/dev/null || true
mv web_qa.md web-qa.md 2>/dev/null || true
mv web_ui.md web-ui.md 2>/dev/null || true

# Internal documentation files (for consistency)
mv circuit_breakers.md circuit-breakers.md 2>/dev/null || true
mv git_file_tracking.md git-file-tracking.md 2>/dev/null || true
mv pm_examples.md pm-examples.md 2>/dev/null || true
mv pm_red_flags.md pm-red-flags.md 2>/dev/null || true
mv research_gate_examples.md research-gate-examples.md 2>/dev/null || true
mv response_format.md response-format.md 2>/dev/null || true
mv ticket_completeness_examples.md ticket-completeness-examples.md 2>/dev/null || true
mv validation_templates.md validation-templates.md 2>/dev/null || true

echo "✅ Template files renamed successfully"
echo ""
echo "Renamed files:"
ls -1 *-*.md | sort
