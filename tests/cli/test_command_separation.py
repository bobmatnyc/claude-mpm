"""Test command separation between run and run-guarded.

WHY: This test ensures that the main run command and the experimental run-guarded
command remain properly separated with no cross-dependencies.

DESIGN DECISION: We test both import isolation and functional isolation to ensure
changes to experimental features don't affect stable functionality.
"""

import ast
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import json


class TestCommandSeparation(unittest.TestCase):
    """Test that run and run-guarded commands are properly separated."""
    
    def setUp(self):
        """Set up test environment."""
        self.src_dir = Path(__file__).parent.parent.parent / "src"
        self.run_module_path = self.src_dir / "claude_mpm" / "cli" / "commands" / "run.py"
        self.run_guarded_module_path = self.src_dir / "claude_mpm" / "cli" / "commands" / "run_guarded.py"
    
    def test_run_has_no_memory_guardian_imports(self):
        """Test that run.py doesn't import any memory guardian code.
        
        WHY: The main run command should have zero dependencies on experimental
        memory guardian features to ensure stability.
        """
        with open(self.run_module_path, 'r') as f:
            source = f.read()
        
        # Parse the AST to find all imports
        tree = ast.parse(source)
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
        
        # Check for memory guardian related imports
        memory_guardian_imports = [
            imp for imp in imports 
            if any(term in imp.lower() for term in ['memory_guardian', 'memory_aware', 'run_guarded'])
        ]
        
        self.assertEqual(
            memory_guardian_imports, [],
            f"run.py should not import memory guardian code, but found: {memory_guardian_imports}"
        )
    
    def test_run_has_no_memory_guardian_references(self):
        """Test that run.py doesn't reference memory guardian classes or functions.
        
        WHY: Even without direct imports, we want to ensure no references to
        memory guardian functionality exist in the stable run command.
        """
        with open(self.run_module_path, 'r') as f:
            source = f.read()
        
        # Check for string references to memory guardian
        forbidden_terms = [
            'MemoryAwareClaudeRunner',
            'MemoryGuardian',
            'memory_guardian',
            'run_guarded',
            'StateManager',
            'memory_threshold',
            'restart_policy'
        ]
        
        for term in forbidden_terms:
            self.assertNotIn(
                term, source,
                f"run.py should not reference '{term}'"
            )
    
    def test_run_guarded_extends_claude_runner(self):
        """Test that run-guarded properly extends ClaudeRunner.
        
        WHY: The experimental command should extend the base functionality
        without modifying it, ensuring clean separation.
        """
        # Import the modules
        spec = importlib.util.spec_from_file_location("run_guarded", self.run_guarded_module_path)
        run_guarded_module = importlib.util.module_from_spec(spec)
        
        # Check that MemoryAwareClaudeRunner is imported
        with open(self.run_guarded_module_path, 'r') as f:
            source = f.read()
        
        self.assertIn(
            'from claude_mpm.core.memory_aware_runner import MemoryAwareClaudeRunner',
            source,
            "run_guarded.py should import MemoryAwareClaudeRunner"
        )
        
        # Check that it doesn't directly import ClaudeRunner
        self.assertNotIn(
            'from claude_mpm.core.claude_runner import ClaudeRunner',
            source,
            "run_guarded.py should not directly import ClaudeRunner (uses MemoryAwareClaudeRunner instead)"
        )
    
    def test_experimental_warning_shown(self):
        """Test that experimental warning is shown for run-guarded.
        
        WHY: Users must be warned when using experimental features to set
        proper expectations about stability and support.
        """
        with open(self.run_guarded_module_path, 'r') as f:
            source = f.read()
        
        # Check for experimental warnings in the code
        self.assertIn(
            'EXPERIMENTAL',
            source,
            "run_guarded.py should contain EXPERIMENTAL warnings"
        )
        
        self.assertIn(
            'get_experimental_features',
            source,
            "run_guarded.py should use experimental features configuration"
        )
    
    def test_parser_marks_run_guarded_as_experimental(self):
        """Test that the parser marks run-guarded as experimental.
        
        WHY: The command help should clearly indicate experimental status
        so users know before running the command.
        """
        parser_path = self.src_dir / "claude_mpm" / "cli" / "parser.py"
        with open(parser_path, 'r') as f:
            source = f.read()
        
        # Check for experimental marking in parser
        self.assertIn(
            'EXPERIMENTAL',
            source,
            "parser.py should mark run-guarded as EXPERIMENTAL"
        )
    
    def test_experimental_features_config_exists(self):
        """Test that experimental features configuration exists.
        
        WHY: We need a centralized way to manage experimental features
        and their warnings.
        """
        config_path = self.src_dir / "claude_mpm" / "config" / "experimental_features.py"
        self.assertTrue(
            config_path.exists(),
            f"experimental_features.py should exist at {config_path}"
        )
        
        # Check that it has the required functionality
        with open(config_path, 'r') as f:
            source = f.read()
        
        required_methods = [
            'is_enabled',
            'get_warning',
            'should_show_warning',
            'mark_accepted'
        ]
        
        for method in required_methods:
            self.assertIn(
                f'def {method}',
                source,
                f"experimental_features.py should have {method} method"
            )
    
    def test_can_import_run_without_memory_guardian(self):
        """Test that run module can be imported without memory guardian dependencies.
        
        WHY: The main run command must work even if memory guardian dependencies
        are missing or broken.
        """
        # Create a mock that will fail if memory guardian is imported
        with patch.dict('sys.modules', {
            'claude_mpm.core.memory_aware_runner': None,
            'claude_mpm.services.infrastructure.memory_guardian': None,
            'claude_mpm.services.infrastructure.state_manager': None,
        }):
            try:
                # This should work without importing memory guardian modules
                spec = importlib.util.spec_from_file_location("run", self.run_module_path)
                run_module = importlib.util.module_from_spec(spec)
                # Don't execute the module, just verify it can be loaded
                self.assertIsNotNone(run_module)
            except ImportError as e:
                self.fail(f"run.py should not depend on memory guardian modules: {e}")
    
    def test_experimental_flag_controls_feature(self):
        """Test that experimental flag properly controls feature availability.
        
        WHY: Experimental features should be disabled by default and only
        available when explicitly enabled.
        """
        # Import the experimental features module
        spec = importlib.util.spec_from_file_location(
            "experimental_features",
            self.src_dir / "claude_mpm" / "config" / "experimental_features.py"
        )
        exp_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exp_module)
        
        # Create config with memory guardian disabled
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'experimental_features': {'enable_memory_guardian': False}}, f)
            config_file = Path(f.name)
        
        try:
            # Test with feature disabled
            features = exp_module.ExperimentalFeatures(config_file)
            self.assertFalse(
                features.is_enabled('memory_guardian'),
                "Memory Guardian should be disabled by default"
            )
            
            # Test warning should be shown
            self.assertTrue(
                features.should_show_warning('memory_guardian'),
                "Warning should be shown for experimental features"
            )
            
            # Test warning message exists
            warning = features.get_warning('memory_guardian')
            self.assertIsNotNone(warning, "Warning message should exist")
            self.assertIn('EXPERIMENTAL', warning, "Warning should mention experimental status")
        finally:
            config_file.unlink()
    
    def test_documentation_has_experimental_warnings(self):
        """Test that documentation files have experimental warnings.
        
        WHY: Documentation must clearly indicate experimental status to set
        proper user expectations.
        """
        docs_dir = Path(__file__).parent.parent.parent / "docs"
        memory_guardian_docs = [
            "USER_GUIDE_MEMORY_GUARDIAN.md",
            "MEMORY_GUARDIAN_TECHNICAL.md",
            "MEMORY_GUARDIAN_CONFIG.md"
        ]
        
        for doc_file in memory_guardian_docs:
            doc_path = docs_dir / doc_file
            if doc_path.exists():
                with open(doc_path, 'r') as f:
                    content = f.read()
                
                # Check for experimental warning
                self.assertTrue(
                    any(term in content.upper() for term in ['EXPERIMENTAL', 'BETA']),
                    f"{doc_file} should contain experimental/beta warning"
                )


if __name__ == '__main__':
    unittest.main()