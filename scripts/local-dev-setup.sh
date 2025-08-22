#!/bin/bash

# Local development setup script for Azure migration
# Sets up the development environment for Azure Functions and React

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Setup Azure Functions backend
setup_backend() {
    print_status "Setting up Azure Functions backend..."
    
    cd server-azure
    
    # Install Azure Functions Core Tools if not present
    if ! command_exists func; then
        print_status "Installing Azure Functions Core Tools..."
        npm install -g azure-functions-core-tools@4 --unsafe-perm true
    fi
    
    # Create Python virtual environment
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install Python dependencies
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt
    
    # Copy local settings template
    if [ ! -f "local.settings.json" ]; then
        print_status "Creating local.settings.json..."
        cp local.settings.json.template local.settings.json 2>/dev/null || true
    fi
    
    print_success "Backend setup complete!"
    
    # Instructions for running
    echo ""
    print_warning "To run the backend locally:"
    echo "1. cd server-azure"
    echo "2. source venv/bin/activate"
    echo "3. func start"
    echo ""
    
    cd ..
}

# Setup React frontend
setup_frontend() {
    print_status "Setting up React frontend..."
    
    cd frontend
    
    # Install Node.js dependencies
    print_status "Installing Node.js dependencies..."
    npm install
    
    # Copy environment template
    if [ ! -f ".env.development" ]; then
        print_status "Creating .env.development..."
        cp .env.template .env.development
    fi
    
    print_success "Frontend setup complete!"
    
    # Instructions for running
    echo ""
    print_warning "To run the frontend locally:"
    echo "1. cd frontend"
    echo "2. npm run dev"
    echo ""
    
    cd ..
}

# Setup development environment
setup_dev_env() {
    print_status "Setting up development environment..."
    
    # Create .env.development if it doesn't exist
    if [ ! -f "server-azure/.env" ]; then
        print_status "Creating backend .env file..."
        cat > server-azure/.env << EOF
# Local development environment variables
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=dev-secret-key-change-in-production
COSMOS_DB_ENDPOINT=
COSMOS_DB_KEY=
COSMOS_DB_NAME=sage-db
KEY_VAULT_URL=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
PLAID_CLIENT_ID=
PLAID_SECRET=
PLAID_ENV=sandbox
EOF
        print_warning "Please update server-azure/.env with your actual credentials"
    fi
    
    print_success "Development environment setup complete!"
}

# Install prerequisites
install_prerequisites() {
    print_status "Checking and installing prerequisites..."
    
    # Check Python
    if ! command_exists python3; then
        print_error "Python 3 is required but not installed."
        print_status "Please install Python 3 from https://python.org/"
        exit 1
    fi
    
    # Check Node.js
    if ! command_exists node; then
        print_error "Node.js is required but not installed."
        print_status "Please install Node.js from https://nodejs.org/"
        exit 1
    fi
    
    # Check npm
    if ! command_exists npm; then
        print_error "npm is required but not installed."
        print_status "npm should come with Node.js installation"
        exit 1
    fi
    
    print_success "All prerequisites are available!"
}

# Main setup function
main() {
    echo ""
    echo "=================================================="
    echo "   Sage - Azure Local Development Setup          "
    echo "=================================================="
    echo ""
    
    install_prerequisites
    setup_dev_env
    setup_backend
    setup_frontend
    
    echo ""
    print_success "🎉 Local development setup completed successfully!"
    echo ""
    echo "=================================="
    echo "       DEVELOPMENT WORKFLOW       "
    echo "=================================="
    echo "1. Start the backend:"
    echo "   cd server-azure && source venv/bin/activate && func start"
    echo ""
    echo "2. Start the frontend (in another terminal):"
    echo "   cd frontend && npm run dev"
    echo ""
    echo "3. Open your browser to:"
    echo "   Frontend: http://localhost:5173"
    echo "   Backend:  http://localhost:7071"
    echo ""
    echo "=================================="
    echo "       CONFIGURATION              "
    echo "=================================="
    echo "1. Update server-azure/.env with your credentials"
    echo "2. Update frontend/.env.development with your settings"
    echo "3. Get Google OAuth credentials from Google Cloud Console"
    echo "4. Get Plaid credentials from Plaid Dashboard"
    echo ""
}

# Check if running with --help
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "Sage Financial Management App - Local Development Setup"
    echo ""
    echo "Usage: ./scripts/local-dev-setup.sh"
    echo ""
    echo "This script will:"
    echo "1. Check prerequisites (Python, Node.js, npm)"
    echo "2. Setup Azure Functions backend environment"
    echo "3. Setup React frontend environment"
    echo "4. Create development configuration files"
    echo ""
    echo "Prerequisites:"
    echo "- Python 3.8+ installed"
    echo "- Node.js 18+ installed"
    echo "- npm installed"
    echo ""
    exit 0
fi

# Run main function
main "$@"