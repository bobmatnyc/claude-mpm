"""
Test suite for env-manager validate_env.py script.

Tests cover:
- Structure validation
- Duplicate detection
- Comparison with .env.example
- Framework-specific validation (Next.js, Vite, React, Node.js, Flask)
- Edge cases and error handling

Target coverage: 85%+
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestEnvValidator:
    """Test suite for environment validation."""

    @pytest.fixture
    def script_path(self):
        """Path to validate_env.py script."""
        return (
            Path(__file__).parent.parent.parent
            / "src/claude_mpm/skills/bundled/infrastructure/env-manager/scripts/validate_env.py"
        )

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def create_env_file(self, temp_dir: Path, filename: str, content: str) -> Path:
        """Helper to create .env file with content."""
        file_path = temp_dir / filename
        file_path.write_text(content)
        return file_path

    def run_validator(
        self, script_path: Path, env_file: Path, *args
    ) -> subprocess.CompletedProcess:
        """Helper to run validation script."""
        cmd = ["python3", str(script_path), str(env_file)] + list(args)
        return subprocess.run(cmd, check=False, capture_output=True, text=True)

    # Structure Validation Tests

    def test_valid_env_file(self, script_path, temp_dir):
        """Test validation passes for valid .env file."""
        content = """
# Database configuration
DATABASE_URL=postgres://localhost:5432/mydb
API_KEY=test-api-key-123
PORT=3000
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file)

        assert result.returncode == 0
        assert "✅ Validation passed!" in result.stdout

    def test_invalid_format_missing_equals(self, script_path, temp_dir):
        """Test error on line without equals sign."""
        content = """
DATABASE_URL=postgres://localhost:5432/mydb
INVALID_LINE_NO_EQUALS
API_KEY=test-key
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file)

        assert result.returncode == 1
        assert "Invalid format (missing =)" in result.stdout

    def test_invalid_naming_lowercase(self, script_path, temp_dir):
        """Test error on lowercase variable names."""
        content = """
database_url=postgres://localhost:5432/mydb
API_KEY=test-key
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file)

        assert result.returncode == 1
        assert "Invalid naming" in result.stdout

    def test_invalid_naming_kebab_case(self, script_path, temp_dir):
        """Test error on kebab-case variable names."""
        content = """
database-url=postgres://localhost:5432/mydb
API_KEY=test-key
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file)

        assert result.returncode == 1
        assert "Invalid naming" in result.stdout

    def test_warning_inline_comments(self, script_path, temp_dir):
        """Test warning on inline comments."""
        content = """
DATABASE_URL=postgres://localhost:5432/mydb # This is my database
API_KEY=test-key
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file)

        assert "inline comment" in result.stdout.lower()

    def test_warning_unquoted_spaces(self, script_path, temp_dir):
        """Test warning on values with spaces without quotes."""
        content = """
DATABASE_URL=postgres://localhost:5432/mydb
APP_NAME=My Great App
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file)

        assert "should be quoted" in result.stdout

    def test_quoted_values_accepted(self, script_path, temp_dir):
        """Test quoted values are accepted."""
        content = """
DATABASE_URL="postgres://localhost:5432/mydb"
APP_NAME="My Great App"
DESCRIPTION='This is a description'
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file)

        assert result.returncode == 0

    # Duplicate Detection Tests

    def test_duplicate_keys_detected(self, script_path, temp_dir):
        """Test duplicate keys are detected."""
        content = """
DATABASE_URL=postgres://localhost:5432/mydb
API_KEY=test-key-1
DATABASE_URL=postgres://localhost:5432/other
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file)

        assert result.returncode == 1
        assert "Duplicate key" in result.stdout
        assert "DATABASE_URL" in result.stdout

    # Comparison Tests

    def test_compare_with_example_all_present(self, script_path, temp_dir):
        """Test comparison when all required vars present."""
        example_content = """
DATABASE_URL=postgres://example
API_KEY=example-key
PORT=3000
"""
        env_content = """
DATABASE_URL=postgres://localhost:5432/mydb
API_KEY=actual-key-123
PORT=4000
"""
        example_file = self.create_env_file(temp_dir, ".env.example", example_content)
        env_file = self.create_env_file(temp_dir, ".env", env_content)

        result = self.run_validator(
            script_path, env_file, "--compare-with", str(example_file)
        )

        assert result.returncode == 0
        assert "✅ Validation passed!" in result.stdout

    def test_compare_with_example_missing_vars(self, script_path, temp_dir):
        """Test error when required vars missing."""
        example_content = """
DATABASE_URL=postgres://example
API_KEY=example-key
JWT_SECRET=example-secret
"""
        env_content = """
DATABASE_URL=postgres://localhost:5432/mydb
API_KEY=actual-key-123
"""
        example_file = self.create_env_file(temp_dir, ".env.example", example_content)
        env_file = self.create_env_file(temp_dir, ".env", env_content)

        result = self.run_validator(
            script_path, env_file, "--compare-with", str(example_file)
        )

        assert result.returncode == 1
        assert "JWT_SECRET" in result.stdout
        assert "missing" in result.stdout.lower()

    def test_compare_with_example_extra_vars(self, script_path, temp_dir):
        """Test warning when extra undocumented vars present."""
        example_content = """
DATABASE_URL=postgres://example
API_KEY=example-key
"""
        env_content = """
DATABASE_URL=postgres://localhost:5432/mydb
API_KEY=actual-key-123
EXTRA_VAR=some-value
"""
        example_file = self.create_env_file(temp_dir, ".env.example", example_content)
        env_file = self.create_env_file(temp_dir, ".env", env_content)

        result = self.run_validator(
            script_path, env_file, "--compare-with", str(example_file)
        )

        assert "EXTRA_VAR" in result.stdout
        assert "not documented" in result.stdout.lower()

    # Next.js Framework Tests

    def test_nextjs_valid_public_vars(self, script_path, temp_dir):
        """Test Next.js accepts NEXT_PUBLIC_ vars."""
        content = """
NEXT_PUBLIC_API_URL=https://api.example.com
NEXT_PUBLIC_SITE_NAME=My Site
DATABASE_URL=postgres://localhost:5432/mydb
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file, "--framework", "nextjs")

        assert result.returncode == 0

    def test_nextjs_secret_in_public_var_error(self, script_path, temp_dir):
        """Test error when secret in NEXT_PUBLIC_ var."""
        content = """
NEXT_PUBLIC_API_SECRET=my-secret-key
DATABASE_URL=postgres://localhost:5432/mydb
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file, "--framework", "nextjs")

        assert result.returncode == 1
        assert "SECURITY" in result.stdout
        assert "NEXT_PUBLIC_" in result.stdout

    def test_nextjs_api_url_without_public_warning(self, script_path, temp_dir):
        """Test warning when API URL not public."""
        content = """
API_URL=https://api.example.com
DATABASE_URL=postgres://localhost:5432/mydb
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file, "--framework", "nextjs")

        assert "API_URL" in result.stdout
        assert "NEXT_PUBLIC_" in result.stdout

    # Vite Framework Tests

    def test_vite_valid_vars(self, script_path, temp_dir):
        """Test Vite accepts VITE_ prefixed vars."""
        content = """
VITE_API_URL=https://api.example.com
VITE_APP_TITLE=My App
NODE_ENV=development
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file, "--framework", "vite")

        assert result.returncode == 0

    def test_vite_secret_in_vite_var_error(self, script_path, temp_dir):
        """Test error when secret in VITE_ var."""
        content = """
VITE_API_KEY=my-secret-api-key
NODE_ENV=development
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file, "--framework", "vite")

        assert result.returncode == 1
        assert "SECURITY" in result.stdout

    def test_vite_non_vite_var_warning(self, script_path, temp_dir):
        """Test warning for vars without VITE_ prefix."""
        content = """
VITE_API_URL=https://api.example.com
DATABASE_URL=postgres://localhost:5432/mydb
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file, "--framework", "vite")

        assert "DATABASE_URL" in result.stdout
        assert "not accessible" in result.stdout.lower()

    # React Framework Tests

    def test_react_secret_in_public_var_error(self, script_path, temp_dir):
        """Test error when secret in REACT_APP_ var."""
        content = """
REACT_APP_API_SECRET=my-secret
NODE_ENV=development
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file, "--framework", "react")

        assert result.returncode == 1
        assert "SECURITY" in result.stdout

    # Node.js Framework Tests

    def test_nodejs_valid_node_env(self, script_path, temp_dir):
        """Test Node.js accepts valid NODE_ENV values."""
        for env_value in ["development", "production", "test"]:
            content = f"""
NODE_ENV={env_value}
PORT=3000
"""
            env_file = self.create_env_file(temp_dir, ".env", content)
            result = self.run_validator(script_path, env_file, "--framework", "nodejs")

            assert result.returncode == 0

    def test_nodejs_invalid_node_env(self, script_path, temp_dir):
        """Test error on invalid NODE_ENV value."""
        content = """
NODE_ENV=staging
PORT=3000
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file, "--framework", "nodejs")

        assert result.returncode == 1
        assert "NODE_ENV" in result.stdout
        assert "Invalid value" in result.stdout

    def test_no_secret_exposure_in_errors(self, script_path, temp_dir):
        """SECURITY: Ensure error messages never expose actual variable values."""
        # Test with secret-looking value in NODE_ENV
        content = """
NODE_ENV=sk-proj-fake-secret-key-abc123xyz789
PORT=3000
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file, "--framework", "nodejs")

        # Assert validation error exists
        assert result.returncode == 1, (
            "Should have validation error for invalid NODE_ENV"
        )
        assert "NODE_ENV" in result.stdout, "Error should mention NODE_ENV"

        # CRITICAL: Verify the secret value is NOT in error message
        assert "sk-proj-fake-secret-key-abc123xyz789" not in result.stdout, (
            "SECURITY VIOLATION: Secret value exposed in error message"
        )

        # Verify proper error message format (explains expectation without exposing value)
        assert "expected one of" in result.stdout.lower(), (
            "Error message should explain expected values"
        )
        assert "invalid value" in result.stdout.lower(), (
            "Error message should indicate invalid value"
        )

        # Test with JSON output too
        result_json = self.run_validator(
            script_path, env_file, "--framework", "nodejs", "--json"
        )
        assert result_json.returncode == 1
        assert "sk-proj-fake-secret-key-abc123xyz789" not in result_json.stdout, (
            "SECURITY VIOLATION: Secret value exposed in JSON output"
        )

    def test_nodejs_invalid_port(self, script_path, temp_dir):
        """Test error on invalid PORT value."""
        content = """
NODE_ENV=development
PORT=99999
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file, "--framework", "nodejs")

        assert result.returncode == 1
        assert "PORT" in result.stdout

    def test_nodejs_non_numeric_port(self, script_path, temp_dir):
        """Test error on non-numeric PORT."""
        content = """
NODE_ENV=development
PORT=abc
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file, "--framework", "nodejs")

        assert result.returncode == 1
        assert "PORT" in result.stdout
        assert "numeric" in result.stdout.lower()

    # Flask Framework Tests

    def test_flask_missing_required_vars(self, script_path, temp_dir):
        """Test error when Flask required vars missing."""
        content = """
DATABASE_URL=postgres://localhost:5432/mydb
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file, "--framework", "flask")

        assert result.returncode == 1
        assert "FLASK_APP" in result.stdout or "SECRET_KEY" in result.stdout

    def test_flask_valid_config(self, script_path, temp_dir):
        """Test Flask accepts valid configuration."""
        content = """
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=my-secret-key
DATABASE_URL=postgresql://localhost/mydb
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file, "--framework", "flask")

        assert result.returncode == 0

    def test_flask_invalid_env_value(self, script_path, temp_dir):
        """Test error on invalid FLASK_ENV value."""
        content = """
FLASK_APP=app.py
FLASK_ENV=staging
SECRET_KEY=my-secret-key
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file, "--framework", "flask")

        assert result.returncode == 1
        assert "FLASK_ENV" in result.stdout

    # JSON Output Tests

    def test_json_output_format(self, script_path, temp_dir):
        """Test JSON output is valid and contains expected fields."""
        content = """
DATABASE_URL=postgres://localhost:5432/mydb
API_KEY=test-key
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file, "--json")

        assert result.returncode == 0
        data = json.loads(result.stdout)

        assert "valid" in data
        assert "file" in data
        assert "errors" in data
        assert "warnings" in data
        assert data["valid"] is True

    def test_json_output_with_errors(self, script_path, temp_dir):
        """Test JSON output includes error details."""
        content = """
invalid_line
DATABASE_URL=postgres://localhost:5432/mydb
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file, "--json")

        assert result.returncode == 1
        data = json.loads(result.stdout)

        assert data["valid"] is False
        assert len(data["errors"]) > 0
        assert "line" in data["errors"][0]
        assert "message" in data["errors"][0]

    # Generate Example Tests

    def test_generate_example(self, script_path, temp_dir):
        """Test .env.example generation."""
        content = """
# Database configuration
DATABASE_URL=postgres://localhost:5432/mydb
API_KEY=secret-key-123
PORT=3000
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        example_file = temp_dir / ".env.example"

        result = self.run_validator(
            script_path, env_file, "--generate-example", str(example_file)
        )

        assert result.returncode == 0
        assert example_file.exists()

        example_content = example_file.read_text()
        assert "DATABASE_URL=" in example_content
        assert "API_KEY=" in example_content
        assert "PORT=" in example_content
        # Should not contain actual secrets
        assert "secret-key-123" not in example_content
        assert "postgres://localhost:5432/mydb" not in example_content

    # Edge Cases

    def test_empty_env_file(self, script_path, temp_dir):
        """Test validation of empty .env file."""
        content = ""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file)

        assert result.returncode == 0  # Empty file is valid

    def test_comments_only_env_file(self, script_path, temp_dir):
        """Test validation of .env file with only comments."""
        content = """
# This is a comment
# Another comment
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file)

        assert result.returncode == 0

    def test_empty_values_accepted(self, script_path, temp_dir):
        """Test empty values are accepted."""
        content = """
DATABASE_URL=
API_KEY=test-key
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file)

        assert result.returncode == 0

    def test_file_not_found(self, script_path, temp_dir):
        """Test error when file doesn't exist."""
        nonexistent = temp_dir / "nonexistent.env"
        result = self.run_validator(script_path, nonexistent)

        assert result.returncode == 2
        assert "not found" in result.stdout.lower()

    def test_strict_mode_treats_warnings_as_errors(self, script_path, temp_dir):
        """Test --strict mode treats warnings as errors."""
        content = """
DATABASE_URL=postgres://localhost:5432/mydb
APP_NAME=My App
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file, "--strict")

        # Should fail because APP_NAME has unquoted spaces (warning)
        assert result.returncode == 1

    def test_quiet_mode_hides_warnings(self, script_path, temp_dir):
        """Test --quiet mode hides warnings."""
        content = """
DATABASE_URL=postgres://localhost:5432/mydb
APP_NAME=My App
"""
        env_file = self.create_env_file(temp_dir, ".env", content)
        result = self.run_validator(script_path, env_file, "--quiet")

        assert "⚠️" not in result.stdout
