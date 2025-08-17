#!/usr/bin/env python3
"""
Validate response file format and structure.
"""

import glob
import json
import os
from datetime import datetime
from pathlib import Path


def validate_response_files(responses_dir):
    """Validate all response files in the directory."""

    responses_dir = Path(responses_dir)
    if not responses_dir.exists():
        print(f"❌ Response directory does not exist: {responses_dir}")
        return False

    # Get all JSON response files
    response_files = list(responses_dir.glob("*.json"))

    if not response_files:
        print(f"❌ No response files found in {responses_dir}")
        return False

    print(f"🔍 Found {len(response_files)} response files to validate")
    print("=" * 60)

    valid_count = 0
    total_count = len(response_files)

    # Required fields for all response files
    required_fields = ["timestamp", "agent", "session_id", "request", "response"]

    for file_path in sorted(response_files):
        print(f"\n📄 Validating: {file_path.name}")

        try:
            # Check if file is valid JSON
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check required fields
            missing_fields = []
            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)

            if missing_fields:
                print(f"  ❌ Missing required fields: {missing_fields}")
                continue

            # Validate field types and content
            issues = []

            # Timestamp validation
            try:
                datetime.fromisoformat(data["timestamp"])
            except ValueError:
                issues.append("Invalid timestamp format")

            # Agent name validation
            if not isinstance(data["agent"], str) or not data["agent"].strip():
                issues.append("Agent name must be non-empty string")

            # Session ID validation
            if (
                not isinstance(data["session_id"], str)
                or not data["session_id"].strip()
            ):
                issues.append("Session ID must be non-empty string")

            # Request validation
            if not isinstance(data["request"], str):
                issues.append("Request must be string")

            # Response validation
            if not isinstance(data["response"], str):
                issues.append("Response must be string")

            # Metadata validation (optional but should be dict if present)
            if "metadata" in data:
                if not isinstance(data["metadata"], dict):
                    issues.append("Metadata must be dictionary")
                else:
                    # Check common metadata fields
                    metadata = data["metadata"]
                    if "timestamp" in metadata:
                        try:
                            datetime.fromisoformat(metadata["timestamp"])
                        except ValueError:
                            issues.append("Invalid metadata timestamp format")

            if issues:
                print(f"  ❌ Issues found: {', '.join(issues)}")
                continue

            # Success validation
            print(f"  ✅ Valid response file")
            print(f"     Agent: {data['agent']}")
            print(f"     Session: {data['session_id']}")
            print(f"     Request length: {len(data['request'])} chars")
            print(f"     Response length: {len(data['response'])} chars")

            if "metadata" in data:
                metadata = data["metadata"]
                print(f"     Metadata keys: {list(metadata.keys())}")
                if "event_type" in metadata:
                    print(f"     Event type: {metadata['event_type']}")

            valid_count += 1

        except json.JSONDecodeError as e:
            print(f"  ❌ Invalid JSON: {e}")
        except Exception as e:
            print(f"  ❌ Error reading file: {e}")

    print("\n" + "=" * 60)
    print(f"📊 Validation Summary:")
    print(f"  Total files: {total_count}")
    print(f"  Valid files: {valid_count}")
    print(f"  Invalid files: {total_count - valid_count}")
    print(f"  Success rate: {(valid_count/total_count)*100:.1f}%")

    return valid_count == total_count


def check_file_naming_convention(responses_dir):
    """Check if files follow the expected naming convention."""

    responses_dir = Path(responses_dir)
    response_files = list(responses_dir.glob("*.json"))

    print(f"\n🏷️  Checking file naming convention...")

    valid_names = 0

    for file_path in response_files:
        name = file_path.name

        # Expected format: YYYYMMDD_HHMMSS-agent-YYYYMMDDTHHMMSS_microseconds.json
        parts = name.replace(".json", "").split("-", 2)

        if len(parts) >= 3:
            session_part = parts[0]  # YYYYMMDD_HHMMSS
            agent_part = parts[1]  # agent name
            timestamp_part = parts[2]  # YYYYMMDDTHHMMSS_microseconds

            # Basic validation
            if (
                len(session_part) == 15
                and session_part[8] == "_"
                and agent_part
                and timestamp_part
            ):
                print(f"  ✅ {name} - Valid naming")
                valid_names += 1
            else:
                print(f"  ❌ {name} - Invalid naming format")
        else:
            print(f"  ❌ {name} - Too few parts in filename")

    print(f"\n  Valid names: {valid_names}/{len(response_files)}")
    return valid_names == len(response_files)


def analyze_agent_distribution(responses_dir):
    """Analyze the distribution of agents in response files."""

    responses_dir = Path(responses_dir)
    response_files = list(responses_dir.glob("*.json"))

    agent_counts = {}
    event_types = {}

    for file_path in response_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            agent = data.get("agent", "unknown")
            agent_counts[agent] = agent_counts.get(agent, 0) + 1

            # Check event type from metadata
            if "metadata" in data and "event_type" in data["metadata"]:
                event_type = data["metadata"]["event_type"]
                event_types[event_type] = event_types.get(event_type, 0) + 1
        except:
            continue

    print(f"\n📈 Agent Distribution:")
    for agent, count in sorted(agent_counts.items()):
        print(f"  {agent}: {count} responses")

    if event_types:
        print(f"\n📋 Event Type Distribution:")
        for event_type, count in sorted(event_types.items()):
            print(f"  {event_type}: {count} events")


if __name__ == "__main__":
    responses_dir = ".claude-mpm/responses"

    print("🧪 Response Logging Format Validation")
    print("=" * 60)

    # Main validation
    format_valid = validate_response_files(responses_dir)

    # File naming validation
    naming_valid = check_file_naming_convention(responses_dir)

    # Agent distribution analysis
    analyze_agent_distribution(responses_dir)

    # Overall result
    print(f"\n🎯 Overall Validation Result:")
    if format_valid and naming_valid:
        print("✅ All validation checks PASSED")
        exit(0)
    else:
        print("❌ Some validation checks FAILED")
        if not format_valid:
            print("  - Response format validation failed")
        if not naming_valid:
            print("  - File naming convention validation failed")
        exit(1)
