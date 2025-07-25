# Ticket Wrapper Documentation

The `ticket` command is a simplified wrapper around ai-trackdown-pytools that makes creating and managing tickets easier.

## Installation

The ticket wrapper is already included in the `scripts/` directory and has a convenience alias at the project root.

### Within the Project
```bash
# Use the top-level alias (recommended)
./ticket create "My ticket"

# Or use the script directly
./scripts/ticket create "My ticket"
```

### Global Usage Options

### Option 1: Add to PATH
```bash
export PATH="$PATH:/path/to/claude-mpm/scripts"
```

### Option 2: Create an alias
Add this to your shell configuration file (`~/.bashrc`, `~/.zshrc`, etc.):
```bash
alias ticket='/path/to/claude-mpm/scripts/ticket'
```

### Option 3: Create a symlink
```bash
ln -s /path/to/claude-mpm/scripts/ticket /usr/local/bin/ticket
```

## Usage

### Creating Tickets

```bash
# Basic task creation
ticket create "Implement new feature"

# Create a bug with high priority
ticket create "Fix critical login bug" -t bug -p high

# Create a feature with description
ticket create "Add dark mode" -t feature -d "Users have requested dark mode support for better night usage"

# Create with tags
ticket create "Update dependencies" --tags "maintenance,security"
```

### Listing Tickets

```bash
# List recent tickets (default: 10)
ticket list

# List more tickets with details
ticket list -v --limit 20

# Quick list of 5 most recent
ticket list --limit 5
```

### Viewing Tickets

```bash
# View a specific ticket
ticket view TSK-0001

# View with metadata (verbose)
ticket view TSK-0001 -v
```

### Updating Tickets

```bash
# Update status
ticket update TSK-0001 -s in_progress

# Update priority
ticket update TSK-0001 -p critical

# Assign to someone
ticket update TSK-0001 -a "john.doe"

# Update multiple fields
ticket update TSK-0001 -s in_progress -p high --tags "urgent,backend"
```

### Closing Tickets

```bash
# Close a ticket
ticket close TSK-0001
```

## Ticket Types

- **task** (default) - General tasks
- **bug** - Bug reports
- **feature** - Feature requests
- **issue** - General issues

## Priority Levels

- **low**
- **medium** (default)
- **high**
- **critical**

## Examples

### Common Workflows

1. **Quick bug report**:
   ```bash
   ticket create "Login button not working" -t bug -p high
   ```

2. **Feature request with details**:
   ```bash
   ticket create "Add export to PDF" -t feature -d "Users need to export reports as PDF files for sharing"
   ```

3. **Check your work**:
   ```bash
   ticket list -v
   ```

4. **Update progress**:
   ```bash
   ticket update TSK-0005 -s in_progress
   ```

5. **Complete a task**:
   ```bash
   ticket close TSK-0005
   ```

## Integration with claude-mpm

The ticket wrapper integrates seamlessly with claude-mpm:

- Uses the same TicketManager backend
- Tickets created with the wrapper appear in `claude-mpm tickets`
- Consistent ticket IDs and formatting
- Works with the same project structure

## Tips

1. **Keep titles concise** - Use the description field for details
2. **Use appropriate types** - This helps with filtering and reporting
3. **Set realistic priorities** - Reserve "critical" for truly urgent issues
4. **Add tags** - Makes finding related tickets easier
5. **Update status** - Keep tickets current as you work on them