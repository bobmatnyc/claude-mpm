# Claude MPM Teach Style: Comprehensive Teaching Framework Design

**Research Date**: 2025-12-03
**Status**: Complete
**Objective**: Design adaptive teaching system for Claude MPM beginners

---

## Executive Summary

This research synthesizes best practices from educational technology, AI assistants, and developer onboarding to design a comprehensive "Claude MPM Teach" style that adapts to user experience levels. The framework balances progressive disclosure, Socratic questioning, and error-driven learning to help beginners become proficient without dependency.

**Key Innovation**: Adaptive teaching that distinguishes between MPM-new vs. coding-new users, providing scaffolded support through Zone of Proximal Development principles while maintaining framework integrity.

---

## 1. Experience Level Assessment

### 1.1 Research Findings: Industry Patterns

**Adaptive Learning Platforms** (Market: $4.39B in 2025, 52.7% YoY growth):
- Built-in adaptive assessments adjust difficulty in real-time
- Provide immediate feedback and surface knowledge gaps
- Use AI-driven systems to personalize training

**Codecademy's 5-Step System**:
1. Hook (engagement)
2. Introduction to new material
3. Guided practice
4. Independent practice
5. Evaluation (with feedback loops)

**Skill Level Distinctions**:

| Level | Characteristics | Assessment Indicators |
|-------|----------------|----------------------|
| **Beginner** | Little/no coding knowledge; relies on tutorials; misses corner cases | Struggles with variables, loops, arrays; needs pattern to follow |
| **Intermediate** | 2-4 years experience; routine tasks familiar; needs debugging support | Builds tests if assigned; catches simple corner cases; solid fundamentals |
| **Advanced** | Expert problem-solver; mentors others; knows best practices from experience | Adept with algorithms, OOP, testing; contributes to community knowledge |

### 1.2 Claude MPM-Specific Assessment Design

**Two-Dimensional Assessment Matrix**:

```
Coding Experience
    ↑
    │ Quadrant 3:           Quadrant 4:
    │ Coding Expert         Coding Expert
    │ MPM New               MPM Familiar
    │ [Teach MPM concepts]  [Power user mode]
    │
    │ Quadrant 1:           Quadrant 2:
    │ Coding Beginner       Coding Beginner
    │ MPM New               MPM Familiar
    │ [Full scaffolding]    [Focus on coding]
    │
    └─────────────────────────────────→
                    MPM Experience
```

**Recommended Assessment Questionnaire** (Minimal, 3-5 questions):

```markdown
## Quick Assessment (Optional - Skip to Get Started)

To help me teach effectively, answer these quick questions:

1. **Coding Experience**
   - [ ] New to programming (< 6 months)
   - [ ] Learning programming (6 months - 2 years)
   - [ ] Comfortable with code (2+ years)
   - [ ] Professional developer (5+ years)

2. **Framework Experience**
   - [ ] First time using Claude MPM
   - [ ] Explored documentation
   - [ ] Used similar tools (GitHub Copilot, Cursor, etc.)

3. **Current Project**
   - [ ] New project (just starting)
   - [ ] Existing codebase (already has code)
   - [ ] Learning/experimenting (no production code)

4. **What do you want to accomplish first?**
   [Free text - helps determine immediate teaching focus]

5. **Preferred learning style** (optional)
   - [ ] Show me examples first
   - [ ] Explain concepts first
   - [ ] Let me try and correct me
```

**Assessment Scoring System**:

```python
# Pseudocode for adaptive teaching level
def determine_teaching_level(responses):
    coding_score = map_coding_experience(responses.coding_exp)
    mpm_score = map_mpm_experience(responses.framework_exp)

    if coding_score < 2 and mpm_score < 2:
        return "FULL_SCAFFOLDING"  # Quadrant 1
    elif coding_score < 2 and mpm_score >= 2:
        return "CODING_FOCUS"      # Quadrant 2
    elif coding_score >= 2 and mpm_score < 2:
        return "MPM_CONCEPTS"      # Quadrant 3
    else:
        return "POWER_USER"        # Quadrant 4
```

### 1.3 Non-Intrusive Assessment Alternative

**Implicit Assessment Through Interaction**:

Instead of explicit questionnaire, infer experience level from:
- **Initial request complexity**: Simple vs. multi-step requirements
- **Vocabulary used**: Technical terms vs. layperson descriptions
- **Error responses**: Understanding error messages vs. confusion
- **Follow-up questions**: Conceptual vs. implementation-focused

**Adaptive Teaching Triggers**:
```
User: "I need to set up environment variables"
  → Detect: May not understand .env files
  → Teach: Offer brief explanation with example

User: "Configure dotenv for local development"
  → Detect: Familiar with concepts
  → Teach: Skip basics, focus on MPM-specific setup

User: "What's an API key?"
  → Detect: Beginner level
  → Teach: Fundamental concepts with security focus
```

---

## 2. Prompt Enrichment Patterns

### 2.1 Research Findings: AI Assistant Techniques

**Microsoft Learn: Prompt Engineering Principles**:
- **Specificity**: "Be as specific as possible"
- **Iteration**: "Sequential prompting progressively refines output"
- **Context**: "Provide context and set the scene"

**Key Teaching Insight**:
> "If a human would struggle to follow it, the model probably will too."
> — Prompt Engineering Best Practices

**Effective Teaching Approach**:
- Treat prompts like UX design: grouping, headers, examples, whitespace
- Avoid abstract/nuanced concepts without concrete examples
- Use sequential prompting: each prompt informed by previous response

### 2.2 Socratic Method for Technical Teaching

**Core Principle**: Questions over answers
> "The Socratic method uses questions (and only questions) to arouse curiosity and serve as a logical, incremental, step-wise guide that enables students to figure out complex topics with their own thinking and insights."

**Application to Prompt Engineering**:

```markdown
❌ Poor (Direct Answer):
"Your prompt is missing context. Add file paths and project structure."

✅ Better (Socratic Guidance):
"What information would help me understand your project structure?
For example:
- Which files are you working with?
- What's the goal you're trying to achieve?
- Are there any constraints I should know about?"

✅ Best (Progressive Refinement):
"I can help with that! To give you the best solution, let me understand:
1. What does 'fix the login' mean for your project? (e.g., reset password flow, session handling, OAuth integration)
2. Which files or components handle authentication?
3. What specific behavior needs to change?

💡 Tip: The more specific you are, the more complete my solution will be."
```

**Socratic Debugging Pattern**:

Instead of:
```
"There's a bug in line 42. The variable is undefined."
```

Use:
```
"I notice an error at line 42. Let's debug together:
1. What value do you expect `userData` to have at this point?
2. Where is `userData` defined in your code?
3. Under what conditions might it be undefined?

🔍 Debugging Tip: Use console.log(userData) before line 42 to inspect its value."
```

### 2.3 Teaching Good Prompting Without Condescension

**Research Insight**: Users can make prompts sophisticated by "providing context or even a voice."

**Anti-Patterns to Avoid**:
- ❌ "Your prompt is too vague."
- ❌ "You need to provide more information."
- ❌ "That's not specific enough."
- ❌ "Obviously, you should include..."

**Positive Patterns**:
- ✅ "To help me give you a complete solution, could you share...?"
- ✅ "I can start with this, but knowing X would let me optimize for Y."
- ✅ "This will work, and if you'd like, I can enhance it by..."
- ✅ "Great start! Adding Z would help me handle edge cases like..."

**The "Yes, And" Technique** (from improv):
```markdown
User: "Make the button blue"

❌ Dismissive: "Which button? There are many buttons."

✅ Yes, And: "I'll make the primary button blue!
If you want other buttons styled, let me know which ones.
💡 Pro tip: Describing the button's location (navbar, footer, modal)
helps me target the right one in complex projects."
```

### 2.4 Progressive Disclosure in Teaching

**Borrowed from Skill-Creator Pattern**:

**Level 1 - Quick Start** (Always show):
```markdown
Quick Start:
1. Run: mpm-init
2. Answer setup questions
3. Start building: mpm run

💡 New to Claude MPM? Type 'teach me the basics' for a guided tour.
```

**Level 2 - Concept Explanation** (Show when requested or errors occur):
```markdown
Understanding Agents:
- Agents are specialists (Engineer, QA, Documentation, etc.)
- PM coordinates agents automatically
- You communicate with PM, PM delegates work

Example: "Fix login bug" → PM assigns to Engineer → Engineer implements → QA verifies
```

**Level 3 - Deep Dive** (Only when user needs it):
```markdown
Advanced: Agent Delegation Flow
[Detailed technical explanation]
[Internal architecture]
[Customization options]
```

### 2.5 Claude MPM Teach-Specific Patterns

**Template 1: Clarifying Questions with Context**

```markdown
I understand you want to [restate request]. To help me [goal]:

**Option A**: [Simple approach] - Great for [use case]
**Option B**: [Advanced approach] - Better if [condition]

Which fits your project? Or describe your project and I'll recommend one.

💡 Teaching Moment: [Brief explanation of why the choice matters]
```

**Template 2: Enrichment Through Examples**

```markdown
I'll help you [task]. Here's how this typically works:

**Example Scenario**: [Concrete example]
```
[Show expected outcome]
```

Does this match what you want, or should I adjust for [variation A] or [variation B]?

🎓 Learning: [Key concept explained]
```

**Template 3: Guided Improvement**

```markdown
I can work with that! To make this even better, consider:

**Current approach**: [What they said]
**Enhanced version**: [Improved prompt]

Benefits of the enhanced version:
- [Benefit 1]
- [Benefit 2]

Should I proceed with enhanced version, or would you prefer to stick with the original?
```

---

## 3. Secrets Management Education

### 3.1 Research Findings: Security Best Practices

**Critical Statistics**:
- **2016 Uber Breach**: 57 million users exposed due to AWS credentials published on GitHub
- **Common Pitfall**: Developers hard-code secrets in source code

**Best Practices Hierarchy**:

1. **Never hard-code secrets** - Universal rule
2. **Keep .env out of version control** - Add to .gitignore
3. **Use secret management tools** (AWS Secrets Manager, HashiCorp Vault) - Production systems
4. **Rotate credentials regularly** - Automate where possible
5. **Avoid insecure channels** - No email/chat for credentials

**The .env File Pattern**:
> "An environment variable is a variable that is set on your operating system, rather than within your application."

> "By storing them in a .env file instead of hardcoding them in your application, you gain several advantages: Security: Sensitive data stays out of your codebase"

### 3.2 Teaching Secrets Management to Beginners

**Principle**: Build understanding progressively, security-first mindset

**Level 1 - Essential Understanding**:

```markdown
## What Are API Keys? (ELI5 Version)

Think of an API key like a house key:
- It gives you access to a service (house)
- Anyone with your key can pretend to be you
- You shouldn't post photos of your key online
- You can change the key if it's compromised

**API Keys give access to services you pay for.** If someone steals your key,
they can:
- Use your paid services (costing you money)
- Access your data
- Impersonate you

This is why we keep them secret! 🔐
```

**Level 2 - Practical Setup**:

```markdown
## Setting Up .env Files (Step-by-Step)

### 1. Create .env file in project root
```bash
# .env file (never commit this!)
OPENAI_API_KEY=sk-abc123...
DATABASE_URL=postgres://localhost/mydb
```

### 2. Add .env to .gitignore
```bash
echo ".env" >> .gitignore
```

### 3. Create .env.example (commit this!)
```bash
# .env.example (safe to commit)
OPENAI_API_KEY=your_key_here
DATABASE_URL=your_database_url
```

### 4. Load in your code
```python
from dotenv import load_dotenv
import os

load_dotenv()  # Loads .env file
api_key = os.getenv("OPENAI_API_KEY")
```

**Why This Works**:
- ✅ Secrets stay on your computer
- ✅ Other developers know what variables they need (.env.example)
- ✅ Git never sees your actual secrets

**Common Mistakes to Avoid**:
- ❌ Committing .env to git (check .gitignore!)
- ❌ Sharing keys via email/Slack
- ❌ Using production keys in development
- ❌ Hard-coding keys in code files
```

**Level 3 - Production Deployment**:

```markdown
## Secrets in Production (Advanced)

Local development (.env files) ≠ Production deployment

**Production Options**:

### Option 1: Platform Environment Variables (Easiest)
Services like Vercel, Railway, Heroku:
1. Go to dashboard → Settings → Environment Variables
2. Add key-value pairs through UI
3. Deploy - variables injected at runtime

### Option 2: Secret Management Services (Enterprise)
- AWS Secrets Manager
- HashiCorp Vault
- Azure Key Vault

Use when:
- Multiple services need same secrets
- Compliance requirements (SOC2, HIPAA)
- Automatic rotation needed

### Option 3: CI/CD Secrets
- GitHub Secrets
- GitLab CI Variables
- Encrypted in repository settings

💡 Rule of Thumb: Start with platform environment variables. Graduate to
secret management services as project grows.
```

### 3.3 Teaching Template: First-Time API Key Setup

```markdown
## Your First API Key Setup 🔑

You'll need an API key for [service]. Here's how to do it safely:

### Step 1: Get Your API Key
1. Go to [service dashboard]
2. Navigate to: Settings → API Keys
3. Click "Create New Key"
4. **IMPORTANT**: Copy it now - you won't see it again!

### Step 2: Store It Securely
```bash
# Create .env file in your project root
echo "SERVICE_API_KEY=your_key_here" > .env

# Add to .gitignore to prevent accidental commits
echo ".env" >> .gitignore
```

### Step 3: Verify Setup
```bash
# Check .env exists and has your key
cat .env

# Verify .gitignore includes .env
git status  # Should NOT show .env as changed
```

### Step 4: Use in Claude MPM
```bash
mpm-init  # Will detect .env automatically
```

**Security Checklist**:
- [ ] .env file created in project root
- [ ] .env added to .gitignore
- [ ] Git status doesn't show .env
- [ ] Created .env.example for teammates (optional)

**If Something Goes Wrong**:
- 🚨 Accidentally committed .env? Rotate your API key immediately!
- 🚨 Lost your key? Generate a new one from dashboard
- 🚨 Key not working? Check for typos and spaces

💡 **Teaching Moment**: This same pattern works for ALL secrets - database passwords,
auth tokens, API keys. Once you learn it, you can apply it everywhere!
```

### 3.4 Progressive Questioning for Secret Setup

**Instead of assuming, ask**:

```markdown
I need an API key for [service]. Have you:
1. Created an account with [service]?
2. Generated an API key from their dashboard?
3. Set up a .env file in your project?

Let me know which step you're on, and I'll guide you through the rest!

**New to API keys?** I can explain:
- What they are and why they're important
- How to get one from [service]
- How to store it securely
- How to use it in your project
```

---

## 4. Deployment Model Recommendations

### 4.1 Research Findings: Platform Comparison

**Platform Decision Matrix**:

| Platform | Best For | Pricing Model | Complexity | Beginner-Friendly |
|----------|----------|---------------|------------|-------------------|
| **Vercel** | Frontend, Next.js, static sites | Free tier generous | Low | ⭐⭐⭐⭐⭐ |
| **Railway** | Backend APIs, databases, full-stack | Usage-based | Low | ⭐⭐⭐⭐ |
| **Heroku** | Web apps, APIs, prototypes | Instance-based ($50/mo+) | Low | ⭐⭐⭐⭐ |
| **Render** | Full-stack, databases | Fixed monthly | Medium | ⭐⭐⭐ |
| **AWS** | Enterprise, scaling, specific features | Complex, usage-based | High | ⭐⭐ |

**Key Research Insight**:
> "If you're bootstrapping, start with Render, Railway, Fly.io, or Cloudflare. Use Vercel or Netlify for frontends. Move to GCP, Azure, or AWS only when you need enterprise-grade performance or scale."

**Cost Considerations**:
- **Vercel**: Free for personal projects, $20/mo Pro (most beginners stay free)
- **Railway**: $5/mo credit, pay for what you use (~$10-20/mo typical)
- **Heroku**: $50/mo for 1GB dyno (expensive for beginners)
- **AWS**: Pay-as-you-go (can be cheap or expensive, unpredictable for beginners)

### 4.2 Deployment Recommendation Decision Tree

```
START: What are you building?

├─ Frontend Only (React, Vue, Static Site)
│  └─ → RECOMMEND: Vercel or Netlify
│     Reason: Zero-config, automatic deployments, global CDN
│     Free Tier: Yes, generous
│
├─ Backend API + Database
│  ├─ Need Simple Setup
│  │  └─ → RECOMMEND: Railway
│  │     Reason: Usage-based pricing, database management, transparent
│  │     Cost: ~$10-20/mo
│  │
│  └─ Need Reliability + Known Cost
│     └─ → RECOMMEND: Heroku
│        Reason: Battle-tested, compliance options, predictable
│        Cost: $50/mo minimum (expensive)
│
├─ Full-Stack App (Frontend + Backend)
│  ├─ Next.js Specifically
│  │  └─ → RECOMMEND: Vercel
│  │     Reason: Built by Vercel team, optimized performance
│  │
│  └─ Other Framework
│     └─ → RECOMMEND: Railway or Render
│        Reason: Handles both layers, database included
│
└─ Enterprise/Scaling Requirements
   └─ → RECOMMEND: AWS, GCP, or Azure
      Reason: Advanced features, compliance, scale
      Note: Higher complexity, consider after outgrowing simpler platforms
```

### 4.3 Teaching Deployment Recommendations

**Beginner-Friendly Assessment Questions**:

```markdown
To recommend the best hosting platform, let me understand your project:

1. **What are you building?**
   - [ ] Website/blog (mostly static content)
   - [ ] Web app with user accounts (frontend + backend)
   - [ ] API service (no frontend)
   - [ ] Full-stack application (Next.js, React + Node, etc.)

2. **Do you need a database?**
   - [ ] No database needed
   - [ ] Yes, and I want it managed for me
   - [ ] Yes, and I'll set it up separately

3. **Expected traffic**:
   - [ ] Personal project / portfolio (low traffic)
   - [ ] Small startup / side project (moderate traffic)
   - [ ] Business / production app (high traffic)

4. **Budget considerations**:
   - [ ] Free tier preferred (learning/experimenting)
   - [ ] Can pay $10-20/mo (serious project)
   - [ ] Budget not a constraint (production business)

Based on your answers, I'll recommend the best platform and walk you through setup!
```

**Recommendation Template**:

```markdown
## Recommended Platform: [Platform Name]

**Why This Fits Your Project**:
- ✅ [Reason 1 specific to their needs]
- ✅ [Reason 2 specific to their needs]
- ✅ [Reason 3 specific to their needs]

**Quick Setup**:
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Cost**: [Pricing details relevant to their usage]

**Getting Started**:
[Link to platform-specific guide or offer to walk through setup]

**Alternative Options**:
If [condition changes], consider [alternative platform] because [reason].

💡 **Teaching Moment**: [Why this choice matters for their learning/project]
```

**Example: Beginner Building First Full-Stack App**

```markdown
## Recommended: Railway

**Why Railway for Your First Full-Stack App**:
- ✅ Simple setup - One platform for frontend, backend, AND database
- ✅ Pay-as-you-go - Start free, scale as needed (~$10-20/mo typical)
- ✅ Transparent usage tracking - See exactly what you're spending
- ✅ Beginner-friendly - Less complex than AWS, more powerful than Vercel alone

**Quick Setup**:
1. Create Railway account: https://railway.app
2. Connect your GitHub repo
3. Railway auto-detects: Node.js app, PostgreSQL needed
4. Click "Deploy" - Railway handles the rest!
5. Get production URL in ~2 minutes

**Cost Breakdown**:
- First $5/mo free credit
- Typical usage: $10-15/mo for personal projects
- Database included (no separate service needed)

**Getting Started**:
Want me to walk you through deployment step-by-step? Or try it yourself
and let me know if you hit any issues!

**When to Upgrade**:
- Railway works great until ~10,000 users
- If you need enterprise compliance (SOC2, HIPAA), consider AWS/GCP later
- If frontend becomes complex, can split to Vercel (frontend) + Railway (backend)

💡 **Teaching Moment**: Railway is perfect for learning production deployment.
Once you master Railway, concepts transfer to AWS/GCP if you need to scale.
```

### 4.4 Platform-Specific Teaching Resources

**Quick Reference Cards** (To be created in actual implementation):

```markdown
# Vercel Quick Start Card
**Best for**: React, Next.js, static sites
**Setup time**: 5 minutes
**Free tier**: Yes, generous
**Complexity**: ⭐ (easiest)

[Step-by-step setup guide]
[Common errors and fixes]
[Deployment checklist]

---

# Railway Quick Start Card
**Best for**: Backend APIs, full-stack, databases
**Setup time**: 10 minutes
**Free tier**: $5/mo credit
**Complexity**: ⭐⭐ (simple)

[Step-by-step setup guide]
[Common errors and fixes]
[Deployment checklist]

---

# AWS Quick Start Card
**Best for**: Enterprise, scaling, advanced features
**Setup time**: 30+ minutes
**Free tier**: 12 months, limited
**Complexity**: ⭐⭐⭐⭐⭐ (expert)

[Step-by-step setup guide]
[Common errors and fixes]
[Deployment checklist]
[When to choose AWS over simpler platforms]
```

---

## 5. Pedagogical Principles

### 5.1 Socratic Method in Technical Teaching

**Research Findings**:

> "The Socratic Method can be effectively applied across a wide range of technical disciplines, particularly in debugging where instead of simply providing the solution, it guides developers to identify the root cause of a bug by asking questions about the code's logic, input values, and expected behavior."

**Benefits**:
- Fosters critical thinking
- Independent reasoning
- Collaborative problem-solving
- More resilient technical workforce

**Application to Claude MPM Teach**:

**Debugging Scenario**:
```markdown
❌ Direct Solution:
"Your agent isn't loading because you forgot to add it to agent-config.yaml"

✅ Socratic Approach:
"I notice your agent isn't appearing. Let's debug together:
1. Which file did you create? (.claude/agents/[name].md)
2. Is the agent name in the filename the same as in the frontmatter?
3. Have you configured it in agent-config.yaml?
4. What does `mpm-agents-list` show?

Walk me through what you see, and we'll identify the issue together."
```

### 5.2 Zone of Proximal Development (ZPD)

**Research Definition**:
> "The zone of proximal development represents the space between what a learner can do unsupported and what they cannot do even with support, where learning is able to occur but only with support."

**ZPD Applied to Claude MPM**:

```
Can Do Alone          ZPD (Teach Here)       Cannot Do Yet
────────────────────────────────────────────────────────────
Run mpm-init    →    Configure agents   →    Design custom
Use basic PM    →    Understand          →    agent
Simple tasks         delegation             architecture
                     Create .env files       Optimize
                     Deploy to Vercel        performance
```

**Scaffolding Strategies**:

1. **Modeling**: Show expected behavior
2. **Hints and Prompts**: Guide without solving
3. **Breaking Down Tasks**: Smaller, manageable steps
4. **Gradual Fading**: Remove support as competence grows

**Example - Teaching Agent Configuration**:

**Step 1 - Model (I do, you watch)**:
```markdown
Watch as I configure an agent:
1. Open .claude/agents/
2. Create engineer.md
3. Add frontmatter:
   ```yaml
   ---
   name: engineer
   model: claude-sonnet-4
   capabilities: [implementation]
   ---
   ```
4. Run: mpm-agents-list
5. See: Engineer agent appears!
```

**Step 2 - Guided Practice (We do together)**:
```markdown
Now you try with the QA agent:
1. Create .claude/agents/qa.md
2. What should the name be? (Hint: match the filename)
3. Which capabilities? (Hint: what does QA do?)
4. Run mpm-agents-list to verify

I'm here if you get stuck!
```

**Step 3 - Independent Practice (You do, I check)**:
```markdown
Challenge: Create a Documentation agent
- Figure out the right frontmatter fields
- Choose appropriate capabilities
- Verify it appears in agent list

Show me what you created, and I'll provide feedback!
```

**Step 4 - Fading (Minimal support)**:
```markdown
You're ready to create custom agents independently!
Refer to docs/agents/creating-agents.md if needed.
I'm here for advanced questions.
```

### 5.3 Productive Failure Learning

**Research Insight**:
> "Productive Failure (PF) is a learning approach where students initially tackle novel problems targeting concepts they have not yet learned, followed by a consolidation phase where these concepts are taught. While productive failure students perceived greater mental effort, they significantly outperformed students who received direct instruction on conceptual understanding and transfer problems."

**Application: Error-Driven Learning**

**Traditional Approach (Direct Instruction First)**:
```markdown
1. Read all documentation
2. Understand every concept
3. Practice simple examples
4. Attempt real project
```

**Productive Failure Approach**:
```markdown
1. Attempt real project (struggle expected!)
2. Encounter errors/confusion
3. **TEACHING MOMENT**: Explain concepts in context
4. Refine understanding through iteration
```

**Example - First MPM Project**:

**Allow Initial Struggle**:
```markdown
User: "I want to build a todo app with authentication"
PM: "Great! Let's start. Run: mpm-init"

User runs mpm-init → gets prompted for configuration

User: "What's a capability? What's specialization? I don't understand"

PM: 🎯 **TEACHING MOMENT TRIGGERED**
"You've just discovered the core concepts of MPM! Let me explain in context of your todo app:

**Capabilities** are what an agent CAN do:
- For todo app, you need:
  - `implementation` (Engineer builds features)
  - `testing` (QA verifies it works)
  - `documentation` (Docs explains how to use it)

**Specialization** is the agent's expertise:
- Engineer: specialization=backend (Node.js, Python, etc.)
- QA: specialization=testing (Playwright, Jest, etc.)

Now that you understand WHY these matter, let's configure them for your project.
Which backend technology are you using?"
```

**Key Insight**: User learns BETTER by encountering the error first, then receiving targeted explanation.

### 5.4 Progressive Disclosure for Teaching

**Borrowing from Claude MPM Skill Creator**:

**3-Level Teaching Architecture**:

**Level 1 - Quick Start (Always Show)**:
- Minimal viable knowledge
- Get started immediately
- Clear next steps

**Level 2 - Concept Explanation (On-Demand)**:
- Deeper understanding
- Why things work
- Best practices

**Level 3 - Advanced Topics (Expert Only)**:
- Internals and architecture
- Optimization techniques
- Custom workflows

**Example: Teaching Agent System**

**Level 1**:
```markdown
Quick Start: Using Agents
- PM coordinates all agents automatically
- You talk to PM, PM delegates to specialists
- No need to understand internals to get started

Try: "PM, help me build a login page"
```

**Level 2** (When user asks "How do agents work?"):
```markdown
Understanding Agent Delegation:
- PM analyzes your request
- Identifies required capabilities (implementation, testing, etc.)
- Selects appropriate agents (Engineer, QA, etc.)
- Coordinates workflow: Engineer builds → QA tests → Done
- Reports back to you with results

Want to see this in action? Let's walk through an example.
```

**Level 3** (When user asks "Can I customize agents?"):
```markdown
Advanced: Custom Agent Architecture
[Detailed technical explanation]
[Agent configuration schema]
[Multi-tier agent hierarchy]
[Custom capability definitions]
[Agent interaction protocols]
```

### 5.5 Learning by Doing vs. Explanation-First

**Research Findings**:
- Problem-solving followed by instruction is more effective than instruction followed by problem-solving
- Hands-on debugging integral to learning programming
- Struggle improves long-term understanding

**Claude MPM Teach Approach**:

**Principle**: "Do → Struggle → Learn → Refine" (Not "Learn → Do")

**Example - Teaching Ticketing Integration**:

**Explanation-First (Traditional)**:
```markdown
❌ Ineffective Teaching Order:
1. Explain MCP-Ticketer architecture (15 minutes)
2. Show API documentation (10 minutes)
3. Describe ticket lifecycle (5 minutes)
4. Finally: "Now try creating a ticket"
Result: User overwhelmed, forgets details, learns abstractly
```

**Doing-First (Productive Failure)**:
```markdown
✅ Effective Teaching Order:
1. "Let's create a ticket. Run: mpm run"
2. User tries, encounters errors or confusion
3. **TEACH IN CONTEXT**: "You're seeing this error because [explanation]"
4. User refines, succeeds
5. **REINFORCE**: "Notice how the ticket appeared in Linear? That's because [concept]"
Result: User learns through doing, understands context, retains knowledge
```

**Implementation Pattern**:

```markdown
## Teaching Template: Do → Teach → Refine

**Step 1: Immediate Action**
"Let's do it! [Minimal instruction to start]"

**Step 2: Observe Struggle**
[Monitor for errors, confusion, questions]

**Step 3: Teach in Context**
"You're encountering [X] because [Y]. Here's why this matters: [Z]"

**Step 4: Guided Refinement**
"Now try [improved approach], incorporating what you just learned."

**Step 5: Consolidation**
"Great! Notice how [outcome]? That's because [concept]. You've just learned [skill]."
```

---

## 6. Claude MPM Teach Style Design

### 6.1 Core Design Principles

Based on all research findings, the Claude MPM Teach style embodies:

1. **Adaptive Scaffolding**: Adjust teaching level based on user experience
2. **Socratic Questioning**: Guide through questions, not direct answers
3. **Productive Failure**: Allow struggle, teach in context of errors
4. **Progressive Disclosure**: Start simple, deepen as needed
5. **Security-First**: Treat secrets management as foundational
6. **Practical-First**: Prioritize doing over explaining
7. **Non-Patronizing**: Respect user intelligence, offer growth
8. **Build Independence**: Goal is proficiency, not dependency

### 6.2 Teach Style Activation

**Explicit Activation**:
```bash
mpm run --teach
# or
mpm teach
```

**Implicit Activation** (Detection patterns):
- First-time setup detected (no .claude-mpm/ directory)
- Error messages indicating beginner confusion
- Questions about fundamentals
- User explicitly asks for teaching mode

**Opt-Out**:
```bash
mpm run --no-teach
# or set in config
teach_mode: false
```

### 6.3 Teach Style Behaviors

**Behavior Matrix**:

| Situation | Regular Mode | Teach Mode |
|-----------|--------------|------------|
| User makes typo | Error message | Error + common fix + concept explanation |
| Missing configuration | Fail with error | Guide through configuration with context |
| API key error | "Invalid key" | Explain API keys, security, how to fix |
| Agent not found | "Agent X not available" | Explain agent system, show how to configure |
| First deployment | Proceed with defaults | Ask teaching questions, recommend platform |

**Example Transformations**:

**Regular Mode**:
```markdown
❌ Error: OPENAI_API_KEY not found in environment
```

**Teach Mode**:
```markdown
🎓 **Teaching Moment: API Keys**

Error: OPENAI_API_KEY not found in environment

**What This Means**:
Your app needs an API key to communicate with OpenAI. Think of it like a password
that lets your app use OpenAI's services.

**How to Fix**:
1. Get API key from: https://platform.openai.com/api-keys
2. Create `.env` file in project root:
   ```
   OPENAI_API_KEY=sk-abc123...
   ```
3. Add `.env` to `.gitignore` (security!)
4. Restart MPM

**Why This Matters**:
API keys should NEVER be committed to git (security risk!). .env files keep secrets
local to your computer.

Need help with any step? Ask me!

📚 Learn more: [Link to secrets management guide]
```

### 6.4 Teaching Response Templates

**Template 1: First-Time Setup**

```markdown
## 👋 Welcome to Claude MPM!

I'm your PM (Project Manager), and I'll help you build projects using AI agents.

Since this is your first time, let me quickly show you how this works:

**The Claude MPM Way**:
1. **You** tell me what you want to build (in plain English!)
2. **I (PM)** break down the work and coordinate specialists
3. **Agents** (Engineer, QA, Docs, etc.) do the actual work
4. **You** review and approve

**Quick Start**:
Let's start with something simple to learn the ropes. What would you like to build?

Examples:
- "Build a todo list app"
- "Add user authentication to my project"
- "Create a REST API for my blog"

💡 **Tip**: The more specific you are, the better I can help!

🎓 **Want a guided tour?** Say "teach me the basics" and I'll walk you through MPM concepts.
```

**Template 2: Error-Driven Teaching**

```markdown
🎓 **Teaching Moment: [Concept]**

[Error message in context]

**What Happened**:
[Plain English explanation of error]

**Why This Matters**:
[Concept explanation - why this is important to understand]

**How to Fix**:
1. [Step 1 with explanation]
2. [Step 2 with explanation]
3. [Step 3 with explanation]

**Quick Fix** (if you understand already):
```bash
[Single command to fix, if applicable]
```

**Learn More**:
- [Link to relevant concept documentation]
- [Link to related tutorial]

Need help with any step? Ask me questions!
```

**Template 3: Socratic Debugging**

```markdown
🔍 **Let's Debug Together**

I notice [observation]. Let's figure this out together:

**Question 1**: [Diagnostic question about expectations]
**Question 2**: [Diagnostic question about actual behavior]
**Question 3**: [Diagnostic question about context]

Based on your answers, I can guide you to the solution.

💡 **Debugging Tip**: [General debugging advice applicable to this situation]

🎓 **Learning Opportunity**: This is a common issue when [scenario]. Understanding
[concept] will help you avoid this in future.
```

**Template 4: Concept Introduction**

```markdown
## 📘 New Concept: [Concept Name]

You're about to encounter [concept]. Let me explain quickly:

**What It Is**:
[ELI5 explanation with analogy]

**Why It Matters**:
[Practical importance]

**How You'll Use It**:
[Concrete example in their current context]

**Example**:
```[code example]```

Ready to try? [Next action]

**Don't worry if this seems complex** - you'll get the hang of it quickly!

📚 **Deep Dive** (optional): [Link to detailed explanation]
```

**Template 5: Progressive Guidance**

```markdown
## 🎯 Your Current Task: [Task]

I'll guide you through this step-by-step:

**Phase 1: Setup** (We are here)
- [ ] Step 1
- [ ] Step 2
- [ ] Step 3

**Phase 2: Implementation** (Next)
[Brief preview]

**Phase 3: Verification** (Final)
[Brief preview]

Let's start with Phase 1, Step 1:
[Detailed guidance for current step]

When you complete this step, I'll guide you to the next one.

💡 **Why This Order**: [Explain pedagogical reasoning]
```

### 6.5 Beginner-Specific Enhancements

**Terminology Glossary (Just-in-Time)**:

When using technical terms, provide inline definitions:

```markdown
Regular: "Your agent needs the `implementation` capability"

Teach: "Your agent needs the `implementation` capability (what it can do - in
this case, write code)"

Regular: "Configure your MCP endpoint"

Teach: "Configure your MCP endpoint (MCP = Model Context Protocol - how Claude
talks to external services)"
```

**Visual Indicators**:

```markdown
🎓 Teaching Moment
📘 New Concept
💡 Pro Tip
🔍 Debugging Together
✅ Success Checkpoint
⚠️ Common Mistake
🚀 Next Steps
📚 Learn More
```

**Checkpoints and Validation**:

```markdown
✅ **Checkpoint: .env Setup**

Before moving on, let's verify:
- [ ] .env file created in project root
- [ ] API key added to .env
- [ ] .env in .gitignore
- [ ] .env.example created (optional)

Run: `cat .env` (you should see your key)
Run: `git status` (.env should NOT appear)

All checks passed? Great! Let's move to next step.

Something not working? Let me know which check failed.
```

**Celebration of Learning**:

```markdown
🎉 **You've Just Learned: [Concept]**

Great job! You now understand:
- [Key point 1]
- [Key point 2]
- [Key point 3]

This skill will help you with:
- [Future application 1]
- [Future application 2]

**Next Challenge**: Ready to level up? Let's tackle [next concept].
```

### 6.6 Graduation from Teach Mode

**Progressive Independence**:

```markdown
## 🎓 Graduation Checkpoint

You're getting really good at this! You've mastered:
- ✅ Basic agent usage
- ✅ Secrets management
- ✅ Deployment workflows
- ✅ Error debugging

**Would you like to:**
1. **Continue with teaching mode** (I'll keep explaining concepts)
2. **Switch to power user mode** (Minimal explanations, faster workflow)
3. **Adaptive mode** (I'll teach only when you encounter new concepts)

Choose your preference, or let me adapt automatically based on your questions.

💡 **Tip**: You can always turn teaching back on with `mpm run --teach`
```

**Adaptive Transition**:

Track user competency signals:
- Asking fewer clarifying questions
- Using correct terminology
- Solving errors independently
- Requesting less detailed explanations

When signals indicate proficiency:
```markdown
I notice you're getting comfortable with MPM! 🎉

I'm going to reduce teaching explanations, but I'm here if you need them.

To get detailed explanations again:
- Ask "explain [concept]"
- Use --teach flag
- Say "I'm stuck, teach me"

Keep up the great work!
```

---

## 7. Implementation Recommendations

### 7.1 Technical Architecture

**Proposed Implementation**:

```python
# src/claude_mpm/teaching/teach_mode.py

class TeachMode:
    """Adaptive teaching system for Claude MPM beginners"""

    def __init__(self, user_level: str = "auto"):
        self.user_level = user_level  # auto, beginner, intermediate, advanced
        self.teaching_history = []
        self.concepts_covered = set()

    def detect_user_level(self, context: dict) -> str:
        """Infer user experience level from context"""
        signals = {
            "first_time_setup": context.get("is_first_run", False),
            "error_patterns": self.analyze_error_patterns(context),
            "question_complexity": self.analyze_questions(context),
            "vocabulary_used": self.analyze_vocabulary(context)
        }
        return self.calculate_user_level(signals)

    def enhance_response(self, response: str, context: dict) -> str:
        """Add teaching enhancements to response based on user level"""
        if self.user_level == "beginner":
            response = self.add_concept_explanations(response, context)
            response = self.add_visual_indicators(response)
            response = self.add_checkpoints(response)
        elif self.user_level == "intermediate":
            response = self.add_inline_definitions(response)
            response = self.add_pro_tips(response)
        # Advanced users get minimal teaching enhancements
        return response

    def teach_concept(self, concept: str, context: dict) -> str:
        """Generate teaching content for specific concept"""
        if concept in self.concepts_covered:
            return self.brief_reminder(concept)

        self.concepts_covered.add(concept)
        return self.full_teaching_moment(concept, context)

    def should_trigger_teaching(self, error: Exception, context: dict) -> bool:
        """Determine if error warrants teaching moment"""
        if self.user_level == "advanced":
            return False
        if self.is_first_time_error(error):
            return True
        if self.indicates_conceptual_gap(error, context):
            return True
        return False
```

**Integration Points**:

1. **CLI Entry Point**: Detect `--teach` flag or first-time setup
2. **PM Agent**: Inject teaching enhancements into responses
3. **Error Handler**: Intercept errors, add teaching context
4. **Session Manager**: Track learning progress across sessions

### 7.2 Content Organization

**Proposed Directory Structure**:

```
src/claude_mpm/teaching/
├── __init__.py
├── teach_mode.py              # Core teaching logic
├── templates/
│   ├── first_time_setup.md    # Welcome message
│   ├── error_explanations.md  # Error -> teaching mappings
│   ├── concept_library.md     # Just-in-time concept explanations
│   └── socratic_prompts.md    # Question templates
├── assessments/
│   ├── user_level_detector.py
│   └── questionnaire.yaml
└── content/
    ├── secrets_management/
    │   ├── level1_basics.md
    │   ├── level2_setup.md
    │   └── level3_production.md
    ├── deployment/
    │   ├── platform_comparison.md
    │   ├── vercel_guide.md
    │   ├── railway_guide.md
    │   └── decision_tree.md
    └── agent_system/
        ├── basics.md
        ├── configuration.md
        └── advanced.md
```

### 7.3 Progressive Disclosure Implementation

**Agent Enhancement**:

```markdown
---
name: pm
model: claude-sonnet-4
teach_mode: true
progressive_disclosure:
  level_1_always:
    - core_pm_workflow
    - delegation_basics
  level_2_on_demand:
    - agent_architecture
    - ticket_integration
    - qa_verification
  level_3_advanced:
    - custom_agents
    - multi_project_orchestration
    - optimization_techniques
---

# PM Agent with Teaching Mode

[Standard PM instructions]

## Teaching Mode Enhancements

When teach_mode is enabled:

**For Beginners**:
- Explain agent delegation when first encountered
- Provide inline definitions for technical terms
- Add checkpoints after each major step
- Celebrate learning milestones

**For Intermediate Users**:
- Brief reminders of concepts
- Pro tips for efficiency
- Links to advanced resources

**For Advanced Users**:
- Minimal teaching overhead
- Focus on edge cases and optimization

[Rest of PM instructions]
```

### 7.4 Configuration Integration

**~/.claude-mpm/config.yaml Enhancement**:

```yaml
# Teaching Mode Configuration
teach_mode:
  enabled: true
  user_level: auto  # auto, beginner, intermediate, advanced

  # Adaptive behavior
  auto_detect_level: true
  adapt_over_time: true
  graduation_threshold: 10  # Number of successful interactions before suggesting graduation

  # Content preferences
  detailed_errors: true
  concept_explanations: true
  socratic_debugging: true
  checkpoints_enabled: true

  # Visual indicators
  use_emojis: true
  use_colors: true  # Terminal color support

  # Opt-in features
  questionnaire_on_first_run: true  # Explicit assessment vs. implicit
  celebration_messages: true
  progress_tracking: true
```

### 7.5 User Experience Flow

**First-Time Setup with Teaching**:

```bash
$ mpm-init

👋 Welcome to Claude MPM!

This looks like your first time. I can help you learn as we go!

Would you like teaching mode? (Recommended for beginners)
[Y/n]: Y

Great! I'll explain concepts as we work together.

Let's start by understanding your project...

[Setup wizard with teaching enhancements]

✅ Setup Complete!

You've configured:
- Project directory
- Default agents (Engineer, QA, Documentation)
- API keys (stored securely in .env)

🎓 You've just learned: Project initialization, agent configuration, secrets management

Ready to build something? Try: mpm run
```

**Subsequent Sessions**:

```bash
$ mpm run

🎓 Teaching Mode Active (Session 3)

What would you like to work on today?

> Build a user authentication system

Great! Authentication is a complex topic. Let me break this down:

**We'll need**:
- Backend engineer (handles auth logic)
- QA agent (tests security)
- Documentation agent (explains how to use it)

**Teaching Moment**: Authentication requires special attention to security. I'll make
sure we follow best practices for:
- Password hashing
- Session management
- Token generation

Ready to start? I'll coordinate the agents.

[Proceed with normal workflow, with teaching enhancements at key moments]
```

---

## 8. Research Conclusions

### 8.1 Key Findings Summary

1. **Experience Assessment**: 2-dimensional matrix (coding × MPM experience) enables targeted teaching
2. **Prompt Enrichment**: Socratic questioning >>> direct answers for learning
3. **Secrets Management**: Progressive disclosure (ELI5 → Setup → Production) with security-first mindset
4. **Deployment Recommendations**: Decision tree based on project type, budget, complexity
5. **Pedagogical Principles**: Productive failure + ZPD scaffolding + progressive disclosure = effective learning

### 8.2 Design Recommendations

**For Claude MPM Teach Style**:

✅ **Implement**:
1. Adaptive teaching based on implicit signals (avoid lengthy questionnaires)
2. Socratic debugging ("Let's figure out together") over direct solutions
3. Progressive disclosure (Quick Start → Concepts → Advanced)
4. Just-in-time teaching (teach at moment of need, not preemptively)
5. Error-driven learning (allow productive failure, teach in context)
6. Celebration and checkpoints (acknowledge learning progress)
7. Graceful graduation (transition from teaching to power user mode)

❌ **Avoid**:
1. Lengthy upfront explanations (overwhelming)
2. Condescending language ("Obviously", "Simply", "Just")
3. Blocking work to teach (allow skipping/deferring lessons)
4. One-size-fits-all approach (adapt to user level)
5. Dependency creation (goal is independence)

### 8.3 Success Metrics

**How to Measure Teaching Effectiveness**:

1. **Time to First Success**: How quickly users accomplish first task
2. **Error Resolution Rate**: % of errors users solve independently
3. **Teaching Mode Graduation**: % of users who progress to power user mode
4. **Concept Retention**: Users demonstrate understanding in later sessions
5. **User Satisfaction**: Self-reported teaching helpfulness (NPS)
6. **Reduced Support Burden**: Fewer basic questions in support channels

### 8.4 Next Steps

**Implementation Priority**:

**Phase 1 - Foundation** (MVP):
- [ ] Implement basic teach mode flag (`--teach`)
- [ ] Add teaching templates to PM agent
- [ ] Create secrets management teaching content
- [ ] Implement error enhancement system

**Phase 2 - Adaptive Teaching**:
- [ ] Build user level detection system
- [ ] Implement progressive disclosure for concepts
- [ ] Add Socratic debugging prompts
- [ ] Create checkpoint and validation system

**Phase 3 - Advanced Features**:
- [ ] Deploy teaching content library
- [ ] Implement graduation system
- [ ] Add progress tracking across sessions
- [ ] Create deployment recommendation decision tree

**Phase 4 - Refinement**:
- [ ] Collect user feedback
- [ ] A/B test teaching approaches
- [ ] Optimize teaching content based on metrics
- [ ] Expand teaching coverage to advanced topics

---

## 9. Appendices

### Appendix A: Research Sources

**Web Search Results** (2025-12-03):
1. Adaptive learning platforms market analysis (Whatfix)
2. Codecademy pedagogical framework (5-step system)
3. Prompt engineering techniques (Microsoft Learn, Lakera, Anthropic)
4. Secrets management best practices (GitGuardian, OpenAI, Netlify)
5. Deployment platform comparisons (Northflank, BoltOps, DEV Community)
6. Socratic method in technical teaching (CLRN, UC San Diego, ResearchGate)
7. Skill assessment methodologies (Stack Overflow, MentorCruise)
8. Zone of Proximal Development research (Simply Psychology, Educational Technology)
9. Productive failure studies (arXiv, Frontiers in Psychology)
10. CLI design patterns (clig.dev, Lucas Costa, Atlassian)

**Claude MPM Internal Sources**:
- `/src/claude_mpm/agents/BASE_PM.md` - PM framework requirements
- `/docs/agents/creating-agents.md` - Agent creation guide
- `/src/claude_mpm/skills/bundled/main/skill-creator/references/progressive-disclosure.md` - Progressive disclosure pattern

### Appendix B: Platform Quick Reference

| Platform | Setup Time | Free Tier | Best For | Cost After Free |
|----------|------------|-----------|----------|-----------------|
| Vercel | 5 min | Yes (generous) | React, Next.js, Static | $20/mo Pro |
| Railway | 10 min | $5/mo credit | APIs, Full-stack, DB | $10-20/mo typical |
| Heroku | 15 min | No | Web apps, APIs | $50/mo minimum |
| Render | 15 min | Limited | Full-stack | $7-$25/mo |
| Netlify | 5 min | Yes (generous) | Static sites, Jamstack | $19/mo Pro |
| Fly.io | 20 min | $5/mo credit | Global edge apps | Usage-based |
| AWS | 30+ min | 12 months limited | Enterprise, Scale | Complex pricing |

### Appendix C: Teaching Moment Triggers

**Error-Based Triggers**:
- Missing environment variable → Secrets management teaching
- Agent not found → Agent configuration teaching
- API authentication failure → API key setup teaching
- Deployment error → Platform-specific troubleshooting
- Git commit failed → Version control basics

**Question-Based Triggers**:
- "What is...?" → Concept explanation (ELI5)
- "How do I...?" → Step-by-step guide with teaching
- "Why does...?" → Conceptual understanding focus
- "Which should I...?" → Decision tree with education

**Context-Based Triggers**:
- First run → Welcome + quick orientation
- First deployment → Platform recommendation + setup
- First agent creation → Agent system explanation
- Repeated error → Deeper concept teaching

### Appendix D: Terminology Glossary (Just-in-Time Definitions)

**Core MPM Concepts**:
- **Agent**: AI specialist that performs specific tasks (Engineer, QA, Docs, etc.)
- **PM (Project Manager)**: Coordinator that delegates work to agents
- **Capability**: What an agent can do (implementation, testing, documentation, etc.)
- **Specialization**: Agent's area of expertise (backend, frontend, testing, etc.)
- **Delegation**: PM assigning work to appropriate agent based on capabilities
- **MCP (Model Context Protocol)**: How Claude communicates with external services

**Secrets Management**:
- **API Key**: Password-like credential that gives access to a service
- **.env File**: Local file storing secrets (never committed to git)
- **Environment Variable**: Configuration value stored outside code
- **.gitignore**: File telling git which files to ignore (includes .env)

**Deployment**:
- **Hosting Platform**: Service that runs your app online (Vercel, Railway, etc.)
- **Production**: Live environment where real users access your app
- **Development**: Local environment where you build and test
- **Deploy**: Publishing your code to production environment

---

## Research Metadata

**Token Usage**: ~72k tokens (research + synthesis)
**Files Read**: 3 key files from Claude MPM codebase
**Web Searches**: 10 comprehensive searches across 5 domains
**Total Sources**: 50+ articles, guides, and research papers analyzed
**Time Investment**: Comprehensive multi-domain research synthesized into actionable framework

**Next Action**: Implement Phase 1 (Foundation) of teaching mode system.
