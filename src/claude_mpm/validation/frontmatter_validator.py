from pathlib import Path

"""
Claude Code Frontmatter Validator

Validates agent frontmatter against Claude Code specification.
Critical for ensuring agents work correctly with Claude Code.
"""

import re
from typing import ClassVar, Dict, List, Optional, Tuple

import yaml


class FrontmatterValidator:
    """Validates agent frontmatter against Claude Code specification."""

    # Claude Code name pattern: lowercase letters, numbers, hyphens only
    # NO UNDERSCORES, NO UPPERCASE, NO SPECIAL CHARACTERS
    NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

    # Valid tool names (from Claude Code spec)
    VALID_TOOLS: ClassVar[set] = {
        "Read",
        "Write",
        "Edit",
        "MultiEdit",
        "Bash",
        "Grep",
        "Glob",
        "LS",
        "WebSearch",
        "WebFetch",
        "TodoWrite",
        "BashOutput",
        "KillBash",
        "NotebookEdit",
        "Task",
        "ExitPlanMode",
    }

    # Valid model tiers
    VALID_MODELS: ClassVar[set] = {"opus", "sonnet", "haiku"}

    # Required fields in frontmatter
    REQUIRED_FIELDS: ClassVar[set] = {"name", "description", "tools"}

    @classmethod
    def validate_name(cls, name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate agent name field against Claude Code spec.

        Args:
            name: Agent name to validate

        Returns:
            (is_valid, error_message)
        """
        if not name:
            return False, "Name field is required"

        if not cls.NAME_PATTERN.match(name):
            return False, (
                f"Invalid name '{name}'. Must match pattern ^[a-z0-9]+(-[a-z0-9]+)*$ "
                "(lowercase letters, numbers, and hyphens only - NO underscores!)"
            )

        if len(name) > 50:
            return False, f"Name '{name}' too long (max 50 characters)"

        return True, None

    @classmethod
    def validate_tools(cls, tools: str) -> Tuple[bool, Optional[str]]:
        """
        Validate tools field format and content.

        CRITICAL: Tools must be comma-separated WITHOUT spaces!

        Args:
            tools: Tools string to validate

        Returns:
            (is_valid, error_message)
        """
        if not tools:
            return False, "Tools field is required"

        # Check for spaces after commas (CRITICAL ERROR)
        if ", " in tools:
            return False, (
                f"CRITICAL: Tools contain spaces after commas! '{tools}' "
                "Must be comma-separated WITHOUT spaces (e.g., 'Read,Write,Edit')"
            )

        # Validate individual tools
        tool_list = tools.split(",")
        invalid_tools = [t for t in tool_list if t not in cls.VALID_TOOLS]

        if invalid_tools:
            return (
                False,
                f"Invalid tools: {', '.join(invalid_tools)}. Valid tools: {', '.join(sorted(cls.VALID_TOOLS))}",
            )

        return True, None

    @classmethod
    def validate_model(cls, model: str) -> Tuple[bool, Optional[str]]:
        """
        Validate model field.

        Args:
            model: Model tier to validate

        Returns:
            (is_valid, error_message)
        """
        if model and model not in cls.VALID_MODELS:
            return (
                False,
                f"Invalid model '{model}'. Must be one of: {', '.join(cls.VALID_MODELS)}",
            )

        return True, None

    @classmethod
    def validate_frontmatter(cls, frontmatter: Dict) -> List[str]:
        """
        Validate complete frontmatter structure.

        Args:
            frontmatter: Parsed frontmatter dictionary

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check required fields
        missing = cls.REQUIRED_FIELDS - set(frontmatter.keys())
        if missing:
            errors.append(f"Missing required fields: {', '.join(missing)}")

        # Validate name
        if "name" in frontmatter:
            valid, error = cls.validate_name(frontmatter["name"])
            if not valid:
                errors.append(error)

        # Validate tools
        if "tools" in frontmatter:
            valid, error = cls.validate_tools(frontmatter["tools"])
            if not valid:
                errors.append(error)

        # Validate model
        if "model" in frontmatter:
            valid, error = cls.validate_model(frontmatter["model"])
            if not valid:
                errors.append(error)

        # Validate description
        if "description" in frontmatter:
            desc = frontmatter["description"]
            if len(desc) < 10:
                errors.append(f"Description too short ({len(desc)} chars, min 10)")
            if len(desc) > 200:
                errors.append(f"Description too long ({len(desc)} chars, max 200)")

        return errors

    @classmethod
    def validate_agent_file(cls, file_path: Path) -> List[str]:
        """
        Validate an agent markdown file.

        Args:
            file_path: Path to agent .md file

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        try:
            with file_path.open() as f:
                content = f.read()

            # Check for frontmatter markers
            if not content.startswith("---\n"):
                errors.append("File must start with '---' frontmatter marker")
                return errors

            # Extract frontmatter
            end_marker = content.find("\n---\n", 4)
            if end_marker == -1:
                errors.append("Missing closing '---' frontmatter marker")
                return errors

            frontmatter_text = content[4:end_marker]

            # Parse YAML
            try:
                frontmatter = yaml.safe_load(frontmatter_text)
            except yaml.YAMLError as e:
                errors.append(f"Invalid YAML in frontmatter: {e}")
                return errors

            # Validate frontmatter content
            validation_errors = cls.validate_frontmatter(frontmatter)
            errors.extend(validation_errors)

        except Exception as e:
            errors.append(f"Error reading file: {e}")

        return errors


def main():
    """Command-line validation tool."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python frontmatter_validator.py <agent.md> [agent2.md ...]")
        sys.exit(1)

    all_valid = True

    for file_path in sys.argv[1:]:
        path = Path(file_path)
        if not path.exists():
            print(f"❌ {file_path}: File not found")
            all_valid = False
            continue

        errors = FrontmatterValidator.validate_agent_file(path)

        if errors:
            print(f"❌ {file_path}:")
            for error in errors:
                print(f"   - {error}")
            all_valid = False
        else:
            print(f"✅ {file_path}: Valid")

    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()
