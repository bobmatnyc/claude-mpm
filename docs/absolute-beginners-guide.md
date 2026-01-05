---
title: Absolute Beginner's Guide to Claude MPM
version: 2.0.0
last_updated: 2026-01-05
audience: Non-technical founders and business leaders
status: current
---

# Absolute Beginner's Guide to Using Claude MPM

**For Non-Technical Founders**

This guide gets you from zero to asking questions about your code in under 10 minutes. No programming experience required.

## Table of Contents

1. [What You Need](#what-you-need)
2. [Install (3 Steps)](#install-3-steps)
3. [Start Using It](#start-using-it)
4. [Switch to Founders Mode](#switch-to-founders-mode)
5. [Questions to Ask](#questions-to-ask)
6. [Glossary](#glossary)

---

## What You Need

1. **Claude subscription** - Go to https://claude.ai (Claude Max recommended for unlimited usage)
   - Free tier works for trying it out, but you'll hit usage limits quickly
   - Claude Max recommended for regular use—gives you unlimited access to Claude Code

2. **A computer** - Mac, Windows, or Linux

3. **Your code on GitHub** - Just the URL (like `https://github.com/company/repo`)

That's it. Everything else gets installed in the next step.

---

## Install (3 Steps)

### 1. Install Claude Code

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
You should see a version number. If not, try the install command again.

### 2. Install Claude MPM

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

### 3. Set Your API Key

**Get your key:**
1. Go to https://console.anthropic.com/settings/keys
2. Click "Create Key"
3. Copy it (starts with `sk-ant-api03-...`)

**Save it permanently:**

**Mac/Linux:**
```bash
echo 'export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"' >> ~/.zshrc  # pragma: allowlist secret
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

**Done!** One-time setup complete. You'll never need to do this again.

---

## Start Using It

### Get Your Code

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

### Ask Questions

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

## Switch to Founders Mode

For technically accurate answers explained in plain English (no jargon), enable Founders Mode.

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

## Questions to Ask

### Security
```
Are there any security vulnerabilities in our code?
```

```
Show me how user passwords are stored. Is this secure?
```

```
What happens if we get hacked? How would we know?
```

### Team & Progress
```
Show me what the team worked on this week
```

```
Who's working on what right now?
```

```
Are there any blocked tasks or issues?
```

### Code Quality
```
Give me a health check of our codebase
```

```
What technical debt do we have? Should I be worried?
```

```
How well tested is our code?
```

### Features & Planning
```
We want to add [feature name]. How big of a project is this?
```

```
Is [feature name] ready to ship? What are the risks?
```

```
Explain how [system component] works in simple terms
```

### Business Impact
```
What would break if [person name] left the company?
```

```
Can our system handle 10x more users?
```

```
What are our biggest technical risks right now?
```

---

## Glossary

Quick reference for technical terms you'll hear:

**Repository (Repo)** - A folder with all your code
> Like a project folder with full history of every change

**Commit** - A saved snapshot of code changes
> Like "Save Version" in Google Docs

**Pull Request (PR)** - A proposed change to the code
> Like suggesting edits in a shared document

**Technical Debt** - Quick fixes that need proper solutions later
> Like duct tape on a leak - works now, but you'll need a real fix eventually

**Bug** - An error that causes incorrect behavior
> Like a typo in a contract

**Deploy** - Publishing changes live to users
> Like launching a new product

**API** - How different software talks to each other
> Like a waiter between you and the kitchen

**Frontend** - The part users see (website/app)
> The storefront

**Backend** - The logic and processing behind the scenes
> The warehouse and operations

**Database** - Where data is stored permanently
> A highly organized filing cabinet

**Security Vulnerability** - A weakness that could be exploited
> A hole in your building's security

**Test Coverage** - Percentage of code that's tested
> How much of your product gets quality-checked before shipping

For more terms, ask Claude:
```
What does [technical term] mean in simple English?
```

---

## Getting Help

**If Claude's answer is too technical:**
```
Explain that in simpler terms. Use a business analogy.
```

**If you need a decision:**
```
Skip the details. What should I do? What's the business impact?
```

**For executive summaries:**
```
[FOUNDERS MODE] Give me the executive summary of [topic]
```

**When to involve your CTO:**
- Security issues Claude identifies
- Major architectural decisions
- System outages or critical bugs
- Before making big technical investments

**Remember:** Claude MPM helps you ask better questions and understand your code. It doesn't replace your technical team - it helps you work with them more effectively.

---

**That's it!** You now know everything you need to start using Claude MPM.

**Next steps:**
1. Install it (takes 5 minutes)
2. Download your code (1 command)
3. Start asking questions (just talk naturally)

Good luck!

---

**Document Information**:
- **Version**: 2.0.0
- **Last Updated**: 2026-01-05
- **Reading Time**: 5 minutes
- **Setup Time**: 10 minutes
