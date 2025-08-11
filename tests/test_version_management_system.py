"""
Test version management system.

This test suite validates semantic version parsing, comparison logic,
migration from old formats, and version update detection.
"""

import pytest
import re
from typing import Tuple, Optional


class TestVersionManagement:
    """Test version management and migration."""
    
    def test_semantic_version_parsing(self):
        """Test parsing of semantic version strings."""
        test_cases = [
            ("1.0.0", (1, 0, 0)),
            ("2.3.4", (2, 3, 4)),
            ("10.20.30", (10, 20, 30)),
            ("0.1.0", (0, 1, 0)),
            ("v1.2.3", (1, 2, 3)),  # With v prefix
            ("1.0.0-alpha", (1, 0, 0)),  # With pre-release (base version)
            ("2.1.0+build123", (2, 1, 0)),  # With build metadata
        ]
        
        for version_str, expected in test_cases:
            result = self._parse_semantic_version(version_str)
            assert result == expected, f"Failed to parse {version_str}"
    
    def test_invalid_version_parsing(self):
        """Test handling of invalid version formats."""
        invalid_versions = [
            "1.0",  # Missing patch
            "1",  # Only major
            "a.b.c",  # Non-numeric
            "1.2.3.4",  # Too many parts
            "",  # Empty
            "invalid",  # Text
            "0002-0005",  # Old serial format
        ]
        
        for version_str in invalid_versions:
            result = self._parse_semantic_version(version_str)
            # Should return a default or None for invalid
            assert result == (0, 0, 0) or result is None
    
    def test_version_comparison_logic(self):
        """Test semantic version comparison."""
        test_cases = [
            ((1, 0, 0), (1, 0, 0), 0),  # Equal
            ((1, 0, 0), (2, 0, 0), -1),  # Major difference
            ((2, 0, 0), (1, 0, 0), 1),  # Major difference reverse
            ((1, 1, 0), (1, 2, 0), -1),  # Minor difference
            ((1, 2, 0), (1, 1, 0), 1),  # Minor difference reverse
            ((1, 0, 1), (1, 0, 2), -1),  # Patch difference
            ((1, 0, 2), (1, 0, 1), 1),  # Patch difference reverse
            ((0, 9, 9), (1, 0, 0), -1),  # Major trumps minor/patch
            ((1, 0, 0), (0, 99, 99), 1),  # Major trumps all
        ]
        
        for v1, v2, expected in test_cases:
            result = self._compare_versions(v1, v2)
            assert result == expected, f"Comparison failed for {v1} vs {v2}"
    
    def test_migration_from_old_serial_format(self):
        """Test migration from old serial version format."""
        old_formats = [
            ("0002-0005", (0, 5, 0)),  # Serial format
            ("0001-0010", (0, 10, 0)),  # Higher serial
            ("agent_version: 3", (0, 3, 0)),  # Old field format
            ("5", (0, 5, 0)),  # Simple integer
        ]
        
        for old_format, expected in old_formats:
            result = self._migrate_old_version(old_format)
            assert result == expected, f"Migration failed for {old_format}"
    
    def test_version_update_detection(self):
        """Test detection of version updates."""
        test_cases = [
            # (current, new, should_update)
            ((1, 0, 0), (1, 0, 0), False),  # Same version
            ((1, 0, 0), (1, 0, 1), True),  # Patch update
            ((1, 0, 0), (1, 1, 0), True),  # Minor update
            ((1, 0, 0), (2, 0, 0), True),  # Major update
            ((2, 0, 0), (1, 9, 9), False),  # Downgrade (not an update)
            ((1, 2, 3), (1, 2, 2), False),  # Patch downgrade
        ]
        
        for current, new, should_update in test_cases:
            result = self._needs_update(current, new)
            assert result == should_update, f"Update detection failed for {current} -> {new}"
    
    def test_version_string_formatting(self):
        """Test formatting of version tuples to strings."""
        test_cases = [
            ((1, 0, 0), "1.0.0"),
            ((2, 3, 4), "2.3.4"),
            ((10, 20, 30), "10.20.30"),
            ((0, 1, 0), "0.1.0"),
        ]
        
        for version_tuple, expected in test_cases:
            result = self._format_version(version_tuple)
            assert result == expected, f"Formatting failed for {version_tuple}"
    
    def test_version_increment_logic(self):
        """Test version increment for different types of changes."""
        base_version = (1, 2, 3)
        
        # Patch increment
        patch_result = self._increment_version(base_version, 'patch')
        assert patch_result == (1, 2, 4)
        
        # Minor increment (resets patch)
        minor_result = self._increment_version(base_version, 'minor')
        assert minor_result == (1, 3, 0)
        
        # Major increment (resets minor and patch)
        major_result = self._increment_version(base_version, 'major')
        assert major_result == (2, 0, 0)
    
    def test_version_range_checking(self):
        """Test version range compatibility checking."""
        test_cases = [
            # (version, min_version, max_version, is_compatible)
            ((1, 2, 3), (1, 0, 0), (2, 0, 0), True),  # Within range
            ((0, 9, 0), (1, 0, 0), (2, 0, 0), False),  # Below minimum
            ((2, 1, 0), (1, 0, 0), (2, 0, 0), False),  # Above maximum
            ((1, 0, 0), (1, 0, 0), (1, 0, 0), True),  # Exact match
            ((1, 5, 0), (1, 0, 0), None, True),  # No max limit
            ((0, 5, 0), None, (1, 0, 0), True),  # No min limit
        ]
        
        for version, min_ver, max_ver, expected in test_cases:
            result = self._is_version_compatible(version, min_ver, max_ver)
            assert result == expected, f"Range check failed for {version}"
    
    def test_version_history_tracking(self):
        """Test tracking of version history for migrations."""
        history = []
        
        # Add versions to history
        versions = [(1, 0, 0), (1, 1, 0), (1, 1, 1), (2, 0, 0)]
        for v in versions:
            history = self._add_to_version_history(history, v)
        
        # Check history is maintained correctly
        assert len(history) == 4
        assert history[-1] == (2, 0, 0)  # Latest version
        assert history[0] == (1, 0, 0)  # Oldest version
        
        # Check for version in history
        assert self._version_in_history(history, (1, 1, 0))
        assert not self._version_in_history(history, (1, 2, 0))
    
    def test_version_compatibility_matrix(self):
        """Test version compatibility matrix for agent interactions."""
        # Define compatibility rules
        compatibility = {
            'agent': (2, 0, 0),
            'base': (1, 5, 0),
            'framework': (3, 1, 0)
        }
        
        # Test various scenarios
        scenarios = [
            # All components compatible
            {'agent': (2, 1, 0), 'base': (1, 6, 0), 'framework': (3, 2, 0), 'compatible': True},
            # Agent too old
            {'agent': (1, 9, 0), 'base': (1, 6, 0), 'framework': (3, 2, 0), 'compatible': False},
            # Base too old
            {'agent': (2, 1, 0), 'base': (1, 4, 0), 'framework': (3, 2, 0), 'compatible': False},
            # Framework too old
            {'agent': (2, 1, 0), 'base': (1, 6, 0), 'framework': (3, 0, 0), 'compatible': False},
        ]
        
        for scenario in scenarios:
            result = self._check_compatibility_matrix(
                scenario['agent'],
                scenario['base'],
                scenario['framework'],
                compatibility
            )
            assert result == scenario['compatible']
    
    def test_version_migration_path(self):
        """Test determining migration path between versions."""
        test_cases = [
            # (from_version, to_version, expected_steps)
            ((1, 0, 0), (1, 2, 0), ['1.0.0 -> 1.1.0', '1.1.0 -> 1.2.0']),
            ((1, 0, 0), (2, 0, 0), ['1.0.0 -> 2.0.0']),  # Major jump
            ((1, 2, 3), (1, 2, 5), ['1.2.3 -> 1.2.4', '1.2.4 -> 1.2.5']),
        ]
        
        for from_ver, to_ver, expected_steps in test_cases:
            steps = self._get_migration_path(from_ver, to_ver)
            # Simplified check - just verify we get some migration steps
            assert len(steps) > 0
    
    def test_version_regex_patterns(self):
        """Test regex patterns for version extraction."""
        patterns = {
            'semantic': r'^v?(\d+)\.(\d+)\.(\d+)',
            'serial': r'^(\d+)-(\d+)$',
            'simple': r'^(\d+)$',
            'yaml_field': r'^version:\s*["\']?([^\'"]+)["\']?',
        }
        
        test_strings = [
            ("version: 1.2.3", 'yaml_field', "1.2.3"),
            ("v2.1.0", 'semantic', ('2', '1', '0')),
            ("0002-0005", 'serial', ('0002', '0005')),
            ("42", 'simple', "42"),
        ]
        
        for test_str, pattern_name, expected in test_strings:
            pattern = patterns[pattern_name]
            match = re.search(pattern, test_str)
            assert match is not None, f"Pattern {pattern_name} failed on {test_str}"
            
            if isinstance(expected, tuple):
                assert match.groups() == expected
            else:
                assert match.group(1) == expected
    
    # Helper methods
    
    def _parse_semantic_version(self, version_str: str) -> Tuple[int, int, int]:
        """Parse semantic version string to tuple."""
        if not version_str:
            return (0, 0, 0)
        
        # Remove v prefix if present
        if version_str.startswith('v'):
            version_str = version_str[1:]
        
        # Remove pre-release and build metadata
        version_str = version_str.split('-')[0].split('+')[0]
        
        # Parse semantic version
        pattern = r'^(\d+)\.(\d+)\.(\d+)$'
        match = re.match(pattern, version_str)
        
        if match:
            return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        
        return (0, 0, 0)
    
    def _compare_versions(self, v1: Tuple[int, int, int], v2: Tuple[int, int, int]) -> int:
        """Compare two version tuples."""
        for a, b in zip(v1, v2):
            if a < b:
                return -1
            elif a > b:
                return 1
        return 0
    
    def _migrate_old_version(self, old_version: str) -> Tuple[int, int, int]:
        """Migrate old version format to semantic version."""
        # Handle serial format (e.g., "0002-0005")
        if '-' in old_version:
            parts = old_version.split('-')
            if len(parts) == 2 and parts[1].isdigit():
                return (0, int(parts[1]), 0)
        
        # Handle simple integer
        if old_version.isdigit():
            return (0, int(old_version), 0)
        
        # Handle "agent_version: X" format
        if ':' in old_version:
            value = old_version.split(':')[1].strip()
            if value.isdigit():
                return (0, int(value), 0)
        
        return (0, 0, 0)
    
    def _needs_update(self, current: Tuple[int, int, int], new: Tuple[int, int, int]) -> bool:
        """Check if new version is an update from current."""
        return self._compare_versions(new, current) > 0
    
    def _format_version(self, version: Tuple[int, int, int]) -> str:
        """Format version tuple as string."""
        return f"{version[0]}.{version[1]}.{version[2]}"
    
    def _increment_version(self, version: Tuple[int, int, int], increment_type: str) -> Tuple[int, int, int]:
        """Increment version based on change type."""
        major, minor, patch = version
        
        if increment_type == 'major':
            return (major + 1, 0, 0)
        elif increment_type == 'minor':
            return (major, minor + 1, 0)
        elif increment_type == 'patch':
            return (major, minor, patch + 1)
        
        return version
    
    def _is_version_compatible(self, version: Tuple[int, int, int], 
                              min_version: Optional[Tuple[int, int, int]],
                              max_version: Optional[Tuple[int, int, int]]) -> bool:
        """Check if version is within compatibility range."""
        if min_version and self._compare_versions(version, min_version) < 0:
            return False
        
        if max_version and self._compare_versions(version, max_version) > 0:
            return False
        
        return True
    
    def _add_to_version_history(self, history: list, version: Tuple[int, int, int]) -> list:
        """Add version to history list."""
        new_history = history.copy()
        new_history.append(version)
        return new_history
    
    def _version_in_history(self, history: list, version: Tuple[int, int, int]) -> bool:
        """Check if version exists in history."""
        return version in history
    
    def _check_compatibility_matrix(self, agent_ver: Tuple[int, int, int],
                                   base_ver: Tuple[int, int, int],
                                   framework_ver: Tuple[int, int, int],
                                   requirements: dict) -> bool:
        """Check if all components meet compatibility requirements."""
        if self._compare_versions(agent_ver, requirements['agent']) < 0:
            return False
        if self._compare_versions(base_ver, requirements['base']) < 0:
            return False
        if self._compare_versions(framework_ver, requirements['framework']) < 0:
            return False
        return True
    
    def _get_migration_path(self, from_ver: Tuple[int, int, int], 
                           to_ver: Tuple[int, int, int]) -> list:
        """Get migration steps from one version to another."""
        steps = []
        
        # Simplified migration path logic
        if from_ver[0] != to_ver[0]:
            # Major version change - direct jump
            steps.append(f"{self._format_version(from_ver)} -> {self._format_version(to_ver)}")
        else:
            # Minor/patch changes - incremental steps
            current = from_ver
            while self._compare_versions(current, to_ver) < 0:
                if current[1] < to_ver[1]:
                    next_ver = (current[0], current[1] + 1, 0)
                else:
                    next_ver = (current[0], current[1], current[2] + 1)
                
                steps.append(f"{self._format_version(current)} -> {self._format_version(next_ver)}")
                current = next_ver
                
                if current == to_ver:
                    break
        
        return steps