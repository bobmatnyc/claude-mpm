---
title: Claude MPM for Non-Technical Users
version: 1.0.0
last_updated: 2026-01-07
audience: Founders, PMs, and business leaders
status: current
---

# Claude MPM for Non-Technical Users

**For Founders, Product Managers, and Business Leaders**

This guide helps non-technical users leverage Claude MPM to understand and oversee their technical projects without coding experience.

> 📖 **Background Reading**: [This One's for the Founders](https://open.substack.com/pub/hyperdev/p/this-ones-for-the-founders?r=nff5&utm_campaign=post&utm_medium=web&showWelcomeOnShare=true) - The story behind why we built this for non-technical leaders.

## Table of Contents

1. [What You Need](#what-you-need)
2. [Quick Installation](#quick-installation)
3. [Getting Started](#getting-started)
4. [Founders Mode](#founders-mode)
5. [Common Use Cases](#common-use-cases)
6. [Questions to Ask](#questions-to-ask)
7. [Understanding Responses](#understanding-responses)
8. [Glossary](#glossary)

---

## What You Need

**Prerequisites (one-time setup):**

1. **Claude subscription** - Get it at https://claude.ai
   - Free tier works for trying it out, but you'll hit usage limits quickly
   - Claude Max recommended for regular use—unlimited access to Claude Code
   - No programming knowledge required!

2. **A computer** - Mac, Windows, or Linux

3. **Your code on GitHub** - Just the URL (like `https://github.com/company/repo`)
   - If your code isn't on GitHub yet, ask your development team for the repository URL

That's it. Everything else gets installed in the next step.

---

## Quick Installation

### Step 1: Install Claude Code

**Mac/Linux:**
```bash
npm install -g @anthropic-ai/claude-code
```

**Windows:**
Visit https://docs.anthropic.com/en/docs/claude-code and follow the Windows installation instructions.

**Verify it worked:**
```bash
claude --version
```
You should see a version number. If not, try the install command again or reach out for help.

### Step 2: Install Claude MPM

```bash
pipx install claude-mpm
```

**If you don't have pipx:**
```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```
Close and reopen your terminal, then try the `pipx install claude-mpm` command again.

**Verify it worked:**
```bash
claude-mpm --version
```

### Step 3: Set Your API Key

**Get your key:**
1. Go to https://console.anthropic.com/settings/keys
2. Click "Create Key"
3. Copy it (starts with `sk-ant-api03-...`)

**Save it permanently:**

**Mac/Linux:**
```bash
# pragma: allowlist secret
echo 'export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"' >> ~/.zshrc
source ~/.zshrc
```

**Windows:**
1. Search for "Environment Variables"
2. Click "Edit system environment variables"
3. Click "Environment Variables"
4. Under "User variables", click "New"
5. Variable name: `ANTHROPIC_API_KEY`
6. Variable value: Your API key
7. Click OK

**Done!** One-time setup complete.

---

## Getting Started

### Download Your Code

1. **Create a workspace folder:**
   ```bash
   mkdir ~/Projects
   cd ~/Projects
   ```

2. **Start Claude:**
   ```bash
   claude
   ```

3. **Tell Claude to download your code:**
   ```
   Download the code from https://github.com/yourcompany/yourproject
   ```

   Replace with your actual GitHub URL. Claude handles everything else.

### Ask Your First Question

That's it! You can now ask Claude anything about your code:

```
What does this project do?
```

```
Show me what changed this week
```

```
Are there any security issues?
```

Claude has full access to your codebase and can answer in plain English.

**Every time you want to use it:**
1. `cd ~/Projects/yourproject`
2. `claude`
3. Ask your question

---

## Founders Mode

For technically accurate answers explained in plain English (no jargon), enable **Founders Mode**.

### How to Enable Founders Mode

**Method 1: Using Command Palette (Recommended)**

1. In Claude Code, press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac)
2. Type "output style"
3. Select **"Claude MPM Founders"** from the dropdown
4. All answers will be technically accurate but explained in plain, non-technical language

**Method 2: Ask Claude Directly**

```
Switch to Founders Mode. From now on, explain everything in business terms, not technical jargon.
```

### Use Founders Mode When You:

- Want answers in plain English without jargon
- Need explanations focused on business impact
- Prefer analogies to technical details
- Want to understand security risks in simple terms
- Need to brief non-technical stakeholders

### What Changes in Founders Mode

Every answer will be:
- Technically accurate but explained in plain English
- Focused on business impact
- Using analogies and examples you understand
- Clear about when something is genuinely complex (not oversimplified)

**Example Comparison:**

**Before (Technical Mode):**
> "Your authentication module uses bcrypt for password hashing with a cost factor of 12. JWT tokens are signed using RS256 with a 15-minute expiration."

**After (Founders Mode):**
> "Your login system is secure. Passwords are scrambled in a way that makes them nearly impossible to crack (industry standard). Login sessions expire after 15 minutes of inactivity for security."

---

## Common Use Cases

### 1. Project Understanding

**Goal:** Understand what your technical team has built

**Questions to ask:**
- "What does this project do? Explain it like I'm not technical."
- "What are the main features?"
- "How does the system work at a high level?"
- "What technologies are being used and why?"

**Real-world example:**
```
Founder: What does this codebase do?

Claude (Founders Mode): This is an e-commerce platform. It lets customers browse products, add them to a cart, and check out. Behind the scenes, it handles payments securely, manages inventory, and sends confirmation emails. Think of it as the digital version of a store—storefront, cash register, and stockroom all in one.
```

### 2. Security Review

**Goal:** Understand security risks in your project

**Questions to ask:**
- "Are there any security vulnerabilities I should know about?"
- "Is customer data being protected properly?"
- "What are the biggest security risks in this code?"
- "Is our login system secure?"

**Real-world example:**
```
Founder: Is customer data being protected properly?

Claude (Founders Mode): There are two concerns:

1. ✅ GOOD: Passwords are encrypted (industry standard)
2. ⚠️ NEEDS ATTENTION: Customer credit card data is stored in the database. Industry best practice is to never store card numbers—use a payment processor like Stripe instead.

This is a compliance risk (PCI-DSS) that could lead to fines if there's a breach.
```

### 3. Code Quality Assessment

**Goal:** Understand if the code is maintainable and well-built

**Questions to ask:**
- "Is this code well-organized?"
- "Will this be easy for new developers to work with?"
- "Are there any major technical debt issues?"
- "What would you improve if you were starting over?"

**Real-world example:**
```
Founder: Will this be easy for new developers to work with?

Claude (Founders Mode): Partially. Good news:
- Clear folder structure
- Well-documented API endpoints
- Automated tests (like a safety net)

Needs work:
- No setup documentation (new devs will struggle to get started)
- Complex database queries without comments
- Inconsistent coding style (like different handwriting on every page)

Estimate: A new developer could get productive in 3-5 days instead of 1-2 days with better documentation.
```

### 4. Recent Changes Review

**Goal:** Stay informed about what changed recently

**Questions to ask:**
- "What changed this week?"
- "Show me the most important updates from the last sprint"
- "What new features were added recently?"
- "Were there any bug fixes in the last month?"

**Real-world example:**
```
Founder: What changed this week?

Claude (Founders Mode): Three main updates:

1. **New Feature**: Added password reset via email
   - Users can now recover their accounts
   - Industry-standard security flow

2. **Bug Fix**: Fixed shopping cart total calculation
   - Was adding tax twice on some orders
   - Affected ~50 orders this month (now refunded)

3. **Performance**: Sped up product search
   - Search now returns results in 0.2 seconds instead of 3 seconds
   - Much better user experience
```

### 5. Technical Debt Discovery

**Goal:** Identify areas that need refactoring or improvement

**Questions to ask:**
- "What are the biggest problems in this codebase?"
- "What will slow us down as we grow?"
- "Are there any quick wins to improve code quality?"
- "What should we fix before hiring more developers?"

### 6. Dependency & Security Updates

**Goal:** Understand if libraries and dependencies are up-to-date

**Questions to ask:**
- "Are our dependencies up to date?"
- "Are there any security updates we should install?"
- "What libraries have known vulnerabilities?"

---

## Questions to Ask

### Project Overview
- "What does this project do?" (plain English explanation)
- "What are the main features?"
- "How does the architecture work?"
- "What technologies are being used and why?"

### Security & Compliance
- "Are there any security vulnerabilities?"
- "Is customer data being protected properly?"
- "What are the biggest security risks?"
- "Are we following best practices for [specific compliance requirement]?"

### Code Quality
- "Is this code well-organized?"
- "What would make this easier to maintain?"
- "Are there any major technical debt issues?"
- "What would you improve if starting over?"

### Recent Activity
- "What changed this week?"
- "Show me the most important updates"
- "What new features were added?"
- "Were there any bug fixes?"

### Planning & Roadmap
- "What would it take to add [new feature]?"
- "What are the risks of [proposed change]?"
- "How long would [feature] take to implement?"
- "What would we need to scale to 10x users?"

### Team Handoffs
- "Summarize the current state of the project for a new developer"
- "What documentation is missing?"
- "What should a new PM know about this codebase?"

---

## Understanding Responses

### Reading Technical Information

Claude MPM (especially in Founders Mode) will:
- Use plain English whenever possible
- Provide analogies for complex concepts
- Focus on business impact over technical details
- Be honest about complexity (not oversimplify)

### When to Ask Follow-up Questions

**If you don't understand something:**
```
Can you explain that in simpler terms?
```

**If you need more detail:**
```
Can you give me more details about [specific topic]?
```

**If you need context:**
```
Why is this important for the business?
```

**If you need action items:**
```
What should I do about this?
```

### Red Flags to Watch For

1. **Security Issues**: Take seriously immediately
2. **Data Privacy Concerns**: Consult legal/compliance
3. **Technical Debt**: Budget time to address
4. **Outdated Dependencies**: Schedule updates
5. **Missing Tests**: Higher risk of bugs

---

## Glossary

**API (Application Programming Interface)**: How different software systems talk to each other (like a menu at a restaurant)

**Backend**: The server-side code that runs behind the scenes (like a kitchen in a restaurant)

**Bug**: A mistake in the code that causes unexpected behavior

**Codebase**: All the code files that make up your project

**Database**: Where data is stored (like a filing cabinet)

**Dependency**: External code libraries your project relies on (like ingredients for a recipe)

**Deployment**: Making your code live for users

**Frontend**: The user-facing part of the application (like the dining room in a restaurant)

**Git/GitHub**: Version control system that tracks code changes (like Track Changes in Microsoft Word)

**Repository (Repo)**: A folder containing all your project's code and history

**Security Vulnerability**: A weakness in the code that could be exploited by attackers

**Technical Debt**: Shortcuts taken in code that will need fixing later (like deferring maintenance on a building)

**Test/Testing**: Automated checks that verify code works correctly

---

## Next Steps

### Learn More

- **[Installation Guide](../getting-started/installation.md)** - Detailed installation instructions
- **[User Guide](../user/user-guide.md)** - Complete user documentation
- **[FAQ](../guides/FAQ.md)** - Common questions answered

### Get Help

- **Documentation Issues**: Open an issue on [GitHub](https://github.com/bobmatnyc/claude-mpm/issues)
- **Questions**: Ask in Claude Code with `/help` command
- **Community**: Join discussions on GitHub Discussions

### Advanced Topics

Once comfortable with basics:
- **[Developer Use Cases](./developers.md)** - For technical users
- **[Team Collaboration](./teams.md)** - Multi-user workflows
- **[Skills Guide](../user/skills-guide.md)** - Advanced features

---

**Last updated:** 2026-01-07
**Version:** 1.0.0
**Feedback:** Submit issues at https://github.com/bobmatnyc/claude-mpm/issues
