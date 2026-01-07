# Claude MPM Licensing Implementation Guide

**Complete reference for implementing Elastic License 2.0**

**Copyright Holder:** Bob Matsuoka (bob@matsuoka.com)  
**License:** Elastic License 2.0  
**SPDX Identifier:** `Elastic-2.0`  
**Date:** 2025

---

## Table of Contents

1. [LICENSE File (Copy to Repo Root)](#1-license-file)
2. [../../LICENSE-FAQ.md (Copy to Repo Root)](#2-license-faqmd)
3. [README.md License Section](#3-readmemd-license-section)
4. [pyproject.toml Updates](#4-pyprojecttoml-updates)
5. [Source File Headers](#5-source-file-headers)
6. [CONTRIBUTING.md Updates](#6-contributingmd-updates)
7. [CHANGELOG Entry](#7-changelog-entry)
8. [Implementation Checklist](#8-implementation-checklist)
9. [Response Templates](#9-response-templates-for-inquiries)

---

## 1. LICENSE File

**Action:** Create `LICENSE` in repository root with this exact content:

```text
Elastic License 2.0

Copyright (c) 2024-2025 Bob Matsuoka
Contact: bob@matsuoka.com

## Acceptance

By using the software, you agree to all of the terms and conditions below.

## Copyright License

The licensor grants you a non-exclusive, royalty-free, worldwide,
non-sublicensable, non-transferable license to use, copy, distribute, make
available, and prepare derivative works of the software, in each case subject to
the limitations and conditions below.

## Limitations

You may not provide the software to third parties as a hosted or managed
service, where the service provides users with access to any substantial set of
the features or functionality of the software.

You may not move, change, disable, or circumvent the license key functionality
in the software, and you may not remove or obscure any functionality in the
software that is protected by the license key.

You may not alter, remove, or obscure any licensing, copyright, or other notices
of the licensor in the software. Any use of the licensor's trademarks is subject
to applicable law.

## Patents

The licensor grants you a license, under any patent claims the licensor can
license, or becomes able to license, to make, have made, use, sell, offer for
sale, import and have imported the software, in each case subject to the
limitations and conditions in this license. This license does not cover any
patent claims that you cause to be infringed by modifications or additions to
the software. If you or your company make any written claim that the software
infringes or contributes to infringement of any patent, your patent license for
the software granted under these terms ends immediately. If your company makes
such a claim, your patent license ends immediately for work on behalf of your
company.

## Notices

You must ensure that anyone who gets a copy of any part of the software from you
also gets a copy of these terms.

If you modify the software, you must include in any modified copies of the
software prominent notices stating that you have modified the software.

## No Other Rights

These terms do not imply any licenses other than those expressly granted in
these terms.

## Termination

If you use the software in violation of these terms, such use is not licensed,
and your licenses will automatically terminate. If the licensor provides you
with a notice of your violation, and you cease all violation of this license no
later than 30 days after you receive that notice, your licenses will be
reinstated retroactively. However, if you violate these terms after such
reinstatement, any additional violation of these terms will cause your licenses
to terminate automatically and permanently.

## No Liability

*As far as the law allows, the software comes as is, without any warranty or
condition, and the licensor will not be liable to you for any damages arising
out of these terms or the use or nature of the software, under any kind of legal
claim.*

## Definitions

The **licensor** is the entity offering these terms, and the **software** is the
software the licensor makes available under these terms, including any portion
of it.

**you** refers to the individual or entity agreeing to these terms.

**your company** is any legal entity, sole proprietorship, or other kind of
organization that you work for, plus all organizations that have control over,
are under the control of, or are under common control with that
organization. **control** means ownership of substantially all the assets of an
entity, or the power to direct its management and policies by vote, contract, or
otherwise. Control can be direct or indirect.

**your licenses** are all the licenses granted to you for the software under
these terms.

**use** means anything you do with the software requiring one of your licenses.

**trademark** means trademarks, service marks, and similar rights.
```

---

## 2. ../../LICENSE-FAQ.md

**Action:** Create `../../LICENSE-FAQ.md` in repository root with this content:

```markdown
# Claude MPM Licensing FAQ

## TL;DR

**✅ You CAN:**
- Use Claude MPM internally in your company (any size)
- Build products and services that use Claude MPM
- Modify and redistribute Claude MPM
- Provide consulting/integration services
- Embed Claude MPM in your applications

**❌ You CANNOT:**
- Offer Claude MPM as a hosted SaaS service
- Provide managed Claude MPM hosting to customers
- Remove or modify license notices

**Need SaaS rights?** Contact bob@matsuoka.com for commercial licensing.

---

## Detailed Q&A

### What is the Elastic License 2.0?

The Elastic License 2.0 is a source-available license that allows free use with one main restriction: you cannot offer the software as a hosted service to others. It was created by Elastic (the company behind Elasticsearch) to prevent cloud providers from reselling their work.

### Is this "open source"?

Not according to the OSI (Open Source Initiative) definition, but the source code is fully available, and you can modify and redistribute it. This is sometimes called "source-available" or "fair-code."

### Why did you choose this license?

To protect Claude MPM from SaaS providers who might take the work and offer it as a competing hosted service without contributing back to development. This ensures the project remains sustainable.

---

## Common Use Cases

### ✅ ALLOWED: Internal Business Use

**Scenario:** Your company uses Claude MPM to automate development workflows.

**Allowed:** Yes, unlimited use for internal purposes, any company size.

---

### ✅ ALLOWED: Building Products with Claude MPM

**Scenario:** You build a development tool that uses Claude MPM as a component.

**Allowed:** Yes, you can sell your product. The restriction is on offering *Claude MPM itself* as a service, not products that use it.

**Example:** A CI/CD tool that uses Claude MPM for agent orchestration is fine.

---

### ✅ ALLOWED: Consulting Services

**Scenario:** You offer consulting to help companies set up and customize Claude MPM.

**Allowed:** Yes, you can charge for consulting, training, integration, and support services.

---

### ✅ ALLOWED: On-Premise Deployment for Clients

**Scenario:** You install and configure Claude MPM on a client's infrastructure.

**Allowed:** Yes, as long as you're deploying it for their internal use, not running it as a service you control.

---

### ✅ ALLOWED: Modified Versions

**Scenario:** You fork Claude MPM and add features for your needs.

**Allowed:** Yes, you can modify it. Just keep the license notices and note what you changed.

---

### ❌ NOT ALLOWED: SaaS/Hosted Service

**Scenario:** You want to offer "Claude MPM as a Service" where customers sign up and use your hosted instance.

**Not Allowed:** This requires a commercial license. Contact us to discuss terms.

---

### ❌ NOT ALLOWED: Managed Service Provider

**Scenario:** You offer managed Claude MPM hosting where you run instances for multiple clients.

**Not Allowed:** This is a managed service and requires a commercial license.

---

### ⚠️ GRAY AREA: Internal SaaS Platform

**Scenario:** You build an internal platform for your company's developers that uses Claude MPM.

**Typically Allowed:** If it's genuinely internal (employees only), this is usually fine. If you're providing it to external clients as a service, you need a commercial license.

**Contact us if unsure:** bob@matsuoka.com

---

## Additional Questions

### Can I contribute to Claude MPM?

Yes! Contributions are welcome. By contributing, you agree that your contributions will be licensed under the same Elastic License 2.0 terms.

### Can I redistribute Claude MPM?

Yes, you can distribute it (modified or unmodified) as long as:
1. You include the LICENSE file
2. You don't offer it as a hosted service
3. You don't remove license notices
4. If modified, you note the modifications

### What if I want to offer Claude MPM as a service?

Contact bob@matsuoka.com to discuss commercial licensing. We offer reasonable terms for companies that want to provide hosted services.

### What about agents and configurations I create?

**Your agents, configurations, and workflows are yours.** The license only covers the Claude MPM software itself, not the content you create with it.

### What happens if I violate the license?

Your license automatically terminates. However, if we notify you and you stop the violation within 30 days, your license is reinstated. Continued violations result in permanent termination.

### I'm still not sure if my use case is allowed

Email bob@matsuoka.com with your specific scenario. We're happy to clarify and are reasonable about edge cases.

---

## Commercial Licensing

For use cases that require:
- Offering Claude MPM as a hosted SaaS service
- Providing managed Claude MPM hosting
- Embedding in proprietary systems with SaaS components
- Custom licensing terms

**Contact:** bob@matsuoka.com

---

**Questions?** bob@matsuoka.com  
**GitHub Issues:** https://github.com/bobmatnyc/claude-mpm/issues  
**License Text:** https://github.com/bobmatnyc/claude-mpm/blob/main/LICENSE
```

---

## 3. README.md License Section

**Action:** Add this section to README.md (near the end, before Contributing):

```markdown
## 📜 License

Claude MPM is licensed under the **Elastic License 2.0**.

### What This Means

**✅ You can freely:**
- Use Claude MPM for internal business purposes (any company size)
- Build commercial products that use Claude MPM
- Modify and redistribute Claude MPM
- Provide consulting and integration services

**❌ You cannot:**
- Offer Claude MPM as a hosted SaaS service
- Provide managed hosting of Claude MPM to customers

### Why This License?

We chose the Elastic License 2.0 to:
- Keep Claude MPM freely available for most use cases
- Ensure sustainable development by preventing free-riding SaaS providers
- Protect against large cloud providers reselling our work

### Need SaaS Rights?

If you want to offer Claude MPM as a hosted service, we offer commercial licensing. Contact bob@matsuoka.com

### Questions?

See our [Licensing FAQ](../../LICENSE-FAQ.md) for detailed examples and scenarios.
```

**Alternative (shorter version):**

```markdown
## 📜 License

[![License](https://img.shields.io/badge/License-Elastic_2.0-blue.svg)](LICENSE)

Licensed under the [Elastic License 2.0](LICENSE) - free for internal use and commercial products.

**Main restriction:** Cannot offer as a hosted SaaS service without a commercial license.

📖 [Licensing FAQ](../../LICENSE-FAQ.md) | 💼 Commercial licensing: bob@matsuoka.com
```

---

## 4. pyproject.toml Updates

**Action:** Update `pyproject.toml` with these changes:

```toml
[project]
name = "claude-mpm"
version = "4.26.x"  # your current version
description = "Multi-Agent Project Manager for Claude Code"
license = {text = "Elastic-2.0"}
authors = [
    {name = "Bob Matsuoka", email = "bob@matsuoka.com"}
]

classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: Other/Proprietary License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
```

**Key changes:**
- `license = {text = "Elastic-2.0"}` - Sets the SPDX identifier
- `"License :: Other/Proprietary License"` - PyPI classifier (Elastic-2.0 isn't OSI-approved)

---

## 5. Source File Headers

**Action:** Add this header to key source files (do gradually as you touch files):

### Python Files

```python
# Copyright (c) 2024-2025 Bob Matsuoka
# Licensed under the Elastic License 2.0
# See LICENSE file in the project root for full license information.
```

### Priority Files to Update First

1. `src/claude_mpm/__init__.py`
2. `src/claude_mpm/cli/__main__.py`
3. `src/claude_mpm/core/container.py`
4. `src/claude_mpm/services/core/interfaces.py`

### Full Header (for important files)

```python
"""
Claude MPM - Multi-Agent Project Manager

Copyright (c) 2024-2025 Bob Matsuoka
Licensed under the Elastic License 2.0

You may use this software for internal business purposes or non-commercial use.
You may NOT provide this software as a hosted or managed service.

See LICENSE file for full terms.
Contact: bob@matsuoka.com
"""
```

---

## 6. CONTRIBUTING.md Updates

**Action:** Add or update the license section in CONTRIBUTING.md:

```markdown
## License

By contributing to Claude MPM, you agree that your contributions will be
licensed under the Elastic License 2.0, the same license that covers the project.

### What This Means for Contributors

- Your contributions become part of Claude MPM under Elastic License 2.0
- You retain copyright to your contributions
- You grant Bob Matsuoka and the project the right to use your contributions
- You confirm you have the right to submit the contribution

### Contributor License Agreement

For significant contributions, we may ask you to sign a Contributor License
Agreement (CLA). This protects both you and the project.

### Questions?

If you have questions about licensing your contribution, contact bob@matsuoka.com
```

---

## 7. CHANGELOG Entry

**Action:** Add this entry to CHANGELOG.md for the next release:

```markdown
## [X.X.X] - 2025-XX-XX

### Changed

- **License Update**: Changed license to Elastic License 2.0
  - **For most users**: No action required - internal and commercial use remains free
  - **SaaS providers**: Contact bob@matsuoka.com for commercial licensing
  - See [../../LICENSE-FAQ.md](../../LICENSE-FAQ.md) for detailed use cases and examples
  
### Why This Change

To ensure sustainable development of Claude MPM by preventing SaaS providers
from reselling the project without contributing back, while keeping it freely
available for the vast majority of use cases.
```

---

## 8. Implementation Checklist

### Phase 1: Core Files (Do First)

- [ ] Create `LICENSE` file in repository root
- [ ] Create `../../LICENSE-FAQ.md` in repository root
- [ ] Update `pyproject.toml` with license identifier
- [ ] Update README.md with license section
- [ ] Commit: `git commit -m "chore: Update license to Elastic License 2.0"`

### Phase 2: Documentation

- [ ] Update CONTRIBUTING.md with license section
- [ ] Add CHANGELOG entry
- [ ] Update any other docs mentioning licensing

### Phase 3: Source Headers (Gradual)

- [ ] Add header to `src/claude_mpm/__init__.py`
- [ ] Add header to `src/claude_mpm/cli/__main__.py`
- [ ] Add headers to other files as you touch them

### Phase 4: External Updates

- [ ] Update GitHub repository description
- [ ] Verify GitHub shows correct license
- [ ] Update PyPI on next release
- [ ] Announce to users (if appropriate)

### Verification

After implementation, verify:

- [ ] `LICENSE` file exists at repository root
- [ ] `../../LICENSE-FAQ.md` exists and is linked from README
- [ ] README clearly explains what users can/cannot do
- [ ] `pyproject.toml` has `license = {text = "Elastic-2.0"}`
- [ ] GitHub recognizes the license
- [ ] Key source files have copyright headers

---

## 9. Response Templates for Inquiries

### Template: General License Question

```
Subject: RE: Claude MPM License Question

Hi [Name],

Thanks for reaching out about Claude MPM licensing.

Claude MPM is licensed under the Elastic License 2.0, which means:

✅ You CAN:
- Use it internally in your company (any size)
- Build commercial products with it
- Modify and redistribute it
- Provide consulting services

❌ You CANNOT (without a commercial license):
- Offer it as a hosted SaaS service
- Provide managed hosting to customers

Based on your description, [your use case assessment].

If you need SaaS/hosting rights, I'm happy to discuss commercial licensing terms.

Let me know if you have other questions!

Best,
Bob Matsuoka
bob@matsuoka.com
```

### Template: SaaS/Commercial License Inquiry

```
Subject: RE: Claude MPM Commercial Licensing

Hi [Name],

Thanks for your interest in commercial licensing for Claude MPM.

For SaaS/hosted service use cases, we offer commercial licenses. To help me
understand your needs, could you share:

1. Brief description of your use case
2. Expected scale (users, instances)
3. Timeline for deployment

I'll then provide appropriate licensing options.

Best,
Bob Matsuoka
bob@matsuoka.com
```

### Template: Confirming Allowed Use

```
Subject: RE: Claude MPM License - Use Case Confirmed

Hi [Name],

Good news! Your use case is fully covered under the Elastic License 2.0:

[Describe their use case] is allowed because [reason - internal use / building
products / consulting / etc.].

No commercial license needed. You're free to proceed.

Let me know if you have other questions!

Best,
Bob Matsuoka
bob@matsuoka.com
```

---

## Quick Reference

| Item | Value |
|------|-------|
| **License** | Elastic License 2.0 |
| **SPDX** | `Elastic-2.0` |
| **Copyright** | Bob Matsuoka |
| **Contact** | bob@matsuoka.com |
| **PyPI Classifier** | `License :: Other/Proprietary License` |

### Allowed vs Not Allowed

| Use Case | Allowed? |
|----------|----------|
| Internal business use | ✅ Yes |
| Commercial products using Claude MPM | ✅ Yes |
| Consulting/integration services | ✅ Yes |
| Modify and redistribute | ✅ Yes |
| Fork for internal use | ✅ Yes |
| Hosted SaaS service | ❌ No (commercial license required) |
| Managed hosting for clients | ❌ No (commercial license required) |

---

## Git Commands Summary

```bash
# Implementation commands
git add LICENSE ../../LICENSE-FAQ.md
git add pyproject.toml README.md
git add CONTRIBUTING.md CHANGELOG.md
git commit -m "chore: Update license to Elastic License 2.0

- Add Elastic License 2.0 as LICENSE file
- Add ../../LICENSE-FAQ.md with detailed use cases
- Update pyproject.toml with license identifier
- Update README with license section
- Update CONTRIBUTING.md with license terms

This change protects Claude MPM from SaaS free-riding while keeping
it freely available for internal use, commercial products, and consulting.

See ../../LICENSE-FAQ.md for detailed use cases."

git push origin main
```

---

**End of Implementation Guide**

*Generated for Claude MPM - Bob Matsuoka (bob@matsuoka.com)*
