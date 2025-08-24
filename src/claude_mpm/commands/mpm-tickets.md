# mpm-tickets

Create and manage tickets using aitrackdown

## Usage

Use this command to create and manage tickets (epics, issues, tasks) through aitrackdown CLI integration.

## Commands

### Create tickets
```bash
# Create an epic
aitrackdown create epic "Title" --description "Description"

# Create an issue  
aitrackdown create issue "Title" --description "Description"

# Create a task
aitrackdown create task "Title" --description "Description"

# Create task under an issue
aitrackdown create task "Title" --issue ISS-0001
```

### View tickets
```bash
# Show all tasks
aitrackdown status tasks

# Show specific ticket
aitrackdown show ISS-0001
```

### Update tickets
```bash
# Change status
aitrackdown transition ISS-0001 in-progress
aitrackdown transition ISS-0001 done

# Add comment
aitrackdown comment ISS-0001 "Your comment"
```

### Search tickets
```bash
aitrackdown search tasks "keyword"
```

## Ticket Types

- **EP-XXXX**: Epics (major initiatives)
- **ISS-XXXX**: Issues (bugs, features, user requests)  
- **TSK-XXXX**: Tasks (individual work items)

## Workflow States

Valid transitions:
- `open` → `in-progress` → `ready` → `tested` → `done`
- Any state → `waiting` (when blocked)
- Any state → `closed` (to close)

## Examples

### Bug Report Flow
```bash
# Create issue for bug
aitrackdown create issue "Login bug" --description "Users can't login" --severity high

# Create investigation task
aitrackdown create task "Investigate login bug" --issue ISS-0001

# Update status
aitrackdown transition TSK-0001 in-progress
aitrackdown comment TSK-0001 "Found the issue"

# Complete
aitrackdown transition TSK-0001 done
aitrackdown transition ISS-0001 done
```

### Feature Implementation
```bash
# Create epic
aitrackdown create epic "OAuth2 Support"

# Create issues
aitrackdown create issue "Google OAuth2" --description "Add Google auth"
aitrackdown create issue "GitHub OAuth2" --description "Add GitHub auth"

# Create tasks
aitrackdown create task "Design OAuth flow" --issue ISS-0001
aitrackdown create task "Implement Google client" --issue ISS-0001
```

## Tips

- Always use aitrackdown directly (not claude-mpm tickets)
- Check ticket exists with `show` before updating
- Add comments to document progress
- Use `--severity` for bugs, `--priority` for features
- Associate tasks with issues using `--issue`