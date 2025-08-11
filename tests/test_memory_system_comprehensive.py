#!/usr/bin/env python3
"""
Comprehensive memory system testing script.

This script validates that the memory system is properly activated and working
as designed, including hook registration, memory injection, learning extraction,
and integration testing.

WHY: Ensures the memory system works end-to-end after the recent activation changes.
"""

import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Add the src directory to Python path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from claude_mpm.core.config import Config
    from claude_mpm.services.agents.memory import AgentMemoryManager
    from claude_mpm.hooks.memory_integration_hook import (
        MemoryPreDelegationHook,
        MemoryPostDelegationHook
    )
    from claude_mpm.hooks.base_hook import HookContext
    from claude_mpm.services.hook_service import HookService
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("This may be due to circular import issues. Trying alternative import approach...")
    # Try importing individual modules to avoid circular dependencies
    sys.exit(1)


class MemorySystemTester:
    """Comprehensive memory system testing."""
    
    def __init__(self):
        """Initialize test environment."""
        self.config = Config()
        self.test_agent_id = "test_engineer"
        self.temp_dir = None
        self.memory_manager = None
        self.results = {
            "hook_registration": [],
            "memory_injection": [],
            "learning_extraction": [],
            "integration": [],
            "errors": []
        }
    
    def setup_test_environment(self):
        """Set up temporary test environment."""
        print("🔧 Setting up test environment...")
        
        # Create temporary directory for test
        self.temp_dir = tempfile.mkdtemp(prefix="claude_mpm_memory_test_")
        print(f"   Test directory: {self.temp_dir}")
        
        # Override project root for testing
        with patch('claude_mpm.utils.paths.PathResolver.get_project_root') as mock_root:
            mock_root.return_value = Path(self.temp_dir)
            self.memory_manager = AgentMemoryManager(self.config)
        
        print("✅ Test environment setup complete")
    
    def test_hook_registration(self):
        """Test 1: Verify memory hooks can be registered properly."""
        print("\n📋 Testing Hook Registration...")
        
        try:
            # Test HookService initialization
            hook_service = HookService(self.config)
            self.results["hook_registration"].append({
                "test": "hook_service_init",
                "status": "pass",
                "message": "HookService initialized successfully"
            })
            
            # Test memory pre-delegation hook registration
            pre_hook = MemoryPreDelegationHook(self.config)
            success = hook_service.register_hook(pre_hook)
            self.results["hook_registration"].append({
                "test": "pre_hook_registration",
                "status": "pass" if success else "fail",
                "message": f"Pre-delegation hook registration: {'Success' if success else 'Failed'}"
            })
            
            # Test memory post-delegation hook registration
            post_hook = MemoryPostDelegationHook(self.config)
            success = hook_service.register_hook(post_hook)
            self.results["hook_registration"].append({
                "test": "post_hook_registration", 
                "status": "pass" if success else "fail",
                "message": f"Post-delegation hook registration: {'Success' if success else 'Failed'}"
            })
            
            # Verify hooks are in the service
            registered_hooks = hook_service.get_hooks()
            pre_hooks = [h for h in registered_hooks if h.name == "memory_pre_delegation"]
            post_hooks = [h for h in registered_hooks if h.name == "memory_post_delegation"]
            
            self.results["hook_registration"].append({
                "test": "hook_verification",
                "status": "pass" if len(pre_hooks) > 0 and len(post_hooks) > 0 else "fail",
                "message": f"Hooks verified in service: {len(pre_hooks)} pre, {len(post_hooks)} post"
            })
            
            print(f"   ✅ Hook registration tests completed")
            
        except Exception as e:
            self.results["errors"].append(f"Hook registration test error: {str(e)}")
            print(f"   ❌ Hook registration failed: {e}")
    
    def test_memory_injection(self):
        """Test 2: Verify memory content injection into delegation context."""
        print("\n💉 Testing Memory Injection...")
        
        try:
            # Create test memory content
            test_memory = """# Test Engineer Agent Memory

## Project Architecture (Max: 15 items)
- Service-oriented architecture with clear module boundaries
- Three-tier agent hierarchy: project → user → system

## Implementation Guidelines (Max: 15 items)
- Always use PathResolver for path operations
- Follow existing import patterns

## Common Mistakes to Avoid (Max: 15 items)
- Don't hardcode file paths
- Avoid duplicating code
"""
            
            # Save test memory
            with patch('claude_mpm.utils.paths.PathResolver.get_project_root') as mock_root:
                mock_root.return_value = Path(self.temp_dir)
                memory_manager = AgentMemoryManager(self.config)
                memory_file = memory_manager.memories_dir / f"{self.test_agent_id}_agent.md"
                memory_file.parent.mkdir(parents=True, exist_ok=True)
                memory_file.write_text(test_memory)
            
            # Test memory injection hook
            pre_hook = MemoryPreDelegationHook(self.config)
            
            # Create test context
            context_data = {
                'agent': 'Test Engineer Agent',
                'context': {'prompt': 'Please implement a new feature'}
            }
            context = HookContext(data=context_data)
            
            # Execute pre-delegation hook
            with patch('claude_mpm.utils.paths.PathResolver.get_project_root') as mock_root:
                mock_root.return_value = Path(self.temp_dir)
                result = pre_hook.execute(context)
            
            # Verify injection occurred
            injection_success = (
                result.success and 
                result.modified and 
                'agent_memory' in result.data.get('context', {})
            )
            
            self.results["memory_injection"].append({
                "test": "memory_injection_basic",
                "status": "pass" if injection_success else "fail",
                "message": f"Memory injection: {'Success' if injection_success else 'Failed'}"
            })
            
            if injection_success:
                injected_content = result.data['context']['agent_memory']
                content_valid = (
                    "AGENT MEMORY" in injected_content and
                    "Service-oriented architecture" in injected_content
                )
                
                self.results["memory_injection"].append({
                    "test": "memory_content_validation",
                    "status": "pass" if content_valid else "fail",
                    "message": f"Memory content validation: {'Valid' if content_valid else 'Invalid'}"
                })
            
            print(f"   ✅ Memory injection tests completed")
            
        except Exception as e:
            self.results["errors"].append(f"Memory injection test error: {str(e)}")
            print(f"   ❌ Memory injection failed: {e}")
    
    def test_learning_extraction(self):
        """Test 3: Verify learning extraction from agent responses."""
        print("\n🧠 Testing Learning Extraction...")
        
        try:
            # Test learning extraction hook
            post_hook = MemoryPostDelegationHook(self.config)
            
            # Create test context with learning markers
            test_response = """
I've implemented the feature successfully. Here are some learnings:

# Add To Memory:
Type: pattern
Content: Always validate input parameters before processing them
#

# Memorize:
Type: guideline
Content: Use dependency injection for better testability
#

# Remember:
Type: mistake
Content: Never hardcode configuration values in source code
#

The implementation is complete and follows best practices.
"""
            
            context_data = {
                'agent': 'Test Engineer Agent',
                'result': {'content': test_response}
            }
            context = HookContext(data=context_data)
            
            # Mock the memory manager to capture learning attempts
            with patch('claude_mpm.utils.paths.PathResolver.get_project_root') as mock_root, \
                 patch.object(post_hook.memory_manager, 'add_learning') as mock_add_learning:
                
                mock_root.return_value = Path(self.temp_dir)
                mock_add_learning.return_value = True
                
                # Execute post-delegation hook
                result = post_hook.execute(context)
                
                # Verify learning extraction
                extraction_success = result.success
                learning_calls = mock_add_learning.call_args_list
                
                self.results["learning_extraction"].append({
                    "test": "learning_extraction_basic",
                    "status": "pass" if extraction_success else "fail",
                    "message": f"Learning extraction: {'Success' if extraction_success else 'Failed'}"
                })
                
                # Verify specific learning types were extracted
                expected_types = ['pattern', 'guideline', 'mistake']
                extracted_types = [call[0][1] for call in learning_calls]  # Second argument is learning_type
                
                types_match = all(t in extracted_types for t in expected_types)
                self.results["learning_extraction"].append({
                    "test": "learning_types_validation",
                    "status": "pass" if types_match and len(learning_calls) == 3 else "fail",
                    "message": f"Learning types extracted: {len(learning_calls)} calls, types: {extracted_types}"
                })
            
            print(f"   ✅ Learning extraction tests completed")
            
        except Exception as e:
            self.results["errors"].append(f"Learning extraction test error: {str(e)}")
            print(f"   ❌ Learning extraction failed: {e}")
    
    def test_integration_flow(self):
        """Test 4: Test complete integration flow."""
        print("\n🔄 Testing Integration Flow...")
        
        try:
            # Test ClaudeRunner initialization with memory hooks
            with patch('claude_mpm.utils.paths.PathResolver.get_project_root') as mock_root, \
                 patch('claude_mpm.core.claude_runner.ClaudeRunner._load_system_instructions') as mock_sys, \
                 patch('claude_mpm.services.ticket_manager.TicketManager'):
                
                mock_root.return_value = Path(self.temp_dir)
                mock_sys.return_value = "System instructions"
                
                # Initialize Claude runner (this should register memory hooks)
                runner = ClaudeRunner(
                    enable_hooks=True,
                    enable_tickets=False
                )
                
                # Verify hook service was initialized
                hook_service_init = hasattr(runner, 'hook_service') and runner.hook_service is not None
                self.results["integration"].append({
                    "test": "claude_runner_hook_service",
                    "status": "pass" if hook_service_init else "fail",
                    "message": f"ClaudeRunner hook service: {'Initialized' if hook_service_init else 'Missing'}"
                })
                
                # Verify memory hooks were registered
                if hook_service_init:
                    registered_hooks = runner.hook_service.get_hooks()
                    memory_hooks = [h for h in registered_hooks if 'memory' in h.name]
                    
                    hooks_registered = len(memory_hooks) >= 2  # Pre and post hooks
                    self.results["integration"].append({
                        "test": "memory_hooks_auto_registration",
                        "status": "pass" if hooks_registered else "fail",
                        "message": f"Memory hooks auto-registered: {len(memory_hooks)} hooks found"
                    })
                
                # Test memory manager initialization
                memory_manager = AgentMemoryManager(runner.config)
                memory_status = memory_manager.get_memory_status()
                
                status_valid = memory_status.get('system_enabled', False)
                self.results["integration"].append({
                    "test": "memory_system_status",
                    "status": "pass" if status_valid else "fail",
                    "message": f"Memory system status: {'Enabled' if status_valid else 'Disabled'}"
                })
            
            print(f"   ✅ Integration flow tests completed")
            
        except Exception as e:
            self.results["errors"].append(f"Integration flow test error: {str(e)}")
            print(f"   ❌ Integration flow failed: {e}")
    
    def test_memory_file_creation(self):
        """Test 5: Verify memory files would be created in correct location."""
        print("\n📁 Testing Memory File Creation...")
        
        try:
            with patch('claude_mpm.utils.paths.PathResolver.get_project_root') as mock_root:
                mock_root.return_value = Path(self.temp_dir)
                
                # Test memory manager initialization
                memory_manager = AgentMemoryManager(self.config)
                
                # Load memory for test agent (should create default)
                memory_content = memory_manager.load_agent_memory(self.test_agent_id)
                
                # Check if memory file was created
                expected_file = memory_manager.memories_dir / f"{self.test_agent_id}_agent.md"
                file_created = expected_file.exists()
                
                self.results["integration"].append({
                    "test": "memory_file_creation",
                    "status": "pass" if file_created else "fail",
                    "message": f"Memory file creation: {'Success' if file_created else 'Failed'} at {expected_file}"
                })
                
                # Verify directory structure
                expected_dir = Path(self.temp_dir) / ".claude-mpm" / "memories"
                dir_structure_valid = expected_dir.exists() and expected_dir.is_dir()
                
                self.results["integration"].append({
                    "test": "memory_directory_structure",
                    "status": "pass" if dir_structure_valid else "fail",
                    "message": f"Memory directory structure: {'Valid' if dir_structure_valid else 'Invalid'} at {expected_dir}"
                })
                
                # Check README creation
                readme_file = expected_dir / "README.md"
                readme_created = readme_file.exists()
                
                self.results["integration"].append({
                    "test": "readme_creation",
                    "status": "pass" if readme_created else "fail",
                    "message": f"README creation: {'Success' if readme_created else 'Failed'}"
                })
            
            print(f"   ✅ Memory file creation tests completed")
            
        except Exception as e:
            self.results["errors"].append(f"Memory file creation test error: {str(e)}")
            print(f"   ❌ Memory file creation failed: {e}")
    
    def test_error_handling(self):
        """Test 6: Verify graceful error handling."""
        print("\n⚠️  Testing Error Handling...")
        
        try:
            # Test memory injection with invalid agent
            pre_hook = MemoryPreDelegationHook(self.config)
            context_data = {'agent': '', 'context': 'test'}
            context = HookContext(data=context_data)
            
            result = pre_hook.execute(context)
            graceful_handling = result.success and not result.modified
            
            self.results["integration"].append({
                "test": "error_handling_empty_agent",
                "status": "pass" if graceful_handling else "fail",
                "message": f"Empty agent handling: {'Graceful' if graceful_handling else 'Failed'}"
            })
            
            # Test learning extraction with malformed content
            post_hook = MemoryPostDelegationHook(self.config)
            context_data = {
                'agent': 'Test Agent',
                'result': {'content': 'Malformed content without proper markers'}
            }
            context = HookContext(data=context_data)
            
            result = post_hook.execute(context)
            graceful_handling = result.success
            
            self.results["integration"].append({
                "test": "error_handling_malformed_content",
                "status": "pass" if graceful_handling else "fail",
                "message": f"Malformed content handling: {'Graceful' if graceful_handling else 'Failed'}"
            })
            
            print(f"   ✅ Error handling tests completed")
            
        except Exception as e:
            self.results["errors"].append(f"Error handling test error: {str(e)}")
            print(f"   ❌ Error handling test failed: {e}")
    
    def cleanup_test_environment(self):
        """Clean up test environment."""
        print("\n🧹 Cleaning up test environment...")
        
        try:
            if self.temp_dir:
                import shutil
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                print(f"   Removed test directory: {self.temp_dir}")
        except Exception as e:
            print(f"   Warning: Could not clean up test directory: {e}")
    
    def generate_report(self):
        """Generate comprehensive test report."""
        print("\n📊 Generating Test Report...")
        
        # Count results
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for category, tests in self.results.items():
            if category != "errors":
                for test in tests:
                    total_tests += 1
                    if test["status"] == "pass":
                        passed_tests += 1
                    else:
                        failed_tests += 1
        
        # Generate report
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
            },
            "test_categories": self.results,
            "overall_status": "PASS" if failed_tests == 0 and len(self.results["errors"]) == 0 else "FAIL",
            "recommendations": []
        }
        
        # Add recommendations based on results
        if failed_tests > 0:
            report["recommendations"].append("Some tests failed - review failed test details")
        
        if len(self.results["errors"]) > 0:
            report["recommendations"].append("Errors occurred during testing - check error list")
        
        if failed_tests == 0 and len(self.results["errors"]) == 0:
            report["recommendations"].append("All tests passed - memory system is properly activated")
            report["recommendations"].append("Memory files will be created at: .claude-mpm/memories/")
            report["recommendations"].append("Auto-learning is enabled by default")
            report["recommendations"].append("Memory hooks are automatically registered during CLI startup")
        
        return report
    
    def run_all_tests(self):
        """Run all memory system tests."""
        print("🚀 Starting Comprehensive Memory System Tests")
        print("=" * 60)
        
        self.setup_test_environment()
        
        # Run all test categories
        self.test_hook_registration()
        self.test_memory_injection() 
        self.test_learning_extraction()
        self.test_integration_flow()
        self.test_memory_file_creation()
        self.test_error_handling()
        
        # Generate and display report
        report = self.generate_report()
        
        print("\n" + "=" * 60)
        print("📋 MEMORY SYSTEM TEST REPORT")
        print("=" * 60)
        
        print(f"Overall Status: {report['overall_status']}")
        print(f"Tests Passed: {report['test_summary']['passed']}/{report['test_summary']['total_tests']} ({report['test_summary']['success_rate']})")
        
        if report['test_summary']['failed'] > 0:
            print(f"Tests Failed: {report['test_summary']['failed']}")
        
        if len(self.results["errors"]) > 0:
            print(f"Errors: {len(self.results['errors'])}")
        
        print("\n📊 Test Details:")
        for category, tests in self.results.items():
            if category != "errors" and tests:
                print(f"\n{category.replace('_', ' ').title()}:")
                for test in tests:
                    status_icon = "✅" if test["status"] == "pass" else "❌"
                    print(f"  {status_icon} {test['test']}: {test['message']}")
        
        if self.results["errors"]:
            print(f"\n❌ Errors:")
            for error in self.results["errors"]:
                print(f"  • {error}")
        
        print(f"\n🎯 Recommendations:")
        for rec in report["recommendations"]:
            print(f"  • {rec}")
        
        self.cleanup_test_environment()
        
        return report


def main():
    """Main test execution."""
    tester = MemorySystemTester()
    report = tester.run_all_tests()
    
    # Exit with appropriate code
    if report["overall_status"] == "PASS":
        print(f"\n🎉 All tests passed! Memory system is properly activated.")
        sys.exit(0)
    else:
        print(f"\n⚠️  Some tests failed. Review the report above.")
        sys.exit(1)


if __name__ == "__main__":
    main()