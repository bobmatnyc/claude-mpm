"""End-to-end test for the full agent name delegation chain.

This test verifies the complete path from user-written todo text
through to AGENT_NAME_MAP resolution:

    todo text  ->  extract_from_todo()  ->  display name
    display name  ->  to_task_format()  ->  kebab-case stem
    kebab-case stem  ->  AGENT_NAME_MAP lookup  ->  known agent

This ensures that the PM's delegation flow works correctly: when a user
writes a todo like ``[Python Engineer] Build API``, the system can extract
the display name, normalize it to a task-format stem, and resolve it
against the agent registry.
"""

import pytest

from claude_mpm.core.agent_name_normalizer import AgentNameNormalizer
from claude_mpm.core.agent_name_registry import AGENT_NAME_MAP

# ---------------------------------------------------------------------------
# Known roundtrip failures in the delegation chain.
#
# These AGENT_NAME_MAP entries have display names that do NOT survive a
# roundtrip through AgentNameNormalizer.normalize().  They represent real
# bugs where the normalizer cannot recover the display name that the
# registry declares.
#
# Each entry is:  stem -> (registry display name, what normalize() returns)
#
#   code-analyzer:  "Code Analysis"      -> normalize returns "Engineer"
#                   Cause: No alias for "code_analysis"; only "code_analyzer"
#                   and "analyzer" exist.
#   gcp-ops:        "Google Cloud Ops"   -> normalize returns "Ops"
#                   Cause: "google_cloud" alias maps to gcp_ops, but
#                   "Google Cloud Ops" with three words is partially matched
#                   on "ops" by the alias scanner.
#   clerk-ops:      "Clerk Operations"   -> normalize returns "Ops"
#                   Cause: "operations" alias maps to "ops", so the partial
#                   match on "operations" fires before "clerk_ops" can match.
# ---------------------------------------------------------------------------
KNOWN_ROUNDTRIP_FAILURES: frozenset[str] = frozenset(
    {
        "code-analyzer",
        "gcp-ops",
        "clerk-ops",
    }
)


class TestDelegationChainE2E:
    """End-to-end test: display name -> stem -> AGENT_NAME_MAP lookup."""

    @pytest.mark.parametrize(
        "display_name,expected_stem",
        [
            # -- Standard two-word agents --
            ("Python Engineer", "python-engineer"),
            ("Local Ops", "local-ops"),
            ("Version Control", "version-control"),
            ("Data Engineer", "data-engineer"),
            ("Web UI", "web-ui"),
            # -- Single-word agents --
            ("Research", "research"),
            ("Engineer", "engineer"),
            ("QA", "qa"),
            ("Security", "security"),
            ("Ops", "ops"),
            # -- Multi-word / special agents --
            ("Web QA", "web-qa"),
            ("API QA", "api-qa"),
            ("Golang Engineer", "golang-engineer"),
            ("Rust Engineer", "rust-engineer"),
            ("React Engineer", "react-engineer"),
            ("Nextjs Engineer", "nextjs-engineer"),
            ("Data Scientist", "data-scientist"),
            # -- Agents whose display name includes "Agent" --
            ("Documentation Agent", "documentation"),
        ],
        ids=lambda val: val.replace(" ", "_") if isinstance(val, str) else val,
    )
    def test_display_name_resolves_to_known_agent(
        self, display_name: str, expected_stem: str
    ) -> None:
        """Display name normalizes to expected stem and exists in AGENT_NAME_MAP."""
        # Step 1: Normalize the display name (should roundtrip to itself)
        normalized = AgentNameNormalizer.normalize(display_name)
        assert normalized == display_name, (
            f"normalize('{display_name}') returned '{normalized}', "
            f"expected '{display_name}'"
        )

        # Step 2: Convert to task format (kebab-case stem)
        stem = AgentNameNormalizer.to_task_format(display_name)
        assert stem == expected_stem, (
            f"to_task_format('{display_name}') returned '{stem}', "
            f"expected '{expected_stem}'"
        )

        # Step 3: Verify stem exists in AGENT_NAME_MAP
        assert stem in AGENT_NAME_MAP, (
            f"Stem '{stem}' (from display name '{display_name}') "
            f"not found in AGENT_NAME_MAP"
        )

    @pytest.mark.parametrize(
        "todo_text,expected_display_name,expected_stem",
        [
            ("[Python Engineer] Build API", "Python Engineer", "python-engineer"),
            ("[Research] Analyze codebase", "Research", "research"),
            ("[Local Ops] Start server", "Local Ops", "local-ops"),
            ("[Version Control] Create PR", "Version Control", "version-control"),
            ("[QA] Run tests", "QA", "qa"),
            ("[Security] Run audit", "Security", "security"),
            ("[Data Engineer] Build pipeline", "Data Engineer", "data-engineer"),
            ("[Web QA] Test login flow", "Web QA", "web-qa"),
            (
                "[Documentation Agent] Update docs",
                "Documentation Agent",
                "documentation",
            ),
            ("[Engineer] Implement feature", "Engineer", "engineer"),
        ],
        ids=lambda val: val[:30].replace(" ", "_") if isinstance(val, str) else val,
    )
    def test_todo_text_full_chain(
        self,
        todo_text: str,
        expected_display_name: str,
        expected_stem: str,
    ) -> None:
        """Full chain: todo text -> extract display name -> normalize -> stem -> registry."""
        # Step 1: Extract agent display name from todo brackets
        extracted = AgentNameNormalizer.extract_from_todo(todo_text)
        assert extracted is not None, f"extract_from_todo('{todo_text}') returned None"
        assert extracted == expected_display_name, (
            f"extract_from_todo('{todo_text}') returned '{extracted}', "
            f"expected '{expected_display_name}'"
        )

        # Step 2: Convert display name to task format stem
        stem = AgentNameNormalizer.to_task_format(extracted)
        assert stem == expected_stem, (
            f"to_task_format('{extracted}') returned '{stem}', "
            f"expected '{expected_stem}'"
        )

        # Step 3: Verify stem resolves in AGENT_NAME_MAP
        assert stem in AGENT_NAME_MAP, (
            f"Stem '{stem}' (from todo '{todo_text}') not found in AGENT_NAME_MAP"
        )

    def test_all_core_agent_name_map_stems_roundtrip(self) -> None:
        """Every non-legacy AGENT_NAME_MAP stem should roundtrip through the normalizer.

        For each entry in AGENT_NAME_MAP:
          1. Look up the display name from the stem.
          2. Normalize the display name (should be stable).
          3. Convert back to task format and verify it resolves to a valid stem.

        We skip entries whose display name is in ID-style format (e.g. 'ticketing_agent',
        'mpm_agent_manager') and legacy -agent suffix variants, since those are
        backward-compatibility entries, not part of the user-facing delegation chain.

        Known roundtrip failures are documented in KNOWN_ROUNDTRIP_FAILURES and
        tested separately in test_known_roundtrip_failures_are_documented.
        """
        skipped_id_style = []
        skipped_legacy = []
        tested = []

        for stem, display_name in AGENT_NAME_MAP.items():
            # Skip legacy -agent suffix variants (they duplicate canonical stems)
            if stem.endswith("-agent") and stem.replace("-agent", "") in AGENT_NAME_MAP:
                skipped_legacy.append(stem)
                continue

            # Skip entries where display_name is ID-style (contains underscore or
            # matches the stem verbatim, indicating it's not a user-facing name)
            if "_" in display_name or display_name == stem:
                skipped_id_style.append(stem)
                continue

            # Skip known roundtrip failures (tested separately)
            if stem in KNOWN_ROUNDTRIP_FAILURES:
                continue

            tested.append(stem)

            # The display name should normalize to itself
            normalized = AgentNameNormalizer.normalize(display_name)
            assert normalized == display_name, (
                f"AGENT_NAME_MAP['{stem}'] has display name '{display_name}' "
                f"but normalize() returns '{normalized}'. "
                f"If this is expected, add '{stem}' to KNOWN_ROUNDTRIP_FAILURES."
            )

            # Converting the display name to task format should produce a
            # stem that exists in AGENT_NAME_MAP
            roundtrip_stem = AgentNameNormalizer.to_task_format(display_name)
            assert roundtrip_stem in AGENT_NAME_MAP, (
                f"Display name '{display_name}' (from stem '{stem}') "
                f"roundtrips to stem '{roundtrip_stem}' which is not in AGENT_NAME_MAP"
            )

        # Ensure we actually tested a substantial number of entries
        assert len(tested) >= 25, (
            f"Only tested {len(tested)} stems; expected at least 25. "
            f"Skipped ID-style: {skipped_id_style}, legacy: {skipped_legacy}"
        )

    def test_known_roundtrip_failures_are_documented(self) -> None:
        """Verify that KNOWN_ROUNDTRIP_FAILURES contains only entries that actually fail.

        This test ensures:
        1. Every stem in KNOWN_ROUNDTRIP_FAILURES actually fails roundtrip.
        2. No new roundtrip failures exist outside the known set (caught by
           test_all_core_agent_name_map_stems_roundtrip).

        When a failure is fixed, it should be removed from KNOWN_ROUNDTRIP_FAILURES
        so this test fails and alerts the developer.
        """
        for stem in KNOWN_ROUNDTRIP_FAILURES:
            assert stem in AGENT_NAME_MAP, (
                f"KNOWN_ROUNDTRIP_FAILURES contains '{stem}' "
                f"which is not in AGENT_NAME_MAP"
            )

            display_name = AGENT_NAME_MAP[stem]
            normalized = AgentNameNormalizer.normalize(display_name)

            # This entry SHOULD fail -- if it passes, it's been fixed and
            # should be removed from KNOWN_ROUNDTRIP_FAILURES.
            assert normalized != display_name, (
                f"AGENT_NAME_MAP['{stem}'] display name '{display_name}' now "
                f"roundtrips correctly (normalize returns '{normalized}'). "
                f"Remove '{stem}' from KNOWN_ROUNDTRIP_FAILURES."
            )

    def test_from_task_format_reverses_to_task_format(self) -> None:
        """from_task_format should reverse to_task_format for common agents."""
        agent_pairs = [
            ("Research", "research"),
            ("Engineer", "engineer"),
            ("Python Engineer", "python-engineer"),
            ("Version Control", "version-control"),
            ("QA", "qa"),
            ("Local Ops", "local-ops"),
            ("Data Engineer", "data-engineer"),
            ("Security", "security"),
        ]

        for display_name, expected_stem in agent_pairs:
            stem = AgentNameNormalizer.to_task_format(display_name)
            assert stem == expected_stem

            # Reverse: from_task_format should return the display name
            recovered = AgentNameNormalizer.from_task_format(stem)
            assert recovered == display_name, (
                f"from_task_format('{stem}') returned '{recovered}', "
                f"expected '{display_name}'"
            )

    def test_alias_driven_todo_extraction(self) -> None:
        """Aliases used in todo brackets should still resolve through the chain.

        Users might write ``[python]`` instead of ``[Python Engineer]``.
        The system should still resolve this to the correct stem.
        """
        alias_cases = [
            ("[python] Build API", "Python Engineer", "python-engineer"),
            ("[git] Create branch", "Version Control", "version-control"),
            ("[docs] Write guide", "Documentation Agent", "documentation"),
            ("[sec] Run scan", "Security", "security"),
            ("[testing] Run suite", "QA", "qa"),
        ]

        for todo_text, expected_display, expected_stem in alias_cases:
            extracted = AgentNameNormalizer.extract_from_todo(todo_text)
            assert extracted is not None, (
                f"extract_from_todo('{todo_text}') returned None"
            )
            assert extracted == expected_display, (
                f"extract_from_todo('{todo_text}') returned '{extracted}', "
                f"expected '{expected_display}'"
            )

            stem = AgentNameNormalizer.to_task_format(extracted)
            assert stem == expected_stem, (
                f"to_task_format('{extracted}') returned '{stem}', "
                f"expected '{expected_stem}'"
            )
            assert stem in AGENT_NAME_MAP
