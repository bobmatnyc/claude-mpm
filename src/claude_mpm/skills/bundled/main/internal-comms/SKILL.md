---
name: internal-comms
description: A set of resources to help me write all kinds of internal communications, using the formats that my company likes to use. Claude should use this skill whenever asked to write some sort of internal communications (status reports, leadership updates, 3P updates, company newsletters, FAQs, incident reports, project updates, etc.).
license: Complete terms in LICENSE.txt
progressive_disclosure:
  entry_point:
    summary: "Write internal communications using company-specific formats and guidelines"
    when_to_use: "Writing 3P updates, newsletters, FAQs, status reports, leadership updates, project updates, or incident reports"
    quick_start: |
      1. Identify communication type (3P update, newsletter, FAQ, etc.)
      2. Load appropriate guideline from examples/ directory
      3. Follow specific instructions for formatting, tone, and content
      Available: examples/3p-updates.md, examples/company-newsletter.md, examples/faq-answers.md, examples/general-comms.md
    note: "Already optimal at 32 lines - examples/ directory provides all format guidelines, no fragmentation needed"
  references: []
---

## When to use this skill
To write internal communications, use this skill for:
- 3P updates (Progress, Plans, Problems)
- Company newsletters
- FAQ responses
- Status reports
- Leadership updates
- Project updates
- Incident reports

## How to use this skill

To write any internal communication:

1. **Identify the communication type** from the request
2. **Load the appropriate guideline file** from the `examples/` directory:
    - `examples/3p-updates.md` - For Progress/Plans/Problems team updates
    - `examples/company-newsletter.md` - For company-wide newsletters
    - `examples/faq-answers.md` - For answering frequently asked questions
    - `examples/general-comms.md` - For anything else that doesn't explicitly match one of the above
3. **Follow the specific instructions** in that file for formatting, tone, and content gathering

If the communication type doesn't match any existing guideline, ask for clarification or more context about the desired format.

## Keywords
3P updates, company newsletter, company comms, weekly update, faqs, common questions, updates, internal comms
