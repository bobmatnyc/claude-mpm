#!/bin/bash

# Memory Guardian Test Suite Runner
# Comprehensive test execution script for Memory Guardian System

set -e  # Exit on any error

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PATH="$PROJECT_ROOT/venv"
PYTHON_CMD=""
PYTEST_CMD=""

# Test configuration
RUN_UNIT_TESTS=true
RUN_INTEGRATION_TESTS=true
RUN_E2E_TESTS=true
RUN_PERFORMANCE_TESTS=true
RUN_STRESS_TESTS=true
GENERATE_COVERAGE=true
GENERATE_REPORTS=true
VERBOSE=false
PARALLEL_JOBS=4
TEST_TIMEOUT=3600  # 1 hour total timeout

# Output configuration
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
RESULTS_DIR="$PROJECT_ROOT/test-results/memory_guardian_$TIMESTAMP"
COVERAGE_DIR="$RESULTS_DIR/coverage"
LOG_FILE="$RESULTS_DIR/test_execution.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')] ✓${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] ⚠${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%H:%M:%S')] ✗${NC} $1" | tee -a "$LOG_FILE"
}

log_section() {
    echo ""
    echo -e "${PURPLE}========================================${NC}" | tee -a "$LOG_FILE"
    echo -e "${PURPLE} $1${NC}" | tee -a "$LOG_FILE"
    echo -e "${PURPLE}========================================${NC}" | tee -a "$LOG_FILE"
    echo ""
}

# Print usage information
usage() {
    cat << EOF
Memory Guardian Test Suite Runner

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --unit-only         Run only unit tests
    --integration-only  Run only integration tests
    --e2e-only          Run only E2E tests
    --performance-only  Run only performance tests
    --stress-only       Run only stress tests
    --no-coverage       Skip coverage generation
    --no-reports        Skip report generation
    --verbose, -v       Verbose output
    --parallel JOBS     Number of parallel jobs (default: 4)
    --timeout SECONDS   Test timeout in seconds (default: 3600)
    --help, -h          Show this help message

EXAMPLES:
    # Run complete test suite
    $0

    # Run only integration and E2E tests with verbose output
    $0 --integration-only --e2e-only --verbose

    # Run performance tests with custom timeout
    $0 --performance-only --timeout 1800

    # Run stress tests without coverage
    $0 --stress-only --no-coverage

ENVIRONMENT:
    The script will automatically detect and use:
    - Virtual environment at $VENV_PATH
    - System Python if virtual environment not found
    - pytest-xvs for parallel execution
    - pytest-cov for coverage reporting

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --unit-only)
                RUN_UNIT_TESTS=true
                RUN_INTEGRATION_TESTS=false
                RUN_E2E_TESTS=false
                RUN_PERFORMANCE_TESTS=false
                RUN_STRESS_TESTS=false
                shift
                ;;
            --integration-only)
                RUN_UNIT_TESTS=false
                RUN_INTEGRATION_TESTS=true
                RUN_E2E_TESTS=false
                RUN_PERFORMANCE_TESTS=false
                RUN_STRESS_TESTS=false
                shift
                ;;
            --e2e-only)
                RUN_UNIT_TESTS=false
                RUN_INTEGRATION_TESTS=false
                RUN_E2E_TESTS=true
                RUN_PERFORMANCE_TESTS=false
                RUN_STRESS_TESTS=false
                shift
                ;;
            --performance-only)
                RUN_UNIT_TESTS=false
                RUN_INTEGRATION_TESTS=false
                RUN_E2E_TESTS=false
                RUN_PERFORMANCE_TESTS=true
                RUN_STRESS_TESTS=false
                shift
                ;;
            --stress-only)
                RUN_UNIT_TESTS=false
                RUN_INTEGRATION_TESTS=false
                RUN_E2E_TESTS=false
                RUN_PERFORMANCE_TESTS=false
                RUN_STRESS_TESTS=true
                shift
                ;;
            --no-coverage)
                GENERATE_COVERAGE=false
                shift
                ;;
            --no-reports)
                GENERATE_REPORTS=false
                shift
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --parallel)
                PARALLEL_JOBS="$2"
                shift 2
                ;;
            --timeout)
                TEST_TIMEOUT="$2"
                shift 2
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

# Setup environment
setup_environment() {
    log_section "Setting Up Test Environment"

    # Create results directory
    mkdir -p "$RESULTS_DIR"
    mkdir -p "$COVERAGE_DIR"

    # Initialize log file
    touch "$LOG_FILE"

    log "Results directory: $RESULTS_DIR"
    log "Project root: $PROJECT_ROOT"

    # Detect Python environment
    if [[ -f "$VENV_PATH/bin/activate" ]]; then
        log "Activating virtual environment: $VENV_PATH"
        source "$VENV_PATH/bin/activate"
        PYTHON_CMD="$VENV_PATH/bin/python"
        PYTEST_CMD="$VENV_PATH/bin/pytest"
    elif [[ -f "$VENV_PATH/Scripts/activate" ]]; then
        # Windows virtual environment
        log "Activating Windows virtual environment: $VENV_PATH"
        source "$VENV_PATH/Scripts/activate"
        PYTHON_CMD="$VENV_PATH/Scripts/python"
        PYTEST_CMD="$VENV_PATH/Scripts/pytest"
    else
        log_warning "Virtual environment not found, using system Python"
        PYTHON_CMD="python3"
        PYTEST_CMD="pytest"
    fi

    # Verify Python and pytest
    if ! command -v "$PYTHON_CMD" &> /dev/null; then
        log_error "Python not found: $PYTHON_CMD"
        exit 1
    fi

    if ! command -v "$PYTEST_CMD" &> /dev/null; then
        log_error "pytest not found: $PYTEST_CMD"
        log "Installing pytest..."
        "$PYTHON_CMD" -m pip install pytest pytest-asyncio pytest-cov pytest-xdist
        PYTEST_CMD="$PYTHON_CMD -m pytest"
    fi

    # Verify Memory Guardian modules can be imported
    cd "$PROJECT_ROOT"
    if ! "$PYTHON_CMD" -c "import sys; sys.path.insert(0, 'src'); from claude_mpm.services.infrastructure.memory_guardian import MemoryGuardian" 2>/dev/null; then
        log_error "Cannot import Memory Guardian modules"
        log "Make sure the project is properly installed:"
        log "  pip install -e ."
        exit 1
    fi

    log_success "Environment setup complete"
    log "Python: $("$PYTHON_CMD" --version)"
    log "pytest: $("$PYTEST_CMD" --version | head -n1)"
}

# Check system requirements
check_requirements() {
    log_section "Checking System Requirements"

    # Check Python version
    python_version=$("$PYTHON_CMD" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    log "Python version: $python_version"

    if [[ $(echo "$python_version >= 3.8" | bc -l) -eq 0 ]]; then
        log_error "Python 3.8 or higher required, found $python_version"
        exit 1
    fi

    # Check available memory
    if command -v free &> /dev/null; then
        available_memory=$(free -g | awk '/^Mem:/{print $7}')
        log "Available memory: ${available_memory}GB"

        if [[ $available_memory -lt 2 ]]; then
            log_warning "Low available memory (${available_memory}GB). Some tests may fail or be slow."
        fi
    fi

    # Check disk space
    available_space=$(df "$PROJECT_ROOT" | awk 'NR==2 {print int($4/1024/1024)}')
    log "Available disk space: ${available_space}GB"

    if [[ $available_space -lt 1 ]]; then
        log_warning "Low disk space (${available_space}GB). Large state file tests may fail."
    fi

    # Check required packages
    required_packages=("psutil" "asyncio")
    for package in "${required_packages[@]}"; do
        if ! "$PYTHON_CMD" -c "import $package" 2>/dev/null; then
            log_warning "Required package not found: $package"
            log "Installing $package..."
            "$PYTHON_CMD" -m pip install "$package"
        fi
    done

    log_success "System requirements check complete"
}

# Build pytest command with common options
build_pytest_cmd() {
    local test_path="$1"
    local output_file="$2"
    local extra_args="$3"

    cmd="$PYTEST_CMD"

    # Add basic options
    cmd="$cmd --tb=short"
    cmd="$cmd --durations=10"
    cmd="$cmd --junitxml=$output_file"

    # Add verbose output if requested
    if [[ "$VERBOSE" == "true" ]]; then
        cmd="$cmd -v -s"
    fi

    # Add parallel execution for appropriate tests
    if [[ "$PARALLEL_JOBS" -gt 1 ]] && [[ "$test_path" != *"stress"* ]]; then
        cmd="$cmd -n $PARALLEL_JOBS"
    fi

    # Add coverage if requested and not performance/stress tests
    if [[ "$GENERATE_COVERAGE" == "true" ]] && [[ "$test_path" != *"performance"* ]] && [[ "$test_path" != *"stress"* ]]; then
        cmd="$cmd --cov=claude_mpm.services.infrastructure.memory_guardian"
        cmd="$cmd --cov=claude_mpm.services.infrastructure.restart_protection"
        cmd="$cmd --cov=claude_mpm.services.infrastructure.state_manager"
        cmd="$cmd --cov=claude_mpm.services.infrastructure.health_monitor"
        cmd="$cmd --cov=claude_mpm.services.infrastructure.graceful_degradation"
        cmd="$cmd --cov-report=xml:$COVERAGE_DIR/coverage_$(basename "$output_file" .xml).xml"
        cmd="$cmd --cov-report=html:$COVERAGE_DIR/html_$(basename "$output_file" .xml)"
    fi

    # Add extra arguments
    if [[ -n "$extra_args" ]]; then
        cmd="$cmd $extra_args"
    fi

    # Add test path
    cmd="$cmd $test_path"

    echo "$cmd"
}

# Run unit tests
run_unit_tests() {
    if [[ "$RUN_UNIT_TESTS" != "true" ]]; then
        return 0
    fi

    log_section "Running Unit Tests"

    local test_path="$PROJECT_ROOT/tests/services/infrastructure/test_memory_guardian.py"
    local output_file="$RESULTS_DIR/unit_tests.xml"

    if [[ ! -f "$test_path" ]]; then
        log_warning "Unit test file not found: $test_path"
        return 1
    fi

    local cmd=$(build_pytest_cmd "$test_path" "$output_file" "--timeout=300")

    log "Executing: $cmd"

    if eval "$cmd"; then
        log_success "Unit tests passed"
        return 0
    else
        log_error "Unit tests failed"
        return 1
    fi
}

# Run integration tests
run_integration_tests() {
    if [[ "$RUN_INTEGRATION_TESTS" != "true" ]]; then
        return 0
    fi

    log_section "Running Integration Tests"

    local test_path="$PROJECT_ROOT/tests/integration/test_memory_guardian_integration.py"
    local output_file="$RESULTS_DIR/integration_tests.xml"

    if [[ ! -f "$test_path" ]]; then
        log_warning "Integration test file not found: $test_path"
        return 1
    fi

    local cmd=$(build_pytest_cmd "$test_path" "$output_file" "--timeout=600")

    log "Executing: $cmd"

    if eval "$cmd"; then
        log_success "Integration tests passed"
        return 0
    else
        log_error "Integration tests failed"
        return 1
    fi
}

# Run E2E tests
run_e2e_tests() {
    if [[ "$RUN_E2E_TESTS" != "true" ]]; then
        return 0
    fi

    log_section "Running End-to-End Tests"

    local test_path="$PROJECT_ROOT/tests/e2e/test_memory_guardian_e2e.py"
    local output_file="$RESULTS_DIR/e2e_tests.xml"

    if [[ ! -f "$test_path" ]]; then
        log_warning "E2E test file not found: $test_path"
        return 1
    fi

    local cmd=$(build_pytest_cmd "$test_path" "$output_file" "--timeout=900")

    log "Executing: $cmd"

    if eval "$cmd"; then
        log_success "E2E tests passed"
        return 0
    else
        log_error "E2E tests failed"
        return 1
    fi
}

# Run performance tests
run_performance_tests() {
    if [[ "$RUN_PERFORMANCE_TESTS" != "true" ]]; then
        return 0
    fi

    log_section "Running Performance Tests"

    local test_path="$PROJECT_ROOT/tests/performance/test_memory_guardian_perf.py"
    local output_file="$RESULTS_DIR/performance_tests.xml"

    if [[ ! -f "$test_path" ]]; then
        log_warning "Performance test file not found: $test_path"
        return 1
    fi

    # Performance tests run single-threaded with longer timeout
    local cmd=$(build_pytest_cmd "$test_path" "$output_file" "--timeout=1800 -n 1")

    log "Executing: $cmd"
    log_warning "Performance tests may take a while..."

    if eval "$cmd"; then
        log_success "Performance tests completed"
        return 0
    else
        log_error "Performance tests failed"
        return 1
    fi
}

# Run stress tests
run_stress_tests() {
    if [[ "$RUN_STRESS_TESTS" != "true" ]]; then
        return 0
    fi

    log_section "Running Stress Tests"

    local test_path="$PROJECT_ROOT/tests/stress/test_memory_guardian_stress.py"
    local output_file="$RESULTS_DIR/stress_tests.xml"

    if [[ ! -f "$test_path" ]]; then
        log_warning "Stress test file not found: $test_path"
        return 1
    fi

    # Stress tests run single-threaded with very long timeout
    local cmd=$(build_pytest_cmd "$test_path" "$output_file" "--timeout=2400 -n 1")

    log "Executing: $cmd"
    log_warning "Stress tests may take a long time and consume significant resources..."

    if eval "$cmd"; then
        log_success "Stress tests completed"
        return 0
    else
        log_error "Stress tests failed"
        return 1
    fi
}

# Generate comprehensive coverage report
generate_coverage_report() {
    if [[ "$GENERATE_COVERAGE" != "true" ]]; then
        return 0
    fi

    log_section "Generating Coverage Report"

    # Combine coverage data if multiple files exist
    coverage_files=("$COVERAGE_DIR"/coverage_*.xml)
    if [[ ${#coverage_files[@]} -gt 1 ]]; then
        log "Combining coverage reports..."
        "$PYTHON_CMD" -m coverage combine "$COVERAGE_DIR"/*.xml 2>/dev/null || true
    fi

    # Generate combined HTML report
    if command -v coverage &> /dev/null; then
        log "Generating combined HTML coverage report..."
        coverage html -d "$COVERAGE_DIR/combined_html" 2>/dev/null || true
        coverage report > "$COVERAGE_DIR/coverage_summary.txt" 2>/dev/null || true
    fi

    log_success "Coverage report generated in $COVERAGE_DIR"
}

# Generate test summary report
generate_test_report() {
    if [[ "$GENERATE_REPORTS" != "true" ]]; then
        return 0
    fi

    log_section "Generating Test Summary Report"

    local report_file="$RESULTS_DIR/test_summary.md"

    cat > "$report_file" << EOF
# Memory Guardian Test Suite Results

**Execution Date**: $(date)
**Execution Duration**: $((SECONDS / 60)) minutes $((SECONDS % 60)) seconds
**Results Directory**: $RESULTS_DIR

## Test Execution Summary

EOF

    # Add results for each test type
    local total_tests=0
    local passed_tests=0
    local failed_tests=0

    for test_type in "unit" "integration" "e2e" "performance" "stress"; do
        local xml_file="$RESULTS_DIR/${test_type}_tests.xml"

        if [[ -f "$xml_file" ]]; then
            # Parse JUnit XML for test counts
            local tests=$(grep -o 'tests="[0-9]*"' "$xml_file" | cut -d'"' -f2)
            local failures=$(grep -o 'failures="[0-9]*"' "$xml_file" | cut -d'"' -f2)
            local errors=$(grep -o 'errors="[0-9]*"' "$xml_file" | cut -d'"' -f2)

            local test_passed=$((tests - failures - errors))
            local test_failed=$((failures + errors))

            total_tests=$((total_tests + tests))
            passed_tests=$((passed_tests + test_passed))
            failed_tests=$((failed_tests + test_failed))

            echo "### ${test_type^} Tests" >> "$report_file"
            echo "- **Total**: $tests" >> "$report_file"
            echo "- **Passed**: $test_passed" >> "$report_file"
            echo "- **Failed**: $test_failed" >> "$report_file"
            echo "" >> "$report_file"
        fi
    done

    # Add overall summary
    cat >> "$report_file" << EOF
## Overall Results

- **Total Tests**: $total_tests
- **Passed**: $passed_tests
- **Failed**: $failed_tests
- **Success Rate**: $((passed_tests * 100 / total_tests))%

EOF

    # Add coverage summary if available
    if [[ -f "$COVERAGE_DIR/coverage_summary.txt" ]]; then
        echo "## Coverage Summary" >> "$report_file"
        echo '```' >> "$report_file"
        cat "$COVERAGE_DIR/coverage_summary.txt" >> "$report_file"
        echo '```' >> "$report_file"
        echo "" >> "$report_file"
    fi

    # Add system information
    cat >> "$report_file" << EOF
## System Information

- **OS**: $(uname -s) $(uname -r)
- **Python**: $("$PYTHON_CMD" --version)
- **Architecture**: $(uname -m)
- **CPU Cores**: $(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo "Unknown")

## Files Generated

- Test Results: \`$RESULTS_DIR\`
- Coverage Reports: \`$COVERAGE_DIR\`
- Execution Log: \`$LOG_FILE\`

EOF

    log_success "Test summary report generated: $report_file"

    # Display summary in console
    echo ""
    log_section "TEST EXECUTION SUMMARY"
    echo ""
    printf "%-20s %10s %10s %10s\n" "Test Type" "Total" "Passed" "Failed"
    printf "%-20s %10s %10s %10s\n" "----------" "-----" "------" "------"

    for test_type in "unit" "integration" "e2e" "performance" "stress"; do
        local xml_file="$RESULTS_DIR/${test_type}_tests.xml"

        if [[ -f "$xml_file" ]]; then
            local tests=$(grep -o 'tests="[0-9]*"' "$xml_file" | cut -d'"' -f2)
            local failures=$(grep -o 'failures="[0-9]*"' "$xml_file" | cut -d'"' -f2)
            local errors=$(grep -o 'errors="[0-9]*"' "$xml_file" | cut -d'"' -f2)

            local test_passed=$((tests - failures - errors))
            local test_failed=$((failures + errors))

            if [[ $test_failed -eq 0 ]]; then
                printf "${GREEN}%-20s %10s %10s %10s${NC}\n" "$test_type" "$tests" "$test_passed" "$test_failed"
            else
                printf "${RED}%-20s %10s %10s %10s${NC}\n" "$test_type" "$tests" "$test_passed" "$test_failed"
            fi
        fi
    done

    echo ""
    printf "%-20s %10s %10s %10s\n" "TOTAL" "$total_tests" "$passed_tests" "$failed_tests"

    if [[ $failed_tests -eq 0 ]]; then
        echo -e "${GREEN}✓ All tests passed!${NC}"
    else
        echo -e "${RED}✗ $failed_tests test(s) failed${NC}"
    fi

    echo ""
    log "Detailed results available in: $RESULTS_DIR"
}

# Main execution function
main() {
    local start_time=$SECONDS
    local exit_code=0

    # Parse arguments
    parse_args "$@"

    # Setup environment
    setup_environment
    check_requirements

    log_section "Starting Memory Guardian Test Suite"
    log "Test configuration:"
    log "  Unit tests: $RUN_UNIT_TESTS"
    log "  Integration tests: $RUN_INTEGRATION_TESTS"
    log "  E2E tests: $RUN_E2E_TESTS"
    log "  Performance tests: $RUN_PERFORMANCE_TESTS"
    log "  Stress tests: $RUN_STRESS_TESTS"
    log "  Generate coverage: $GENERATE_COVERAGE"
    log "  Parallel jobs: $PARALLEL_JOBS"
    log "  Timeout: $TEST_TIMEOUT seconds"

    # Set overall timeout
    (
        sleep "$TEST_TIMEOUT"
        log_error "Test suite timeout reached ($TEST_TIMEOUT seconds)"
        exit 124
    ) &
    timeout_pid=$!

    # Run test suites
    if ! run_unit_tests; then
        exit_code=1
    fi

    if ! run_integration_tests; then
        exit_code=1
    fi

    if ! run_e2e_tests; then
        exit_code=1
    fi

    if ! run_performance_tests; then
        exit_code=1
    fi

    if ! run_stress_tests; then
        exit_code=1
    fi

    # Kill timeout process
    kill $timeout_pid 2>/dev/null || true

    # Generate reports
    generate_coverage_report
    generate_test_report

    local end_time=$SECONDS
    local duration=$((end_time - start_time))

    log_section "Test Suite Completed"
    log "Total execution time: $((duration / 60)) minutes $((duration % 60)) seconds"

    if [[ $exit_code -eq 0 ]]; then
        log_success "All test suites completed successfully!"
    else
        log_error "Some test suites failed. Check the results for details."
    fi

    exit $exit_code
}

# Run main function with all arguments
main "$@"
