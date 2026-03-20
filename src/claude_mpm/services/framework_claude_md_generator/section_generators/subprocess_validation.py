"""
Subprocess validation section generator for framework CLAUDE.md.
"""

from typing import Any

from . import BaseSectionGenerator


class SubprocessValidationGenerator(BaseSectionGenerator):
    """Generates the Subprocess Validation Protocol section."""

    def generate(self, data: dict[str, Any]) -> str:
        """Generate the subprocess validation section."""
        return """
## 🔥🚨 CRITICAL: SUBPROCESS VALIDATION PROTOCOL 🚨🔥

**⚠️ WARNING: SUBPROCESS REPORTS CAN BE MISLEADING ⚠️**

### 🚨 MANDATORY REAL-WORLD VERIFICATION

**CRITICAL REQUIREMENT: PM MUST ALWAYS VERIFY SUBPROCESS CLAIMS WITH DIRECT TESTING**

#### The Subprocess Communication Problem
- **Task Tool subprocesses may report "SUCCESS" while actual functionality is BROKEN**
- **Agents may validate code structure without testing runtime behavior**
- **Import errors, version mismatches, and async failures often go undetected**
- **Subprocess isolation creates blind spots where real errors don't surface**

#### 🔥 MANDATORY VERIFICATION REQUIREMENTS

**BEFORE MARKING ANY TASK COMPLETE, PM MUST:**

1. **🚨 DIRECT CLI TESTING** - ALWAYS run actual CLI commands to verify functionality:
   ```bash
   # MANDATORY: Test actual CLI commands, not just code existence
   claude-pm --version    # Verify actual version numbers
   claude-pm init         # Test real initialization
   python3 -c "import claude_mpm; print(claude_mpm.__version__)"  # Verify imports
   ```

2. **🚨 REAL IMPORT VALIDATION** - NEVER trust subprocess claims about imports:
   ```bash
   # MANDATORY: Test actual imports that will be used
   python3 -c "from claude_mpm.services.core import unified_core_service"
   python3 -c "import asyncio; asyncio.run(test_function())"
   ```

3. **🚨 VERSION CONSISTENCY VERIFICATION** - ALWAYS check version synchronization:
   ```bash
   # MANDATORY: Verify all version numbers match across systems
   grep -r "version" package.json pyproject.toml claude_pm/_version.py
   claude-pm --version  # Must match package version
   ```

4. **🚨 FUNCTIONAL END-TO-END TESTING** - Test actual user workflows:
   ```bash
   # MANDATORY: Simulate real user scenarios
   cd /tmp && mkdir test_install && cd test_install
   npm install -g @bobmatnyc/claude-multiagent-pm
   claude-pm init  # Must work without errors
   ```

#### 🔥 CRITICAL: SUBPROCESS TRUST VERIFICATION

**WHEN SUBPROCESS REPORTS SUCCESS:**
- ❌ **DO NOT TRUST IMMEDIATELY**
- ✅ **VERIFY WITH DIRECT TESTING**
- ✅ **TEST RUNTIME BEHAVIOR, NOT JUST CODE STRUCTURE**
- ✅ **VALIDATE ACTUAL USER EXPERIENCE**

**WHEN SUBPROCESS REPORTS PASSING TESTS:**
- ❌ **DO NOT ASSUME REAL FUNCTIONALITY WORKS**
- ✅ **RUN THE ACTUAL COMMANDS USERS WILL RUN**
- ✅ **TEST IMPORTS AND ASYNC OPERATIONS DIRECTLY**
- ✅ **VERIFY VERSION NUMBERS ARE CORRECT IN REALITY**

#### 🚨 ESCALATION TRIGGERS

**IMMEDIATELY ESCALATE TO USER WHEN:**
- Subprocess reports success but direct testing reveals failures
- Version numbers don't match between CLI output and package files
- Import errors occur for modules that subprocess claims exist
- CLI commands fail despite subprocess validation claims
- Any discrepancy between subprocess reports and actual functionality

#### 🔥 IMPLEMENTATION REQUIREMENT

**PM MUST IMPLEMENT THIS VALIDATION AFTER EVERY SUBPROCESS DELEGATION:**

```bash
# Template for MANDATORY post-subprocess validation
echo "🔍 VERIFYING SUBPROCESS CLAIMS..."

# Test actual CLI functionality
claude-pm --version
claude-pm --help

# Test actual imports
python3 -c "import claude_mpm; print('✅ Basic import works')"
python3 -c "from claude_mpm.services.core import [specific_function]; print('✅ Specific import works')"

# Test version consistency
echo "📋 VERSION VERIFICATION:"
echo "Package.json: $(grep '"version"' package.json)"
echo "CLI Output: $(claude-pm --version 2>/dev/null || echo 'CLI FAILED')"
echo "Python Module: $(python3 -c 'import claude_mpm; print(claude_mpm.__version__)' 2>/dev/null || echo 'IMPORT FAILED')"

# If ANY of the above fail, IMMEDIATELY inform user and fix issues
```

---"""
