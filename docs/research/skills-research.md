# The Definitive Guide to Open Source Claude Code Skills Libraries

## Executive Overview

Claude Skills are modular capabilities that extend Claude's functionality through specialized instruction sets, scripts, and resources. They use progressive disclosure architecture (~100 tokens for metadata, <5k tokens when activated) to maintain efficiency while providing expert-level capabilities. The ecosystem includes **official Anthropic resources**, **200+ MCP servers**, **dozens of comprehensive community collections**, and **hundreds of individual skills** covering coding, toolchains, languages, and operations.

**All resources documented here are freely available as open source content**, primarily under MIT or Apache 2.0 licenses.

---

## Official Anthropic Resources

### anthropics/skills - The Official Repository
**Primary hub for Claude Skills with production-grade implementations**

**URL:** https://github.com/anthropics/skills  
**License:** Apache 2.0 (example skills); Source-available (document skills)  
**Stars:** ~17,900+ | **Status:** ✅ Actively maintained by Anthropic

**Example Skills (Apache 2.0):**
- **algorithmic-art** - Generate p5.js art with seeded randomness, flow fields, particle systems
- **canvas-design** - Design visual art in PNG and PDF formats using design philosophies
- **artifacts-builder** - Build complex HTML artifacts using React, Tailwind CSS, shadcn/ui
- **mcp-server** - Guide for creating high-quality MCP servers for API integration
- **webapp-testing** - Test local applications using Playwright for UI verification
- **brand-guidelines** - Apply Anthropic's official brand colors and typography
- **skill-creator** - Interactive tool that guides you through building new skills
- **template-skill** - Basic template to use as starting point for new skills

**Document Skills (Source-Available, Pre-included with Claude):**
- **docx** - Create, edit, analyze Word documents with tracked changes and formatting preservation
- **pdf** - Comprehensive PDF manipulation toolkit for extraction, creation, merging, splitting
- **pptx** - Create, edit, analyze PowerPoint presentations with layouts, charts, templates
- **xlsx** - Create, edit, analyze Excel spreadsheets with formulas, formatting, data analysis

**Installation:** `/plugin marketplace add anthropics/skills`

### anthropics/mcpb - MCP Bundles
**One-click installation of MCP servers for desktop applications**

**URL:** https://github.com/anthropics/mcpb  
**License:** MIT | **Status:** ✅ Actively maintained

**Capabilities:** Simplified distribution and installation of local MCP servers with automatic updates, easy configuration, and curated directory integration. Supports Node.js, Python, and binary bundles.

**Installation:** `npm install -g @anthropic-ai/mcpb`

### Model Context Protocol (MCP) - Official Organization
**Open protocol enabling seamless integration between LLMs and external data sources**

**Organization:** https://github.com/modelcontextprotocol  
**Managed by:** Anthropic, PBC  
**Documentation:** https://modelcontextprotocol.io

**Official SDKs (All MIT License):**
- TypeScript SDK: https://github.com/modelcontextprotocol/typescript-sdk
- Python SDK: https://github.com/modelcontextprotocol/python-sdk
- C# SDK: https://github.com/modelcontextprotocol/csharp-sdk (with Microsoft)
- Go SDK: https://github.com/modelcontextprotocol/go-sdk (with Google)
- Java SDK: https://github.com/modelcontextprotocol/java-sdk
- Kotlin SDK: https://github.com/modelcontextprotocol/kotlin-sdk (with JetBrains)
- PHP, Ruby, Rust, Swift SDKs also available

**Official MCP Servers:** https://github.com/modelcontextprotocol/servers
- **filesystem** - Secure file operations with configurable access controls
- **git** - Repository operations, searching, analyzing commits
- **fetch** - Web content fetching and conversion for efficient LLM usage
- **memory** - Knowledge graph-based persistent memory system
- **sequential-thinking** - Dynamic problem-solving through thought sequences

**MCP Registry:** https://github.com/modelcontextprotocol/registry  
**Browse servers:** https://registry.modelcontextprotocol.io

---

## Community Collections and Curated Lists

### travisvn/awesome-claude-skills
**Most comprehensive guide with detailed documentation and comparison matrices**

**URL:** https://github.com/travisvn/awesome-claude-skills  
**Stars:** ~2,000+ | **License:** Apache 2.0  
**Last Updated:** November 2025 | **Status:** ✅ Active

**Features:**
- Comprehensive curated list of official and community skills
- Extensive Skills vs MCP vs System Prompts comparison
- Security guidelines and best practices
- FAQ and troubleshooting guide
- Progressive disclosure architecture explained
- Community verification system

### BehiSecc/awesome-claude-skills
**Well-organized categorized collection with practical focus**

**URL:** https://github.com/BehiSecc/awesome-claude-skills  
**Stars:** ~3,800+ | **License:** Open source  
**Last Updated:** 2025 | **Status:** ✅ Active

**Categories:**
- Document Skills (docx, pdf, pptx, xlsx)
- Development & Code Tools (TDD, git-worktrees, AWS, pypict testing)
- Data & Analysis (CSV analysis, root-cause-tracing)
- Scientific & Research Tools (26 databases, 58 packages including PubMed, PubChem, UniProt, ChEMBL, AlphaFold)
- Writing & Research (article extraction, brainstorming)
- Media & Content (YouTube transcripts, EPUB, image enhancer)
- Security & Web Testing (ffuf, webapp-testing, systematic debugging)
- Utility & Automation (file organizer, invoice organizer)

### ComposioHQ/awesome-claude-skills
**Production-focused collection emphasizing real-world productivity**

**URL:** https://github.com/ComposioHQ/awesome-claude-skills  
**License:** Apache 2.0 | **Status:** ✅ Active

**Highlights:**
- Official document skills integration
- Business & marketing skills (competitive ads, domain brainstormer, lead research)
- Security & forensics (computer forensics, threat hunting with Sigma rules, metadata extraction)
- Integration with Composio platform (500+ apps)
- Skills API documentation and examples

### obra/superpowers
**Battle-tested skills library with systematic development workflows**

**URL:** https://github.com/obra/superpowers  
**License:** MIT | **Last Updated:** October 2025 | **Status:** ✅ Active

**Core Skills:**
- **Testing:** test-driven-development, condition-based-waiting, testing-anti-patterns
- **Debugging:** systematic-debugging, root-cause-tracing, verification-before-completion, defense-in-depth
- **Collaboration:** brainstorming, writing-plans, executing-plans, dispatching-parallel-agents
- **Development:** using-git-worktrees, finishing-a-development-branch, subagent-driven-development
- **Meta:** writing-skills, sharing-skills, testing-skills-with-subagents

**Custom Slash Commands:** /superpowers:brainstorm, /superpowers:write-plan, /superpowers:execute-plan

**Installation:** `/plugin marketplace add obra/superpowers-marketplace`  
**Companion:** https://github.com/obra/superpowers-lab (experimental skills)

### alirezarezvani/claude-skills
**Production-ready skill packages with comprehensive Python CLI tools**

**URL:** https://github.com/alirezarezvani/claude-skills  
**License:** MIT | **Last Updated:** November 2025 | **Status:** ✅ Active

**42 Production Skills Including:**

**Marketing (3 skills):**
- content-creator: Brand voice analyzer, SEO optimizer, social media frameworks
- marketing-demand-acquisition: CAC calculator, full-funnel strategy
- marketing-strategy-pmm: Positioning, GTM strategy, competitive intelligence

**Executive Advisory (2 skills):**
- ceo-advisor: Strategy analyzer, financial scenario modeling, board governance
- cto-advisor: Tech debt analyzer, team scaling calculator, architecture decisions

**Product Team (5 skills):**
- product-manager-toolkit: RICE prioritizer, customer interview analyzer, PRD templates
- agile-product-owner: User story generator, sprint planner
- ux-researcher-designer: Persona generator, journey mapper

**Engineering Team - Core (9 skills):**
- Software Architect, Frontend Engineer, Backend Engineer, Fullstack Engineer
- QA Testing Engineer, DevOps Engineer, SecOps Engineer, Code Reviewer, Security Engineer

**Engineering Team - AI/ML/Data (5 skills):**
- Data Scientist, Data Engineer, ML/AI Engineer, Prompt Engineer, Computer Vision Engineer

**Regulatory Affairs & Quality (12 skills):**
- Quality Manager, QMS ISO 13485 Specialist, CAPA Officer, Documentation Manager
- Risk Management Specialist, Information Security Manager, MDR/FDA Specialists

**Features:**
- 97+ Python CLI analysis tools included
- Documented ROI: 40%+ time savings, 30%+ quality improvements
- Estimated value: $1.7M+/month per organization

**Related:** https://github.com/alirezarezvani/claude-code-skill-factory (generation toolkit)

### Additional Community Collections

**abubakarsiddik31/claude-skills-collection**  
**URL:** https://github.com/abubakarsiddik31/claude-skills-collection  
Table-based organization with categorized links to all major skills

**metaskills/skill-builder**  
**URL:** https://github.com/metaskills/skill-builder  
**Author:** Ken Collins (AWS Serverless Hero)  
Claude Code Agent Skills Builder - meta-skill for creating, editing, converting skills

**SkillsMP.com - Discovery Platform**  
**URL:** https://skillsmp.com  
Searchable marketplace of 13,000+ Claude Code skills from GitHub with installation commands

---

## CODING SKILLS: Development Workflows

### Code Generation and Refactoring

**artifacts-builder** (Official Anthropic)  
**URL:** https://github.com/anthropics/skills/tree/main/artifacts-builder  
Build complex HTML artifacts using React, Tailwind CSS, shadcn/ui components for claude.ai

**Code Refactoring Skill**  
**URL:** https://claude-plugins.dev/skills/@dasien/RemoteCredentialRequestPOC/code-refactoring  
Improve code structure and readability without changing external behavior

**subagent-driven-development** (obra/superpowers)  
Dispatches independent subagents for individual tasks with code review checkpoints for rapid, controlled development

**using-git-worktrees** (obra/superpowers)  
Creates isolated git worktrees with smart directory selection for parallel development branches

### Testing Frameworks and Test Generation

**test-driven-development** (obra/superpowers)  
**URL:** https://github.com/obra/superpowers/tree/main/skills/test-driven-development  
RED-GREEN-REFACTOR cycle enforcement. Mandatory use before implementation code for any feature/bugfix

**webapp-testing** (Official Anthropic)  
**URL:** https://github.com/anthropics/skills/tree/main/webapp-testing  
Test local web applications using Playwright for UI verification, screenshot capture, debugging

**playwright-skill** (Community Enhanced)  
**URL:** https://github.com/lackeyjb/playwright-skill  
**License:** MIT | Model-invoked Playwright automation where Claude writes custom automation code on-the-fly. Zero module resolution errors, visible browser by default, safe cleanup.

**pypict-claude-skill**  
**URL:** https://github.com/omkamal/pypict-claude-skill  
Design comprehensive test cases using PICT (Pairwise Independent Combinatorial Testing) for optimized test suites with pairwise coverage

**test-fixing**  
**URL:** https://github.com/mhattingpete/claude-skills-marketplace/tree/main/engineering-workflow-plugin/skills/test-fixing  
Detect failing tests and propose patches with systematic error grouping strategies

**defense-in-depth** (obra/superpowers)  
Implement multi-layered testing and security best practices with comprehensive validation coverage

### Linting and Code Quality

**clj-kondo**  
**URL:** https://claude-plugins.dev/skills/@hugoduncan/library-skills/clj-kondo  
Comprehensive guide to using clj-kondo for Clojure code linting with configuration management, custom hooks, CI/CD integration

**move-code-quality-skill**  
**URL:** https://github.com/1NickPappas/move-code-quality-skill  
Analyzes Move language packages against official Move Book Code Quality Checklist for Move 2024 Edition compliance

**cclint - Claude Code Linter**  
**URL:** https://github.com/carlrannaberg/cclint  
Comprehensive linting tool for Claude Code projects with agent/subagent linting, command validation, settings validation, documentation linting, multiple output formats (Console, JSON, Markdown), CI/CD friendly

### Debugging and Error Analysis

**systematic-debugging** (obra/superpowers)  
**URL:** https://github.com/obra/superpowers/tree/main/skills/systematic-debugging  
Four-phase debugging framework ensuring root cause investigation before fixes: (1) Information gathering, (2) Hypothesis formation, (3) Hypothesis testing, (4) Fix implementation. Evidence-based debugging over ad-hoc approaches.

**root-cause-tracing** (obra/superpowers)  
Use when errors occur deep in execution to trace back to the original trigger across components

**verification-before-completion** (obra/superpowers)  
Ensure issues are actually fixed before claiming completion with mandatory evidence validation

### Documentation Generation

**skill-creator** (Official Anthropic)  
**URL:** https://github.com/anthropics/skills/tree/main/skill-creator  
Interactive skill creation tool with guided Q&A, template generation, best practices enforcement

**claude-auto-documenter-v2**  
**URL:** https://github.com/Puneet8800/claude-auto-documenter-v2  
Production-ready MCP server for automatic documentation generation with task completion detection, file system watcher, real-time updates

### API Integration and Development

**mcp-builder / mcp-server** (Official Anthropic)  
**URL:** https://github.com/anthropics/skills/tree/main/mcp-server  
Guide for creating high-quality MCP servers to integrate external APIs and services with best practices

**aws-skills**  
**URL:** https://github.com/zxkane/aws-skills  
**License:** MIT | AWS development with CDK best practices, cost optimization MCP servers, serverless architecture patterns, event-driven architecture

### Data Processing and Transformation

**csv-data-summarizer-claude-skill**  
**URL:** https://github.com/coffeefuelbump/csv-data-summarizer-claude-skill  
Automatically analyzes CSV files with column analysis, distribution analysis, missing data detection, correlation identification

**scientific-packages**  
**URL:** https://github.com/K-Dense-AI/claude-scientific-skills/tree/main/scientific-packages  
58 specialized Python packages for bioinformatics, cheminformatics, machine learning, data analysis

**scientific-databases**  
**URL:** https://github.com/K-Dense-AI/claude-scientific-skills/tree/main/scientific-databases  
Access to 26 scientific databases including PubMed, PubChem, UniProt, ChEMBL, AlphaFold DB

**article-extractor**  
**URL:** https://github.com/michalparkola/tapestry-skills-for-claude-code/tree/main/article-extractor  
Extract full article text and metadata from web pages with text extraction, metadata parsing, web scraping

---

## TOOLCHAIN SKILLS: Build Tools, Package Managers, Development Environments

### Version Control and Code Repository

**GitHub Official MCP Server**  
**URL:** https://github.com/github/github-mcp-server  
**License:** MIT | **Status:** ⭐⭐⭐⭐⭐ Official GitHub implementation

**Capabilities:**
- Repository management: Browse code, search files, analyze commits, project structure
- Issue & PR automation: Create, update, manage issues and pull requests
- CI/CD intelligence: Monitor GitHub Actions, analyze build failures, manage releases
- Code security: Code scanning alerts, Dependabot integration, secret scanning
- Team collaboration: Discussions, notifications, team activity

**Toolsets:** Context, Actions, Code Security, Dependabot, Discussions, Gists, Git, Issues, Labels, Notifications, Organizations, Projects, Pull Requests, Repositories, Secret Protection, Security Advisories, Stargazers, Users

**GitLab Server**  
**URL:** https://github.com/modelcontextprotocol/servers/tree/main/src/gitlab  
**License:** MIT | GitLab platform integration for project management and CI/CD operations

**Git MCP Server (Community - Enhanced)**  
**URL:** https://github.com/cyanheads/git-mcp-server  
Comprehensive Git operations: clone, commit, branch, diff, log, status, push, pull, merge, rebase, worktree management, tag management, GPG/SSH commit signing

**GitMCP - Repository Documentation**  
**URL:** https://gitmcp.io | https://github.com/idosal/git-mcp  
Automatically creates MCP server for ANY GitHub repository. Simply change `github.com` to `gitmcp.io` in any repo URL for instant documentation access

### Package Managers

**NPM/Node.js Package Management**  
Multiple MCP servers provide npm integration for registry access, package search, dependency management

**NuGet Server** (Microsoft)  
**URL:** Part of https://github.com/microsoft/mcp  
NuGet package management, search, installation for .NET ecosystem

**Maven Tools MCP**  
**URL:** https://github.com/arvindand/maven-tools-mcp  
Maven Central dependency intelligence for JVM build tools (Maven, Gradle, SBT, Mill) with Context7 documentation support

**Homebrew Server** (Official)  
**URL:** https://docs.brew.sh/MCP-Server  
Run Homebrew commands locally for macOS/Linux package management

### Build and Development Environment Tools

**Nx Server** (Official)  
**URL:** https://github.com/nrwl/nx-console/blob/master/apps/nx-mcp  
Nx workspace understanding, project relationships, runnable tasks for monorepo management and build orchestration

**Next.js Devtools**  
Next.js development tools for AI coding assistants providing project management capabilities

**VS Code Devtools - BifrostMCP**  
**URL:** https://github.com/biegehydra/BifrostMCP  
Connect to VS Code IDE with semantic tools like find_usages for IDE integration and code navigation

**E2B Server** (Official)  
**URL:** https://github.com/e2b-dev/mcp-server  
Secure cloud sandboxes for code execution providing safe testing environments

**RchGrav/claudebox**  
**URL:** https://github.com/RchGrav/claudebox  
**License:** MIT | Ultimate Claude Code Docker Development Environment with containerized setup, development profiles for C/C++, Python, Rust, Go, per-project isolation, persistent configuration

**VishalJ99/claude-docker**  
**URL:** https://github.com/VishalJ99/claude-docker  
Docker container for running Claude Code with full permissions, pre-configured MCP servers, persistent conversation history, security isolation

**Docker MCP Toolkit** (Official Docker)  
**URL:** https://www.docker.com/blog/connect-mcp-servers-to-claude-desktop-with-mcp-toolkit  
Bridges Claude with Docker's trusted developer workflow - secure containerized MCP server execution, GitHub integration, Kubernetes management, complete isolation with containers torn down after use

---

## PROGRAMMING LANGUAGE SKILLS

### Python-Specific Skills

**hoelzro/dotfiles - python-style**  
**URL:** https://claude-plugins.dev/skills/@hoelzro/dotfiles/python-style  
Python coding conventions and best practices including using `uv run` to execute scripts with temporary dependencies

**google-adk-python** (via mrgoonie/claudekit-skills)  
**URL:** https://github.com/mrgoonie/claudekit-skills  
Google's Agent Development Kit for building AI agents with tool integration, multi-agent orchestration, workflow patterns (sequential, parallel, loop), deployment to Vertex AI

**alirezarezvani/claude-skills - Python Tools**  
97+ Python CLI analysis tools including Brand Voice Analyzer, SEO Optimizer, CAC Calculator, Tech Debt Analyzer, Team Scaling Calculator, RICE Prioritizer, Customer Interview Analyzer

### TypeScript/JavaScript Skills

**Nice-Wolf-Studio/claude-skills-threejs-ecs-ts**  
**URL:** https://github.com/Nice-Wolf-Studio/claude-skills-threejs-ecs-ts  
**License:** MIT | TypeScript + Three.js + Entity Component Systems for mobile-optimized Three.js games

**Capabilities:** Three.js scene initialization, renderer/camera/lighting configuration, resource management, window resize handling, animation loops, React Three Fiber integration, mobile touch input, performance optimizations targeting 60 FPS desktop, 30-60 FPS mobile depending on device tier

**diet103/claude-code-infrastructure-showcase**  
**URL:** https://github.com/diet103/claude-code-infrastructure-showcase  
Born from 6 months real-world use managing complex TypeScript microservices projects. Auto-activating skills, backend development guidelines with 12 resource files (routing, controllers, services, repositories, testing), modular design under context limits

**mrgoonie/claudekit-skills - TypeScript/JavaScript**  
**URL:** https://github.com/mrgoonie/claudekit-skills  
- **better-auth:** Comprehensive TypeScript authentication framework (email/password, OAuth, 2FA, passkeys, multi-tenancy)
- **web-frameworks:** Next.js (App Router, Server Components, RSC, PPR, SSR, SSG, ISR), Turborepo (monorepo management)
- **ui-styling:** shadcn/ui components (Radix UI + Tailwind), Tailwind CSS utility-first styling
- **frontend-development:** React/TypeScript guidelines with Suspense, lazy loading, useSuspenseQuery, MUI v7

**ruvnet/claude-flow - TypeScript**  
**URL:** https://github.com/ruvnet/claude-flow/wiki/CLAUDE-MD-TypeScript  
**Stars:** 10k+ | TypeScript best practices including strict type checking coordination, concurrent/parallel operations, build operations, Jest/Vitest suites with type checking

### Go Language Skills

**BradPerbs/claude-go**  
**URL:** https://github.com/BradPerbs/claude-go  
GoLang Wrapper for Claude 3 API with configuration functions and SendPrompt method

**Effective Go Development with Claude**  
**Article:** https://dshills.medium.com/effective-go-development-with-claude-best-practices-for-ai-pair-programming-83fba0247a4f  
Go-specific practices: Define directory structure early (cmd/, pkg/, internal/, api/, scripts/), write interfaces first for clean contracts, interface-driven design for idiomatic modular code

**ruvnet/claude-flow - Go**  
**URL:** https://github.com/ruvnet/claude-flow/wiki/CLAUDE-MD-Go  
Go concurrency patterns, simple syntax, standard library usage for microservices and CLI tools

### Rust Skills

**Microsoft Pragmatic Rust Guidelines Skill**  
**Article:** https://medium.com/rustaceans/teaching-claude-to-write-better-rust-automating-microsofts-guidelines-with-skills-3207a797b9f8  
**Author:** Enzo Lombardi | AI-optimized version of Microsoft's Rust guidelines specifically for coding assistants teaching Claude to consistently follow Rust best practices

**ruvnet/claude-flow - Rust**  
**URL:** https://github.com/ruvnet/claude-flow/wiki/CLAUDE-MD-Rust  
Memory-safe coordination with Cargo parallel compilation, Cargo operations batching, memory safety patterns, async/threading implementations, borrowing/ownership patterns

**Rust Development Excellence Reports:**
- **"Working with Claude Code: Accelerating My Rust Learning Journey"** (https://www.vincentbruijn.nl/articles/claude-code) - Built HTTP server while learning Rust
- **"Claude Code and Rust"** by Julian Schrittwieser (https://www.julian.ac/blog/2025/05/03/claude-code-and-rust) - "Rust is great for letting Claude Code work unsupervised" with type system acting as expert code reviewer
- **"Building personal software with Claude"** by Nelson Elhage (https://blog.nelhage.com/post/personal-software-with-claude) - Ported Emacs Lisp to Rust in single prompt, compiled first try, 1000x performance improvement

### Java Skills

**anthropic-sdk-java** (Official)  
Official Java client library for the Anthropic API with modern Java features, comprehensive documentation

**ruvnet/claude-flow - Java**  
**URL:** https://github.com/ruvnet/claude-flow/wiki/CLAUDE-MD-Java  
Maven/Gradle ecosystem coordination, Spring Boot operations, JUnit/TestNG suites in parallel, JPA/Hibernate configurations, enterprise patterns

**Claude-Java-AI** (Poe Bot)  
**URL:** https://poe.com/Claude-Java-AI  
Claude Java AI Assistant for writing, optimizing, improving Java code with constructive feedback on quality, efficiency, and adherence to Java standards

### Multi-Language and Language-Agnostic Skills

**Software Architecture** (ComposioHQ)  
Clean Architecture patterns, SOLID principles, comprehensive software design best practices across all languages

**General Language Support:**
Claude Code provides comprehensive support for C++, C#, Ruby, SQL with deep understanding of language-specific patterns, idioms, and best practices for each major language.

---

## OPERATIONS SKILLS: DevOps, Deployment, CI/CD, Infrastructure, Monitoring

### CI/CD Pipeline Skills

**djacobsmeyer/claude-skills-engineering**  
**URL:** https://github.com/djacobsmeyer/claude-skills-engineering  
**License:** MIT | **Created:** 2025-11-14

**DevOps Capabilities:**
- CI/CD Pipeline Builder: GitHub Actions, GitLab CI, CircleCI configuration
- Docker Workflow: Container management, Dockerfile generation, docker-compose
- Git worktree management for parallel development
- Automated code review with linting
- Test generation (unit, integration, E2E)

**Installation:** `/plugin marketplace add djacobsmeyer/claude-skills-engineering`

**wshobson/agents - CI/CD Plugin**  
**URL:** https://github.com/wshobson/agents  
**License:** MIT | **Status:** Updated for Sonnet 4.5 & Haiku 4.5

**Comprehensive system:** 85 specialized AI agents, 47 agent skills, 44 development tools in 63 focused plugins
- 4 specialized CI/CD skills: pipeline design, GitHub Actions, GitLab CI, secrets management
- Deployment engineering agents
- Full-stack orchestration with multi-agent workflows

**Installation:** `/plugin marketplace add wshobson/agents` then `/plugin install kubernetes-operations`

**ruvnet/claude-flow - CI/CD Module**  
**URL:** https://github.com/ruvnet/claude-flow/wiki/CLAUDE-MD-CICD  
**Ranked:** #1 in agent-based frameworks

Complete CI/CD pipeline setup with GitHub Actions, batch processing for all pipeline stages, Docker and Kubernetes configuration, GitOps workflows

### Cloud Platform Integration

**zxkane/aws-skills**  
**URL:** https://github.com/zxkane/aws-skills  
**License:** MIT | **Status:** ✅ Active

**AWS Capabilities:**
- **aws-cdk-development:** AWS CDK best practices, infrastructure as code, pre-deployment validation
- **aws-cost-operations:** Cost optimization with 7 integrated MCP servers (AWS Documentation, CDK, Billing, Cost Management, Pricing, Cost Explorer, CloudWatch, CloudTrail)
- **aws-serverless-eda:** Serverless and event-driven architecture with 4 integrated MCP servers (Serverless MCP, Lambda Tool, Step Functions, SNS/SQS)

**Supported Services:** Lambda, S3, EC2, CloudFormation, CDK, Step Functions, EventBridge, API Gateway, CloudWatch, Cost Explorer

**Installation:** `/plugin marketplace add zxkane/aws-skills` then `/plugin install aws-cdk@aws-skills`

**Claude with Amazon Bedrock** (Official AWS)  
**URL:** https://aws.amazon.com/bedrock/anthropic  
Claude Sonnet 4.5, Haiku 4.5, Opus 4.1 on Bedrock with tool use and agents for AWS integration, extended thinking mode  
**Training:** https://anthropic.skilljar.com/claude-in-amazon-bedrock

**Microsoft Azure Integration** (Official)  
**URL:** https://azure.microsoft.com/en-us/blog/introducing-anthropics-claude-models-in-microsoft-foundry  
Claude available in Microsoft Foundry with Skills integration for Azure DevOps automation, query Azure DevOps logs, diagnose issues, trigger deployments

**Azure MCP Server** (Official Microsoft)  
**URL:** https://github.com/microsoft/mcp/tree/main/servers/Azure.Mcp.Server  
Azure Storage, Cosmos DB, Azure CLI access with 40+ Azure service tools

**Google Cloud Run Server**  
**URL:** https://github.com/GoogleCloudPlatform/cloud-run-mcp  
Deploy code to Google Cloud Run with deployment automation

**Cloudflare Server** (Official)  
**URL:** https://github.com/cloudflare/mcp-server-cloudflare  
Workers, KV, R2, D1 management for edge computing and serverless deployment

### Container and Kubernetes Management

**Docker Server**  
**URL:** https://github.com/QuantGeekDev/docker-mcp  
Container operations, compose stack management for container lifecycle management

**Kubernetes Servers (Multiple implementations):**
1. **mcp-server-kubernetes** - https://github.com/strowk/mcp-k8s-go - Natural language cluster management
2. **k8m** - https://github.com/weibaohui/k8m - Multi-cluster with UI
3. **mkp** - https://github.com/StacklokLabs/mkp - Native Go implementation
4. **blankcut/kubernetes-claude** - https://playbooks.com/mcp/blankcut-kubernetes-claude - Integrating with ArgoCD and GitLab for GitOps workflows

**Common Features:** Pod logs, resource CRUD, command execution, monitoring, deployment management

### Infrastructure as Code (IaC)

**hashicorp/terraform-mcp-server** (Official)  
**URL:** https://github.com/hashicorp/terraform-mcp-server  
**Version:** 0.2.3 | **License:** Official HashiCorp

**Capabilities:**
- Terraform Registry API integration (providers, modules, policies)
- HCP Terraform & Terraform Enterprise support
- Workspace management (create, update, delete)
- Variables, tags, and run management
- Private registry access

**Installation:** `docker run -i --rm hashicorp/terraform-mcp-server:0.2.3`

**ahmedasmar/devops-claude-skills - IaC Terraform**  
**URL:** https://claude-plugins.dev/skills/@ahmedasmar/devops-claude-skills/skills  
Creating and validating Terraform configurations, module development, state management, Terragrunt patterns, terraform-docs auto-generation

**Pulumi Server** (Official)  
**URL:** https://github.com/pulumi/mcp-server  
Deploy and manage cloud infrastructure with infrastructure deployment and cloud automation

**metaskills/skill-builder**  
**URL:** https://github.com/metaskills/skill-builder  
**Author:** AWS Serverless Hero Ken Collins | Natural language skill creation: "Help me create a skill for deploying AWS Lambda functions"

### Deployment Automation

**mrgoonie/claudekit-skills - DevOps**  
**URL:** https://github.com/mrgoonie/claudekit-skills  
**Status:** 6+ months commercial development

**DevOps Capabilities:**
- Deploy to Cloudflare (Workers, R2, D1, KV, Pages, Durable Objects, Browser Rendering)
- Docker containers
- Google Cloud Platform (Compute Engine, GKE, Cloud Run, App Engine, Cloud Storage)
- Deploy serverless functions to the edge
- Set up CI/CD pipelines
- Optimize cloud infrastructure costs

**Vercel Server** (Official)  
**URL:** https://vercel.com/docs/mcp/vercel-mcp  
Access logs, search docs, manage projects and deployments for frontend deployment and serverless functions

**Defang Server**  
**URL:** https://github.com/DefangLabs/defang  
Deploy projects to cloud seamlessly with platform automation

### Monitoring and Logging

**zxkane/aws-skills - Operations Monitoring**  
CloudWatch integration (logs, metrics, alarms), CloudWatch Application Signals for distributed tracing, CloudTrail for audit logging, alert configuration and management

**wshobson/agents - Observability**  
Observability engineering agents, distributed debugging skills, application performance monitoring, incident response workflows with multi-agent orchestration

### Security Scanning and DevSecOps

**claude-code-security-review** (Official Anthropic)  
**URL:** https://github.com/anthropics/claude-code (feature)  
**Status:** Official Anthropic release (August 2025) | **License:** Team/Enterprise

**Security Capabilities:**
- Automated security scanning on pull requests
- Detects 10 major vulnerability categories: SQL injection, XSS, authentication flaws, hardcoded secrets, weak encryption, authorization bypasses, business logic race conditions, CSRF, SSRF, known CVEs in dependencies
- GitHub Actions integration for automated PR reviews
- `/security-review` terminal command
- Inline suggestions with remediation steps
- Built-in false positive filtering
- Diff-aware scanning (only changed files)
- Language agnostic with semantic vulnerability detection

**Snyk MCP Server** (Official)  
**URL:** https://snyk.io/articles/claude-desktop-and-snyk-mcp  
**Status:** Official Snyk (CLI v1.1298.0+)

**Security Capabilities:**
- 11 security scanning tools: Code scanning (SAST), open source dependency scanning, container scanning, infrastructure as code scanning, license compliance, authentication status
- Auto-fix vulnerabilities via natural language
- Scan-fix-rescan workflow
- Real-time vulnerability detection
- Enterprise DevSecOps integration

**Free Tier:** 400 OS tests, 100 Code tests, 300 IaC tests, 100 Container tests monthly  
**Open Source:** Unlimited via Secure Developer Program

**GitGuardian Server** (Official)  
**URL:** https://github.com/GitGuardian/gg-mcp  
Secret scanning with 500+ secret detectors and credential leak prevention

**CrowdStrike Falcon Server** (Official)  
**URL:** https://github.com/CrowdStrike/falcon-mcp  
Detections, incidents, threat intelligence, vulnerabilities for security analysis and threat detection

**Semgrep Server**  
**URL:** https://github.com/semgrep/semgrep/blob/develop/cli/src/semgrep/mcp/README.md  
Static code analysis and vulnerability scanning

**SonarQube Server** (Official)  
**URL:** https://github.com/SonarSource/sonarqube-mcp-server  
Code snippet analysis, integration with SonarQube Server/Cloud for code quality and technical debt monitoring

---

## MCP SERVERS: Essential Tool Integrations

The Model Context Protocol enables Claude to connect with external tools and services. Below are production-ready MCP servers organized by capability.

### Database Integration

**PostgreSQL Server**  
**URL:** https://github.com/modelcontextprotocol/servers/tree/main/src/postgres | **License:** MIT  
Schema inspection, query capabilities, read/write operations

**SQLite Server**  
**URL:** https://github.com/modelcontextprotocol/servers/tree/main/src/sqlite | **License:** MIT  
Database interaction and business intelligence

**MySQL Server**  
**URL:** https://github.com/designcomputer/mysql_mcp_server  
Configurable access controls and schema inspection

**MongoDB Servers**  
1. https://github.com/kiliczsh/mcp-mongo-server
2. https://github.com/furey/mongodb-lens (Full featured)  
Query and analyze MongoDB collections

**BigQuery Server**  
**URL:** https://github.com/LucasHild/mcp-server-bigquery  
Schema inspection and SQL queries for data warehouse querying

**Redis Server** (Official)  
**URL:** https://github.com/redis/mcp-redis  
Key-value store operations and data management

**DuckDB Server**  
**URL:** https://github.com/ktanaka101/mcp-server-duckdb  
Schema inspection, query capabilities, large-scale data analysis

**Apache Doris Server** (Official)  
**URL:** https://github.com/apache/doris-mcp-server  
MPP-based real-time data warehouse queries

### Browser Automation and Testing

**Playwright Server** (Official Microsoft)  
**URL:** https://github.com/microsoft/playwright-mcp  
Browser automation, testing, web scraping for E2E testing

**Puppeteer Server**  
**URL:** https://github.com/modelcontextprotocol/servers/tree/main/src/puppeteer | **License:** MIT  
Browser automation, web scraping, data extraction

### API Development and Testing

**Postman API Server** (Official)  
**URL:** https://github.com/postmanlabs/postman-api-mcp  
Manage Postman resources using Postman API for API testing and collection management

**OpenAPI Schema Explorer**  
**URL:** https://github.com/kadykov/mcp-openapi-schema-explorer  
Token-efficient access to OpenAPI/Swagger specs for API schema exploration

### Search and Web Scraping

**Brave Search Server** (Official)  
**URL:** https://github.com/brave/brave-search-mcp-server  
Web and local search using Brave's Search API

**Exa Search Server** (Official)  
**URL:** https://github.com/exa-labs/exa-mcp-server  
AI-powered search engine integration for semantic search

**Tavily Server**  
**URL:** https://github.com/Tomatio13/mcp-server-tavily  
Search + extract for AI agents and research automation

**Firecrawl Server** (Official)  
**URL:** https://github.com/firecrawl/firecrawl-mcp-server  
Web data extraction and scraping

**Apify Actors Server** (Official)  
**URL:** https://github.com/apify/apify-mcp-server  
6,000+ pre-built cloud tools for data extraction and web scraping at scale

### Documentation and Knowledge

**Context7 Server**  
Up-to-date, version-specific documentation for coding to reduce AI hallucinations

**Microsoft Learn Docs Server** (Official)  
**URL:** https://github.com/microsoftdocs/mcp  
Access to Microsoft's official documentation for technical documentation retrieval

**Obsidian Servers**  
1. https://github.com/MarkusPfundstein/mcp-obsidian
2. https://github.com/calclavia/mcp-obsidian  
Personal knowledge base access and note management

### Collaboration and Project Management

**Linear Server**  
**URL:** https://github.com/jerhadf/linear-mcp-server  
Issue tracking and project management

**Jira Server**  
**URL:** https://github.com/tom28881/mcp-jira-server  
20+ tools for issue CRUD, sprint management, comments, attachments for agile project management

**Atlassian Server** (Official)  
**URL:** https://www.atlassian.com/platform/remote-mcp-server  
Jira and Confluence integration for work item management and documentation access

**Notion Servers**  
1. https://github.com/danhilse/notion_mcp
2. https://github.com/suekou/mcp-notion-server  
Todo lists, notes, database management, knowledge base access

**Slack Server**  
**URL:** https://github.com/korotovsky/slack-mcp-server  
Most powerful MCP Slack Server with Stdio and SSE transports for team communication

### Multi-Tool Aggregators

**Composio**  
**URL:** https://docs.composio.dev/docs/mcp-overview  
Connect to 100+ tools with zero setup and built-in auth

**Rube** (by Composio)  
**URL:** https://rube.composio.dev  
Connect to 500+ apps (Gmail, Slack, GitHub, Notion) with unified integration

**Zapier Server** (Official)  
**URL:** https://zapier.com/mcp  
Connect to 8,000 apps instantly for workflow automation

**Pipedream Server** (Official)  
**URL:** https://github.com/PipedreamHQ/pipedream/tree/master/modelcontextprotocol  
2,500 APIs with 8,000+ prebuilt tools for API integration and workflow automation

---

## Quality Indicators and Selection Criteria

### ⭐⭐⭐⭐⭐ Highest Quality (Official & Well-Maintained)
- Official implementations by Anthropic, GitHub, Microsoft, AWS, HashiCorp, etc.
- Active maintenance with regular updates
- Comprehensive documentation
- High GitHub stars (1000+)
- Production-ready with security considerations

**Examples:** anthropics/skills, GitHub MCP Server, Azure MCP Server, Terraform MCP Server, Snyk MCP

### ⭐⭐⭐⭐ High Quality (Community with Strong Support)
- Well-documented community projects
- Active development with multiple contributors
- Good test coverage
- Moderate GitHub stars (100-1000)

**Examples:** obra/superpowers, alirezarezvani/claude-skills, travisvn/awesome-claude-skills

### ⭐⭐⭐ Good Quality (Functional & Maintained)
- Working implementations
- Basic documentation
- Some maintenance activity
- Smaller community

**Examples:** Individual specialized skills, community MCP servers

---

## Installation Methods

### Claude.ai (Web Interface)
1. Navigate to Settings > Capabilities
2. Enable "Code execution and file creation"
3. Toggle on desired skills or upload custom skills (ZIP format)

### Claude Code (Terminal)
```bash
# Add marketplace
/plugin marketplace add anthropics/skills
/plugin marketplace add obra/superpowers-marketplace

# Install specific skills
/plugin install document-skills@anthropic-agent-skills
/plugin install superpowers@superpowers-marketplace

# Manual installation
cd ~/.claude/skills
git clone [skill-repository-url]
```

### Claude API
Skills accessible via `/v1/skills` API endpoint:
```python
import anthropic
client = anthropic.Anthropic(api_key="your-api-key")
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    skills=["skill-id"],
    messages=[{"role": "user", "content": "prompt"}]
)
```

### MCP Server Configuration
Edit `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "package-name"],
      "env": {
        "API_KEY": "your-key"
      }
    }
  }
}
```

---

## Licensing Summary

**Most Common Open Source Licenses:**
- **MIT License:** Most community skills and MCP servers (highly permissive)
- **Apache 2.0:** Official Anthropic example skills, many enterprise projects
- **BSD-3-Clause:** Some community contributions
- **Open Source (Various):** Individual projects with clear attribution

**Note on Document Skills:** Anthropic's document skills (docx, pdf, pptx, xlsx) are source-available for reference but not open source. They ship pre-included with Claude and are primarily intended as reference examples.

---

## Essential Resources

### Official Documentation
- **MCP Specification:** https://modelcontextprotocol.io
- **Anthropic Skills Blog:** https://www.anthropic.com/news/skills
- **Claude Documentation:** https://docs.anthropic.com
- **Anthropic Academy:** https://anthropic.skilljar.com (Free training courses)

### Community Resources
- **Awesome MCP Servers:** https://github.com/appcypher/awesome-mcp-servers (380+ servers)
- **MCP Servers Directory:** https://mcpservers.org
- **Best of MCP:** https://github.com/tolkonepiu/best-of-mcp-servers
- **Skills Marketplace:** https://skillsmp.com (13,000+ skills indexed)

### Package Managers
- **MCPM (CLI):** https://github.com/pathintegral-institute/mcpm.sh
- **mcp-get:** https://github.com/michaellatman/mcp-get

---

## Conclusion

The Claude Code skills ecosystem has rapidly evolved into a comprehensive, production-ready toolkit with:

**Coverage:**
- **Official Anthropic:** Production-grade document skills, MCP infrastructure, comprehensive SDKs
- **Community Collections:** 10+ major repositories, 13,000+ indexed skills
- **MCP Servers:** 200+ production-ready integrations for tools and services
- **Languages:** Comprehensive support for Python, TypeScript, JavaScript, Go, Rust, Java, and more
- **DevOps:** Complete CI/CD, cloud platforms, security scanning, infrastructure automation

**Key Strengths:**
- Progressive disclosure architecture (efficient token usage)
- Freely available open source content (MIT/Apache 2.0)
- Active community with rapid innovation
- Official support from major companies (GitHub, Microsoft, AWS, HashiCorp)
- Production-ready quality with comprehensive documentation

**Recommended Starting Points:**
1. **Official:** anthropics/skills for production-grade examples
2. **Community:** obra/superpowers for battle-tested development workflows
3. **Comprehensive:** travisvn/awesome-claude-skills for overview
4. **Enterprise:** alirezarezvani/claude-skills for production teams
5. **Integration:** GitHub MCP Server, AWS/Azure cloud skills

All resources documented here are freely available and maintained by active communities, providing a solid foundation for building comprehensive Claude Code skill collections across all development domains.