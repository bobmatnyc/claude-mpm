---
title: Absolute Beginner's Guide to Claude MPM
version: 1.0.0
last_updated: 2026-01-05
audience: Non-technical founders and business leaders
status: current
---

# Absolute Beginner's Guide to Using Claude MPM

**A Complete Guide for Non-Technical Founders**

Welcome! This guide is specifically written for startup founders and business leaders who don't write code but want to understand and oversee their technical projects. No programming experience required.

## Table of Contents

1. [What is Claude MPM?](#part-1-what-is-claude-mpm)
2. [What You'll Need](#part-2-what-youll-need)
3. [Setting Up Your First Project](#part-3-setting-up-your-first-project)
4. [Questions Founders Should Ask](#part-4-questions-founders-should-ask)
5. [Understanding the Answers](#part-5-understanding-the-answers)
6. [Common Tasks for Founders](#part-6-common-tasks-for-founders)
7. [Glossary](#part-7-glossary)
8. [Getting Help](#part-8-getting-help)

---

## Part 1: What is Claude MPM?

### In Plain English

Think of Claude MPM as your **AI technical advisor** that can read, understand, and explain your entire codebase. It's like having a senior developer on call 24/7 who:

- **Never gets tired of answering questions**
- **Remembers everything about your project**
- **Can explain technical concepts in business terms**
- **Reviews code changes and identifies risks**
- **Helps you understand what your team is building**

### The Business Value

**Claude MPM helps you:**
- **Make informed decisions** about technical investments
- **Understand developer productivity** without micromanaging
- **Identify security risks** before they become problems
- **Assess code quality** like a technical co-founder would
- **Ask technical questions** and get straight answers

### What Makes It Special?

Unlike other AI tools, Claude MPM is specifically designed for project management and oversight. It:
- Understands your entire codebase as a system, not just individual files
- Maintains memory of your project's history and decisions
- Can delegate tasks to specialized "agents" (think: different expert consultants)
- Provides business-focused answers, not just technical details

### Real-World Use Cases

**Scenario 1: Pre-Investment Due Diligence**
> "I'm raising a Series A. An investor asked about our technical debt. What should I tell them?"

Claude MPM can analyze your codebase and give you an honest assessment in business terms.

**Scenario 2: Team Performance**
> "My lead developer left. How dependent are we on them? What areas need documentation?"

Get a clear picture of knowledge concentration and risk areas.

**Scenario 3: Feature Planning**
> "We want to add payment processing. How big of a project is this? What are the security considerations?"

Understand scope and complexity before committing to timelines.

---

## Part 2: What You'll Need

### Required Tools

#### 1. A Computer
- **Mac**: macOS 10.15 or newer
- **Windows**: Windows 10 or newer
- **Linux**: Most modern distributions work

#### 2. An Anthropic Account
- Go to: https://console.anthropic.com
- Sign up for an account (free to start)
- You'll need a credit card for API usage (typically $10-50/month for regular use)

#### 3. Your Project's Code
Your code needs to be on your computer. Usually this means:
- **From GitHub**: You'll "clone" it (download a copy)
- **From GitLab/Bitbucket**: Same process
- **On your computer already**: Even better!

### Optional But Helpful

- **GitHub account**: If your code is stored there
- **Terminal knowledge**: We'll walk you through this
- **Budget for API calls**: Claude MPM uses Claude AI, which costs money per use (think pennies per question, not dollars)

---

## Part 3: Setting Up Your First Project

### Step 1: Installing Claude Code

**What is Claude Code?**
Think of it as the foundation - it's Anthropic's official tool that lets you interact with Claude AI from your computer's command line (the text-based interface).

**Installation Steps:**

1. **Open your Terminal** (we'll use this a lot)
   - **Mac**: Press `Command + Space`, type "Terminal", press Enter
   - **Windows**: Press `Windows + R`, type "cmd", press Enter
   - **Linux**: Press `Ctrl + Alt + T`

2. **Visit the installation page**
   - Go to: https://docs.anthropic.com/en/docs/claude-code
   - Follow the installation instructions for your operating system

3. **Verify it's working**
   ```bash
   claude --version
   ```
   - Type this in your Terminal and press Enter
   - You should see a version number like "v2.0.30"
   - If you see "command not found", the installation didn't work - try the installation steps again

**Don't worry if this seems intimidating!** Once it's installed, you won't need to think about it again.

### Step 2: Installing Claude MPM

Now that Claude Code is installed, we'll add Claude MPM on top of it.

**What is pipx?**
It's a tool that keeps Claude MPM separate from other Python programs on your computer. Think of it like installing an app in its own container.

1. **Install pipx** (if you don't have it):
   ```bash
   python3 -m pip install --user pipx
   python3 -m pipx ensurepath
   ```
   - Close and reopen your Terminal after this

2. **Install Claude MPM with monitoring**:
   ```bash
   pipx install "claude-mpm[monitor]"
   ```
   - This takes 1-2 minutes
   - You'll see installation progress messages
   - `[monitor]` gives you a real-time dashboard (highly recommended!)

3. **Verify Claude MPM is installed**:
   ```bash
   claude-mpm --version
   ```
   - You should see a version number like "5.4.68"

**If something goes wrong:**
- Make sure you have Python 3.11 or newer: `python3 --version`
- If you see permission errors, you might need to add `sudo` before the command (this asks for admin access)

### Step 3: Getting Your API Key

Claude MPM needs permission to use Claude AI. This is like giving it your credit card to make purchases on your behalf.

1. **Get your API key**:
   - Visit: https://console.anthropic.com/settings/keys
   - Click "Create Key"
   - Give it a name like "Claude MPM"
   - **Copy the key immediately** - you won't see it again!
   - It looks like: `sk-ant-api03-...` (a long string of characters)

2. **Save your API key**:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"  # pragma: allowlist secret
   ```
   - Replace `your-key-here` with your actual key
   - This tells your computer to use this key for Claude MPM

3. **Make it permanent** (so you don't have to do this every time):

   **Mac/Linux**:
   ```bash
   echo 'export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"' >> ~/.zshrc  # pragma: allowlist secret
   source ~/.zshrc
   ```

   **Windows**:
   - Search for "Environment Variables" in Windows search
   - Click "Edit system environment variables"
   - Click "Environment Variables"
   - Under "User variables", click "New"
   - Variable name: `ANTHROPIC_API_KEY`
   - Variable value: Your API key
   - Click OK

**Security Note**: Treat this API key like a password. Don't share it or commit it to your code repository.

### Step 4: Getting Your Code

If your code is on GitHub (most common), you'll need to "clone" it. This means downloading a copy to your computer.

1. **Find your repository URL**:
   - Go to your GitHub repository
   - Click the green "Code" button
   - Copy the URL (it looks like: `https://github.com/yourcompany/yourproject.git`)

2. **Choose where to put it**:
   - I recommend creating a "Projects" folder in your home directory
   ```bash
   mkdir ~/Projects
   cd ~/Projects
   ```

3. **Clone (download) your code**:
   ```bash
   git clone https://github.com/yourcompany/yourproject.git
   cd yourproject
   ```
   - Replace the URL with your actual repository URL
   - This downloads all your code
   - The `cd yourproject` command moves you into that folder

**What just happened?**
You now have a complete copy of your codebase on your computer. Think of it like downloading a copy of a Google Doc to edit offline.

### Step 5: Initializing Claude MPM

This is where the magic happens. Claude MPM will analyze your project and set itself up automatically.

1. **Navigate to your project** (if you're not already there):
   ```bash
   cd ~/Projects/yourproject
   ```

2. **Run auto-configuration**:
   ```bash
   claude-mpm auto-configure
   ```

   **What this does**:
   - Scans your codebase to understand what languages and frameworks you use
   - Deploys specialized "agents" (AI assistants) for your tech stack
   - Sets up project-specific memory and context
   - Takes 30-60 seconds

3. **You'll see output like**:
   ```
   🔍 Analyzing project structure...
   ✅ Detected: Python (FastAPI), React, PostgreSQL
   📦 Deploying agents: Python Engineer, React Engineer, Database Expert
   ✅ Configuration complete!
   ```

**What are agents?**
Think of agents as different expert consultants. If your project uses Python, you get a Python expert. If you use React, you get a React expert. They work together to answer your questions.

### Step 6: Your First Conversation

Now you're ready to start asking questions!

1. **Start Claude MPM**:
   ```bash
   claude-mpm run --monitor
   ```
   - The `--monitor` flag shows you a dashboard of what's happening
   - You'll see a chat interface

2. **Ask a simple question**:
   ```
   You: Give me a high-level overview of what this project does.
   ```

3. **Wait for the response**:
   - Claude MPM will analyze your codebase
   - You'll see agents working in the monitor
   - You'll get a detailed, business-friendly explanation

**Congratulations!** You've successfully set up Claude MPM and asked your first question.

---

## Part 4: Questions Founders Should Ask

This section organizes questions by the business concerns you actually care about.

### About Security

**Is our user data secure?**
```
Show me how user data is stored and protected. Are there any security vulnerabilities I should be aware of?
```

**What sensitive information is in our code?**
```
Search for any hardcoded passwords, API keys, or sensitive data in the codebase. This is a security audit.
```

**When was our security last reviewed?**
```
Show me the git history of security-related files and authentication code. When were they last updated?
```

**Are we following best practices?**
```
Review our authentication and authorization systems. Are we following industry best practices for [OWASP/PCI-DSS/HIPAA]?
```

**What happens if we get hacked?**
```
Analyze our error handling and logging. If there's a security breach, how would we know? What's our incident response capability?
```

### About Code Quality

**Is our code healthy?**
```
Give me a code health assessment. What's our technical debt level? Use business terms.
```

**How maintainable is our codebase?**
```
Analyze code organization and documentation. If we need to hire new developers, how easy will it be for them to understand our code?
```

**What areas need attention?**
```
Identify the top 5 technical risks in our codebase. What should we prioritize fixing?
```

**Are we using outdated technology?**
```
Check all our dependencies and frameworks. Are we using outdated or unsupported versions? What's the migration risk?
```

**How well tested is our code?**
```
What percentage of our code has tests? Where are the gaps? What's the risk of bugs in production?
```

### About Team Productivity

**Who committed code this week?**
```
Show me git activity for the past 7 days. Who contributed, what did they work on, and how much code changed?
```

**What features were worked on?**
```
Summarize the work completed in the last sprint/month. What features were shipped? What's still in progress?
```

**Are there any blocked tasks?**
```
Check for TODO comments, blocked pull requests, or failing tests. What's preventing forward progress?
```

**How is work distributed across the team?**
```
Analyze commit history by author. Is work evenly distributed? Are there any bottlenecks or knowledge silos?
```

**What's the velocity of our team?**
```
Compare the last 3 months of commit activity. Are we shipping faster or slower? What changed?
```

### About Business Impact

**How stable is our codebase?**
```
Review error handling, test coverage, and recent bugs. How confident should we be in production stability?
```

**What would break if [X person] left?**
```
Show me code ownership by author. Which parts of the system does [Person X] own? What's our bus factor?
```

**How long would [Y feature] take to build?**
```
I want to build [describe feature]. Analyze our codebase architecture and estimate complexity. What's involved?
```

**Can we scale to 10x users?**
```
Review our database queries, API endpoints, and infrastructure code. What are the bottlenecks if we 10x our user base?
```

**What's our deployment risk?**
```
Analyze our deployment process and CI/CD setup. What could go wrong during a deployment? How do we rollback?
```

### About Technical Decisions

**Should we rewrite in [X technology]?**
```
I'm considering rewriting our [component] in [technology]. Analyze the current implementation and assess the risk vs. benefit.
```

**Is this architecture decision sound?**
```
Our team wants to [describe architectural change]. Review our current architecture and assess if this makes sense.
```

**What tech stack should we hire for?**
```
Analyze our codebase and list all technologies we use. What skills should we prioritize in our next hire?
```

**Are we over-engineering?**
```
Review our code for unnecessary complexity. Are we building features we don't need? Where are we over-engineering?
```

---

## Part 5: Understanding the Answers

Claude MPM will give you technical information. Here's how to interpret it in business terms.

### Code Health Metaphors

#### Technical Debt = Unpaid Maintenance Bills

When Claude MPM says "You have significant technical debt in the authentication system," think of it like this:

**Good analogy**: You've been patching holes in your roof instead of replacing it. It works, but every rainstorm is a risk, and eventually you'll have to do a full replacement—which costs more than if you'd done it earlier.

**Red flags**:
- "Significant technical debt" = Major renovation needed
- "Moderate technical debt" = Scheduled maintenance required
- "Low technical debt" = Minor fixes, normal wear and tear

**Business impact**:
- High debt = Slower feature development, more bugs, harder to hire
- Medium debt = Manageable, but should be addressed
- Low debt = Healthy codebase

#### Code Coverage = Insurance Level

When Claude MPM says "You have 45% code coverage," think insurance:

**Coverage percentages**:
- **80%+**: Well-insured. Most features are protected by tests
- **50-80%**: Partially insured. Core features covered, but gaps exist
- **Under 50%**: Under-insured. High risk of undetected bugs

**Business impact**:
- Low coverage = More bugs reach customers, higher support costs
- High coverage = Faster, safer deployments, more confident releases

#### Dependencies = Suppliers You Rely On

When Claude MPM says "You have 247 dependencies," think supply chain:

**What to watch for**:
- **Outdated dependencies**: Like using a supplier who's gone out of business—security risk, compatibility issues
- **Too many dependencies**: Like having 1,000 suppliers for 100 parts—complexity risk
- **Unmaintained dependencies**: Like a supplier who hasn't shipped an update in 3 years—abandonment risk

**Red flags**:
- Dependencies with known security vulnerabilities
- Libraries that haven't been updated in 2+ years
- Critical dependencies with only one maintainer

### Activity Patterns

#### What Good Developer Activity Looks Like

**Healthy patterns**:
- **Regular, consistent commits**: Daily or near-daily activity
- **Meaningful commit messages**: "Add user authentication" not "fixed stuff"
- **Mixed work types**: Features, bug fixes, refactoring, tests
- **Code reviews**: Pull requests are reviewed before merging
- **Test updates**: Tests change alongside code

**Example of healthy activity**:
```
Monday: 3 commits, added payment integration
Tuesday: 5 commits, fixed bugs from QA testing
Wednesday: 2 commits, updated documentation
Thursday: 4 commits, code review and merge
Friday: 3 commits, refactored database queries
```

#### Red Flags in Commit Patterns

**Warning signs**:
- **Radio silence**: No commits for weeks, then a huge dump of code
- **Vague messages**: "Fixed things", "Updates", "WIP" repeatedly
- **No tests**: Code changes but test files never updated
- **Single reviewer**: Same person writes and approves their own code
- **Friday night deployments**: Risky changes right before the weekend

**Example of concerning activity**:
```
(2 weeks of silence)
Friday 11pm: 47 commits, "major refactor"
(No tests updated, no code review)
```

**What this might mean**: Developer is working in isolation, not following best practices, or there's a process problem.

#### Healthy vs. Concerning Team Dynamics

**Healthy team**:
- Work is distributed across multiple developers
- Code ownership is shared (multiple people touch each area)
- Knowledge is documented in code comments and docs
- Pull requests get feedback from multiple people

**Concerning team**:
- One "hero" developer does 80% of commits
- Critical systems only touched by one person
- No documentation, tribal knowledge only
- Rubber-stamp code reviews (instant approvals)

### Reading Between the Lines

#### When "It Works" Isn't Enough

Your developer says: "The feature works, we can ship it."

**Ask Claude MPM**:
```
Review the pull request for [feature name]. Analyze code quality, test coverage, error handling, and security implications.
```

**What to look for**:
- **Tests**: Does the feature have automated tests?
- **Error handling**: What happens when things go wrong?
- **Security**: Are there any obvious vulnerabilities?
- **Performance**: Will this scale under load?

#### Questions Behind the Questions

**"How long will this take?"** really means:
- How complex is this feature?
- What dependencies does it have?
- What could go wrong?
- Do we have the skills to build it?

**Ask Claude MPM**:
```
Analyze the architecture needed for [feature]. Break down the components, identify dependencies, and estimate complexity on a scale of 1-10.
```

**"Is this developer productive?"** really means:
- Are they shipping quality work?
- Are they communicating effectively?
- Are they learning and improving?
- Are they creating value?

**Ask Claude MPM**:
```
Show me [developer name]'s commit history for the last month. Analyze the types of work, complexity, and impact on the project.
```

---

## Part 6: Common Tasks for Founders

Step-by-step guides for the questions you'll ask most often.

### Task 1: "Show me what changed this week"

**Why you need this**: Weekly status without bothering your team.

**Step-by-step**:

1. **Start Claude MPM**:
   ```bash
   cd ~/Projects/yourproject
   claude-mpm run --monitor
   ```

2. **Ask**:
   ```
   Show me all changes in the last 7 days. Group by developer and feature. Include commit messages.
   ```

3. **What you'll get**:
   - List of all commits by each developer
   - Summary of features worked on
   - Bug fixes and improvements
   - Files that changed

4. **Follow-up questions**:
   ```
   Which of these changes are customer-facing features?
   Were there any critical bug fixes?
   Is anything blocking deployment?
   ```

**Business value**: Know what your team is working on without micromanaging.

### Task 2: "Who's working on what?"

**Why you need this**: Understand current focus and spot bottlenecks.

**Step-by-step**:

1. **Ask**:
   ```
   Show me the most recent commit from each developer. What are they currently working on?
   ```

2. **What you'll get**:
   - Latest activity per team member
   - Active branches (works in progress)
   - Pull requests awaiting review

3. **Deep dive**:
   ```
   Show me all open pull requests. Who's waiting on review? Are there any blockers?
   ```

**Business value**: Identify bottlenecks and ensure work is flowing.

### Task 3: "Is this feature ready to launch?"

**Why you need this**: Make confident go/no-go decisions.

**Step-by-step**:

1. **Ask**:
   ```
   Analyze the [feature name] implementation. Is it production-ready? What are the risks?
   ```

2. **What you'll get**:
   - Code quality assessment
   - Test coverage for the feature
   - Known issues or TODOs
   - Security considerations

3. **Follow-up checklist**:
   ```
   Does this feature have:
   - Automated tests?
   - Error handling?
   - User documentation?
   - Database migrations (if needed)?
   - Security review?
   ```

4. **Get a recommendation**:
   ```
   Based on this analysis, should we ship this feature this week? What would you recommend?
   ```

**Business value**: Ship confidently or delay with good reasons.

### Task 4: "Review this pull request for me"

**Why you need this**: Understand proposed changes in business terms.

**Step-by-step**:

1. **Get the pull request number** from GitHub:
   - Go to your repository on GitHub
   - Click "Pull requests"
   - Note the number (e.g., #247)

2. **Ask**:
   ```
   Review pull request #247. Explain what it does in business terms, assess the risk, and tell me if I should approve it.
   ```

3. **What you'll get**:
   - Plain-English explanation of the change
   - Risk assessment (Low/Medium/High)
   - Code quality review
   - Recommendation

4. **Specific concerns**:
   ```
   Does this PR:
   - Change anything security-related?
   - Affect database performance?
   - Break backward compatibility?
   - Need additional testing?
   ```

**Business value**: Stay informed on code changes without being technical.

### Task 5: "Explain this part of our system"

**Why you need this**: Understand your product at a deeper level.

**Step-by-step**:

1. **Identify what you want to understand**:
   - Example: "How does user authentication work?"
   - Example: "How do we process payments?"
   - Example: "What happens when a user uploads a file?"

2. **Ask**:
   ```
   Explain how [system component] works. Use a flowchart or step-by-step description. Assume I'm non-technical.
   ```

3. **What you'll get**:
   - Business-level explanation
   - Step-by-step flow
   - Key files and components
   - Dependencies and integrations

4. **Deep dive**:
   ```
   What would happen if [failure scenario]? How do we handle errors in this system?
   ```

**Business value**: Informed product decisions and technical conversations.

---

## Part 7: Glossary

Technical terms you'll encounter, explained in plain English.

### Code Management Terms

**Repository (Repo)**
> A folder containing all your code, tracked by Git. Think of it as your project's entire codebase with full history.

**Commit**
> A saved snapshot of code changes. Like saving a document, but with a description of what changed and why.
>
> Example: "Fixed login bug" or "Added payment integration"

**Pull Request (PR)**
> A proposed change to the code. A developer says "I made these changes, please review and merge them."
>
> Think of it as a draft that needs approval before becoming official.

**Branch**
> A separate copy of the code where you can make changes without affecting the main version.
>
> Like working on a Google Doc copy before merging changes into the official version.

**Merge**
> Combining changes from a branch into the main codebase.
>
> Think of it as accepting suggested edits in a document.

**Conflict**
> When two people change the same code in different ways. Someone has to manually decide which version to keep.
>
> Like two people editing the same paragraph differently—you need to reconcile them.

### Architecture Terms

**API (Application Programming Interface)**
> How different pieces of software talk to each other. Like a waiter between you and the kitchen—you make requests, the API delivers results.

**Database**
> Where your application stores data permanently. Think of it as a highly organized filing cabinet.

**Server**
> A computer that runs your application and responds to user requests. Like a store that's always open for customers.

**Frontend**
> The part of your application users see and interact with (website, mobile app).
>
> Think of it as the storefront.

**Backend**
> The part of your application that handles logic, databases, and processing behind the scenes.
>
> Think of it as the warehouse and operations center.

**Microservices**
> Breaking your application into smaller, independent services that work together.
>
> Like having specialized departments (sales, shipping, support) instead of one person doing everything.

### Quality Terms

**Bug**
> An error or defect in the code that causes incorrect behavior.
>
> Like a typo in a contract—it might be small, but it can cause problems.

**Feature**
> New functionality added to your product. Something users can now do that they couldn't before.

**Refactor**
> Rewriting code to make it cleaner and more maintainable without changing what it does.
>
> Like reorganizing your closet—everything's still there, just better organized.

**Deploy**
> Publishing code changes to production (making them live for users).
>
> Like opening a new store location or launching a new product.

**Technical Debt**
> Shortcuts or quick fixes in code that will need to be properly fixed later. Like putting duct tape on a leak—it works now, but you'll need a real fix eventually.

**Code Coverage**
> Percentage of your code that's tested by automated tests. Higher is better.
>
> Like quality control—how much of your product is tested before shipping?

### Development Terms

**Stack / Tech Stack**
> The collection of technologies and tools used to build your application.
>
> Example: "Python, React, PostgreSQL" means backend in Python, frontend in React, database is PostgreSQL.

**Framework**
> Pre-built code that provides structure for building applications. Like a house foundation and framing—you still need to finish it, but the hard part is done.

**Library / Package / Dependency**
> Pre-written code that adds specific functionality. Like buying a component instead of building it yourself.
>
> Example: A payment processing library instead of building payment processing from scratch.

**Environment**
> A separate instance of your application for different purposes:
> - **Development**: Where developers write code (on their computers)
> - **Staging**: Where you test changes before going live
> - **Production**: The live version users interact with

### Process Terms

**CI/CD (Continuous Integration/Continuous Deployment)**
> Automated systems that test and deploy code. Like a factory assembly line for software—code goes in one end, tested and deployed code comes out the other.

**Code Review**
> When one developer examines another's code before it's merged. Like peer review in publishing—catches errors and ensures quality.

**Sprint**
> A fixed time period (usually 1-2 weeks) where a team works on a specific set of features. Common in Agile development.

**Agile**
> A development methodology focused on iterative development, flexibility, and customer feedback. Opposite of "Waterfall" (plan everything upfront).

### Security Terms

**Vulnerability**
> A weakness in your code that could be exploited by attackers. Like a security hole in your building.

**Authentication**
> Verifying who a user is (username/password, biometrics, etc.). Like checking someone's ID.

**Authorization**
> Determining what a verified user is allowed to do. Like having different key cards for different rooms.

**Encryption**
> Scrambling data so only authorized parties can read it. Like speaking in code—even if intercepted, it's meaningless without the key.

**SSL/TLS (HTTPS)**
> Encryption for web traffic. The "lock" icon in your browser. Ensures data between user and server is private.

---

## Part 8: Getting Help

### When to Use "Founders" Output Style

Claude MPM has a special mode designed specifically for non-technical executives. Use it when:

**You want business-focused explanations**:
```
[FOUNDERS MODE] Give me an executive summary of our codebase health.
```

**You need risk assessment**:
```
[FOUNDERS MODE] What are the top technical risks I should be aware of?
```

**You're making strategic decisions**:
```
[FOUNDERS MODE] Should we rebuild our frontend in React or keep our current stack?
```

**Benefits of Founders Mode**:
- Answers in business terms, not technical jargon
- Focus on risk, cost, and business impact
- Analogies and metaphors you can understand
- Executive-level summaries instead of technical details

### How to Ask for Simpler Explanations

If an answer is too technical, don't hesitate to ask for clarification:

**"Explain like I'm 5"**:
```
That was too technical. Explain it like I'm 5 years old.
```

**"Use an analogy"**:
```
Can you explain that using a business analogy? Compare it to something in retail/manufacturing/finance.
```

**"Just the bottom line"**:
```
Skip the technical details. What's the business impact? What decision should I make?
```

**"Visual explanation"**:
```
Can you describe this as a flowchart or diagram? Walk me through step by step.
```

### Escalation: When to Involve Your CTO

Claude MPM is a powerful tool, but it's not a replacement for human judgment. Here's when to escalate to your technical leadership:

**🚨 Immediate Escalation (Security Issues)**:
- Claude MPM identifies security vulnerabilities
- Data breach or exposure detected
- Critical production bugs
- System outages or performance degradation

**⚠️ Strategic Escalation (Big Decisions)**:
- Major architectural changes (rebuilding systems)
- Switching core technologies
- Scaling challenges
- Hiring decisions based on analysis

**📊 Informational Escalation (Validation)**:
- You want a second opinion on Claude MPM's assessment
- Technical debt priorities
- Code quality concerns
- Team productivity patterns

**How to bring it up with your CTO**:
1. **Share what you learned**: "I used Claude MPM to analyze our authentication system..."
2. **Ask for validation**: "It says we have moderate technical debt. Does that match your assessment?"
3. **Get their perspective**: "What would you prioritize fixing first?"
4. **Collaborate**: "Can we use Claude MPM together to dig into this?"

### Common Pitfalls to Avoid

**❌ Don't micromanage**:
- Using Claude MPM to track every commit is overkill
- Trust your team, use this for oversight and strategic understanding
- Focus on patterns and trends, not individual commits

**❌ Don't make technical decisions alone**:
- Claude MPM gives you information, but your CTO has context
- Always validate major decisions with technical leadership
- Use this tool to ask better questions, not replace expertise

**❌ Don't over-interpret metrics**:
- Low test coverage doesn't mean your team is bad
- High technical debt doesn't mean you need to rebuild everything
- Activity patterns need context—talk to your team

**✅ Do use it for**:
- Informed questions in technical discussions
- Understanding what your team is building
- Identifying risks early
- Making strategic investment decisions
- Due diligence and investor communications

### Getting More Help

**Official Documentation**:
- Full documentation: https://github.com/bobmatnyc/claude-mpm/tree/main/docs
- Quick start guide: `docs/getting-started/quick-start.md`
- User guide: `docs/user/user-guide.md`

**Community Support**:
- GitHub Issues: Report bugs or ask questions
- Discussions: Share use cases and learn from others

**Pro Tips**:
1. **Save your frequent questions**: Create a text file with your go-to questions
2. **Schedule weekly reviews**: Every Monday, ask "what changed last week?"
3. **Use it for onboarding**: New board member? Have Claude MPM explain your architecture
4. **Investor prep**: Before fundraising calls, get current state of code quality
5. **Quarterly reviews**: Deep dive into technical health every quarter

---

## Conclusion

You now have everything you need to start using Claude MPM as a non-technical founder. Remember:

**You don't need to understand every technical detail** - that's what your technical team is for. What you need is:
- The ability to ask informed questions
- Understanding of risks and opportunities
- Confidence in your technical decisions
- Better communication with your technical team

**Claude MPM is your technical advisor**, available 24/7 to help you understand your codebase, assess your team's work, and make informed business decisions.

**Start simple**:
1. Ask basic questions about what your code does
2. Review weekly activity
3. Gradually build your technical literacy
4. Use it to ask better questions, not replace your team

**Most importantly**: This tool empowers you to be a more effective leader, not to become a developer. Use it to understand, communicate, and make informed decisions—then trust your team to execute.

Good luck, and welcome to a new level of technical oversight!

---

**Document Information**:
- **Version**: 1.0.0
- **Last Updated**: 2026-01-05
- **Audience**: Non-technical founders and business leaders
- **Prerequisites**: None (complete beginner-friendly)
- **Estimated Reading Time**: 30-40 minutes
- **Next Steps**: Read `docs/getting-started/quick-start.md` for installation details
