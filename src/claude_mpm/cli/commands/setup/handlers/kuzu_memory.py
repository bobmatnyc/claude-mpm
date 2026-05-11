"""kuzu-memory graph-based memory backend setup."""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404
from datetime import UTC
from pathlib import Path

from ....constants import SetupService
from ....shared import CommandResult
from .._shared import console


class KuzuMemoryMixin:
    """Mixin: kuzu-memory installation, migration, and hook cleanup."""

    def _remove_kuzu_memory_hooks(self) -> bool:
        """Remove kuzu-memory's independent hooks from Claude Code settings.

        This is called after setting up subservient mode to ensure kuzu-memory
        integrates through MPM's hook system instead of running independently.
        """
        settings_path = Path.home() / ".claude" / "settings.local.json"

        if not settings_path.exists():
            # No settings file, nothing to clean
            return True

        try:
            # Load settings
            with open(settings_path) as f:
                settings = json.load(f)

            hooks = settings.get("hooks", {})
            removed = []

            # Find and remove kuzu-memory hooks
            for hook_name, hook_config in list(hooks.items()):
                if isinstance(hook_config, dict):
                    command = hook_config.get("command", "")
                    if "kuzu-memory hooks" in command or "/kuzu-memory" in command:
                        del hooks[hook_name]
                        removed.append(hook_name)

            if removed:
                # Save cleaned settings
                settings["hooks"] = hooks
                with open(settings_path, "w") as f:
                    json.dump(settings, f, indent=2)

                console.print(
                    f"[green]✓ Removed {len(removed)} kuzu-memory hooks: "
                    f"{', '.join(removed)}[/green]"
                )
                console.print(
                    "[dim]kuzu-memory will now integrate through claude-mpm hooks[/dim]"
                )

            return True

        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not remove kuzu-memory hooks: {e}[/yellow]"
            )
            console.print(
                "[dim]You may need to manually remove them from "
                ".claude/settings.local.json[/dim]"
            )
            return False

    def _setup_kuzu_memory(self, args) -> CommandResult:
        """Set up kuzu-memory graph-based memory backend."""
        try:
            console.print(
                "\n[bold]Kuzu Memory Setup[/bold]\n"
                "This will replace static file-based memory with graph-based kuzu-memory.\n"
                "Kuzu-memory provides semantic search and enhanced context management.\n"
            )

            # Use centralized package installer
            console.print("[cyan]Checking kuzu-memory installation...[/cyan]")

            from .....services.package_installer import (
                InstallAction,
                PackageInstallerService,
                get_spec,
            )

            installer = PackageInstallerService()
            spec = get_spec(SetupService.KUZU_MEMORY)

            force = getattr(args, "force", False)
            upgrade = getattr(args, "upgrade", False)

            # Check if already installed and no flags set
            if installer.is_installed(spec) and not force and not upgrade:
                console.print("[green]✓ kuzu-memory already installed[/green]")
            else:
                console.print("[cyan]Detecting installation method...[/cyan]")
                success, message = installer.install(
                    spec, InstallAction.INSTALL, force=force, upgrade=upgrade
                )
                if success:
                    console.print(f"[green]✓ {message}[/green]")
                else:
                    return CommandResult.error_result(message)

            # Migrate existing static memory files if present
            console.print("\n[cyan]Checking for existing memory files...[/cyan]")
            static_memory_dir = Path.cwd() / ".claude-mpm" / "memories"
            memories_migrated = False

            if static_memory_dir.exists() and list(static_memory_dir.glob("*.md")):
                console.print(
                    "[yellow]Found existing static memory files. Migrating to kuzu-memory...[/yellow]"
                )

                # Count memory files
                memory_files = list(static_memory_dir.glob("*.md"))
                console.print(f"  Found {len(memory_files)} memory file(s)")

                # Migrate each memory file to kuzu-memory
                for memory_file in memory_files:
                    try:
                        content = memory_file.read_text()
                        agent_name = memory_file.stem

                        # Use kuzu-memory CLI to import the memory
                        import_result = subprocess.run(
                            [
                                "kuzu-memory",
                                "memory",
                                "learn",
                                content,
                                "--metadata",
                                f"agent={agent_name}",
                                "--metadata",
                                "source=mpm_static_migration",
                            ],
                            capture_output=True,
                            text=True,
                            check=False,
                        )  # nosec B603 B607

                        if import_result.returncode == 0:
                            console.print(
                                f"  [green]✓ Migrated {memory_file.name}[/green]"
                            )
                            memories_migrated = True
                        else:
                            console.print(
                                f"  [yellow]⚠ Could not migrate {memory_file.name}: {import_result.stderr}[/yellow]"
                            )

                    except Exception as e:
                        console.print(
                            f"  [yellow]⚠ Error migrating {memory_file.name}: {e}[/yellow]"
                        )

                if memories_migrated:
                    console.print(
                        "[green]✓ Memory files migrated to kuzu-memory[/green]"
                    )

                    # Create backup of static memory files
                    backup_dir = static_memory_dir.parent / "memories_backup"
                    backup_dir.mkdir(exist_ok=True)

                    for memory_file in memory_files:
                        shutil.copy2(memory_file, backup_dir / memory_file.name)

                    console.print(f"[green]✓ Backup created at: {backup_dir}[/green]")

                    # Archive original files to prevent re-import
                    console.print("\n[cyan]Archiving original files...[/cyan]")
                    archive_dir = static_memory_dir / ".migrated"
                    archive_dir.mkdir(exist_ok=True)

                    archived_count = 0
                    for memory_file in memory_files:
                        try:
                            dest = archive_dir / memory_file.name
                            memory_file.rename(dest)
                            console.print(f"  [dim]✓ Archived {memory_file.name}[/dim]")
                            archived_count += 1
                        except Exception as e:
                            console.print(
                                f"  [yellow]⚠ Could not archive {memory_file.name}: {e}[/yellow]"
                            )

                    if archived_count > 0:
                        # Create README in archive directory
                        from datetime import datetime

                        readme_content = f"""# Migrated Memory Files

These static memory files were migrated to kuzu-memory on {datetime.now(UTC).isoformat()}.

**Status**: These files are archived and no longer active. The kuzu-memory graph database now manages all memories.

**Backup**: Backup copies exist in `../memories_backup/` for recovery if needed.

**Recovery**: If you need to restore these files, copy them back to `../` (parent directory).
"""
                        try:
                            (archive_dir / "README.md").write_text(readme_content)
                            console.print(
                                f"[green]✓ Archived {archived_count} file(s) to .migrated/[/green]"
                            )
                        except Exception as e:
                            console.print(
                                f"[yellow]Warning: Could not create archive README: {e}[/yellow]"
                            )
            else:
                console.print("  No existing memory files to migrate")

            # Update PROJECT-LOCAL configuration (not global)
            console.print("\n[cyan]Configuring kuzu-memory backend...[/cyan]")

            # Use project-local config in .claude-mpm/configuration.yaml
            config_path = Path.cwd() / ".claude-mpm" / "configuration.yaml"

            # Load existing config or create new
            import yaml

            if config_path.exists():
                with open(config_path) as f:
                    config = yaml.safe_load(f) or {}
            else:
                config = {}

            # Set memory backend to kuzu
            if "memory" not in config:
                config["memory"] = {}

            config["memory"]["backend"] = "kuzu"

            # Set default kuzu config if not present
            if "kuzu" not in config["memory"]:
                config["memory"]["kuzu"] = {
                    "project_root": str(Path.cwd()),
                    "db_path": str(Path.cwd() / "kuzu-memories"),
                }

            # Save config
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            console.print(
                f"[green]✓ Project configuration updated: {config_path}[/green]"
            )

            # Create database directory
            db_path = Path(config["memory"]["kuzu"].get("db_path", "./kuzu-memories"))
            db_path.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]✓ Created database directory: {db_path}[/green]")

            # Create .kuzu-memory-config for subservient mode (v1.6.33+)
            kuzu_config_path = Path.cwd() / ".kuzu-memory-config"
            kuzu_config = {
                "mode": "subservient",
                "managed_by": "claude-mpm",
                "version": "1.0",
            }

            try:
                with open(kuzu_config_path, "w") as f:
                    yaml.dump(kuzu_config, f, default_flow_style=False)
                console.print(
                    f"[green]✓ Created subservient mode config: {kuzu_config_path}[/green]"
                )
            except Exception as e:
                console.print(
                    f"[yellow]Warning: Could not create .kuzu-memory-config: {e}[/yellow]"
                )

            # Remove kuzu-memory's independent hooks
            console.print("\n[cyan]Cleaning up kuzu-memory hooks...[/cyan]")
            self._remove_kuzu_memory_hooks()

            console.print("\n[green]✓ Kuzu Memory setup complete![/green]")

            # Build what changed message
            what_changed = [
                "  1. kuzu-memory v1.6.33+ installed (or re-used if already installed)",
                "  2. Project-local configuration created (.claude-mpm/configuration.yaml)",
                "  3. Memory backend set to 'kuzu' for THIS PROJECT ONLY",
                "  4. Database directory created",
                "  5. Subservient mode enabled (MPM controls hooks, project-only)",
            ]

            if memories_migrated:
                what_changed.append(
                    "  6. Existing static memory files migrated and backed up"
                )

            console.print("\n[dim]What changed:[/dim]")
            console.print("\n".join(what_changed))

            console.print(
                "\n[dim]Next steps:[/dim]\n"
                "  1. Start Claude MPM to use graph-based memory\n"
                "  2. Your memories will be stored in the graph database\n"
                "  3. Use semantic search for better context retrieval\n"
                "\n[dim]Important:[/dim]\n"
                "  • Configuration is PROJECT-LOCAL (not global)\n"
                "  • Hooks are PROJECT-ONLY (not system-wide)\n"
                "  • kuzu-memory operates in subservient mode\n"
                "  • Each project can have its own memory backend configuration\n"
            )

            return CommandResult.success_result("Kuzu Memory setup completed")

        except KeyboardInterrupt:
            console.print("\n[yellow]Setup cancelled by user[/yellow]")
            return CommandResult.error_result("Setup cancelled")
        except Exception as e:
            return CommandResult.error_result(f"Error during setup: {e}")
