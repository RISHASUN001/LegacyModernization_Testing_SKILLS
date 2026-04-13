#!/bin/bash

# Browser Testing Setup and Test Runner
# Automates the complete setup and testing workflow

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$SCRIPT_DIR"
DASHBOARD_DIR="$PROJECT_DIR/src/LegacyModernization.Dashboard.Web"
SKILLS_DIR="$PROJECT_DIR/skills/browser-testing-with-devtools"
DATA_DIR="$PROJECT_DIR/data"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║ $1${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check .NET
    if ! command -v dotnet &> /dev/null; then
        print_error ".NET SDK not found. Please install .NET 8 or later."
        exit 1
    fi
    print_success ".NET SDK found: $(dotnet --version)"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found. Please install Python 3.7 or later."
        exit 1
    fi
    print_success "Python 3 found: $(python3 --version)"
    
    # Check Git
    if ! command -v git &> /dev/null; then
        print_warning "Git not found (optional)"
    else
        print_success "Git found"
    fi
}

# Build the solution
build_solution() {
    print_header "Building Solution"
    
    cd "$PROJECT_DIR"
    print_info "Running: dotnet build"
    
    if dotnet build 2>&1 | tail -20; then
        print_success "Build completed successfully"
    else
        print_error "Build failed"
        exit 1
    fi
}

# Create data directory
setup_data() {
    print_header "Setting Up Data"
    
    mkdir -p "$DATA_DIR"
    print_success "Data directory created/verified"
    
    if [ ! -f "$DATA_DIR/modernization.db" ]; then
        print_info "Database will be created on first run"
    else
        print_success "Database exists"
    fi
}

# Start dashboard
start_dashboard() {
    print_header "Starting Dashboard Application"
    
    cd "$DASHBOARD_DIR"
    print_info "Starting: dotnet run"
    print_info "Dashboard will be available at http://localhost:5276"
    print_info "Press Ctrl+C to stop the dashboard"
    
    dotnet run
}

# Test dashboard
test_dashboard() {
    print_header "Testing Dashboard"
    
    print_info "Waiting for dashboard to start..."
    sleep 3
    
    for i in {1..10}; do
        if curl -s http://localhost:5276/api/test/health > /dev/null; then
            print_success "Dashboard is responding"
            return 0
        fi
        print_info "Attempt $i/10 - waiting..."
        sleep 2
    done
    
    print_error "Dashboard failed to respond"
    return 1
}

# Show test login page
show_login_page() {
    print_header "Test Login Page"
    
    LOGIN_FILE="$PROJECT_DIR/test-login.html"
    
    if [ ! -f "$LOGIN_FILE" ]; then
        print_error "Login page not found: $LOGIN_FILE"
        return 1
    fi
    
    print_success "Login page available at:"
    print_info "file://$LOGIN_FILE"
    echo ""
    print_info "Or after dashboard starts:"
    print_info "http://localhost:5276/test-login.html"
    echo ""
    print_info "Demo Credentials:"
    print_info "  Email: test@buildathon.dev"
    print_info "  Password: TestPassword123!"
    print_info "  Module: Checklist"
}

# List API endpoints
list_api_endpoints() {
    print_header "Available Test API Endpoints"
    
    echo ""
    echo "Health Check:"
    echo "  curl http://localhost:5276/api/test/health"
    echo ""
    echo "Console Logs:"
    echo "  curl http://localhost:5276/api/test/console-logs | python -m json.tool"
    echo ""
    echo "Network Requests:"
    echo "  curl http://localhost:5276/api/test/network-requests | python -m json.tool"
    echo ""
    echo "Performance Metrics:"
    echo "  curl http://localhost:5276/api/test/performance-metrics | python -m json.tool"
    echo ""
    echo "Accessibility Report:"
    echo "  curl http://localhost:5276/api/test/accessibility-report | python -m json.tool"
    echo ""
    echo "DOM Structure:"
    echo "  curl http://localhost:5276/api/test/dom-structure | python -m json.tool"
    echo ""
    echo "Interaction Flows:"
    echo "  curl http://localhost:5276/api/test/interaction-flows | python -m json.tool"
    echo ""
}

# Run browser tests
run_browser_tests() {
    print_header "Running Browser Testing Tasks"
    
    cd "$PROJECT_DIR"
    
    BASE_URL="${1:-http://localhost:5276}"
    MODULE="${2:-Checklist}"
    RUN_ID="${3:-run-001}"
    
    print_info "Parameters:"
    print_info "  Base URL: $BASE_URL"
    print_info "  Module: $MODULE"
    print_info "  Run ID: $RUN_ID"
    echo ""
    
    python3 "$SKILLS_DIR/test_runner.py" \
        --base-url "$BASE_URL" \
        --module "$MODULE" \
        --run-id "$RUN_ID" \
        --verbose
    
    print_success "Browser tests completed"
}

# Interactive menu
show_menu() {
    print_header "Browser Testing - Main Menu"
    
    echo ""
    echo "1) Check prerequisites"
    echo "2) Build solution"
    echo "3) Setup data"
    echo "4) Start dashboard"
    echo "5) Test dashboard (in another terminal)"
    echo "6) Show login page"
    echo "7) List API endpoints"
    echo "8) Run browser tests (requires running dashboard)"
    echo "9) Full setup (1-3) + start dashboard"
    echo "10) Full test (1-3, start dashboard & run tests)"
    echo "0) Exit"
    echo ""
}

# Main script logic
if [ $# -eq 0 ]; then
    # Interactive mode
    while true; do
        show_menu
        read -p "Select option: " choice
        
        case $choice in
            1) check_prerequisites ;;
            2) build_solution ;;
            3) setup_data ;;
            4) start_dashboard ;;
            5) test_dashboard ;;
            6) show_login_page ;;
            7) list_api_endpoints ;;
            8) 
                read -p "Base URL [http://localhost:5276]: " url
                read -p "Module [Checklist]: " module
                read -p "Run ID [run-001]: " runid
                run_browser_tests "${url:-http://localhost:5276}" "${module:-Checklist}" "${runid:-run-001}"
                ;;
            9)
                check_prerequisites
                build_solution
                setup_data
                print_info "Setup complete. Starting dashboard..."
                start_dashboard
                ;;
            10)
                check_prerequisites
                build_solution
                setup_data
                print_info "Setup complete. Starting dashboard in background..."
                start_dashboard &
                DASHBOARD_PID=$!
                sleep 3
                
                if test_dashboard; then
                    echo ""
                    show_login_page
                    echo ""
                    list_api_endpoints
                    echo ""
                    print_info "Running browser tests..."
                    run_browser_tests
                fi
                
                print_info "Stopping dashboard..."
                kill $DASHBOARD_PID
                ;;
            0)
                print_info "Exiting"
                exit 0
                ;;
            *)
                print_error "Invalid option"
                ;;
        esac
        
        echo ""
        read -p "Press Enter to continue..."
    done
else
    # Command line mode
    case "$1" in
        prerequisites)
            check_prerequisites
            ;;
        build)
            build_solution
            ;;
        setup)
            setup_data
            ;;
        start)
            start_dashboard
            ;;
        test)
            test_dashboard
            ;;
        login)
            show_login_page
            ;;
        api)
            list_api_endpoints
            ;;
        run-tests)
            run_browser_tests "$2" "$3" "$4"
            ;;
        full)
            check_prerequisites
            build_solution
            setup_data
            print_info "Starting dashboard in background..."
            start_dashboard &
            DASHBOARD_PID=$!
            sleep 3
            
            if test_dashboard; then
                echo ""
                show_login_page
                echo ""
                list_api_endpoints
                echo ""
                print_info "Running browser tests..."
                run_browser_tests
            fi
            
            print_info "Stopping dashboard..."
            kill $DASHBOARD_PID
            ;;
        help|--help|-h)
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  prerequisites   - Check prerequisites"
            echo "  build           - Build solution"
            echo "  setup           - Setup data"
            echo "  start           - Start dashboard"
            echo "  test            - Test dashboard"
            echo "  login           - Show login page"
            echo "  api             - List API endpoints"
            echo "  run-tests       - Run browser tests"
            echo "  full            - Full setup and test"
            echo "  help            - Show this help"
            echo ""
            echo "No arguments: Interactive menu"
            ;;
        *)
            print_error "Unknown command: $1"
            echo "Run '$0 help' for usage"
            exit 1
            ;;
    esac
fi
