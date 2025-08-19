# Vercel Ops Agent

Specialized operations agent for Vercel platform deployment, environment management, and optimization. Expert in serverless architecture, edge functions, and modern deployment strategies including rolling releases.

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Core Features](#core-features)
4. [Installation and Setup](#installation-and-setup)
5. [Usage Examples](#usage-examples)
6. [Configuration Guide](#configuration-guide)
7. [Integration with PM Workflow](#integration-with-pm-workflow)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)
10. [Reference](#reference)

## Overview

The Vercel Ops Agent is a specialized component of the Claude MPM framework designed to handle all aspects of Vercel platform operations. It provides comprehensive deployment management, environment configuration, performance optimization, and monitoring capabilities for modern serverless applications.

### Key Capabilities

- **Deployment Management**: Preview, production, and rolling releases
- **Environment Configuration**: Multi-environment variable management
- **Performance Optimization**: Edge functions and serverless optimization
- **Domain Management**: Custom domains with automatic SSL
- **Monitoring & Analytics**: Performance tracking and error monitoring
- **Security**: Headers, CORS, and security best practices
- **CI/CD Integration**: GitHub Actions and automated workflows

### Supported Frameworks

- Next.js
- React
- Vue
- Svelte
- Angular
- Nuxt
- Gatsby
- Remix
- Astro
- SolidStart
- Qwik

## Getting Started

### Prerequisites

Before using the Vercel Ops Agent, ensure you have:

- **Node.js**: Version 18.0.0 or higher
- **npm**: Version 9.0.0 or higher
- **Git**: For version control integration
- **Vercel Account**: Free or paid Vercel account
- **Vercel CLI**: Installed globally

### Quick Setup

1. **Install Vercel CLI**:
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel**:
   ```bash
   vercel login
   ```

3. **Verify Installation**:
   ```bash
   vercel --version
   ```

4. **Deploy with Agent**:
   Request deployment through Claude MPM with the Vercel Ops Agent.

## Core Features

### 1. Deployment Management

#### Preview Deployments
- Automatic deployments for every branch and PR
- Unique preview URLs for testing
- Isolated environments for feature testing

```bash
# Deploy current branch to preview
vercel

# Deploy with specific project
vercel --project my-project
```

#### Production Deployments
- Controlled releases with rollback capability
- Deployment aliases and custom URLs
- Build optimization and caching

```bash
# Deploy to production
vercel --prod

# Force new deployment (bypass cache)
vercel --force
```

#### Rolling Releases (2025 Feature)
- Gradual traffic shifting for safe deployments
- Canary deployments with automatic monitoring
- Instant rollback capabilities

```json
{
  "deployments": {
    "rolling": {
      "enabled": true,
      "strategy": "canary",
      "percentage": 10,
      "increment": 20,
      "interval": "5m"
    }
  }
}
```

### 2. Environment Variable Management

#### Environment-Specific Configuration
- Development, preview, and production environments
- Secure secret management
- Team-based access controls

```bash
# Add environment variables
vercel env add API_KEY production
vercel env add API_KEY preview
vercel env add API_KEY development

# Pull variables locally
vercel env pull .env.local

# List all variables
vercel env ls
```

#### Best Practices
- Use different values per environment
- Never commit secrets to repository
- Rotate API keys regularly
- Use Vercel CLI or dashboard for sensitive values

### 3. Domain Configuration

#### Custom Domains
- Automatic SSL certificate provisioning
- Wildcard domain support (Pro plan)
- Subdomain configuration

```bash
# Add custom domain
vercel domains add example.com

# Configure subdomain
vercel domains add api.example.com

# List all domains
vercel domains ls

# Inspect domain configuration
vercel domains inspect example.com
```

#### DNS Configuration
- **A Record**: `76.76.21.21`
- **CNAME**: `cname.vercel-dns.com`
- **SSL**: Automatic provisioning (up to 24 hours)

### 4. Performance Optimization

#### Edge Functions
- Deploy functions to Vercel Edge Network
- Global distribution for low latency
- 1MB size limit for edge functions

```javascript
// middleware.js for Edge Functions
export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
  runtime: 'edge',
  regions: ['iad1', 'sfo1', 'pdx1'],
};

export default function middleware(request) {
  // Edge function logic
  return NextResponse.next();
}
```

#### Serverless Functions
- Optimize function size and cold starts
- Configure memory and timeout settings
- Regional deployment strategies

```javascript
// Optimize serverless functions
export default async function handler(req, res) {
  // Dynamic import for heavy libraries
  const heavyLib = await import('heavy-library');
  
  // Function logic
}

// Configure function settings
export const config = {
  maxDuration: 30,
  memory: 1024,
};
```

### 5. Monitoring & Analytics

#### Key Metrics
- Build time trends
- Cold start frequency
- API response times
- Core Web Vitals scores
- Error rates by deployment
- Traffic patterns and geography

#### Vercel Speed Insights
- Core Web Vitals monitoring
- Performance scoring
- Real user metrics
- Optimization recommendations

```bash
# View deployment logs
vercel logs

# Follow real-time logs
vercel logs --follow

# Check specific deployment
vercel logs deployment-url
```

## Installation and Setup

### Initial Configuration

1. **Project Setup**:
   ```bash
   # Initialize Vercel project
   vercel init

   # Link existing project
   vercel link
   ```

2. **Create vercel.json**:
   ```json
   {
     "buildCommand": "npm run build",
     "outputDirectory": ".next",
     "devCommand": "npm run dev",
     "installCommand": "npm install",
     "framework": "nextjs",
     "regions": ["iad1"],
     "functions": {
       "pages/api/*.js": {
         "maxDuration": 10
       }
     }
   }
   ```

3. **Environment Variables**:
   ```bash
   # Set up environment variables
   vercel env add DATABASE_URL production
   vercel env add API_SECRET production
   vercel env add NEXT_PUBLIC_APP_URL production
   ```

### Authentication Setup

1. **Generate API Token**:
   - Go to Vercel Dashboard → Settings → Tokens
   - Create new token with appropriate scope
   - Store securely for CI/CD integration

2. **Team Configuration**:
   ```bash
   # List teams
   vercel teams ls

   # Switch team context
   vercel switch
   ```

## Usage Examples

### Deploying a Next.js Application

#### Basic Deployment
```bash
# Deploy to preview environment
vercel

# Deploy to production
vercel --prod
```

#### With Custom Configuration
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "framework": "nextjs",
  "regions": ["iad1", "sfo1"],
  "env": {
    "NEXT_PUBLIC_API_URL": "@api-url",
    "DATABASE_URL": "@database-url"
  },
  "functions": {
    "pages/api/heavy-task.js": {
      "maxDuration": 60,
      "memory": 3008
    }
  },
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "X-Frame-Options",
          "value": "DENY"
        }
      ]
    }
  ]
}
```

### Setting up Preview Deployments for PRs

1. **GitHub Integration**:
   - Connect repository to Vercel
   - Configure automatic deployments
   - Set up branch protection rules

2. **Preview URLs**:
   ```bash
   # Each PR gets unique URL
   # Format: projectname-git-branchname-teamname.vercel.app
   ```

3. **Environment Isolation**:
   ```bash
   # Preview environment variables
   vercel env add API_KEY preview
   vercel env add DB_NAME preview_db
   ```

### Configuring Custom Domains

#### Production Domain
```bash
# Add production domain
vercel domains add example.com

# Configure apex domain
vercel alias set production-deployment.vercel.app example.com
```

#### Staging Environment
```bash
# Add staging subdomain
vercel domains add staging.example.com

# Configure staging alias
vercel alias set staging-deployment.vercel.app staging.example.com
```

### Managing Environment Variables Across Environments

#### Development Environment
```bash
vercel env add API_KEY development
vercel env add DB_HOST localhost
vercel env add NODE_ENV development
```

#### Preview Environment
```bash
vercel env add API_KEY preview
vercel env add DB_HOST preview-db.example.com
vercel env add NODE_ENV preview
```

#### Production Environment
```bash
vercel env add API_KEY production
vercel env add DB_HOST prod-db.example.com
vercel env add NODE_ENV production
```

### Implementing Rolling Releases

#### Configuration
```json
{
  "deployments": {
    "rolling": {
      "enabled": true,
      "strategy": "canary",
      "percentage": 10,
      "increment": 20,
      "interval": "5m",
      "metrics": {
        "errorRate": 0.01,
        "responseTime": 500
      }
    }
  }
}
```

#### Monitoring
```bash
# Monitor deployment progress
vercel logs --follow

# Check deployment status
vercel ls

# Rollback if needed
vercel rollback
```

### Setting up CI/CD with GitHub Actions

```yaml
name: Vercel Deployment
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run tests
        run: npm test
      
      - name: Install Vercel CLI
        run: npm install -g vercel
      
      - name: Deploy to Vercel
        env:
          VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
          VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
          VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}
        run: |
          if [ "${{ github.event_name }}" == "push" ] && [ "${{ github.ref }}" == "refs/heads/main" ]; then
            vercel --prod --token=$VERCEL_TOKEN
          else
            vercel --token=$VERCEL_TOKEN
          fi
```

## Configuration Guide

### vercel.json Configuration

#### Basic Configuration
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "devCommand": "npm run dev",
  "installCommand": "npm install",
  "framework": "nextjs"
}
```

#### Advanced Configuration
```json
{
  "version": 2,
  "builds": [
    {
      "src": "package.json",
      "use": "@vercel/node"
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "/api/$1"
    }
  ],
  "env": {
    "NODE_ENV": "production"
  },
  "build": {
    "env": {
      "NEXT_TELEMETRY_DISABLED": "1"
    }
  },
  "functions": {
    "pages/api/*.js": {
      "maxDuration": 30
    }
  },
  "regions": ["iad1"],
  "github": {
    "autoAlias": false
  }
}
```

### Build Optimization

#### Caching Strategy
```json
{
  "crons": [
    {
      "path": "/api/revalidate",
      "schedule": "0 0 * * *"
    }
  ],
  "headers": [
    {
      "source": "/static/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=31536000, immutable"
        }
      ]
    }
  ]
}
```

#### Region Selection
```json
{
  "regions": ["iad1", "sfo1", "hnd1"],
  "functions": {
    "pages/api/global/*.js": {
      "regions": ["all"]
    },
    "pages/api/us/*.js": {
      "regions": ["iad1", "sfo1"]
    }
  }
}
```

### Security Configuration

#### Security Headers
```json
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "Content-Security-Policy",
          "value": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval';"
        },
        {
          "key": "Strict-Transport-Security",
          "value": "max-age=31536000; includeSubDomains"
        },
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "X-Frame-Options",
          "value": "SAMEORIGIN"
        },
        {
          "key": "X-XSS-Protection",
          "value": "1; mode=block"
        },
        {
          "key": "Referrer-Policy",
          "value": "strict-origin-when-cross-origin"
        }
      ]
    }
  ]
}
```

#### CORS Configuration
```json
{
  "headers": [
    {
      "source": "/api/(.*)",
      "headers": [
        {
          "key": "Access-Control-Allow-Origin",
          "value": "https://yourdomain.com"
        },
        {
          "key": "Access-Control-Allow-Methods",
          "value": "GET, POST, PUT, DELETE, OPTIONS"
        },
        {
          "key": "Access-Control-Allow-Headers",
          "value": "Content-Type, Authorization"
        }
      ]
    }
  ]
}
```

### Environment-Specific Settings

#### Development
```bash
export VERCEL_ENV=development
export NODE_ENV=development
export API_URL=http://localhost:3000/api
```

#### Preview
```bash
export VERCEL_ENV=preview
export NODE_ENV=production
export API_URL=https://api-preview.example.com
```

#### Production
```bash
export VERCEL_ENV=production
export NODE_ENV=production
export API_URL=https://api.example.com
```

## Integration with PM Workflow

### Agent Handoff Scenarios

#### From Engineer Agent
When the Engineer Agent completes feature development:

1. **Feature Ready Signal**:
   ```
   Engineer → VercelOps: "Feature branch ready for deployment"
   - Branch: feature/user-authentication
   - Build status: Passing
   - Tests: All green
   ```

2. **VercelOps Response**:
   - Create preview deployment
   - Provide preview URL for testing
   - Configure environment variables
   - Set up monitoring

#### To QA Agent
After successful deployment:

1. **Preview URL Handoff**:
   ```
   VercelOps → QA: "Preview deployment ready for testing"
   - Preview URL: https://app-git-feature-auth-team.vercel.app
   - Environment: Preview
   - Features: User authentication, password reset
   ```

2. **Environment Details**:
   - Database: Preview database
   - API endpoints: Preview API
   - Authentication: Test OAuth providers

#### With Security Agent
For security reviews and token management:

1. **Security Review**:
   ```
   VercelOps → Security: "Production deployment security review"
   - Security headers configured
   - API tokens rotated
   - HTTPS enforced
   ```

2. **Token Rotation**:
   ```
   Security → VercelOps: "API tokens updated"
   - New tokens configured in Vercel
   - Old tokens revoked
   - Environment variables updated
   ```

### PM Delegation Examples

#### Feature Deployment
```
PM: "Deploy the new user dashboard feature to production"

VercelOps Response:
1. Create preview deployment for final testing
2. Configure production environment variables
3. Deploy with rolling release (10% initial traffic)
4. Monitor metrics and error rates
5. Complete rollout or rollback based on performance
```

#### Environment Setup
```
PM: "Set up staging environment for client demo"

VercelOps Response:
1. Configure staging.clientname.com domain
2. Set up environment variables for demo data
3. Configure SSL certificates
4. Set up monitoring and analytics
5. Provide access credentials for demo
```

#### Emergency Rollback
```
PM: "Production issues detected, immediate rollback required"

VercelOps Response:
1. Identify current production deployment
2. Execute immediate rollback to previous stable version
3. Verify rollback success
4. Monitor error rates and performance
5. Provide incident report with timeline
```

### Coordination Protocols

#### Pre-Deployment Checklist
- [ ] Build passes locally and in CI
- [ ] Tests are green
- [ ] Environment variables configured
- [ ] Domain and SSL setup verified
- [ ] Monitoring configured
- [ ] Rollback plan prepared

#### Post-Deployment Verification
- [ ] Deployment URL accessible
- [ ] All features functional
- [ ] Environment variables working
- [ ] Performance metrics within range
- [ ] Error rates under threshold
- [ ] Monitoring alerts configured

#### Rollback Triggers
- Error rate > 1%
- Response time > 500ms
- Build failures
- Security vulnerabilities
- Customer-reported issues

## Best Practices

### Deployment Strategy

#### 1. Use Preview Deployments
- Deploy every branch for testing
- Provide unique URLs for stakeholders
- Test with realistic data
- Verify environment variables

#### 2. Implement Rolling Releases
- Start with 10% traffic
- Monitor key metrics
- Increment by 20% every 5 minutes
- Automatic rollback on errors

#### 3. Environment Isolation
- Separate environments for dev/preview/prod
- Different API endpoints per environment
- Isolated databases and services
- Environment-specific monitoring

### Security Guidelines

#### 1. Environment Variables
- Never commit secrets to repository
- Use Vercel CLI or dashboard for sensitive values
- Rotate API keys regularly
- Use different values per environment

#### 2. Security Headers
- Implement CSP (Content Security Policy)
- Use HTTPS everywhere
- Configure CORS properly
- Set security headers globally

#### 3. API Security
- Implement rate limiting
- Validate all inputs
- Use authentication middleware
- Monitor for suspicious activity

### Performance Optimization

#### 1. Build Optimization
- Use ISR (Incremental Static Regeneration)
- Implement proper caching headers
- Optimize images with next/image
- Minimize JavaScript bundle size

#### 2. Function Optimization
- Use dynamic imports for heavy libraries
- Minimize function size
- Configure appropriate memory settings
- Implement connection pooling

#### 3. Monitoring
- Track Core Web Vitals
- Monitor build times
- Watch error rates
- Set up performance alerts

### Team Collaboration

#### 1. Documentation
- Document deployment procedures
- Maintain runbooks for issues
- Update team on new features
- Share performance insights

#### 2. Communication
- Use TodoWrite for task tracking
- Coordinate with other agents
- Provide status updates
- Share preview URLs promptly

#### 3. Version Control
- Tag production releases
- Maintain clean commit history
- Use semantic versioning
- Document breaking changes

### Cost Management

#### 1. Resource Optimization
- Monitor function execution times
- Optimize build processes
- Use appropriate regions
- Configure function memory efficiently

#### 2. Plan Management
- Understand plan limits
- Monitor usage metrics
- Optimize for cost efficiency
- Plan upgrades strategically

## Troubleshooting

### Common Build Issues

#### Build Timeout
**Symptoms**: Build fails after 45 minutes
**Solutions**:
```bash
# Split large builds into smaller chunks
npm run build:split

# Use prebuilt output
vercel --prebuilt

# Increase build memory in vercel.json
{
  "build": {
    "env": {
      "NODE_OPTIONS": "--max-old-space-size=4096"
    }
  }
}
```

#### Dependency Issues
**Symptoms**: Missing dependencies in production
**Solutions**:
```bash
# Verify package.json dependencies
npm install --production

# Check for peer dependencies
npm ls

# Use exact versions for critical dependencies
{
  "dependencies": {
    "react": "18.2.0"
  }
}
```

#### Build Cache Issues
**Symptoms**: Old code in deployment
**Solutions**:
```bash
# Force new deployment
vercel --force

# Clear build cache
vercel build --debug

# Check .vercelignore file
```

### Environment Variable Problems

#### Variables Not Available
**Symptoms**: Environment variables undefined in application
**Solutions**:
```bash
# Check variable names (case-sensitive)
vercel env ls

# Verify correct environment
vercel env ls production

# For client-side variables, use NEXT_PUBLIC_ prefix
NEXT_PUBLIC_API_URL=https://api.example.com

# Pull latest variables
vercel env pull .env.local
```

#### Secret Management
**Symptoms**: Secrets not properly secured
**Solutions**:
- Use Vercel dashboard for sensitive values
- Never log environment variables
- Rotate secrets regularly
- Use different values per environment

### Domain Configuration Issues

#### DNS Not Working
**Symptoms**: Domain not resolving to Vercel
**Solutions**:
```bash
# Verify DNS configuration
vercel domains inspect example.com

# Check DNS propagation
nslookup example.com
dig example.com

# Common DNS settings:
# A record: 76.76.21.21
# CNAME: cname.vercel-dns.com
```

#### SSL Certificate Problems
**Symptoms**: SSL errors or warnings
**Solutions**:
- Wait up to 24 hours for automatic SSL provisioning
- Verify domain ownership
- Check for DNS CAA records
- Contact Vercel support for persistent issues

### Performance Issues

#### Slow Function Execution
**Symptoms**: High response times, timeouts
**Solutions**:
```javascript
// Optimize function size
export default async function handler(req, res) {
  // Use dynamic imports
  const { processData } = await import('./utils/processor');
  
  // Implement caching
  const cached = await redis.get(key);
  if (cached) return res.json(cached);
  
  // Process and cache result
  const result = await processData(req.body);
  await redis.set(key, result, 'EX', 300);
  
  res.json(result);
}

// Configure function settings
export const config = {
  maxDuration: 30,
  memory: 1024,
};
```

#### High Cold Start Times
**Symptoms**: Slow initial function execution
**Solutions**:
- Minimize dependencies
- Use lighter runtime options
- Implement connection pooling
- Consider Edge Functions for simple operations

### Deployment Rollback

#### Emergency Rollback
```bash
# List recent deployments
vercel ls

# Rollback to previous production deployment
vercel rollback

# Rollback to specific deployment
vercel rollback dpl_FqB4QWLxVqB5QWLxVqB5

# Verify rollback success
vercel ls --prod
```

#### Rollback Verification
- [ ] Application accessible
- [ ] All features functional
- [ ] Database integrity maintained
- [ ] Monitoring shows stable metrics
- [ ] Error rates normalized

### Getting Help

#### Debug Information
```bash
# Enable debug logging
vercel --debug

# Check build logs
vercel logs --type build

# View function logs
vercel logs --type function

# Get deployment info
vercel inspect deployment-url
```

#### Support Channels
1. **Vercel Documentation**: https://vercel.com/docs
2. **Vercel Support**: For paid plans
3. **Community Forum**: GitHub Discussions
4. **Status Page**: https://vercel-status.com

## Reference

### CLI Commands Reference

#### Deployment Commands
```bash
vercel                           # Deploy to preview
vercel --prod                    # Deploy to production
vercel --prebuilt               # Deploy prebuilt output
vercel --force                  # Force new deployment
vercel --project my-project     # Deploy specific project
vercel ./dist --prod           # Deploy specific directory
vercel rollback                # Rollback to previous
vercel rollback [url]          # Rollback to specific deployment
```

#### Environment Commands
```bash
vercel env ls                   # List environment variables
vercel env add KEY value env    # Add environment variable
vercel env rm KEY env          # Remove environment variable
vercel env pull [file]         # Pull environment variables
```

#### Domain Commands
```bash
vercel domains ls              # List domains
vercel domains add domain      # Add domain
vercel domains rm domain       # Remove domain
vercel domains inspect domain  # Inspect domain config
```

#### Project Commands
```bash
vercel project ls              # List projects
vercel project add             # Add project
vercel project rm              # Remove project
vercel link                    # Link local project
```

#### Utility Commands
```bash
vercel ls                      # List deployments
vercel logs                    # View logs
vercel logs --follow          # Follow logs
vercel inspect [url]          # Inspect deployment
vercel alias ls               # List aliases
vercel alias set source target # Set alias
```

### Configuration Files

#### vercel.json Schema
```json
{
  "version": 2,
  "name": "project-name",
  "builds": [],
  "routes": [],
  "env": {},
  "build": {
    "env": {}
  },
  "functions": {},
  "regions": [],
  "github": {
    "autoAlias": false,
    "autoJobCancelation": true
  },
  "headers": [],
  "redirects": [],
  "rewrites": [],
  "cleanUrls": true,
  "trailingSlash": false,
  "crons": []
}
```

#### .vercelignore Example
```
.env.local
.env.*.local
npm-debug.log*
yarn-debug.log*
yarn-error.log*
node_modules/
.DS_Store
*.tgz
my-app*.tar.gz
coverage/
.cache/
.vercel/
```

### API Endpoints

#### Vercel REST API
- **Deployments**: `https://api.vercel.com/v13/deployments`
- **Projects**: `https://api.vercel.com/v9/projects`
- **Domains**: `https://api.vercel.com/v5/domains`
- **Environment**: `https://api.vercel.com/v10/projects/{projectId}/env`
- **Teams**: `https://api.vercel.com/v2/teams`

### Platform Limits

#### Resource Limits
- **Function Size**: 50MB (compressed)
- **Edge Function Size**: 1MB
- **Environment Variables**: 64KB total
- **Build Time**: 45 minutes
- **Function Timeout**: 10s (Hobby), 60s (Pro)
- **File Count**: 10,000 files
- **Deployment Size**: 100MB

#### Plan Differences
- **Hobby**: Personal projects, community support
- **Pro**: Team features, custom domains, priority support
- **Enterprise**: Advanced security, SLA, dedicated support

### Integration Examples

#### GitHub Actions
```yaml
- name: Deploy to Vercel
  uses: amondnet/vercel-action@v25
  with:
    vercel-token: ${{ secrets.VERCEL_TOKEN }}
    vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
    vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
    working-directory: ./
```

#### Next.js Integration
```javascript
// next.config.js
module.exports = {
  async redirects() {
    return [
      {
        source: '/old-path',
        destination: '/new-path',
        permanent: true,
      },
    ]
  },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
        ],
      },
    ]
  },
}
```

This comprehensive documentation provides teams with everything needed to effectively use the Vercel Ops Agent for their deployment and operations needs within the Claude MPM framework.