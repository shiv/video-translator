#!/bin/bash
set -e

# AI Video Translation Service - Quick Start Script
# This script helps you get started with local Docker testing

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker Desktop first."
        echo "Download from: https://www.docker.com/products/docker-desktop"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker Desktop first."
        exit 1
    fi
    
    print_success "All prerequisites are installed and running"
}

# Function to setup environment
setup_environment() {
    print_status "Setting up environment..."
    
    # Check if .env exists
    if [ ! -f ".env" ]; then
        if [ -f "env.example" ]; then
            print_status "Creating .env file from template..."
            cp env.example .env
        else
            print_status "Creating basic .env file..."
            cat > .env << EOF
# AI Video Translation Service - Environment Configuration
HUGGING_FACE_TOKEN=your_hugging_face_token_here
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
OUTPUT_DIRECTORY=output/
UPLOAD_DIRECTORY=uploads/
EOF
        fi
    fi
    
    # Check if Hugging Face token is set
    if grep -q "your_hugging_face_token_here" .env; then
        print_warning "Please update your Hugging Face token in .env file"
        echo ""
        echo "1. Visit https://huggingface.co/settings/tokens"
        echo "2. Create a new token or copy an existing one"
        echo "3. Replace 'your_hugging_face_token_here' in .env file"
        echo ""
        read -p "Press Enter after updating the token to continue..."
    fi
    
    # Create directories
    mkdir -p uploads output logs static templates
    
    print_success "Environment setup complete"
}

# Function to build and start services
start_services() {
    print_status "Building and starting services..."
    
    # Build and start with docker-compose
    docker-compose up --build -d
    
    print_status "Waiting for services to start..."
    sleep 10
    
    # Check if service is healthy
    for i in {1..30}; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            print_success "Service is healthy and ready!"
            break
        else
            if [ $i -eq 30 ]; then
                print_error "Service health check failed after 30 attempts"
                print_status "Checking logs..."
                docker-compose logs
                exit 1
            fi
            print_status "Waiting for service to be ready... (attempt $i/30)"
            sleep 2
        fi
    done
}

# Function to show service information
show_service_info() {
    print_success "🎉 AI Video Translation Service is running!"
    echo ""
    echo "📊 Service Information:"
    echo "  • Web Interface: http://localhost:8000/"
    echo "  • API Documentation: http://localhost:8000/docs"
    echo "  • Health Check: http://localhost:8000/health"
    echo "  • Service Status: http://localhost:8000/status"
    echo ""
    echo "🐳 Docker Commands:"
    echo "  • View logs: docker-compose logs -f"
    echo "  • Stop service: docker-compose down"
    echo "  • Restart service: docker-compose restart"
    echo "  • View containers: docker-compose ps"
    echo ""
    echo "🧪 Testing:"
    echo "  • Upload test video via web interface"
    echo "  • Use API endpoints for programmatic access"
    echo "  • Check logs for debugging information"
    echo ""
}

# Function to run basic tests
run_tests() {
    print_status "Running basic health checks..."
    
    # Test health endpoint
    if curl -f http://localhost:8000/health &> /dev/null; then
        print_success "Health endpoint is working"
    else
        print_error "Health endpoint is not responding"
        return 1
    fi
    
    # Test web interface
    if curl -f http://localhost:8000/ &> /dev/null; then
        print_success "Web interface is accessible"
    else
        print_error "Web interface is not responding"
        return 1
    fi
    
    # Test API documentation
    if curl -f http://localhost:8000/docs &> /dev/null; then
        print_success "API documentation is accessible"
    else
        print_error "API documentation is not responding"
        return 1
    fi
    
    print_success "All basic tests passed!"
}

# Function to show logs
show_logs() {
    print_status "Showing service logs (press Ctrl+C to exit)..."
    docker-compose logs -f
}

# Function to stop services
stop_services() {
    print_status "Stopping services..."
    docker-compose down
    print_success "Services stopped"
}

# Function to clean up everything
cleanup() {
    print_status "Cleaning up containers and images..."
    docker-compose down -v --rmi all
    print_success "Cleanup completed"
}

# Main menu function
show_menu() {
    echo ""
    echo "🚀 AI Video Translation Service - Quick Start"
    echo ""
    echo "Available commands:"
    echo "  start   - Start the service (build + run)"
    echo "  stop    - Stop the service"
    echo "  restart - Restart the service"
    echo "  logs    - Show service logs"
    echo "  test    - Run basic health checks"
    echo "  status  - Show service status"
    echo "  clean   - Clean up everything"
    echo "  help    - Show this menu"
    echo ""
}

# Parse command line arguments
case "$1" in
    "start")
        check_prerequisites
        setup_environment
        start_services
        run_tests
        show_service_info
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        print_status "Restarting service..."
        docker-compose restart
        print_success "Service restarted"
        ;;
    "logs")
        show_logs
        ;;
    "test")
        run_tests
        ;;
    "status")
        echo "Service Status:"
        docker-compose ps
        echo ""
        echo "Health Check:"
        curl -s http://localhost:8000/health | jq . 2>/dev/null || curl -s http://localhost:8000/health
        ;;
    "clean")
        cleanup
        ;;
    "help"|"-h"|"--help")
        show_menu
        ;;
    "")
        # No argument provided, run full start sequence
        check_prerequisites
        setup_environment
        start_services
        run_tests
        show_service_info
        ;;
    *)
        print_error "Unknown command: $1"
        show_menu
        exit 1
        ;;
esac 