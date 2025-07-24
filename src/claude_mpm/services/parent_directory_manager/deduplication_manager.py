#!/usr/bin/env python3
"""
Deduplication Manager - Handles INSTRUCTIONS.md/CLAUDE.md file deduplication in parent directory hierarchy
================================================================================

This module manages the deduplication of INSTRUCTIONS.md (and legacy CLAUDE.md) files 
to prevent duplicate context loading in Claude Code.

Business Logic:
- Walk up the directory tree to find all INSTRUCTIONS.md and CLAUDE.md files
- Identify framework deployment templates vs project files
- Keep only the rootmost framework template
- Preserve all project-specific INSTRUCTIONS.md/CLAUDE.md files
"""

import os
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
import logging


class DeduplicationManager:
    """Manages deduplication of INSTRUCTIONS.md/CLAUDE.md files in parent directories."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the Deduplication Manager.

        Args:
            logger: Logger instance to use
        """
        self.logger = logger or logging.getLogger(__name__)

    async def deduplicate_claude_md_files(
        self,
        is_framework_template_func,
        extract_version_func,
        compare_versions_func,
        create_backup_func
    ) -> List[Tuple[Path, str]]:
        """
        Deduplicate INSTRUCTIONS.md/CLAUDE.md files in parent directory hierarchy.
        
        BUSINESS LOGIC:
        1. Walk up the directory tree from current working directory to root
        2. Find ALL INSTRUCTIONS.md and CLAUDE.md files in this parent hierarchy
        3. Identify which files are framework deployment templates vs project files
           - Framework templates have title "# Claude PM Framework Configuration - Deployment"
           - Project files (like orchestration test projects) are preserved
        4. Among framework templates, find the one with the newest version
        5. Keep ONLY the rootmost (highest in hierarchy) framework template
        6. Update the rootmost template to the newest version if needed
        7. Backup and remove all other framework templates
        8. Never touch project CLAUDE.md files
        
        RATIONALE:
        - Claude Code loads ALL CLAUDE.md files it finds in the directory tree
        - Multiple framework templates cause duplicated context
        - Only one framework template should exist at the rootmost location
        - Project-specific CLAUDE.md files serve different purposes and must be preserved
        
        Args:
            is_framework_template_func: Function to check if content is framework template
            extract_version_func: Function to extract version from content
            compare_versions_func: Function to compare two version strings
            create_backup_func: Function to create backup of a file
        
        Returns:
            List of tuples (original_path, action_taken) for logging
        """
        deduplication_actions = []
        
        try:
            self.logger.info("🔍 Starting INSTRUCTIONS.md/CLAUDE.md deduplication scan...")
            
            # STEP 1: Walk up the directory tree from current directory to root
            current_path = Path.cwd()
            claude_md_files = []
            
            # Collect ALL INSTRUCTIONS.md and CLAUDE.md files found while walking up parent directories
            while current_path != current_path.parent:  # Stop at root
                # Check for INSTRUCTIONS.md first
                instructions_path = current_path / "INSTRUCTIONS.md"
                if instructions_path.exists() and instructions_path.is_file():
                    claude_md_files.append(instructions_path)
                    self.logger.debug(f"Found INSTRUCTIONS.md at: {instructions_path}")
                else:
                    # Check for legacy CLAUDE.md
                    claude_md_path = current_path / "CLAUDE.md"
                    if claude_md_path.exists() and claude_md_path.is_file():
                        claude_md_files.append(claude_md_path)
                        self.logger.debug(f"Found CLAUDE.md at: {claude_md_path}")
                current_path = current_path.parent
            
            # Check root directory as well
            root_instructions = current_path / "INSTRUCTIONS.md"
            if root_instructions.exists() and root_instructions.is_file():
                claude_md_files.append(root_instructions)
                self.logger.debug(f"Found INSTRUCTIONS.md at root: {root_instructions}")
            else:
                # Check for legacy CLAUDE.md at root
                root_claude_md = current_path / "CLAUDE.md"
                if root_claude_md.exists() and root_claude_md.is_file():
                    claude_md_files.append(root_claude_md)
                    self.logger.debug(f"Found CLAUDE.md at root: {root_claude_md}")
            
            # If we found 0 or 1 files, there's nothing to deduplicate
            if len(claude_md_files) <= 1:
                self.logger.info("✅ No duplicate INSTRUCTIONS.md/CLAUDE.md files found in parent hierarchy")
                return deduplication_actions
            
            # STEP 2: Sort by path depth (rootmost first)
            claude_md_files.sort(key=lambda p: len(p.parts))
            
            self.logger.info(f"📊 Found {len(claude_md_files)} INSTRUCTIONS.md/CLAUDE.md files in parent hierarchy")
            
            # STEP 3: First pass - analyze all files to categorize and find newest version
            framework_templates = []
            newest_version = None
            newest_content = None
            
            for file_path in claude_md_files:
                try:
                    content = file_path.read_text()
                    # Check if this is a framework deployment template
                    is_framework_template = is_framework_template_func(content)
                    
                    if is_framework_template:
                        # Extract version from CLAUDE_MD_VERSION metadata
                        version = extract_version_func(content)
                        framework_templates.append((file_path, content, version))
                        
                        # Track the newest version we've seen
                        if version and (newest_version is None or compare_versions_func(version, newest_version) > 0):
                            newest_version = version
                            newest_content = content
                            self.logger.info(f"📋 Found newer version {version} at: {file_path}")
                except Exception as e:
                    self.logger.error(f"Failed to analyze {file_path}: {e}")
            
            # STEP 4: Second pass - process files based on our analysis
            for idx, file_path in enumerate(claude_md_files):
                try:
                    content = file_path.read_text()
                    is_framework_template = is_framework_template_func(content)
                    
                    if idx == 0:
                        # This is the ROOTMOST file
                        if is_framework_template:
                            current_version = extract_version_func(content)
                            
                            # Check if we found a newer version elsewhere that we should update to
                            if newest_version and current_version and compare_versions_func(newest_version, current_version) > 0:
                                # We found a newer version in a subdirectory - update the rootmost file
                                
                                # First backup the current rootmost file
                                backup_path = await create_backup_func(file_path)
                                if backup_path:
                                    self.logger.info(f"📁 Backed up current rootmost file before update: {backup_path}")
                                
                                # Update with the newest content we found
                                file_path.write_text(newest_content)
                                self.logger.info(f"⬆️ Updated rootmost template from {current_version} to {newest_version}")
                                deduplication_actions.append((file_path, f"updated from {current_version} to {newest_version}"))
                            else:
                                # Rootmost file already has the newest version (or versions are equal)
                                self.logger.info(f"✅ Keeping primary framework template at: {file_path} (version {current_version})")
                                deduplication_actions.append((file_path, "kept as primary"))
                        else:
                            # Rootmost file is NOT a framework template - this is unusual but we preserve it
                            self.logger.info(f"⚠️ File at {file_path} is not a framework template - skipping")
                            deduplication_actions.append((file_path, "skipped - not framework template"))
                    else:
                        # This is NOT the rootmost file
                        if is_framework_template:
                            # This is a REDUNDANT framework template that must be removed
                            
                            # Generate backup filename with timestamp
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            backup_name = f"CLAUDE.md.backup_{timestamp}"
                            backup_path = file_path.parent / backup_name
                            
                            # Handle duplicate timestamps (rare but possible)
                            counter = 1
                            while backup_path.exists():
                                backup_name = f"CLAUDE.md.backup_{timestamp}_{counter:02d}"
                                backup_path = file_path.parent / backup_name
                                counter += 1
                            
                            # Rename the duplicate to backup
                            file_path.rename(backup_path)
                            self.logger.warning(f"📦 Backed up duplicate framework template: {file_path} → {backup_path}")
                            deduplication_actions.append((file_path, f"backed up to {backup_path.name}"))
                        else:
                            # This is a PROJECT-SPECIFIC CLAUDE.md file - NEVER REMOVE THESE
                            self.logger.info(f"🛡️ Preserving non-framework file at: {file_path}")
                            deduplication_actions.append((file_path, "preserved - not framework template"))
                            
                except Exception as file_error:
                    self.logger.error(f"Failed to process file {file_path}: {file_error}")
                    deduplication_actions.append((file_path, f"error: {str(file_error)}"))
            
            # Log summary
            backed_up_count = sum(1 for _, action in deduplication_actions if "backed up" in action)
            if backed_up_count > 0:
                self.logger.info(f"✅ Deduplication complete: {backed_up_count} duplicate framework templates backed up")
            else:
                self.logger.info("✅ Deduplication complete: No framework template duplicates needed backing up")
                
        except Exception as e:
            self.logger.error(f"Failed during CLAUDE.md deduplication: {e}")
            
        return deduplication_actions

    async def deduplicate_parent_claude_md(
        self,
        is_framework_template_func,
        extract_version_func,
        compare_versions_func,
        create_backup_func
    ) -> Dict[str, Any]:
        """
        Public method to manually trigger CLAUDE.md deduplication in parent hierarchy.
        
        Args:
            is_framework_template_func: Function to check if content is framework template
            extract_version_func: Function to extract version from content
            compare_versions_func: Function to compare two version strings
            create_backup_func: Function to create backup of a file
        
        Returns:
            Dictionary with deduplication results
        """
        try:
            self.logger.info("🔧 Manual CLAUDE.md deduplication requested")
            
            # Run deduplication
            actions = await self.deduplicate_claude_md_files(
                is_framework_template_func,
                extract_version_func,
                compare_versions_func,
                create_backup_func
            )
            
            # Build result summary
            result = {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "actions_taken": len(actions),
                "details": []
            }
            
            for file_path, action in actions:
                result["details"].append({
                    "file": str(file_path),
                    "action": action
                })
            
            # Count different action types
            action_summary = {
                "kept_primary": sum(1 for _, a in actions if "kept as primary" in a),
                "backed_up": sum(1 for _, a in actions if "backed up" in a),
                "preserved": sum(1 for _, a in actions if "preserved" in a),
                "skipped": sum(1 for _, a in actions if "skipped" in a),
                "errors": sum(1 for _, a in actions if "error:" in a)
            }
            
            result["summary"] = action_summary
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to run manual deduplication: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }