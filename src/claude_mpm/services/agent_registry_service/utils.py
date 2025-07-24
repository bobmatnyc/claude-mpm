"""
Agent Registry Utility Functions and Constants
Provides helper functions and shared constants for agent registry

Created: 2025-07-19
Purpose: Utility functions for agent registry operations
"""

import re
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Core agent types
CORE_AGENT_TYPES = {
    'documentation', 'ticketing', 'version_control', 'qa', 'research',
    'ops', 'security', 'engineer', 'data_engineer'
}

# Extended specialized agent types for ISS-0118
SPECIALIZED_AGENT_TYPES = {
    'ui_ux', 'database', 'api', 'testing', 'performance', 'monitoring',
    'analytics', 'deployment', 'integration', 'workflow', 'content',
    'machine_learning', 'data_science', 'frontend', 'backend', 'mobile',
    'devops', 'cloud', 'infrastructure', 'compliance', 'audit',
    'project_management', 'business_analysis', 'customer_support',
    'marketing', 'sales', 'finance', 'legal', 'hr', 'training',
    'documentation_specialist', 'code_review', 'architecture',
    'orchestrator', 'scaffolding', 'memory_management', 'knowledge_base'
}

# Agent type classification patterns
CLASSIFICATION_PATTERNS = {
    # UI/UX and Frontend specializations
    'ui_ux': ['ui', 'ux', 'design', 'interface', 'user_experience', 'frontend_design'],
    'frontend': ['frontend', 'front_end', 'react', 'vue', 'angular', 'web_ui', 'client_side'],
    
    # Backend and Infrastructure specializations
    'backend': ['backend', 'back_end', 'server', 'api_server', 'microservice'],
    'database': ['database', 'db', 'sql', 'nosql', 'mysql', 'postgres', 'mongodb', 'redis'],
    'api': ['api', 'rest', 'graphql', 'endpoint', 'service', 'web_service'],
    
    # Testing and Quality specializations
    'testing': ['test', 'testing', 'unit_test', 'integration_test', 'e2e', 'automation'],
    'performance': ['performance', 'benchmark', 'optimization', 'profiling', 'load_test'],
    'monitoring': ['monitoring', 'observability', 'metrics', 'logging', 'alerting'],
    
    # DevOps and Infrastructure specializations
    'devops': ['devops', 'ci_cd', 'pipeline', 'automation', 'build'],
    'cloud': ['cloud', 'aws', 'azure', 'gcp', 'kubernetes', 'docker', 'container'],
    'infrastructure': ['infrastructure', 'terraform', 'ansible', 'provisioning'],
    'deployment': ['deployment', 'deploy', 'release', 'staging', 'production'],
    
    # Data and Analytics specializations
    'analytics': ['analytics', 'metrics', 'reporting', 'business_intelligence', 'dashboard'],
    'machine_learning': ['ml', 'machine_learning', 'ai', 'model', 'training', 'prediction'],
    'data_science': ['data_science', 'data_scientist', 'analysis', 'statistics', 'modeling'],
    
    # Business and Process specializations
    'project_management': ['pm', 'project_management', 'scrum', 'agile', 'planning'],
    'business_analysis': ['business_analyst', 'requirements', 'specification', 'process'],
    'compliance': ['compliance', 'audit', 'governance', 'policy', 'regulatory'],
    
    # Content and Communication specializations
    'content': ['content', 'copywriting', 'documentation', 'technical_writing'],
    'customer_support': ['support', 'helpdesk', 'customer_service', 'ticketing'],
    'marketing': ['marketing', 'campaign', 'promotion', 'seo', 'social_media'],
    
    # Framework-specific specializations
    'orchestrator': ['orchestrator', 'coordinator', 'workflow', 'pipeline'],
    'scaffolding': ['scaffolding', 'template', 'generator', 'boilerplate'],
    'architecture': ['architect', 'architecture', 'design_pattern', 'system_design'],
    'code_review': ['code_review', 'review', 'quality_assurance', 'peer_review'],
    'memory_management': ['memory', 'cache', 'storage', 'persistence'],
    'knowledge_base': ['knowledge', 'kb', 'documentation', 'wiki', 'reference'],
    
    # Integration and Workflow specializations
    'integration': ['integration', 'connector', 'bridge', 'adapter', 'sync'],
    'workflow': ['workflow', 'process', 'automation', 'orchestration']
}

# Framework patterns for capability extraction
FRAMEWORK_PATTERNS = {
    'fastapi': ['fastapi', 'pydantic'],
    'django': ['django'],
    'flask': ['flask'],
    'react': ['react', '@types/react'],
    'vue': ['vue', '@vue/'],
    'angular': ['@angular/', 'angular'],
    'express': ['express'],
    'tensorflow': ['tensorflow', 'tf'],
    'pytorch': ['torch', 'pytorch'],
    'pandas': ['pandas'],
    'numpy': ['numpy'],
    'selenium': ['selenium'],
    'pytest': ['pytest'],
    'jest': ['jest'],
    'docker': ['docker'],
    'kubernetes': ['kubernetes', 'kubectl'],
    'aws': ['boto3', 'aws-'],
    'azure': ['azure-'],
    'gcp': ['google-cloud-'],
    'redis': ['redis'],
    'mongodb': ['pymongo', 'mongodb'],
    'postgresql': ['psycopg2', 'postgresql'],
    'mysql': ['mysql', 'pymysql'],
    'graphql': ['graphql'],
    'rest_api': ['requests', 'urllib'],
    'machine_learning': ['scikit-learn', 'sklearn'],
    'data_analysis': ['matplotlib', 'seaborn'],
    'async_processing': ['asyncio', 'aiohttp'],
    'task_queue': ['celery', 'rq'],
    'monitoring': ['prometheus', 'grafana'],
    'logging': ['loguru', 'structlog']
}

# Role patterns for capability extraction
ROLE_PATTERNS = {
    'ui_designer': ['ui design', 'user interface', 'interface design'],
    'ux_specialist': ['user experience', 'ux research', 'usability'],
    'frontend_developer': ['frontend development', 'client-side', 'web development'],
    'backend_developer': ['backend development', 'server-side', 'api development'],
    'database_administrator': ['database admin', 'db management', 'database design'],
    'devops_engineer': ['devops', 'ci/cd', 'deployment automation'],
    'security_specialist': ['security analysis', 'vulnerability assessment', 'penetration testing'],
    'performance_engineer': ['performance optimization', 'load testing', 'benchmarking'],
    'quality_assurance': ['quality assurance', 'test automation', 'qa testing'],
    'data_scientist': ['data science', 'machine learning', 'statistical analysis'],
    'business_analyst': ['business analysis', 'requirements gathering', 'process mapping'],
    'project_manager': ['project management', 'agile', 'scrum master'],
    'technical_writer': ['technical writing', 'documentation', 'content creation'],
    'integration_specialist': ['system integration', 'api integration', 'middleware'],
    'architecture_specialist': ['system architecture', 'software architecture', 'design patterns']
}

# Domain keywords for capability extraction
DOMAIN_KEYWORDS = {
    'e_commerce': ['e-commerce', 'shopping', 'payment', 'order'],
    'healthcare': ['healthcare', 'medical', 'patient', 'clinical'],
    'finance': ['financial', 'banking', 'trading', 'investment'],
    'education': ['education', 'learning', 'student', 'course'],
    'gaming': ['gaming', 'game', 'player', 'score'],
    'social_media': ['social', 'feed', 'post', 'like', 'share'],
    'iot': ['iot', 'sensor', 'device', 'telemetry'],
    'blockchain': ['blockchain', 'crypto', 'smart contract', 'web3'],
    'ai_ml': ['artificial intelligence', 'machine learning', 'neural network'],
    'cloud_native': ['cloud native', 'microservices', 'serverless']
}

# Agent role mappings for markdown files
AGENT_ROLE_MAPPINGS = {
    'documentation-agent': 'role:technical_writer',
    'ticketing-agent': 'role:issue_manager',
    'version-control-agent': 'role:version_manager',
    'qa-agent': 'role:quality_assurance',
    'research-agent': 'role:researcher',
    'ops-agent': 'role:devops_engineer',
    'security-agent': 'role:security_specialist',
    'engineer-agent': 'role:software_engineer',
    'data-agent': 'role:data_engineer',
    'data-engineer-agent': 'role:data_engineer'  # Support both naming conventions
}

# Hybrid agent type indicators
CORE_TYPE_INDICATORS = {
    'documentation': ['docs', 'documentation', 'technical_writing'],
    'ticketing': ['ticketing', 'issue', 'bug_tracking'],
    'version_control': ['git', 'version', 'branching'],
    'qa': ['testing', 'quality', 'validation'],
    'research': ['research', 'analysis', 'investigation'],
    'ops': ['operations', 'deployment', 'infrastructure'],
    'security': ['security', 'auth', 'vulnerability'],
    'engineer': ['engineering', 'development', 'coding'],
    'data_engineer': ['data', 'pipeline', 'etl']
}

# Framework compatibility mappings
COMPATIBLE_COMBINATIONS = {
    'react': ['typescript', 'javascript', 'webpack'],
    'django': ['python', 'postgresql', 'redis'],
    'fastapi': ['python', 'pydantic', 'asyncio'],
    'kubernetes': ['docker', 'yaml', 'helm']
}


def determine_tier(path: Path) -> str:
    """
    Determine hierarchy tier based on path
    
    Args:
        path: Directory path
        
    Returns:
        Tier classification ('project', 'user', or 'system')
    """
    path_str = str(path)
    
    if '.claude-pm/agents/user' in path_str:
        return 'user'
    elif 'claude_pm/agents' in path_str:
        return 'system'
    else:
        return 'project'  # Current/parent directory agents


def has_tier_precedence(tier1: str, tier2: str) -> bool:
    """
    Check if tier1 has precedence over tier2
    
    Args:
        tier1: First tier
        tier2: Second tier
        
    Returns:
        True if tier1 has precedence
    """
    precedence_order = ['project', 'user', 'system']
    try:
        return precedence_order.index(tier1) < precedence_order.index(tier2)
    except ValueError:
        return False


def parse_explicit_model_config(content: str) -> Optional[Dict[str, Any]]:
    """
    Parse explicit model configuration from agent file content.
    
    Looks for patterns like:
    - MODEL_PREFERENCE = "claude-3-opus-20240229"
    - PREFERRED_MODEL = "claude-3-5-sonnet-20241022"
    - model_config = {"model": "claude-3-opus-20240229", "max_tokens": 4096}
    
    Args:
        content: Agent file content
        
    Returns:
        Dictionary with model configuration or None
    """
    # Pattern for direct model assignment
    model_patterns = [
        r'MODEL_PREFERENCE\s*=\s*["\']([^"\']+)["\']',
        r'PREFERRED_MODEL\s*=\s*["\']([^"\']+)["\']',
        r'model\s*=\s*["\']([^"\']+)["\']',
        r'MODEL\s*=\s*["\']([^"\']+)["\']'
    ]
    
    for pattern in model_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            model_id = match.group(1)
            return {"model_id": model_id, "config": {"explicit": True}}
    
    # Pattern for configuration dictionary
    config_pattern = r'model_config\s*=\s*\{([^}]+)\}'
    config_match = re.search(config_pattern, content, re.IGNORECASE)
    if config_match:
        try:
            # Simple parsing of model config dictionary
            config_str = config_match.group(1)
            model_match = re.search(r'["\']model["\']:\s*["\']([^"\']+)["\']', config_str)
            if model_match:
                return {
                    "model_id": model_match.group(1),
                    "config": {"explicit": True, "from_dict": True}
                }
        except Exception as e:
            logger.warning(f"Error parsing model config dictionary: {e}")
    
    return None


def extract_specialized_metadata(capabilities: List[str]) -> Tuple[List[str], List[str], List[str], List[str]]:
    """
    Extract specialized metadata from capabilities list.
    
    Args:
        capabilities: List of agent capabilities
        
    Returns:
        Tuple of (specializations, frameworks, domains, roles)
    """
    specializations = []
    frameworks = []
    domains = []
    roles = []
    
    for capability in capabilities:
        if capability.startswith('specialization:'):
            specializations.append(capability.replace('specialization:', ''))
        elif capability.startswith('framework:'):
            frameworks.append(capability.replace('framework:', ''))
        elif capability.startswith('domain:'):
            domains.append(capability.replace('domain:', ''))
        elif capability.startswith('role:'):
            roles.append(capability.replace('role:', ''))
    
    return specializations, frameworks, domains, roles


def detect_hybrid_agent(agent_type: str, specializations: List[str]) -> Tuple[bool, List[str]]:
    """
    Detect if agent is hybrid (combines multiple agent types).
    
    Args:
        agent_type: Primary agent type
        specializations: List of specializations
        
    Returns:
        Tuple of (is_hybrid, hybrid_types)
    """
    hybrid_types = []
    
    primary_type = agent_type
    detected_types = set()
    
    for spec in specializations:
        for core_type, indicators in CORE_TYPE_INDICATORS.items():
            if any(indicator in spec.lower() for indicator in indicators):
                detected_types.add(core_type)
    
    # If more than one core type detected, it's hybrid
    if len(detected_types) > 1 or (len(detected_types) == 1 and primary_type not in detected_types):
        hybrid_types = list(detected_types)
        if primary_type not in hybrid_types:
            hybrid_types.append(primary_type)
        return True, hybrid_types
    
    return False, []


def assess_complexity_level(capabilities: List[str], specializations: List[str]) -> str:
    """
    Assess agent complexity level based on capabilities and specializations.
    
    Args:
        capabilities: List of capabilities
        specializations: List of specializations
        
    Returns:
        Complexity level ('basic', 'intermediate', 'advanced', 'expert')
    """
    total_features = len(capabilities) + len(specializations)
    
    # Count advanced features
    advanced_indicators = [
        'async_', 'class:', 'framework:', 'machine_learning', 'ai',
        'microservices', 'kubernetes', 'blockchain', 'neural_network'
    ]
    
    advanced_count = sum(1 for cap in capabilities 
                       if any(indicator in cap.lower() for indicator in advanced_indicators))
    
    # Assess complexity
    if total_features >= 20 or advanced_count >= 5:
        return 'expert'
    elif total_features >= 15 or advanced_count >= 3:
        return 'advanced'
    elif total_features >= 8 or advanced_count >= 1:
        return 'intermediate'
    else:
        return 'basic'