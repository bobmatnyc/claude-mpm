#!/bin/bash
"""
Claude MPM Performance Validation Runner
========================================

Master script to execute all performance benchmarks for TSK-0056 validation.
Runs individual benchmarks and generates a comprehensive performance report.

Usage:
    ./run_performance_validation.sh [--verbose] [--output-dir DIR]
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
VERBOSE=false
OUTPUT_DIR="$(dirname "$0")/results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PYTHON_CMD="python3"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose)
            VERBOSE=true
            shift
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--verbose] [--output-dir DIR]"
            echo ""
            echo "Options:"
            echo "  --verbose      Enable verbose output"
            echo "  --output-dir   Specify output directory for results"
            echo "  --help         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            exit 1
            ;;
    esac
done

# Setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
RESULTS_DIR="$OUTPUT_DIR/$TIMESTAMP"

echo -e "${BLUE}🎯 Claude MPM Performance Validation Suite${NC}"
echo -e "${BLUE}===========================================${NC}"
echo "Timestamp: $(date)"
echo "Results Directory: $RESULTS_DIR"
echo "Project Root: $PROJECT_ROOT"
echo ""

# Create results directory
mkdir -p "$RESULTS_DIR"

# Verbose flag for Python scripts
VERBOSE_FLAG=""
if [ "$VERBOSE" = true ]; then
    VERBOSE_FLAG="--verbose"
fi

# Function to run a benchmark
run_benchmark() {
    local name="$1"
    local script="$2"
    local output_file="$3"
    local description="$4"

    echo -e "${YELLOW}📊 Running $name Benchmark${NC}"
    echo "Description: $description"
    echo "Script: $script"
    echo "Output: $output_file"
    echo ""

    start_time=$(date +%s)

    if cd "$SCRIPT_DIR" && $PYTHON_CMD "$script" $VERBOSE_FLAG --output "$output_file"; then
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        echo -e "${GREEN}✅ $name benchmark completed in ${duration}s${NC}"
        return 0
    else
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        echo -e "${RED}❌ $name benchmark failed after ${duration}s${NC}"
        return 1
    fi
}

# Function to check dependencies
check_dependencies() {
    echo -e "${BLUE}🔍 Checking dependencies...${NC}"

    # Check Python
    if ! command -v $PYTHON_CMD &> /dev/null; then
        echo -e "${RED}❌ Python 3 not found${NC}"
        exit 1
    fi

    # Check claude-mpm installation
    if ! cd "$PROJECT_ROOT" && $PYTHON_CMD -c "import sys; sys.path.insert(0, 'src'); import claude_mpm" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  claude-mpm not properly installed, attempting to add to PYTHONPATH${NC}"
        export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
    fi

    # Check for required Python packages
    local required_packages=("asyncio" "psutil" "statistics")
    for package in "${required_packages[@]}"; do
        if ! $PYTHON_CMD -c "import $package" 2>/dev/null; then
            echo -e "${YELLOW}⚠️  Package $package not available${NC}"
        fi
    done

    echo -e "${GREEN}✅ Dependencies checked${NC}"
    echo ""
}

# Function to generate summary report
generate_summary_report() {
    local summary_file="$RESULTS_DIR/performance_validation_summary.md"

    echo -e "${BLUE}📋 Generating summary report...${NC}"

    cat > "$summary_file" << EOF
# Claude MPM Performance Validation Summary

**Timestamp:** $(date)
**TSK-0056 Validation Results**

## Performance Targets

| Metric | Target | Baseline | Status |
|--------|--------|----------|--------|
| Startup Time | <2 seconds | 3-5 seconds | 🔍 |
| Agent Deployment | <500ms per agent | 1000ms | 🔍 |
| Memory Query | <100ms for 10k entries | 200ms | 🔍 |
| Cache Hit Rate | >50% improvement | 0% | 🔍 |
| Connection Reliability | 40-60% error reduction | 40% failure rate | 🔍 |

## Benchmark Results

EOF

    # Process individual benchmark results
    local overall_status="PASS"
    local total_tests=0
    local passed_tests=0

    for result_file in "$RESULTS_DIR"/*.json; do
        if [ -f "$result_file" ]; then
            local benchmark_name=$(basename "$result_file" .json)
            echo "### $benchmark_name" >> "$summary_file"
            echo "" >> "$summary_file"

            # Try to extract key metrics from JSON
            if command -v jq &> /dev/null; then
                # Use jq for JSON parsing if available
                local status=$(jq -r '.benchmark_metadata.meets_target // false' "$result_file" 2>/dev/null)
                local execution_time=$(jq -r '.benchmark_metadata.execution_time // 0' "$result_file" 2>/dev/null)

                echo "- **Status:** $([ "$status" = "true" ] && echo "✅ PASS" || echo "❌ FAIL")" >> "$summary_file"
                echo "- **Execution Time:** ${execution_time}s" >> "$summary_file"
                echo "- **Details:** See \`$benchmark_name.json\`" >> "$summary_file"
                echo "" >> "$summary_file"

                total_tests=$((total_tests + 1))
                if [ "$status" = "true" ]; then
                    passed_tests=$((passed_tests + 1))
                else
                    overall_status="FAIL"
                fi
            else
                echo "- **Status:** 🔍 See JSON file for details" >> "$summary_file"
                echo "- **Details:** \`$benchmark_name.json\`" >> "$summary_file"
                echo "" >> "$summary_file"
            fi
        fi
    done

    # Add overall summary
    cat >> "$summary_file" << EOF

## Overall Summary

- **Total Tests:** $total_tests
- **Passed:** $passed_tests
- **Failed:** $((total_tests - passed_tests))
- **Overall Status:** $([ "$overall_status" = "PASS" ] && echo "✅ PASS" || echo "❌ FAIL")

## Files Generated

EOF

    # List all generated files
    for file in "$RESULTS_DIR"/*; do
        if [ -f "$file" ]; then
            echo "- \`$(basename "$file")\`" >> "$summary_file"
        fi
    done

    echo "" >> "$summary_file"
    echo "---" >> "$summary_file"
    echo "*Generated by Claude MPM Performance Validation Suite*" >> "$summary_file"

    echo -e "${GREEN}✅ Summary report generated: $summary_file${NC}"
}

# Main execution
main() {
    echo -e "${BLUE}🚀 Starting Performance Validation...${NC}"
    echo ""

    # Check dependencies
    check_dependencies

    # Track overall results
    local failed_benchmarks=0
    local total_benchmarks=0

    # Run individual benchmarks
    echo -e "${BLUE}📊 Running Individual Benchmarks${NC}"
    echo -e "${BLUE}=================================${NC}"
    echo ""

    # Startup Performance Benchmark
    total_benchmarks=$((total_benchmarks + 1))
    if ! run_benchmark "Startup Performance" \
                      "startup_benchmark.py" \
                      "$RESULTS_DIR/startup_benchmark.json" \
                      "Measure application startup time across different modes"; then
        failed_benchmarks=$((failed_benchmarks + 1))
    fi
    echo ""

    # Cache Performance Benchmark
    total_benchmarks=$((total_benchmarks + 1))
    if ! run_benchmark "Cache Performance" \
                      "cache_benchmark.py" \
                      "$RESULTS_DIR/cache_benchmark.json" \
                      "Validate cache effectiveness and hit rates"; then
        failed_benchmarks=$((failed_benchmarks + 1))
    fi
    echo ""

    # Connection Performance Benchmark
    total_benchmarks=$((total_benchmarks + 1))
    if ! run_benchmark "Connection Performance" \
                      "connection_benchmark.py" \
                      "$RESULTS_DIR/connection_benchmark.json" \
                      "Test connection pool reliability and error reduction"; then
        failed_benchmarks=$((failed_benchmarks + 1))
    fi
    echo ""

    # Comprehensive Performance Validation
    total_benchmarks=$((total_benchmarks + 1))
    if ! run_benchmark "Comprehensive Validation" \
                      "performance_validation_suite.py" \
                      "$RESULTS_DIR/comprehensive_validation.json" \
                      "Complete validation of all performance targets"; then
        failed_benchmarks=$((failed_benchmarks + 1))
    fi
    echo ""

    # Generate summary report
    generate_summary_report

    # Final results
    local passed_benchmarks=$((total_benchmarks - failed_benchmarks))

    echo -e "${BLUE}🎯 PERFORMANCE VALIDATION COMPLETE${NC}"
    echo -e "${BLUE}===================================${NC}"
    echo "Timestamp: $(date)"
    echo "Results Directory: $RESULTS_DIR"
    echo "Total Benchmarks: $total_benchmarks"
    echo "Passed: $passed_benchmarks"
    echo "Failed: $failed_benchmarks"

    if [ $failed_benchmarks -eq 0 ]; then
        echo -e "${GREEN}✅ ALL BENCHMARKS PASSED${NC}"
        echo ""
        echo -e "${GREEN}🎉 TSK-0056 Performance Targets Validated!${NC}"
        exit 0
    else
        echo -e "${RED}❌ $failed_benchmarks BENCHMARK(S) FAILED${NC}"
        echo ""
        echo -e "${RED}🔧 Performance targets not fully met. See results for details.${NC}"
        exit 1
    fi
}

# Run main function
main "$@"
