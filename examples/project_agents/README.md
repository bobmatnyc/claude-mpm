# Project Agent Examples

This directory contains examples of project-specific agents that override system agents using the three-tier precedence system.

## Quick Start

1. Copy the `.claude-mpm` directory to your project root
2. Modify the agent files as needed (supports .json, .md, .yaml formats)
3. Run `claude-mpm` - agents are loaded automatically with PROJECT tier precedence

## Directory Structure

```
your-project/
└── .claude-mpm/
    └── agents/
        ├── custom_engineer.json   # Override system engineer
        ├── project_qa.json        # Project-specific QA
        └── security_auditor.json  # New custom agent
```

## Examples Included

### 1. Custom Engineer (`custom_engineer.json`)
- Overrides the system engineer agent
- Adds project-specific coding standards
- Includes custom tool requirements

### 2. Project QA (`project_qa.json`) 
- Customized QA agent for your project
- Specific test requirements and standards
- Integration with project test frameworks

### 3. Security Auditor (`security_auditor.json`)
- New agent type for security auditing
- OWASP compliance checks
- Vulnerability scanning focus

## Usage

After copying to your project:

```bash
# View agent hierarchy to see which agents are active
claude-mpm agents list --by-tier

# Start interactive session with project agents loaded
claude-mpm

# Or in non-interactive mode
claude-mpm run -i "Review the security of this code"
```

Project agents are loaded automatically with highest precedence in the three-tier system.

## Customization

Edit the JSON files to match your project needs:

1. Update the `instructions` field with your requirements
2. Modify `tools` array to include needed capabilities
3. Adjust `model` for performance vs cost tradeoffs
4. Increment `version` when making changes

## Best Practices

1. **Version Control**: Commit your `.claude-mpm/agents/` directory
2. **Documentation**: Document agent purposes and capabilities
3. **Testing**: Test agents thoroughly before team deployment
4. **Consistency**: Maintain consistent naming and versioning