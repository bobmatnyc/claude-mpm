#!/usr/bin/env python3
"""
Agent Migration Script - Convert existing agents to new schema format.

This script migrates agent templates from the old format to the new
standardized schema with clean IDs and resource tiers.
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import shutil
import argparse

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.validation.agent_validator import AgentValidator, validate_agent_migration

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AgentMigrator:
    """Handles migration of agent templates to new schema format."""
    
    # Mapping of old agent types to clean IDs
    AGENT_ID_MAPPING = {
        "research_agent": "research",
        "engineer_agent": "engineer",
        "qa_agent": "qa",
        "security_agent": "security",
        "documentation_agent": "documentation",
        "version_control_agent": "version_control",
        "ops_agent": "ops",
        "data_engineer_agent": "data_engineer"
    }
    
    # Resource tier assignments based on agent type
    RESOURCE_TIER_MAPPING = {
        "research": "intensive",
        "engineer": "intensive",
        "data_engineer": "intensive",
        "qa": "standard",
        "security": "standard",
        "ops": "standard",
        "documentation": "lightweight",
        "version_control": "lightweight"
    }
    
    # Category mapping
    CATEGORY_MAPPING = {
        "research": "research",
        "engineer": "engineering",
        "data_engineer": "engineering",
        "qa": "quality",
        "security": "quality",
        "ops": "operations",
        "documentation": "specialized",
        "version_control": "specialized"
    }
    
    def __init__(self, templates_dir: Path, backup_dir: Optional[Path] = None):
        """Initialize the migrator."""
        self.templates_dir = templates_dir
        self.backup_dir = backup_dir or templates_dir / "backup"
        self.validator = AgentValidator()
        
    def backup_agents(self) -> None:
        """Create backup of all agent files."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for agent_file in self.templates_dir.glob("*.json"):
            if agent_file.name == "agent_schema.json":
                continue
            
            backup_path = self.backup_dir / f"{agent_file.stem}_{timestamp}.json"
            shutil.copy2(agent_file, backup_path)
            logger.info(f"Backed up {agent_file.name} to {backup_path}")
    
    def migrate_agent(self, old_agent: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Migrate a single agent to the new format."""
        # Determine clean agent ID
        agent_type = old_agent.get("agent_type", "")
        clean_id = self.AGENT_ID_MAPPING.get(agent_type, agent_type.replace("_agent", ""))
        
        # Extract instructions
        instructions = (
            old_agent.get("narrative_fields", {}).get("instructions", "") or
            old_agent.get("instructions", "") or
            ""
        )
        
        # Ensure instructions don't exceed 8000 characters
        if len(instructions) > 8000:
            logger.warning(f"Truncating instructions for {clean_id} from {len(instructions)} to 8000 characters")
            instructions = instructions[:7997] + "..."
        
        # Extract configuration fields
        config = old_agent.get("configuration_fields", {})
        
        # Build new agent structure
        new_agent = {
            "id": clean_id,
            "version": "1.0.0",
            "metadata": {
                "name": self._format_agent_name(clean_id),
                "description": config.get("description", f"{clean_id.title()} agent for Claude MPM"),
                "category": self.CATEGORY_MAPPING.get(clean_id, "specialized"),
                "tags": self._extract_tags(old_agent),
                "author": "Claude MPM Team",
                "created_at": datetime.utcnow().isoformat() + "Z",
                "updated_at": datetime.utcnow().isoformat() + "Z"
            },
            "capabilities": {
                "model": self._map_model_name(config.get("model", "claude-sonnet-4-20250514")),
                "tools": config.get("tools", []),
                "resource_tier": self.RESOURCE_TIER_MAPPING.get(clean_id, "standard"),
                "max_tokens": config.get("max_tokens", 8192),
                "temperature": config.get("temperature", 0.7),
                "timeout": config.get("timeout", 300),
                "memory_limit": self._get_memory_limit(clean_id),
                "cpu_limit": self._get_cpu_limit(clean_id),
                "network_access": config.get("network_access", False)
            },
            "instructions": instructions,
            "knowledge": self._extract_knowledge(old_agent),
            "interactions": self._extract_interactions(old_agent),
            "testing": self._create_default_testing(clean_id)
        }
        
        # Add file access if needed
        if any(tool in new_agent["capabilities"]["tools"] for tool in ["Read", "Write", "Edit"]):
            new_agent["capabilities"]["file_access"] = {
                "read_paths": ["./"],
                "write_paths": ["./"]
            }
        
        return new_agent
    
    def _format_agent_name(self, agent_id: str) -> str:
        """Format a human-readable name from agent ID."""
        return " ".join(word.capitalize() for word in agent_id.split("_")) + " Agent"
    
    def _extract_tags(self, old_agent: Dict[str, Any]) -> List[str]:
        """Extract and clean tags from old agent format."""
        tags = old_agent.get("configuration_fields", {}).get("tags", [])
        
        # Clean tags to match pattern
        clean_tags = []
        for tag in tags:
            # Convert to lowercase and replace spaces/special chars with hyphens
            clean_tag = tag.lower().replace(" ", "-").replace("_", "-")
            clean_tag = "".join(c for c in clean_tag if c.isalnum() or c == "-")
            if clean_tag and clean_tag[0].isalpha():
                clean_tags.append(clean_tag)
        
        return clean_tags[:10]  # Max 10 tags
    
    def _map_model_name(self, old_model: str) -> str:
        """Map old model names to valid schema values."""
        # Handle various model name formats
        model_mapping = {
            "claude-4-opus": "claude-opus-4-20250514",
            "claude-4-sonnet": "claude-sonnet-4-20250514",
            "claude-3-haiku": "claude-3-haiku-20240307",
            "claude-3-sonnet": "claude-3-sonnet-20240229",
            "claude-3-opus": "claude-3-opus-20240229"
        }
        
        # Check for exact match first
        if old_model in model_mapping.values():
            return old_model
        
        # Check for mapping
        for old, new in model_mapping.items():
            if old in old_model:
                return new
        
        # Default to sonnet
        return "claude-sonnet-4-20250514"
    
    def _get_memory_limit(self, agent_id: str) -> int:
        """Get memory limit based on resource tier."""
        tier = self.RESOURCE_TIER_MAPPING.get(agent_id, "standard")
        limits = {
            "intensive": 6144,
            "standard": 3072,
            "lightweight": 1024
        }
        return limits.get(tier, 3072)
    
    def _get_cpu_limit(self, agent_id: str) -> int:
        """Get CPU limit based on resource tier."""
        tier = self.RESOURCE_TIER_MAPPING.get(agent_id, "standard")
        limits = {
            "intensive": 80,
            "standard": 50,
            "lightweight": 20
        }
        return limits.get(tier, 50)
    
    def _extract_knowledge(self, old_agent: Dict[str, Any]) -> Dict[str, Any]:
        """Extract knowledge section from old agent format."""
        narrative = old_agent.get("narrative_fields", {})
        
        return {
            "domain_expertise": narrative.get("specialized_knowledge", []),
            "best_practices": narrative.get("unique_capabilities", []),
            "constraints": [],  # Will be populated based on agent type
            "examples": []  # Can be added later
        }
    
    def _extract_interactions(self, old_agent: Dict[str, Any]) -> Dict[str, Any]:
        """Extract interaction patterns from old agent format."""
        # Determine handoff agents based on agent type
        agent_type = old_agent.get("agent_type", "")
        clean_id = self.AGENT_ID_MAPPING.get(agent_type, agent_type.replace("_agent", ""))
        
        handoff_mapping = {
            "research": ["engineer", "qa"],
            "engineer": ["qa", "security", "documentation"],
            "qa": ["engineer", "security"],
            "security": ["engineer", "ops"],
            "documentation": ["version_control"],
            "version_control": ["documentation"],
            "ops": ["engineer", "security"],
            "data_engineer": ["engineer", "ops"]
        }
        
        return {
            "input_format": {
                "required_fields": ["task"],
                "optional_fields": ["context", "constraints"]
            },
            "output_format": {
                "structure": "markdown",
                "includes": ["analysis", "recommendations", "code"]
            },
            "handoff_agents": handoff_mapping.get(clean_id, []),
            "triggers": []
        }
    
    def _create_default_testing(self, agent_id: str) -> Dict[str, Any]:
        """Create default testing configuration."""
        return {
            "test_cases": [{
                "name": f"Basic {agent_id} task",
                "input": f"Perform a basic {agent_id} analysis",
                "expected_behavior": f"Agent performs {agent_id} tasks correctly",
                "validation_criteria": ["completes_task", "follows_format"]
            }],
            "performance_benchmarks": {
                "response_time": 300,
                "token_usage": 8192,
                "success_rate": 0.95
            }
        }
    
    def migrate_all(self, dry_run: bool = False) -> Tuple[int, int, List[str]]:
        """
        Migrate all agent files in the templates directory.
        
        Returns:
            Tuple of (success_count, failure_count, error_messages)
        """
        if not dry_run:
            self.backup_agents()
        
        success_count = 0
        failure_count = 0
        error_messages = []
        
        for agent_file in sorted(self.templates_dir.glob("*.json")):
            if agent_file.name == "agent_schema.json":
                continue
            
            logger.info(f"Processing {agent_file.name}")
            
            try:
                # Load old agent
                with open(agent_file, 'r') as f:
                    old_agent = json.load(f)
                
                # Migrate to new format
                new_agent = self.migrate_agent(old_agent, agent_file.name)
                
                # Validate new format
                validation_result = self.validator.validate_agent(new_agent)
                
                if not validation_result.is_valid:
                    failure_count += 1
                    for error in validation_result.errors:
                        error_msg = f"{agent_file.name}: {error}"
                        error_messages.append(error_msg)
                        logger.error(error_msg)
                    continue
                
                # Validate migration compatibility
                migration_result = validate_agent_migration(old_agent, new_agent)
                if migration_result.warnings:
                    for warning in migration_result.warnings:
                        logger.warning(f"{agent_file.name}: {warning}")
                
                if not dry_run:
                    # Write new agent file
                    new_filename = f"{new_agent['id']}.json"
                    new_path = self.templates_dir / new_filename
                    
                    with open(new_path, 'w') as f:
                        json.dump(new_agent, f, indent=2)
                    
                    # Remove old file if filename changed
                    if new_filename != agent_file.name:
                        agent_file.unlink()
                        logger.info(f"Renamed {agent_file.name} to {new_filename}")
                
                success_count += 1
                logger.info(f"Successfully migrated {agent_file.name}")
                
            except Exception as e:
                failure_count += 1
                error_msg = f"{agent_file.name}: Migration failed - {str(e)}"
                error_messages.append(error_msg)
                logger.error(error_msg)
        
        return success_count, failure_count, error_messages


def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(description="Migrate agent templates to new schema format")
    parser.add_argument(
        "--templates-dir",
        type=Path,
        default=Path(__file__).parent.parent / "src" / "claude_mpm" / "agents" / "templates",
        help="Directory containing agent templates"
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        help="Directory for backups (default: templates_dir/backup)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate migration without making changes"
    )
    
    args = parser.parse_args()
    
    # Create migrator
    migrator = AgentMigrator(args.templates_dir, args.backup_dir)
    
    # Run migration
    logger.info(f"Starting agent migration {'(DRY RUN)' if args.dry_run else ''}")
    success, failure, errors = migrator.migrate_all(dry_run=args.dry_run)
    
    # Report results
    logger.info(f"\nMigration complete:")
    logger.info(f"  Success: {success}")
    logger.info(f"  Failure: {failure}")
    
    if errors:
        logger.error("\nErrors encountered:")
        for error in errors:
            logger.error(f"  - {error}")
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()