#!/usr/bin/env bash
# MCP Local Development Setup Script
# Sets up and manages MCP services for local development

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
MCP_HOME="${MCP_HOME:-$HOME/.mcp}"
MCP_LOGS="$MCP_HOME/logs"
MCP_PIDS="$MCP_HOME/pids"
MCP_CONFIG="$PROJECT_ROOT/config/mcp_services.yaml"

# Service details
SERVICE_NAMES=("eva-memory" "cloud-bridge" "desktop-gateway")
SERVICE_PORTS=("3001" "3002" "3003")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create necessary directories
setup_directories() {
    log_info "Setting up MCP directories..."
    mkdir -p "$MCP_HOME"
    mkdir -p "$MCP_LOGS"
    mkdir -p "$MCP_PIDS"
    log_success "Directories created"
}

# Check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Find process using a port
find_port_process() {
    local port=$1
    lsof -Pi :$port -sTCP:LISTEN -t 2>/dev/null || echo ""
}

# Kill process on port
kill_port_process() {
    local port=$1
    local pid=$(find_port_process $port)
    
    if [[ -n "$pid" ]]; then
        log_warning "Killing process $pid on port $port"
        kill -TERM $pid 2>/dev/null || true
        sleep 2
        
        # Force kill if still running
        if kill -0 $pid 2>/dev/null; then
            kill -KILL $pid 2>/dev/null || true
        fi
    fi
}

# Check service dependencies
check_dependencies() {
    log_info "Checking dependencies..."
    
    local missing_deps=()
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        missing_deps+=("node")
    fi
    
    # Check npm/npx
    if ! command -v npx &> /dev/null; then
        missing_deps+=("npx")
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        missing_deps+=("python3")
    fi
    
    # Check required tools
    if ! command -v lsof &> /dev/null; then
        missing_deps+=("lsof")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_info "Please install missing dependencies and try again"
        return 1
    fi
    
    log_success "All dependencies satisfied"
    return 0
}

# Install MCP services if needed
install_services() {
    log_info "Checking MCP service installations..."
    
    # Check eva-memory
    if ! npm list -g @modelcontextprotocol/server-memory &>/dev/null; then
        log_info "Installing eva-memory service..."
        npm install -g @modelcontextprotocol/server-memory
    fi
    
    # Check cloud bridge (example - adjust based on actual package)
    if ! npm list -g @aws/mcp-server-aws &>/dev/null; then
        log_info "Installing cloud bridge service..."
        npm install -g @aws/mcp-server-aws
    fi
    
    # Check desktop gateway (example - adjust based on actual package)
    if ! pip show mcp-server-desktop &>/dev/null; then
        log_info "Installing desktop gateway service..."
        pip install mcp-server-desktop
    fi
    
    log_success "All services installed"
}

# Setup environment variables
setup_environment() {
    log_info "Setting up environment..."
    
    # Create env file if it doesn't exist
    local env_file="$MCP_HOME/.env"
    if [[ ! -f "$env_file" ]]; then
        cat > "$env_file" << EOF
# MCP Environment Configuration
export MCP_HOME="$MCP_HOME"
export MCP_LOGS="$MCP_LOGS"
export NODE_ENV="development"

# Service-specific settings
export EVA_MEMORY_PORT="3001"
export CLOUD_BRIDGE_PORT="3002"
export DESKTOP_GATEWAY_PORT="3003"

# AWS settings (customize as needed)
export AWS_REGION="${AWS_REGION:-us-east-1}"
export AWS_PROFILE="${AWS_PROFILE:-default}"

# Desktop gateway settings
export DESKTOP_GATEWAY_SCREENSHOT_ENABLED="true"
export DESKTOP_GATEWAY_FILE_ACCESS_ENABLED="true"
EOF
        log_success "Created environment file: $env_file"
    fi
    
    # Source environment
    source "$env_file"
}

# Get port for service
get_service_port() {
    local service=$1
    for i in "${!SERVICE_NAMES[@]}"; do
        if [[ "${SERVICE_NAMES[$i]}" == "$service" ]]; then
            echo "${SERVICE_PORTS[$i]}"
            return
        fi
    done
}

# Stop a single service
stop_service() {
    local service=$1
    local port=$(get_service_port "$service")
    local pidfile="$MCP_PIDS/$service.pid"
    
    log_info "Stopping $service..."
    
    # Check pidfile
    if [[ -f "$pidfile" ]]; then
        local pid=$(cat "$pidfile")
        if kill -0 $pid 2>/dev/null; then
            kill -TERM $pid
            sleep 2
            if kill -0 $pid 2>/dev/null; then
                kill -KILL $pid 2>/dev/null || true
            fi
        fi
        rm -f "$pidfile"
    fi
    
    # Also check port
    kill_port_process $port
    
    log_success "$service stopped"
}

# Stop all services
stop_all_services() {
    log_info "Stopping all MCP services..."
    
    for service in "${SERVICE_NAMES[@]}"; do
        stop_service "$service"
    done
    
    log_success "All services stopped"
}

# Clean up resources
cleanup() {
    log_info "Cleaning up MCP resources..."
    
    # Stop all services
    stop_all_services
    
    # Clean old logs (keep last 7 days)
    if [[ -d "$MCP_LOGS" ]]; then
        find "$MCP_LOGS" -name "*.log" -mtime +7 -delete 2>/dev/null || true
    fi
    
    # Remove stale pidfiles
    if [[ -d "$MCP_PIDS" ]]; then
        for pidfile in "$MCP_PIDS"/*.pid; do
            if [[ -f "$pidfile" ]]; then
                local pid=$(cat "$pidfile")
                if ! kill -0 $pid 2>/dev/null; then
                    rm -f "$pidfile"
                fi
            fi
        done
    fi
    
    log_success "Cleanup completed"
}

# Show service status
show_status() {
    echo ""
    echo "MCP Service Status"
    echo "=================="
    
    for i in "${!SERVICE_NAMES[@]}"; do
        local service="${SERVICE_NAMES[$i]}"
        local port="${SERVICE_PORTS[$i]}"
        local pidfile="$MCP_PIDS/$service.pid"
        local status="${RED}Stopped${NC}"
        local pid="N/A"
        
        if [[ -f "$pidfile" ]]; then
            pid=$(cat "$pidfile")
            if kill -0 $pid 2>/dev/null; then
                status="${GREEN}Running${NC}"
            fi
        fi
        
        printf "%-20s Status: %b  PID: %-8s Port: %s\n" \
            "$service" "$status" "$pid" "$port"
    done
    
    echo ""
}

# Start monitoring
start_monitoring() {
    log_info "Starting MCP service monitoring..."
    
    # Use the Python monitor script
    local monitor_script="$SCRIPT_DIR/monitor_mcp_services.py"
    
    if [[ ! -f "$monitor_script" ]]; then
        log_error "Monitor script not found: $monitor_script"
        return 1
    fi
    
    # Check if monitor is already running
    local monitor_pidfile="$MCP_PIDS/monitor.pid"
    if [[ -f "$monitor_pidfile" ]]; then
        local monitor_pid=$(cat "$monitor_pidfile")
        if kill -0 $monitor_pid 2>/dev/null; then
            log_warning "Monitor already running (PID: $monitor_pid)"
            return 0
        fi
    fi
    
    # Start monitor in background
    nohup python3 "$monitor_script" \
        --config "$MCP_CONFIG" \
        --log-dir "$MCP_LOGS" \
        > "$MCP_LOGS/monitor.out" 2>&1 &
    
    local monitor_pid=$!
    echo $monitor_pid > "$monitor_pidfile"
    
    log_success "Monitor started (PID: $monitor_pid)"
    log_info "Logs: $MCP_LOGS/monitor.out"
}

# Stop monitoring
stop_monitoring() {
    log_info "Stopping MCP monitor..."
    
    local monitor_pidfile="$MCP_PIDS/monitor.pid"
    if [[ -f "$monitor_pidfile" ]]; then
        local monitor_pid=$(cat "$monitor_pidfile")
        if kill -0 $monitor_pid 2>/dev/null; then
            kill -TERM $monitor_pid
            sleep 2
            if kill -0 $monitor_pid 2>/dev/null; then
                kill -KILL $monitor_pid 2>/dev/null || true
            fi
        fi
        rm -f "$monitor_pidfile"
    fi
    
    log_success "Monitor stopped"
}

# Show logs
show_logs() {
    local service=${1:-}
    
    if [[ -z "$service" ]]; then
        # Show monitor log
        if [[ -f "$MCP_LOGS/monitor.out" ]]; then
            tail -f "$MCP_LOGS/monitor.out"
        else
            log_error "No monitor log found"
        fi
    else
        # Show service log
        local logfile="$MCP_LOGS/$service.log"
        if [[ -f "$logfile" ]]; then
            tail -f "$logfile"
        else
            log_error "No log found for $service"
        fi
    fi
}

# Main menu
show_menu() {
    echo ""
    echo "MCP Local Development Setup"
    echo "=========================="
    echo "1. Setup environment"
    echo "2. Start monitoring"
    echo "3. Stop monitoring"
    echo "4. Show status"
    echo "5. Show logs"
    echo "6. Stop all services"
    echo "7. Clean up"
    echo "8. Exit"
    echo ""
}

# Main function
main() {
    # Parse command line arguments
    case "${1:-}" in
        setup)
            setup_directories
            check_dependencies || exit 1
            install_services
            setup_environment
            log_success "Setup completed"
            ;;
        start)
            start_monitoring
            sleep 3
            show_status
            ;;
        stop)
            stop_monitoring
            stop_all_services
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "${2:-}"
            ;;
        cleanup)
            cleanup
            ;;
        *)
            # Interactive mode
            while true; do
                show_menu
                read -p "Select option: " choice
                
                case $choice in
                    1)
                        setup_directories
                        check_dependencies || continue
                        install_services
                        setup_environment
                        ;;
                    2)
                        start_monitoring
                        sleep 3
                        show_status
                        ;;
                    3)
                        stop_monitoring
                        ;;
                    4)
                        show_status
                        ;;
                    5)
                        read -p "Service name (leave empty for monitor log): " service
                        show_logs "$service"
                        ;;
                    6)
                        stop_all_services
                        ;;
                    7)
                        cleanup
                        ;;
                    8)
                        log_info "Exiting..."
                        exit 0
                        ;;
                    *)
                        log_error "Invalid option"
                        ;;
                esac
                
                echo ""
                read -p "Press Enter to continue..."
            done
            ;;
    esac
}

# Run main
main "$@"