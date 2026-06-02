# Prior Art: Bidirectional Spec-to-Code Traceability

**Research date:** 2026-06-01
**Purpose:** Determine whether the "linked docs" model proposed in `05-sdd-best-practices.md`
(markdown specs with stable IDs, docstring back-references, CI bidirectional completeness
check) is an original contribution or prior art — and if prior art exists, who got there first,
how completely, and what if anything is distinctive about the owner's instantiation.

**Verdict upfront:** The core idea is well-established prior art, not novel. OpenFastTrace (OFT)
is the closest existing tool; it embodies the owner's model almost exactly, differs in one
important mechanical detail (code-comment tags vs. docstring-embedded tags), and has been
production-ready since at least 2018. The claim in `05-sdd-best-practices.md` that "no other
model specifies these links" is false.

---

## 1. OpenFastTrace (OFT) — itsallcode

**Repository:** <https://github.com/itsallcode/openfasttrace>
**PyPI wrapper:** <https://pypi.org/project/oft-trace/>
**Gradle plugin:** <https://github.com/itsallcode/openfasttrace-gradle>
**Demo:** <https://github.com/itsallcode/openfasttrace-demo/blob/main/oft-live-demo-medium.md>

### What it does

OFT is an open-source requirement tracing suite (Java runtime, language-agnostic) that
enforces bidirectional traceability between plaintext/Markdown specification documents and
source code via a `trace` command designed for CI. It "eats its own dog food": OFT traces
its own requirements against its own codebase.

### Specification Item Format

In any Markdown or RST file, a specification item is declared with a structured ID:

```
artifact-type~name~revision
```

Example in a Markdown spec file:

```markdown
`req~validate-authentication-request~1`

The system shall validate every authentication request before processing.

Needs: dsn
```

The triple `(artifact-type, name, revision)` is mandatory. Artifact types are user-defined
strings (`req`, `dsn`, `impl`, `test`, etc.) representing traceability levels.
The chain looks like:

```
req~validate-auth~1  →  dsn~validate-auth~1  →  impl~validate-auth~1
```

### Coverage Tags in Source Code

In any source file (Java, Python, C, C++, Go, Kotlin, and 30+ others), coverage is declared
via a tag in a **code comment** (not a docstring):

```java
// [impl->dsn~validate-authentication-request~1]
private void validate(final AuthenticationRequest request) { ... }
```

Extended form with explicit revision and name:

```
[impl~~42->dsn~validate-authentication-request~1]
```

The tag importer recognizes the file by extension. For Python, tags go in `#` comments or
inside docstrings (any text the importer scans). The key point: the tag is an **in-file
annotation** at or near the implementing function, not in the requirement document.

### Trace Command and CI Output

```bash
oft trace doc/spec $(find . -name "*.java")
```

The `trace` command crawls spec files and source trees, correlates IDs, and reports:

- COVERED — requirement has a matching `impl` tag in source
- UNCOVERED — requirement exists in spec but has no `impl` tag anywhere
- ORPHANED — an `impl` tag exists in source but no matching `req` exists in spec
- OUTDATED — revision mismatch between tag and current spec revision
- SHALLOW — partial coverage only

A CI build configured with the Gradle/Maven plugin fails if any item is UNCOVERED or has an
ORPHANED tag. This is **precisely** the bidirectional completeness check the owner describes:
every spec ID must be implemented; every impl tag must point to a real spec ID.

### How Close Is It to the Owner's Model?

| Dimension | Owner's model | OpenFastTrace |
|---|---|---|
| Spec format | Markdown with `SPEC-SUBSYSTEM-NN` IDs | Markdown/RST with `req~name~version` IDs |
| ID stability | Stable string, human-readable | Stable string + integer revision |
| Spec location | `docs/specs/` | Any configured directory |
| Code annotation | Docstring `References` block or `:spec:` field | Comment tag `[impl->req~name~1]` |
| Annotation location | Docstring (Python-idiomatic) | Code comment (language-agnostic) |
| Forward link (spec→code) | Manual "Implementing Modules" table | Generated automatically from tags |
| CI check: dangling code refs | Yes (pytest) | Yes (trace command, ORPHANED status) |
| CI check: unimplemented specs | Yes (pytest) | Yes (trace command, UNCOVERED status) |
| Revision tracking | No | Yes (revision integer, OUTDATED detection) |
| Build integration | pytest / pre-commit | Gradle, Maven, CLI, Makefile |
| Language requirement | None (grep + Python) | Java 17 runtime for OFT itself |
| WHAT/WHY prose convention | Explicit rule | Not specified (OFT is mechanical) |

**Summary:** OFT implements the bidirectional ID-based spec-to-code linkage with a
CI-enforced completeness check. It is the same idea, running in production, with a richer
feature set (revision tracking, orphaned-tag detection, multi-level chains). It predates the
owner's proposal.

**The one real difference:** OFT tags go in code **comments**; the owner's model places the
reference in **docstrings**. This is a deliberate Python-idiomatic choice — docstrings are
first-class language objects, rendered by IDEs, picked up by Sphinx autodoc, and surfaced in
`help()`. An OFT code comment is invisible to all tooling except OFT's own scanner.

---

## 2. Doorstop — doorstop-dev

**Repository:** <https://github.com/doorstop-dev/doorstop>
**Docs:** <https://doorstop.readthedocs.io/>
**PyPI:** <https://pypi.org/project/doorstop/>
**Paper:** <https://www.researchgate.net/publication/276044183_Doorstop_Text-Based_Requirements_Management_Using_Version_Control>

### What it does

Doorstop stores each requirement as a YAML file in a Git repository. Requirements form a
directed acyclic graph (DAG) via `links` fields. A `ref` (or `references`) field in each
YAML item points to a source code file or a keyword within a file. Running `doorstop` in CI
validates the entire hierarchy: broken `ref` paths exit with error; suspect links (parent
changed but child not reviewed) are flagged.

### YAML item structure

```yaml
active: true
level: 2.1
normative: true
reviewed: 1f33605bbc5d1a39c9a6441b91389e88
links: [SYS001]
ref: 'validate_authentication_request'
text: |
  The system shall validate every authentication request before processing.
```

The `ref` keyword causes Doorstop to search all project files for a matching filename or
substring. If the keyword appears in a docstring or function name, it will be found — but this
is a substring match, not a structured ID-based link. The `links` field establishes
parent-child relationships between requirements only (not to code items).

### How Close Is It to the Owner's Model?

- Forward traceability (spec→code): YES — the `ref` field resolves to a source file/line.
- Backward traceability (code→spec): PARTIAL — Doorstop does not scan code files for
  requirement IDs. Code files are passive targets; they do not actively reference requirement
  IDs. A community issue (#577) requested "parse source code and link to requirement
  traceability" as a feature — suggesting it was not built-in.
- CI completeness check: PARTIAL — Doorstop validates that `ref` paths resolve and that
  `links` chains are valid, but there is no check that every requirement has at least one code
  reference, nor that every code function references a requirement.
- Bidirectional completeness: WEAKER than OFT. Doorstop is primarily a requirement-hierarchy
  tool; source code is a secondary artifact pointed to from requirements, not a first-class
  participant in the tracing graph.

**Assessment:** Doorstop is good prior art for the "requirements as text files in Git" half
of the model, but it does not achieve genuine bidirectional completeness enforcement. It is
closer to a sophisticated RTM with Git storage than to the owner's CI-enforced two-way link
model.

---

## 3. StrictDoc — strictdoc-project

**Repository:** <https://github.com/strictdoc-project/strictdoc>
**User guide:** <https://strictdoc.readthedocs.io/en/stable/stable/docs/strictdoc_01_user_guide.html>
**Feature map:** <https://strictdoc.readthedocs.io/en/stable/stable/docs/strictdoc_02_feature_map.html>

### What it does

StrictDoc manages requirements in a domain-specific language (`.sdoc` files) and provides
HTML/RST/PDF export, a web editor, and — critically — source code traceability. The `.sdoc`
format is similar to TOML/YAML hybrid optimized for large requirements documents (hundreds to
thousands of requirements).

### SDoc format

```
[REQUIREMENT]
UID: REQ-001
TITLE: Validate authentication requests
STATEMENT: >>>
The system shall validate every authentication request before processing.
<<<
RELATIONS:
- TYPE: File
  VALUE: src/auth/validator.py
```

### Source Code Traceability Tags (Current Standard)

Source files are annotated with `@relation` markers in comments:

```python
# @relation(REQ-001, role=Implements)
def validate_authentication_request(request):
    ...
```

Legacy syntax was `@sdoc[REQ-001]` (line marker) or range markers. These have been migrated
to `@relation`. StrictDoc parses source files using Tree-sitter for language-aware
identification of functions, classes, and ranges.

The "Source Coverage" screen in StrictDoc's HTML output shows which requirements have code
coverage and which source functions are linked to requirements. This is a visual
bidirectional matrix, not a CI pass/fail check in the conventional sense — StrictDoc
generates the traceability report, but the build does not fail on uncovered requirements
unless configured to do so.

### How Close Is It to the Owner's Model?

- Forward traceability (spec→code): YES — `RELATIONS: TYPE: File` points to source files.
- Backward traceability (code→spec): YES — `@relation` markers in source comments.
- CI completeness check: PARTIAL — StrictDoc generates coverage reports; automated
  build-break on uncovered specs requires additional configuration.
- Annotation location: Code comments (same limitation as OFT relative to the owner's
  docstring preference).
- WHAT/WHY prose structure: Not specified; StrictDoc is format-neutral about prose content.
- Dependency: Requires Python + StrictDoc installation; not zero-dep like the owner's pytest
  approach.

**Assessment:** StrictDoc is the most feature-rich of the three alternatives. It handles the
full bidirectional link and produces visual coverage maps. However it is heavier than OFT (no
Java runtime, but requires StrictDoc tooling), and like OFT it uses code-comment tags rather
than docstrings.

---

## 4. Sphinx-Needs — useblocks

**Docs:** <https://sphinx-needs.readthedocs.io/>
**Homepage:** <https://www.sphinx-needs.com/>
**Tutorial:** <https://sphinx-needs.readthedocs.io/en/stable/tutorial.html>

### What it does

Sphinx-Needs extends Sphinx with typed "need" objects (`req`, `spec`, `impl`, `test`) that
carry unique IDs and can be linked to each other. A `needtable` directive generates
traceability matrices from the graph. It supports ISO 26262 and DO-178B/C workflows. The
`open-needs` project extends it with an IDE/server layer.

### Need definition

```rst
.. req:: Validate authentication requests
   :id: REQ-001
   :status: open

   The system shall validate every authentication request before processing.
```

### Code linking

Sphinx-Needs does **not** natively scan Python source files for need references. The
Sphinx-Test-Reports extension can import pytest test results and link them to needs, providing
coverage from tests to requirements. Direct code-to-requirement annotation (as in OFT or
StrictDoc) is not a built-in feature; it requires custom extensions. A `sphinxcontrib-traceability`
extension exists (<https://pypi.org/project/sphinxcontrib-traceability/>) that adds
bidirectional relationship matrices, but still within the Sphinx documentation layer.

### How Close Is It to the Owner's Model?

- Forward traceability (spec→code): PARTIAL — links are between need objects in docs, not
  to source files.
- Backward traceability (code→spec): NOT BUILT-IN — no scanner for source-code annotations.
- CI completeness check: PARTIAL — Sphinx warns on broken links; no automated check that
  every req has a code coverage tag.
- Python-idiomatic docstring approach: NOT SUPPORTED.

**Assessment:** Sphinx-Needs is the right tool when you live entirely in the Sphinx
documentation ecosystem and your "code coverage" means "test coverage." It is not a close
match to the owner's model of docstring-embedded spec IDs validated by pytest.

---

## 5. Requirements Traceability as a Regulated Discipline (RTM)

**DO-178C RTM overview:** <https://rtmify.io/standards/do-178c>
**ISO 26262 traceability:** <https://www.parasoft.com/learning-center/iso-26262/requirements-traceability/>
**Cross-standard overview:** <https://www.trace.space/blog/traceability-in-compliance-projects>
**LDRA RTM:** <https://ldra.com/capabilities/requirements-traceability/>

Bidirectional spec-to-code traceability is mandated by:

- **DO-178C** (aviation, FAA/EASA): Section 11.9 "Traceability Data" requires a document
  showing the bidirectional trace from system requirements → high-level requirements → low-level
  requirements → source code → tests. 100% coverage at DAL A–C is not optional.
- **ISO 26262** (automotive ASIL A–D): Section 6.4.3.2 requires every safety requirement to
  link to its origin and to downstream verification evidence through to source code.
- **IEC 62304** (medical device software, Class B/C): Implies bidirectional traceability
  between software requirements, architecture, and unit implementation.
- **ASPICE** (automotive process standard): Explicitly requires bidirectional traceability.

The concept of "every requirement must have a code reference; every code reference must point
to a real requirement" is the RTM discipline articulated in regulated industries since the
1980s. It is not new.

What is comparatively new (mid-2010s) is tooling that embeds this discipline directly in
source files rather than in an external spreadsheet or database, enabling Git-native,
developer-friendly tracing. OFT, Doorstop, and StrictDoc are all responses to this shift.

---

## 6. Other Prior Art

### IBM DOORS / Polarion / Jama Connect

Enterprise commercial tools that implement full bidirectional RTMs with code linking via
integrations (Polarion links to Git commits/files; DOORS requires custom plugins). These are
heavyweight, license-gated, and not applicable to an open-source project. They do not affect
the novelty assessment for developer-centric tooling.

### Capella / SysML

Model-Based Systems Engineering (MBSE) tools that maintain traceability in graphical models
(block diagrams, activity diagrams). Capella's `ReqIf` import/export enables linking SysML
requirements to model elements. These operate at a higher abstraction level than source-code
traceability and are not relevant to the owner's text-in-Git approach.

### Literate Programming Descendants (noweb, Org-mode, Jupyter)

These collapse the spec/code boundary rather than linking across it. They are the philosophical
ancestor of the idea but not the same mechanism.

### pytest-mark-requirements (SAP SDK pattern)

Using `@pytest.mark.requirements(issues=["42"])` to link test functions to requirement IDs
is a narrower version of the owner's model: test→requirement tracing only, no enforcement
that every requirement is covered by a test (requires custom reporting). Source:
<https://data-attribute-recommendation-python-sdk.readthedocs.io/en/latest/traceability.html>

### ReqToCode (arxiv:2603.13999, 2025)

Proposes embedding requirement traceability as compile-time-verifiable language objects
(Python classes generated from requirements). Most technically rigorous approach; over-engineered
for the owner's use case. Not widely adopted.

### EARS Notation

Easy Approach to Requirements Syntax (EARS) is a structured natural-language syntax for writing
requirements (`WHEN <condition> the <system> SHALL <response>`). It standardizes requirement
prose, not traceability. Mentioned for completeness.

---

## 7. Blunt Verdict

### Is the core idea novel?

**No.** The idea of assigning stable IDs to specification sections, annotating source code with
those IDs, and running a CI tool that verifies bidirectional completeness (every spec ID is
implemented; every code annotation points to a real spec ID) is the exact feature set of
**OpenFastTrace**, which has been publicly available and used in production since at least
2017–2018. The principle is also mandated in regulated industries (DO-178C, ISO 26262) and has
been practiced since the 1990s in the form of RTMs, though historically in spreadsheets rather
than embedded in source files.

The claim in `05-sdd-best-practices.md` — "no other model specifies these links" — is wrong.
OFT specifies exactly these links with a richer feature set (revision tracking, OUTDATED
detection, multi-level artifact chains). Doorstop and StrictDoc provide comparable coverage.

### What is genuinely distinctive about the owner's specific instantiation?

Three things are real (if modest) differentiators:

1. **Docstring as the annotation site, not a code comment.** OFT, StrictDoc, and Doorstop all
   use code comments (or separate YAML files) for the back-reference. The owner's model places
   the spec reference inside the Python docstring — making it a first-class language object
   visible to `help()`, Sphinx autodoc, IDEs (hover), and type checkers. This is
   Python-idiomatic in a way no existing tool has standardized.

2. **Zero new runtime dependencies.** The owner's CI check (`tests/test_traceability.py`) uses
   only `re`, `pathlib`, and `ast` — packages in the Python standard library. OFT requires a
   Java 17 runtime. StrictDoc requires its own installation. Doorstop requires the `doorstop`
   package. For a Python project that wants traceability enforcement with no new tooling, the
   pytest-based approach is genuinely lighter.

3. **Explicit WHAT/WHY/HOW layer separation as a prose rule.** OFT, Doorstop, and StrictDoc
   are mechanical tools — they enforce linkage completeness but say nothing about what prose
   belongs in a spec vs. a docstring vs. inline comments. The owner's model goes further by
   mandating that specs capture WHAT and WHY (observable contracts and rationale) while code
   captures HOW (implementation). This is a documentation discipline layered on top of a
   mechanical traceability check; it has no direct equivalent in OFT et al.

### Recommendation

**(b) Adopt OFT's convention, keep a lightweight pytest implementation.**

Specifically:

- Adopt OFT's naming convention insight: use a structured `artifact-type~name~version` or
  simplified `SPEC-SUBSYSTEM-NN` scheme — OFT validates that a three-part ID is the right
  granularity. The owner's `SPEC-HOOKS-01` format is fine; it just lacks the revision integer
  that OFT uses to detect outdated coverage (consider adding it as `SPEC-HOOKS-01-v1` if spec
  sections will evolve).

- Do NOT adopt OFT's Java runtime or its code-comment tag syntax. Instead, keep the docstring
  `References` block as the annotation site. This is the owner's genuine differentiator:
  `References\n----------\nSPEC-HOOKS-01 : docs/specs/hooks.md#SPEC-HOOKS-01` in a Python
  docstring is superior to `// [impl->req~hooks~1]` in a comment for a Python-first team.

- Keep the pytest-based `test_traceability.py` as the CI enforcement mechanism. It is simpler,
  faster, and has zero dependencies. OFT's Gradle/Maven integration is Java-ecosystem tooling
  that would be friction in a Python project.

- Explicitly acknowledge in the convention documentation that this approach is a lightweight
  Python-idiomatic implementation of the same bidirectional traceability discipline embodied
  by OpenFastTrace, Doorstop, and StrictDoc — and that the docstring-as-annotation-site is
  the deliberate Python-specific adaptation.

- If the project ever needs multi-level tracing (spec→design→implementation→test chains with
  revision tracking and OUTDATED detection), graduate to OFT at that point. The `oft-trace`
  PyPI wrapper makes this feasible without introducing a Java build system.

---

## 8. Sources

- [OpenFastTrace GitHub — itsallcode/openfasttrace](https://github.com/itsallcode/openfasttrace)
- [OpenFastTrace user guide (main)](https://github.com/itsallcode/openfasttrace/blob/main/doc/user_guide.md)
- [OpenFastTrace demo — oft-live-demo-medium.md](https://github.com/itsallcode/openfasttrace-demo/blob/main/oft-live-demo-medium.md)
- [oft-trace — PyPI](https://pypi.org/project/oft-trace/)
- [openfasttrace-gradle plugin](https://github.com/itsallcode/openfasttrace-gradle)
- [Doorstop GitHub — doorstop-dev/doorstop](https://github.com/doorstop-dev/doorstop)
- [Doorstop documentation](https://doorstop.readthedocs.io/)
- [Doorstop — PyPI](https://pypi.org/project/doorstop/)
- [Doorstop paper — ResearchGate](https://www.researchgate.net/publication/276044183_Doorstop_Text-Based_Requirements_Management_Using_Version_Control)
- [Doorstop issue #577 — parse source code for requirement links](https://github.com/doorstop-dev/doorstop/issues/577)
- [Doorstop item reference — ref field](https://doorstop.readthedocs.io/en/v1.3/reference/items/)
- [StrictDoc GitHub — strictdoc-project/strictdoc](https://github.com/strictdoc-project/strictdoc)
- [StrictDoc user guide](https://strictdoc.readthedocs.io/en/stable/stable/docs/strictdoc_01_user_guide.html)
- [StrictDoc feature map](https://strictdoc.readthedocs.io/en/stable/stable/docs/strictdoc_02_feature_map.html)
- [StrictDoc @relation source marker — release notes](https://github.com/strictdoc-project/strictdoc/releases)
- [Sphinx-Needs documentation](https://sphinx-needs.readthedocs.io/)
- [Sphinx-Needs homepage](https://www.sphinx-needs.com/)
- [sphinxcontrib-traceability — PyPI](https://pypi.org/project/sphinxcontrib-traceability/)
- [DO-178C RTM template — rtmify.io](https://rtmify.io/standards/do-178c)
- [ISO 26262 requirements traceability — Parasoft](https://www.parasoft.com/learning-center/iso-26262/requirements-traceability/)
- [Traceability in compliance projects — trace.space](https://www.trace.space/blog/traceability-in-compliance-projects)
- [LDRA requirements traceability](https://ldra.com/capabilities/requirements-traceability/)
- [Requirements traceability — Perforce](https://www.perforce.com/resources/alm/requirements-traceability-matrix)
- [SAP SDK pytest.mark.requirements pattern](https://data-attribute-recommendation-python-sdk.readthedocs.io/en/latest/traceability.html)
- [ReqToCode — arxiv:2603.13999](https://arxiv.org/pdf/2603.13999)
