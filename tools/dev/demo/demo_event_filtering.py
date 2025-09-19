#!/usr/bin/env python3
"""
Interactive demo to showcase event filtering in the Claude MPM dashboard.
This script sends a continuous stream of realistic events to demonstrate
that each dashboard view (agents, tools, files) correctly filters and
displays only relevant events.
"""

import json
import random
import time
from datetime import datetime

import socketio


class EventFilteringDemo:
    def __init__(self):
        self.sio = socketio.Client()
        self.running = True

        # Realistic event templates
        self.agent_templates = [
            {
                "type": "agent_start",
                "data": {
                    "agent_id": "pm-{id}",
                    "agent_name": "Project Manager",
                    "agent_type": "PM",
                    "status": "active",
                    "message": "Analyzing project requirements"
                }
            },
            {
                "hook_event_name": "SubagentStart",
                "data": {
                    "agent": "Engineer-{id}",
                    "task": "Implementing feature #{task_id}"
                }
            },
            {
                "type": "agent_inference",
                "data": {
                    "agent_name": "QA Agent {id}",
                    "status": "running",
                    "message": "Running test suite {suite}"
                }
            },
            {
                "type": "agent_complete",
                "data": {
                    "agent_id": "devops-{id}",
                    "agent_name": "DevOps Agent",
                    "status": "complete",
                    "message": "Deployment successful"
                }
            }
        ]

        self.tool_templates = [
            {
                "type": "tool_start",
                "data": {
                    "tool": "Bash",
                    "command": "{command}",
                    "description": "Executing: {command}"
                }
            },
            {
                "hook_event_name": "ToolStart",
                "data": {
                    "tool_name": "Read",
                    "file_path": "/src/{file}"
                }
            },
            {
                "type": "tool_execution",
                "data": {
                    "tool": "WebFetch",
                    "url": "https://api.{service}.com/v1/data",
                    "status": "running"
                }
            },
            {
                "type": "tool_complete",
                "data": {
                    "tool": "Grep",
                    "pattern": "{pattern}",
                    "status": "completed",
                    "matches": random.randint(1, 50)
                }
            },
            {
                "type": "bash_command",
                "data": {
                    "command": "git {git_cmd}",
                    "tool": "Bash",
                    "status": "completed"
                }
            }
        ]

        self.file_templates = [
            {
                "type": "file_read",
                "data": {
                    "file_path": "/src/{module}/{file}.{ext}",
                    "size": random.randint(100, 10000)
                }
            },
            {
                "hook_event_name": "FileWrite",
                "data": {
                    "path": "/config/{config}.json",
                    "operation": "write",
                    "size": random.randint(50, 5000)
                }
            },
            {
                "type": "file_edit",
                "data": {
                    "file": "/src/components/{component}.jsx",
                    "operation": "edit",
                    "lines_changed": random.randint(1, 100)
                }
            },
            {
                "type": "file_delete",
                "data": {
                    "file_path": "/tmp/{temp_file}",
                    "operation": "delete"
                }
            }
        ]

        # Random data for templates
        self.commands = ["npm test", "npm build", "npm install", "yarn test", "make build"]
        self.git_commands = ["status", "diff", "log --oneline", "branch -a", "pull"]
        self.patterns = ["TODO", "FIXME", "import.*from", "class.*extends", "function.*\\("]
        self.services = ["github", "npm", "pypi", "docker", "kubernetes"]
        self.modules = ["components", "utils", "services", "hooks", "stores"]
        self.files = ["index", "app", "main", "utils", "helpers", "config"]
        self.extensions = ["js", "jsx", "ts", "tsx", "py", "json", "md"]
        self.components = ["Button", "Header", "Footer", "Modal", "Form", "List"]
        self.configs = ["settings", "database", "webpack", "babel", "eslint"]
        self.temp_files = ["cache_123", "build_456", "tmp_789", "test_abc", "log_xyz"]

    def connect(self):
        """Connect to the Socket.IO server"""
        try:
            print("🔌 Connecting to monitor server...")
            self.sio.connect('http://localhost:8765', transports=['polling', 'websocket'])
            time.sleep(1)
            if self.sio.connected:
                print("✅ Connected successfully!")
                return True
            print("❌ Connection failed")
            return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False

    def format_event(self, template, event_id):
        """Format a template with random data"""
        event = json.loads(json.dumps(template))  # Deep copy

        # Replace placeholders in the event
        if "data" in event:
            for key, value in event["data"].items():
                if isinstance(value, str):
                    event["data"][key] = value.format(
                        id=event_id,
                        task_id=random.randint(100, 999),
                        suite=random.choice(["unit", "integration", "e2e", "smoke"]),
                        command=random.choice(self.commands),
                        git_cmd=random.choice(self.git_commands),
                        pattern=random.choice(self.patterns),
                        service=random.choice(self.services),
                        module=random.choice(self.modules),
                        file=random.choice(self.files),
                        ext=random.choice(self.extensions),
                        component=random.choice(self.components),
                        config=random.choice(self.configs),
                        temp_file=random.choice(self.temp_files)
                    )

        return event

    def send_event_batch(self):
        """Send a batch of mixed events"""
        event_id = int(time.time() * 1000) % 10000

        # Send 1-2 agent events
        for _ in range(random.randint(1, 2)):
            template = random.choice(self.agent_templates)
            event = self.format_event(template, event_id)
            self.sio.emit('claude_event', event)
            event_type = event.get('type') or event.get('hook_event_name')
            print(f"  📤 Agent: {event_type}")
            time.sleep(0.1)

        # Send 2-3 tool events
        for _ in range(random.randint(2, 3)):
            template = random.choice(self.tool_templates)
            event = self.format_event(template, event_id + 1)
            self.sio.emit('claude_event', event)
            event_type = event.get('type') or event.get('hook_event_name')
            print(f"  🔧 Tool: {event_type}")
            time.sleep(0.1)

        # Send 1-2 file events
        for _ in range(random.randint(1, 2)):
            template = random.choice(self.file_templates)
            event = self.format_event(template, event_id + 2)
            self.sio.emit('claude_event', event)
            event_type = event.get('type') or event.get('hook_event_name')
            print(f"  📁 File: {event_type}")
            time.sleep(0.1)

    def run_demo(self, duration=60):
        """Run the demo for specified duration (seconds)"""
        print("\n" + "=" * 60)
        print("🎭 EVENT FILTERING DEMO")
        print("=" * 60)

        if not self.connect():
            print("\n⚠️  Make sure the monitor server is running:")
            print('  python -c "from claude_mpm.services.monitor import UnifiedMonitorDaemon; d = UnifiedMonitorDaemon(); d.start()"')
            return

        print("\n📺 OPEN THESE URLS IN YOUR BROWSER:")
        print("  1. http://localhost:8765/static/agents.html - Agent events only")
        print("  2. http://localhost:8765/static/tools.html  - Tool events only")
        print("  3. http://localhost:8765/static/files.html  - File events only")
        print("\n💡 TIP: Click 'Toggle Debug' in each view to see filtering stats!")
        print("\n" + "-" * 60)

        start_time = time.time()
        batch_count = 0

        try:
            print(f"\n🚀 Starting {duration}-second demo...\n")

            while time.time() - start_time < duration:
                batch_count += 1
                print(f"📦 Batch {batch_count} @ {datetime.now().strftime('%H:%M:%S')}")
                self.send_event_batch()

                # Wait between batches
                time.sleep(random.uniform(2, 4))

            print("\n" + "=" * 60)
            print("✅ DEMO COMPLETE!")
            print("=" * 60)
            print("\n📊 RESULTS:")
            print(f"  • Sent {batch_count} batches of events")
            print(f"  • ~{batch_count * 5} total events sent")
            print("\n🔍 CHECK THE DASHBOARD TABS:")
            print("  • Agents tab should show ONLY agent-related events")
            print("  • Tools tab should show ONLY tool-related events")
            print("  • Files tab should show ONLY file-related events")
            print("\n✨ The EventFilterService is working correctly!")

        except KeyboardInterrupt:
            print("\n\n⏹️  Demo stopped by user")
        finally:
            if self.sio.connected:
                self.sio.disconnect()
                print("🔌 Disconnected from server")

def main():
    import sys

    # Parse duration from command line (default 60 seconds)
    duration = 60
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            print(f"Invalid duration: {sys.argv[1]}, using default 60 seconds")

    demo = EventFilteringDemo()
    demo.run_demo(duration)

if __name__ == "__main__":
    main()
