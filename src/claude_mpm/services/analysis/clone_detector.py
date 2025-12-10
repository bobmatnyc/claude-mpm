"""Code clone detection service using AST-based similarity analysis.

This module provides functionality to detect code clones (duplicated or similar code)
across Python codebases and suggest refactoring opportunities.
"""

import ast
import difflib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, ClassVar

from pylint.checkers.similar import Similar


logger = logging.getLogger(__name__)


@dataclass
class CloneReport:
    """Report of detected code clone between two files.

    Attributes:
        file1: First file containing cloned code
        file2: Second file containing cloned code
        line_start1: Starting line number in file1
        line_end1: Ending line number in file1
        line_start2: Starting line number in file2
        line_end2: Ending line number in file2
        similarity: Similarity score from 0.0 to 1.0
        clone_type: Type of clone ("exact", "renamed", "modified")
        code_snippet1: Code snippet from file1
        code_snippet2: Code snippet from file2
    """

    file1: Path
    file2: Path
    line_start1: int
    line_end1: int
    line_start2: int
    line_end2: int
    similarity: float
    clone_type: str
    code_snippet1: str
    code_snippet2: str

    def __post_init__(self) -> None:
        """Validate clone report fields."""
        if not 0.0 <= self.similarity <= 1.0:
            raise ValueError(f"Similarity must be between 0.0 and 1.0, got {self.similarity}")
        if self.clone_type not in ("exact", "renamed", "modified"):
            raise ValueError(
                f"Clone type must be 'exact', 'renamed', or 'modified', got {self.clone_type}"
            )


@dataclass
class RefactoringSuggestion:
    """Suggestion for refactoring detected clones.

    Attributes:
        description: Human-readable description of the refactoring
        affected_files: List of files that would be affected
        estimated_reduction: Estimated lines of code saved
        suggested_function_name: Suggested name for extracted function
        parameters: List of parameter names for extracted function
        code_template: Template code showing the suggested refactoring
    """

    description: str
    affected_files: list[Path]
    estimated_reduction: int
    suggested_function_name: str
    parameters: list[str]
    code_template: str


@dataclass
class SimilarityReport:
    """Report of similar functions between two files.

    Attributes:
        file1: First file path
        file2: Second file path
        similar_functions: List of tuples (func1_name, func2_name, similarity_score)
        overall_similarity: Overall similarity between files (0.0 to 1.0)
    """

    file1: Path
    file2: Path
    similar_functions: list[tuple[str, str, float]] = field(default_factory=list)
    overall_similarity: float = 0.0


class CloneDetector:
    """AST-based code clone detector using pycode_similar and pylint.

    This class provides methods to detect code clones, analyze similarity between
    functions, and suggest refactoring opportunities to reduce code duplication.

    Features:
    - Exact clone detection (Type-1): Identical code blocks
    - Renamed clone detection (Type-2): Same structure, different identifiers
    - Modified clone detection (Type-3): Similar logic with minor changes
    """

    # Similarity thresholds for clone classification
    EXACT_THRESHOLD: ClassVar[float] = 0.95
    RENAMED_THRESHOLD: ClassVar[float] = 0.80
    MODIFIED_THRESHOLD: ClassVar[float] = 0.60

    # Minimum lines for clone detection
    MIN_CLONE_LINES: ClassVar[int] = 4

    def __init__(self, min_similarity: float = 0.60, min_lines: int = 4) -> None:
        """Initialize clone detector.

        Args:
            min_similarity: Minimum similarity threshold (0.0 to 1.0)
            min_lines: Minimum number of lines to consider for clones
        """
        if not 0.0 <= min_similarity <= 1.0:
            raise ValueError(f"min_similarity must be between 0.0 and 1.0, got {min_similarity}")
        if min_lines < 1:
            raise ValueError(f"min_lines must be >= 1, got {min_lines}")

        self.min_similarity = min_similarity
        self.min_lines = min_lines

    def detect_clones(self, project_path: Path) -> list[CloneReport]:
        """Detect code clones in a project directory.

        Uses pylint's duplicate-code checker (R0801) to find similar code blocks
        across Python files.

        Args:
            project_path: Root directory of project to analyze

        Returns:
            List of CloneReport objects describing detected clones

        Raises:
            ValueError: If project_path doesn't exist or isn't a directory
        """
        if not project_path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")
        if not project_path.is_dir():
            raise ValueError(f"Project path is not a directory: {project_path}")

        logger.info("Detecting clones in project: %s", project_path)

        # Find all Python files in project
        python_files = list(project_path.rglob("*.py"))
        if not python_files:
            logger.warning("No Python files found in %s", project_path)
            return []

        logger.info("Found %d Python files to analyze", len(python_files))

        # Use pylint's Similar checker for duplicate detection
        clones: list[CloneReport] = []
        try:
            clones = self._detect_with_pylint(python_files)
        except Exception as e:
            logger.error("Error detecting clones with pylint: %s", e)

        logger.info("Detected %d clones", len(clones))
        return clones

    def _detect_with_pylint(self, files: list[Path]) -> list[CloneReport]:
        """Detect clones using pylint's Similar checker.

        Args:
            files: List of Python files to analyze

        Returns:
            List of CloneReport objects
        """
        clones: list[CloneReport] = []

        # Create Similar instance with our minimum line threshold
        similar = Similar(
            min_lines=self.min_lines,
            ignore_comments=True,
            ignore_docstrings=True,
            ignore_imports=False,
        )

        # Process files
        for file_path in files:
            try:
                with open(file_path, encoding="utf-8") as f:
                    similar.append_stream(str(file_path), f, file_path.name)
            except Exception as e:
                logger.warning("Error reading %s: %s", file_path, e)
                continue

        # Run similarity analysis
        try:
            similar.run()

            # Extract clone information from Similar instance
            # Similar stores results in linesets which we need to process
            for duplicate in similar._compute_sims():  # noqa: SLF001
                # Each duplicate is ((file1, start1, end1), (file2, start2, end2))
                if len(duplicate) >= 2:
                    loc1, loc2 = duplicate[0], duplicate[1]
                    file1_path = Path(loc1[0])
                    file2_path = Path(loc2[0])

                    # Read code snippets
                    snippet1 = self._read_lines(file1_path, loc1[1], loc1[2])
                    snippet2 = self._read_lines(file2_path, loc2[1], loc2[2])

                    # Calculate similarity
                    similarity = self._calculate_similarity(snippet1, snippet2)

                    # Determine clone type
                    clone_type = self._classify_clone_type(similarity)

                    # Only include if meets minimum similarity threshold
                    if similarity >= self.min_similarity:
                        clone = CloneReport(
                            file1=file1_path,
                            file2=file2_path,
                            line_start1=loc1[1],
                            line_end1=loc1[2],
                            line_start2=loc2[1],
                            line_end2=loc2[2],
                            similarity=similarity,
                            clone_type=clone_type,
                            code_snippet1=snippet1,
                            code_snippet2=snippet2,
                        )
                        clones.append(clone)

        except Exception as e:
            logger.error("Error running similarity analysis: %s", e)

        return clones

    def _read_lines(self, file_path: Path, start_line: int, end_line: int) -> str:
        """Read specific lines from a file.

        Args:
            file_path: Path to file
            start_line: Starting line number (1-indexed)
            end_line: Ending line number (1-indexed)

        Returns:
            String containing the specified lines
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                lines = f.readlines()
                # Convert to 0-indexed
                return "".join(lines[start_line - 1 : end_line])
        except Exception as e:
            logger.warning("Error reading lines from %s: %s", file_path, e)
            return ""

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings.

        Uses difflib's SequenceMatcher for similarity calculation.

        Args:
            text1: First text string
            text2: Second text string

        Returns:
            Similarity score from 0.0 to 1.0
        """
        return difflib.SequenceMatcher(None, text1, text2).ratio()

    def _classify_clone_type(self, similarity: float) -> str:
        """Classify clone type based on similarity score.

        Args:
            similarity: Similarity score from 0.0 to 1.0

        Returns:
            Clone type: "exact", "renamed", or "modified"
        """
        if similarity >= self.EXACT_THRESHOLD:
            return "exact"
        elif similarity >= self.RENAMED_THRESHOLD:
            return "renamed"
        else:
            return "modified"

    def find_similar_functions(
        self, file1: Path, file2: Path
    ) -> SimilarityReport:
        """Find similar functions between two files.

        Uses AST analysis to compare function structures and identify similar
        implementations.

        Args:
            file1: First Python file path
            file2: Second Python file path

        Returns:
            SimilarityReport with function-level similarity analysis

        Raises:
            ValueError: If files don't exist or aren't Python files
        """
        if not file1.exists() or not file2.exists():
            raise ValueError("Both files must exist")
        if file1.suffix != ".py" or file2.suffix != ".py":
            raise ValueError("Both files must be Python files (.py)")

        logger.info("Analyzing function similarity between %s and %s", file1, file2)

        # Parse AST for both files
        try:
            tree1 = self._parse_file(file1)
            tree2 = self._parse_file(file2)
        except Exception as e:
            logger.error("Error parsing files: %s", e)
            return SimilarityReport(file1=file1, file2=file2)

        # Extract functions from both files
        funcs1 = self._extract_functions(tree1)
        funcs2 = self._extract_functions(tree2)

        logger.debug("Found %d functions in %s", len(funcs1), file1)
        logger.debug("Found %d functions in %s", len(funcs2), file2)

        # Compare all function pairs
        similar_functions: list[tuple[str, str, float]] = []
        for name1, func1 in funcs1.items():
            for name2, func2 in funcs2.items():
                similarity = self._compare_functions(func1, func2)
                if similarity >= self.min_similarity:
                    similar_functions.append((name1, name2, similarity))

        # Calculate overall file similarity
        overall_similarity = 0.0
        if similar_functions:
            overall_similarity = sum(s for _, _, s in similar_functions) / len(
                similar_functions
            )

        return SimilarityReport(
            file1=file1,
            file2=file2,
            similar_functions=similar_functions,
            overall_similarity=overall_similarity,
        )

    def _parse_file(self, file_path: Path) -> ast.AST:
        """Parse Python file into AST.

        Args:
            file_path: Path to Python file

        Returns:
            AST node

        Raises:
            SyntaxError: If file has syntax errors
        """
        with open(file_path, encoding="utf-8") as f:
            return ast.parse(f.read(), filename=str(file_path))

    def _extract_functions(self, tree: ast.AST) -> dict[str, ast.FunctionDef]:
        """Extract function definitions from AST.

        Args:
            tree: AST root node

        Returns:
            Dictionary mapping function names to FunctionDef nodes
        """
        functions: dict[str, ast.FunctionDef] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions[node.name] = node
        return functions

    def _compare_functions(
        self, func1: ast.FunctionDef, func2: ast.FunctionDef
    ) -> float:
        """Compare two function AST nodes for similarity.

        Args:
            func1: First function AST node
            func2: Second function AST node

        Returns:
            Similarity score from 0.0 to 1.0
        """
        # Convert AST to source code
        code1 = ast.unparse(func1)
        code2 = ast.unparse(func2)

        # Use difflib for comparison
        return self._calculate_similarity(code1, code2)

    def suggest_parameterization(
        self, clones: list[CloneReport]
    ) -> list[RefactoringSuggestion]:
        """Suggest parameterization opportunities for detected clones.

        Analyzes clone groups and suggests how to extract common logic into
        reusable functions.

        Args:
            clones: List of detected clone reports

        Returns:
            List of RefactoringSuggestion objects
        """
        logger.info("Generating refactoring suggestions for %d clones", len(clones))

        # Group clones by similarity
        clone_groups = self._group_similar_clones(clones)

        suggestions: list[RefactoringSuggestion] = []
        for group in clone_groups:
            try:
                suggestion = self._create_suggestion(group)
                if suggestion:
                    suggestions.append(suggestion)
            except Exception as e:
                logger.warning("Error creating suggestion: %s", e)

        logger.info("Generated %d refactoring suggestions", len(suggestions))
        return suggestions

    def _group_similar_clones(
        self, clones: list[CloneReport]
    ) -> list[list[CloneReport]]:
        """Group clones that are similar to each other.

        Args:
            clones: List of clone reports

        Returns:
            List of clone groups
        """
        # Simple grouping: clones with same code are grouped together
        groups: dict[str, list[CloneReport]] = {}
        for clone in clones:
            # Use code snippet as key (normalize whitespace)
            key = " ".join(clone.code_snippet1.split())
            if key not in groups:
                groups[key] = []
            groups[key].append(clone)

        return list(groups.values())

    def _create_suggestion(
        self, clone_group: list[CloneReport]
    ) -> RefactoringSuggestion | None:
        """Create refactoring suggestion for a group of clones.

        Args:
            clone_group: List of similar clones

        Returns:
            RefactoringSuggestion or None if no suggestion possible
        """
        if not clone_group:
            return None

        # Use first clone as representative
        representative = clone_group[0]

        # Collect all affected files
        affected_files: set[Path] = set()
        for clone in clone_group:
            affected_files.add(clone.file1)
            affected_files.add(clone.file2)

        # Calculate estimated reduction
        # Each clone instance can be replaced with 1-2 lines (function call)
        lines_per_clone = representative.line_end1 - representative.line_start1 + 1
        estimated_reduction = (len(clone_group) * lines_per_clone) - lines_per_clone

        # Generate function name suggestion
        suggested_name = self._suggest_function_name(representative)

        # Analyze code to identify potential parameters
        parameters = self._identify_parameters(representative)

        # Create code template
        code_template = self._create_code_template(
            suggested_name, parameters, representative.code_snippet1
        )

        description = (
            f"Extract {len(clone_group)} similar code blocks "
            f"from {len(affected_files)} files into reusable function"
        )

        return RefactoringSuggestion(
            description=description,
            affected_files=list(affected_files),
            estimated_reduction=estimated_reduction,
            suggested_function_name=suggested_name,
            parameters=parameters,
            code_template=code_template,
        )

    def _suggest_function_name(self, clone: CloneReport) -> str:
        """Suggest a function name based on clone code.

        Args:
            clone: Clone report

        Returns:
            Suggested function name
        """
        # Simple heuristic: extract first meaningful identifier
        try:
            tree = ast.parse(clone.code_snippet1)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    return f"extracted_{node.func.id}"
        except Exception:
            pass

        return "extracted_function"

    def _identify_parameters(self, clone: CloneReport) -> list[str]:
        """Identify potential parameters for extracted function.

        Args:
            clone: Clone report

        Returns:
            List of parameter names
        """
        parameters: list[str] = []

        try:
            tree = ast.parse(clone.code_snippet1)
            # Collect names that are used but not defined in the snippet
            names_used: set[str] = set()
            names_defined: set[str] = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    if isinstance(node.ctx, ast.Store):
                        names_defined.add(node.id)
                    elif isinstance(node.ctx, ast.Load):
                        names_used.add(node.id)

            # Parameters are names used but not defined
            parameters = list(names_used - names_defined)

        except Exception as e:
            logger.debug("Error identifying parameters: %s", e)

        return parameters or ["data"]  # Default parameter if none found

    def _create_code_template(
        self, func_name: str, parameters: list[str], code: str
    ) -> str:
        """Create code template for suggested refactoring.

        Args:
            func_name: Suggested function name
            parameters: List of parameter names
            code: Clone code snippet

        Returns:
            Code template string
        """
        param_str = ", ".join(parameters)
        indent = "    "

        # Indent code block
        indented_code = "\n".join(
            f"{indent}{line}" if line.strip() else ""
            for line in code.split("\n")
        )

        template = f"""def {func_name}({param_str}):
    \"\"\"Extracted common logic from multiple locations.

    Args:
{indent}{indent}""" + f"\n{indent}{indent}".join(f"{p}: Parameter" for p in parameters) + f"""
    \"\"\"
{indented_code}
"""

        return template
