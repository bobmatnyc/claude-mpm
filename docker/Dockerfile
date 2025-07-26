# Test Dockerfile for claude-mpm with hooks
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy the entire project
COPY . .

# Install claude-mpm
RUN pip install --upgrade pip && \
    pip install -e .

# Create a test script to verify hook installation
RUN mkdir -p /root/.claude/

# Copy hook configuration to the expected location (if exists)
# Note: These files might not exist in all environments

# Create test script
RUN echo '#!/bin/bash\n\
echo "=== Testing claude-mpm installation ==="\n\
echo ""\n\
echo "1. Python path: $(which python)"\n\
echo ""\n\
echo "2. Claude-mpm version:"\n\
python -c "import claude_mpm; print(claude_mpm.__version__)"\n\
echo ""\n\
echo "3. Package location:"\n\
python -c "import claude_mpm; print(claude_mpm.__file__)"\n\
echo ""\n\
echo "4. Hook files in installed package:"\n\
python -c "import claude_mpm; import os; pkg_dir = os.path.dirname(claude_mpm.__file__); hook_dir = os.path.join(pkg_dir, \"hooks\", \"claude_hooks\"); print(\"Hook dir:\", hook_dir); print(\"Files:\", os.listdir(hook_dir) if os.path.exists(hook_dir) else \"Not found\")"\n\
echo ""\n\
echo "5. Hook handler location:"\n\
find /usr/local/lib -name "hook_handler.py" -path "*/claude_hooks/*" 2>/dev/null || echo "Not found in /usr/local/lib"\n\
find /app -name "hook_handler.py" -path "*/claude_hooks/*" 2>/dev/null || echo "Not found in /app"\n\
echo ""\n\
echo "6. Hook wrapper location:"\n\
find /usr/local/lib -name "hook_wrapper.sh" -path "*/claude_hooks/*" 2>/dev/null || echo "Not found in /usr/local/lib"\n\
find /app -name "hook_wrapper.sh" -path "*/claude_hooks/*" 2>/dev/null || echo "Not found in /app"\n\
echo ""\n\
echo "7. Testing hook import:"\n\
python -c "from claude_mpm.hooks.claude_hooks import hook_handler; print(\"✓ Hook handler imported successfully\")"\n\
echo ""\n\
echo "8. Testing hook installation script:"\n\
python /app/scripts/install_hooks.py\n\
' > /test_installation.sh && chmod +x /test_installation.sh

# Set entrypoint
ENTRYPOINT ["/bin/bash"]
CMD ["/test_installation.sh"]