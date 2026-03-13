---
name: finding-duplicate-functions
description: Use when auditing a codebase for semantic duplication — functions that do the same thing but have different names or implementations, especially common in LLM-generated codebases
when_to_use: after syntactic duplicate detection (jscpd), during codebase audits, or before major refactoring to find consolidation opportunities
version: 1.0.0
category: debugging
author: Jesse Vincent
license: MIT
source: https://github.com/obra/superpowers-lab/tree/main/skills/finding-duplicate-functions
tags:
  - debugging
  - refactoring
  - duplication
  - code-quality
  - analysis
---

# Finding Duplicate-Intent Functions

## Overview

LLM-generated codebases accumulate semantic duplicates: functions that serve the same purpose but were implemented independently. Classical copy-paste detectors (jscpd) find syntactic duplicates but miss "same intent, different implementation."

This skill uses a two-phase approach: classical extraction followed by LLM-powered intent clustering.

## When to Use

- Codebase has grown organically with multiple contributors (human or LLM)
- You suspect utility functions have been reimplemented multiple times
- Before major refactoring to identify consolidation opportunities
- After jscpd has been run and syntactic duplicates are already handled

## Quick Reference

| Phase | Tool | Model | Output |
|-------|------|-------|--------|
| 1. Extract | Extract function catalog | - | `catalog.json` |
| 2. Categorize | Categorize by domain | haiku model | `categorized.json` |
| 3. Split | Split by category | - | `categories/*.json` |
| 4. Detect | Find duplicates per category | opus model | `duplicates/*.json` |
| 5. Report | Generate prioritized report | - | `report.md` |

## Process

### Phase 1: Extract Function Catalog

Extract all functions from source files. Focus on:
- Exported functions and public methods
- Files in utility/helper directories
- Excluding test files (`*.test.*`, `*.spec.*`, `__tests__/**`)

For each function capture:
- Function name and signature
- File path and location
- ~15 lines of context (enough to understand intent)

### Phase 2: Categorize by Domain

Dispatch a **haiku** subagent to categorize functions by domain.

Insert the function catalog into the prompt. Save output as `categorized.json` with functions grouped into domains like:
- String manipulation
- Validation
- Path operations
- Error formatting
- Date/time formatting
- API response shaping

### Phase 3: Split into Categories

Create one JSON file per category. Only categories with 3+ functions are worth analyzing for duplicates.

### Phase 4: Find Duplicates (Per Category)

For each category file, dispatch an **opus** subagent to find semantic duplicates.

Opus is required here (not haiku) — subtle semantic matches require stronger reasoning. The subagent should identify:
- Functions with same intent, different implementation
- Recommended "survivor" function (the one to keep)
- Confidence level (HIGH/MEDIUM/LOW)
- Reasoning for the grouping

Save each output as `./duplicates/{category}.json`.

### Phase 5: Generate Report

Produce a prioritized markdown report grouped by confidence level.

For each duplicate group, report:
- All function names and file locations
- Recommended survivor
- Confidence level
- Brief reasoning

### Phase 6: Human Review

Review the report. For HIGH confidence duplicates:
1. Verify the recommended survivor has tests covering all use cases
2. Update callers to use the survivor
3. Delete the duplicates
4. Run tests to confirm no regressions

## High-Risk Duplicate Zones

Focus extraction on these areas first — they accumulate duplicates fastest:

| Zone | Common Duplicates |
|------|-------------------|
| `utils/`, `helpers/`, `lib/` | General utilities reimplemented |
| Validation code | Same checks written multiple ways |
| Error formatting | Error-to-string conversions |
| Path manipulation | Joining, resolving, normalizing paths |
| String formatting | Case conversion, truncation, escaping |
| Date formatting | Same formats implemented repeatedly |
| API response shaping | Similar transformations for different endpoints |

## Common Mistakes

**Extracting too much**: Focus on exported functions and public methods. Internal helpers are less likely to be duplicated across files.

**Skipping the categorization step**: Going straight to duplicate detection on the full catalog produces noise. Categories focus the comparison.

**Using haiku for duplicate detection**: Haiku is cost-effective for categorization but misses subtle semantic duplicates. Use Opus for the actual duplicate analysis.

**Consolidating without tests**: Before deleting duplicates, ensure the survivor has tests covering all use cases of the deleted functions.

## Red Flags

**Never:**
- Delete duplicates without verifying the survivor has adequate test coverage
- Use a cheap model for the duplicate detection phase (use opus)
- Skip categorization and try to find duplicates in the full catalog at once

**Always:**
- Run full test suite after consolidation
- Verify all callers have been updated before deletion
- Start with HIGH confidence duplicates before attempting MEDIUM or LOW
