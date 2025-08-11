# Claude-MPM Docker Testing

This directory contains Docker configurations for testing clean installations of claude-mpm.

## Quick Start

### 1. Run Installation Verification

Test a clean installation and run verification checks:

```bash
# From the project root directory
cd docker
docker-compose up claude-mpm-clean
```

This will:
- Build a clean Python 3.11 environment
- Install all dependencies
- Install claude-mpm in editable mode
- Run comprehensive verification tests
- Display the results

### 2. Interactive Testing

Start an interactive container for manual testing:

```bash
# Start interactive container
docker-compose --profile interactive up -d claude-mpm-interactive

# Connect to the container
docker-compose exec claude-mpm-interactive bash

# Inside the container, you can run:
python -m claude_mpm.cli --help
python -m claude_mpm.cli agents list
python -m claude_mpm.cli memory show
```

### 3. Run Test Suite

Execute the test suite in a clean environment:

```bash
# Run unit tests (excluding e2e tests)
docker-compose --profile test up claude-mpm-test
```

### 4. Development Mode

Run a development container with mounted source code:

```bash
# Start development container
docker-compose --profile dev up -d claude-mpm-dev

# Connect to the container
docker-compose exec claude-mpm-dev bash

# Changes to source files on host will be reflected in container
```

## Available Services

| Service | Purpose | Profile | Command |
|---------|---------|---------|---------|
| `claude-mpm-clean` | Verify clean installation | default | Automatic verification |
| `claude-mpm-interactive` | Manual testing | interactive | Bash shell |
| `claude-mpm-test` | Run test suite | test | pytest |
| `claude-mpm-dev` | Development with hot reload | dev | Bash shell |

## Building Images

```bash
# Build all images
docker-compose build

# Build specific image
docker-compose build claude-mpm-clean

# Build without cache
docker-compose build --no-cache claude-mpm-clean
```

## Viewing Logs

```bash
# View logs from verification
docker-compose logs claude-mpm-clean

# Follow logs in real-time
docker-compose logs -f claude-mpm-clean

# View last 100 lines
docker-compose logs --tail=100 claude-mpm-clean
```

## Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove containers and volumes
docker-compose down -v

# Remove everything including images
docker-compose down -v --rmi all
```

## Troubleshooting

### Installation Verification Failed

If the verification script fails:

1. Check the logs for specific error:
   ```bash
   docker-compose logs claude-mpm-clean | grep ERROR
   ```

2. Run interactive container to debug:
   ```bash
   docker-compose --profile interactive run claude-mpm-interactive bash
   ```

3. Inside container, run individual checks:
   ```bash
   python -c "import claude_mpm"
   pip list | grep claude
   python -m claude_mpm.cli --help
   ```

### Permission Issues

If you encounter permission errors:

```bash
# Rebuild with proper permissions
docker-compose build --no-cache claude-mpm-clean
```

### Port Conflicts

If ports 8080 or 5000 are in use (dev profile):

```bash
# Check what's using the ports
lsof -i :8080
lsof -i :5000

# Or modify docker-compose.yml to use different ports
```

## Environment Variables

You can customize behavior with environment variables:

```bash
# Run with debug logging
CLAUDE_MPM_LOG_LEVEL=DEBUG docker-compose up claude-mpm-clean

# Custom configuration
docker-compose run -e CLAUDE_MPM_CONFIG=/custom/path claude-mpm-clean
```

## Testing Different Python Versions

To test with a different Python version, modify the base image in `Dockerfile.clean-install`:

```dockerfile
# For Python 3.10
FROM python:3.10-slim

# For Python 3.12
FROM python:3.12-slim
```

Then rebuild:

```bash
docker-compose build --no-cache
```