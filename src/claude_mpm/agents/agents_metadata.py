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
        "quality_assurance",
    ],
    "primary_interface": "documentation_management",
    "performance_targets": {
        "changelog_generation": "5m",
        "documentation_update": "24h",
        "coverage_target": "90%",
    },
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
        "version_file_updates",
    ],
    "primary_interface": "git_cli",
    "performance_targets": {
        "branch_creation": "5s",
        "merge_operation": "30s",
        "version_bump": "10s",
        "conflict_resolution": "5m",
    },
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
        "test_automation",
    ],
    "primary_interface": "testing_framework",
    "performance_targets": {
        "unit_test_suite": "5m",
        "integration_tests": "15m",
        "full_test_suite": "30m",
        "coverage_target": "80%",
    },
}

# API QA Agent Metadata
API_QA_CONFIG = {
    "name": "api_qa_agent",
    "version": "1.0.0",
    "type": "core_agent",
    "capabilities": [
        "rest_api_testing",
        "graphql_testing",
        "endpoint_validation",
        "authentication_testing",
        "authorization_testing",
        "contract_testing",
        "load_testing",
        "api_performance_testing",
    ],
    "primary_interface": "api_testing_framework",
    "performance_targets": {
        "endpoint_validation": "2m",
        "auth_flow_testing": "5m",
        "load_testing": "10m",
        "contract_validation": "5m",
        "response_time_target": "200ms",
    },
}

# Web QA Agent Metadata
WEB_QA_CONFIG = {
    "name": "web_qa_agent",
    "version": "1.0.0",
    "type": "core_agent",
    "capabilities": [
        "browser_automation",
        "e2e_testing",
        "ui_testing",
        "responsive_testing",
        "accessibility_testing",
        "cross_browser_testing",
        "performance_testing",
        "visual_regression",
    ],
    "primary_interface": "browser_testing_framework",
    "performance_targets": {
        "e2e_test_suite": "15m",
        "accessibility_audit": "5m",
        "cross_browser_test": "20m",
        "page_load_target": "2.5s",
        "lighthouse_score": "90",
    },
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
        "feasibility_studies",
    ],
    "primary_interface": "research_tools",
    "performance_targets": {
        "quick_research": "15m",
        "deep_analysis": "2h",
        "comprehensive_report": "24h",
    },
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
        "performance_optimization",
    ],
    "primary_interface": "deployment_tools",
    "performance_targets": {
        "deployment": "10m",
        "rollback": "5m",
        "infrastructure_update": "30m",
        "monitoring_setup": "1h",
    },
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
        "compliance_checking",
    ],
    "primary_interface": "security_tools",
    "performance_targets": {
        "quick_scan": "10m",
        "full_audit": "2h",
        "penetration_test": "4h",
        "dependency_scan": "30m",
    },
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
        "database_design",
    ],
    "primary_interface": "development_tools",
    "performance_targets": {
        "feature_implementation": "4h",
        "bug_fix": "1h",
        "code_review": "30m",
        "refactoring": "2h",
    },
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
        "schema_design",
    ],
    "primary_interface": "data_management_tools",
    "performance_targets": {
        "pipeline_setup": "2h",
        "data_migration": "4h",
        "api_integration": "1h",
        "schema_update": "30m",
    },
}

# Project Organizer Agent Metadata
PROJECT_ORGANIZER_CONFIG = {
    "name": "project_organizer_agent",
    "version": "1.0.0",
    "type": "core_agent",
    "capabilities": [
        "pattern_detection",
        "file_organization",
        "structure_validation",
        "convention_enforcement",
        "batch_reorganization",
        "framework_recognition",
        "documentation_maintenance",
    ],
    "primary_interface": "organization_tools",
    "performance_targets": {
        "structure_analysis": "2m",
        "file_placement": "10s",
        "validation_scan": "5m",
        "batch_reorganization": "15m",
    },
}

# ImageMagick Agent Metadata
IMAGEMAGICK_CONFIG = {
    "name": "imagemagick_agent",
    "version": "1.0.0",
    "type": "optimization_agent",
    "capabilities": [
        "image_optimization",
        "format_conversion",
        "responsive_image_generation",
        "batch_processing",
        "web_performance_optimization",
        "core_web_vitals_improvement",
        "avif_webp_conversion",
        "quality_compression",
    ],
    "primary_interface": "imagemagick_cli",
    "performance_targets": {
        "single_image_optimization": "30s",
        "batch_processing_100_images": "10m",
        "format_conversion": "10s",
        "responsive_set_generation": "60s",
        "file_size_reduction": "50-70%",
        "quality_threshold": "0.95_ssim",
    },
}

# Agentic Coder Optimizer Agent Metadata
AGENTIC_CODER_OPTIMIZER_CONFIG = {
    "name": "agentic_coder_optimizer_agent",
    "version": "1.0.0",
    "type": "optimization_agent",
    "capabilities": [
        "project_optimization",
        "documentation_standardization",
        "workflow_unification",
        "build_system_optimization",
        "developer_experience_improvement",
        "agentic_workflow_design",
        "quality_tooling_setup",
        "version_management_setup",
    ],
    "primary_interface": "project_optimization_tools",
    "performance_targets": {
        "project_analysis": "10m",
        "documentation_optimization": "30m",
        "workflow_standardization": "1h",
        "setup_time_reduction": "80%",
        "command_unification_rate": "90%",
        "onboarding_improvement": "5x_faster",
    },
}

# Agent Manager Agent Metadata
AGENT_MANAGER_CONFIG = {
    "name": "agent_manager",
    "version": "2.0.0",
    "type": "system_agent",
    "capabilities": [
        "agent_creation",
        "variant_management",
        "pm_configuration",
        "deployment_control",
        "hierarchy_management",
        "template_generation",
        "agent_validation",
        "version_precedence_resolution",
        "yaml_configuration_management",
        "instruction_customization",
    ],
    "primary_interface": "agent_lifecycle_management",
    "performance_targets": {
        "agent_creation": "30s",
        "deployment_operation": "10s",
        "validation_check": "5s",
        "pm_instruction_update": "15s",
        "version_conflict_resolution": "5s",
        "template_generation": "20s",
        "configuration_validation": "3s",
    },
}

# Aggregate all configs for easy access
ALL_AGENT_CONFIGS = {
    "documentation": DOCUMENTATION_CONFIG,
    "version_control": VERSION_CONTROL_CONFIG,
    "qa": QA_CONFIG,
    "api_qa": API_QA_CONFIG,
    "web_qa": WEB_QA_CONFIG,
    "research": RESEARCH_CONFIG,
    "ops": OPS_CONFIG,
    "security": SECURITY_CONFIG,
    "engineer": ENGINEER_CONFIG,
    "data_engineer": DATA_ENGINEER_CONFIG,
    "project_organizer": PROJECT_ORGANIZER_CONFIG,
    "imagemagick": IMAGEMAGICK_CONFIG,
    "agentic_coder_optimizer": AGENTIC_CODER_OPTIMIZER_CONFIG,
    "agent_manager": AGENT_MANAGER_CONFIG,
}
