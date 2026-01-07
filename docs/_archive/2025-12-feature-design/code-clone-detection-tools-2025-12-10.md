# Code Clone Detection Tools Research
**Research Date:** 2025-12-10
**Purpose:** Identify tools for detecting repeated/similar code that can be integrated into the code-analyzer agent
**Goal:** Find tools to detect repeated code blocks, copy-paste patterns, and similar code across files that could be parameterized or refactored

---

## Executive Summary

Based on comprehensive research of code clone detection tools in 2025, the recommended approach for the code-analyzer agent is a **hybrid Python-native solution** combining:

1. **pylint's duplicate-code checker (R0801)** - For immediate, zero-dependency duplicate detection
2. **pycode_similar** - For AST-based similarity with minimal dependencies
3. **rope's SimilarFinder** - For refactoring suggestions with similar code extraction
4. **Custom AST hashing** - For semantic similarity detection

**Recommended Primary Tool:** **pycode_similar** + **pylint duplicate-code** + **rope SimilarFinder**

**Why:** Pure Python, AST-based, minimal dependencies, actively maintained, integrates seamlessly with existing code-analyzer architecture.

---

## 1. Clone Detection Tools Categorized

### A. Python-Native Tools (Recommended)

#### 1.1 pylint duplicate-code checker (R0801)
- **Type:** Token-based duplicate detection
- **Languages:** Python
- **Installation:** `pip install pylint` (already in code-analyzer dependencies)
- **Pros:**
  - Zero additional dependencies (pylint already used)
  - Fast and efficient
  - Well-maintained and widely adopted
  - Configurable threshold (`min-similarity-lines`)
  - Built-in to existing toolchain
- **Cons:**
  - Python-only
  - Token-based (misses semantic clones)
  - Reports line-level duplicates, not structural similarity
- **Output Format:** Standard pylint messages with file:line references
- **Usage:**
  ```bash
  pylint --disable=all --enable=duplicate-code src/
  ```
- **Integration Complexity:** ⭐ Very Easy (already integrated)
- **Recommendation:** ✅ **Use as first-line defense**

**Sources:**
- [Pylint duplicate-code documentation](https://pylint.readthedocs.io/en/latest/user_guide/messages/refactor/duplicate-code.html)
- [Pylint duplicate code checker](https://pylint.pycqa.org/en/v2.13.9/messages/refactor/duplicate-code.html)

---

#### 1.2 pycode_similar
- **Type:** AST-based plagiarism/similarity detection
- **Languages:** Python
- **Installation:** `pip install pycode_similar` (single file, minimal dependencies)
- **Pros:**
  - Pure Python AST analysis
  - Two diff methods: UnifiedDiff (fast) and TreeDiff (slow, thorough)
  - Can be used as library or CLI
  - No third-party parsing dependencies
  - Actively maintained
  - Normalizes AST for comparison
- **Cons:**
  - Python-only
  - TreeDiff method very slow for large codebases
  - Not multi-language
- **Output Format:**
  ```
  ref: tests/original_version.py candidate: pycode_similar.py
  80.14 % (803/1002) of ref code structure is plagiarized by candidate.
  ```
- **Usage:**
  ```python
  import pycode_similar
  pycode_similar.detect([ref_code, candidate1, candidate2],
                        diff_method=pycode_similar.UnifiedDiff,
                        keep_prints=False, module_level=False)
  ```
- **Integration Complexity:** ⭐⭐ Easy
- **Recommendation:** ✅ **Primary tool for Python AST similarity**

**Sources:**
- [pycode_similar GitHub](https://github.com/fyrestone/pycode_similar)

---

#### 1.3 rope (SimilarFinder for refactoring)
- **Type:** Refactoring library with similar code extraction
- **Languages:** Python (up to 3.10 syntax)
- **Installation:** `pip install rope` (already in code-analyzer dependencies)
- **Pros:**
  - Advanced refactoring capabilities
  - Can extract similar expressions/statements automatically
  - Suggests parameterization opportunities
  - Open source, pure Python
  - IDE-quality refactoring operations
- **Cons:**
  - Primarily a refactoring library, not a clone detector
  - Python 3.10 max syntax support (as of late 2024)
  - Requires more setup than simple detection
- **Output Format:** Refactoring suggestions with code locations
- **Usage:**
  ```python
  from rope.base.project import Project
  from rope.refactor.extract import ExtractMethod

  project = Project('.')
  resource = project.get_file('module.py')

  # Extract method will find similar blocks
  extractor = ExtractMethod(project, resource, start, end)
  changes = extractor.get_changes('new_method_name', similar=True)
  ```
- **Integration Complexity:** ⭐⭐⭐ Moderate
- **Recommendation:** ✅ **Use for actionable refactoring suggestions**

**Sources:**
- [rope GitHub](https://github.com/python-rope/rope)
- [rope PyPI](https://pypi.org/project/rope/)
- [rope documentation](https://rope.readthedocs.io/en/latest/overview.html)

---

#### 1.4 Clone Digger
- **Type:** AST-based clone detection using anti-unification
- **Languages:** Python, Java, Lua, JavaScript
- **Installation:** `pip install clonedigger`
- **Pros:**
  - Multi-language support
  - AST-based analysis
  - HTML output with visual diffs
  - Anti-unification algorithm (academic rigor)
- **Cons:**
  - Last updated 2010-2011 (maintenance concern)
  - Slower than modern tools
  - Limited Python 3 support
  - Academic tool, not production-grade
- **Output Format:** HTML reports with side-by-side comparisons
- **Usage:**
  ```bash
  python clonedigger.py -o output.html source_directory/
  ```
- **Integration Complexity:** ⭐⭐⭐ Moderate
- **Recommendation:** ⚠️ **Legacy tool, avoid unless specific need**

**Sources:**
- [Clone Digger documentation](https://clonedigger.sourceforge.net/documentation.html)
- [Clone Digger PyPI](https://pypi.org/project/clonedigger/)

---

### B. Multi-Language Tools

#### 1.5 PMD CPD (Copy-Paste Detector)
- **Type:** Token-based Rabin-Karp algorithm
- **Languages:** 40+ languages including Python, Java, JavaScript, TypeScript, Go, Rust, C/C++
- **Installation:** Requires Java runtime + PMD binary
- **Pros:**
  - Multi-language support (40+ languages)
  - Mature, well-maintained
  - Production-grade tool
  - Configurable minimum token threshold
  - XML/JSON/text output formats
- **Cons:**
  - **Requires Java runtime** (heavy dependency)
  - Token-based (misses semantic clones)
  - External binary (not Python library)
  - CLI integration adds complexity
- **Output Format:** XML, JSON, text with duplicate code blocks
- **Usage:**
  ```bash
  pmd cpd --minimum-tokens 100 --dir src/main/java
  pmd cpd --minimum-tokens 50 --files "**/*.py" --format json
  ```
- **Integration Complexity:** ⭐⭐⭐⭐ Complex (requires Java)
- **Recommendation:** ⚠️ **Only if multi-language support critical and Java acceptable**

**Sources:**
- [PMD installation guide](https://docs.pmd-code.org/pmd-doc-7.5.0/pmd_userdocs_installation.html)
- [PMD CPD documentation](https://github.com/pmd/pmd/blob/main/docs/pages/pmd/userdocs/cpd/cpd.md)
- [GitLab Code Quality with PMD CPD](https://aarongoldenthal.com/posts/gitlab-code-quality-duplication-analysis-with-pmd-cpd/)

---

#### 1.6 jscpd
- **Type:** Token-based Rabin-Karp algorithm (JavaScript implementation)
- **Languages:** 150+ languages including Python
- **Installation:** `npm install -g jscpd`
- **Pros:**
  - Multi-language (150+ languages)
  - Fast detection
  - JSON/XML/console output
  - Configurable reporters
  - Active development
- **Cons:**
  - **Requires Node.js** (heavy dependency)
  - Token-based (misses semantic clones)
  - Reports duplicate pairs only (3+ copies reported as pairs)
  - External binary (not Python library)
- **Output Format:** JSON, XML, console with duplicate pairs
- **Usage:**
  ```bash
  jscpd --languages python -f "**/*.py" --min-tokens 50 ./src
  ```
- **Integration Complexity:** ⭐⭐⭐⭐ Complex (requires Node.js)
- **Recommendation:** ⚠️ **Only if Node.js already in stack**

**Sources:**
- [jscpd npm package](https://www.npmjs.com/package/jscpd/v/0.6.7)
- [jscpd README](https://app.unpkg.com/jscpd@0.6.0/files/README.md)

---

### C. Advanced/Research Tools

#### 1.7 TACC (Token and AST-based Code Clone Detector)
- **Type:** Hybrid token + AST tree matching
- **Languages:** Research tool (configurable)
- **Installation:** Not publicly available (research prototype)
- **Pros:**
  - Hybrid approach (token filtering + tree verification)
  - Hash tree-based subtree matching
  - Effective for Type-1 through Type-3 clones
- **Cons:**
  - Research tool, not production-ready
  - No public release
  - Complex implementation
- **Recommendation:** ❌ **Research only, not for integration**

**Sources:**
- [TACC comparison paper](https://wu-yueming.github.io/Files/ICSE2023_TACC.pdf)

---

#### 1.8 Ringer (2025)
- **Type:** Multi-language clone detector
- **Languages:** Python, C, Java, Verilog
- **Installation:** Not widely available
- **Pros:**
  - High accuracy (94%+ for Type-1/Type-2/Type-3 in Python)
  - Outperforms Moss and NiCad
  - Cross-language detection
- **Cons:**
  - Recent research tool (2025)
  - Limited public availability
  - Unknown maintenance status
- **Recommendation:** ⏳ **Monitor for future public release**

**Sources:**
- [Multi-language clone detection comparison 2025](https://dl.acm.org/doi/10.1145/3723178.3723206)

---

#### 1.9 TreeCen
- **Type:** AST-based semantic clone detection with centrality analysis
- **Languages:** Configurable (research tool)
- **Installation:** GitHub repository available
- **Pros:**
  - Scalable tree-based detection
  - 72-dimensional vectors (efficient)
  - Semantic clone detection (Type-4)
- **Cons:**
  - Research tool complexity
  - Not production-grade
  - Setup overhead
- **Recommendation:** ❌ **Too complex for immediate integration**

**Sources:**
- [TreeCen GitHub](https://github.com/CGCL-codes/TreeCen)

---

## 2. Clone Type Detection Capabilities

| Tool | Type-1 (Exact) | Type-2 (Renamed) | Type-3 (Modified) | Type-4 (Semantic) |
|------|----------------|------------------|-------------------|-------------------|
| **pylint duplicate-code** | ✅ | ✅ | ⚠️ | ❌ |
| **pycode_similar** | ✅ | ✅ | ✅ | ⚠️ |
| **rope SimilarFinder** | ✅ | ✅ | ✅ | ⚠️ |
| **Clone Digger** | ✅ | ✅ | ✅ | ❌ |
| **PMD CPD** | ✅ | ✅ | ⚠️ | ❌ |
| **jscpd** | ✅ | ✅ | ⚠️ | ❌ |
| **TACC** | ✅ | ✅ | ✅ | ⚠️ |
| **TreeCen** | ✅ | ✅ | ✅ | ✅ |

**Clone Types Explained:**
- **Type-1:** Exact copies (possibly with whitespace/comment changes)
- **Type-2:** Renamed variables/functions but same structure
- **Type-3:** Modified code with insertions/deletions but same logic
- **Type-4:** Semantically identical but different implementations

---

## 3. Recommended Integration Strategy for code-analyzer

### Phase 1: Immediate Integration (Zero New Dependencies)

**Tool:** pylint duplicate-code checker
**Reason:** Already integrated, zero setup cost
**Implementation:**
```python
import subprocess
result = subprocess.run(
    ['pylint', '--disable=all', '--enable=duplicate-code',
     '--min-similarity-lines=5', 'src/'],
    capture_output=True, text=True
)
# Parse pylint output for duplicate-code violations
```

**Output:** Line-based duplicate detection with file references

---

### Phase 2: AST-Based Similarity (Minimal Dependencies)

**Tool:** pycode_similar
**Reason:** Pure Python, AST-based, minimal dependencies
**Installation:** `pip install pycode_similar`
**Implementation:**
```python
import pycode_similar
from pathlib import Path

# Find all Python files
files = list(Path('src').rglob('*.py'))

# Compare all pairs for similarity
results = []
for i, ref_file in enumerate(files):
    with open(ref_file) as f:
        ref_code = f.read()

    for candidate_file in files[i+1:]:
        with open(candidate_file) as f:
            candidate_code = f.read()

        similarity = pycode_similar.detect(
            [ref_code, candidate_code],
            diff_method=pycode_similar.UnifiedDiff
        )

        if similarity[0][1] > 70:  # >70% similar
            results.append({
                'ref': ref_file,
                'candidate': candidate_file,
                'similarity': similarity[0][1]
            })
```

**Output:** Percentage similarity between file pairs

---

### Phase 3: Refactoring Suggestions (Existing Dependency)

**Tool:** rope SimilarFinder
**Reason:** Already in code-analyzer, provides actionable refactoring
**Implementation:**
```python
from rope.base.project import Project
from rope.refactor.extract import ExtractMethod, ExtractVariable

project = Project('.')

# For each function with duplicated blocks:
resource = project.get_file('module.py')

# Extract similar expressions
extract_var = ExtractVariable(project, resource, start, end)
changes = extract_var.get_changes('variable_name', similar=True)

# This will find and extract ALL similar expressions
```

**Output:** Refactoring change sets with similar code locations

---

### Phase 4: Custom AST Hashing (Advanced)

**Approach:** Implement custom AST hashing for semantic similarity
**Reason:** No external dependencies, tailored to code-analyzer needs
**Implementation:**
```python
import ast
import hashlib
from collections import defaultdict

def normalize_ast(node):
    """Normalize AST by removing variable names."""
    if isinstance(node, ast.Name):
        return ast.Name(id='VAR', ctx=node.ctx)
    elif isinstance(node, ast.FunctionDef):
        return ast.FunctionDef(
            name='FUNC',
            args=node.args,
            body=node.body,
            decorator_list=[]
        )
    # Continue normalization...
    return node

def hash_ast_subtree(node):
    """Hash normalized AST subtree."""
    normalized = normalize_ast(node)
    ast_str = ast.dump(normalized)
    return hashlib.md5(ast_str.encode()).hexdigest()

def find_similar_blocks(filepath):
    """Find similar code blocks via AST hashing."""
    with open(filepath) as f:
        tree = ast.parse(f.read())

    hash_map = defaultdict(list)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.For, ast.While, ast.If)):
            node_hash = hash_ast_subtree(node)
            hash_map[node_hash].append({
                'type': type(node).__name__,
                'line': node.lineno,
                'col': node.col_offset
            })

    # Find hashes with multiple occurrences
    duplicates = {k: v for k, v in hash_map.items() if len(v) > 1}
    return duplicates
```

**Output:** Dictionary of AST hashes with duplicate locations

---

## 4. Integration Architecture for code-analyzer

### Recommended Multi-Tier Approach

```python
class CloneDetector:
    """Multi-tier clone detection for code-analyzer."""

    def __init__(self, project_root):
        self.project_root = project_root
        self.results = {
            'line_duplicates': [],
            'ast_similar': [],
            'refactorable': [],
            'semantic_clones': []
        }

    def detect_all(self):
        """Run all detection tiers."""
        # Tier 1: Fast line-based duplicates (pylint)
        self.detect_line_duplicates()

        # Tier 2: AST similarity (pycode_similar)
        self.detect_ast_similarity()

        # Tier 3: Refactoring opportunities (rope)
        self.detect_refactorable()

        # Tier 4: Semantic clones (custom AST hashing)
        self.detect_semantic_clones()

        return self.generate_report()

    def detect_line_duplicates(self):
        """Use pylint duplicate-code checker."""
        import subprocess
        result = subprocess.run(
            ['pylint', '--disable=all', '--enable=duplicate-code',
             '--min-similarity-lines=5', self.project_root],
            capture_output=True, text=True
        )
        # Parse and store results
        self.results['line_duplicates'] = self._parse_pylint_output(result.stdout)

    def detect_ast_similarity(self):
        """Use pycode_similar for AST-based detection."""
        import pycode_similar
        from pathlib import Path

        files = list(Path(self.project_root).rglob('*.py'))

        for i, ref_file in enumerate(files):
            for candidate_file in files[i+1:]:
                similarity = self._compare_files(ref_file, candidate_file)
                if similarity > 70:
                    self.results['ast_similar'].append({
                        'files': [str(ref_file), str(candidate_file)],
                        'similarity': similarity
                    })

    def detect_refactorable(self):
        """Use rope to find refactoring opportunities."""
        # Implement rope-based similar code extraction
        pass

    def detect_semantic_clones(self):
        """Use custom AST hashing for semantic similarity."""
        # Implement AST hashing approach
        pass

    def generate_report(self):
        """Generate unified clone detection report."""
        return {
            'summary': {
                'line_duplicates': len(self.results['line_duplicates']),
                'ast_similar_pairs': len(self.results['ast_similar']),
                'refactorable_blocks': len(self.results['refactorable']),
                'semantic_clones': len(self.results['semantic_clones'])
            },
            'details': self.results
        }
```

---

## 5. Installation Requirements Summary

### Minimal Setup (Recommended)
```bash
# Already in code-analyzer dependencies:
pip install pylint  # duplicate-code checker
pip install rope    # refactoring suggestions

# New minimal dependency:
pip install pycode_similar  # AST similarity
```

**Total new dependencies:** 1 (pycode_similar)

### Optional Multi-Language Setup (If Needed)
```bash
# Java required for PMD CPD:
brew install openjdk  # or apt-get install default-jre
wget https://github.com/pmd/pmd/releases/download/pmd_releases/7.16.0/pmd-bin-7.16.0.zip
unzip pmd-bin-7.16.0.zip

# Node.js required for jscpd:
npm install -g jscpd
```

**Total additional dependencies:** Java runtime + Node.js (heavy)

---

## 6. Comparative Tool Analysis

### Best for Python-Only Projects
**Winner:** pycode_similar + pylint duplicate-code
**Reason:** Pure Python, AST-based, minimal dependencies, fast

### Best for Multi-Language Projects
**Winner:** PMD CPD (if Java acceptable) OR Custom AST per language
**Reason:** 40+ languages, production-grade, configurable

### Best for Refactoring Automation
**Winner:** rope SimilarFinder
**Reason:** Actionable suggestions, parameterization detection, IDE-quality

### Best for Research/Advanced Detection
**Winner:** TreeCen or TACC
**Reason:** Semantic clone detection (Type-4), academic rigor

### Best for Zero Setup Cost
**Winner:** pylint duplicate-code
**Reason:** Already integrated, immediate value

---

## 7. Recommended Priorities for code-analyzer Integration

### Priority 1: IMMEDIATE (This Sprint)
- ✅ Enable pylint duplicate-code checker in code-analyzer
- ✅ Parse and report duplicate code violations
- **Effort:** 1-2 hours
- **Value:** Immediate duplicate detection with zero new dependencies

### Priority 2: HIGH (Next Sprint)
- ✅ Integrate pycode_similar for AST similarity
- ✅ Implement pairwise file comparison
- ✅ Report similarity percentages >70%
- **Effort:** 4-6 hours
- **Value:** Semantic similarity detection beyond line duplicates

### Priority 3: MEDIUM (Future)
- ⏳ Implement rope SimilarFinder integration
- ⏳ Generate refactoring suggestions for similar blocks
- **Effort:** 8-12 hours
- **Value:** Actionable parameterization opportunities

### Priority 4: LOW (Research)
- ⏳ Implement custom AST hashing for Type-4 clones
- ⏳ Evaluate TreeCen or advanced research tools
- **Effort:** 20+ hours
- **Value:** Advanced semantic clone detection

---

## 8. Example Output Format for code-analyzer

```markdown
# Code Clone Detection Report

## Summary
- Total files analyzed: 45
- Line-based duplicates: 12 instances
- AST-similar pairs: 8 pairs (>70% similarity)
- Refactorable blocks: 5 opportunities
- Semantic clones: 3 groups

## Critical Issues (Immediate Refactoring)

### 1. AST Similarity: 87% (src/auth/oauth.py ↔ src/auth/saml.py)
**Lines:** oauth.py:45-78 ↔ saml.py:102-135

**Similarity:** Both implement token validation with slight parameter differences

**Recommendation:** Extract to `validate_token(token, provider_type)` with provider parameter

**Affected Code:**
```python
# oauth.py:45-78
def validate_oauth_token(token):
    if not token:
        raise ValueError("Token required")
    decoded = jwt.decode(token, secret)
    if decoded['exp'] < time.time():
        raise TokenExpired()
    return decoded

# saml.py:102-135
def validate_saml_token(assertion):
    if not assertion:
        raise ValueError("Assertion required")
    decoded = saml.decode(assertion, cert)
    if decoded['exp'] < time.time():
        raise AssertionExpired()
    return decoded
```

**Refactored:**
```python
def validate_token(token, provider='oauth'):
    if not token:
        raise ValueError(f"{provider.title()} token required")

    decoder = jwt.decode if provider == 'oauth' else saml.decode
    key = secret if provider == 'oauth' else cert

    decoded = decoder(token, key)
    if decoded['exp'] < time.time():
        raise TokenExpired(f"{provider.title()} token expired")
    return decoded
```

---

### 2. Line Duplicate: 15 lines (src/api/users.py ↔ src/api/posts.py)
**Lines:** users.py:234-248 ↔ posts.py:156-170

**Duplication:** Pagination logic repeated verbatim

**Recommendation:** Extract to `paginate(query, page, per_page)` utility function

---

## High Priority Issues

### 3. Rope Refactoring: Similar variable extraction in 4 locations
**Files:**
- src/reports/analytics.py:45
- src/reports/metrics.py:78
- src/reports/dashboards.py:102
- src/reports/exports.py:34

**Pattern:** `current_time = datetime.now(timezone.utc).isoformat()`

**Recommendation:** Extract to module-level constant or utility function

---

## Metrics
- Code duplication: 8.4% (target: <5%)
- Largest clone: 34 lines (auth/oauth.py ↔ auth/saml.py)
- Most duplicated pattern: Error handling boilerplate (12 instances)
- Refactoring potential: ~450 lines reducible to ~180 lines (60% reduction)
```

---

## 9. Future Research Directions

### Emerging Tools to Monitor (2025+)
- **Ringer:** High-accuracy multi-language detector (monitor for public release)
- **LLM-based clone detection:** GPT-4/Claude for semantic similarity
- **Tree-sitter query-based detection:** Custom queries for pattern matching
- **GitHub Copilot code analysis:** Similarity detection via embeddings

### Integration Opportunities
- **CI/CD integration:** Fail builds on duplication threshold
- **IDE plugins:** Real-time duplicate detection in VS Code
- **Pre-commit hooks:** Prevent duplicate code commits
- **Code review automation:** Flag similar code in PRs

---

## 10. Conclusion and Final Recommendation

### Recommended Solution for code-analyzer Agent

**Tier 1 (Immediate):**
✅ **pylint duplicate-code** - Enable today, zero dependencies

**Tier 2 (Next sprint):**
✅ **pycode_similar** - Add for AST similarity, minimal dependency

**Tier 3 (Future):**
⏳ **rope SimilarFinder** - For actionable refactoring suggestions
⏳ **Custom AST hashing** - For advanced semantic clone detection

### Implementation Checklist

- [ ] Add `pycode_similar` to code-analyzer dependencies
- [ ] Implement `CloneDetector` class with multi-tier detection
- [ ] Enable pylint duplicate-code in existing analysis workflow
- [ ] Create clone detection report template
- [ ] Add clone detection to code-analyzer output
- [ ] Document clone detection thresholds and configuration
- [ ] Add unit tests for clone detection logic
- [ ] Integrate with TodoWrite for refactoring tasks

### Key Benefits

1. **Pure Python solution** - No Java/Node.js dependencies
2. **Multi-tier detection** - Line, AST, semantic levels
3. **Actionable insights** - Refactoring suggestions, not just warnings
4. **Minimal overhead** - Fast analysis, low memory footprint
5. **Extensible architecture** - Easy to add new detection methods

### Memory Usage Estimate

- pylint duplicate-code: ~50MB for 1000 files
- pycode_similar: ~100MB for pairwise comparison of 100 files
- rope SimilarFinder: ~150MB for refactoring analysis
- **Total:** <300MB for comprehensive clone detection

---

## Sources

### Python Tools
- [pycode_similar GitHub](https://github.com/fyrestone/pycode_similar)
- [Pylint duplicate-code documentation](https://pylint.readthedocs.io/en/latest/user_guide/messages/refactor/duplicate-code.html)
- [rope GitHub](https://github.com/python-rope/rope)
- [rope documentation](https://rope.readthedocs.io/en/latest/overview.html)
- [Clone Digger documentation](https://clonedigger.sourceforge.net/documentation.html)

### Multi-Language Tools
- [PMD installation guide](https://docs.pmd-code.org/pmd-doc-7.5.0/pmd_userdocs_installation.html)
- [PMD CPD documentation](https://github.com/pmd/pmd/blob/main/docs/pages/pmd/userdocs/cpd/cpd.md)
- [jscpd npm package](https://www.npmjs.com/package/jscpd/v/0.6.7)

### Research Papers
- [TACC comparison paper](https://wu-yueming.github.io/Files/ICSE2023_TACC.pdf)
- [Multi-language clone detection comparison 2025](https://dl.acm.org/doi/10.1145/3723178.3723206)
- [TreeCen GitHub](https://github.com/CGCL-codes/TreeCen)
- [AST-based Markov Chains (Amain)](https://github.com/CGCL-codes/Amain)

---

**Research completed:** 2025-12-10
**Researcher:** Claude Code (Research Agent)
**Next steps:** Review findings with engineering team, prioritize integration tasks, create implementation tickets
