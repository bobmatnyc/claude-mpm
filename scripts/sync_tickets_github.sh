#!/bin/bash
# Script to help sync AI Trackdown tickets with GitHub issues

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "AI Trackdown to GitHub Sync Helper"
echo "=================================="

# Function to extract ticket info
get_ticket_info() {
    local ticket_id=$1
    ./ticket view "$ticket_id" 2>/dev/null || echo "Ticket not found"
}

# Function to create GitHub issue from ticket
create_github_issue() {
    local ticket_id=$1
    local title=$2
    local description=$3
    local priority=$4
    local epic_ref=$5
    
    # Map priority
    local gh_priority="priority:medium"
    case $priority in
        "critical") gh_priority="priority:critical" ;;
        "high") gh_priority="priority:high" ;;
        "medium") gh_priority="priority:medium" ;;
    esac
    
    # Create issue body
    local body="## Description
$description

## Related to
- AI Trackdown: $ticket_id"
    
    if [ -n "$epic_ref" ]; then
        body="$body
- EPIC: #$epic_ref"
    fi
    
    body="$body

## Priority
$priority"
    
    # Create the issue
    gh issue create --title "$title" --body "$body" --label "enhancement,multi-agent,$gh_priority"
}

# Function to update ticket with GitHub reference
update_ticket_with_github() {
    local ticket_id=$1
    local github_issue=$2
    
    echo -e "${YELLOW}Note: Manual update needed for $ticket_id${NC}"
    echo "Add to ticket description: 'GitHub Issue: #$github_issue'"
    echo "./ticket update $ticket_id -d \"Updated description with GitHub Issue: #$github_issue\""
}

# Main menu
while true; do
    echo ""
    echo "Options:"
    echo "1. View sync status"
    echo "2. Create GitHub issue from ticket"
    echo "3. Update ticket with GitHub reference"
    echo "4. Exit"
    
    read -p "Select option: " option
    
    case $option in
        1)
            echo -e "\n${GREEN}Current GitHub Issues:${NC}"
            gh issue list --label "multi-agent" --limit 20
            echo -e "\n${GREEN}Current AI Trackdown Tickets:${NC}"
            ./ticket list | grep -E "(EP-|ISS-)" || echo "No tickets found"
            ;;
        2)
            read -p "Enter ticket ID (e.g., ISS-0011): " ticket_id
            read -p "Enter issue title: " title
            read -p "Enter description: " description
            read -p "Enter priority (critical/high/medium): " priority
            read -p "Enter EPIC GitHub issue # (or leave empty): " epic_ref
            
            create_github_issue "$ticket_id" "$title" "$description" "$priority" "$epic_ref"
            ;;
        3)
            read -p "Enter ticket ID: " ticket_id
            read -p "Enter GitHub issue number: " github_issue
            
            update_ticket_with_github "$ticket_id" "$github_issue"
            ;;
        4)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option${NC}"
            ;;
    esac
done