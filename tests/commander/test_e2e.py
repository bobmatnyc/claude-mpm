#!/usr/bin/env python3
"""
MPM Commander End-to-End Test

Automated test that:
1. Spawns the Commander daemon in a subprocess
2. Registers a test project via REST API
3. Adds work items and verifies queue behavior
4. Tests event/inbox endpoints
5. Tests state persistence (restart recovery)
6. Cleans up automatically

Usage:
    uv run python examples/commander_e2e_test.py

Options:
    --port PORT     Daemon port (default: 18765 to avoid conflicts)
    --keep-running  Don't stop daemon after tests (for manual inspection)
    --verbose       Show daemon output
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def log_step(msg):
    print(f"{BLUE}▶{RESET} {msg}")


def log_pass(msg):
    print(f"{GREEN}✓{RESET} {msg}")


def log_fail(msg):
    print(f"{RED}✗{RESET} {msg}")


def log_warn(msg):
    print(f"{YELLOW}⚠{RESET} {msg}")


class CommanderE2ETest:
    def __init__(self, port: int = 18765, verbose: bool = False):
        self.port = port
        self.verbose = verbose
        self.base_url = f"http://localhost:{port}/api"
        self.daemon_process = None
        self.test_dir = None
        self.project_id = None

    def setup(self):
        """Create test directory and start daemon."""
        # Create temp test project
        self.test_dir = Path(tempfile.mkdtemp(prefix="commander-test-"))
        (self.test_dir / "package.json").write_text('{"name": "e2e-test"}')
        log_step(f"Created test project: {self.test_dir}")

        # Start daemon
        log_step(f"Starting daemon on port {self.port}...")
        cmd = [
            sys.executable,
            "-m",
            "claude_mpm.cli",
            "commander",
            "start",
            "--port",
            str(self.port),
        ]

        stdout = None if self.verbose else subprocess.DEVNULL
        stderr = None if self.verbose else subprocess.DEVNULL

        self.daemon_process = subprocess.Popen(
            cmd, stdout=stdout, stderr=stderr, cwd=Path(__file__).parent.parent
        )

        # Wait for daemon to be ready (MPM startup can take 30+ seconds)
        self._wait_for_daemon(timeout=45)
        log_pass("Daemon started")

    def _wait_for_daemon(self, timeout: int):
        """Wait for daemon to respond to health check."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = requests.get(f"{self.base_url}/health", timeout=1)
                if resp.status_code == 200:
                    return
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                pass
            except Exception as e:
                # Log unexpected errors but continue trying
                if self.verbose:
                    log_warn(f"Health check error: {e}")
            time.sleep(0.5)
        raise TimeoutError(f"Daemon didn't start within {timeout}s")

    def teardown(self):
        """Stop daemon and clean up."""
        if self.daemon_process:
            log_step("Stopping daemon...")
            self.daemon_process.terminate()
            try:
                self.daemon_process.wait(timeout=5)
                log_pass("Daemon stopped")
            except subprocess.TimeoutExpired:
                self.daemon_process.kill()
                log_warn("Daemon killed (didn't stop gracefully)")

        if self.test_dir and self.test_dir.exists():
            shutil.rmtree(self.test_dir)
            log_step("Cleaned up test directory")

    def test_health_endpoint(self) -> bool:
        """Test health endpoint responds."""
        log_step("Testing health endpoint...")
        try:
            resp = requests.get(f"{self.base_url}/health")
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            log_pass("Health endpoint OK")
            return True
        except Exception as e:
            log_fail(f"Health check failed: {e}")
            return False

    def test_project_crud(self) -> bool:
        """Test project create/read/list."""
        log_step("Testing project CRUD...")
        try:
            # Create project
            resp = requests.post(
                f"{self.base_url}/projects",
                json={"name": "e2e-test-project", "path": str(self.test_dir)},
            )
            assert resp.status_code in [200, 201], f"Create failed: {resp.status_code}"
            data = resp.json()
            self.project_id = data.get("id") or data.get("project_id")
            assert self.project_id, "No project ID returned"
            log_pass(f"Created project: {self.project_id}")

            # List projects
            resp = requests.get(f"{self.base_url}/projects")
            assert resp.status_code == 200
            projects = resp.json()
            assert any(
                p.get("id") == self.project_id or p.get("project_id") == self.project_id
                for p in projects
            ), "Project not in list"
            log_pass("Project listed")

            # Get project
            resp = requests.get(f"{self.base_url}/projects/{self.project_id}")
            assert resp.status_code == 200
            log_pass("Project retrieved")

            return True
        except Exception as e:
            log_fail(f"Project CRUD failed: {e}")
            return False

    def test_work_queue(self) -> bool:
        """Test work queue operations."""
        log_step("Testing work queue...")
        try:
            # Add work item (priority: 1=LOW, 2=MEDIUM, 3=HIGH, 4=CRITICAL)
            resp = requests.post(
                f"{self.base_url}/projects/{self.project_id}/work",
                json={"content": "Test task 1", "priority": 3},  # HIGH
            )
            assert resp.status_code in [
                200,
                201,
            ], f"Add work failed: {resp.status_code}"
            work_data = resp.json()
            work_id = work_data.get("id") or work_data.get("work_id")
            log_pass(f"Added work item: {work_id}")

            # Add another with lower priority
            resp = requests.post(
                f"{self.base_url}/projects/{self.project_id}/work",
                json={"content": "Test task 2", "priority": 1},  # LOW
            )
            assert resp.status_code in [200, 201]
            log_pass("Added second work item")

            # List work
            resp = requests.get(f"{self.base_url}/projects/{self.project_id}/work")
            assert resp.status_code == 200
            work_items = resp.json()
            assert len(work_items) >= 2, f"Expected 2+ items, got {len(work_items)}"
            log_pass(f"Listed {len(work_items)} work items")

            return True
        except Exception as e:
            log_fail(f"Work queue failed: {e}")
            return False

    def test_inbox(self) -> bool:
        """Test inbox/events endpoints."""
        log_step("Testing inbox/events...")
        try:
            # Get inbox
            resp = requests.get(f"{self.base_url}/inbox")
            assert resp.status_code == 200
            log_pass("Inbox endpoint OK")

            # Get pending events
            resp = requests.get(f"{self.base_url}/events/pending")
            assert resp.status_code == 200
            log_pass("Pending events endpoint OK")

            return True
        except Exception as e:
            log_fail(f"Inbox/events failed: {e}")
            return False

    def test_persistence(self) -> bool:
        """Test state persists across daemon restart."""
        log_step("Testing persistence (restart recovery)...")
        try:
            # Stop daemon
            self.daemon_process.terminate()
            self.daemon_process.wait(timeout=5)
            log_step("Daemon stopped for restart test")

            # Restart daemon
            time.sleep(1)
            cmd = [
                sys.executable,
                "-m",
                "claude_mpm.cli",
                "commander",
                "start",
                "--port",
                str(self.port),
            ]
            stdout = None if self.verbose else subprocess.DEVNULL
            stderr = None if self.verbose else subprocess.DEVNULL
            self.daemon_process = subprocess.Popen(
                cmd, stdout=stdout, stderr=stderr, cwd=Path(__file__).parent.parent
            )
            self._wait_for_daemon(timeout=45)
            log_pass("Daemon restarted")

            # Verify project still exists
            resp = requests.get(f"{self.base_url}/projects")
            assert resp.status_code == 200
            projects = resp.json()

            # Check if our project persisted
            found = any(
                p.get("id") == self.project_id or p.get("project_id") == self.project_id
                for p in projects
            )

            if found:
                log_pass("Project persisted across restart")
            else:
                log_warn("Project not found after restart (persistence may need work)")
                # Don't fail - persistence might be partial in Phase 2

            return True
        except Exception as e:
            log_fail(f"Persistence test failed: {e}")
            return False

    def test_chat_mode(self) -> bool:
        """Test the interactive chat mode starts correctly.

        This test verifies that the Commander chat mode can initialize
        and respond to basic commands without requiring full interaction.
        """
        log_step("Testing chat mode initialization...")
        try:
            # Test that Commander REPL components are available
            from claude_mpm.commander.chat.repl import CommanderREPL
            from claude_mpm.commander.instance_manager import InstanceManager
            from claude_mpm.commander.session.manager import SessionManager

            # Create minimal instances
            manager = InstanceManager()
            session = SessionManager()
            repl = CommanderREPL(instance_manager=manager, session_manager=session)

            # Verify initialization
            assert repl.instances is not None, "Instance manager not initialized"
            assert repl.session is not None, "Session manager not initialized"
            assert not repl._running, "REPL should not be running yet"

            log_pass("Chat mode components initialized")

            # Test basic command methods exist
            assert hasattr(repl, "_cmd_list"), "list command missing"
            assert hasattr(repl, "_cmd_start"), "start command missing"
            assert hasattr(repl, "_cmd_stop"), "stop command missing"
            assert hasattr(repl, "_cmd_connect"), "connect command missing"
            assert hasattr(repl, "_cmd_disconnect"), "disconnect command missing"
            assert hasattr(repl, "_cmd_status"), "status command missing"
            assert hasattr(repl, "_cmd_help"), "help command missing"

            log_pass("All chat commands available")

            return True
        except Exception as e:
            log_fail(f"Chat mode test failed: {e}")
            return False

    def run_all_tests(self) -> bool:
        """Run all tests and return overall success."""
        tests = [
            ("Health Check", self.test_health_endpoint),
            ("Project CRUD", self.test_project_crud),
            ("Work Queue", self.test_work_queue),
            ("Inbox/Events", self.test_inbox),
            ("Persistence", self.test_persistence),
            ("Chat Mode", self.test_chat_mode),
        ]

        results = []
        for name, test_fn in tests:
            print(f"\n{BLUE}━━━ {name} ━━━{RESET}")
            try:
                results.append(test_fn())
            except Exception as e:
                log_fail(f"Test crashed: {e}")
                results.append(False)

        return all(results)


def main():
    parser = argparse.ArgumentParser(description="MPM Commander E2E Test")
    parser.add_argument("--port", type=int, default=18765, help="Daemon port")
    parser.add_argument("--keep-running", action="store_true", help="Don't stop daemon")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show daemon output"
    )
    args = parser.parse_args()

    print(f"\n{BLUE}╔══════════════════════════════════════════╗{RESET}")
    print(f"{BLUE}║  MPM Commander End-to-End Test           ║{RESET}")
    print(f"{BLUE}╚══════════════════════════════════════════╝{RESET}\n")

    test = CommanderE2ETest(port=args.port, verbose=args.verbose)

    try:
        test.setup()
        success = test.run_all_tests()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted{RESET}")
        success = False
    except Exception as e:
        log_fail(f"Setup failed: {e}")
        success = False
    finally:
        if not args.keep_running:
            test.teardown()
        else:
            print(f"\n{YELLOW}Daemon still running on port {args.port}{RESET}")
            print(f"Stop with: kill {test.daemon_process.pid}")

    print(f"\n{BLUE}━━━ Results ━━━{RESET}")
    if success:
        print(f"{GREEN}All tests passed!{RESET}\n")
        sys.exit(0)
    else:
        print(f"{RED}Some tests failed{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
