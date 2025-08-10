#!/bin/bash
# Emergency System Cleanup Script
# Stops ALL crypto trading system processes and background loops

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${RED}🚨 EMERGENCY SYSTEM CLEANUP${NC}"
echo "=============================================="
echo "This will stop ALL crypto trading system processes"
echo "Start Time: $(date)"
echo ""

# Function to print status
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Kill all Python processes related to the trading system
cleanup_python_processes() {
    echo -e "${BLUE}🔄 Stopping Python trading system processes...${NC}"
    
    # Kill specific trading system processes
    pkill -f "python.*app.main" 2>/dev/null && print_status "Stopped app.main processes" || print_info "No app.main processes found"
    pkill -f "python.*main.py" 2>/dev/null && print_status "Stopped main.py processes" || print_info "No main.py processes found"
    pkill -f "uvicorn.*app" 2>/dev/null && print_status "Stopped uvicorn processes" || print_info "No uvicorn processes found"
    pkill -f "fastapi" 2>/dev/null && print_status "Stopped FastAPI processes" || print_info "No FastAPI processes found"
    
    # Kill any Python processes in the project directory
    local project_dir=$(pwd)
    pkill -f "python.*$project_dir" 2>/dev/null && print_status "Stopped project Python processes" || print_info "No project Python processes found"
    
    # Kill autonomous trading orchestrator specifically
    pkill -f "autonomous_trading_orchestrator" 2>/dev/null && print_status "Stopped autonomous trading orchestrator" || print_info "No autonomous trading orchestrator found"
    
    # Kill any background trading loops
    pkill -f "trading.*loop" 2>/dev/null && print_status "Stopped trading loops" || print_info "No trading loops found"
    pkill -f "risk.*manager" 2>/dev/null && print_status "Stopped risk manager" || print_info "No risk manager found"
    pkill -f "position.*manager" 2>/dev/null && print_status "Stopped position manager" || print_info "No position manager found"
    
    sleep 2
    print_status "Python process cleanup completed"
}

# Kill all Node.js processes related to the frontend
cleanup_node_processes() {
    echo -e "${BLUE}🔄 Stopping Node.js frontend processes...${NC}"
    
    # Kill React development server
    pkill -f "node.*react-scripts" 2>/dev/null && print_status "Stopped React development server" || print_info "No React server found"
    pkill -f "npm.*start" 2>/dev/null && print_status "Stopped npm start processes" || print_info "No npm start processes found"
    pkill -f "yarn.*start" 2>/dev/null && print_status "Stopped yarn start processes" || print_info "No yarn start processes found"
    
    # Kill any Node processes in the project directory
    local project_dir=$(pwd)
    pkill -f "node.*$project_dir" 2>/dev/null && print_status "Stopped project Node processes" || print_info "No project Node processes found"
    
    sleep 2
    print_status "Node.js process cleanup completed"
}

# Clean up PID files and logs
cleanup_files() {
    echo -e "${BLUE}🔄 Cleaning up PID files and logs...${NC}"
    
    # Remove PID files
    rm -f logs/backend.pid 2>/dev/null && print_status "Removed backend PID file" || print_info "No backend PID file found"
    rm -f logs/frontend.pid 2>/dev/null && print_status "Removed frontend PID file" || print_info "No frontend PID file found"
    rm -f logs/*.pid 2>/dev/null && print_status "Removed all PID files" || print_info "No PID files found"
    
    # Archive current logs
    if [[ -d "logs" ]]; then
        local timestamp=$(date +%Y%m%d-%H%M%S)
        local archive_dir="logs/archive-$timestamp"
        mkdir -p "$archive_dir"
        
        # Move current logs to archive
        mv logs/*.log "$archive_dir/" 2>/dev/null && print_status "Archived log files to $archive_dir" || print_info "No log files to archive"
        
        # Create fresh log directory
        mkdir -p logs
        print_status "Created fresh logs directory"
    fi
}

# Check for any remaining processes
check_remaining_processes() {
    echo -e "${BLUE}🔄 Checking for remaining processes...${NC}"
    
    # Check for any remaining Python processes
    local python_procs=$(ps aux | grep -E "python.*app|uvicorn|fastapi" | grep -v grep | wc -l)
    if [[ $python_procs -gt 0 ]]; then
        print_warning "Found $python_procs remaining Python processes:"
        ps aux | grep -E "python.*app|uvicorn|fastapi" | grep -v grep | head -5
        echo ""
        print_warning "Force killing remaining Python processes..."
        pkill -9 -f "python.*app" 2>/dev/null || true
        pkill -9 -f "uvicorn" 2>/dev/null || true
        pkill -9 -f "fastapi" 2>/dev/null || true
    else
        print_status "No remaining Python processes found"
    fi
    
    # Check for any remaining Node processes
    local node_procs=$(ps aux | grep -E "node.*react|npm.*start" | grep -v grep | wc -l)
    if [[ $node_procs -gt 0 ]]; then
        print_warning "Found $node_procs remaining Node processes:"
        ps aux | grep -E "node.*react|npm.*start" | grep -v grep | head -5
        echo ""
        print_warning "Force killing remaining Node processes..."
        pkill -9 -f "node.*react" 2>/dev/null || true
        pkill -9 -f "npm.*start" 2>/dev/null || true
    else
        print_status "No remaining Node processes found"
    fi
}

# Check port usage
check_port_usage() {
    echo -e "${BLUE}🔄 Checking port usage...${NC}"
    
    # Check backend port (8000)
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port 8000 still in use:"
        lsof -Pi :8000 -sTCP:LISTEN
        print_warning "Killing processes on port 8000..."
        lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    else
        print_status "Port 8000 is free"
    fi
    
    # Check frontend port (3000)
    if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port 3000 still in use:"
        lsof -Pi :3000 -sTCP:LISTEN
        print_warning "Killing processes on port 3000..."
        lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    else
        print_status "Port 3000 is free"
    fi
    
    # Check other common ports
    for port in 8001 8080 9000; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            print_warning "Port $port in use (may be related):"
            lsof -Pi :$port -sTCP:LISTEN
        fi
    done
}

# Stop database services if they were started by the deployment
stop_database_services() {
    echo -e "${BLUE}🔄 Checking database services...${NC}"
    
    # Check if PostgreSQL was started by our deployment
    if brew services list | grep -q "postgresql.*started"; then
        print_info "PostgreSQL is running (leaving it running as it may be used by other applications)"
        print_info "To stop PostgreSQL manually: brew services stop postgresql@15"
    else
        print_status "PostgreSQL is not running"
    fi
    
    # Check if Redis was started by our deployment
    if brew services list | grep -q "redis.*started"; then
        print_info "Redis is running (leaving it running as it may be used by other applications)"
        print_info "To stop Redis manually: brew services stop redis"
    else
        print_status "Redis is not running"
    fi
}

# Clean up virtual environment processes
cleanup_virtual_env() {
    echo -e "${BLUE}🔄 Cleaning up virtual environment...${NC}"
    
    # Deactivate any active virtual environment
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        print_info "Deactivating virtual environment: $VIRTUAL_ENV"
        deactivate 2>/dev/null || true
    fi
    
    # Kill any processes using the virtual environment
    if [[ -d "venv" ]]; then
        local venv_path=$(realpath venv)
        pkill -f "$venv_path" 2>/dev/null && print_status "Stopped virtual environment processes" || print_info "No virtual environment processes found"
    fi
}

# Main cleanup function
main_cleanup() {
    print_info "Starting comprehensive system cleanup..."
    echo ""
    
    cleanup_python_processes
    echo ""
    
    cleanup_node_processes
    echo ""
    
    cleanup_virtual_env
    echo ""
    
    cleanup_files
    echo ""
    
    check_remaining_processes
    echo ""
    
    check_port_usage
    echo ""
    
    stop_database_services
    echo ""
    
    print_status "System cleanup completed!"
}

# Confirmation before cleanup
echo -e "${YELLOW}This will stop ALL crypto trading system processes.${NC}"
echo "This includes:"
echo "  - Backend API server"
echo "  - Frontend development server"
echo "  - Autonomous trading orchestrator"
echo "  - Risk manager"
echo "  - Position manager"
echo "  - All background trading loops"
echo ""

read -p "Are you sure you want to continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Cleanup cancelled by user"
    exit 0
fi

echo ""
main_cleanup

echo ""
echo "=============================================="
print_status "🎉 EMERGENCY CLEANUP COMPLETED!"
echo "=============================================="
echo "End Time: $(date)"
echo ""
print_info "All crypto trading system processes have been stopped."
print_info "The system is now in a clean state."
print_info "You can safely restart the deployment when ready."
echo ""
print_info "To restart the system:"
echo "  1. Ensure your API keys are set:"
echo "     export DELTA_TESTNET_API_KEY='your_key'"
echo "     export DELTA_TESTNET_API_SECRET='your_secret'"
echo "  2. Run the deployment script:"
echo "     ./deploy-v2-macos.sh"

