#!/bin/bash
# migrate-skills-to-user.sh
# Migrate project skills to user directory for global availability
#
# Usage:
#   ./migrate-skills-to-user.sh [--dry-run] [--force]
#
# Options:
#   --dry-run    Show what would be done without making changes
#   --force      Overwrite existing skills in user directory
#   --help       Show this help message

set -e

# Configuration
PROJECT_SKILLS="/Users/masa/Projects/claude-mpm/.claude/skills"
USER_SKILLS="$HOME/.claude/skills"

# Parse command line arguments
DRY_RUN=false
FORCE=false

for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help|-h)
            grep '^#' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Run with --help for usage information"
            exit 1
            ;;
    esac
done

# Banner
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Claude Code Skills Migration Tool                      ║"
echo "║     Project → User Directory                               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Validate source directory
if [ ! -d "$PROJECT_SKILLS" ]; then
    echo "❌ ERROR: Project skills directory not found: $PROJECT_SKILLS"
    exit 1
fi

# Count skills
skill_count=$(ls -1 "$PROJECT_SKILLS" | wc -l | tr -d ' ')
if [ "$skill_count" -eq 0 ]; then
    echo "⚠️  No skills found in project directory"
    exit 0
fi

echo "📦 Found $skill_count skills in project directory"
echo "📂 Source: $PROJECT_SKILLS"
echo "📂 Target: $USER_SKILLS"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "🔍 DRY RUN MODE - No changes will be made"
    echo ""
fi

# Create user skills directory
if [ "$DRY_RUN" = false ]; then
    mkdir -p "$USER_SKILLS"
    echo "✅ User skills directory ready: $USER_SKILLS"
else
    echo "Would create: $USER_SKILLS"
fi
echo ""

# Counters
migrated=0
skipped=0
overwritten=0

# Process each skill
for skill_dir in "$PROJECT_SKILLS"/*; do
    skill_name=$(basename "$skill_dir")

    # Skip if not a directory
    if [ ! -d "$skill_dir" ]; then
        echo "⏭️  Skipping non-directory: $skill_name"
        continue
    fi

    # Check if skill already exists in user directory
    if [ -d "$USER_SKILLS/$skill_name" ]; then
        if [ "$FORCE" = true ]; then
            if [ "$DRY_RUN" = false ]; then
                rm -rf "$USER_SKILLS/$skill_name"
                cp -r "$skill_dir" "$USER_SKILLS/"
                echo "🔄 Overwritten: $skill_name"
                ((overwritten++))
            else
                echo "Would overwrite: $skill_name"
                ((overwritten++))
            fi
        else
            echo "⚠️  Exists (skipping): $skill_name"
            ((skipped++))
            continue
        fi
    else
        # Copy skill
        if [ "$DRY_RUN" = false ]; then
            cp -r "$skill_dir" "$USER_SKILLS/"
            echo "✅ Migrated: $skill_name"
            ((migrated++))
        else
            echo "Would migrate: $skill_name"
            ((migrated++))
        fi
    fi
done

# Summary
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    Migration Summary                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Results:"
echo "   ✅ Migrated: $migrated skills"
echo "   🔄 Overwritten: $overwritten skills"
echo "   ⏭️  Skipped: $skipped skills (already exist)"
echo ""

if [ "$DRY_RUN" = false ]; then
    total_skills=$(ls -1 "$USER_SKILLS" | wc -l | tr -d ' ')
    echo "📂 User skills directory now contains: $total_skills skills"
    echo "📍 Location: $USER_SKILLS"
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                      NEXT STEPS                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "⚠️  IMPORTANT: Skills are loaded at Claude Code STARTUP ONLY"
    echo ""
    echo "1️⃣  Restart Claude Code:"
    echo "    - Exit Claude Code completely"
    echo "    - Start a new session"
    echo ""
    echo "2️⃣  Verify skills are loaded:"
    echo "    - Run '/skills' command in Claude Code"
    echo "    - Check that all $total_skills skills appear"
    echo ""
    echo "3️⃣  Test in different projects:"
    echo "    - Open different project directories"
    echo "    - Skills should be available everywhere"
    echo ""
    echo "4️⃣  Optional - Clean up project directory:"
    echo "    - Remove skills from: $PROJECT_SKILLS"
    echo "    - Keep only project-specific skills (if any)"
    echo ""
    echo "📚 For more information, see:"
    echo "    docs/research/claude-code-user-skills-persistence-2025-12-22.md"
else
    echo "🔍 DRY RUN COMPLETE - No changes made"
    echo ""
    echo "To perform migration, run:"
    echo "    ./migrate-skills-to-user.sh"
    echo ""
    echo "To overwrite existing skills, run:"
    echo "    ./migrate-skills-to-user.sh --force"
fi

echo ""
echo "✨ Migration script complete!"
