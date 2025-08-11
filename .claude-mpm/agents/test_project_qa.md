---
description: "Project-specific QA Agent for Local Testing"
version: "2.0.0"
tools: ["testing", "validation", "quality_assurance"]
metadata:
  tier: "project"
  source: "local"
---

# Test Project QA Agent

## Description
This is a project-specific QA agent used for testing local agent deployment functionality. It should take precedence over any system-level QA agents when running in this project.

## Capabilities
- Local project testing
- Custom validation rules
- Project-specific quality checks

## Version
2.0.0 (Higher than default system agent to verify precedence)

## Authority
Full authority for project-specific QA operations.