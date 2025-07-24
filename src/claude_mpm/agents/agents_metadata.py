#!/usr/bin/env python3
"""
Agent Metadata Definitions
=========================

Preserves AGENT_CONFIG metadata for all agents.
This metadata is used for agent registration, capability tracking, and performance targets.
"""

# Documentation Agent Metadata
DOCUMENTATION_CONFIG = {
    "name": "documentation_agent",
    "version": "1.0.0",
    "type": "core_agent",
    "capabilities": [
        "documentation_analysis",
        "changelog_generation",
        "release_notes",
        "api_documentation",
        "version_documentation",
        "operational_docs",
        "quality_assurance"
    ],
    "primary_interface": "documentation_management",
    "performance_targets": {
        "changelog_generation": "5m",
        "documentation_update": "24h",
        "coverage_target": "90%"
    }
}


# Version Control Agent Metadata
VERSION_CONTROL_CONFIG = {
    "name": "version_control_agent",
    "version": "2.0.0",
    "type": "core_agent",
    "capabilities": [
        "git_operations",
        "branch_management",
        "merge_conflict_resolution",
        "semantic_versioning",
        "tag_management",
        "release_coordination",
        "version_file_updates"
    ],
    "primary_interface": "git_cli",
    "performance_targets": {
        "branch_creation": "5s",
        "merge_operation": "30s",
        "version_bump": "10s",
        "conflict_resolution": "5m"
    }
}

# QA Agent Metadata
QA_CONFIG = {
    "name": "qa_agent",
    "version": "1.0.0",
    "type": "core_agent",
    "capabilities": [
        "test_execution",
        "quality_validation",
        "coverage_analysis",
        "performance_testing",
        "security_testing",
        "regression_testing",
        "test_automation"
    ],
    "primary_interface": "testing_framework",
    "performance_targets": {
        "unit_test_suite": "5m",
        "integration_tests": "15m",
        "full_test_suite": "30m",
        "coverage_target": "80%"
    }
}

# Research Agent Metadata
RESEARCH_CONFIG = {
    "name": "research_agent",
    "version": "1.0.0",
    "type": "core_agent",
    "capabilities": [
        "technology_research",
        "library_analysis",
        "best_practices_research",
        "performance_analysis",
        "security_research",
        "market_analysis",
        "feasibility_studies"
    ],
    "primary_interface": "research_tools",
    "performance_targets": {
        "quick_research": "15m",
        "deep_analysis": "2h",
        "comprehensive_report": "24h"
    }
}

# Ops Agent Metadata
OPS_CONFIG = {
    "name": "ops_agent",
    "version": "1.0.0",
    "type": "core_agent",
    "capabilities": [
        "deployment_automation",
        "infrastructure_management",
        "monitoring_setup",
        "ci_cd_pipeline",
        "containerization",
        "cloud_services",
        "performance_optimization"
    ],
    "primary_interface": "deployment_tools",
    "performance_targets": {
        "deployment": "10m",
        "rollback": "5m",
        "infrastructure_update": "30m",
        "monitoring_setup": "1h"
    }
}

# Security Agent Metadata
SECURITY_CONFIG = {
    "name": "security_agent",
    "version": "1.0.0",
    "type": "core_agent",
    "capabilities": [
        "vulnerability_assessment",
        "security_audit",
        "penetration_testing",
        "code_security_review",
        "dependency_scanning",
        "security_patching",
        "compliance_checking"
    ],
    "primary_interface": "security_tools",
    "performance_targets": {
        "quick_scan": "10m",
        "full_audit": "2h",
        "penetration_test": "4h",
        "dependency_scan": "30m"
    }
}

# Engineer Agent Metadata
ENGINEER_CONFIG = {
    "name": "engineer_agent",
    "version": "1.0.0",
    "type": "core_agent",
    "capabilities": [
        "code_implementation",
        "feature_development",
        "bug_fixing",
        "code_refactoring",
        "performance_optimization",
        "api_development",
        "database_design"
    ],
    "primary_interface": "development_tools",
    "performance_targets": {
        "feature_implementation": "4h",
        "bug_fix": "1h",
        "code_review": "30m",
        "refactoring": "2h"
    }
}

# Data Engineer Agent Metadata
DATA_ENGINEER_CONFIG = {
    "name": "data_engineer_agent",
    "version": "1.0.0",
    "type": "core_agent",
    "capabilities": [
        "data_store_management",
        "ai_api_integration",
        "data_pipeline_design",
        "database_optimization",
        "data_migration",
        "api_key_management",
        "data_analytics",
        "schema_design"
    ],
    "primary_interface": "data_management_tools",
    "performance_targets": {
        "pipeline_setup": "2h",
        "data_migration": "4h",
        "api_integration": "1h",
        "schema_update": "30m"
    }
}

# Aggregate all configs for easy access
ALL_AGENT_CONFIGS = {
    "documentation": DOCUMENTATION_CONFIG,
    "version_control": VERSION_CONTROL_CONFIG,
    "qa": QA_CONFIG,
    "research": RESEARCH_CONFIG,
    "ops": OPS_CONFIG,
    "security": SECURITY_CONFIG,
    "engineer": ENGINEER_CONFIG,
    "data_engineer": DATA_ENGINEER_CONFIG
}