#!/bin/bash

cd /Users/masa/Projects/claude-mpm

echo "Staging all changes..."
git add .

echo "Committing changes..."
git commit -m "feat: comprehensive memory command implementation and system improvements

- Complete memory command implementation with MemoryManagementCommand class
- Enhanced CLI command structure with shared utilities and base classes  
- Improved agent deployment and configuration management
- Updated MCP gateway and service registry implementations
- Enhanced memory integration hooks and response tracking
- Added comprehensive documentation and development guides
- Improved build system and project structure
- Updated agent templates and configurations
- Enhanced service implementations across the system
- Added new shared utilities for CLI and services
- Improved error handling and logging throughout
- Updated configuration management and validation
- Enhanced testing infrastructure and utilities

This release includes the complete memory command functionality that was
missing from v4.0.24, along with numerous system improvements and
architectural enhancements."

echo "Bumping version to 4.0.25..."
cz bump --increment PATCH

echo "Creating tag..."
git tag v4.0.25

echo "Pushing to remote..."
git push origin main
git push origin --tags

echo "Done!"
