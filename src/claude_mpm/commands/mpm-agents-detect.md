# Detect project toolchain and frameworks

Scan your project to detect programming languages, frameworks, tools, and configurations.

## Usage

```
/mpm-agents-detect
```

## Description

This command scans your project directory to automatically detect:
- Programming languages and their versions
- Web frameworks and libraries
- Testing tools and frameworks
- Build tools and bundlers
- Package managers
- Deployment configurations

This is useful for understanding what Claude MPM can detect in your project before running auto-configuration.

## Implementation

When you run `/mpm-agents-detect`, the PM will execute:
```bash
claude-mpm agents detect
```

This performs a comprehensive scan of your project looking for:
- Package manifests (package.json, requirements.txt, Cargo.toml, go.mod, pom.xml)
- Framework-specific files (next.config.js, fastapi imports, etc.)
- Test configurations (pytest.ini, jest.config.js, playwright.config.ts)
- Build configurations (vite.config.js, webpack.config.js, tsconfig.json)
- Deployment files (Dockerfile, vercel.json, railway.json)

## Expected Output

```
🔍 Project Toolchain Detection
================================

Languages:
  ✓ Python 3.11.5
  ✓ Node.js 20.10.0
  ✓ TypeScript 5.3.2

Frameworks:
  ✓ FastAPI 0.104.0
  ✓ React 18.2.0
  ✓ Next.js 14.0.4

Testing:
  ✓ pytest 7.4.3
  ✓ Jest 29.7.0
  ✓ Playwright 1.40.0

Build Tools:
  ✓ Vite 5.0.0
  ✓ TypeScript Compiler

Package Managers:
  ✓ poetry (Python)
  ✓ npm (Node.js)

Deployment:
  ✓ Docker (Dockerfile found)
  ✓ Vercel (vercel.json found)
  ✓ PM2 (ecosystem.config.js found)

Configuration Files Detected:
  - pyproject.toml
  - package.json
  - tsconfig.json
  - next.config.js
  - pytest.ini
  - jest.config.js
  - playwright.config.ts
  - Dockerfile
  - vercel.json

Summary:
  Full-stack project with Python backend (FastAPI) and
  React/Next.js frontend, comprehensive testing setup,
  and multiple deployment targets.
```

## What Gets Detected

### Language Detection
- **Python**: Looks for .py files, requirements.txt, pyproject.toml, setup.py
- **JavaScript/TypeScript**: Looks for .js/.ts files, package.json, tsconfig.json
- **Rust**: Looks for Cargo.toml, .rs files
- **Go**: Looks for go.mod, .go files
- **Java**: Looks for pom.xml, build.gradle, .java files

### Framework Detection
**Python:**
- FastAPI (imports, decorator patterns)
- Flask (imports, app patterns)
- Django (settings.py, manage.py)

**JavaScript/TypeScript:**
- Next.js (next.config.js, pages/ or app/ directory)
- React (package.json dependencies, JSX usage)
- Vue (vue.config.js, .vue files)
- Express (imports, app patterns)
- Nest.js (nest-cli.json, decorators)

### Testing Detection
- pytest (pytest.ini, conftest.py)
- unittest (test_*.py patterns)
- Jest (jest.config.js)
- Vitest (vitest.config.js)
- Playwright (playwright.config.ts)
- Cypress (cypress.json)

### Build Tool Detection
- Vite (vite.config.js/ts)
- Webpack (webpack.config.js)
- Rollup (rollup.config.js)
- esbuild (esbuild configuration)
- Turbopack (next.config.js with turbopack)

### Deployment Detection
- Docker (Dockerfile, docker-compose.yml)
- Vercel (vercel.json, .vercel directory)
- Railway (railway.json, railway.toml)
- PM2 (ecosystem.config.js)
- Kubernetes (k8s/, kubernetes/ directories)

## Use Cases

1. **Before Auto-Configuration**: Run this to see what will be detected
2. **Troubleshooting**: Verify that your project setup is being recognized correctly
3. **Documentation**: Generate a summary of your project's tech stack
4. **Planning**: Understand what agents might be recommended

## Tips

1. **Run from project root**: Detection works best from your project's root directory
2. **Check detection accuracy**: Verify detected versions match your actual setup
3. **Missing detections**: If something isn't detected, you can still deploy agents manually
4. **Configuration files**: Detection relies on standard configuration files being present

## Common Issues

**Nothing detected?**
- Make sure you're in the project root directory
- Check that you have standard configuration files (package.json, requirements.txt, etc.)
- Some projects may need manual agent deployment

**Wrong versions detected?**
- Detection shows what's configured in manifest files
- Actual runtime versions may differ
- This doesn't affect agent functionality

**Framework not detected?**
- Some frameworks are harder to detect automatically
- You can still use auto-configure and manually select agents
- Or deploy specific agents manually with `/mpm-agents deploy <name>`

## Related Commands

- `/mpm-agents-recommend` - See agent recommendations based on detection
- `/mpm-auto-configure` - Automatically configure agents based on detection
- `/mpm-agents` - Manually manage agents
- `/mpm-help auto-configure` - Learn about auto-configuration
