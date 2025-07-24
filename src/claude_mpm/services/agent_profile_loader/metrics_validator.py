"""
Metrics and validation functionality.
"""

import logging
from typing import Dict, Any, List

from .models import ProfileTier

logger = logging.getLogger(__name__)


class MetricsValidator:
    """Handles metrics collection and validation."""
    
    def __init__(self, tier_paths: Dict[ProfileTier, dict]):
        """Initialize metrics validator."""
        self.tier_paths = tier_paths
    
    async def validate_profile_integration(self, service_integrations) -> Dict[str, Any]:
        """Validate profile integration with framework systems."""
        validation_results = {
            'valid': True,
            'issues': [],
            'warnings': [],
            'integrations': {}
        }
        
        # Validate tier paths
        for tier, path in self.tier_paths.items():
            if not path.exists():
                validation_results['issues'].append(f"Missing tier directory: {path}")
                validation_results['valid'] = False
            else:
                # Check for profiles in tier
                profile_count = len(list(path.glob('*.md')))
                validation_results['integrations'][f'{tier.value}_profiles'] = profile_count
        
        # Validate service integrations
        validation_results['integrations']['shared_cache'] = service_integrations.is_cache_enabled()
        validation_results['integrations']['agent_registry'] = service_integrations.is_registry_enabled()
        validation_results['integrations']['training_integration'] = service_integrations.is_training_enabled()
        
        # Validate improved prompts directory
        improved_prompts_dir = self.tier_paths[ProfileTier.USER].parent.parent / 'training' / 'agent-prompts'
        if improved_prompts_dir.exists():
            improved_count = len(list(improved_prompts_dir.glob('*.json')))
            validation_results['integrations']['improved_prompts'] = improved_count
        else:
            validation_results['warnings'].append("Improved prompts directory not found")
        
        return validation_results
    
    def collect_performance_metrics(self, profile_manager, service_integrations) -> Dict[str, Any]:
        """Collect comprehensive performance metrics."""
        metrics = profile_manager.get_metrics()
        
        # Add cache statistics
        cache_metrics = service_integrations.get_cache_metrics()
        if cache_metrics:
            metrics.update({
                'shared_cache_hits': cache_metrics.get('hits', 0),
                'shared_cache_misses': cache_metrics.get('misses', 0),
                'shared_cache_hit_rate': cache_metrics.get('hit_rate', 0.0),
                'shared_cache_size': cache_metrics.get('entry_count', 0)
            })
        
        # Add improved prompts statistics
        improved_prompt_manager = profile_manager.improved_prompt_manager
        metrics.update({
            'improved_prompts_available': len(improved_prompt_manager.get_all_improved_prompts())
        })
        
        return metrics
    
    def validate_profile_structure(self, profile) -> List[str]:
        """Validate the structure of a loaded profile."""
        issues = []
        
        # Check required fields
        if not profile.name:
            issues.append("Profile missing name")
        if not profile.role:
            issues.append("Profile missing role")
        if not profile.capabilities:
            issues.append("Profile has no capabilities defined")
        if not profile.authority_scope:
            issues.append("Profile has no authority scope defined")
        
        # Check content length
        if len(profile.content) < 100:
            issues.append("Profile content seems too short")
        
        return issues