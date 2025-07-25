"""Tests for JSON-RPC based hook system."""

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from claude_mpm.hooks.base_hook import (
    BaseHook, HookContext, HookResult, HookType, SubmitHook
)
from claude_mpm.hooks.json_rpc_executor import JSONRPCHookExecutor, JSONRPCError
from claude_mpm.hooks.json_rpc_hook_client import JSONRPCHookClient
from claude_mpm.hooks.hook_runner import JSONRPCHookRunner, HookLoader


class TestJSONRPCExecutor(unittest.TestCase):
    """Test cases for JSONRPCHookExecutor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.executor = JSONRPCHookExecutor(timeout=5)
        
    def test_execute_hook_success(self):
        """Test successful hook execution."""
        # Mock subprocess.run
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "jsonrpc": "2.0",
            "result": {
                "hook_name": "test_hook",
                "success": True,
                "data": {"processed": True},
                "modified": True,
                "execution_time_ms": 10.5
            },
            "id": "test_123"
        })
        mock_result.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result):
            result = self.executor.execute_hook(
                hook_name="test_hook",
                hook_type=HookType.SUBMIT,
                context_data={"prompt": "test"}
            )
            
            self.assertTrue(result["success"])
            self.assertEqual(result["hook_name"], "test_hook")
            self.assertEqual(result["data"], {"processed": True})
            self.assertTrue(result["modified"])
            
    def test_execute_hook_timeout(self):
        """Test hook execution timeout."""
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('cmd', 5)):
            with self.assertRaises(JSONRPCError) as ctx:
                self.executor.execute_hook(
                    hook_name="slow_hook",
                    hook_type=HookType.SUBMIT,
                    context_data={"prompt": "test"}
                )
                
            self.assertEqual(ctx.exception.code, JSONRPCHookExecutor.INTERNAL_ERROR)
            self.assertIn("timed out", ctx.exception.message)
            
    def test_execute_hook_invalid_json(self):
        """Test handling of invalid JSON response."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Invalid JSON"
        mock_result.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result):
            with self.assertRaises(JSONRPCError) as ctx:
                self.executor.execute_hook(
                    hook_name="bad_hook",
                    hook_type=HookType.SUBMIT,
                    context_data={"prompt": "test"}
                )
                
            self.assertEqual(ctx.exception.code, JSONRPCHookExecutor.PARSE_ERROR)
            
    def test_execute_hook_process_failure(self):
        """Test handling of subprocess failure."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Hook runner error"
        
        with patch('subprocess.run', return_value=mock_result):
            with self.assertRaises(JSONRPCError) as ctx:
                self.executor.execute_hook(
                    hook_name="failing_hook",
                    hook_type=HookType.SUBMIT,
                    context_data={"prompt": "test"}
                )
                
            self.assertEqual(ctx.exception.code, JSONRPCHookExecutor.INTERNAL_ERROR)
            self.assertIn("Hook runner error", ctx.exception.message)
            
    def test_execute_hooks_partial_failure(self):
        """Test executing multiple hooks with partial failure."""
        def mock_run(*args, **kwargs):
            # Check which hook is being executed based on input
            request = json.loads(kwargs['input'])
            hook_name = request['params']['hook_name']
            
            mock_result = MagicMock()
            
            if hook_name == "hook1":
                mock_result.returncode = 0
                mock_result.stdout = json.dumps({
                    "jsonrpc": "2.0",
                    "result": {
                        "hook_name": "hook1",
                        "success": True,
                        "data": {"result": "ok"}
                    },
                    "id": request['id']
                })
            else:  # hook2 fails
                mock_result.returncode = 1
                mock_result.stderr = "Hook2 failed"
                
            return mock_result
            
        with patch('subprocess.run', side_effect=mock_run):
            results = self.executor.execute_hooks(
                hook_type=HookType.SUBMIT,
                hook_names=["hook1", "hook2"],
                context_data={"prompt": "test"}
            )
            
            self.assertEqual(len(results), 2)
            self.assertTrue(results[0]["success"])
            self.assertFalse(results[1]["success"])
            self.assertIn("failed", results[1]["error"])
            
    def test_batch_execute(self):
        """Test batch execution of hooks."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([
            {
                "jsonrpc": "2.0",
                "result": {
                    "hook_name": "hook1",
                    "success": True,
                    "data": {"processed": True}
                },
                "id": "batch_0_123"
            },
            {
                "jsonrpc": "2.0",
                "result": {
                    "hook_name": "hook2",
                    "success": True,
                    "data": {"processed": True}
                },
                "id": "batch_1_123"
            }
        ])
        
        with patch('subprocess.run', return_value=mock_result):
            requests = [
                {
                    "hook_name": "hook1",
                    "hook_type": "submit",
                    "context_data": {"prompt": "test1"}
                },
                {
                    "hook_name": "hook2",
                    "hook_type": "submit",
                    "context_data": {"prompt": "test2"}
                }
            ]
            
            results = self.executor.batch_execute(requests)
            
            self.assertEqual(len(results), 2)
            self.assertTrue(results[0]["success"])
            self.assertTrue(results[1]["success"])


class TestHookLoader(unittest.TestCase):
    """Test cases for HookLoader."""
    
    def test_hook_discovery(self):
        """Test hook discovery from builtin directory."""
        loader = HookLoader()
        
        # Should have discovered some hooks
        hook = loader.get_hook("ticket_detection")
        self.assertIsNotNone(hook)
        
        hook_type = loader.get_hook_type("ticket_detection")
        self.assertEqual(hook_type, HookType.SUBMIT)
        
    def test_get_nonexistent_hook(self):
        """Test getting a non-existent hook."""
        loader = HookLoader()
        
        hook = loader.get_hook("nonexistent")
        self.assertIsNone(hook)
        
        hook_type = loader.get_hook_type("nonexistent")
        self.assertIsNone(hook_type)


class TestJSONRPCHookRunner(unittest.TestCase):
    """Test cases for JSONRPCHookRunner."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.runner = JSONRPCHookRunner()
        
    def test_handle_valid_request(self):
        """Test handling a valid JSON-RPC request."""
        request = {
            "jsonrpc": "2.0",
            "method": "execute_hook",
            "params": {
                "hook_name": "ticket_detection",
                "hook_type": "submit",
                "context_data": {"prompt": "Fix TSK-123"},
                "metadata": {}
            },
            "id": "test_123"
        }
        
        response = self.runner.handle_request(request)
        
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], "test_123")
        self.assertIn("result", response)
        result = response["result"]
        self.assertEqual(result["hook_name"], "ticket_detection")
        self.assertTrue(result["success"])
        self.assertIn("tickets", result["data"])
        self.assertEqual(result["data"]["tickets"], ["TSK-123"])
        
    def test_handle_invalid_jsonrpc_version(self):
        """Test handling request with invalid JSON-RPC version."""
        request = {
            "jsonrpc": "1.0",
            "method": "execute_hook",
            "params": {},
            "id": "test_123"
        }
        
        response = self.runner.handle_request(request)
        
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32600)
        self.assertIn("jsonrpc", response["error"]["data"])
        
    def test_handle_missing_method(self):
        """Test handling request without method."""
        request = {
            "jsonrpc": "2.0",
            "params": {},
            "id": "test_123"
        }
        
        response = self.runner.handle_request(request)
        
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32600)
        self.assertIn("method", response["error"]["data"])
        
    def test_handle_unknown_method(self):
        """Test handling request with unknown method."""
        request = {
            "jsonrpc": "2.0",
            "method": "unknown_method",
            "params": {},
            "id": "test_123"
        }
        
        response = self.runner.handle_request(request)
        
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32601)
        
    def test_execute_hook_not_found(self):
        """Test executing a non-existent hook."""
        request = {
            "jsonrpc": "2.0",
            "method": "execute_hook",
            "params": {
                "hook_name": "nonexistent_hook",
                "hook_type": "submit",
                "context_data": {"prompt": "test"}
            },
            "id": "test_123"
        }
        
        response = self.runner.handle_request(request)
        
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32602)
        self.assertIn("not found", response["error"]["data"])
        
    def test_execute_hook_validation_failure(self):
        """Test executing a hook that fails validation."""
        request = {
            "jsonrpc": "2.0",
            "method": "execute_hook",
            "params": {
                "hook_name": "ticket_detection",
                "hook_type": "submit",
                "context_data": {},  # Missing required 'prompt'
                "metadata": {}
            },
            "id": "test_123"
        }
        
        response = self.runner.handle_request(request)
        
        self.assertIn("result", response)
        result = response["result"]
        self.assertFalse(result["success"])
        self.assertTrue(result.get("skipped", False))
        
    def test_handle_batch_requests(self):
        """Test handling batch requests."""
        batch = [
            {
                "jsonrpc": "2.0",
                "method": "execute_hook",
                "params": {
                    "hook_name": "ticket_detection",
                    "hook_type": "submit",
                    "context_data": {"prompt": "Fix TSK-123"}
                },
                "id": "batch_0"
            },
            {
                "jsonrpc": "2.0",
                "method": "execute_hook",
                "params": {
                    "hook_name": "priority_detection",
                    "hook_type": "submit",
                    "context_data": {"prompt": "urgent fix needed"}
                },
                "id": "batch_1"
            }
        ]
        
        responses = self.runner.handle_batch(batch)
        
        self.assertEqual(len(responses), 2)
        self.assertIn("result", responses[0])
        self.assertIn("result", responses[1])
        
        # First hook should find ticket
        self.assertTrue(responses[0]["result"]["success"])
        self.assertEqual(responses[0]["result"]["data"]["tickets"], ["TSK-123"])
        
        # Second hook should detect priority
        self.assertTrue(responses[1]["result"]["success"])
        self.assertEqual(responses[1]["result"]["data"]["priority"], "high")


class TestJSONRPCHookClient(unittest.TestCase):
    """Test cases for JSONRPCHookClient."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = JSONRPCHookClient(timeout=5)
        
    def test_health_check(self):
        """Test health check."""
        health = self.client.health_check()
        
        self.assertEqual(health["status"], "healthy")
        self.assertEqual(health["executor"], "json-rpc")
        self.assertIn("hook_count", health)
        self.assertIn("discovered_hooks", health)
        
    def test_list_hooks(self):
        """Test listing hooks."""
        hooks = self.client.list_hooks()
        
        # Should have hooks for each type
        self.assertIn("submit", hooks)
        self.assertIn("pre_delegation", hooks)
        self.assertIn("post_delegation", hooks)
        self.assertIn("ticket_extraction", hooks)
        
        # Submit hooks should include our examples
        submit_hooks = hooks["submit"]
        hook_names = [h["name"] for h in submit_hooks]
        self.assertIn("ticket_detection", hook_names)
        self.assertIn("priority_detection", hook_names)
        
    def test_execute_specific_hook(self):
        """Test executing a specific hook."""
        with patch.object(self.client.executor, 'execute_hook') as mock_execute:
            mock_execute.return_value = {
                "hook_name": "test_hook",
                "success": True,
                "data": {"result": "ok"}
            }
            
            results = self.client.execute_hook(
                hook_type=HookType.SUBMIT,
                context_data={"prompt": "test"},
                specific_hook="test_hook"
            )
            
            self.assertEqual(len(results), 1)
            self.assertTrue(results[0]["success"])
            mock_execute.assert_called_once()
            
    def test_execute_all_hooks_of_type(self):
        """Test executing all hooks of a type."""
        with patch.object(self.client.executor, 'execute_hooks') as mock_execute:
            mock_execute.return_value = [
                {"hook_name": "hook1", "success": True},
                {"hook_name": "hook2", "success": True}
            ]
            
            results = self.client.execute_hook(
                hook_type=HookType.SUBMIT,
                context_data={"prompt": "test"}
            )
            
            self.assertEqual(len(results), 2)
            mock_execute.assert_called_once()
            
    def test_convenience_methods(self):
        """Test convenience methods for different hook types."""
        with patch.object(self.client, 'execute_hook') as mock_execute:
            mock_execute.return_value = [{"success": True}]
            
            # Test submit hook
            self.client.execute_submit_hook("test prompt")
            mock_execute.assert_called_with(
                HookType.SUBMIT,
                {"prompt": "test prompt"}
            )
            
            # Test pre-delegation hook
            self.client.execute_pre_delegation_hook("agent1", {"context": "data"})
            mock_execute.assert_called_with(
                HookType.PRE_DELEGATION,
                {"agent": "agent1", "context": {"context": "data"}}
            )
            
            # Test post-delegation hook
            self.client.execute_post_delegation_hook("agent1", "result")
            mock_execute.assert_called_with(
                HookType.POST_DELEGATION,
                {"agent": "agent1", "result": "result"}
            )
            
            # Test ticket extraction hook
            self.client.execute_ticket_extraction_hook("content")
            mock_execute.assert_called_with(
                HookType.TICKET_EXTRACTION,
                {"content": "content"}
            )
            
    def test_get_modified_data(self):
        """Test extracting modified data from results."""
        results = [
            {
                "hook_name": "hook1",
                "success": True,
                "modified": True,
                "data": {"key1": "value1", "key2": "value2"}
            },
            {
                "hook_name": "hook2",
                "success": True,
                "modified": False,
                "data": {"key3": "value3"}
            },
            {
                "hook_name": "hook3",
                "success": True,
                "modified": True,
                "data": {"key2": "updated_value2", "key4": "value4"}
            }
        ]
        
        modified_data = self.client.get_modified_data(results)
        
        # Should merge data from modified hooks only
        self.assertEqual(modified_data["key1"], "value1")
        self.assertEqual(modified_data["key2"], "updated_value2")  # Later value wins
        self.assertEqual(modified_data["key4"], "value4")
        self.assertNotIn("key3", modified_data)  # Not modified
        
    def test_get_extracted_tickets(self):
        """Test extracting tickets from results."""
        results = [
            {
                "hook_name": "hook1",
                "success": True,
                "data": {"tickets": ["TSK-001", "TSK-002"]}
            },
            {
                "hook_name": "hook2",
                "success": False,
                "data": {"tickets": ["TSK-003"]}  # Failed, should be ignored
            },
            {
                "hook_name": "hook3",
                "success": True,
                "data": {"other": "data"}  # No tickets
            },
            {
                "hook_name": "hook4",
                "success": True,
                "data": {"tickets": ["TSK-004"]}
            }
        ]
        
        tickets = self.client.get_extracted_tickets(results)
        
        # Should only include tickets from successful hooks
        self.assertEqual(len(tickets), 3)
        self.assertIn("TSK-001", tickets)
        self.assertIn("TSK-002", tickets)
        self.assertIn("TSK-004", tickets)
        self.assertNotIn("TSK-003", tickets)  # From failed hook


class TestIntegration(unittest.TestCase):
    """Integration tests for the JSON-RPC hook system."""
    
    def test_end_to_end_hook_execution(self):
        """Test end-to-end hook execution via JSON-RPC."""
        client = JSONRPCHookClient()
        
        # Execute a submit hook
        results = client.execute_submit_hook("Please fix TSK-123 urgently")
        
        # Should have results from both ticket and priority detection
        self.assertTrue(len(results) >= 2)
        
        # Check ticket detection worked
        ticket_results = [r for r in results if r.get("hook_name") == "ticket_detection"]
        self.assertTrue(len(ticket_results) > 0)
        self.assertTrue(ticket_results[0]["success"])
        self.assertIn("TSK-123", ticket_results[0]["data"]["tickets"])
        
        # Check priority detection worked
        priority_results = [r for r in results if r.get("hook_name") == "priority_detection"]
        self.assertTrue(len(priority_results) > 0)
        self.assertTrue(priority_results[0]["success"])
        self.assertEqual(priority_results[0]["data"]["priority"], "high")
        
    def test_hook_client_backward_compatibility(self):
        """Test backward compatibility with get_hook_client function."""
        # Test importing from old location shows deprecation warning
        with self.assertWarns(DeprecationWarning):
            from claude_mpm.hooks.hook_client import get_hook_client
            client = get_hook_client()
        
        # Should always return JSON-RPC client now
        self.assertIsInstance(client, JSONRPCHookClient)
        
        # Test direct import from new location (no warning)
        from claude_mpm.hooks.json_rpc_hook_client import get_hook_client as get_json_rpc_client
        client2 = get_json_rpc_client()
        self.assertIsInstance(client2, JSONRPCHookClient)
    
    def test_http_client_deprecation_warning(self):
        """Test that HookServiceClient shows deprecation warning."""
        with self.assertWarns(DeprecationWarning) as cm:
            from claude_mpm.hooks.hook_client import HookServiceClient
            client = HookServiceClient()
        
        # Check warning message
        self.assertIn("HookServiceClient is deprecated", str(cm.warning.message))


if __name__ == '__main__':
    unittest.main()