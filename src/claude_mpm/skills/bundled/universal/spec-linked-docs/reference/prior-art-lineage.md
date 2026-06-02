# Prior Art Lineage: Understanding SLD's Place in Traceability History

## Why Understanding Lineage Matters

Spec-Linked Documentation (SLD) is not a novel invention. It is a **Python-idiomatic adaptation** of a well-established discipline with decades of practice in regulated industries. Understanding this lineage is important for three reasons:

1. **Intellectual honesty:** Claim only what you innovated; credit what you adapted.
2. **Learning from others:** Prior art tools (OpenFastTrace, Doorstop, StrictDoc) have solved problems you will face; study their solutions.
3. **Avoiding reinvented wheels:** When you hit a problem, check if OFT or ISO 26262 already solved it.

---

## The Three Generations

### Generation 1: Regulated Industry RTM (1980s–1990s)

**Context:** Aviation (DO-178C), automotive (ISO 26262), medical (IEC 62304) industries require **bidirectional Requirements Traceability Matrices** as a mandatory compliance artifact.

**What an RTM is:** A table (spreadsheet or database) mapping:
- System Requirements → High-Level Design → Low-Level Design → Source Code → Tests

**Example RTM Row:**
```
Req ID      | Req Description                | Design Component | Code Module | Test Case |
REQ-001     | Validate input before process  | InputValidator   | auth.py     | test_03   |
```

**How it failed in non-regulated projects:**
- Manual spreadsheet maintenance created infinite friction.
- Every code change meant manually updating the RTM.
- In fast-moving agile teams, RTMs became stale within weeks.
- **80% of practitioners cited manual cost as the primary barrier** (Springer, 2023 study).

**Failure pattern:** RTM created at project start, never updated again. Becomes a historical artifact, not a living document.

### Generation 2: Source-Control-Native Traceability (2017–present)

**Key insight:** Instead of maintaining a spreadsheet external to the codebase, embed traceability directly in source files using version control as the system of record.

#### OpenFastTrace (2017–present)

**Repository:** https://github.com/itsallcode/openfasttrace
**Status:** Production-ready; actively maintained (latest release: 2026-06-01)
**Language:** Java runtime; language-agnostic spec scanner

**How it works:**

Specs in Markdown:
```markdown
`req~validate-input~1`

The system shall validate all user input before processing.

Needs: impl
```

Code annotations in comments:
```java
// [impl->req~validate-input~1]
public void validateInput(String input) { ... }
```

Trace command:
```bash
oft trace docs/ $(find . -name "*.java")
```

Output: Coverage report with status for each requirement:
- **COVERED** — requirement has an impl tag
- **UNCOVERED** — requirement has no impl tag
- **ORPHANED** — impl tag points to no requirement
- **OUTDATED** — tag revision doesn't match spec revision

**Why OFT matters:** It proves the concept works in production. The four-status model (COVERED/UNCOVERED/ORPHANED/OUTDATED) is correct and sufficient. Revision tracking is valuable.

**Why OFT is not enough for Python projects:** Requires Java 17 runtime; uses code comments instead of docstrings; has small community (145 GitHub stars).

#### Doorstop (2012–present)

**Repository:** https://github.com/doorstop-dev/doorstop
**Status:** Stable; actively maintained (3.1 released Jan 2026)
**Language:** Python; text-based RTM

**How it works:**

Each requirement is a YAML file in Git:
```yaml
active: true
level: 2.1
reviewed: 1f33605bbc5d1a39c9a6441b91389e88
links: [SYS001]
ref: 'validate_input'
text: |
  The system shall validate every input before processing.
```

The `ref` field points to source code by keyword matching.

**Why Doorstop matters:** Shows that YAML-based, Git-native requirement storage is viable and enables version control workflows.

**Why Doorstop is not a perfect match:** Uses substring matching for code references (not structured IDs); has only weak bidirectional completeness checking; requires Doorstop installation.

#### StrictDoc (2018–present)

**Repository:** https://github.com/strictdoc-project/strictdoc
**Status:** Growing community; recent conference presence (ESA, ELISA, Zephyr projects)
**Language:** Python; full-featured requirements management

**How it works:**

Requirements in `.sdoc` domain-specific language:
```
[REQUIREMENT]
UID: REQ-001
TITLE: Validate input
STATEMENT: The system shall validate all input.
RELATIONS:
- TYPE: File
  VALUE: src/auth/validator.py
```

Code annotations:
```python
# @relation(REQ-001, role=Implements)
def validate_input(request):
    ...
```

Produces visual coverage matrices in HTML and generates traceability reports.

**Why StrictDoc matters:** Demonstrates that bidirectional traceability scales to thousands of requirements with visual dashboards. Most actively developed (5,896 commits vs. OFT's 1,340).

**Why StrictDoc is more than SLD:** Richer feature set (visual coverage, multi-level traces, DSL for requirements); not as lightweight; best used when traceability is a primary concern.

### Generation 3: AI-Assisted Traceability (2024–present)

**New development:** Research on using LLMs to generate and maintain trace links.

**TraceLLM (2026, Springer Nature):** Uses prompt engineering with GPT-4o, Claude-3.5-Sonnet, Gemini-1.5-Pro to generate trace links with ~52% precision (zero-shot) and ~61% F2-score (few-shot). Focuses on *link recovery* (retrospective reconstruction), not *link maintenance* (keeping links fresh as code evolves).

**SpecMap (arXiv:2601.11688):** Hierarchical LLM agent for hardware datasheet-to-firmware traceability. Also recovery-focused.

**TRAIL (2018, arXiv:1807.06684):** ML-based approach to automatic traceability maintenance; predates LLMs; requires classifier retraining.

**ReqToCode (arXiv:2603.13999):** Most technically rigorous approach — embeds traceability as compile-time-verifiable language objects. Avoids hallucination by making links structural, not probabilistic.

**Live agents (2025, emerging research):** References to "maintaining and propagating trace links automatically as repositories evolve using live agents" (Naumcheva et al., Feb 2025; Jin et al., Sep 2025). Not yet deployed at scale.

---

## SLD's Position in This Lineage

### What SLD Adopts (without Invention)

- **Four-status model** from OpenFastTrace: COVERED / UNCOVERED / ORPHANED / OUTDATED
- **Stable ID discipline** from DO-178C RTMs: every requirement gets a unique, persistent identifier
- **Bidirectional completeness check** from regulated industry practice: every spec must be implemented; every code reference must point to a real spec
- **Revision tracking** from OFT: when a spec section's behavior changes, the revision number increments, enabling detection of mismatches

### What SLD Distinctly Contributes

1. **Docstring as the annotation site (Python-idiomatic)**
   - OFT, StrictDoc, Doorstop: code comments
   - SLD: Python docstrings (NumpyDoc `References` block, Sphinx `:spec:` field)
   - **Why this matters:** Docstrings are first-class Python objects, visible to `help()`, IDE hover, type checkers, and Sphinx autodoc. Comments are invisible to tooling except the traceability scanner.

2. **Zero-dependency implementation**
   - OFT: requires Java 17
   - StrictDoc: requires StrictDoc installation
   - Doorstop: requires `doorstop` package
   - SLD: uses only `re`, `pathlib`, `ast` (Python stdlib)
   - **Why this matters:** Lower barrier to adoption; CI checks run without new dependencies; fits naturally into pytest workflow.

3. **Explicit WHAT/WHY/HOW documentation discipline**
   - OFT et al.: enforce syntactic traceability completeness; silent on prose content
   - SLD: adds a rule layer — specs must capture WHAT (observable contract) and WHY (rationale); HOW (implementation) stays in code
   - **Why this matters:** Prevents specs from drifting into implementation details, which is a common failure mode.

4. **AI agent as the maintainer**
   - Prior art tools: support human-maintained traceability
   - SLD: explicitly frames the AI coding agent as the atomic link maintainer — when an agent writes or modifies code, it updates spec IDs in docstrings as the same action
   - **Why this matters:** Removes the manual cost that historically made RTMs unmaintainable; leverages what AI agents are good at (atomic, careful code modification).

---

## The Honest Assessment

**SLD is not novel in concept.** The core machinery — stable IDs, bidirectional CI checking, code-spec linking — is decades-old, proven in production, and formalized in standards like DO-178C.

**What is novel about SLD is the package:**
- Python docstring as the annotation site (not previous practice)
- Zero-dependency pytest implementation (simpler than existing tools)
- Explicit WHAT/WHY/HOW boundary as a prose rule (complementary to mechanical checks)
- Framing AI agents as atomic link maintainers (emergent research direction, not yet mainstream)

**Claim honestly:** "We adapted OpenFastTrace's proven four-status model to Python docstrings, removed the Java dependency, added an explicit prose discipline, and positioned AI agents as the link maintainers."

---

## Further Reading

- [OpenFastTrace documentation](https://github.com/itsallcode/openfasttrace/blob/main/doc/user_guide.md)
- [DO-178C Traceability Requirements](https://rtmify.io/standards/do-178c)
- [ISO 26262 Traceability (Automotive Safety)](https://www.parasoft.com/learning-center/iso-26262/requirements-traceability/)
- [Springer 2023 Study: Why traceability fails](https://link.springer.com/article/10.1007/s00766-023-00408-9)
