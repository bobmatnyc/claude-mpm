#!/bin/bash
# Complete Lightweight SWE Benchmark Execution
# Runs full benchmark pipeline: test selection → execution → scoring → display generation

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR"
SCRIPTS_DIR="$BASE_DIR/scripts"
RESULTS_DIR="$BASE_DIR/results/lightweight"

# Banner
echo -e "${PURPLE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${PURPLE}   🚀 LIGHTWEIGHT SWE BENCHMARK - COMPLETE EXECUTION PIPELINE   ${NC}"
echo -e "${PURPLE}════════════════════════════════════════════════════════════════${NC}"
echo
echo -e "${CYAN}Base Directory:${NC} $BASE_DIR"
echo -e "${CYAN}Results Directory:${NC} $RESULTS_DIR"
echo
echo -e "${PURPLE}────────────────────────────────────────────────────────────────${NC}"
echo

# Step 1: Ensure test suites are generated
echo -e "${BLUE}📋 Step 1: Checking test suite selection...${NC}"
if [ ! -d "$BASE_DIR/benchmarks/lightweight" ] || [ -z "$(ls -A $BASE_DIR/benchmarks/lightweight 2>/dev/null)" ]; then
    echo -e "${YELLOW}   ⚠ Lightweight test suites not found. Generating...${NC}"
    cd "$BASE_DIR"
    python3 "$SCRIPTS_DIR/select_lightweight_tests.py"
    echo -e "${GREEN}   ✓ Test suites generated${NC}"
else
    echo -e "${GREEN}   ✓ Test suites already exist${NC}"
    echo -e "${CYAN}   Found: $(ls -1 $BASE_DIR/benchmarks/lightweight/*.json 2>/dev/null | wc -l) test suites${NC}"
fi
echo

# Step 2: Run benchmark
echo -e "${BLUE}🎯 Step 2: Running lightweight benchmark...${NC}"
echo -e "${CYAN}   Executing 84 tests across 7 agents (12 tests each)${NC}"
echo
cd "$BASE_DIR"
python3 "$SCRIPTS_DIR/run_lightweight_benchmark.py"
echo
echo -e "${GREEN}   ✓ Benchmark execution complete${NC}"
echo

# Step 3: Calculate scores
echo -e "${BLUE}📊 Step 3: Calculating multi-dimensional scores...${NC}"
echo -e "${CYAN}   Applying difficulty weighting and dimension analysis${NC}"
echo
cd "$BASE_DIR"
python3 "$SCRIPTS_DIR/score_lightweight_results.py"
echo
echo -e "${GREEN}   ✓ Scoring complete${NC}"
echo

# Step 4: Generate displays
echo -e "${BLUE}🎨 Step 4: Generating display formats...${NC}"
echo -e "${CYAN}   Creating markdown, badges, HTML dashboard, and ASCII charts${NC}"
echo
cd "$BASE_DIR"
python3 "$SCRIPTS_DIR/generate_benchmark_display.py"
echo
echo -e "${GREEN}   ✓ Display generation complete${NC}"
echo

# Step 5: Summary
echo -e "${PURPLE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ BENCHMARK COMPLETE!${NC}"
echo -e "${PURPLE}════════════════════════════════════════════════════════════════${NC}"
echo
echo -e "${CYAN}📂 Results Location:${NC} $RESULTS_DIR"
echo
echo -e "${YELLOW}Generated Files:${NC}"
echo -e "   ${GREEN}●${NC} benchmark_results.json  (Raw benchmark data)"
echo -e "   ${GREEN}●${NC} scores.json            (Detailed scoring data)"
echo -e "   ${GREEN}●${NC} scoring_report.txt     (Text report)"
echo -e "   ${GREEN}●${NC} benchmark_report.md    (Markdown report)"
echo -e "   ${GREEN}●${NC} badges.md              (Badge markdown)"
echo -e "   ${GREEN}●${NC} dashboard.html         (HTML dashboard)"
echo -e "   ${GREEN}●${NC} leaderboard.txt        (ASCII leaderboard)"
echo
echo -e "${YELLOW}Quick Views:${NC}"
echo -e "   ${CYAN}View leaderboard:${NC} cat $RESULTS_DIR/leaderboard.txt"
echo -e "   ${CYAN}View report:${NC}      less $RESULTS_DIR/scoring_report.txt"
echo -e "   ${CYAN}View dashboard:${NC}   open $RESULTS_DIR/dashboard.html"
echo
echo -e "${PURPLE}════════════════════════════════════════════════════════════════${NC}"
echo

# Display leaderboard
if [ -f "$RESULTS_DIR/leaderboard.txt" ]; then
    echo -e "${BLUE}🏆 Quick Leaderboard Preview:${NC}"
    echo
    cat "$RESULTS_DIR/leaderboard.txt"
    echo
fi

# Exit successfully
exit 0
