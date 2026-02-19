# Hello World with Claude MPM

A hands-on quickstart guide to get you building with Claude MPM in 30-60 minutes.

## What You'll Build

Choose your learning path:

- **Path A: CLI Tool (30 mins)** - Build a simple Python task manager to learn MPM basics
- **Path B: Full-Stack Web App (60 mins)** - Build a FastAPI + React app to see multi-agent workflows in action

Both paths teach you:
- How to initialize projects with MPM
- How to write effective prompts
- How multi-agent delegation works
- How to iterate and refine with AI assistance

## Prerequisites

Before starting, ensure you have:

### Required Software

- **Claude Code CLI v1.0.92+** - [Installation guide](https://docs.anthropic.com/en/docs/claude-code)
  - ⚠️ Note: This is Claude *Code* CLI, not Claude Desktop app
  - Verify: `claude --version`
- **Python 3.11+** - Check with `python --version`
- **Git** - Check with `git --version`

### Optional but Recommended: ASDF Version Manager

ASDF helps manage Python and Node.js versions consistently:

```bash
# Install ASDF (macOS/Linux)
brew install asdf
# OR
git clone https://github.com/asdf-vm/asdf.git ~/.asdf --branch v0.13.1

# Add to your shell profile (~/.bashrc, ~/.zshrc)
echo '. "$HOME/.asdf/asdf.sh"' >> ~/.bashrc

# Install language plugins
asdf plugin add python
asdf plugin add nodejs

# Install specific versions
asdf install python 3.11.12
asdf install nodejs 18.20.0

# Set global defaults
asdf global python 3.11.12
asdf global nodejs 18.20.0
```

### Install Claude MPM

```bash
# Recommended: Use pipx for isolated installation
pipx install "claude-mpm[monitor]"

# Alternative: Use pip
pip install "claude-mpm[monitor]"

# Verify installation
claude-mpm --version
claude-mpm doctor
```

✅ If `claude-mpm doctor` shows all checks passing, you're ready to start!

---

## Path A: CLI Tool (30 minutes)

Build a simple Python task manager CLI to learn MPM fundamentals.

### Why This Path?

- Single language (Python)
- Simple structure (1-2 files to start)
- Learn core MPM concepts quickly
- Perfect for first-time users

### Step 1: Create Project Structure (5 mins)

First, scaffold your project *before* running `/mpm-init`:

```bash
# Create project directory
mkdir hello-cli
cd hello-cli

# Create Python project structure
mkdir -p src/taskmanager tests

# Create pyproject.toml
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=64", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "taskmanager"
version = "0.1.0"
description = "A simple CLI task manager"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
]

[project.scripts]
taskmanager = "taskmanager.cli:cli"
EOF

# Create initial CLI file
cat > src/taskmanager/__init__.py << 'EOF'
"""Simple task manager CLI."""
__version__ = "0.1.0"
EOF

cat > src/taskmanager/cli.py << 'EOF'
"""Task manager command-line interface."""
import click

@click.group()
@click.version_option()
def cli():
    """A simple task manager CLI."""
    pass

@cli.command()
@click.argument('task')
def add(task):
    """Add a new task."""
    click.echo(f"Added task: {task}")

@cli.command()
def list():
    """List all tasks."""
    click.echo("No tasks yet!")

if __name__ == '__main__':
    cli()
EOF

# Create .tool-versions for ASDF (optional)
cat > .tool-versions << 'EOF'
python 3.11.12
EOF

# Install dependencies
pip install -e ".[dev]"

# Initialize git
git init
git add .
git commit -m "Initial project scaffold"
```

**Why scaffold first?** MPM's `/mpm-init` analyzes your project structure to generate context-aware documentation. An empty directory gives generic results.

### Step 2: Initialize with MPM (5 mins)

Now run `/mpm-init` to analyze your project and set up MPM:

```bash
# Start MPM session
claude-mpm run --monitor
```

Inside the Claude session, run:

```
/mpm-init
```

**Expected output:**

```
🔍 Analyzing project structure...

Detected:
  Language: Python 3.11
  Framework: Click CLI
  Dependencies: click, pytest
  Structure: src/taskmanager/

✅ Generated CLAUDE.md with project-specific instructions
✅ Added .claude-mpm/memories/ directory
✅ Updated .gitignore (excluded .claude-mpm/)

Next steps:
  1. Review CLAUDE.md for project guidelines
  2. Start building features!
```

**What just happened?**
- MPM analyzed your code structure
- Created `CLAUDE.md` with project context
- Set up memory system for learning
- Configured git to ignore MPM internal files

### Step 3: Build Features with MPM (15 mins)

Now let's use MPM to add features. Try these prompts:

#### Prompt 1: Add Task Persistence

```
Add task persistence using JSON file storage. Tasks should be saved to ~/.taskmanager/tasks.json and loaded on startup. Include error handling for file operations.
```

**What to expect:**
- Engineer agent implements JSON storage
- Code is added to `cli.py`
- File operations with proper error handling
- Automatic git commit of changes

**Tip:** Watch the monitor dashboard to see agent activity!

#### Prompt 2: Add Delete Command

```
Add a delete command that removes a task by ID. Show a confirmation message after deletion. Do not commit yet - I want to test it first.
```

**What to expect:**
- Engineer agent adds `delete` command
- Implements task lookup by ID
- Adds user feedback
- NO automatic commit (you asked to wait)

**Key concept:** You can control commit behavior with your prompts!

#### Prompt 3: Add Tests

```
Add pytest tests for the add, list, and delete commands. Include tests for error cases like invalid IDs and empty task lists.
```

**What to expect:**
- QA agent creates `tests/test_cli.py`
- Multiple test cases covering happy paths and errors
- Tests run to verify they pass
- Automatic commit with test additions

#### Prompt 4: Improve CLI Output

```
Improve the list command to show tasks in a numbered table format with better formatting. Use click's styling features for colors.
```

**What to expect:**
- Engineer agent refactors `list` command
- Adds colored output with click.style()
- Improves UX with better formatting

### Step 4: Test Your CLI

```bash
# Exit MPM session (Ctrl+D or type 'exit')

# Test your CLI
taskmanager add "Learn Claude MPM"
taskmanager add "Build something cool"
taskmanager list
taskmanager delete 1
taskmanager list
```

### Key Lessons from Path A

✅ **Always scaffold before `/mpm-init`** - MPM needs structure to analyze
✅ **Be specific in prompts** - "Add JSON storage with error handling" > "Make it persistent"
✅ **Control commits with prompts** - Add "do not commit" when experimenting
✅ **Iterate quickly** - Make changes, test, refine with new prompts

### Next Steps

- Re-run `/mpm-init update` after major changes
- Try Path B for multi-agent workflows
- Read [Common Pitfalls](#common-pitfalls) below

---

## Path B: Full-Stack Web App (60 minutes)

Build a FastAPI + React todo app to see multi-agent coordination in action.

### Why This Path?

- Realistic full-stack scenario
- Multiple technologies (Python backend, TypeScript frontend)
- See PM agent delegation to specialists
- Learn how MPM coordinates across domains

### Step 1: Scaffold Backend (10 mins)

```bash
# Create project directory
mkdir hello-webapp
cd hello-webapp

# Create backend structure
mkdir -p backend/src/api backend/tests

# Create backend pyproject.toml
cat > backend/pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=64", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "todo-api"
version = "0.1.0"
description = "FastAPI Todo API"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.4.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "httpx>=0.25.0",
]
EOF

# Create initial FastAPI app
cat > backend/src/api/main.py << 'EOF'
"""FastAPI Todo API."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Todo API", version="0.1.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Todo API is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
EOF

# Install backend dependencies
cd backend
pip install -e ".[dev]"
cd ..
```

### Step 2: Scaffold Frontend (10 mins)

```bash
# Create React + TypeScript frontend with Vite
npm create vite@latest frontend -- --template react-ts

# Navigate to frontend and install dependencies
cd frontend
npm install
cd ..

# Create .tool-versions for ASDF
cat > .tool-versions << 'EOF'
python 3.11.12
nodejs 18.20.0
EOF

# Initialize git
git init
git add .
git commit -m "Initial full-stack scaffold"
```

### Step 3: Initialize with MPM (5 mins)

```bash
# Start MPM with monitoring dashboard
claude-mpm run --monitor
```

Inside Claude session:

```
/mpm-init
```

**Expected output:**

```
🔍 Analyzing project structure...

Detected:
  Backend: FastAPI (Python 3.11)
  Frontend: React + TypeScript (Vite)
  Structure: Monorepo with backend/ and frontend/

✅ Generated CLAUDE.md with full-stack guidance
✅ Detected specialized agents:
   - Backend Engineer (Python/FastAPI)
   - Frontend Engineer (React/TypeScript)
   - QA Engineer (Testing both tiers)
✅ Added .claude-mpm/memories/

Next steps:
  1. Review CLAUDE.md for project architecture
  2. Start building features with multi-agent workflows!
```

### Step 4: Multi-Agent Delegation Example (30 mins)

Now let's see MPM's multi-agent coordination in action!

#### Example 1: Add Todo API Endpoints

```
Add CRUD endpoints for todos to the FastAPI backend:
- POST /todos - Create a todo (title, description, completed status)
- GET /todos - List all todos
- GET /todos/{id} - Get a specific todo
- PUT /todos/{id} - Update a todo
- DELETE /todos/{id} - Delete a todo

Use Pydantic models for request/response validation. Store todos in memory for now (list/dict).
```

**What to expect - Multi-agent delegation:**

```
🧠 PM Agent: Analyzing requirements...

📋 Delegation Plan:
  1. Research Agent: Check FastAPI best practices for CRUD APIs
  2. Backend Engineer: Implement endpoints with Pydantic models
  3. QA Agent: Add API tests

🔍 Research Agent: Analyzing FastAPI patterns...
  ✓ Recommendations: Use Pydantic models, HTTPException for errors, dependency injection

⚙️ Backend Engineer: Implementing CRUD endpoints...
  Created: backend/src/api/models.py (Pydantic models)
  Updated: backend/src/api/main.py (all 5 endpoints)
  Added: backend/src/api/storage.py (in-memory storage)

🧪 QA Agent: Adding API tests...
  Created: backend/tests/test_api.py (15 test cases)
  Result: All tests passing ✅

✅ PM Agent: Todo API implementation complete!

Git status: 4 files changed, 187 insertions(+)
```

**Key observation:** PM automatically coordinated three agents without you asking!

#### Example 2: Build React Frontend

```
Create a React frontend that:
1. Fetches todos from the API on load
2. Displays todos in a list with checkbox for completion
3. Has a form to add new todos (title and description)
4. Has delete buttons for each todo

Use fetch API for HTTP requests. Add basic error handling. Style with Tailwind CSS utility classes.
```

**What to expect:**

```
🧠 PM Agent: Analyzing frontend requirements...

📋 Delegation Plan:
  1. Frontend Engineer: Build React components and API integration
  2. QA Agent: Add component tests (optional)

⚙️ Frontend Engineer: Building React UI...
  Created: frontend/src/services/api.ts (API client)
  Created: frontend/src/components/TodoList.tsx
  Created: frontend/src/components/TodoForm.tsx
  Updated: frontend/src/App.tsx (integrate components)
  Added: Tailwind CSS configuration

✅ PM Agent: Frontend implementation complete!

Git status: 5 files changed, 234 insertions(+)
```

#### Example 3: Add Authentication (Advanced)

```
Add JWT authentication to the API:
- POST /auth/register - Register new user
- POST /auth/login - Login and get JWT token
- Protect todo endpoints (require valid JWT)

Then update the frontend to:
- Show login form before todos
- Store JWT in localStorage
- Include JWT in API requests
- Handle 401 errors (logout and show login again)
```

**What to expect - Complex multi-agent coordination:**

```
🧠 PM Agent: Analyzing authentication requirements...
  This is a complex feature spanning backend and frontend.

📋 Delegation Plan:
  1. Research Agent: Analyze JWT auth patterns for FastAPI + React
  2. Backend Engineer: Implement auth endpoints and JWT middleware
  3. Frontend Engineer: Build login UI and token management
  4. QA Agent: Add auth tests for both tiers
  5. Documentation Agent: Update API docs

🔍 Research Agent: Analyzing auth patterns...
  ✓ Recommendations: python-jose for JWT, bcrypt for passwords, token refresh strategy

⚙️ Backend Engineer: Implementing JWT auth...
  Created: backend/src/api/auth.py (JWT utilities)
  Created: backend/src/api/users.py (user storage)
  Updated: backend/src/api/main.py (auth routes, protected endpoints)
  Added: pyproject.toml (python-jose, passlib dependencies)

⚙️ Frontend Engineer: Building auth UI...
  Created: frontend/src/components/LoginForm.tsx
  Created: frontend/src/utils/auth.ts (token management)
  Updated: frontend/src/services/api.ts (JWT interceptor)
  Updated: frontend/src/App.tsx (conditional rendering)

🧪 QA Agent: Adding comprehensive auth tests...
  Created: backend/tests/test_auth.py (auth endpoint tests)
  Created: backend/tests/test_protected.py (JWT middleware tests)
  Result: All 12 tests passing ✅

📝 Documentation Agent: Updating documentation...
  Created: backend/API.md (auth endpoints documentation)
  Updated: README.md (authentication section)

✅ PM Agent: Authentication implementation complete!

Summary:
  - JWT auth with token refresh
  - Secure password hashing (bcrypt)
  - Protected API endpoints
  - Complete test coverage
  - Documentation updated

Git status: 12 files changed, 487 insertions(+)
```

**Key observation:** PM coordinated FIVE agents across backend and frontend!

### Step 5: Run Your Full-Stack App

```bash
# Exit MPM session

# Terminal 1: Start backend
cd backend
uvicorn src.api.main:app --reload --port 8000

# Terminal 2: Start frontend
cd frontend
npm run dev

# Open browser: http://localhost:5173
```

### Key Lessons from Path B

✅ **PM auto-delegates** - You don't specify which agents, PM decides
✅ **Multi-agent coordination** - Complex tasks split across specialists
✅ **Research before implementation** - Research agent analyzes patterns first
✅ **Testing is automatic** - QA agent adds tests without prompting
✅ **Documentation is automatic** - Documentation agent updates docs

### Next Steps

- Try adding database persistence (PostgreSQL or MongoDB)
- Deploy to production (Render, Railway, or Docker)
- Add more features (filtering, due dates, tags)

---

## Key Concepts

### Why Scaffold BEFORE /mpm-init?

**The chicken-and-egg problem:**

- `/mpm-init` analyzes your project structure to generate context-aware `CLAUDE.md`
- An empty directory has nothing to analyze → generic output
- Solution: Create basic structure first, then run `/mpm-init`

**Good workflow:**
1. Scaffold project (files, dependencies, basic structure)
2. Run `/mpm-init` (analyzes and generates CLAUDE.md)
3. Start building features with MPM

**Bad workflow:**
1. Run `/mpm-init` on empty directory
2. Get generic CLAUDE.md with no project context
3. MPM doesn't understand your project

### Re-running /mpm-init as Project Evolves

Your project changes over time. Keep `CLAUDE.md` fresh:

```bash
# Quick update (analyzes last 30 days of git history)
/mpm-init update

# Custom timeframe (last 7 days)
/mpm-init context --days 7

# Full re-analysis (re-generates everything)
/mpm-init --comprehensive
```

**When to re-run:**
- After adding new dependencies or frameworks
- After major architectural changes
- Before starting work after long break
- Weekly for active projects

### Auto-Commit Behavior

**How it works:** Agents commit based on their instructions—Claude Code itself doesn't auto-commit. You control when commits happen through your prompts.

**Default behavior:** Agents commit working implementations automatically.

**Why this is good:**
- Tracks AI-generated changes in git history
- Easy to revert if something breaks
- Shows progression of features

**Why this can be problematic:**
- Multiple commits during debugging ("spaghettification")
- Messy git history
- Hard to create clean pull requests

**Quick mitigation strategies:**

**Strategy 1: Control commits with prompts**
```
Add a delete command. Do not commit yet - I want to test it first.
```

```
This is a debugging session - don't commit until we have a working solution.
```

**Strategy 2: Work on feature branches**
```bash
git checkout -b feature/new-feature
# Work with MPM
# Squash commits later
git rebase -i main
```

**Strategy 3: Squash commits after**
```bash
# Squash last 5 commits
git reset --soft HEAD~5
git commit -m "feat: add user authentication"
```

**Strategy 4: Use separate testing branch**
```bash
git checkout -b experiment
# Let MPM make commits
# Cherry-pick good commits to main
git checkout main
git cherry-pick <commit-hash>
```

**📖 For comprehensive debugging strategies, see:** [Debugging Session Strategies Guide](../guides/debugging-session-strategies.md)

### Understanding Multi-Agent Delegation

**How PM decides which agents to use:**

1. **Analyzes your prompt** - What domains are involved?
2. **Checks project structure** - What technologies detected?
3. **Creates delegation plan** - Which specialists needed?
4. **Coordinates execution** - Agents work in sequence or parallel

**Example delegation patterns:**

| Your Prompt | Agents Involved |
|-------------|-----------------|
| "Add login API endpoint" | Research → Backend Engineer → QA |
| "Fix bug in React component" | Frontend Engineer |
| "Add database migrations" | Research → Backend Engineer → Documentation |
| "Improve test coverage" | QA Agent |
| "Add user authentication" | Research → Backend → Frontend → QA → Documentation |

**You don't need to specify agents!** PM figures it out.

---

## Common Pitfalls

### Pitfall 1: Wrong Versions

**Problem:** Python 3.9 or Node 14 installed, MPM requires 3.11+ and Node 18+

**Symptoms:**
- Dependency installation errors
- `claude-mpm doctor` fails
- Import errors

**Solution:** Use ASDF to manage versions (see [Prerequisites](#optional-but-recommended-asdf-version-manager))

### Pitfall 2: Claude Code vs Claude Desktop

**Problem:** Installing Claude Desktop app instead of Claude Code CLI

**Symptoms:**
- `claude: command not found`
- MPM won't start

**Solution:**
- Install Claude Code CLI from [official docs](https://docs.anthropic.com/en/docs/claude-code)
- Verify: `claude --version` should show v1.0.92+

### Pitfall 3: /mpm-init on Empty Directory

**Problem:** Running `/mpm-init` before creating project structure

**Symptoms:**
- Generic CLAUDE.md with no project-specific context
- MPM doesn't understand your tech stack
- Poor agent selection

**Solution:** Scaffold project FIRST, then run `/mpm-init` (see workflows above)

### Pitfall 4: Vague Prompts

**Problem:** Prompts like "make it better", "fix bugs", "add features"

**Symptoms:**
- PM agent confused
- Wrong agents delegated
- Unsatisfactory results

**Solution:** Be specific!

❌ Bad: "Add authentication"
✅ Good: "Add JWT authentication with bcrypt password hashing, protecting all /todos endpoints"

❌ Bad: "Fix the bug"
✅ Good: "Fix the NullPointerException in TodoList.tsx line 42 when todos array is empty"

❌ Bad: "Make it faster"
✅ Good: "Add database indexes on todos.user_id and todos.created_at for faster queries"

### Pitfall 5: Not Re-running /mpm-init

**Problem:** Running `/mpm-init` once at project start, never updating

**Symptoms:**
- CLAUDE.md becomes stale
- MPM misses new patterns
- Agent selection degrades

**Solution:** Re-run `/mpm-init update` periodically:
- After adding dependencies
- After architectural changes
- Weekly for active projects

### Pitfall 6: Deploying All Agents

**Problem:** Running `claude-mpm auto-configure` and accepting all 47+ default agents

**Symptoms:**
- Slow responses
- High token usage
- Context bloat

**Solution:** Only deploy agents you need!

```bash
# Let MPM auto-detect based on your tech stack
claude-mpm auto-configure

# OR manually select agents
claude-mpm agents list
claude-mpm agents deploy engineer-python
claude-mpm agents deploy engineer-react
claude-mpm agents deploy qa-universal
```

**Good starting set:**
- PM agent (required)
- Engineer agents for your languages
- QA agent
- Documentation agent (optional)

### Pitfall 7: Not Using Monitor Dashboard

**Problem:** Running `claude-mpm` without `--monitor` flag

**Symptoms:**
- Can't see agent activity
- Hard to debug issues
- Miss useful insights

**Solution:** Always use monitor dashboard!

```bash
# Start with monitoring
claude-mpm run --monitor

# Opens web dashboard at http://localhost:3000
```

**Dashboard shows:**
- Agent delegation flow
- Current task status
- Token usage metrics
- Error logs

---

## Next Steps

### Learn More

- **User Guide**: [../user/user-guide.md](../user/user-guide.md) - Comprehensive feature guide
- **PM Workflow**: [../agents/pm-workflow.md](../agents/pm-workflow.md) - How PM agent works
- **Skills System**: [../guides/skills-guide.md](../guides/skills-guide.md) - Advanced MPM features
- **Troubleshooting**: [../user/troubleshooting.md](../user/troubleshooting.md) - Common issues and solutions

### Try Advanced Features

- **Semantic Search**: Find code by meaning, not just keywords
- **Session Resume**: Continue work across sessions with `--resume`
- **Ticketing Integration**: Connect MPM to Linear, Jira, GitHub Issues
- **Custom Agents**: Create project-specific agents

### Join the Community

- **GitHub**: [bobmatnyc/claude-mpm](https://github.com/bobmatnyc/claude-mpm)
- **Issues**: Report bugs or request features
- **Discussions**: Share your projects and tips

### Sample Projects

Check out full working examples:

- `examples/quickstart-cli/` - Complete CLI tool with MPM history
- `examples/quickstart-webapp/` - Full-stack app with multi-agent workflows

---

## Quick Reference

### Essential Commands

```bash
# Start MPM session
claude-mpm run --monitor

# Initialize project
/mpm-init

# Update project context
/mpm-init update

# Check status
claude-mpm doctor

# List agents
claude-mpm agents list

# Resume previous session
claude-mpm --resume
```

### Good Prompts

```
"Add [feature] that [specific behavior] using [library/approach]"
"Add tests for [feature] covering [scenarios]"
"Fix [specific issue] in [file] where [problem]"
"Refactor [component] to [improvement] while [constraint]"
```

### Commit Control

```
"Do not commit yet - I want to test first"
"Make changes without committing"
"Commit this with message: [your message]"
```

### Agent Control (Usually Not Needed)

```
"Have the QA agent add tests for this"
"Ask the Documentation agent to update the README"
```

PM usually figures this out automatically!

---

**Ready to build?** Choose a path above and start your first MPM project in 30-60 minutes! 🚀
