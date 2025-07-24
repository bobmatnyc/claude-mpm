"""
Improved prompt management functionality.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .models import ImprovedPrompt

logger = logging.getLogger(__name__)


class ImprovedPromptManager:
    """Manages improved prompts from training system."""
    
    def __init__(self, user_home: Path):
        """Initialize the improved prompt manager."""
        self.user_home = user_home
        self.training_dir = user_home / '.claude-pm' / 'training'
        self.improved_prompts_dir = self.training_dir / 'agent-prompts'
        self.improved_prompts_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache for improved prompts
        self.improved_prompts_cache: Dict[str, ImprovedPrompt] = {}
        
        # Load existing prompts on initialization
        self._load_improved_prompts()
    
    def _load_improved_prompts(self) -> None:
        """Load improved prompts from training system."""
        try:
            if not self.improved_prompts_dir.exists():
                return
            
            # Load improved prompts from training directory
            for prompt_file in self.improved_prompts_dir.glob('*.json'):
                try:
                    with open(prompt_file, 'r') as f:
                        data = json.load(f)
                    
                    # Convert to ImprovedPrompt object
                    improved_prompt = ImprovedPrompt(
                        agent_type=data['agent_type'],
                        original_prompt=data['original_prompt'],
                        improved_prompt=data['improved_prompt'],
                        improvement_score=data['improvement_score'],
                        training_session_id=data['training_session_id'],
                        timestamp=datetime.fromisoformat(data['timestamp']),
                        validation_metrics=data.get('validation_metrics', {}),
                        deployment_ready=data.get('deployment_ready', False)
                    )
                    
                    # Cache the improved prompt
                    self.improved_prompts_cache[improved_prompt.agent_type] = improved_prompt
                    
                    logger.debug(f"Loaded improved prompt for {improved_prompt.agent_type}")
                    
                except Exception as e:
                    logger.error(f"Error loading improved prompt from {prompt_file}: {e}")
                    continue
            
            logger.info(f"Loaded {len(self.improved_prompts_cache)} improved prompts")
            
        except Exception as e:
            logger.error(f"Error loading improved prompts: {e}")
    
    async def get_improved_prompt(self, agent_name: str) -> Optional[ImprovedPrompt]:
        """Get improved prompt for an agent if available."""
        return self.improved_prompts_cache.get(agent_name)
    
    async def save_improved_prompt(self, improved_prompt: ImprovedPrompt) -> bool:
        """Save improved prompt to training system."""
        try:
            # Create filename
            filename = f"{improved_prompt.agent_type}_{improved_prompt.training_session_id}.json"
            filepath = self.improved_prompts_dir / filename
            
            # Convert to dictionary
            data = {
                'agent_type': improved_prompt.agent_type,
                'original_prompt': improved_prompt.original_prompt,
                'improved_prompt': improved_prompt.improved_prompt,
                'improvement_score': improved_prompt.improvement_score,
                'training_session_id': improved_prompt.training_session_id,
                'timestamp': improved_prompt.timestamp.isoformat(),
                'validation_metrics': improved_prompt.validation_metrics,
                'deployment_ready': improved_prompt.deployment_ready
            }
            
            # Save to file
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Update cache
            self.improved_prompts_cache[improved_prompt.agent_type] = improved_prompt
            
            logger.info(f"Saved improved prompt for {improved_prompt.agent_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving improved prompt: {e}")
            return False
    
    def mark_deployment_ready(self, agent_name: str, training_session_id: str) -> bool:
        """Mark an improved prompt as deployment ready."""
        improved_prompt = self.improved_prompts_cache.get(agent_name)
        if improved_prompt and improved_prompt.training_session_id == training_session_id:
            improved_prompt.deployment_ready = True
            return True
        return False
    
    def get_all_improved_prompts(self) -> Dict[str, ImprovedPrompt]:
        """Get all cached improved prompts."""
        return self.improved_prompts_cache.copy()