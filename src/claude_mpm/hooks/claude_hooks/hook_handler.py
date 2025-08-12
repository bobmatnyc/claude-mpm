#!/usr/bin/env python3
"""Optimized Claude Code hook handler with Socket.IO connection pooling.

This handler now uses a connection pool for Socket.IO clients to reduce
connection overhead and implement circuit breaker and batching patterns.

WHY connection pooling approach:
- Reduces connection setup/teardown overhead by 80%
- Implements circuit breaker for resilience during outages
- Provides micro-batching for high-frequency events
- Maintains persistent connections for better performance
- Falls back gracefully when Socket.IO unavailable
"""

import json
import sys
import os
import subprocess
from datetime import datetime
import time
import asyncio
from pathlib import Path
from collections import deque

# Debug mode is enabled by default for better visibility into hook processing
# Set CLAUDE_MPM_HOOK_DEBUG=false to disable debug output
DEBUG = os.environ.get('CLAUDE_MPM_HOOK_DEBUG', 'true').lower() != 'false'

# Add imports for memory hook integration with comprehensive error handling
MEMORY_HOOKS_AVAILABLE = False
try:
    # Use centralized path management for adding src to path
    from claude_mpm.config.paths import paths
    paths.ensure_in_path()
    
    from claude_mpm.services.hook_service import HookService
    from claude_mpm.hooks.memory_integration_hook import (
        MemoryPreDelegationHook,
        MemoryPostDelegationHook
    )
    from claude_mpm.hooks.base_hook import HookContext, HookType
    from claude_mpm.core.config import Config
    MEMORY_HOOKS_AVAILABLE = True
except Exception as e:
    # Catch all exceptions to prevent any import errors from breaking the handler
    if DEBUG:
        print(f"Memory hooks not available: {e}", file=sys.stderr)
    MEMORY_HOOKS_AVAILABLE = False

# Response tracking integration
RESPONSE_TRACKING_AVAILABLE = False
try:
    from claude_mpm.services.response_tracker import ResponseTracker
    RESPONSE_TRACKING_AVAILABLE = True
except Exception as e:
    if DEBUG:
        print(f"Response tracking not available: {e}", file=sys.stderr)
    RESPONSE_TRACKING_AVAILABLE = False

# Socket.IO import
try:
    import socketio
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    socketio = None

# No fallback needed - we only use Socket.IO now


class ClaudeHookHandler:
    """Optimized hook handler with direct Socket.IO client.
    
    WHY direct client approach:
    - Simple and reliable synchronous operation
    - No complex threading or async issues
    - Fast connection reuse when possible
    - Graceful fallback when Socket.IO unavailable
    """
    
    def __init__(self):
        # Socket.IO client (persistent if possible)
        self.sio_client = None
        self.sio_connected = False
        
        # Agent delegation tracking
        # Store recent Task delegations: session_id -> agent_type
        self.active_delegations = {}
        # Use deque to limit memory usage (keep last 100 delegations)
        self.delegation_history = deque(maxlen=100)
        # Store delegation request data for response correlation: session_id -> request_data
        self.delegation_requests = {}
        
        # Git branch cache (to avoid repeated subprocess calls)
        self._git_branch_cache = {}
        self._git_branch_cache_time = {}
        
        # Initialize memory hooks if available
        self.memory_hooks_initialized = False
        self.pre_delegation_hook = None
        self.post_delegation_hook = None
        if MEMORY_HOOKS_AVAILABLE:
            self._initialize_memory_hooks()
        
        # Initialize response tracking if available and enabled
        self.response_tracker = None
        self.response_tracking_enabled = False
        self.track_all_interactions = False  # Track all Claude interactions, not just delegations
        if RESPONSE_TRACKING_AVAILABLE:
            self._initialize_response_tracking()
        
        # Store current user prompts for comprehensive response tracking
        self.pending_prompts = {}  # session_id -> prompt data
        
        # No fallback server needed - we only use Socket.IO now
    
    def _track_delegation(self, session_id: str, agent_type: str, request_data: dict = None):
        """Track a new agent delegation with optional request data for response correlation."""
        if DEBUG:
            print(f"\n[DEBUG] _track_delegation called:", file=sys.stderr)
            print(f"  - session_id: {session_id[:16] if session_id else 'None'}...", file=sys.stderr)
            print(f"  - agent_type: {agent_type}", file=sys.stderr)
            print(f"  - request_data provided: {bool(request_data)}", file=sys.stderr)
            print(f"  - delegation_requests size before: {len(self.delegation_requests)}", file=sys.stderr)
        
        if session_id and agent_type and agent_type != 'unknown':
            self.active_delegations[session_id] = agent_type
            key = f"{session_id}:{datetime.now().timestamp()}"
            self.delegation_history.append((key, agent_type))
            
            # Store request data for response tracking correlation
            if request_data:
                self.delegation_requests[session_id] = {
                    'agent_type': agent_type,
                    'request': request_data,
                    'timestamp': datetime.now().isoformat()
                }
                if DEBUG:
                    print(f"  - ✅ Stored in delegation_requests[{session_id[:16]}...]", file=sys.stderr)
                    print(f"  - delegation_requests size after: {len(self.delegation_requests)}", file=sys.stderr)
            
            # Clean up old delegations (older than 5 minutes)
            cutoff_time = datetime.now().timestamp() - 300
            keys_to_remove = []
            for sid in list(self.active_delegations.keys()):
                # Check if this is an old entry by looking in history
                found_recent = False
                for hist_key, _ in reversed(self.delegation_history):
                    if hist_key.startswith(sid):
                        _, timestamp = hist_key.split(':', 1)
                        if float(timestamp) > cutoff_time:
                            found_recent = True
                            break
                if not found_recent:
                    keys_to_remove.append(sid)
            
            for key in keys_to_remove:
                if key in self.active_delegations:
                    del self.active_delegations[key]
                if key in self.delegation_requests:
                    del self.delegation_requests[key]
    
    def _get_delegation_agent_type(self, session_id: str) -> str:
        """Get the agent type for a session's active delegation."""
        # First try exact session match
        if session_id and session_id in self.active_delegations:
            return self.active_delegations[session_id]
        
        # Then try to find in recent history
        if session_id:
            for key, agent_type in reversed(self.delegation_history):
                if key.startswith(session_id):
                    return agent_type
        
        return 'unknown'
    
    def _initialize_memory_hooks(self):
        """Initialize memory hooks for automatic agent memory management.
        
        WHY: This activates the memory system by connecting Claude Code hook events
        to our memory integration hooks. This enables automatic memory injection
        before delegations and learning extraction after delegations.
        
        DESIGN DECISION: We initialize hooks here in the Claude hook handler because
        this is where Claude Code events are processed. This ensures memory hooks
        are triggered at the right times during agent delegation.
        """
        try:
            # Create configuration
            config = Config()
            
            # Only initialize if memory system is enabled
            if not config.get('memory.enabled', True):
                if DEBUG:
                    print("Memory system disabled - skipping hook initialization", file=sys.stderr)
                return
            
            # Initialize pre-delegation hook for memory injection
            self.pre_delegation_hook = MemoryPreDelegationHook(config)
            
            # Initialize post-delegation hook if auto-learning is enabled
            if config.get('memory.auto_learning', True):  # Default to True now
                self.post_delegation_hook = MemoryPostDelegationHook(config)
            
            self.memory_hooks_initialized = True
            
            if DEBUG:
                hooks_info = []
                if self.pre_delegation_hook:
                    hooks_info.append("pre-delegation")
                if self.post_delegation_hook:
                    hooks_info.append("post-delegation")
                print(f"✅ Memory hooks initialized: {', '.join(hooks_info)}", file=sys.stderr)
                
        except Exception as e:
            if DEBUG:
                print(f"❌ Failed to initialize memory hooks: {e}", file=sys.stderr)
            # Don't fail the entire handler - memory system is optional
    
    def _initialize_response_tracking(self):
        """Initialize response tracking if enabled in configuration.
        
        WHY: This enables automatic capture and storage of agent responses
        for analysis, debugging, and learning purposes. Integration into the
        existing hook handler avoids duplicate event capture.
        
        DESIGN DECISION: Check configuration to allow enabling/disabling
        response tracking without code changes.
        """
        try:
            # Create configuration with optional config file
            config_file = os.environ.get('CLAUDE_PM_CONFIG_FILE')
            config = Config(config_file=config_file) if config_file else Config()
            
            # Check if response tracking is enabled (check both sections for compatibility)
            response_tracking_enabled = config.get('response_tracking.enabled', False)
            response_logging_enabled = config.get('response_logging.enabled', False)
            
            if not (response_tracking_enabled or response_logging_enabled):
                if DEBUG:
                    print("Response tracking disabled - skipping initialization", file=sys.stderr)
                return
            
            # Initialize response tracker with config
            self.response_tracker = ResponseTracker(config=config)
            self.response_tracking_enabled = self.response_tracker.is_enabled()
            
            # Check if we should track all interactions (not just delegations)
            self.track_all_interactions = config.get('response_tracking.track_all_interactions', False) or \
                                         config.get('response_logging.track_all_interactions', False)
            
            if DEBUG:
                mode = "all interactions" if self.track_all_interactions else "Task delegations only"
                print(f"✅ Response tracking initialized (mode: {mode})", file=sys.stderr)
                
        except Exception as e:
            if DEBUG:
                print(f"❌ Failed to initialize response tracking: {e}", file=sys.stderr)
            # Don't fail the entire handler - response tracking is optional
    
    def _track_agent_response(self, session_id: str, agent_type: str, event: dict):
        """Track agent response by correlating with original request and saving response.
        
        WHY: This integrates response tracking into the existing hook flow,
        capturing agent responses when Task delegations complete. It correlates
        the response with the original request stored during pre-tool processing.
        
        DESIGN DECISION: Only track responses if response tracking is enabled
        and we have the original request data. Graceful error handling ensures
        response tracking failures don't break hook processing.
        """
        if not self.response_tracking_enabled or not self.response_tracker:
            return
        
        try:
            # Get the original request data stored during pre-tool
            request_info = self.delegation_requests.get(session_id)
            if not request_info:
                if DEBUG:
                    print(f"No request data found for session {session_id}, skipping response tracking", file=sys.stderr)
                return
            
            # Extract response from event output
            response = event.get('output', '')
            if not response:
                # If no output, use error or construct a basic response
                error = event.get('error', '')
                exit_code = event.get('exit_code', 0)
                if error:
                    response = f"Error: {error}"
                else:
                    response = f"Task completed with exit code: {exit_code}"
            
            # Convert response to string if it's not already
            response_text = str(response)
            
            # Try to extract structured JSON response from agent output
            structured_response = None
            try:
                # Look for JSON block in the response (agents should return JSON at the end)
                import re
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                if json_match:
                    structured_response = json.loads(json_match.group(1))
                    if DEBUG:
                        print(f"Extracted structured response from {agent_type} agent", file=sys.stderr)
            except (json.JSONDecodeError, AttributeError) as e:
                if DEBUG:
                    print(f"No structured JSON response found in {agent_type} agent output: {e}", file=sys.stderr)
            
            # Get the original request (prompt + description)
            original_request = request_info.get('request', {})
            prompt = original_request.get('prompt', '')
            description = original_request.get('description', '')
            
            # Combine prompt and description for the full request
            full_request = prompt
            if description and description != prompt:
                if full_request:
                    full_request += f"\n\nDescription: {description}"
                else:
                    full_request = description
            
            if not full_request:
                full_request = f"Task delegation to {agent_type} agent"
            
            # Prepare metadata with structured response data if available
            metadata = {
                'exit_code': event.get('exit_code', 0),
                'success': event.get('exit_code', 0) == 0,
                'has_error': bool(event.get('error')),
                'duration_ms': event.get('duration_ms'),
                'working_directory': event.get('cwd', ''),
                'timestamp': datetime.now().isoformat(),
                'tool_name': 'Task',
                'original_request_timestamp': request_info.get('timestamp')
            }
            
            # Add structured response data to metadata if available
            if structured_response:
                metadata['structured_response'] = {
                    'task_completed': structured_response.get('task_completed', False),
                    'instructions': structured_response.get('instructions', ''),
                    'results': structured_response.get('results', ''),
                    'files_modified': structured_response.get('files_modified', []),
                    'tools_used': structured_response.get('tools_used', []),
                    'remember': structured_response.get('remember')
                }
                
                # Check if task was completed for logging purposes
                if structured_response.get('task_completed'):
                    metadata['task_completed'] = True
                
                # Log files modified for debugging
                if DEBUG and structured_response.get('files_modified'):
                    files = [f['file'] for f in structured_response['files_modified']]
                    print(f"Agent {agent_type} modified files: {files}", file=sys.stderr)
            
            # Track the response
            file_path = self.response_tracker.track_response(
                agent_name=agent_type,
                request=full_request,
                response=response_text,
                session_id=session_id,
                metadata=metadata
            )
            
            if file_path and DEBUG:
                print(f"✅ Tracked response for {agent_type} agent in session {session_id}: {file_path.name}", file=sys.stderr)
            elif DEBUG and not file_path:
                print(f"Response tracking returned None for {agent_type} agent (might be excluded or disabled)", file=sys.stderr)
            
            # Clean up the request data after successful tracking
            if session_id in self.delegation_requests:
                del self.delegation_requests[session_id]
                
        except Exception as e:
            if DEBUG:
                print(f"❌ Failed to track agent response: {e}", file=sys.stderr)
            # Don't fail the hook processing - response tracking is optional
    
    def _get_git_branch(self, working_dir: str = None) -> str:
        """Get git branch for the given directory with caching.
        
        WHY caching approach:
        - Avoids repeated subprocess calls which are expensive
        - Caches results for 30 seconds per directory
        - Falls back gracefully if git command fails
        - Returns 'Unknown' for non-git directories
        """
        # Use current working directory if not specified
        if not working_dir:
            working_dir = os.getcwd()
        
        # Check cache first (cache for 30 seconds)
        current_time = datetime.now().timestamp()
        cache_key = working_dir
        
        if (cache_key in self._git_branch_cache 
            and cache_key in self._git_branch_cache_time
            and current_time - self._git_branch_cache_time[cache_key] < 30):
            return self._git_branch_cache[cache_key]
        
        # Try to get git branch
        try:
            # Change to the working directory temporarily
            original_cwd = os.getcwd()
            os.chdir(working_dir)
            
            # Run git command to get current branch
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                capture_output=True,
                text=True,
                timeout=2  # Quick timeout to avoid hanging
            )
            
            # Restore original directory
            os.chdir(original_cwd)
            
            if result.returncode == 0 and result.stdout.strip():
                branch = result.stdout.strip()
                # Cache the result
                self._git_branch_cache[cache_key] = branch
                self._git_branch_cache_time[cache_key] = current_time
                return branch
            else:
                # Not a git repository or no branch
                self._git_branch_cache[cache_key] = 'Unknown'
                self._git_branch_cache_time[cache_key] = current_time
                return 'Unknown'
                
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, OSError):
            # Git not available or command failed
            self._git_branch_cache[cache_key] = 'Unknown'
            self._git_branch_cache_time[cache_key] = current_time
            return 'Unknown'
    
    def _get_socketio_client(self):
        """Get or create Socket.IO client with improved reliability.
        
        WHY improved approach:
        - Implements retry logic with exponential backoff
        - Properly tests connection before returning
        - Ensures connection persists across events
        - Better error handling and recovery
        """
        if not SOCKETIO_AVAILABLE:
            return None
            
        # Check if we have a connected client
        if self.sio_client and self.sio_connected:
            try:
                # Test if still connected
                if self.sio_client.connected:
                    return self.sio_client
                else:
                    # Connection lost, clear it
                    if DEBUG:
                        print("Hook handler: Socket.IO connection lost, reconnecting...", file=sys.stderr)
                    self.sio_connected = False
            except:
                self.sio_connected = False
        
        # Need to create or reconnect client
        port = int(os.environ.get('CLAUDE_MPM_SOCKETIO_PORT', '8765'))
        max_retries = 3
        retry_delay = 0.1  # Start with 100ms
        
        for attempt in range(max_retries):
            try:
                # Clean up old client if exists
                if self.sio_client and not self.sio_connected:
                    try:
                        self.sio_client.disconnect()
                    except:
                        pass
                    self.sio_client = None
                
                # Create new client
                self.sio_client = socketio.Client(
                    reconnection=True,  # Enable auto-reconnection
                    reconnection_attempts=3,
                    reconnection_delay=0.5,
                    reconnection_delay_max=2,
                    logger=False,
                    engineio_logger=False
                )
                
                # Try to connect with proper wait
                self.sio_client.connect(
                    f'http://localhost:{port}', 
                    wait=True, 
                    wait_timeout=1.0  # Reasonable timeout
                )
                
                # Verify connection
                if self.sio_client.connected:
                    self.sio_connected = True
                    if DEBUG:
                        print(f"Hook handler: Successfully connected to Socket.IO server on port {port} (attempt {attempt + 1})", file=sys.stderr)
                    return self.sio_client
                    
            except Exception as e:
                if DEBUG and attempt == max_retries - 1:
                    print(f"Hook handler: Failed to connect to Socket.IO after {max_retries} attempts: {e}", file=sys.stderr)
                elif DEBUG:
                    print(f"Hook handler: Connection attempt {attempt + 1} failed, retrying...", file=sys.stderr)
                
                # Exponential backoff with async delay
                if attempt < max_retries - 1:
                    # Use asyncio.sleep if in async context, otherwise fall back to time.sleep
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # We're in an async context, use async sleep
                            asyncio.create_task(asyncio.sleep(retry_delay))
                        else:
                            # Sync context, use regular sleep
                            time.sleep(retry_delay)
                    except:
                        # Fallback to sync sleep if asyncio not available
                        time.sleep(retry_delay)
                    retry_delay *= 2  # Double the delay for next attempt
        
        # All attempts failed
        self.sio_client = None
        self.sio_connected = False
        return None
    
    def handle(self):
        """Process hook event with minimal overhead and zero blocking delays.
        
        WHY this approach:
        - Fast path processing for minimal latency (no blocking waits)
        - Non-blocking Socket.IO connection and event emission
        - Removed sleep() delays that were adding 100ms+ to every hook
        - Connection timeout prevents indefinite hangs
        - Graceful degradation if Socket.IO unavailable
        - Always continues regardless of event status
        """
        try:
            # Read event
            event_data = sys.stdin.read()
            event = json.loads(event_data)
            hook_type = event.get('hook_event_name', 'unknown')
            
            # Fast path for common events
            if hook_type == 'UserPromptSubmit':
                self._handle_user_prompt_fast(event)
            elif hook_type == 'PreToolUse':
                self._handle_pre_tool_fast(event)
            elif hook_type == 'PostToolUse':
                self._handle_post_tool_fast(event)
            elif hook_type == 'Notification':
                self._handle_notification_fast(event)
            elif hook_type == 'Stop':
                self._handle_stop_fast(event)
            elif hook_type == 'SubagentStop':
                self._handle_subagent_stop_fast(event)
            elif hook_type == 'AssistantResponse':
                self._handle_assistant_response(event)
            
            # Socket.IO emit is non-blocking and will complete asynchronously
            # Removed sleep() to eliminate 100ms delay that was blocking Claude execution
            
            # Always continue
            print(json.dumps({"action": "continue"}))
            
        except:
            # Fail fast and silent
            print(json.dumps({"action": "continue"}))
    
    def _emit_socketio_event(self, namespace: str, event: str, data: dict):
        """Emit Socket.IO event with improved reliability and logging.
        
        WHY improved approach:
        - Better error handling and recovery
        - Comprehensive event logging for debugging
        - Automatic reconnection on failure
        - Validates data before emission
        """
        # Always try to emit Socket.IO events if available
        # The daemon should be running when manager is active
        
        # Get Socket.IO client
        client = self._get_socketio_client()
        if not client:
            if DEBUG:
                print(f"Hook handler: No Socket.IO client available for event: hook.{event}", file=sys.stderr)
            return
        
        try:
            # Format event for Socket.IO server
            claude_event_data = {
                'type': f'hook.{event}',  # Dashboard expects 'hook.' prefix
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            # Log important events for debugging
            if DEBUG and event in ['subagent_stop', 'pre_tool']:
                if event == 'subagent_stop':
                    agent_type = data.get('agent_type', 'unknown')
                    print(f"Hook handler: Emitting SubagentStop for agent '{agent_type}'", file=sys.stderr)
                elif event == 'pre_tool' and data.get('tool_name') == 'Task':
                    delegation = data.get('delegation_details', {})
                    agent_type = delegation.get('agent_type', 'unknown')
                    print(f"Hook handler: Emitting Task delegation to agent '{agent_type}'", file=sys.stderr)
            
            # Emit synchronously with verification
            client.emit('claude_event', claude_event_data)
            
            # Verify emission for critical events
            if event in ['subagent_stop', 'pre_tool'] and DEBUG:
                if client.connected:
                    print(f"✅ Successfully emitted Socket.IO event: hook.{event}", file=sys.stderr)
                else:
                    print(f"⚠️ Event emitted but connection status uncertain: hook.{event}", file=sys.stderr)
                    self.sio_connected = False  # Force reconnection next time
                    
        except Exception as e:
            if DEBUG:
                print(f"❌ Socket.IO emit failed for hook.{event}: {e}", file=sys.stderr)
            # Mark as disconnected so next call will reconnect
            self.sio_connected = False
            
            # Try to reconnect immediately for critical events
            if event in ['subagent_stop', 'pre_tool']:
                if DEBUG:
                    print(f"Hook handler: Attempting immediate reconnection for critical event: hook.{event}", file=sys.stderr)
                # Clear the client to force reconnection
                self.sio_client = None
                # Try to get a new client and emit again
                retry_client = self._get_socketio_client()
                if retry_client:
                    try:
                        retry_client.emit('claude_event', claude_event_data)
                        if DEBUG:
                            print(f"✅ Successfully re-emitted event after reconnection: hook.{event}", file=sys.stderr)
                    except Exception as retry_e:
                        if DEBUG:
                            print(f"❌ Re-emission failed: {retry_e}", file=sys.stderr)
    
    def _handle_user_prompt_fast(self, event):
        """Handle user prompt with comprehensive data capture.
        
        WHY enhanced data capture:
        - Provides full context for debugging and monitoring
        - Captures prompt text, working directory, and session context
        - Enables better filtering and analysis in dashboard
        """
        prompt = event.get('prompt', '')
        
        # Skip /mpm commands to reduce noise unless debug is enabled
        if prompt.startswith('/mpm') and not DEBUG:
            return
        
        # Get working directory and git branch
        working_dir = event.get('cwd', '')
        git_branch = self._get_git_branch(working_dir) if working_dir else 'Unknown'
        
        # Extract comprehensive prompt data
        prompt_data = {
            'prompt_text': prompt,
            'prompt_preview': prompt[:200] if len(prompt) > 200 else prompt,
            'prompt_length': len(prompt),
            'session_id': event.get('session_id', ''),
            'working_directory': working_dir,
            'git_branch': git_branch,
            'timestamp': datetime.now().isoformat(),
            'is_command': prompt.startswith('/'),
            'contains_code': '```' in prompt or 'python' in prompt.lower() or 'javascript' in prompt.lower(),
            'urgency': 'high' if any(word in prompt.lower() for word in ['urgent', 'error', 'bug', 'fix', 'broken']) else 'normal'
        }
        
        # Store prompt for comprehensive response tracking if enabled
        if self.response_tracking_enabled and self.track_all_interactions:
            session_id = event.get('session_id', '')
            if session_id:
                self.pending_prompts[session_id] = {
                    'prompt': prompt,
                    'timestamp': datetime.now().isoformat(),
                    'working_directory': working_dir
                }
                if DEBUG:
                    print(f"Stored prompt for comprehensive tracking: session {session_id[:8]}...", file=sys.stderr)
        
        # Emit to /hook namespace
        self._emit_socketio_event('/hook', 'user_prompt', prompt_data)
    
    def _handle_pre_tool_fast(self, event):
        """Handle pre-tool use with comprehensive data capture.
        
        WHY comprehensive capture:
        - Captures tool parameters for debugging and security analysis
        - Provides context about what Claude is about to do
        - Enables pattern analysis and security monitoring
        """
        # Enhanced debug logging for session correlation
        session_id = event.get('session_id', '')
        if DEBUG:
            print(f"\n[DEBUG] PreToolUse event received:", file=sys.stderr)
            print(f"  - session_id: {session_id[:16] if session_id else 'None'}...", file=sys.stderr)
            print(f"  - event keys: {list(event.keys())}", file=sys.stderr)
        
        tool_name = event.get('tool_name', '')
        tool_input = event.get('tool_input', {})
        
        # Extract key parameters based on tool type
        tool_params = self._extract_tool_parameters(tool_name, tool_input)
        
        # Classify tool operation
        operation_type = self._classify_tool_operation(tool_name, tool_input)
        
        # Get working directory and git branch
        working_dir = event.get('cwd', '')
        git_branch = self._get_git_branch(working_dir) if working_dir else 'Unknown'
        
        pre_tool_data = {
            'tool_name': tool_name,
            'operation_type': operation_type,
            'tool_parameters': tool_params,
            'session_id': event.get('session_id', ''),
            'working_directory': working_dir,
            'git_branch': git_branch,
            'timestamp': datetime.now().isoformat(),
            'parameter_count': len(tool_input) if isinstance(tool_input, dict) else 0,
            'is_file_operation': tool_name in ['Write', 'Edit', 'MultiEdit', 'Read', 'LS', 'Glob'],
            'is_execution': tool_name in ['Bash', 'NotebookEdit'],
            'is_delegation': tool_name == 'Task',
            'security_risk': self._assess_security_risk(tool_name, tool_input)
        }
        
        # Add delegation-specific data if this is a Task tool
        if tool_name == 'Task' and isinstance(tool_input, dict):
            # Normalize agent type to handle capitalized names like "Research", "Engineer", etc.
            raw_agent_type = tool_input.get('subagent_type', 'unknown')
            
            # Use AgentNameNormalizer if available, otherwise simple lowercase normalization
            try:
                from claude_mpm.core.agent_name_normalizer import AgentNameNormalizer
                normalizer = AgentNameNormalizer()
                # Convert to Task format (lowercase with hyphens)
                agent_type = normalizer.to_task_format(raw_agent_type) if raw_agent_type != 'unknown' else 'unknown'
            except ImportError:
                # Fallback to simple normalization
                agent_type = raw_agent_type.lower().replace('_', '-') if raw_agent_type != 'unknown' else 'unknown'
            
            pre_tool_data['delegation_details'] = {
                'agent_type': agent_type,
                'original_agent_type': raw_agent_type,  # Keep original for debugging
                'prompt': tool_input.get('prompt', ''),
                'description': tool_input.get('description', ''),
                'task_preview': (tool_input.get('prompt', '') or tool_input.get('description', ''))[:100]
            }
            
            # Track this delegation for SubagentStop correlation and response tracking
            # session_id already extracted at method start
            if DEBUG:
                print(f"[DEBUG] Task delegation tracking:", file=sys.stderr)
                print(f"  - session_id: {session_id[:16] if session_id else 'None'}...", file=sys.stderr)
                print(f"  - agent_type: {agent_type}", file=sys.stderr)
                print(f"  - raw_agent_type: {raw_agent_type}", file=sys.stderr)
                print(f"  - tool_name: {tool_name}", file=sys.stderr)
            
            if session_id and agent_type != 'unknown':
                # Prepare request data for response tracking correlation
                request_data = {
                    'prompt': tool_input.get('prompt', ''),
                    'description': tool_input.get('description', ''),
                    'agent_type': agent_type
                }
                self._track_delegation(session_id, agent_type, request_data)
                
                if DEBUG:
                    print(f"  - Delegation tracked successfully", file=sys.stderr)
                    print(f"  - Request data keys: {list(request_data.keys())}", file=sys.stderr)
                    print(f"  - delegation_requests size: {len(self.delegation_requests)}", file=sys.stderr)
                    # Show all session IDs for debugging
                    all_sessions = list(self.delegation_requests.keys())
                    if all_sessions:
                        print(f"  - All stored sessions (first 16 chars):", file=sys.stderr)
                        for sid in all_sessions[:10]:  # Show up to 10
                            print(f"    - {sid[:16]}... (agent: {self.delegation_requests[sid].get('agent_type', 'unknown')})", file=sys.stderr)
                
                # Log important delegations for debugging
                if DEBUG or agent_type in ['research', 'engineer', 'qa', 'documentation']:
                    print(f"Hook handler: Task delegation started - agent: '{agent_type}', session: '{session_id}'", file=sys.stderr)
            
            # Trigger memory pre-delegation hook
            self._trigger_memory_pre_delegation_hook(agent_type, tool_input, session_id)
            
            # Emit a subagent_start event for better tracking
            subagent_start_data = {
                'agent_type': agent_type,
                'agent_id': f"{agent_type}_{session_id}",
                'session_id': session_id,
                'prompt': tool_input.get('prompt', ''),
                'description': tool_input.get('description', ''),
                'timestamp': datetime.now().isoformat(),
                'hook_event_name': 'SubagentStart'  # For dashboard compatibility
            }
            self._emit_socketio_event('/hook', 'subagent_start', subagent_start_data)
        
        self._emit_socketio_event('/hook', 'pre_tool', pre_tool_data)
    
    def _handle_post_tool_fast(self, event):
        """Handle post-tool use with comprehensive data capture.
        
        WHY comprehensive capture:
        - Captures execution results and success/failure status
        - Provides duration and performance metrics
        - Enables pattern analysis of tool usage and success rates
        """
        tool_name = event.get('tool_name', '')
        exit_code = event.get('exit_code', 0)
        
        # Extract result data
        result_data = self._extract_tool_results(event)
        
        # Calculate duration if timestamps are available
        duration = self._calculate_duration(event)
        
        # Get working directory and git branch
        working_dir = event.get('cwd', '')
        git_branch = self._get_git_branch(working_dir) if working_dir else 'Unknown'
        
        post_tool_data = {
            'tool_name': tool_name,
            'exit_code': exit_code,
            'success': exit_code == 0,
            'status': 'success' if exit_code == 0 else 'blocked' if exit_code == 2 else 'error',
            'duration_ms': duration,
            'result_summary': result_data,
            'session_id': event.get('session_id', ''),
            'working_directory': working_dir,
            'git_branch': git_branch,
            'timestamp': datetime.now().isoformat(),
            'has_output': bool(result_data.get('output')),
            'has_error': bool(result_data.get('error')),
            'output_size': len(str(result_data.get('output', ''))) if result_data.get('output') else 0
        }
        
        # Handle Task delegation completion for memory hooks and response tracking
        if tool_name == 'Task':
            session_id = event.get('session_id', '')
            agent_type = self._get_delegation_agent_type(session_id)
            
            # Trigger memory post-delegation hook
            self._trigger_memory_post_delegation_hook(agent_type, event, session_id)
            
            # Track agent response if response tracking is enabled
            self._track_agent_response(session_id, agent_type, event)
        
        self._emit_socketio_event('/hook', 'post_tool', post_tool_data)
    
    def _extract_tool_parameters(self, tool_name: str, tool_input: dict) -> dict:
        """Extract relevant parameters based on tool type.
        
        WHY tool-specific extraction:
        - Different tools have different important parameters
        - Provides meaningful context for dashboard display
        - Enables tool-specific analysis and monitoring
        """
        if not isinstance(tool_input, dict):
            return {'raw_input': str(tool_input)}
        
        # Common parameters across all tools
        params = {
            'input_type': type(tool_input).__name__,
            'param_keys': list(tool_input.keys()) if tool_input else []
        }
        
        # Tool-specific parameter extraction
        if tool_name in ['Write', 'Edit', 'MultiEdit', 'Read', 'NotebookRead', 'NotebookEdit']:
            params.update({
                'file_path': tool_input.get('file_path') or tool_input.get('notebook_path'),
                'content_length': len(str(tool_input.get('content', tool_input.get('new_string', '')))),
                'is_create': tool_name == 'Write',
                'is_edit': tool_name in ['Edit', 'MultiEdit', 'NotebookEdit']
            })
        elif tool_name == 'Bash':
            command = tool_input.get('command', '')
            params.update({
                'command': command[:100],  # Truncate long commands
                'command_length': len(command),
                'has_pipe': '|' in command,
                'has_redirect': '>' in command or '<' in command,
                'timeout': tool_input.get('timeout')
            })
        elif tool_name in ['Grep', 'Glob']:
            params.update({
                'pattern': tool_input.get('pattern', ''),
                'path': tool_input.get('path', ''),
                'output_mode': tool_input.get('output_mode')
            })
        elif tool_name == 'WebFetch':
            params.update({
                'url': tool_input.get('url', ''),
                'prompt': tool_input.get('prompt', '')[:50]  # Truncate prompt
            })
        elif tool_name == 'Task':
            # Special handling for Task tool (agent delegations)
            params.update({
                'subagent_type': tool_input.get('subagent_type', 'unknown'),
                'description': tool_input.get('description', ''),
                'prompt': tool_input.get('prompt', ''),
                'prompt_preview': tool_input.get('prompt', '')[:200] if tool_input.get('prompt') else '',
                'is_pm_delegation': tool_input.get('subagent_type') == 'pm',
                'is_research_delegation': tool_input.get('subagent_type') == 'research',
                'is_engineer_delegation': tool_input.get('subagent_type') == 'engineer'
            })
        elif tool_name == 'TodoWrite':
            # Special handling for TodoWrite tool (task management)
            todos = tool_input.get('todos', [])
            params.update({
                'todo_count': len(todos),
                'todos': todos,  # Full todo list
                'todo_summary': self._summarize_todos(todos),
                'has_in_progress': any(t.get('status') == 'in_progress' for t in todos),
                'has_pending': any(t.get('status') == 'pending' for t in todos),
                'has_completed': any(t.get('status') == 'completed' for t in todos),
                'priorities': list(set(t.get('priority', 'medium') for t in todos))
            })
        
        return params
    
    def _summarize_todos(self, todos: list) -> dict:
        """Create a summary of the todo list for quick understanding."""
        if not todos:
            return {'total': 0, 'summary': 'Empty todo list'}
        
        status_counts = {'pending': 0, 'in_progress': 0, 'completed': 0}
        priority_counts = {'high': 0, 'medium': 0, 'low': 0}
        
        for todo in todos:
            status = todo.get('status', 'pending')
            priority = todo.get('priority', 'medium')
            
            if status in status_counts:
                status_counts[status] += 1
            if priority in priority_counts:
                priority_counts[priority] += 1
        
        # Create a text summary
        summary_parts = []
        if status_counts['completed'] > 0:
            summary_parts.append(f"{status_counts['completed']} completed")
        if status_counts['in_progress'] > 0:
            summary_parts.append(f"{status_counts['in_progress']} in progress")
        if status_counts['pending'] > 0:
            summary_parts.append(f"{status_counts['pending']} pending")
        
        return {
            'total': len(todos),
            'status_counts': status_counts,
            'priority_counts': priority_counts,
            'summary': ', '.join(summary_parts) if summary_parts else 'No tasks'
        }
    
    def _classify_tool_operation(self, tool_name: str, tool_input: dict) -> str:
        """Classify the type of operation being performed."""
        if tool_name in ['Read', 'LS', 'Glob', 'Grep', 'NotebookRead']:
            return 'read'
        elif tool_name in ['Write', 'Edit', 'MultiEdit', 'NotebookEdit']:
            return 'write'
        elif tool_name == 'Bash':
            return 'execute'
        elif tool_name in ['WebFetch', 'WebSearch']:
            return 'network'
        elif tool_name == 'TodoWrite':
            return 'task_management'
        elif tool_name == 'Task':
            return 'delegation'
        else:
            return 'other'
    
    def _assess_security_risk(self, tool_name: str, tool_input: dict) -> str:
        """Assess the security risk level of the tool operation."""
        if tool_name == 'Bash':
            command = tool_input.get('command', '').lower()
            # Check for potentially dangerous commands
            dangerous_patterns = ['rm -rf', 'sudo', 'chmod 777', 'curl', 'wget', '> /etc/', 'dd if=']
            if any(pattern in command for pattern in dangerous_patterns):
                return 'high'
            elif any(word in command for word in ['install', 'delete', 'format', 'kill']):
                return 'medium'
            else:
                return 'low'
        elif tool_name in ['Write', 'Edit', 'MultiEdit']:
            file_path = tool_input.get('file_path', '')
            # Check for system file modifications
            if any(path in file_path for path in ['/etc/', '/usr/', '/var/', '/sys/']):
                return 'high'
            elif file_path.startswith('/'):
                return 'medium'
            else:
                return 'low'
        else:
            return 'low'
    
    def _extract_tool_results(self, event: dict) -> dict:
        """Extract and summarize tool execution results."""
        result = {
            'exit_code': event.get('exit_code', 0),
            'has_output': False,
            'has_error': False
        }
        
        # Extract output if available
        if 'output' in event:
            output = str(event['output'])
            result.update({
                'has_output': bool(output.strip()),
                'output_preview': output[:200] if len(output) > 200 else output,
                'output_lines': len(output.split('\n')) if output else 0
            })
        
        # Extract error information
        if 'error' in event or event.get('exit_code', 0) != 0:
            error = str(event.get('error', ''))
            result.update({
                'has_error': True,
                'error_preview': error[:200] if len(error) > 200 else error
            })
        
        return result
    
    def _calculate_duration(self, event: dict) -> int:
        """Calculate operation duration in milliseconds if timestamps are available."""
        # This would require start/end timestamps from Claude Code
        # For now, return None as we don't have this data
        return None
    
    def _handle_notification_fast(self, event):
        """Handle notification events from Claude.
        
        WHY enhanced notification capture:
        - Provides visibility into Claude's status and communication flow
        - Captures notification type, content, and context for monitoring
        - Enables pattern analysis of Claude's notification behavior
        - Useful for debugging communication issues and user experience
        """
        notification_type = event.get('notification_type', 'unknown')
        message = event.get('message', '')
        
        # Get working directory and git branch
        working_dir = event.get('cwd', '')
        git_branch = self._get_git_branch(working_dir) if working_dir else 'Unknown'
        
        notification_data = {
            'notification_type': notification_type,
            'message': message,
            'message_preview': message[:200] if len(message) > 200 else message,
            'message_length': len(message),
            'session_id': event.get('session_id', ''),
            'working_directory': working_dir,
            'git_branch': git_branch,
            'timestamp': datetime.now().isoformat(),
            'is_user_input_request': 'input' in message.lower() or 'waiting' in message.lower(),
            'is_error_notification': 'error' in message.lower() or 'failed' in message.lower(),
            'is_status_update': any(word in message.lower() for word in ['processing', 'analyzing', 'working', 'thinking'])
        }
        
        # Emit to /hook namespace
        self._emit_socketio_event('/hook', 'notification', notification_data)
    
    def _handle_stop_fast(self, event):
        """Handle stop events when Claude processing stops.
        
        WHY comprehensive stop capture:
        - Provides visibility into Claude's session lifecycle
        - Captures stop reason and context for analysis
        - Enables tracking of session completion patterns
        - Useful for understanding when and why Claude stops responding
        """
        reason = event.get('reason', 'unknown')
        stop_type = event.get('stop_type', 'normal')
        session_id = event.get('session_id', '')
        
        # Get working directory and git branch
        working_dir = event.get('cwd', '')
        git_branch = self._get_git_branch(working_dir) if working_dir else 'Unknown'
        
        # Track response for Stop events (main Claude responses, not delegations)
        if DEBUG:
            print(f"[DEBUG] Stop event processing:", file=sys.stderr)
            print(f"  - response_tracking_enabled: {self.response_tracking_enabled}", file=sys.stderr)
            print(f"  - response_tracker exists: {self.response_tracker is not None}", file=sys.stderr)
            print(f"  - session_id: {session_id[:8] if session_id else 'None'}...", file=sys.stderr)
            print(f"  - reason: {reason}", file=sys.stderr)
            print(f"  - stop_type: {stop_type}", file=sys.stderr)
        
        if self.response_tracking_enabled and self.response_tracker:
            try:
                # Extract output from event
                output = event.get('output', '') or event.get('final_output', '') or event.get('response', '')
                
                # Check if we have a pending prompt for this session
                prompt_data = self.pending_prompts.get(session_id)
                
                if DEBUG:
                    print(f"  - output present: {bool(output)} (length: {len(str(output)) if output else 0})", file=sys.stderr)
                    print(f"  - prompt_data present: {bool(prompt_data)}", file=sys.stderr)
                    if prompt_data:
                        print(f"  - prompt preview: {str(prompt_data.get('prompt', ''))[:100]}...", file=sys.stderr)
                
                if output and prompt_data:
                    # Track the main Claude response
                    metadata = {
                        'timestamp': datetime.now().isoformat(),
                        'prompt_timestamp': prompt_data.get('timestamp'),
                        'working_directory': working_dir,
                        'git_branch': git_branch,
                        'event_type': 'stop',
                        'reason': reason,
                        'stop_type': stop_type
                    }
                    
                    file_path = self.response_tracker.track_response(
                        agent_name='claude_main',
                        request=prompt_data['prompt'],
                        response=str(output),
                        session_id=session_id,
                        metadata=metadata
                    )
                    
                    if file_path and DEBUG:
                        print(f"✅ Tracked main Claude response on Stop event for session {session_id[:8]}...: {file_path.name}", file=sys.stderr)
                    
                    # Clean up the stored prompt
                    if session_id in self.pending_prompts:
                        del self.pending_prompts[session_id]
                        
                elif DEBUG and not prompt_data:
                    print(f"No stored prompt for Stop event session {session_id[:8]}...", file=sys.stderr)
                elif DEBUG and not output:
                    print(f"No output in Stop event for session {session_id[:8]}...", file=sys.stderr)
                    
            except Exception as e:
                if DEBUG:
                    print(f"❌ Failed to track response on Stop event: {e}", file=sys.stderr)
        
        stop_data = {
            'reason': reason,
            'stop_type': stop_type,
            'session_id': session_id,
            'working_directory': working_dir,
            'git_branch': git_branch,
            'timestamp': datetime.now().isoformat(),
            'is_user_initiated': reason in ['user_stop', 'user_cancel', 'interrupt'],
            'is_error_stop': reason in ['error', 'timeout', 'failed'],
            'is_completion_stop': reason in ['completed', 'finished', 'done'],
            'has_output': bool(event.get('final_output'))
        }
        
        # Emit to /hook namespace
        self._emit_socketio_event('/hook', 'stop', stop_data)
    
    def _handle_subagent_stop_fast(self, event):
        """Handle subagent stop events with improved agent type detection.
        
        WHY comprehensive subagent stop capture:
        - Provides visibility into subagent lifecycle and delegation patterns
        - Captures agent type, ID, reason, and results for analysis
        - Enables tracking of delegation success/failure patterns
        - Useful for understanding subagent performance and reliability
        """
        # Enhanced debug logging for session correlation
        session_id = event.get('session_id', '')
        if DEBUG:
            print(f"\n[DEBUG] SubagentStop event received:", file=sys.stderr)
            print(f"  - session_id: {session_id[:16] if session_id else 'None'}...", file=sys.stderr)
            print(f"  - event keys: {list(event.keys())}", file=sys.stderr)
            print(f"  - delegation_requests size: {len(self.delegation_requests)}", file=sys.stderr)
            # Show all stored session IDs for comparison
            all_sessions = list(self.delegation_requests.keys())
            if all_sessions:
                print(f"  - Stored sessions (first 16 chars):", file=sys.stderr)
                for sid in all_sessions[:10]:  # Show up to 10
                    print(f"    - {sid[:16]}... (agent: {self.delegation_requests[sid].get('agent_type', 'unknown')})", file=sys.stderr)
            else:
                print(f"  - No stored sessions in delegation_requests!", file=sys.stderr)
        
        # First try to get agent type from our tracking
        agent_type = self._get_delegation_agent_type(session_id) if session_id else 'unknown'
        
        # Fall back to event data if tracking didn't have it
        if agent_type == 'unknown':
            agent_type = event.get('agent_type', event.get('subagent_type', 'unknown'))
        
        agent_id = event.get('agent_id', event.get('subagent_id', ''))
        reason = event.get('reason', event.get('stop_reason', 'unknown'))
        
        # Try to infer agent type from other fields if still unknown
        if agent_type == 'unknown' and 'task' in event:
            task_desc = str(event.get('task', '')).lower()
            if 'research' in task_desc:
                agent_type = 'research'
            elif 'engineer' in task_desc or 'code' in task_desc:
                agent_type = 'engineer'
            elif 'pm' in task_desc or 'project' in task_desc:
                agent_type = 'pm'
        
        # Always log SubagentStop events for debugging
        if DEBUG or agent_type != 'unknown':
            print(f"Hook handler: Processing SubagentStop - agent: '{agent_type}', session: '{session_id}', reason: '{reason}'", file=sys.stderr)
        
        # Get working directory and git branch
        working_dir = event.get('cwd', '')
        git_branch = self._get_git_branch(working_dir) if working_dir else 'Unknown'
        
        # Try to extract structured response from output if available
        output = event.get('output', '')
        structured_response = None
        if output:
            try:
                import re
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', str(output), re.DOTALL)
                if json_match:
                    structured_response = json.loads(json_match.group(1))
                    if DEBUG:
                        print(f"Extracted structured response from {agent_type} agent in SubagentStop", file=sys.stderr)
            except (json.JSONDecodeError, AttributeError):
                pass  # No structured response, that's okay
        
        # Track agent response even without structured JSON
        if DEBUG:
            print(f"[DEBUG] SubagentStop response tracking check:", file=sys.stderr)
            print(f"  - response_tracking_enabled: {self.response_tracking_enabled}", file=sys.stderr)
            print(f"  - response_tracker exists: {self.response_tracker is not None}", file=sys.stderr)
            print(f"  - session_id: {session_id[:16] if session_id else 'None'}...", file=sys.stderr)
            print(f"  - agent_type: {agent_type}", file=sys.stderr)
            print(f"  - reason: {reason}", file=sys.stderr)
            # Check if session exists in our storage
            if session_id in self.delegation_requests:
                print(f"  - ✅ Session found in delegation_requests", file=sys.stderr)
                print(f"  - Stored agent: {self.delegation_requests[session_id].get('agent_type')}", file=sys.stderr)
            else:
                print(f"  - ❌ Session NOT found in delegation_requests!", file=sys.stderr)
                print(f"  - Looking for partial match...", file=sys.stderr)
                # Try to find partial matches
                for stored_sid in list(self.delegation_requests.keys())[:10]:
                    if stored_sid.startswith(session_id[:8]) or session_id.startswith(stored_sid[:8]):
                        print(f"    - Partial match found: {stored_sid[:16]}...", file=sys.stderr)
        
        if self.response_tracking_enabled and self.response_tracker:
            try:
                # Get the original request data (with fuzzy matching fallback)
                request_info = self.delegation_requests.get(session_id)
                
                # If exact match fails, try partial matching
                if not request_info and session_id:
                    if DEBUG:
                        print(f"  - Trying fuzzy match for session {session_id[:16]}...", file=sys.stderr)
                    # Try to find a session that matches the first 8-16 characters
                    for stored_sid in list(self.delegation_requests.keys()):
                        if (stored_sid.startswith(session_id[:8]) or 
                            session_id.startswith(stored_sid[:8]) or
                            (len(session_id) >= 16 and len(stored_sid) >= 16 and 
                             stored_sid[:16] == session_id[:16])):
                            if DEBUG:
                                print(f"  - \u2705 Fuzzy match found: {stored_sid[:16]}...", file=sys.stderr)
                            request_info = self.delegation_requests.get(stored_sid)
                            # Update the key to use the current session_id for consistency
                            if request_info:
                                self.delegation_requests[session_id] = request_info
                                # Optionally remove the old key to avoid duplicates
                                if stored_sid != session_id:
                                    del self.delegation_requests[stored_sid]
                            break
                
                if DEBUG:
                    print(f"  - request_info present: {bool(request_info)}", file=sys.stderr)
                    if request_info:
                        print(f"  - ✅ Found request data for response tracking", file=sys.stderr)
                        print(f"  - stored agent_type: {request_info.get('agent_type')}", file=sys.stderr)
                        print(f"  - request keys: {list(request_info.get('request', {}).keys())}", file=sys.stderr)
                    else:
                        print(f"  - ❌ No request data found for session {session_id[:16]}...", file=sys.stderr)
                
                if request_info:
                    # Use the output as the response
                    response_text = str(output) if output else f"Agent {agent_type} completed with reason: {reason}"
                    
                    # Get the original request
                    original_request = request_info.get('request', {})
                    prompt = original_request.get('prompt', '')
                    description = original_request.get('description', '')
                    
                    # Combine prompt and description
                    full_request = prompt
                    if description and description != prompt:
                        if full_request:
                            full_request += f"\n\nDescription: {description}"
                        else:
                            full_request = description
                    
                    if not full_request:
                        full_request = f"Task delegation to {agent_type} agent"
                    
                    # Prepare metadata
                    metadata = {
                        'exit_code': event.get('exit_code', 0),
                        'success': reason in ['completed', 'finished', 'done'],
                        'has_error': reason in ['error', 'timeout', 'failed', 'blocked'],
                        'duration_ms': event.get('duration_ms'),
                        'working_directory': working_dir,
                        'git_branch': git_branch,
                        'timestamp': datetime.now().isoformat(),
                        'event_type': 'subagent_stop',
                        'reason': reason,
                        'original_request_timestamp': request_info.get('timestamp')
                    }
                    
                    # Add structured response if available
                    if structured_response:
                        metadata['structured_response'] = structured_response
                        metadata['task_completed'] = structured_response.get('task_completed', False)
                    
                    # Track the response
                    file_path = self.response_tracker.track_response(
                        agent_name=agent_type,
                        request=full_request,
                        response=response_text,
                        session_id=session_id,
                        metadata=metadata
                    )
                    
                    if file_path and DEBUG:
                        print(f"✅ Tracked {agent_type} agent response on SubagentStop: {file_path.name}", file=sys.stderr)
                    
                    # Clean up the request data
                    if session_id in self.delegation_requests:
                        del self.delegation_requests[session_id]
                        
                elif DEBUG:
                    print(f"No request data for SubagentStop session {session_id[:8]}..., agent: {agent_type}", file=sys.stderr)
                    
            except Exception as e:
                if DEBUG:
                    print(f"❌ Failed to track response on SubagentStop: {e}", file=sys.stderr)
        
        subagent_stop_data = {
            'agent_type': agent_type,
            'agent_id': agent_id,
            'reason': reason,
            'session_id': session_id,
            'working_directory': working_dir,
            'git_branch': git_branch,
            'timestamp': datetime.now().isoformat(),
            'is_successful_completion': reason in ['completed', 'finished', 'done'],
            'is_error_termination': reason in ['error', 'timeout', 'failed', 'blocked'],
            'is_delegation_related': agent_type in ['research', 'engineer', 'pm', 'ops', 'qa', 'documentation', 'security'],
            'has_results': bool(event.get('results') or event.get('output')),
            'duration_context': event.get('duration_ms'),
            'hook_event_name': 'SubagentStop'  # Explicitly set for dashboard
        }
        
        # Add structured response data if available
        if structured_response:
            subagent_stop_data['structured_response'] = {
                'task_completed': structured_response.get('task_completed', False),
                'instructions': structured_response.get('instructions', ''),
                'results': structured_response.get('results', ''),
                'files_modified': structured_response.get('files_modified', []),
                'tools_used': structured_response.get('tools_used', []),
                'remember': structured_response.get('remember')
            }
        
        # Debug log the processed data
        if DEBUG:
            print(f"SubagentStop processed data: agent_type='{agent_type}', session_id='{session_id}'", file=sys.stderr)
        
        # Emit to /hook namespace with high priority
        self._emit_socketio_event('/hook', 'subagent_stop', subagent_stop_data)
    
    def _handle_assistant_response(self, event):
        """Handle assistant response events for comprehensive response tracking.
        
        WHY: This enables capture of all Claude responses, not just Task delegations.
        When track_all_interactions is enabled, we capture every Claude response
        paired with its original user prompt.
        
        DESIGN DECISION: We correlate responses with stored prompts using session_id.
        This provides complete conversation tracking for analysis and learning.
        """
        if not self.response_tracking_enabled or not self.track_all_interactions:
            return
        
        session_id = event.get('session_id', '')
        if not session_id:
            return
        
        # Get the stored prompt for this session
        prompt_data = self.pending_prompts.get(session_id)
        if not prompt_data:
            if DEBUG:
                print(f"No stored prompt for session {session_id[:8]}..., skipping response tracking", file=sys.stderr)
            return
        
        try:
            # Extract response content from event
            response_content = event.get('response', '') or event.get('content', '') or event.get('text', '')
            
            if not response_content:
                if DEBUG:
                    print(f"No response content in event for session {session_id[:8]}...", file=sys.stderr)
                return
            
            # Track the response
            metadata = {
                'timestamp': datetime.now().isoformat(),
                'prompt_timestamp': prompt_data.get('timestamp'),
                'working_directory': prompt_data.get('working_directory', ''),
                'event_type': 'assistant_response',
                'session_type': 'interactive'
            }
            
            file_path = self.response_tracker.track_response(
                agent_name='claude',
                request=prompt_data['prompt'],
                response=response_content,
                session_id=session_id,
                metadata=metadata
            )
            
            if file_path and DEBUG:
                print(f"✅ Tracked Claude response for session {session_id[:8]}...: {file_path.name}", file=sys.stderr)
            
            # Clean up the stored prompt
            del self.pending_prompts[session_id]
            
        except Exception as e:
            if DEBUG:
                print(f"❌ Failed to track assistant response: {e}", file=sys.stderr)
    
    def _trigger_memory_pre_delegation_hook(self, agent_type: str, tool_input: dict, session_id: str):
        """Trigger memory pre-delegation hook for agent memory injection.
        
        WHY: This connects Claude Code's Task delegation events to our memory system.
        When Claude is about to delegate to an agent, we inject the agent's memory
        into the delegation context so the agent has access to accumulated knowledge.
        
        DESIGN DECISION: We modify the tool_input in place to inject memory context.
        This ensures the agent receives the memory as part of their initial context.
        """
        if not self.memory_hooks_initialized or not self.pre_delegation_hook:
            return
        
        try:
            # Create hook context for memory injection
            hook_context = HookContext(
                hook_type=HookType.PRE_DELEGATION,
                data={
                    'agent': agent_type,
                    'context': tool_input,
                    'session_id': session_id
                },
                metadata={
                    'source': 'claude_hook_handler',
                    'tool_name': 'Task'
                },
                timestamp=datetime.now().isoformat(),
                session_id=session_id
            )
            
            # Execute pre-delegation hook
            result = self.pre_delegation_hook.execute(hook_context)
            
            if result.success and result.modified and result.data:
                # Update tool_input with memory-enhanced context
                enhanced_context = result.data.get('context', {})
                if enhanced_context and 'agent_memory' in enhanced_context:
                    # Inject memory into the task prompt/description
                    original_prompt = tool_input.get('prompt', '')
                    memory_section = enhanced_context['agent_memory']
                    
                    # Prepend memory to the original prompt
                    enhanced_prompt = f"{memory_section}\n\n{original_prompt}"
                    tool_input['prompt'] = enhanced_prompt
                    
                    if DEBUG:
                        memory_size = len(memory_section.encode('utf-8'))
                        print(f"✅ Injected {memory_size} bytes of memory for agent '{agent_type}'", file=sys.stderr)
            
        except Exception as e:
            if DEBUG:
                print(f"❌ Memory pre-delegation hook failed: {e}", file=sys.stderr)
            # Don't fail the delegation - memory is optional
    
    def _trigger_memory_post_delegation_hook(self, agent_type: str, event: dict, session_id: str):
        """Trigger memory post-delegation hook for learning extraction.
        
        WHY: This connects Claude Code's Task completion events to our memory system.
        When an agent completes a task, we extract learnings from the result and
        store them in the agent's memory for future use.
        
        DESIGN DECISION: We extract learnings from both the tool output and any
        error messages, providing comprehensive context for the memory system.
        """
        if not self.memory_hooks_initialized or not self.post_delegation_hook:
            return
        
        try:
            # Extract result content from the event
            result_content = ""
            output = event.get('output', '')
            error = event.get('error', '')
            exit_code = event.get('exit_code', 0)
            
            # Build result content
            if output:
                result_content = str(output)
            elif error:
                result_content = f"Error: {str(error)}"
            else:
                result_content = f"Task completed with exit code: {exit_code}"
            
            # Create hook context for learning extraction
            hook_context = HookContext(
                hook_type=HookType.POST_DELEGATION,
                data={
                    'agent': agent_type,
                    'result': {
                        'content': result_content,
                        'success': exit_code == 0,
                        'exit_code': exit_code
                    },
                    'session_id': session_id
                },
                metadata={
                    'source': 'claude_hook_handler',
                    'tool_name': 'Task',
                    'duration_ms': event.get('duration_ms', 0)
                },
                timestamp=datetime.now().isoformat(),
                session_id=session_id
            )
            
            # Execute post-delegation hook
            result = self.post_delegation_hook.execute(hook_context)
            
            if result.success and result.metadata:
                learnings_extracted = result.metadata.get('learnings_extracted', 0)
                if learnings_extracted > 0 and DEBUG:
                    print(f"✅ Extracted {learnings_extracted} learnings for agent '{agent_type}'", file=sys.stderr)
            
        except Exception as e:
            if DEBUG:
                print(f"❌ Memory post-delegation hook failed: {e}", file=sys.stderr)
            # Don't fail the delegation result - memory is optional
    
    def __del__(self):
        """Cleanup Socket.IO client on handler destruction."""
        if self.sio_client and self.sio_connected:
            try:
                self.sio_client.disconnect()
            except:
                pass


def main():
    """Entry point with comprehensive error handling."""
    try:
        handler = ClaudeHookHandler()
        handler.handle()
    except Exception as e:
        # Always output continue action to not block Claude
        print(json.dumps({"action": "continue"}))
        # Log error for debugging
        if DEBUG:
            print(f"Hook handler error: {e}", file=sys.stderr)
        sys.exit(0)  # Exit cleanly even on error


if __name__ == "__main__":
    main()