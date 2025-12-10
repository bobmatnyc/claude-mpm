#!/usr/bin/env python3
"""Demo script for multi-language clone detection.

This script demonstrates the extended CloneDetector capabilities for detecting
code clones across multiple programming languages using tree-sitter.
"""

import tempfile
from pathlib import Path

from claude_mpm.services.analysis import CloneDetector


def demo_javascript_clone_detection():
    """Demonstrate JavaScript clone detection."""
    print("=== JavaScript Clone Detection Demo ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        # Create two JavaScript files with similar functions
        file1 = project / "user_service.js"
        file1.write_text(
            """
function processUser(userId) {
    const user = fetchUser(userId);
    if (!user) {
        throw new Error("User not found");
    }
    validateUser(user);
    updateTimestamp(user);
    saveUser(user);
    return user;
}

function deleteUser(userId) {
    const user = fetchUser(userId);
    markAsDeleted(user);
    saveUser(user);
}
"""
        )

        file2 = project / "admin_service.js"
        file2.write_text(
            """
function processAdmin(adminId) {
    const admin = fetchAdmin(adminId);
    if (!admin) {
        throw new Error("Admin not found");
    }
    validateAdmin(admin);
    updateTimestamp(admin);
    saveAdmin(admin);
    return admin;
}

function deleteAdmin(adminId) {
    const admin = fetchAdmin(adminId);
    markAsDeleted(admin);
    saveAdmin(admin);
}
"""
        )

        detector = CloneDetector(min_similarity=0.70, min_lines=4)

        # Detect clones across all JavaScript files
        print(f"Analyzing project: {project}")
        clones = detector.detect_clones(project, languages=["javascript"])

        print(f"\nFound {len(clones)} clones:\n")
        for i, clone in enumerate(clones, 1):
            print(f"Clone {i}:")
            print(f"  File 1: {clone.file1.name} (lines {clone.line_start1}-{clone.line_end1})")
            print(f"  File 2: {clone.file2.name} (lines {clone.line_start2}-{clone.line_end2})")
            print(f"  Similarity: {clone.similarity:.2%}")
            print(f"  Type: {clone.clone_type}")
            print()

        # Compare specific files
        print("\nComparing specific files:")
        report = detector.find_similar_functions(file1, file2)
        print(f"Overall similarity: {report.overall_similarity:.2%}")
        print(f"Similar function pairs: {len(report.similar_functions)}")


def demo_typescript_clone_detection():
    """Demonstrate TypeScript clone detection."""
    print("\n=== TypeScript Clone Detection Demo ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        # Create TypeScript files with similar functions
        file1 = project / "math_utils.ts"
        file1.write_text(
            """
function add(a: number, b: number): number {
    return a + b;
}

function subtract(a: number, b: number): number {
    return a - b;
}

function multiply(a: number, b: number): number {
    return a * b;
}
"""
        )

        file2 = project / "calculator.ts"
        file2.write_text(
            """
function sum(x: number, y: number): number {
    return x + y;
}

function difference(x: number, y: number): number {
    return x - y;
}

function product(x: number, y: number): number {
    return x * y;
}
"""
        )

        detector = CloneDetector(min_similarity=0.70, min_lines=2)

        print(f"Analyzing project: {project}")
        clones = detector.detect_clones(project, languages=["typescript"])

        print(f"\nFound {len(clones)} clones:\n")
        for i, clone in enumerate(clones, 1):
            print(f"Clone {i}:")
            print(f"  File 1: {clone.file1.name} (lines {clone.line_start1}-{clone.line_end1})")
            print(f"  File 2: {clone.file2.name} (lines {clone.line_start2}-{clone.line_end2})")
            print(f"  Similarity: {clone.similarity:.2%}")
            print(f"  Type: {clone.clone_type}")
            print()


def demo_multi_language_project():
    """Demonstrate detection across multiple languages in one project."""
    print("\n=== Multi-Language Project Demo ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        # Create files in different languages
        (project / "utils.py").write_text("def process_data(data): return data")
        (project / "utils.js").write_text("function processData(data) { return data; }")
        (project / "utils.ts").write_text("function processData(data: any): any { return data; }")

        detector = CloneDetector(min_similarity=0.60)

        print(f"Analyzing project: {project}")
        print("\nSupported languages in project:")

        for lang in ["python", "javascript", "typescript"]:
            clones = detector.detect_clones(project, languages=[lang])
            print(f"  {lang.capitalize()}: {len(clones)} clones detected")


def main():
    """Run all demos."""
    detector = CloneDetector()

    print("CloneDetector Multi-Language Support")
    print("=" * 50)
    print(f"\nInitialized parsers for: {len(detector._parsers)} languages")
    print(f"Available languages: {', '.join(sorted(detector._parsers.keys()))}")
    print()

    # Only run demos if tree-sitter parsers are available
    if "javascript" in detector._parsers:
        demo_javascript_clone_detection()
    else:
        print("Skipping JavaScript demo (parser not available)\n")

    if "typescript" in detector._parsers:
        demo_typescript_clone_detection()
    else:
        print("Skipping TypeScript demo (parser not available)\n")

    demo_multi_language_project()


if __name__ == "__main__":
    main()
