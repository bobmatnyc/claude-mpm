"""
Comprehensive tests for agent name parsing bug fix in AgentValidator._extract_agent_info

This test suite verifies that the fixed _extract_agent_info method:
1. Only parses YAML frontmatter (between first two --- markers)
2. Ignores all code examples in body content
3. Correctly extracts agent metadata from frontmatter
4. Handles edge cases gracefully
"""

from pathlib import Path

import pytest

from claude_mpm.services.agents.deployment.agent_validator import AgentValidator


class TestAgentValidatorFrontmatterParsing:
    """Test suite for agent frontmatter parsing bug fix"""

    def setup_method(self):
        """Setup test fixtures"""
        self.validator = AgentValidator()

    def test_extracts_correct_name_from_frontmatter(self):
        """Test: Should extract agent name from YAML frontmatter only"""
        content = """---
name: vercel-ops-agent
description: "Ops agent for deployments"
version: "2.0.1"
---
# Agent Content

Some body content here.
"""
        agent_file = Path("test_agent.md")
        result = self.validator._extract_agent_info(content, agent_file)

        assert result["name"] == "vercel-ops-agent"
        assert result["description"] == "Ops agent for deployments"
        assert result["version"] == "2.0.1"

    def test_ignores_yaml_name_in_code_example(self):
        """Test: Should NOT parse 'name: Deploy' from GitHub Actions YAML in body"""
        content = """---
name: vercel-ops-agent
description: "Vercel operations agent"
version: "2.0.1"
---
# Vercel Agent

## CI/CD Integration

```yaml
# GitHub Actions with environment sync
name: Deploy
on:
  push:
    branches: [main, staging]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Install Vercel CLI
        run: npm i -g vercel@latest
```
"""
        agent_file = Path("vercel_ops_agent.md")
        result = self.validator._extract_agent_info(content, agent_file)

        # Should get the frontmatter name, NOT "Deploy" from the YAML example
        assert result["name"] == "vercel-ops-agent"
        assert result["name"] != "Deploy"
        assert result["description"] == "Vercel operations agent"

    def test_ignores_typescript_zod_schema_in_code(self):
        """Test: Should NOT parse 'name: z.string(),' from TypeScript code"""
        content = """---
name: typescript-engineer
description: "TypeScript development agent"
version: "1.0.0"
type: engineer
---
# TypeScript Engineer

## Schema Validation Example

```typescript
import { z } from 'zod';

const envSchema = z.object({
  name: z.string(),
  description: z.string().optional(),
});
```
"""
        agent_file = Path("typescript_engineer.md")
        result = self.validator._extract_agent_info(content, agent_file)

        # Should get the frontmatter name, NOT "z.string()," from TypeScript
        assert result["name"] == "typescript-engineer"
        assert "z.string" not in result["name"]
        assert result["description"] == "TypeScript development agent"

    def test_ignores_interface_definition_in_code(self):
        """Test: Should NOT parse 'name: string;' from interface definitions"""
        content = """---
name: svelte-engineer
description: "Svelte development agent"
version: "1.0.0"
---
# Svelte Engineer

## Component Interface

```typescript
interface ComponentProps {
    name: string;
    title: string;
    description?: string;
}
```
"""
        agent_file = Path("svelte-engineer.md")
        result = self.validator._extract_agent_info(content, agent_file)

        # Should get the frontmatter name, NOT "string;" from interface
        assert result["name"] == "svelte-engineer"
        assert result["name"] != "string"
        assert "string;" not in result["name"]

    def test_handles_missing_frontmatter_gracefully(self):
        """Test: Should use filename when frontmatter is missing"""
        content = """# Agent Without Frontmatter

This agent file has no YAML frontmatter at all.
Just markdown content.
"""
        agent_file = Path("no-frontmatter-agent.md")
        result = self.validator._extract_agent_info(content, agent_file)

        # Should fall back to filename stem
        assert result["name"] == "no-frontmatter-agent"
        assert result["description"] == "No description"
        assert result["version"] == "unknown"

    def test_handles_unclosed_frontmatter(self):
        """Test: Should handle frontmatter without closing --- marker"""
        content = """---
name: incomplete-agent
description: "Agent with unclosed frontmatter"

# This is body content but frontmatter was never closed
"""
        agent_file = Path("incomplete-agent.md")
        result = self.validator._extract_agent_info(content, agent_file)

        # Should still extract what it can from the YAML-like content
        # before stopping at the markdown header
        assert result["name"] == "incomplete-agent"
        assert result["description"] == "Agent with unclosed frontmatter"

    def test_handles_empty_frontmatter_block(self):
        """Test: Should handle empty frontmatter block"""
        content = """---
---
# Agent Content

Body starts immediately after empty frontmatter.
"""
        agent_file = Path("empty-frontmatter.md")
        result = self.validator._extract_agent_info(content, agent_file)

        # Should fall back to filename
        assert result["name"] == "empty-frontmatter"
        assert result["description"] == "No description"

    def test_handles_multiple_triple_dashes_in_body(self):
        """Test: Should stop at second --- and ignore later ones in body"""
        content = """---
name: complex-agent
description: "Agent with complex content"
version: "1.0.0"
---
# Agent Content

Some content here.

---
This is NOT frontmatter, just a horizontal rule in markdown.

```yaml
name: FakeAgent
description: "This should be ignored"
---
```

More content with --- markers.
"""
        agent_file = Path("complex-agent.md")
        result = self.validator._extract_agent_info(content, agent_file)

        # Should only parse the first frontmatter block
        assert result["name"] == "complex-agent"
        assert result["description"] == "Agent with complex content"
        assert result["name"] != "FakeAgent"

    def test_handles_quoted_values_in_frontmatter(self):
        """Test: Should strip quotes from YAML values"""
        content = """---
name: "quoted-agent"
description: 'Single quoted description'
version: "1.0.0"
type: 'engineer'
---
# Content
"""
        agent_file = Path("quoted-agent.md")
        result = self.validator._extract_agent_info(content, agent_file)

        assert result["name"] == "quoted-agent"
        assert result["description"] == "Single quoted description"
        assert result["version"] == "1.0.0"
        assert result["type"] == "engineer"

    def test_preserves_default_values_for_missing_fields(self):
        """Test: Should use defaults when fields are missing"""
        content = """---
name: minimal-agent
---
# Content
"""
        agent_file = Path("minimal-agent.md")
        result = self.validator._extract_agent_info(content, agent_file)

        assert result["name"] == "minimal-agent"
        assert result["description"] == "No description"
        assert result["version"] == "unknown"
        assert result["type"] == "agent"

    def test_extracts_all_frontmatter_fields(self):
        """Test: Should extract all supported frontmatter fields"""
        content = """---
name: full-featured-agent
description: "Complete agent with all metadata"
version: "2.1.0"
type: specialist
---
# Content
"""
        agent_file = Path("full-featured-agent.md")
        result = self.validator._extract_agent_info(content, agent_file)

        assert result["name"] == "full-featured-agent"
        assert result["description"] == "Complete agent with all metadata"
        assert result["version"] == "2.1.0"
        assert result["type"] == "specialist"
        assert result["file"] == "full-featured-agent.md"
        assert "path" in result


class TestAgentValidatorRealWorldFiles:
    """Test with actual agent files from the codebase"""

    def setup_method(self):
        """Setup test fixtures"""
        self.validator = AgentValidator()
        self.agents_dir = Path("/Users/masa/Projects/claude-mpm/.claude/agents")

    def test_vercel_ops_agent_parses_correctly(self):
        """Test: vercel_ops_agent.md should extract correct name, not 'Deploy'"""
        agent_file = self.agents_dir / "vercel_ops_agent.md"

        if not agent_file.exists():
            pytest.skip(f"Agent file not found: {agent_file}")

        content = agent_file.read_text()
        result = self.validator._extract_agent_info(content, agent_file)

        # Should extract 'vercel-ops-agent' from frontmatter
        # NOT 'Deploy' from the GitHub Actions YAML example
        assert result["name"] == "vercel-ops-agent"
        assert result["name"] != "Deploy"
        assert (
            "vercel" in result["description"].lower()
            or "ops" in result["description"].lower()
        )

    def test_gcp_ops_agent_parses_correctly(self):
        """Test: gcp_ops_agent.md should parse correctly if it exists"""
        agent_file = self.agents_dir / "gcp_ops_agent.md"

        if not agent_file.exists():
            pytest.skip(f"Agent file not found: {agent_file}")

        content = agent_file.read_text()
        result = self.validator._extract_agent_info(content, agent_file)

        # Should extract proper name from frontmatter
        assert result["name"] is not None
        assert len(result["name"]) > 0
        # Should not contain code artifacts
        assert "string;" not in result["name"]
        assert "z.string" not in result["name"]

    def test_all_agents_parse_without_code_artifacts(self):
        """Test: All agents should parse without code artifacts in names"""
        if not self.agents_dir.exists():
            pytest.skip(f"Agents directory not found: {self.agents_dir}")

        agent_files = list(self.agents_dir.glob("*.md"))

        if not agent_files:
            pytest.skip("No agent files found")

        problematic_patterns = [
            "Deploy",  # From GitHub Actions YAML
            "z.string",  # From Zod schemas
            "string;",  # From TypeScript interfaces
            "interface",  # From code examples
            "function",  # From code examples
            "const",  # From code examples
        ]

        for agent_file in agent_files:
            content = agent_file.read_text()
            result = self.validator._extract_agent_info(content, agent_file)

            agent_name = result["name"]

            # Check for code artifacts in the extracted name
            for pattern in problematic_patterns:
                assert pattern not in agent_name, (
                    f"Agent {agent_file.name} has code artifact '{pattern}' "
                    f"in extracted name: '{agent_name}'"
                )

            # Name should follow kebab-case pattern
            assert agent_name, f"Agent {agent_file.name} has empty name"


class TestAgentValidatorEdgeCases:
    """Test edge cases and boundary conditions"""

    def setup_method(self):
        """Setup test fixtures"""
        self.validator = AgentValidator()

    def test_frontmatter_with_colons_in_values(self):
        """Test: Should handle colons in YAML values"""
        content = """---
name: test-agent
description: "Description with: colon in it"
version: "1.0.0"
---
# Content
"""
        agent_file = Path("test-agent.md")
        result = self.validator._extract_agent_info(content, agent_file)

        assert result["name"] == "test-agent"
        assert "colon" in result["description"]

    def test_frontmatter_with_multiline_values(self):
        """Test: Should handle multiline YAML values (take first line)"""
        content = """---
name: multiline-agent
description: "First line of description
  Second line should be ignored by simple parser"
version: "1.0.0"
---
# Content
"""
        agent_file = Path("multiline-agent.md")
        result = self.validator._extract_agent_info(content, agent_file)

        assert result["name"] == "multiline-agent"
        # Simple parser takes first line value
        assert "First line" in result["description"]

    def test_whitespace_handling(self):
        """Test: Should handle various whitespace in frontmatter"""
        content = """---
name:    whitespace-agent
description:   "Description with spaces"
version:  "1.0.0"
---
# Content
"""
        agent_file = Path("whitespace-agent.md")
        result = self.validator._extract_agent_info(content, agent_file)

        # Should strip whitespace
        assert result["name"] == "whitespace-agent"
        assert result["description"] == "Description with spaces"

    def test_case_sensitivity(self):
        """Test: Field names should be case-sensitive"""
        content = """---
Name: wrong-case-agent
DESCRIPTION: "Should not be extracted"
name: correct-agent
description: "Should be extracted"
---
# Content
"""
        agent_file = Path("case-test.md")
        result = self.validator._extract_agent_info(content, agent_file)

        # Should use lowercase field names
        assert result["name"] == "correct-agent"
        assert result["description"] == "Should be extracted"
