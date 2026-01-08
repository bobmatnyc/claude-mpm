# Project Bootstrap Workflows

**Complete guide to setting up new projects before running /mpm-init**

## Table of Contents

- [Overview](#overview)
- [Why Bootstrap Matters](#why-bootstrap-matters)
- [Prerequisites](#prerequisites)
- [Approach 1: Manual Scaffolding](#approach-1-manual-scaffolding)
  - [Python + FastAPI](#python--fastapi)
  - [JavaScript/TypeScript + Node.js](#javascripttypescript--nodejs)
  - [Java + Spring Boot](#java--spring-boot)
  - [Vue + Quasar](#vue--quasar)
- [Approach 2: MPM-Assisted Scaffolding](#approach-2-mpm-assisted-scaffolding)
- [ASDF Tool Version Management](#asdf-tool-version-management)
- [Running /mpm-init](#running-mpm-init)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

Claude MPM works best with properly structured projects. Before running `/mpm-init`, you need a basic project scaffold with:

- **Project directory structure** - Organized source code layout
- **Build configuration** - Package managers and build tools configured
- **Tool versions defined** - Consistent development environment via ASDF
- **Basic documentation** - README and essential project files

This guide covers **two approaches** to project bootstrapping:

1. **Manual Scaffolding** - Use standard tooling (uv, npm, Maven, etc.)
2. **MPM-Assisted Scaffolding** - Ask Claude MPM to generate structure for you

## Why Bootstrap Matters

### Before /mpm-init

MPM needs to analyze your project to generate intelligent documentation. Without proper structure:

❌ **Without Bootstrap:**
```bash
mkdir my-project
cd my-project
/mpm-init  # What should MPM analyze? No context!
```

✅ **With Bootstrap:**
```bash
mkdir my-project
cd my-project
uv init  # Creates Python project structure
# Add basic files, configure tools
/mpm-init  # MPM extracts architecture from your setup
```

### Benefits of Proper Bootstrapping

- **Better AI Assistance** - Claude understands your project structure
- **Consistent Environments** - ASDF ensures version compatibility
- **Faster Onboarding** - Clear structure helps team members
- **Reduced Errors** - Proper tooling prevents common issues
- **Documentation Quality** - /mpm-init generates accurate instructions

## Prerequisites

Before bootstrapping any project:

### Required Tools

- **Git** - Version control
  ```bash
  git --version  # Should be 2.x or higher
  ```

- **ASDF** - Tool version management ([Install guide](asdf-tool-versions.md))
  ```bash
  asdf --version  # Should be v0.14.0 or higher
  ```

- **Claude Code** - MPM CLI integration
  ```bash
  claude-mpm version  # Verify MPM is installed
  ```

### Optional but Recommended

- **GitHub CLI** - Repository management
  ```bash
  gh --version
  ```

- **Make** - Build automation
  ```bash
  make --version
  ```

## Approach 1: Manual Scaffolding

Use standard tooling to create project structure. This approach gives you full control and follows framework conventions.

### Python + FastAPI

FastAPI is a modern, high-performance Python web framework perfect for APIs.

#### 1. Install Python and uv via ASDF

```bash
# Install ASDF plugins
asdf plugin add python
asdf plugin add uv https://github.com/b1-luettje/asdf-uv.git

# Install specific versions
asdf install python 3.11.12
asdf install uv 0.9.17
```

#### 2. Create Project Directory

```bash
# Create and navigate to project
mkdir my-fastapi-app
cd my-fastapi-app

# Set tool versions
cat > .tool-versions <<EOF
python 3.11.12
uv 0.9.17
EOF

# Install tools for this project
asdf install
```

#### 3. Initialize Python Project with uv

```bash
# Initialize project
uv init

# Install FastAPI dependencies
uv add fastapi uvicorn[standard]

# Add development dependencies
uv add --dev pytest pytest-asyncio httpx ruff mypy
```

#### 4. Create Basic Project Structure

```bash
# Create directory structure
mkdir -p {src/app,tests,docs}

# Create main application file
cat > src/app/main.py <<'EOF'
from fastapi import FastAPI

app = FastAPI(
    title="My FastAPI App",
    description="A sample FastAPI application",
    version="0.1.0"
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
EOF

# Create test file
cat > tests/test_main.py <<'EOF'
from fastapi.testclient import TestClient
from src.app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
EOF
```

#### 5. Create Configuration Files

```bash
# Create pyproject.toml for tool configuration
cat > pyproject.toml <<'EOF'
[project]
name = "my-fastapi-app"
version = "0.1.0"
description = "A sample FastAPI application"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "httpx>=0.25.0",
    "ruff>=0.1.0",
    "mypy>=1.7.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = true
EOF

# Create README
cat > README.md <<'EOF'
# My FastAPI App

A sample FastAPI application.

## Setup

```bash
# Install dependencies
uv sync

# Run development server
uvicorn src.app.main:app --reload
```

## Testing

```bash
# Run tests
uv run pytest
```

## Development

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Type check
uv run mypy src/
```
EOF
```

#### 6. Initialize Git Repository

```bash
# Create .gitignore
cat > .gitignore <<'EOF'
__pycache__/
*.py[cod]
*$py.class
.venv/
.env
*.log
.pytest_cache/
.mypy_cache/
.ruff_cache/
dist/
build/
*.egg-info/
EOF

# Initialize git
git init
git add .
git commit -m "Initial FastAPI project setup"
```

#### 7. Verify Setup

```bash
# Run the application
uvicorn src.app.main:app --reload &

# Test the endpoint
curl http://localhost:8000/
# Expected: {"message":"Hello World"}

# Run tests
uv run pytest

# Stop the server
kill %1
```

**✅ Your Python + FastAPI project is ready for /mpm-init!**

---

### JavaScript/TypeScript + Node.js

Modern JavaScript/TypeScript project with Node.js runtime.

#### 1. Install Node.js via ASDF

```bash
# Install ASDF Node.js plugin
asdf plugin add nodejs

# Install specific version
asdf install nodejs 20.11.0
```

#### 2. Create Project Directory

```bash
# Create and navigate to project
mkdir my-node-app
cd my-node-app

# Set tool versions
cat > .tool-versions <<EOF
nodejs 20.11.0
EOF

# Install tools
asdf install
```

#### 3. Initialize Node.js Project

```bash
# Initialize package.json
npm init -y

# Install TypeScript and dependencies
npm install --save-dev typescript @types/node ts-node nodemon
npm install express
npm install --save-dev @types/express

# Initialize TypeScript configuration
npx tsc --init
```

#### 4. Configure TypeScript

```bash
# Create tsconfig.json
cat > tsconfig.json <<'EOF'
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "moduleResolution": "node"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
EOF
```

#### 5. Create Project Structure

```bash
# Create directories
mkdir -p {src,tests,dist}

# Create main application file
cat > src/index.ts <<'EOF'
import express, { Request, Response } from 'express';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

app.get('/', (req: Request, res: Response) => {
  res.json({ message: 'Hello World' });
});

app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'healthy' });
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

export default app;
EOF
```

#### 6. Update package.json Scripts

```bash
# Update package.json with scripts
cat > package.json <<'EOF'
{
  "name": "my-node-app",
  "version": "0.1.0",
  "description": "A sample Node.js TypeScript application",
  "main": "dist/index.js",
  "scripts": {
    "build": "tsc",
    "dev": "nodemon --exec ts-node src/index.ts",
    "start": "node dist/index.js",
    "test": "echo \"Error: no test specified\" && exit 1"
  },
  "keywords": [],
  "author": "",
  "license": "MIT",
  "dependencies": {
    "express": "^4.18.0"
  },
  "devDependencies": {
    "@types/express": "^4.17.0",
    "@types/node": "^20.11.0",
    "nodemon": "^3.0.0",
    "ts-node": "^10.9.0",
    "typescript": "^5.3.0"
  }
}
EOF

# Reinstall dependencies
npm install
```

#### 7. Create README and Git Setup

```bash
# Create README
cat > README.md <<'EOF'
# My Node.js App

A sample Node.js TypeScript application with Express.

## Setup

```bash
# Install dependencies
npm install
```

## Development

```bash
# Run development server with auto-reload
npm run dev
```

## Production

```bash
# Build TypeScript to JavaScript
npm run build

# Run production server
npm start
```
EOF

# Create .gitignore
cat > .gitignore <<'EOF'
node_modules/
dist/
.env
*.log
.DS_Store
EOF

# Initialize git
git init
git add .
git commit -m "Initial Node.js TypeScript project setup"
```

#### 8. Verify Setup

```bash
# Run development server
npm run dev &

# Test endpoint
curl http://localhost:3000/
# Expected: {"message":"Hello World"}

# Build project
npm run build

# Stop server
kill %1
```

**✅ Your Node.js + TypeScript project is ready for /mpm-init!**

---

### Java + Spring Boot

Enterprise-grade Java application with Spring Boot framework.

#### 1. Install Java via ASDF

```bash
# Install ASDF Java plugin
asdf plugin add java

# Install Java (OpenJDK)
asdf install java openjdk-21.0.1

# Set as global default
asdf global java openjdk-21.0.1
```

#### 2. Create Project with Spring Initializr

**Option A: Web Interface**

1. Visit [start.spring.io](https://start.spring.io)
2. Configure:
   - **Project**: Maven
   - **Language**: Java
   - **Spring Boot**: 3.2.x (latest stable)
   - **Project Metadata**:
     - Group: `com.example`
     - Artifact: `myapp`
     - Name: `myapp`
     - Package name: `com.example.myapp`
     - Packaging: Jar
     - Java: 21
3. **Dependencies**: Add `Spring Web`, `Spring Boot DevTools`
4. Click **Generate** and extract ZIP

**Option B: Command Line (curl)**

```bash
# Create Spring Boot project via Spring Initializr API
curl https://start.spring.io/starter.zip \
  -d type=maven-project \
  -d language=java \
  -d bootVersion=3.2.1 \
  -d baseDir=my-spring-app \
  -d groupId=com.example \
  -d artifactId=myapp \
  -d name=myapp \
  -d packageName=com.example.myapp \
  -d packaging=jar \
  -d javaVersion=21 \
  -d dependencies=web,devtools \
  -o my-spring-app.zip

# Extract and navigate
unzip my-spring-app.zip
cd my-spring-app
```

#### 3. Set Tool Versions

```bash
# Create .tool-versions
cat > .tool-versions <<EOF
java openjdk-21.0.1
EOF

# Ensure Java version
asdf install
```

#### 4. Add Sample REST Controller

```bash
# Create controller directory
mkdir -p src/main/java/com/example/myapp/controller

# Create REST controller
cat > src/main/java/com/example/myapp/controller/HelloController.java <<'EOF'
package com.example.myapp.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import java.util.Map;

@RestController
public class HelloController {

    @GetMapping("/")
    public Map<String, String> root() {
        return Map.of("message", "Hello World");
    }

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "healthy");
    }
}
EOF
```

#### 5. Update Application Properties

```bash
# Configure application
cat > src/main/resources/application.properties <<'EOF'
# Server Configuration
server.port=8080
spring.application.name=myapp

# Logging
logging.level.root=INFO
logging.level.com.example.myapp=DEBUG
EOF
```

#### 6. Create README and Git Setup

```bash
# Update README
cat > README.md <<'EOF'
# My Spring Boot App

A sample Spring Boot application.

## Setup

Requires Java 21 (managed via ASDF).

```bash
# Ensure correct Java version
asdf install
```

## Development

```bash
# Run application
./mvnw spring-boot:run
```

Application runs on http://localhost:8080

## Testing

```bash
# Run tests
./mvnw test
```

## Building

```bash
# Build JAR
./mvnw clean package

# Run JAR
java -jar target/myapp-0.0.1-SNAPSHOT.jar
```
EOF

# Create .gitignore (if not already present)
cat > .gitignore <<'EOF'
target/
!.mvn/wrapper/maven-wrapper.jar
.mvn/
.idea/
*.iml
*.iws
*.ipr
.DS_Store
EOF

# Initialize git
git init
git add .
git commit -m "Initial Spring Boot project setup"
```

#### 7. Verify Setup

```bash
# Run Spring Boot application
./mvnw spring-boot:run &

# Wait for startup (takes ~10 seconds)
sleep 15

# Test endpoint
curl http://localhost:8080/
# Expected: {"message":"Hello World"}

# Run tests
./mvnw test

# Stop application
pkill -f spring-boot:run
```

**✅ Your Java + Spring Boot project is ready for /mpm-init!**

---

### Vue + Quasar

Modern Vue.js application with Quasar framework for cross-platform development.

#### 1. Install Node.js via ASDF

```bash
# Install ASDF Node.js plugin
asdf plugin add nodejs

# Install Node.js
asdf install nodejs 20.11.0

# Set global version
asdf global nodejs 20.11.0
```

#### 2. Install Quasar CLI

```bash
# Install Quasar CLI globally
npm install -g @quasar/cli
```

#### 3. Create Quasar Project

```bash
# Create project with Quasar CLI
quasar create my-quasar-app

# Follow prompts:
# - Project name: my-quasar-app
# - Project description: A sample Quasar application
# - Author: Your Name
# - CSS preprocessor: Sass with SCSS syntax (recommended)
# - Features: ESLint, TypeScript (optional)
# - Quasar components: Yes (recommended)
# - Plugins: None initially

# Navigate to project
cd my-quasar-app
```

#### 4. Set Tool Versions

```bash
# Create .tool-versions
cat > .tool-versions <<EOF
nodejs 20.11.0
EOF

# Install tools
asdf install
```

#### 5. Project Structure Overview

Quasar creates this structure automatically:

```
my-quasar-app/
├── src/
│   ├── assets/        # Static assets
│   ├── components/    # Vue components
│   ├── layouts/       # Page layouts
│   ├── pages/         # Route pages
│   ├── router/        # Vue Router configuration
│   ├── stores/        # Pinia stores (state management)
│   ├── App.vue        # Root component
│   └── index.template.html
├── public/            # Public static files
├── quasar.config.js   # Quasar configuration
├── package.json       # Dependencies and scripts
└── README.md          # Project documentation
```

#### 6. Add Sample Page

```bash
# Create a simple page
cat > src/pages/HelloPage.vue <<'EOF'
<template>
  <q-page class="flex flex-center">
    <div class="text-center">
      <h1 class="text-h2">Hello World</h1>
      <p class="text-h6">Welcome to your Quasar application</p>
      <q-btn
        color="primary"
        label="Click Me"
        @click="showNotification"
      />
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { useQuasar } from 'quasar';

const $q = useQuasar();

const showNotification = () => {
  $q.notify({
    message: 'Hello from Quasar!',
    color: 'positive',
    icon: 'check_circle'
  });
};
</script>
EOF

# Update router to include new page
cat > src/router/routes.ts <<'EOF'
import { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [
      { path: '', component: () => import('pages/HelloPage.vue') },
      { path: 'index', component: () => import('pages/IndexPage.vue') }
    ],
  },
  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue'),
  },
];

export default routes;
EOF
```

#### 7. Update README

```bash
# Create comprehensive README
cat > README.md <<'EOF'
# My Quasar App

A sample Quasar Framework application.

## Setup

Requires Node.js 20.11.0 (managed via ASDF).

```bash
# Install dependencies
npm install
```

## Development

```bash
# Start development server with hot-reload
quasar dev
```

Application runs on http://localhost:9000

## Building

```bash
# Build for production (SPA mode)
quasar build

# Build for production (PWA mode)
quasar build -m pwa

# Build for Electron
quasar build -m electron
```

## Testing

```bash
# Run unit tests (if configured)
npm test

# Run linting
npm run lint
```

## Quasar CLI Commands

```bash
# Create new component
quasar new component MyComponent

# Create new page
quasar new page MyPage

# Create new layout
quasar new layout MyLayout

# Create new store
quasar new store MyStore
```
EOF
```

#### 8. Initialize Git (if not already done)

```bash
# Quasar creates .gitignore automatically
# Just initialize git if needed
git init
git add .
git commit -m "Initial Quasar project setup"
```

#### 9. Verify Setup

```bash
# Run development server
quasar dev &

# Wait for build (takes ~10 seconds)
sleep 15

# Open in browser
open http://localhost:9000

# Stop server
pkill -f "quasar dev"
```

**✅ Your Vue + Quasar project is ready for /mpm-init!**

---

## Approach 2: MPM-Assisted Scaffolding

Let Claude MPM generate your project structure for you. This approach is ideal when:

- You're exploring a new framework
- You want best practices applied automatically
- You need a quick proof-of-concept
- You're working with unfamiliar technology stacks

### How MPM-Assisted Scaffolding Works

Instead of manually running framework commands, you provide Claude MPM with a **project specification** and let it create the structure.

### Step 1: Create Project Directory

```bash
# Create empty project directory
mkdir my-mpm-project
cd my-mpm-project

# Initialize git early
git init

# Create .tool-versions (set versions before scaffolding)
cat > .tool-versions <<EOF
python 3.11.12
nodejs 20.11.0
EOF

# Install tools
asdf install
```

### Step 2: Create Project Specification

Create a detailed specification document that describes your project:

```bash
# Create project spec
cat > PROJECT_SPEC.md <<'EOF'
# Project Specification: My FastAPI Application

## Overview
Build a REST API for managing a task list (todo application) using FastAPI and PostgreSQL.

## Technology Stack
- **Backend**: Python 3.11 + FastAPI
- **Database**: PostgreSQL 15
- **ORM**: SQLAlchemy 2.0
- **Migration**: Alembic
- **Testing**: pytest
- **Code Quality**: ruff, mypy, black

## Project Structure
```
src/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app entry point
│   ├── config.py         # Configuration management
│   ├── database.py       # Database connection
│   ├── models/           # SQLAlchemy models
│   │   ├── __init__.py
│   │   └── task.py
│   ├── schemas/          # Pydantic schemas
│   │   ├── __init__.py
│   │   └── task.py
│   ├── routers/          # API routes
│   │   ├── __init__.py
│   │   └── tasks.py
│   └── services/         # Business logic
│       ├── __init__.py
│       └── task_service.py
tests/
├── __init__.py
├── conftest.py
├── test_tasks.py
└── test_database.py
alembic/                  # Database migrations
docs/                     # Documentation
```

## API Endpoints

### Tasks
- `GET /tasks` - List all tasks
- `GET /tasks/{id}` - Get specific task
- `POST /tasks` - Create new task
- `PUT /tasks/{id}` - Update task
- `DELETE /tasks/{id}` - Delete task

## Data Models

### Task Model
- id: UUID (primary key)
- title: String (required, max 200 chars)
- description: Text (optional)
- completed: Boolean (default: false)
- created_at: DateTime (auto)
- updated_at: DateTime (auto)

## Development Requirements
- Use environment variables for configuration (.env file)
- Implement database connection pooling
- Add API documentation via FastAPI's auto-generated OpenAPI
- Include Docker Compose for local PostgreSQL
- Write comprehensive tests with >80% coverage
- Type hints on all functions
- Docstrings following Google style

## Build and Run
- `uv sync` - Install dependencies
- `docker-compose up -d` - Start PostgreSQL
- `alembic upgrade head` - Run migrations
- `uvicorn src.app.main:app --reload` - Start server

## Quality Checks
- `ruff check .` - Linting
- `mypy src/` - Type checking
- `pytest` - Run tests
- `pytest --cov=src` - Run with coverage

## Deployment
- Target: Docker container
- Health check endpoint: `/health`
- Database: PostgreSQL (managed instance)
EOF
```

### Step 3: Ask MPM to Generate Structure

Open Claude Code and use this prompt:

```
I need you to scaffold a complete FastAPI project based on the specification
in PROJECT_SPEC.md. Please:

1. Read PROJECT_SPEC.md to understand requirements
2. Create all directories and files as specified
3. Implement:
   - Complete database models with SQLAlchemy
   - Pydantic schemas for request/response validation
   - API routers with full CRUD operations
   - Database connection and session management
   - Alembic configuration for migrations
   - Docker Compose setup for PostgreSQL
   - Comprehensive pytest test suite
   - Configuration management with Pydantic Settings
   - .env.example file with all required variables

4. Create supporting files:
   - pyproject.toml with all dependencies
   - README.md with setup and usage instructions
   - .gitignore appropriate for Python projects
   - Makefile with common commands
   - docker-compose.yml for local development

5. Ensure:
   - All code has type hints
   - All functions have docstrings
   - Tests are comprehensive
   - Code follows best practices
   - Configuration is environment-based

Please scaffold the complete project structure now.
```

### Step 4: Review Generated Code

MPM will create all files. Review carefully:

```bash
# Check structure
tree -L 3

# Review key files
cat pyproject.toml
cat src/app/main.py
cat README.md

# Check configuration
cat .env.example
cat docker-compose.yml
```

### Step 5: Verify and Test

```bash
# Install dependencies
uv sync

# Start database
docker-compose up -d

# Run migrations
uv run alembic upgrade head

# Run tests
uv run pytest

# Start server
uv run uvicorn src.app.main:app --reload
```

### MPM Scaffolding Best Practices

#### Be Specific in Your Spec

**❌ Too Vague:**
```markdown
Create a web application with a database.
```

**✅ Specific and Clear:**
```markdown
Create a FastAPI REST API with:
- PostgreSQL database via SQLAlchemy
- CRUD endpoints for Task model
- JWT authentication
- Docker Compose for local development
- Pytest test suite with >80% coverage
```

#### Include Technology Versions

```markdown
## Technology Stack
- Python: 3.11.12 (via .tool-versions)
- FastAPI: ^0.104.0
- SQLAlchemy: ^2.0.0
- PostgreSQL: 15 (Docker)
```

#### Specify Directory Structure

```markdown
## Project Structure
```
src/app/
├── api/          # API routes
├── core/         # Core functionality
├── db/           # Database
└── models/       # Data models
```
```

#### Define Conventions

```markdown
## Code Conventions
- Use Google-style docstrings
- Type hints on all functions
- snake_case for variables and functions
- PascalCase for classes
- Maximum line length: 100 characters
```

#### Request Tests and Documentation

```markdown
## Testing Requirements
- pytest with pytest-asyncio
- Minimum 80% code coverage
- Unit tests for all services
- Integration tests for API endpoints
- Test fixtures in conftest.py

## Documentation Requirements
- README with setup instructions
- API documentation via OpenAPI
- Docstrings on all public functions
- CONTRIBUTING.md for developers
```

### Example Specifications

#### Minimal Spec (Python + FastAPI)

```markdown
# Project: Simple API

## Stack
- Python 3.11 + FastAPI
- SQLite database
- pytest for testing

## Features
- Single /items endpoint with GET/POST
- Basic CRUD operations
- Auto-generated API docs

## Structure
Standard FastAPI layout with tests/
```

#### Comprehensive Spec (Full Stack)

```markdown
# Project: E-Commerce Platform

## Stack
- Backend: Python 3.11 + FastAPI
- Frontend: Vue 3 + TypeScript + Quasar
- Database: PostgreSQL 15
- Cache: Redis 7
- Search: Elasticsearch 8

## Architecture
- Monorepo with backend/ and frontend/
- Shared types via OpenAPI generation
- Microservices: auth, catalog, orders, payments

## Features
[Detailed feature list...]

## Database Schema
[Complete schema definition...]

## API Specification
[Full API contract...]

## Deployment
- Docker Compose for local development
- Kubernetes manifests for production
- CI/CD via GitHub Actions
```

### When to Use MPM-Assisted Scaffolding

**✅ Use MPM Scaffolding When:**
- Learning a new framework or stack
- Need a working example quickly
- Want best practices applied automatically
- Prototyping or proof-of-concept
- Standardizing project structure across team

**❌ Use Manual Scaffolding When:**
- You need precise control over every detail
- Framework has specific initialization requirements
- You're an expert and know exact setup needed
- Company has strict scaffolding standards
- Project will be production-critical from day one

---

## ASDF Tool Version Management

**Always set tool versions before scaffolding!**

### Why ASDF Matters

ASDF ensures everyone on your team uses identical tool versions, eliminating "works on my machine" issues.

### Quick Setup

```bash
# 1. Create .tool-versions in project root
cat > .tool-versions <<EOF
python 3.11.12
nodejs 20.11.0
java openjdk-21.0.1
EOF

# 2. Install specified versions
asdf install

# 3. Verify versions
python --version   # 3.11.12
node --version     # v20.11.0
java --version     # openjdk 21.0.1
```

### Technology-Specific Versions

#### Python Projects
```
python 3.11.12
uv 0.9.17
```

#### Node.js Projects
```
nodejs 20.11.0
```

#### Java Projects
```
java openjdk-21.0.1
maven 3.9.6
```

#### Full Stack Projects
```
python 3.11.12
nodejs 20.11.0
uv 0.9.17
```

### Integration with Scaffolding

**Manual Scaffolding:**
1. Create `.tool-versions` first
2. Run `asdf install`
3. Then run framework initialization (uv init, npm init, etc.)

**MPM-Assisted Scaffolding:**
1. Create `.tool-versions` first
2. Run `asdf install`
3. Ask MPM to scaffold project
4. MPM uses installed tool versions automatically

**See [ASDF Guide](asdf-tool-versions.md) for complete ASDF documentation.**

---

## Running /mpm-init

After bootstrapping your project (manually or via MPM), initialize MPM integration.

### Prerequisites Checklist

Before running `/mpm-init`, ensure:

- ✅ **Project directory exists** with source code
- ✅ **Build system configured** (package.json, pyproject.toml, pom.xml, etc.)
- ✅ **Tool versions set** via `.tool-versions`
- ✅ **Git initialized** with initial commit
- ✅ **README created** with basic project info
- ✅ **Dependencies installable** (can run build commands)

### Basic /mpm-init Usage

```bash
# Navigate to your project root
cd my-project

# Run MPM initialization
/mpm-init
```

MPM will:
1. Analyze your project structure
2. Detect technology stack
3. Extract build commands and workflows
4. Generate intelligent CLAUDE.md documentation
5. Set up agent templates
6. Create project memory system

### First-Time Setup

On first run, MPM creates:

```
my-project/
├── CLAUDE.md              # AI instructions
├── .claude-mpm/           # MPM configuration directory
│   ├── config.json
│   ├── agents/            # Agent templates
│   ├── memory/            # Project memory
│   └── workflows/         # Common workflows
└── .tool-versions         # ASDF tool versions (you created)
```

### Verify MPM Setup

```bash
# Check CLAUDE.md was created
cat CLAUDE.md

# Verify MPM configuration
ls -la .claude-mpm/

# Test MPM commands
claude-mpm status
```

### Re-Running /mpm-init

**Your project evolves** - re-run `/mpm-init` to keep documentation current:

```bash
# Update MPM documentation with recent changes
/mpm-init update

# Full re-initialization
/mpm-init
```

**See [Re-Running /mpm-init Guide](mpm-init-rerun-guide.md) for complete details.**

---

## Best Practices

### 1. Version Control Everything

```bash
# Commit immediately after scaffolding
git add .
git commit -m "Initial project scaffold"

# Commit after /mpm-init
git add .
git commit -m "Initialize Claude MPM integration"
```

### 2. Document Your Setup

Update README.md with setup instructions:

```markdown
## Setup

1. **Install ASDF and tools**:
   ```bash
   asdf install
   ```

2. **Install dependencies**:
   ```bash
   uv sync  # Python
   npm install  # Node.js
   ./mvnw install  # Java
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

4. **Run application**:
   ```bash
   # See specific commands below
   ```
```

### 3. Test Before Committing

```bash
# Always verify your scaffold works
# Python
uv run pytest

# Node.js
npm test

# Java
./mvnw test

# Vue/Quasar
npm run lint
```

### 4. Use .env for Configuration

Never commit secrets:

```bash
# Create .env.example with safe defaults
cat > .env.example <<EOF
DATABASE_URL=postgresql://localhost/myapp
API_KEY=your-api-key-here
DEBUG=true
EOF

# Add .env to .gitignore
echo ".env" >> .gitignore

# Users copy and customize
cp .env.example .env
```

### 5. Standardize Tool Versions

**Team consistency:**
```bash
# Same .tool-versions for all developers
cat > .tool-versions <<EOF
python 3.11.12
nodejs 20.11.0
EOF

# Commit to repository
git add .tool-versions
git commit -m "Set standard tool versions via ASDF"
```

### 6. Create Makefile for Common Tasks

```bash
# Create Makefile
cat > Makefile <<'EOF'
.PHONY: install test dev build clean

install:
	asdf install
	uv sync

test:
	uv run pytest

dev:
	uvicorn src.app.main:app --reload

build:
	uv build

clean:
	rm -rf dist/ build/ .pytest_cache/
EOF
```

### 7. Document Architecture Decisions

```bash
# Create architecture decision record
mkdir -p docs/architecture
cat > docs/architecture/ADR-001-tech-stack.md <<EOF
# ADR-001: Technology Stack Selection

## Status
Accepted

## Context
Need to choose technology stack for new API project.

## Decision
Use Python 3.11 + FastAPI for:
- Modern async support
- Automatic API documentation
- Type safety with Pydantic
- High performance

## Consequences
- Team needs Python 3.11+
- Learning curve for async/await
- Great ecosystem and tooling
EOF
```

---

## Troubleshooting

### Tool Version Issues

**Problem:** `python: command not found` after `asdf install`

**Solution:**
```bash
# Ensure ASDF is sourced in shell
echo '. $(brew --prefix asdf)/libexec/asdf.sh' >> ~/.zshrc
source ~/.zshrc

# Re-install
asdf install
```

**Problem:** Wrong tool version being used

**Solution:**
```bash
# Check what version is active
asdf current

# Verify .tool-versions exists
cat .tool-versions

# Re-install if needed
asdf install python 3.11.12
```

### Dependency Installation Fails

**Python (uv):**
```bash
# Clear cache and retry
uv cache clean
uv sync

# Check Python version
python --version

# Ensure uv is updated
asdf install uv latest
```

**Node.js (npm):**
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

**Java (Maven):**
```bash
# Clear Maven cache
./mvnw dependency:purge-local-repository

# Reinstall
./mvnw clean install
```

### /mpm-init Doesn't Detect Framework

**Problem:** MPM can't determine project type

**Solution:**
```bash
# Ensure you have framework-specific files
# Python: pyproject.toml or setup.py
# Node.js: package.json
# Java: pom.xml or build.gradle
# Vue: quasar.config.js

# Add README.md with project description
cat > README.md <<EOF
# My Project

A FastAPI application for task management.
EOF

# Re-run /mpm-init
/mpm-init
```

### MPM-Scaffolded Code Has Errors

**Problem:** MPM-generated code doesn't work

**Solution:**
```bash
# 1. Review PROJECT_SPEC.md - was it specific enough?
cat PROJECT_SPEC.md

# 2. Check for missing dependencies
uv sync  # or npm install, etc.

# 3. Test incrementally
uv run pytest tests/test_basic.py

# 4. Ask MPM to fix specific issues
# "The database connection in src/app/database.py fails.
#  Please review and fix the connection pooling configuration."

# 5. Manual fixes are okay - commit after verification
git add .
git commit -m "Fix database connection configuration"
```

### Project Structure Doesn't Match Expectations

**Problem:** MPM scaffolded different structure than wanted

**Solution:**
```bash
# 1. Be more explicit in PROJECT_SPEC.md
cat >> PROJECT_SPEC.md <<EOF

## Exact Directory Structure Required
```
src/
  api/
    v1/
      endpoints/
        tasks.py
        users.py
    deps.py
  core/
    config.py
    security.py
```
EOF

# 2. Re-scaffold or manually adjust
# 3. Use manual scaffolding if you need exact control
```

---

## Summary

### Quick Reference

**Manual Scaffolding:**
1. Set `.tool-versions` → 2. Run `asdf install` → 3. Initialize framework → 4. Create structure → 5. Run `/mpm-init`

**MPM-Assisted Scaffolding:**
1. Set `.tool-versions` → 2. Run `asdf install` → 3. Write `PROJECT_SPEC.md` → 4. Ask MPM to scaffold → 5. Run `/mpm-init`

### Next Steps

After bootstrapping and running `/mpm-init`:

1. **Verify setup** - Run tests, start development server
2. **Commit changes** - Git commit all scaffolding work
3. **Review CLAUDE.md** - Ensure AI instructions are accurate
4. **Start development** - Begin building features
5. **Re-run /mpm-init periodically** - Keep documentation fresh

### Related Documentation

- [ASDF Tool Versions Guide](asdf-tool-versions.md) - Complete ASDF documentation
- [Re-Running /mpm-init Guide](mpm-init-rerun-guide.md) - Keep documentation current
- [Installation Guide](../getting-started/installation.md) - MPM installation
- [Quick Start](../getting-started/quick-start.md) - Get started with MPM

---

**Ready to bootstrap your project? Choose your approach and get started!**
