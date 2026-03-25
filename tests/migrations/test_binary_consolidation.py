"""
Tests for binary consolidation migration.

Tests the migration of old .mcp.json binary/module invocations
to the consolidated 'claude-mpm mcp serve <name>' format.
"""

import json
from pathlib import Path

import pytest


class TestIsAlreadyMigrated:
    """Tests for _is_already_migrated detection."""

    def test_direct_claude_mpm_invocation(self):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            _is_already_migrated,
        )

        config = {
            "command": "claude-mpm",
            "args": ["mcp", "serve", "messaging"],
        }
        assert _is_already_migrated(config) is True

    def test_uv_wrapped_claude_mpm_invocation(self):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            _is_already_migrated,
        )

        config = {
            "command": "uv",
            "args": [
                "run",
                "--directory",
                "/some/path",
                "claude-mpm",
                "mcp",
                "serve",
                "slack-proxy",
            ],
        }
        assert _is_already_migrated(config) is True

    def test_old_module_invocation_not_migrated(self):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            _is_already_migrated,
        )

        config = {
            "command": "uv",
            "args": [
                "run",
                "--directory",
                "/some/path",
                "python",
                "-m",
                "claude_mpm.mcp.messaging_server",
            ],
        }
        assert _is_already_migrated(config) is False

    def test_old_binary_invocation_not_migrated(self):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            _is_already_migrated,
        )

        config = {"command": "mpm-session-server", "args": []}
        assert _is_already_migrated(config) is False

    def test_non_mpm_server_not_migrated(self):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            _is_already_migrated,
        )

        config = {"command": "kuzu-memory", "args": ["mcp"]}
        assert _is_already_migrated(config) is False


class TestFindModuleInArgs:
    """Tests for _find_module_in_args."""

    def test_finds_module_after_dash_m(self):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            _find_module_in_args,
        )

        args = [
            "run",
            "--directory",
            "/path",
            "python",
            "-m",
            "claude_mpm.mcp.messaging_server",
        ]
        assert _find_module_in_args(args) == "claude_mpm.mcp.messaging_server"

    def test_finds_slack_proxy_module(self):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            _find_module_in_args,
        )

        args = [
            "run",
            "python",
            "-m",
            "claude_mpm.mcp.slack_user_proxy_server",
        ]
        assert _find_module_in_args(args) == "claude_mpm.mcp.slack_user_proxy_server"

    def test_returns_none_for_non_mpm_module(self):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            _find_module_in_args,
        )

        args = ["run", "python", "-m", "some_other_module"]
        assert _find_module_in_args(args) is None

    def test_returns_none_for_empty_args(self):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            _find_module_in_args,
        )

        assert _find_module_in_args([]) is None


class TestMigrateModuleInvocation:
    """Tests for _migrate_module_invocation."""

    def test_uv_wrapped_python_module(self):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            _migrate_module_invocation,
        )

        config = {
            "command": "uv",
            "args": [
                "run",
                "--directory",
                "/Users/masa/Projects/claude-mpm",
                "python",
                "-m",
                "claude_mpm.mcp.messaging_server",
            ],
        }

        result = _migrate_module_invocation(config, "claude_mpm.mcp.messaging_server")

        assert result["command"] == "uv"
        assert result["args"] == [
            "run",
            "--directory",
            "/Users/masa/Projects/claude-mpm",
            "claude-mpm",
            "mcp",
            "serve",
            "messaging",
        ]

    def test_uv_wrapped_slack_proxy(self):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            _migrate_module_invocation,
        )

        config = {
            "command": "uv",
            "args": [
                "run",
                "--directory",
                "/some/path",
                "python",
                "-m",
                "claude_mpm.mcp.slack_user_proxy_server",
            ],
        }

        result = _migrate_module_invocation(
            config, "claude_mpm.mcp.slack_user_proxy_server"
        )

        assert result["args"] == [
            "run",
            "--directory",
            "/some/path",
            "claude-mpm",
            "mcp",
            "serve",
            "slack-proxy",
        ]

    def test_direct_python_module(self):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            _migrate_module_invocation,
        )

        config = {
            "command": "python",
            "args": ["-m", "claude_mpm.mcp.messaging_server"],
        }

        result = _migrate_module_invocation(config, "claude_mpm.mcp.messaging_server")

        assert result["command"] == "claude-mpm"
        assert result["args"] == ["mcp", "serve", "messaging"]

    def test_preserves_non_mcp_fields(self):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            _migrate_module_invocation,
        )

        config = {
            "type": "stdio",
            "command": "python",
            "args": ["-m", "claude_mpm.mcp.confluence_server"],
            "env": {"SOME_VAR": "value"},
        }

        result = _migrate_module_invocation(config, "claude_mpm.mcp.confluence_server")

        assert result["type"] == "stdio"
        assert result["env"] == {"SOME_VAR": "value"}
        assert result["command"] == "claude-mpm"
        assert result["args"] == ["mcp", "serve", "confluence"]


class TestMigrateBinaryInvocation:
    """Tests for _migrate_binary_invocation."""

    def test_direct_session_server(self):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            _migrate_binary_invocation,
        )

        config = {"command": "mpm-session-server", "args": []}

        result = _migrate_binary_invocation(config, "mpm-session-server")

        assert result["command"] == "claude-mpm"
        assert result["args"] == ["mcp", "serve", "session"]

    def test_direct_session_server_http(self):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            _migrate_binary_invocation,
        )

        config = {"command": "mpm-session-server-http", "args": []}

        result = _migrate_binary_invocation(config, "mpm-session-server-http")

        assert result["command"] == "claude-mpm"
        assert result["args"] == ["mcp", "serve", "session-http"]

    def test_direct_confluence_mcp(self):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            _migrate_binary_invocation,
        )

        config = {"command": "confluence-mcp", "args": []}

        result = _migrate_binary_invocation(config, "confluence-mcp")

        assert result["command"] == "claude-mpm"
        assert result["args"] == ["mcp", "serve", "confluence"]

    def test_preserves_existing_args(self):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            _migrate_binary_invocation,
        )

        config = {
            "command": "mpm-session-server",
            "args": ["--port", "8080"],
        }

        result = _migrate_binary_invocation(config, "mpm-session-server")

        assert result["command"] == "claude-mpm"
        assert result["args"] == [
            "mcp",
            "serve",
            "session",
            "--port",
            "8080",
        ]

    def test_uv_wrapped_binary(self):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            _migrate_binary_invocation,
        )

        config = {
            "command": "uv",
            "args": [
                "run",
                "--directory",
                "/path",
                "mpm-session-server",
            ],
        }

        result = _migrate_binary_invocation(config, "mpm-session-server")

        assert result["command"] == "uv"
        assert result["args"] == [
            "run",
            "--directory",
            "/path",
            "claude-mpm",
            "mcp",
            "serve",
            "session",
        ]


class TestMigrateMcpJson:
    """Integration tests for migrate_mcp_json."""

    @pytest.fixture
    def project_dir(self, tmp_path):
        """Create a temporary project directory."""
        return tmp_path

    def _write_mcp_json(self, project_dir: Path, data: dict) -> Path:
        """Helper to write .mcp.json."""
        mcp_json = project_dir / ".mcp.json"
        mcp_json.write_text(json.dumps(data, indent=2))
        return mcp_json

    def test_no_mcp_json(self, project_dir):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            migrate_mcp_json,
        )

        result = migrate_mcp_json(project_dir)
        assert result["migrated"] == []
        assert result["errors"] == []

    def test_empty_mcp_json(self, project_dir):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            migrate_mcp_json,
        )

        self._write_mcp_json(project_dir, {"mcpServers": {}})

        result = migrate_mcp_json(project_dir)
        assert result["migrated"] == []

    def test_malformed_json(self, project_dir):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            migrate_mcp_json,
        )

        mcp_json = project_dir / ".mcp.json"
        mcp_json.write_text("{invalid json")

        result = migrate_mcp_json(project_dir)
        assert len(result["errors"]) == 1
        assert "Malformed" in result["errors"][0]

    def test_migrates_module_invocation(self, project_dir):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            migrate_mcp_json,
        )

        data = {
            "mcpServers": {
                "mpm-messaging": {
                    "type": "stdio",
                    "command": "uv",
                    "args": [
                        "run",
                        "--directory",
                        "/path",
                        "python",
                        "-m",
                        "claude_mpm.mcp.messaging_server",
                    ],
                    "env": {},
                }
            }
        }
        self._write_mcp_json(project_dir, data)

        result = migrate_mcp_json(project_dir)

        assert len(result["migrated"]) == 1
        assert result["migrated"][0][0] == "mpm-messaging"

        # Verify file was updated
        updated = json.loads((project_dir / ".mcp.json").read_text())
        server = updated["mcpServers"]["mpm-messaging"]
        assert server["command"] == "uv"
        assert "claude-mpm" in server["args"]
        assert "mcp" in server["args"]
        assert "serve" in server["args"]
        assert "messaging" in server["args"]

    def test_migrates_binary_invocation(self, project_dir):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            migrate_mcp_json,
        )

        data = {
            "mcpServers": {
                "session": {
                    "command": "mpm-session-server",
                    "args": [],
                }
            }
        }
        self._write_mcp_json(project_dir, data)

        result = migrate_mcp_json(project_dir)

        assert len(result["migrated"]) == 1
        updated = json.loads((project_dir / ".mcp.json").read_text())
        server = updated["mcpServers"]["session"]
        assert server["command"] == "claude-mpm"
        assert server["args"] == ["mcp", "serve", "session"]

    def test_preserves_non_mpm_servers(self, project_dir):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            migrate_mcp_json,
        )

        data = {
            "mcpServers": {
                "kuzu-memory": {
                    "type": "stdio",
                    "command": "kuzu-memory",
                    "args": ["mcp"],
                    "env": {"KEY": "value"},
                },
                "session": {
                    "command": "mpm-session-server",
                    "args": [],
                },
            }
        }
        self._write_mcp_json(project_dir, data)

        result = migrate_mcp_json(project_dir)

        assert "kuzu-memory" in result["unchanged"]
        assert len(result["migrated"]) == 1

        # Verify kuzu-memory was not modified
        updated = json.loads((project_dir / ".mcp.json").read_text())
        kuzu = updated["mcpServers"]["kuzu-memory"]
        assert kuzu["command"] == "kuzu-memory"
        assert kuzu["args"] == ["mcp"]
        assert kuzu["env"] == {"KEY": "value"}

    def test_skips_already_migrated(self, project_dir):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            migrate_mcp_json,
        )

        data = {
            "mcpServers": {
                "messaging": {
                    "command": "uv",
                    "args": [
                        "run",
                        "--directory",
                        "/path",
                        "claude-mpm",
                        "mcp",
                        "serve",
                        "messaging",
                    ],
                }
            }
        }
        self._write_mcp_json(project_dir, data)

        result = migrate_mcp_json(project_dir)

        assert result["migrated"] == []
        assert "messaging" in result["skipped"]

    def test_creates_backup(self, project_dir):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            migrate_mcp_json,
        )

        original_data = {
            "mcpServers": {
                "session": {
                    "command": "mpm-session-server",
                    "args": [],
                }
            }
        }
        self._write_mcp_json(project_dir, original_data)

        result = migrate_mcp_json(project_dir)

        assert result["backup_path"] is not None
        backup = Path(result["backup_path"])
        assert backup.exists()

        # Verify backup contains original content
        backup_data = json.loads(backup.read_text())
        assert backup_data["mcpServers"]["session"]["command"] == "mpm-session-server"

    def test_dry_run_does_not_modify(self, project_dir):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            migrate_mcp_json,
        )

        original_data = {
            "mcpServers": {
                "session": {
                    "command": "mpm-session-server",
                    "args": [],
                }
            }
        }
        self._write_mcp_json(project_dir, original_data)

        result = migrate_mcp_json(project_dir, dry_run=True)

        assert len(result["migrated"]) == 1
        assert result["dry_run"] is True
        assert result["backup_path"] is None

        # Verify file was NOT modified
        current = json.loads((project_dir / ".mcp.json").read_text())
        assert current["mcpServers"]["session"]["command"] == "mpm-session-server"

    def test_idempotent(self, project_dir):
        """Running migration twice should have no additional effect."""
        from claude_mpm.migrations.migrate_binary_consolidation import (
            migrate_mcp_json,
        )

        data = {
            "mcpServers": {
                "session": {
                    "command": "mpm-session-server",
                    "args": [],
                }
            }
        }
        self._write_mcp_json(project_dir, data)

        # First run
        result1 = migrate_mcp_json(project_dir)
        assert len(result1["migrated"]) == 1

        # Second run
        result2 = migrate_mcp_json(project_dir)
        assert result2["migrated"] == []
        assert "session" in result2["skipped"]

    def test_migrates_multiple_servers(self, project_dir):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            migrate_mcp_json,
        )

        data = {
            "mcpServers": {
                "messaging": {
                    "command": "uv",
                    "args": [
                        "run",
                        "--directory",
                        "/path",
                        "python",
                        "-m",
                        "claude_mpm.mcp.messaging_server",
                    ],
                },
                "session": {
                    "command": "mpm-session-server",
                    "args": [],
                },
                "confluence": {
                    "command": "confluence-mcp",
                    "args": [],
                },
                "kuzu-memory": {
                    "command": "kuzu-memory",
                    "args": ["mcp"],
                },
            }
        }
        self._write_mcp_json(project_dir, data)

        result = migrate_mcp_json(project_dir)

        assert len(result["migrated"]) == 3
        assert "kuzu-memory" in result["unchanged"]

    def test_mixed_old_and_new_format(self, project_dir):
        """Some servers already migrated, some not."""
        from claude_mpm.migrations.migrate_binary_consolidation import (
            migrate_mcp_json,
        )

        data = {
            "mcpServers": {
                "messaging": {
                    "command": "uv",
                    "args": [
                        "run",
                        "--directory",
                        "/path",
                        "claude-mpm",
                        "mcp",
                        "serve",
                        "messaging",
                    ],
                },
                "session": {
                    "command": "mpm-session-server",
                    "args": [],
                },
            }
        }
        self._write_mcp_json(project_dir, data)

        result = migrate_mcp_json(project_dir)

        assert len(result["migrated"]) == 1
        assert result["migrated"][0][0] == "session"
        assert "messaging" in result["skipped"]


class TestCheckNeedsMigration:
    """Tests for check_needs_migration."""

    @pytest.fixture
    def project_dir(self, tmp_path):
        return tmp_path

    def test_no_mcp_json(self, project_dir):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            check_needs_migration,
        )

        assert check_needs_migration(project_dir) is False

    def test_all_migrated(self, project_dir):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            check_needs_migration,
        )

        data = {
            "mcpServers": {
                "messaging": {
                    "command": "claude-mpm",
                    "args": ["mcp", "serve", "messaging"],
                }
            }
        }
        (project_dir / ".mcp.json").write_text(json.dumps(data))

        assert check_needs_migration(project_dir) is False

    def test_module_needs_migration(self, project_dir):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            check_needs_migration,
        )

        data = {
            "mcpServers": {
                "messaging": {
                    "command": "uv",
                    "args": [
                        "run",
                        "python",
                        "-m",
                        "claude_mpm.mcp.messaging_server",
                    ],
                }
            }
        }
        (project_dir / ".mcp.json").write_text(json.dumps(data))

        assert check_needs_migration(project_dir) is True

    def test_binary_needs_migration(self, project_dir):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            check_needs_migration,
        )

        data = {
            "mcpServers": {
                "session": {
                    "command": "mpm-session-server",
                    "args": [],
                }
            }
        }
        (project_dir / ".mcp.json").write_text(json.dumps(data))

        assert check_needs_migration(project_dir) is True

    def test_uv_wrapped_binary_needs_migration(self, project_dir):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            check_needs_migration,
        )

        data = {
            "mcpServers": {
                "confluence": {
                    "command": "uv",
                    "args": [
                        "run",
                        "--directory",
                        "/path",
                        "confluence-mcp",
                    ],
                }
            }
        }
        (project_dir / ".mcp.json").write_text(json.dumps(data))

        assert check_needs_migration(project_dir) is True

    def test_non_mpm_servers_dont_trigger(self, project_dir):
        from claude_mpm.migrations.migrate_binary_consolidation import (
            check_needs_migration,
        )

        data = {
            "mcpServers": {
                "kuzu-memory": {
                    "command": "kuzu-memory",
                    "args": ["mcp"],
                }
            }
        }
        (project_dir / ".mcp.json").write_text(json.dumps(data))

        assert check_needs_migration(project_dir) is False


class TestRealisticMcpJson:
    """Test with realistic .mcp.json configurations matching actual user setups."""

    @pytest.fixture
    def project_dir(self, tmp_path):
        return tmp_path

    def test_full_realistic_mcp_json(self, project_dir):
        """Test with a realistic .mcp.json similar to real user configurations."""
        from claude_mpm.migrations.migrate_binary_consolidation import (
            migrate_mcp_json,
        )

        data = {
            "mcpServers": {
                "kuzu-memory": {
                    "type": "stdio",
                    "command": "kuzu-memory",
                    "args": ["mcp"],
                    "env": {
                        "KUZU_MEMORY_PROJECT_ROOT": "/Users/user/project",
                        "KUZU_MEMORY_DB": "/Users/user/project/kuzu-memories",
                    },
                },
                "mcp-ticketer": {
                    "type": "stdio",
                    "command": "mcp-ticketer",
                    "args": ["mcp", "--path", "/Users/user/project"],
                    "env": {},
                },
                "slack-user-proxy": {
                    "type": "stdio",
                    "command": "uv",
                    "args": [
                        "run",
                        "--directory",
                        "/Users/user/project",
                        "python",
                        "-m",
                        "claude_mpm.mcp.slack_user_proxy_server",
                    ],
                    "env": {},
                },
                "mpm-messaging": {
                    "type": "stdio",
                    "command": "uv",
                    "args": [
                        "run",
                        "--directory",
                        "/Users/user/project",
                        "python",
                        "-m",
                        "claude_mpm.mcp.messaging_server",
                    ],
                    "env": {},
                },
                "mcp-vector-search": {
                    "type": "stdio",
                    "command": "uv",
                    "args": [
                        "run",
                        "--directory",
                        "/Users/user/project",
                        "mcp-vector-search",
                        "mcp",
                    ],
                    "env": {
                        "PROJECT_ROOT": "/Users/user/project",
                    },
                },
            }
        }

        (project_dir / ".mcp.json").write_text(json.dumps(data, indent=2))

        result = migrate_mcp_json(project_dir)

        # Only the two MPM module-based servers should be migrated
        assert len(result["migrated"]) == 2
        migrated_names = [m[0] for m in result["migrated"]]
        assert "slack-user-proxy" in migrated_names
        assert "mpm-messaging" in migrated_names

        # Non-MPM servers should be unchanged
        assert "kuzu-memory" in result["unchanged"]
        assert "mcp-ticketer" in result["unchanged"]
        assert "mcp-vector-search" in result["unchanged"]

        # Verify the migrated entries
        updated = json.loads((project_dir / ".mcp.json").read_text())

        slack_proxy = updated["mcpServers"]["slack-user-proxy"]
        assert slack_proxy["command"] == "uv"
        assert slack_proxy["args"] == [
            "run",
            "--directory",
            "/Users/user/project",
            "claude-mpm",
            "mcp",
            "serve",
            "slack-proxy",
        ]

        messaging = updated["mcpServers"]["mpm-messaging"]
        assert messaging["command"] == "uv"
        assert messaging["args"] == [
            "run",
            "--directory",
            "/Users/user/project",
            "claude-mpm",
            "mcp",
            "serve",
            "messaging",
        ]

        # Verify non-MPM servers are untouched
        kuzu = updated["mcpServers"]["kuzu-memory"]
        assert kuzu["command"] == "kuzu-memory"
        assert kuzu["env"]["KUZU_MEMORY_PROJECT_ROOT"] == "/Users/user/project"

    def test_session_server_binary_migration(self, project_dir):
        """Test session server binary migration (not wrapped in uv)."""
        from claude_mpm.migrations.migrate_binary_consolidation import (
            migrate_mcp_json,
        )

        data = {
            "mcpServers": {
                "mpm-session": {
                    "type": "stdio",
                    "command": "mpm-session-server",
                    "args": [],
                },
                "mpm-session-http": {
                    "type": "stdio",
                    "command": "mpm-session-server-http",
                    "args": [],
                },
            }
        }

        (project_dir / ".mcp.json").write_text(json.dumps(data, indent=2))

        result = migrate_mcp_json(project_dir)

        assert len(result["migrated"]) == 2

        updated = json.loads((project_dir / ".mcp.json").read_text())

        session = updated["mcpServers"]["mpm-session"]
        assert session["command"] == "claude-mpm"
        assert session["args"] == ["mcp", "serve", "session"]

        session_http = updated["mcpServers"]["mpm-session-http"]
        assert session_http["command"] == "claude-mpm"
        assert session_http["args"] == ["mcp", "serve", "session-http"]
