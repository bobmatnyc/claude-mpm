# /pm:daily-standup - Daily Project Management Standup

## Purpose
Automated daily standup process to review progress, identify blockers, and plan the day's work.

## Usage
```
/pm:daily-standup [--detailed] [--milestone M01|M02|M03]
```

## Implementation Logic

### 1. Previous Day Review
- Check git commits across all active projects
- Identify completed tasks from todo lists
- Review any failed CI/CD processes
- Summarize progress against current sprint goals

### 2. Current Status Assessment
- Evaluate project health indicators
- Check for dependency blockers
- Review team capacity and availability
- Identify urgent issues requiring attention

### 3. Today's Planning
- Generate prioritized task list from tickets/issues
- Suggest focus areas based on milestone priorities
- Identify collaboration opportunities
- Recommend time allocation

### 4. Output Format
```
# Daily Standup - [Date]

## Yesterday's Accomplishments
- [Project]: [Completed tasks]
- [Cross-project]: [Coordination activities]

## Today's Priority Tasks
1. [High Priority]: [Task description]
2. [Medium Priority]: [Task description]
3. [Low Priority]: [Task description]

## Blockers & Dependencies
- [Blocker]: [Description and resolution plan]

## Focus Recommendations
- Primary focus: [Milestone/Project]
- Time allocation: [Breakdown]
- Collaboration needs: [Team coordination]
```

## Integration Points
- Reads from git-portfolio-manager for project status
- Checks ai-code-review for quality blockers
- References milestone requirements and sprint goals
- Updates project tracking metrics