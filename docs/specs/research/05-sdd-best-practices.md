# Spec-Driven Documentation: Best Practices Research

**Research date:** 2026-06-01
**Scope:** Survey of established documentation models, naming analysis, WHAT/WHY/HOW boundary assessment, linkage mechanics, and a concrete recommended convention for claude-mpm.
**Method:** Web search of primary sources + canonical documentation; all claims cite URLs.

---

## Table of Contents

1. [Survey of Established Models](#1-survey-of-established-models)
2. [Naming Resolution](#2-naming-resolution)
3. [WHAT/WHY/HOW Separation Assessment](#3-whatwhyhow-separation-assessment)
4. [Linkage Mechanics](#4-linkage-mechanics)
5. [Recommended Model for claude-mpm](#5-recommended-model-for-claude-mpm)
6. [Sources](#6-sources)

---

## 1. Survey of Established Models

### 1.1 Architecture Decision Records (ADRs / MADR)

An ADR captures a single architecturally significant decision — its context, the decision itself, the alternatives considered, and the consequences. MADR (Markdown Architectural Decision Records) is the current dominant template, now at v4.0 (2024). ADRs live in `doc/adr/` inside the repository as Markdown files and are treated as immutable append-only records: when a decision changes, a new ADR supersedes the old one with a link back.

**Mapping to the proposed model:** ADRs address the WHY at decision level — they record *why* a design choice was made. The proposed model's `docs/specs/*.md` files serve a closely related but broader role (they capture WHAT a subsystem does, not just individual decisions). ADRs complement the proposed model but do not replace it: specs describe ongoing behavior contracts while ADRs document the history of architectural choices that produced them. A mature SDD implementation would include both layers.

**Divergence:** ADRs are append-only history; specs in the proposed model are living documents updated as behavior changes. The two have different update semantics.

Sources: [adr.github.io](https://adr.github.io/), [MADR](https://adr.github.io/madr/), [Martin Fowler ADR](https://martinfowler.com/bliki/ArchitectureDecisionRecord.html), [AWS ADR Best Practices](https://aws.amazon.com/blogs/architecture/master-architecture-decision-records-adrs-best-practices-for-effective-decision-making/)

---

### 1.2 arc42 and the C4 Model

**arc42** is a 12-section template for comprehensive architecture documentation covering quality requirements, runtime views, deployment views, cross-cutting concepts, risks, and technical debt. It is technology- and process-neutral and is used by enterprises including SAP and Siemens.

**C4 Model** (Context, Container, Component, Code) by Simon Brown provides a hierarchical, abstraction-first diagramming language for visualizing architecture at four zoom levels. It is lighter than arc42 and developer-focused.

The two complement each other: arc42 supplies the documentation structure and C4 supplies the visual language. C4 dynamic diagrams map to arc42's "Run-time View" chapter; C4 deployment diagrams map to arc42's "Deployment View."

**Mapping to the proposed model:** Both arc42 and C4 operate at a higher architectural level than `docs/specs/*.md` files. The proposed model's spec layer is closer to arc42's "Component View" or "Building Block View" chapters — it captures subsystem-level behavior contracts. Neither arc42 nor C4 defines how specs map back to source-code docstrings; the proposed model's traceability layer is an addition the proposed model makes that these frameworks leave unspecified.

**Divergence:** arc42 and C4 are architecture-documentation frameworks for communicating system structure to teams and stakeholders. The proposed model is a documentation discipline for maintaining contract fidelity between specs and code — narrower in scope but richer in code-linkage mechanics.

Sources: [arc42 FAQ](https://faq.arc42.org/questions/B-17/), [arc42 principles](https://arc42.org/principles-of-technical-documentation), [arc42+C4 example](https://bitsmuggler.github.io/arc42-c4-software-architecture-documentation-example/), [DEV comparison](https://dev.to/adityasatrio/comparing-software-architecture-documentation-models-and-when-to-use-them-495n)

---

### 1.3 The Diataxis Framework

Diataxis (Daniele Procida) organizes documentation into four modes keyed to reader intent:

| Mode | Reader intent | Answers |
|------|--------------|---------|
| Tutorial | "I want to learn" | How to get started |
| How-to guide | "I need to accomplish X" | Steps to reach a goal |
| Reference | "What is the precise definition?" | Facts, API, parameters |
| Explanation | "Why does it work this way?" | Context, rationale, concepts |

Adopted by Cloudflare, Django, Kubernetes, and Stripe docs among many others.

**Mapping to the proposed model:** The proposed model's spec files map primarily to Diataxis's **Explanation** and **Reference** quadrants — they explain WHY a subsystem behaves as it does (Explanation) and define the contract/WHAT (Reference). Inline docstrings map to Reference. The proposed model deliberately omits Tutorials and How-to guides — that is appropriate for a spec layer. Diataxis would counsel against writing specs that mix contract definition with procedural instructions; the proposed model already respects this boundary.

**Divergence:** Diataxis is a user-facing documentation framework about *how readers consume* documentation. The proposed model is a developer-facing discipline about *how writers maintain* documentation in sync with code. They operate at different levels and are complementary, not conflicting.

Sources: [diataxis.fr](https://diataxis.fr/), [I'd Rather Be Writing](https://idratherbewriting.com/blog/what-is-diataxis-documentation-framework), [Diataxis start-here](https://diataxis.fr/start-here/)

---

### 1.4 Requirements Traceability Matrix (RTM) / Bidirectional Traceability

An RTM is a table (or tool-maintained artifact) that maps each requirement to the design elements, code modules, and test cases that satisfy it. Forward traceability follows requirements to outputs; backward traceability goes from outputs back to requirements; bidirectional traceability covers both.

RTMs are ubiquitous in regulated industries (aerospace DO-178C, medical FDA, automotive ISO 26262). The main failure mode is manual maintenance — spreadsheet-based RTMs decay within weeks as code and requirements diverge independently.

**Mapping to the proposed model:** The proposed model's "explicit, maintained mapping/traceability between the spec layer and the inline layer" is precisely a bidirectional RTM — implemented not as a spreadsheet but as embedded markers in source and spec files. The RTM concept validates the owner's intuition about bidirectionality. The key lesson from RTM practice is that **automation is required** to prevent rot: any manually maintained mapping will drift.

**Divergence:** Traditional RTMs are external artifacts and rarely live inside the codebase. The proposed model embeds links directly in code and spec files, which is the right approach for a software project with a Git-based workflow.

Sources: [Inflectra RTM](https://www.inflectra.com/Ideas/Topic/Requirements-Traceability.aspx), [Jama traceability](https://www.jamasoftware.com/requirements-management-guide/requirements-traceability/traceability-matrix-101/), [Perforce RTM](https://www.perforce.com/resources/alm/requirements-traceability-matrix), [Sodius Willert guide](https://www.sodiuswillert.com/en/blog/implementing-requirements-traceability-in-systems-software-engineering)

---

### 1.5 Docs-as-Code

Docs-as-Code (popularized by Write the Docs, used by Google, Microsoft, and most major tech companies) treats documentation as source: written in plain text markup (Markdown, reStructuredText, AsciiDoc), version-controlled in Git alongside code, reviewed in pull requests, and built/deployed via CI/CD pipelines. Linters (Vale, markdownlint) enforce style. Documentation is part of the definition of "Done" for a feature.

**Mapping to the proposed model:** The proposed model is built on Docs-as-Code assumptions — specs live in `docs/specs/` inside the repository and are reviewed in PRs. This is the right foundation. Docs-as-Code does not, however, specify *how* specs link to code; it provides the workflow scaffold onto which the proposed linkage mechanics must be added.

**Divergence:** Docs-as-Code is about workflow (where and how docs are authored and reviewed), not about semantic structure (what content goes where and how it maps to code). The proposed model extends Docs-as-Code with explicit structural conventions and traceability.

Sources: [Kong Docs-as-Code](https://konghq.com/blog/learning-center/what-is-docs-as-code), [Hyperlint 5 practices](https://hyperlint.com/blog/5-critical-documentation-best-practices-for-docs-as-code/), [TechTarget Docs-as-Code](https://www.techtarget.com/searchapparchitecture/tip/Docs-as-Code-explained-Benefits-tools-and-best-practices)

---

### 1.6 Literate Programming (Knuth) and Modern Descendants

Knuth's literate programming (WEB, 1984) interleaves narrative prose and code in a single source file. A "weave" step extracts documentation; a "tangle" step extracts executable code. The prose defines the program's intent and the code implements it as one unified artifact. Modern descendants include:

- **Jupyter Notebooks** — executable cells interleaved with Markdown; dominant in data science but not suited to production codebases
- **Emacs Org-mode with org-babel** — similar interleaving, Emacs-centric
- **Noweb** — language-agnostic literate programming framework

**Mapping to the proposed model:** Literate programming is the most radical version of "docs and code as one artifact." The proposed model deliberately rejects this: specs live separately from code, with docstrings as the bridge. This separation is correct for a production Python codebase because: (a) IDEs, linters, and toolchains work better with standard `.py` files; (b) literate programming requires both writers and engineers to work in the same artifact, creating friction; (c) Jupyter's JSON storage is hostile to diff review. The proposed model achieves the *intent* of literate programming (intent and implementation in proximity) without the toolchain friction.

**Divergence:** Literate programming collapses the spec/code boundary; the proposed model maintains it with explicit links. The proposed model is the pragmatic industrial descendant of Knuth's vision.

Sources: [Wikipedia literate programming](https://en.wikipedia.org/wiki/Literate_programming), [Knuth Stanford LP page](https://cs.stanford.edu/~knuth/lp.html), [NYU Data Science guide](https://guides.nyu.edu/datascience/literate-prog)

---

### 1.7 Doxygen / Sphinx Autodoc / Javadoc Cross-Reference Conventions

These tools generate API reference documentation from inline docstrings and support cross-reference tags:

- **Doxygen** (`\sa` / `@see`): Starts a "See Also" paragraph linking to classes, functions, URLs, or external documentation via tag files.
- **Javadoc** (`@see`, `{@link}`): Inline hyperlinks from API reference to related classes or external URLs.
- **Sphinx** (`:ref:`, `:func:`, `:class:`, `:mod:`): Cross-reference roles that generate navigable links across documentation pages; can reference spec documents from docstrings and vice versa. Custom field lists (`:spec: SPEC-ID`) are parseable by autodoc and custom Sphinx extensions.
- **mkdocstrings**: Stable anchor generation from Python identifiers (`[full.path.object][]`), enabling cross-references from spec documents to module/class/function anchors.

**Mapping to the proposed model:** These tools provide the *mechanical* cross-reference infrastructure the proposed model needs. The pattern `:spec: SPEC-HOOKS-01` in a docstring is directly analogous to Javadoc's `@see` pointing to an external spec URI. Sphinx's `:ref:` can point from a spec file to an API reference page. This is proven, mature tooling — the proposed model should adopt these conventions rather than invent new ones.

Sources: [Sphinx autodoc](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html), [Doxygen commands](https://www.doxygen.nl/manual/commands.html), [lukasatkinson Python docstrings Sphinx](https://lukasatkinson.de/dump/2023-08-25-python-docstrings-sphinx/), [mkdocstrings usage](https://mkdocstrings.github.io/usage/)

---

### 1.8 "Spec-Driven Development" as Used in Industry — Disambiguation

The term "spec-driven development" (SDD) is heavily overloaded. Birgitta Böckeler (Distinguished Engineer, Thoughtworks) writing on MartinFowler.com explicitly flags it as "quite overloaded at the moment" and "already semantically diffused." Three distinct usages exist:

**Usage A — AI-assisted SDD (2024–2026 dominant usage):** Writing structured specifications before invoking AI coding agents, where the spec is the prompt scaffold. Tools: GitHub Spec Kit (released September 2024), Kiro, Tessl, OpenSpec. Thoughtworks placed this on their Technology Radar as an emerging technique in 2025. The spec is defined as "a structured, behavior-oriented artifact...written in natural language that serves as guidance to AI coding agents." Fowler's article identifies a hierarchy: spec-first → spec-anchored → spec-as-source. Tessl's radical version marks generated code with "GENERATED FROM SPEC — DO NOT EDIT."

**Usage B — API-first / Contract-first design:** OpenAPI (formerly Swagger) as the single source of truth for an HTTP API. The spec (a YAML/JSON OpenAPI document) precedes and governs both implementation and documentation. Code generators, mock servers, and documentation are all derived from the spec. This usage predates AI assistants by a decade and is well-established.

**Usage C — BDD executable specifications:** Gherkin `.feature` files (Cucumber, Behave) written before implementation. Scenarios are simultaneously the specification, the acceptance criteria, and the automated test. "Living documentation" in BDD means the specs are always true because they are executed as tests.

**The proposed model is none of these.** It is a documentation discipline: how to write, structure, and link spec prose documents and code docstrings so both remain accurate and traceable. It has more in common with RTM + Docs-as-Code + arc42 than with AI-SDD tools.

Sources: [MartinFowler.com SDD-3-tools](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html), [Thoughtworks SDD](https://www.thoughtworks.com/en-us/insights/blog/agile-engineering-practices/spec-driven-development-unpacking-2025-new-engineering-practices), [Thoughtworks Radar](https://www.thoughtworks.com/radar/techniques/spec-driven-development), [evangelistsoftware.com](https://evangelistsoftware.com/blog/spec-driven-development-guide/), [arxiv SDD](https://arxiv.org/html/2602.00180v1)

---

### 1.9 OpenAPI as Spec-of-Record / Single Source of Truth Patterns

OpenAPI's design-first (contract-first) pattern establishes the spec as the authority from which code stubs, mock servers, tests, and documentation are generated. No information about the API exists in two places — the spec is the single source of truth. Validation tools run in CI to verify that the implementation conforms to the spec; deviations cause build failures.

**Mapping to the proposed model:** This is the most direct precedent for the owner's linkage goal: the spec governs, code conforms, and CI enforces conformance. The proposed model applies this philosophy to prose-level functional specs and Python module docstrings, rather than to machine-readable OpenAPI contracts. The OpenAPI pattern suggests one crucial lesson: **the spec must be machine-readable enough that automated checks can verify conformance**. Pure prose specs cannot be validated by CI; stable identifiers and structured link markers are necessary.

Sources: [OpenAPI SSoT](https://blog.dochia.dev/blog/openapi-single-source/), [Contract-first HackerNoon](https://hackernoon.com/contract-first-apis-how-openapi-becomes-your-single-source-of-truth), [OpenAPI best practices](https://learn.openapis.org/best-practices.html)

---

### 1.10 Executable Specifications / BDD

BDD (Behavior-Driven Development) with Gherkin `.feature` files (Cucumber, Behave, pytest-bdd) produces executable specifications: the spec file *is* the test. Scenarios written in Given/When/Then syntax serve simultaneously as requirements, acceptance criteria, and automated tests. The traceability problem is solved structurally because the spec document and the test are the same artifact.

**Mapping to the proposed model:** BDD provides a form of the tightest possible spec-to-code link (spec == test). The proposed model is less radical: it maintains prose specs separately from tests, relying on identifier-based links rather than code/spec unification. BDD is applicable to behavioral/acceptance-level specifications; the proposed model's `docs/specs/*.md` files operate at the subsystem architecture level where Gherkin's `Given/When/Then` syntax does not fit naturally. The two are complementary: BDD for acceptance-level specifications of discrete behaviors, prose specs for system/subsystem-level contracts.

**Relevant insight from BDD:** "Scenarios should exist before implementation begins." The proposed model should adopt this discipline — spec sections should precede the code they govern, not document it retroactively.

Sources: [BDD guide](https://mastersoftwaretesting.com/testing-fundamentals/testing-techniques/behavior-driven-development-bdd), [Gherkin tutorial](https://testsigma.com/blog/behavior-driven-development-bdd-with-gherkin/), [BDD traceability](https://testquality.com/mastering-gherkin-bdd-tools-a-complete-guide-to-behavior-driven-development-testing/)

---

### 1.11 ReqToCode — Embedded Traceability as a Structural Property

An academic/industry approach (arxiv:2603.13999, 2025) that embeds traceable system elements directly into the codebase via language-native generated code elements called *Traceables*. Each Traceable represents a single requirement and carries its metadata. Developers reference Traceables in implementation and test code, creating hard bidirectional links validated at compile time. When requirements change, the system degrades gracefully from deprecation warnings to build failures.

**Mapping to the proposed model:** ReqToCode is the most technically rigorous approach to the linkage problem the owner is solving. Its core insight — that traceability should be a *compile-time verifiable property* of the codebase, not an external documentation task — is the right direction. The proposed model's CI-enforced link checks are a lighter-weight version of this principle. Full ReqToCode-style code generation may be over-engineered for claude-mpm's needs, but the conceptual model (hard links, graduated failure, build-time verification) should inform the design.

Sources: [ReqToCode arxiv](https://arxiv.org/pdf/2603.13999)

---

## 2. Naming Resolution

### The Acronym Problem

The owner calls the model "SDD." This acronym already collides with at least three established usages:

| Acronym expansion | Domain | Established since |
|------------------|--------|-------------------|
| Spec-Driven Development | AI-assisted coding (Kiro, GitHub Spec Kit, Tessl) | 2024 |
| Spec-Driven Design | Software architecture / API-first design | 2010s |
| Software Design Document | Traditional waterfall documentation | 1970s+ |

None of these match the owner's intent, which is a *documentation discipline* (how documentation is structured, written, and kept in sync with code), not a development process or design methodology.

### Candidate Names

**Option A: Traceable Specification Documentation (TSD)**
Emphasizes bidirectionality and the spec-as-record nature. "Traceable" is well-understood in RTM/systems engineering contexts. Downside: verbose; "TSD" has no prior collision.

**Option B: Contract-Anchored Documentation (CAD)**
Emphasizes that specs are contracts and that code is anchored to them. "Contract" aligns with the OpenAPI/BDD tradition. Downside: "contract" implies machine-verifiable invariants, which is only partially true for prose specs.

**Option C: Spec-Linked Documentation (SLD)**
Precise: "spec" = the `docs/specs/*.md` layer; "linked" = the bidirectional traceability mechanism; "documentation" = the overall discipline. No prior collision. Downside: less memorable.

**Option D: Spec-Anchored Documentation (SAD)**
Borrowed from Fowler's article on AI-SDD ("spec-anchored" = specs persist and govern code throughout the lifecycle). Emphasizes that specs are stable anchors that code is tethered to. Acronym collision: "SAD" has negative connotation.

**Option E: Keep "SDD" but redefine as "Spec-Driven Docs"**
Retains the owner's chosen acronym. "Docs" (not "Development") removes the process-methodology collision. Scope is clear: this is about documentation, not about development workflow. The parenthetical clarification "(documentation discipline, not AI-SDD)" handles residual ambiguity.

### Recommendation: **Spec-Linked Documentation (SLD)**

Rationale:
1. No acronym collision with any established term.
2. "Spec-Linked" precisely names the defining mechanical feature: the bidirectional links between spec files and source code. Every other model (Docs-as-Code, arc42, Diataxis) omits explicit linkage; SLD's defining property is the linkage.
3. "Documentation" correctly scopes it: this is a documentation convention, not a development methodology or process.
4. If the owner prefers to keep "SDD," then the full expansion should be **Spec-Driven Documentation** (not "Development") with explicit documentation in the skill that this is a documentation discipline distinct from AI-SDD tools.

For the remainder of this document the model is called **SLD** (Spec-Linked Documentation), with a note that the owner may use "SDD" as a short form if "Spec-Driven Documentation" is expanded.

---

## 3. WHAT/WHY/HOW Separation Assessment

### The Owner's Split

| Layer | Location | Captures |
|-------|----------|----------|
| Functional specs | `docs/specs/*.md` | System/subsystem-level WHAT and WHY |
| Inline docstrings | Source `.py` files | Component-level WHAT and WHY |
| Code itself | Source `.py` files | HOW (implementation details) |

### Assessment Against Best Practice

**Strengths — the split is sound:**

1. **Code-as-HOW is universally endorsed.** The principle "let code say *what*, comments say *why*" appears across all major documentation authorities. Self-documenting code via clear naming handles the WHAT at the line level; implementation details should not be duplicated in prose. The proposed model correctly excludes HOW from both spec files and docstrings.

2. **Two-tier WHAT/WHY (system vs. component) is architecturally correct.** arc42, C4, and Diataxis all recognize that architecture has multiple zoom levels. The proposed model's separation of system-level WHAT (specs) from component-level WHAT (docstrings) maps directly to C4's Container → Component → Code hierarchy. This is right.

3. **Specs = WHAT + WHY at the system level is precisely what arc42's "Solution Strategy" and "Building Block View" chapters are meant to capture.** The proposed model is an opinionated, leaner version of arc42 for a single-repo Python project.

4. **Docstrings = WHAT + WHY at the component level is the Google/NumPy style docstring convention.** A well-formed docstring explains what the function does and, in the "Notes" or custom section, why a particular approach was chosen. This is the established standard.

**Pitfalls to address:**

| Pitfall | Risk level | Mitigation |
|---------|-----------|------------|
| Spec drift: specs become inaccurate as code evolves | High | CI linkage checks; spec update required in same PR as code change |
| Docstring drift: docstrings lag behind code changes | High | Ruff/pylint docstring linters; PR review checklist |
| WHAT/HOW boundary blur in docstrings: engineers document implementation details in docstrings | Medium | Style guide: "describe observable behavior, not implementation steps" |
| Over-documentation: specs re-state what is obvious from code | Medium | Spec sections should address non-obvious constraints and rationale only |
| Missing WHY: specs capture WHAT (behavior) but omit WHY (rationale) | Medium | Spec template must include a mandatory "Rationale" section |
| HOW leaking into specs: specs describe algorithm steps rather than behavior contracts | Low | Spec review checklist; specs are contracts, not tutorials |

**The boundary is sound.** The most common failure mode in practice is not that the split is conceptually wrong — it is that the boundaries erode under time pressure without enforcement. The linkage mechanism (Section 4) and CI checks are the primary enforcement tools.

**One refinement:** The owner's formulation places WHAT at both the spec layer and the docstring layer. This is correct but can be made more precise:

- Spec-layer WHAT = *observable behavior contract*: inputs, outputs, preconditions, postconditions, invariants, error conditions, and cross-subsystem contracts. It is the "what" as seen from outside the subsystem.
- Docstring-layer WHAT = *component interface contract*: what this specific function/class/module does, its parameters, return values, and exceptions. It is the "what" as seen from the call site.

These are complementary, not redundant, because they operate at different granularities.

---

## 4. Linkage Mechanics

### What Needs to Be Linked

The proposed model requires:
1. Each spec section links to the modules/classes that implement it (spec → code, forward link).
2. Each module/class links back to its governing spec section (code → spec, backward link).

### Survey of Concrete Techniques

#### Technique A: Stable Spec Identifiers (Anchors)

Assign every spec section a stable, human-readable identifier in the spec document. Identifiers must be:
- Unique across all spec files
- Stable (do not change when section titles are rephrased)
- Short enough to embed in docstrings

**Format:** `SPEC-{SUBSYSTEM}-{NUMBER}` (e.g., `SPEC-HOOKS-01`, `SPEC-AGENTS-03`)

Implementation: Use Markdown named anchors. In `docs/specs/hooks.md`:
```markdown
## Hook Dispatch Subsystem {#SPEC-HOOKS-01}

**ID:** SPEC-HOOKS-01
**Status:** Active
**Implements:** Hook relay from Claude Code to Python handlers
...
```

The `{#SPEC-HOOKS-01}` anchor is rendered by most Markdown processors (including MkDocs and GitHub) and by Sphinx via `myst-parser`. The **ID** field in the section body provides a grep-able string for CI tooling.

#### Technique B: Docstring Back-References

In each Python module or class docstring, add a `References` section (NumpyDoc convention) or a custom `:spec:` field list entry (Sphinx convention) pointing to the governing spec:

```python
class HookDispatcher:
    """
    Dispatches pre-tool-use and post-tool-use hook events.

    WHAT: Receives raw hook JSON from claude-hook-fast.sh, routes to the
    appropriate Python handler, and returns a structured response.

    WHY: Claude Code's hook system requires a sub-50ms response; the dispatcher
    isolates routing logic from handler logic to enable independent testing.

    References
    ----------
    SPEC-HOOKS-01 : docs/specs/hooks.md#SPEC-HOOKS-01
    SPEC-HOOKS-02 : docs/specs/hooks.md#SPEC-HOOKS-02
    """
```

Alternatively, using Sphinx field lists (parseable by `sphinx.ext.autodoc`):
```python
    """:spec: SPEC-HOOKS-01, SPEC-HOOKS-02"""
```

The NumpyDoc `References` section is preferred because it is human-readable in source, renders in Sphinx via Napoleon, and is parseable by custom tooling.

#### Technique C: Spec-to-Code Forward Links

In the spec document, include a "Implementations" or "Modules" table after each spec section:

```markdown
## Hook Dispatch Subsystem {#SPEC-HOOKS-01}

...

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.hooks.pretooluse_dispatcher` | Primary dispatcher |
| `claude_mpm.scripts.claude-hook-fast` | Shell relay (not Python) |
```

This forward link is prose, not machine-readable — it must be kept in sync manually or via a generated traceability index (see Technique E).

#### Technique D: CI Link Validation

A custom pytest plugin or pre-commit hook validates:
1. Every `SPEC-*` identifier referenced in a docstring exists in `docs/specs/`.
2. Every spec section with an `ID:` field is referenced by at least one module docstring.
3. No orphaned identifiers (defined but unreferenced).

Implementation using grep + Python:

```python
# tests/test_traceability.py
import ast
import re
from pathlib import Path

SPEC_DIR = Path("docs/specs")
SRC_DIR = Path("src/claude_mpm")
SPEC_ID_PATTERN = re.compile(r"SPEC-[A-Z]+-\d+")

def collect_spec_ids():
    ids = set()
    for md in SPEC_DIR.rglob("*.md"):
        ids.update(SPEC_ID_PATTERN.findall(md.read_text()))
    return ids

def collect_docstring_refs():
    refs = set()
    for py in SRC_DIR.rglob("*.py"):
        refs.update(SPEC_ID_PATTERN.findall(py.read_text()))
    return refs

def test_no_dangling_spec_refs():
    """All SPEC-* IDs in docstrings must exist in docs/specs/."""
    defined = collect_spec_ids()
    referenced = collect_docstring_refs()
    dangling = referenced - defined
    assert not dangling, f"Dangling spec refs in source: {dangling}"

def test_no_unimplemented_specs():
    """Every SPEC-* ID in docs/specs/ must be referenced in at least one module."""
    defined = collect_spec_ids()
    referenced = collect_docstring_refs()
    unimplemented = defined - referenced
    assert not unimplemented, f"Spec IDs not referenced in any module: {unimplemented}"
```

This runs in `make test` and `pre-commit` with zero additional tooling dependencies.

#### Technique E: Generated Traceability Index

A lightweight script generates `docs/specs/TRACEABILITY.md` — a matrix of SPEC-IDs to implementing modules — on every CI run or as a pre-commit hook. This makes forward links (spec → code) machine-generated rather than manually maintained.

```python
# scripts/gen_traceability.py
# Reads all .md files in docs/specs/ and all .py files in src/
# Outputs docs/specs/TRACEABILITY.md with a SPEC-ID → [module list] table
```

The generated file is committed to the repository, reviewed in PRs, and regenerated on each CI run. Differences in the CI-generated version vs. the committed version fail the build.

#### Technique F: Doxygen/Sphinx `@see` Pattern (Established Convention)

Follow Javadoc/Doxygen's `@see` convention by adding a `See Also` section to docstrings with a direct URL to the spec document section:

```python
    """
    See Also
    --------
    Hook Dispatch spec : https://github.com/bobmatnyc/claude-mpm/blob/main/docs/specs/hooks.md#SPEC-HOOKS-01
    """
```

This is self-contained but fragile (URLs break on file renames). Prefer identifier-based references (Technique B) with URL resolution via the traceability index.

### Recommended Mechanism

**Adopt Technique B (docstring back-references with stable identifiers) + Technique C (spec forward links table) + Technique D (CI validation), with Technique E (generated traceability index) as a stretch goal.**

Concretely:

1. **Every spec section** gets a stable `SPEC-{SUBSYSTEM}-{NN}` ID declared on the first line of the section body and as a named Markdown anchor on the section heading.

2. **Every Python module** whose behavior is governed by a spec section includes a `References` block in its module-level docstring listing the governing SPEC-IDs. Classes and functions add a `:spec:` field list entry when they implement a specific spec section distinct from the module-level spec.

3. **Every spec section** includes an "Implementing Modules" table listing the Python modules that implement it.

4. **CI (pytest)** validates bidirectionality: all SPEC-IDs in docstrings exist in spec files; all SPEC-IDs in spec files are referenced in at least one module.

5. **PR template** includes a checklist item: "Spec updated and linkage consistent" for any PR that changes behavior covered by a spec.

**Why this over alternatives:**

- **Lower friction than StrictDoc/ReqToCode**: No new tools required; works with existing pytest and Markdown toolchain.
- **More reliable than manual RTM**: CI enforcement prevents rot.
- **More readable than pure Javadoc `@see` URLs**: Stable IDs survive file renames; URL resolution is handled by the traceability index.
- **Discoverable**: Any developer grepping for `SPEC-HOOKS-01` in the repository immediately finds both the spec definition and all implementations.
- **Survives refactoring**: When a module is split, the SPEC-ID references move with the code, and CI immediately flags if any reference becomes orphaned.

---

## 5. Recommended Model for claude-mpm

### Name

**Spec-Linked Documentation (SLD)** — or **Spec-Driven Documentation (SDD)** if the owner prefers the existing acronym, with the full expansion always including "Documentation" not "Development."

### Spec Document Structure (`docs/specs/{subsystem}.md`)

Each spec file covers one subsystem. Sections follow this template:

```markdown
# {Subsystem Name} Specification

**Status:** Active | Draft | Superseded
**Last reviewed:** YYYY-MM-DD
**Supersedes:** (link to previous spec if applicable)

## Overview

One paragraph: what this subsystem does, why it exists.

---

## {Section Title} {#SPEC-{SUBSYSTEM}-{NN}}

**ID:** SPEC-{SUBSYSTEM}-{NN}
**Status:** Active

### Behavior Contract

*WHAT: Observable behavior from the caller's perspective.*
- Inputs: ...
- Outputs: ...
- Preconditions: ...
- Postconditions: ...
- Error conditions: ...

### Rationale

*WHY: Design decisions and constraints.*
- Why this approach over alternatives...
- Key constraints driving the design...

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.{module}` | ... |
```

Key constraints:
- Specs describe **observable behavior contracts**, not implementation steps.
- Every section has a stable ID and a "Rationale" subsection (WHY is mandatory, not optional).
- The "Implementing Modules" table is maintained manually but validated by CI.
- Specs are written before the code they govern (spec-first discipline, inspired by BDD).

### Docstring Format

Module-level docstring for every module whose behavior is governed by a spec:

```python
"""
{Module name} — {one-line summary of what this module does}.

WHAT: {Two to four sentences describing the module's observable behavior
contract — what callers can rely on, what inputs it accepts, what outputs
it produces.}

WHY: {One to three sentences explaining why this module exists and why
it is designed the way it is — constraints, performance targets,
architectural decisions.}

References
----------
{SPEC-ID} : docs/specs/{subsystem}.md#{SPEC-ID}
{SPEC-ID} : docs/specs/{subsystem}.md#{SPEC-ID}
"""
```

For individual functions and classes that implement a *specific* spec section distinct from the module-level spec, add a `:spec:` field:

```python
def dispatch_hook(event: dict) -> dict:
    """
    Route a hook event to its handler and return the response.

    WHAT: Accepts a parsed hook event dict, identifies the handler by
    event type, and returns the handler's structured response dict.

    WHY: Centralizes routing logic so individual handlers remain
    testable in isolation.

    :spec: SPEC-HOOKS-02
    """
```

Rules:
- Docstrings describe **what the function/class does** (observable behavior) and **why it is designed this way** (rationale), never **how it works** (implementation steps).
- Implementation detail belongs in inline comments (`# reason for this approach`) within the function body, not in the docstring.
- The WHAT section uses active voice, caller's perspective: "Accepts...", "Returns...", "Raises...".
- The WHY section explains constraints, not steps: "Centralizes routing logic *so that*...", not "First we do X, then Y."

### Engineer Agent Responsibilities

When implementing a feature covered by a spec:

1. Check `docs/specs/` for the governing spec section before writing code.
2. Write the module-level docstring WHAT/WHY block before writing the function body (spec-first discipline).
3. Add `References` block to module docstring with the relevant SPEC-IDs.
4. Add `:spec:` field to any function/class implementing a specific spec section.
5. Update the "Implementing Modules" table in the spec if a new module is added.
6. Run `make test` to verify CI traceability checks pass.
7. PR description must confirm: "Spec linkage is consistent."

If no spec exists for a new subsystem being built:
1. Draft the spec section in `docs/specs/{subsystem}.md` first.
2. Assign a SPEC-ID following the existing numbering pattern.
3. Write code, then confirm the spec accurately describes the implemented behavior before merging.

### Documentation Agent Responsibilities

When reviewing or authoring spec documents:

1. Verify every spec section has a stable SPEC-ID, a Behavior Contract subsection, and a Rationale subsection.
2. Verify the "Implementing Modules" table is current — cross-check against actual modules in `src/claude_mpm/`.
3. Verify spec content is at the behavioral contract level (WHAT + WHY), not the implementation level (HOW).
4. Flag any spec section that has been Active for more than 90 days without a "Last reviewed" update.
5. When running `scripts/gen_traceability.py`, verify the generated `docs/specs/TRACEABILITY.md` matches expectations.
6. Apply Diataxis framework: spec files are in the Explanation + Reference quadrants; do not add Tutorial or How-to content to spec files.

### CI Enforcement

Add to `tests/test_traceability.py`:
- `test_no_dangling_spec_refs`: All SPEC-* IDs in source docstrings exist in `docs/specs/`.
- `test_no_unimplemented_specs`: All SPEC-* IDs in `docs/specs/` are referenced in at least one source file.
- `test_spec_id_format`: All IDs match `SPEC-[A-Z]+-[0-9]+` pattern.

These tests run in `make test` (zero additional dependencies: only `re`, `pathlib`, `ast`).

### Summary: 7-Bullet Convention

1. **One spec file per subsystem** in `docs/specs/{subsystem}.md`, organized into sections with stable `SPEC-{SUBSYSTEM}-{NN}` identifiers and named Markdown anchors.
2. **Each spec section has two mandatory subsections:** Behavior Contract (WHAT) and Rationale (WHY). The HOW is never in the spec.
3. **Each Python module governing a spec section** carries a module-level docstring with WHAT, WHY, and a `References` block listing governing SPEC-IDs.
4. **Individual functions/classes** that implement a specific spec section add a `:spec: SPEC-ID` field to their docstring when that spec ID is distinct from the module-level spec.
5. **Each spec section** maintains an "Implementing Modules" table for forward linkage (spec → code).
6. **CI validates bidirectionality**: dangling SPEC-IDs in docstrings fail the build; unreferenced SPEC-IDs in specs fail the build.
7. **Specs are written before the code they govern** (spec-first discipline); PRs must update both spec and code atomically, with the traceability check passing before merge.

---

## 6. Sources

- [adr.github.io — Architecture Decision Records](https://adr.github.io/)
- [MADR — Markdown Architectural Decision Records](https://adr.github.io/madr/)
- [Martin Fowler — ArchitectureDecisionRecord](https://martinfowler.com/bliki/ArchitectureDecisionRecord.html)
- [AWS ADR Best Practices](https://aws.amazon.com/blogs/architecture/master-architecture-decision-records-adrs-best-practices-for-effective-decision-making/)
- [arc42 FAQ — What about arc42 and C4?](https://faq.arc42.org/questions/B-17/)
- [arc42 Principles of Technical Documentation](https://arc42.org/principles-of-technical-documentation)
- [arc42 + C4 example (bitsmuggler)](https://bitsmuggler.github.io/arc42-c4-software-architecture-documentation-example/)
- [DEV.to — Comparing Architecture Documentation Models](https://dev.to/adityasatrio/comparing-software-architecture-documentation-models-and-when-to-use-them-495n)
- [Diataxis framework](https://diataxis.fr/)
- [Diataxis — Start here](https://diataxis.fr/start-here/)
- [I'd Rather Be Writing — Diataxis](https://idratherbewriting.com/blog/what-is-diataxis-documentation-framework)
- [Inflectra — Requirements Traceability](https://www.inflectra.com/Ideas/Topic/Requirements-Traceability.aspx)
- [Jama Software — Traceability Matrix](https://www.jamasoftware.com/requirements-management-guide/requirements-traceability/traceability-matrix-101/)
- [Perforce — Requirements Traceability Matrix](https://www.perforce.com/resources/alm/requirements-traceability-matrix)
- [Sodius Willert — Requirements Traceability Guide](https://www.sodiuswillert.com/en/blog/implementing-requirements-traceability-in-systems-software-engineering)
- [Kong — What is Docs as Code?](https://konghq.com/blog/learning-center/what-is-docs-as-code)
- [Hyperlint — 5 Critical Docs-as-Code Best Practices](https://hyperlint.com/blog/5-critical-documentation-best-practices-for-docs-as-code/)
- [TechTarget — Docs-as-Code Explained](https://www.techtarget.com/searchapparchitecture/tip/Docs-as-Code-explained-Benefits-tools-and-best-practices)
- [Wikipedia — Literate Programming](https://en.wikipedia.org/wiki/Literate_programming)
- [Donald Knuth — Literate Programming](https://cs.stanford.edu/~knuth/lp.html)
- [NYU Data Science — Literate Programming](https://guides.nyu.edu/datascience/literate-prog)
- [Sphinx autodoc documentation](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html)
- [Doxygen Special Commands](https://www.doxygen.nl/manual/commands.html)
- [Lukas Atkinson — Python Docstrings and Sphinx](https://lukasatkinson.de/dump/2023-08-25-python-docstrings-sphinx/)
- [mkdocstrings usage](https://mkdocstrings.github.io/usage/)
- [Martin Fowler — SDD-3-Tools (Kiro, Spec-Kit, Tessl)](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)
- [Thoughtworks — Spec-Driven Development (2025)](https://www.thoughtworks.com/en-us/insights/blog/agile-engineering-practices/spec-driven-development-unpacking-2025-new-engineering-practices)
- [Thoughtworks Technology Radar — Spec-Driven Development](https://www.thoughtworks.com/radar/techniques/spec-driven-development)
- [Evangelist Software — SDD Guide 2026](https://evangelistsoftware.com/blog/spec-driven-development-guide/)
- [arxiv — SDD From Code to Contract](https://arxiv.org/html/2602.00180v1)
- [OpenAPI — Single Source of Truth](https://blog.dochia.dev/blog/openapi-single-source/)
- [HackerNoon — Contract-First APIs](https://hackernoon.com/contract-first-apis-how-openapi-becomes-your-single-source-of-truth)
- [OpenAPI Best Practices](https://learn.openapis.org/best-practices.html)
- [BDD Testing Guide](https://mastersoftwaretesting.com/testing-fundamentals/testing-techniques/behavior-driven-development-bdd)
- [Gherkin BDD guide](https://testsigma.com/blog/behavior-driven-development-bdd-with-gherkin/)
- [TestQuality — Gherkin BDD Cucumber](https://testquality.com/mastering-gherkin-bdd-tools-a-complete-guide-to-behavior-driven-development-testing/)
- [arxiv — ReqToCode: Embedding Requirements Traceability](https://arxiv.org/pdf/2603.13999)
- [StrictDoc — Development Plan Traceability](https://strictdoc.readthedocs.io/en/stable/stable/docs/strictdoc_24_development_plan-TRACE.html)
- [PEP 257 — Docstring Conventions](https://peps.python.org/pep-0257/)
- [NumpyDoc — Google Style Docstrings example](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html)
- [Docsie — Traceability Best Practices](https://www.docsie.io/blog/glossary/traceability/)
- [GitHub — spec-kit Toolkit](https://github.com/github/spec-kit)
- [pytest-check-links](https://pypi.org/project/pytest-check-links/)
