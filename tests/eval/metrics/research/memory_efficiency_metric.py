"""
Memory Efficiency Metric for Research Agent Testing.

This metric evaluates Research Agent compliance with memory efficiency protocols:
- File size checking before reading
- Summarizer usage for large files (>20KB)
- File limit compliance (3-5 files max)
- Strategic sampling (100-200 line excerpts)
- No brute force searches

Scoring Algorithm (weighted):
1. File Size Check (25%): Detects size checking patterns before reads
2. Summarizer Usage (25%): Uses document_summarizer for large files
3. File Limit Compliance (20%): Reads 3-5 files max per research task
4. Strategic Sampling (20%): Reads 100-200 line samples per file
5. No Brute Force (10%): Avoids exhaustive searches, uses targeted discovery

Threshold: 0.9 (90% compliance required)

Example:
    metric = MemoryEfficiencyMetric(threshold=0.9)
    test_case = LLMTestCase(
        input="Research the authentication implementation",
        actual_output='''First checking file size... auth.py is 45KB.
        Using document_summarizer for large file analysis...'''
    )
    metric.measure(test_case)
    print(f"Score: {metric.score}, Passed: {metric.is_successful()}")
"""

import re
from typing import List, Optional, Set, Tuple

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class MemoryEfficiencyMetric(BaseMetric):
    """
    DeepEval metric for Research Agent memory efficiency protocol compliance.

    Evaluates:
    1. File size checking before reading large files
    2. Summarizer usage for files >20KB
    3. File limit compliance (3-5 files max per task)
    4. Strategic sampling (100-200 line excerpts per file)
    5. No brute force exhaustive searches

    Scoring:
    - 1.0: Perfect compliance (all efficiency protocols followed)
    - 0.9-0.99: Minor efficiency issues
    - 0.7-0.89: Some protocols violated
    - 0.0-0.69: Major violations (brute force, no size checks, too many files)
    """

    # File size check patterns
    SIZE_CHECK_PATTERNS: List[str] = [
        r'file\s+size\s*[:\-]?\s*\d+',
        r'(\d+)\s*(KB|MB|bytes)',
        r'checking\s+size',
        r'size\s+check',
        r'file\s+is\s+\d+',
        r'(\d+)\s*KB\s+file',
        r'large\s+file.*\d+\s*KB'
    ]

    # Summarizer usage patterns
    SUMMARIZER_PATTERNS: List[str] = [
        r'document_summarizer',
        r'summariz(?:e|ing|ed)',
        r'summary\s+of\s+file',
        r'using\s+summarizer',
        r'summarization\s+tool'
    ]

    # File read detection (Read tool usage)
    # Matches patterns like "Reading auth.py", "read config.py", "Read `validators.py`"
    FILE_READ_PATTERN = r'(?:Read|read|reading)\s+[`\']?([a-zA-Z0-9_/\-\.]+\.[a-z]+)'

    # Strategic sampling patterns
    SAMPLING_PATTERNS: List[str] = [
        r'lines?\s+(\d+)\s*[-–to]+\s*(\d+)',
        r'sampling',
        r'excerpt',
        r'first\s+\d+\s+lines',
        r'last\s+\d+\s+lines',
        r'lines?\s+\d+\s*-\s*\d+',
        r'reading\s+\d+\s+lines',
        r'100[-\s]200\s+line'
    ]

    # Brute force anti-patterns
    # These indicate exhaustive, inefficient searches
    BRUTE_FORCE_PATTERNS: List[str] = [
        r'\bread(?:ing)?\s+all\s+files\b',
        r'\bscan(?:ning)?\s+entire\s+codebase\b',
        r'\bcheck(?:ing)?\s+every\s+file\b',
        r'\bexhaustive\s+search\b',
        r'\bscan(?:ning)?\s+all\s+files\b',
        r'\biterat(?:e|ing)\s+through\s+all\b'
    ]

    # Negation patterns (good - these AVOID brute force)
    BRUTE_FORCE_NEGATIONS: List[str] = [
        r'\bavoid(?:s|ing)?\s+.*(?:all\s+files|entire\s+codebase|every\s+file)',
        r'\bwithout\s+.*(?:all\s+files|entire\s+codebase|every\s+file)',
        r'\bnot\s+.*(?:all\s+files|entire\s+codebase|every\s+file)'
    ]

    # Targeted discovery patterns (positive indicators)
    TARGETED_DISCOVERY_PATTERNS: List[str] = [
        r'grep',
        r'glob',
        r'search\s+for',
        r'find\s+files',
        r'locate',
        r'filter',
        r'pattern\s+match'
    ]

    # Large file threshold (in KB)
    LARGE_FILE_THRESHOLD = 20

    # File limit range
    MIN_FILE_LIMIT = 3
    MAX_FILE_LIMIT = 5

    # Strategic sampling range (lines per file)
    MIN_SAMPLE_SIZE = 100
    MAX_SAMPLE_SIZE = 200

    def __init__(self, threshold: float = 0.9):
        """
        Initialize MemoryEfficiencyMetric.

        Args:
            threshold: Minimum score to pass (default: 0.9 for 90% compliance)
        """
        self.threshold = threshold
        self._score: Optional[float] = None
        self._reason: Optional[str] = None
        self._success: Optional[bool] = None

    @property
    def __name__(self) -> str:
        return "Memory Efficiency"

    @property
    def score(self) -> Optional[float]:
        """Get the computed score."""
        return self._score

    @property
    def reason(self) -> Optional[str]:
        """Get the reason for the score."""
        return self._reason

    def is_successful(self) -> bool:
        """Check if metric passes threshold (with epsilon for floating-point precision)."""
        if self._success is None:
            return False
        return self._success

    def measure(self, test_case: LLMTestCase) -> float:
        """
        Measure memory efficiency compliance score.

        Args:
            test_case: DeepEval test case with input and actual_output

        Returns:
            Score from 0.0 to 1.0
        """
        output = test_case.actual_output

        # Calculate component scores
        size_check_score = self._score_file_size_check(output)
        summarizer_score = self._score_summarizer_usage(output)
        file_limit_score = self._score_file_limit_compliance(output)
        sampling_score = self._score_strategic_sampling(output)
        brute_force_score = self._score_no_brute_force(output)

        # Weighted average
        final_score = (
            size_check_score * 0.25 +
            summarizer_score * 0.25 +
            file_limit_score * 0.20 +
            sampling_score * 0.20 +
            brute_force_score * 0.10
        )

        # Store results
        self._score = final_score
        self._reason = self._generate_reason(
            size_check_score,
            summarizer_score,
            file_limit_score,
            sampling_score,
            brute_force_score,
            output
        )
        epsilon = 1e-9
        self._success = final_score >= (self.threshold - epsilon)

        return final_score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        """Async version of measure (delegates to sync)."""
        return self.measure(test_case)

    # ========================================================================
    # COMPONENT SCORING METHODS
    # ========================================================================

    def _score_file_size_check(self, output: str) -> float:
        """
        Score file size checking compliance (25% weight).

        Checks:
        - Detects patterns like "checking file size", "file is X KB/MB"
        - Penalizes reading large files without size check
        - Rewards explicit size checking before reads

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        output_lower = output.lower()

        # Check for size check patterns
        has_size_check = any(
            re.search(pattern, output, re.IGNORECASE)
            for pattern in self.SIZE_CHECK_PATTERNS
        )

        # Check for file reads
        file_reads = re.findall(self.FILE_READ_PATTERN, output, re.IGNORECASE)
        has_file_reads = len(file_reads) > 0

        # Scoring logic
        if has_size_check:
            # Perfect score if size checking detected
            return 1.0
        elif has_file_reads:
            # Penalize if files read without size check
            return 0.3
        else:
            # No file reads detected, give neutral score
            return 0.7

    def _score_summarizer_usage(self, output: str) -> float:
        """
        Score summarizer usage for large files (25% weight).

        Checks:
        - Detects "document_summarizer" or summarization tool usage
        - Should be used for files >20KB
        - Penalizes reading large files without summarization

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        output_lower = output.lower()

        # Check for summarizer patterns
        has_summarizer = any(
            re.search(pattern, output, re.IGNORECASE)
            for pattern in self.SUMMARIZER_PATTERNS
        )

        # Check for large file mentions
        large_file_pattern = r'(\d+)\s*(KB|MB)'
        large_file_matches = re.findall(large_file_pattern, output, re.IGNORECASE)

        has_large_files = any(
            int(size) >= self.LARGE_FILE_THRESHOLD
            for size, unit in large_file_matches
            if unit.upper() == 'KB'
        ) or any(
            unit.upper() == 'MB'
            for _, unit in large_file_matches
        )

        # Scoring logic
        if has_summarizer and has_large_files:
            # Perfect score: using summarizer for large files
            return 1.0
        elif has_summarizer:
            # Good: using summarizer (even if no large file mention)
            return 0.9
        elif has_large_files:
            # Penalize: large files without summarizer
            return 0.2
        else:
            # No large files detected, give neutral score
            return 0.7

    def _score_file_limit_compliance(self, output: str) -> float:
        """
        Score file limit compliance (20% weight).

        Checks:
        - Counts distinct file reads (Read tool usage)
        - Should be 3-5 files max per research task
        - Penalizes reading too many files (>5)

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Extract unique file paths
        file_reads = re.findall(self.FILE_READ_PATTERN, output, re.IGNORECASE)
        unique_files: Set[str] = set(file_reads)
        file_count = len(unique_files)

        # Scoring logic
        if self.MIN_FILE_LIMIT <= file_count <= self.MAX_FILE_LIMIT:
            # Perfect score: within recommended range
            return 1.0
        elif file_count < self.MIN_FILE_LIMIT:
            # Acceptable: fewer files is fine (efficient research)
            return 0.9
        elif file_count <= 7:
            # Penalty: slightly over limit
            return 0.6
        elif file_count <= 10:
            # Major penalty: significantly over limit
            return 0.3
        else:
            # Severe penalty: excessive file reads
            return 0.0

    def _score_strategic_sampling(self, output: str) -> float:
        """
        Score strategic sampling compliance (20% weight).

        Checks:
        - Detects 100-200 line samples per file
        - Looks for "sampling", "lines X-Y", "excerpt"
        - Penalizes full file reads

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        output_lower = output.lower()

        # Check for sampling patterns
        has_sampling = any(
            re.search(pattern, output, re.IGNORECASE)
            for pattern in self.SAMPLING_PATTERNS
        )

        # Check for line range patterns
        line_range_pattern = r'lines?\s+(\d+)\s*[-–to]+\s*(\d+)'
        line_ranges = re.findall(line_range_pattern, output, re.IGNORECASE)

        # Calculate sample sizes
        sample_sizes = []
        for start, end in line_ranges:
            try:
                size = int(end) - int(start)
                sample_sizes.append(size)
            except ValueError:
                continue

        # Check if samples are within recommended range
        has_good_samples = any(
            self.MIN_SAMPLE_SIZE <= size <= self.MAX_SAMPLE_SIZE
            for size in sample_sizes
        )

        # Scoring logic
        if has_good_samples or (has_sampling and sample_sizes):
            # Perfect score: strategic sampling detected
            return 1.0
        elif has_sampling:
            # Good: mentions sampling even without explicit ranges
            return 0.8
        else:
            # No sampling detected, penalize
            return 0.2

    def _score_no_brute_force(self, output: str) -> float:
        """
        Score avoidance of brute force searches (10% weight).

        Checks:
        - Detects anti-patterns: "reading all files", "entire codebase"
        - Checks for negations (good): "avoids reading all files"
        - Penalizes exhaustive searches
        - Rewards targeted discovery (grep/glob first)

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        # Check for negation patterns first (these are GOOD)
        has_negation = any(
            re.search(pattern, output, re.IGNORECASE)
            for pattern in self.BRUTE_FORCE_NEGATIONS
        )

        # If negation found, it's a good sign (explicitly avoiding brute force)
        if has_negation:
            return 1.0

        # Check for brute force patterns
        has_brute_force = any(
            re.search(pattern, output, re.IGNORECASE)
            for pattern in self.BRUTE_FORCE_PATTERNS
        )

        # Check for targeted discovery patterns
        has_targeted_discovery = any(
            re.search(pattern, output, re.IGNORECASE)
            for pattern in self.TARGETED_DISCOVERY_PATTERNS
        )

        # Scoring logic
        if has_brute_force:
            # Severe penalty: brute force detected
            return 0.0
        elif has_targeted_discovery:
            # Perfect score: using targeted discovery
            return 1.0
        else:
            # Neutral score: no indicators either way
            return 0.7

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _generate_reason(
        self,
        size_check_score: float,
        summarizer_score: float,
        file_limit_score: float,
        sampling_score: float,
        brute_force_score: float,
        output: str
    ) -> str:
        """
        Generate human-readable reason for the score.

        Args:
            size_check_score: File size check score
            summarizer_score: Summarizer usage score
            file_limit_score: File limit compliance score
            sampling_score: Strategic sampling score
            brute_force_score: No brute force score
            output: Agent output text

        Returns:
            Reason string explaining the score
        """
        reasons = []

        # File size check issues
        if size_check_score < 1.0:
            file_reads = re.findall(self.FILE_READ_PATTERN, output, re.IGNORECASE)
            if file_reads and size_check_score < 0.5:
                reasons.append(
                    f"No file size check detected before reading {len(set(file_reads))} files"
                )

        # Summarizer usage issues
        if summarizer_score < 0.7:
            large_file_pattern = r'(\d+)\s*(KB|MB)'
            large_file_matches = re.findall(large_file_pattern, output, re.IGNORECASE)
            if large_file_matches:
                reasons.append(
                    "Large files detected but no summarizer usage found"
                )

        # File limit issues
        file_reads = re.findall(self.FILE_READ_PATTERN, output, re.IGNORECASE)
        file_count = len(set(file_reads))
        if file_limit_score < 1.0 and file_count > self.MAX_FILE_LIMIT:
            reasons.append(
                f"Excessive file reads ({file_count} files, recommended: {self.MIN_FILE_LIMIT}-{self.MAX_FILE_LIMIT})"
            )

        # Sampling issues
        if sampling_score < 0.5:
            reasons.append(
                "No strategic sampling detected (should read 100-200 line excerpts)"
            )

        # Brute force issues
        if brute_force_score < 0.5:
            brute_force_matches = [
                pattern for pattern in self.BRUTE_FORCE_PATTERNS
                if re.search(pattern, output, re.IGNORECASE)
            ]
            if brute_force_matches:
                reasons.append(
                    "Brute force pattern detected (avoid exhaustive searches)"
                )

        # Success message
        if not reasons:
            return "Perfect memory efficiency compliance - all protocols followed"

        return "; ".join(reasons)


def create_memory_efficiency_metric(threshold: float = 0.9) -> MemoryEfficiencyMetric:
    """
    Factory function to create memory efficiency metric.

    Args:
        threshold: Minimum passing score (default: 0.9 for 90% compliance)

    Returns:
        Configured metric instance

    Example:
        metric = create_memory_efficiency_metric(threshold=0.9)
        test_case = LLMTestCase(
            input="Research authentication implementation",
            actual_output="Checking file size... auth.py is 45KB, using summarizer..."
        )
        score = metric.measure(test_case)
    """
    return MemoryEfficiencyMetric(threshold=threshold)
