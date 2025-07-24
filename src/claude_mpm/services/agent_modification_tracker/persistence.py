#!/usr/bin/env python3
"""
Persistence layer for modification history.

This module handles saving and loading modification history to/from disk,
maintaining persistent state across sessions.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

from .models import AgentModification, ModificationHistory
from ...utils.path_operations import path_ops


class PersistenceManager:
    """Manager for persisting modification history and state."""
    
    def __init__(self, persistence_root: Path):
        self.logger = logging.getLogger(__name__)
        self.persistence_root = persistence_root
        self.history_root = persistence_root / 'history'
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Ensure persistence directories exist."""
        directories = [
            self.persistence_root,
            self.history_root,
            self.persistence_root / 'agents',
            self.persistence_root / 'config'
        ]
        
        for directory in directories:
            path_ops.ensure_dir(directory)
        
        self.logger.debug(f"Created persistence directories at {self.persistence_root}")
    
    async def save_modification_history(self, 
                                      modification_history: Dict[str, ModificationHistory],
                                      active_modifications: Dict[str, AgentModification]) -> None:
        """Persist modification history to disk."""
        try:
            # Save modification history
            history_file = self.history_root / 'modification_history.json'
            history_data = {}
            
            for agent_name, history in modification_history.items():
                history_data[agent_name] = {
                    'agent_name': history.agent_name,
                    'total_modifications': history.total_modifications,
                    'first_seen': history.first_seen,
                    'last_modified': history.last_modified,
                    'current_version': history.current_version,
                    'modifications': [mod.to_dict() for mod in history.modifications]
                }
            
            path_ops.safe_write(history_file, json.dumps(history_data, indent=2, default=str))
            
            # Save active modifications
            active_file = self.persistence_root / 'active_modifications.json'
            active_data = {
                mod_id: mod.to_dict() 
                for mod_id, mod in active_modifications.items()
            }
            
            path_ops.safe_write(active_file, json.dumps(active_data, indent=2, default=str))
            
            self.logger.debug(f"Persisted {len(modification_history)} agent histories")
            
        except Exception as e:
            self.logger.error(f"Failed to persist modification history: {e}")
    
    async def load_modification_history(self) -> tuple[Dict[str, ModificationHistory], Dict[str, AgentModification]]:
        """Load existing modification history from disk."""
        modification_history = {}
        active_modifications = {}
        
        try:
            # Load modification history
            history_file = self.history_root / 'modification_history.json'
            if path_ops.validate_exists(history_file):
                history_content = path_ops.safe_read(history_file)
                if history_content:
                    history_data = json.loads(history_content)
                
                for agent_name, data in history_data.items():
                    history = ModificationHistory(
                        agent_name=data['agent_name'],
                        total_modifications=data['total_modifications'],
                        first_seen=data.get('first_seen'),
                        last_modified=data.get('last_modified'),
                        current_version=data.get('current_version')
                    )
                    
                    # Load modifications
                    for mod_data in data.get('modifications', []):
                        modification = AgentModification.from_dict(mod_data)
                        history.modifications.append(modification)
                    
                    modification_history[agent_name] = history
                
                self.logger.info(f"Loaded {len(modification_history)} agent histories from disk")
            
            # Load active modifications
            active_file = self.persistence_root / 'active_modifications.json'
            if path_ops.validate_exists(active_file):
                active_content = path_ops.safe_read(active_file)
                if active_content:
                    active_data = json.loads(active_content)
                
                for mod_id, mod_data in active_data.items():
                    modification = AgentModification.from_dict(mod_data)
                    active_modifications[mod_id] = modification
                
                self.logger.info(f"Loaded {len(active_modifications)} active modifications")
            
        except Exception as e:
            self.logger.error(f"Failed to load modification history: {e}")
        
        return modification_history, active_modifications
    
    async def save_agent_state(self, agent_name: str, state_data: Dict[str, Any]) -> None:
        """Save agent-specific state data."""
        try:
            agent_file = self.persistence_root / 'agents' / f"{agent_name}_state.json"
            path_ops.safe_write(agent_file, json.dumps(state_data, indent=2, default=str))
            
            self.logger.debug(f"Saved state for agent '{agent_name}'")
            
        except Exception as e:
            self.logger.error(f"Failed to save agent state for '{agent_name}': {e}")
    
    async def load_agent_state(self, agent_name: str) -> Dict[str, Any]:
        """Load agent-specific state data."""
        try:
            agent_file = self.persistence_root / 'agents' / f"{agent_name}_state.json"
            if path_ops.validate_exists(agent_file):
                agent_content = path_ops.safe_read(agent_file)
                if agent_content:
                    return json.loads(agent_content)
            
        except Exception as e:
            self.logger.error(f"Failed to load agent state for '{agent_name}': {e}")
        
        return {}
    
    async def cleanup_old_persisted_data(self, modifications_to_remove: list[str]) -> None:
        """Clean up old persisted modification data."""
        # This is handled by the main cleanup process
        # Just log the cleanup request
        self.logger.debug(f"Cleanup requested for {len(modifications_to_remove)} modifications")