#!/usr/bin/env python3
"""
File metadata analysis for agent modifications.

This module handles analyzing agent files to extract metadata and structural
information for tracking and validation purposes.
"""

import ast
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from .models import ModificationTier, ModificationType


class MetadataAnalyzer:
    """Analyzer for extracting metadata from agent files."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def collect_file_metadata(self, file_path: str, modification_type: ModificationType) -> Dict[str, Any]:
        """Collect comprehensive file metadata."""
        metadata = {}
        
        try:
            path = Path(file_path)
            
            if modification_type != ModificationType.DELETE and path.exists():
                # File statistics
                stat = path.stat()
                metadata['file_size_after'] = stat.st_size
                metadata['file_mode'] = stat.st_mode
                metadata['file_owner'] = stat.st_uid
                
                # File hash
                metadata['file_hash_after'] = await self.calculate_file_hash(path)
                
                # File content analysis
                if path.suffix == '.py':
                    metadata['file_type'] = 'python_agent'
                    metadata.update(await self.analyze_python_file(path))
                elif path.suffix == '.md':
                    metadata['file_type'] = 'markdown_profile'
                    metadata.update(await self.analyze_markdown_file(path))
            else:
                metadata['file_size_after'] = 0
                metadata['file_hash_after'] = None
                
        except Exception as e:
            self.logger.warning(f"Error collecting file metadata for {file_path}: {e}")
            metadata['metadata_error'] = str(e)
        
        return metadata
    
    async def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file content."""
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""
    
    async def analyze_python_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze Python agent file for metadata."""
        analysis = {}
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Extract classes and functions
            tree = ast.parse(content)
            
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            
            analysis['classes'] = classes
            analysis['functions'] = functions
            analysis['lines_of_code'] = len(content.split('\n'))
            
            # Check for async functions
            async_functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)]
            analysis['async_functions'] = async_functions
            
            # Extract imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend([alias.name for alias in node.names])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            analysis['imports'] = list(set(imports))
            
        except Exception as e:
            analysis['analysis_error'] = str(e)
        
        return analysis
    
    async def analyze_markdown_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze Markdown profile file for metadata."""
        analysis = {}
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Count sections
            sections = [line.strip() for line in content.split('\n') if line.strip().startswith('#')]
            analysis['sections'] = len(sections)
            analysis['section_titles'] = sections[:10]  # First 10 sections
            
            # Count lines and words
            lines = content.split('\n')
            analysis['lines'] = len(lines)
            analysis['words'] = len(content.split())
            
            # Extract code blocks
            code_blocks = content.count('```')
            analysis['code_blocks'] = code_blocks // 2  # Pairs of ``` delimiters
            
        except Exception as e:
            analysis['analysis_error'] = str(e)
        
        return analysis
    
    def extract_agent_info_from_path(self, file_path: str) -> Optional[Tuple[str, ModificationTier]]:
        """Extract agent name and tier from file path."""
        path = Path(file_path)
        
        # Determine agent name
        agent_name = path.stem
        if agent_name.endswith('_agent'):
            agent_name = agent_name[:-6]
        elif agent_name.endswith('-agent'):
            agent_name = agent_name[:-6]
        elif agent_name.endswith('-profile'):
            agent_name = agent_name[:-8]
        
        # Determine tier based on path
        path_str = str(path)
        if '.claude-pm/agents/user' in path_str:
            tier = ModificationTier.USER
        elif 'claude_pm/agents' in path_str:
            tier = ModificationTier.SYSTEM
        else:
            tier = ModificationTier.PROJECT
        
        return (agent_name, tier)
    
    def generate_modification_id(self, agent_name: str, modification_type: ModificationType) -> str:
        """Generate unique modification ID."""
        import time
        timestamp = str(int(time.time() * 1000))  # Millisecond precision
        agent_hash = hashlib.md5(agent_name.encode()).hexdigest()[:8]
        return f"{modification_type.value}_{agent_hash}_{timestamp}"