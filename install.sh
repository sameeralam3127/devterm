#!/bin/bash

# DevOps Toolkit Installation Script
# Modern installation with Python checks and uv support

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Installation paths
INSTALL_DIR="/opt/devops_toolkit"
CONFIG_DIR="/etc/devops_toolkit"
CONFIG_FILE="${CONFIG_DIR}/config.yaml"
LOG_DIR="/var/log"
LOG_FILE="${LOG_DIR}/devops_toolkit.log"
BIN_LINK="/usr/local/bin/devops-toolkit"

# Print colored message
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Print header
print_header() {
    echo ""
    print_message "$BLUE" "╔════════════════════════════════════════╗"
    print_message "$BLUE" "║     DevOps Toolkit Installation       ║"
    print_message "$BLUE" "║     Production-Grade System Monitor    ║"
    print_message "$BLUE" "╚════════════════════════════════════════╝"
    echo ""
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_message "$RED" "✗ Error: This script must be run as root"
        print_message "$YELLOW" "  Please run: sudo bash install.sh"
        exit 1
    fi
    print_message "$GREEN" "✓ Running with root privileges"
}

# Detect OS
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
        print_message "$GREEN" "✓ Detected OS: $PRETTY_NAME"
    else
        print_message "$RED" "✗ Cannot detect OS"
        exit 1
    fi
}

# Check Python installation
check_python() {
    print_message "$YELLOW" "Checking Python installation..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
            print_message "$GREEN" "✓ Python $PYTHON_VERSION found (>= 3.8 required)"
            return 0
        else
            print_message "$RED" "✗ Python $PYTHON_VERSION found but >= 3.8 required"
            return 1
        fi
    else
        print_message "$RED" "✗ Python 3 not found"
        return 1
    fi
}

# Install Python
install_python() {
    print_message "$YELLOW" "Installing Python 3..."
    
    if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        apt-get update -qq
        apt-get install -y python3 python3-pip python3-venv
    elif [[ "$OS" =~ ^(rhel|centos|fedora|rocky|almalinux)$ ]]; then
        if command -v dnf &> /dev/null; then
            dnf install -y python3 python3-pip
        else
            yum install -y python3 python3-pip
        fi
    else
        print_message "$RED" "✗ Unsupported OS for automatic Python installation"
        print_message "$YELLOW" "  Please install Python 3.8+ manually"
        exit 1
    fi
    
    print_message "$GREEN" "✓ Python installed successfully"
}

# Check and install uv (optional but recommended)
check_uv() {
    if command -v uv &> /dev/null; then
        print_message "$GREEN" "✓ uv package manager found"
        return 0
    else
        print_message "$YELLOW" "  uv not found (optional but recommended)"
        read -p "  Install uv for faster dependency management? (y/n): " INSTALL_UV
        
        if [[ "$INSTALL_UV" =~ ^[Yy]$ ]]; then
            print_message "$YELLOW" "  Installing uv..."
            curl -LsSf https://astral.sh/uv/install.sh | sh
            export PATH="$HOME/.cargo/bin:$PATH"
            print_message "$GREEN" "✓ uv installed successfully"
            return 0
        fi
        return 1
    fi
}

# Install Python dependencies
install_dependencies() {
    print_message "$YELLOW" "Installing Python dependencies..."
    
    if [ ! -f "pyproject.toml" ]; then
        print_message "$RED" "✗ pyproject.toml not found"
        exit 1
    fi
    
    # Try uv first, fall back to pip
    if command -v uv &> /dev/null; then
        print_message "$BLUE" "  Using uv for installation..."
        uv pip install -e . --system
    else
        print_message "$BLUE" "  Using pip for installation..."
        python3 -m pip install --upgrade pip
        python3 -m pip install -e .
    fi
    
    print_message "$GREEN" "✓ Dependencies installed successfully"
}

# Copy files to installation directory
install_files() {
    print_message "$YELLOW" "Installing DevOps Toolkit files..."
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    
    # Copy application
    if [ -d "app" ]; then
        cp -r app "$INSTALL_DIR/"
        cp pyproject.toml "$INSTALL_DIR/" 2>/dev/null || true
        print_message "$GREEN" "✓ Files copied to $INSTALL_DIR"
    else
        print_message "$RED" "✗ app directory not found"
        exit 1
    fi
    
    # Create symbolic link for CLI
    cat > "$BIN_LINK" << 'EOF'
#!/bin/bash
cd /opt/devops_toolkit
python3 -m app.devops_toolkit.cli "$@"
EOF
    chmod +x "$BIN_LINK"
    print_message "$GREEN" "✓ Created command: devops-toolkit"
}

# Setup configuration
setup_config() {
    print_message "$YELLOW" "Setting up configuration..."
    
    # Create config directory
    mkdir -p "$CONFIG_DIR"
    
    # Copy example config if doesn't exist
    if [ ! -f "$CONFIG_FILE" ]; then
        if [ -f "config.yaml.example" ]; then
            cp config.yaml.example "$CONFIG_FILE"
            print_message "$GREEN" "✓ Configuration created at $CONFIG_FILE"
        fi
    else
        print_message "$YELLOW" "  Configuration already exists at $CONFIG_FILE"
    fi
    
    # Interactive Slack configuration
    echo ""
    print_message "$BLUE" "═══ Slack Configuration ═══"
    print_message "$YELLOW" "  Get your webhook from: https://api.slack.com/messaging/webhooks"
    read -p "  Enter Slack webhook URL (or press Enter to skip): " WEBHOOK_URL
    
    if [ ! -z "$WEBHOOK_URL" ]; then
        if [ -f "$CONFIG_FILE" ]; then
            sed -i "s|webhook_url:.*|webhook_url: '$WEBHOOK_URL'|g" "$CONFIG_FILE"
            print_message "$GREEN" "✓ Slack webhook configured"
        fi
    else
        print_message "$YELLOW" "  Skipped. Edit $CONFIG_FILE to add webhook later"
    fi
}

# Setup logging
setup_logging() {
    print_message "$YELLOW" "Setting up logging..."
    
    touch "$LOG_FILE"
    chmod 644 "$LOG_FILE"
    
    print_message "$GREEN" "✓ Log file: $LOG_FILE"
}

# Setup cron job
setup_cron() {
    echo ""
    print_message "$BLUE" "═══ Cron Job Setup ═══"
    
    read -p "  Setup automatic execution via cron? (y/n): " SETUP_CRON
    
    if [[ "$SETUP_CRON" =~ ^[Yy]$ ]]; then
        echo ""
        echo "  Select schedule:"
        echo "    1) Daily at 2:00 AM"
        echo "    2) Every 6 hours"
        echo "    3) Every 12 hours"
        echo "    4) Weekly (Sunday 2:00 AM)"
        echo "    5) Custom"
        echo "    6) Skip"
        
        read -p "  Choice (1-6): " CRON_CHOICE
        
        case $CRON_CHOICE in
            1) CRON_SCHEDULE="0 2 * * *" ;;
            2) CRON_SCHEDULE="0 */6 * * *" ;;
            3) CRON_SCHEDULE="0 */12 * * *" ;;
            4) CRON_SCHEDULE="0 2 * * 0" ;;
            5) read -p "  Enter cron schedule: " CRON_SCHEDULE ;;
            *) print_message "$YELLOW" "  Skipped cron setup"; return ;;
        esac
        
        CRON_ENTRY="$CRON_SCHEDULE $BIN_LINK run >> $LOG_FILE 2>&1"
        
        if crontab -l 2>/dev/null | grep -q "devops-toolkit"; then
            (crontab -l 2>/dev/null | grep -v "devops-toolkit"; echo "$CRON_ENTRY") | crontab -
        else
            (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
        fi
        
        print_message "$GREEN" "✓ Cron job configured: $CRON_SCHEDULE"
    fi
}

# Run test
run_test() {
    echo ""
    print_message "$BLUE" "═══ Testing Installation ═══"
    
    read -p "  Run test now? (y/n): " RUN_TEST
    
    if [[ "$RUN_TEST" =~ ^[Yy]$ ]]; then
        echo ""
        devops-toolkit test
    fi
}

# Print completion message
print_completion() {
    echo ""
    print_message "$GREEN" "╔════════════════════════════════════════╗"
    print_message "$GREEN" "║   Installation Complete! 🎉            ║"
    print_message "$GREEN" "╚════════════════════════════════════════╝"
    echo ""
    print_message "$BLUE" "Next Steps:"
    print_message "$YELLOW" "  1. Edit config:    sudo nano $CONFIG_FILE"
    print_message "$YELLOW" "  2. Run test:       devops-toolkit test"
    print_message "$YELLOW" "  3. Run full check: devops-toolkit run"
    echo ""
    print_message "$BLUE" "Available Commands:"
    print_message "$YELLOW" "  devops-toolkit run       - Run all modules"
    print_message "$YELLOW" "  devops-toolkit patch     - Patch management"
    print_message "$YELLOW" "  devops-toolkit monitor   - System monitoring"
    print_message "$YELLOW" "  devops-toolkit audit     - Security audits"
    print_message "$YELLOW" "  devops-toolkit test      - Test mode"
    print_message "$YELLOW" "  devops-toolkit --help    - Show help"
    echo ""
    print_message "$BLUE" "Documentation:"
    print_message "$YELLOW" "  README: https://github.com/sameeralam3127/devops-toolkit"
    echo ""
}

# Main installation
main() {
    print_header
    check_root
    detect_os
    
    if ! check_python; then
        install_python
    fi
    
    check_uv
    install_dependencies
    install_files
    setup_config
    setup_logging
    setup_cron
    run_test
    print_completion
}

# Run main installation
main

# Made with Bob
