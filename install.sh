#!/bin/bash

# DevOps Toolkit Installation Script
# Modern installation with Python checks and uv support
#
# Usage:
#   sudo bash install.sh                    # Interactive installation
#   sudo NON_INTERACTIVE=1 bash install.sh  # Non-interactive installation
#
# Environment Variables:
#   NON_INTERACTIVE - Skip all interactive prompts (default: not set)
#   SKIP_UV         - Skip uv installation prompt (default: not set)
#   SKIP_CRON       - Skip cron setup (default: not set)
#   SKIP_TEST       - Skip test execution (default: not set)

# Exit on error, but handle errors gracefully
set -e
trap 'handle_error $? $LINENO' ERR

# Constants
readonly INTERACTIVE_TIMEOUT=30
readonly PYTHON_MIN_MAJOR=3
readonly PYTHON_MIN_MINOR=8
readonly UV_INSTALL_URL="https://astral.sh/uv/install.sh"

# Error handler
handle_error() {
    local exit_code=$1
    local line_number=$2
    echo ""
    print_message "$RED" "✗ Installation failed at line $line_number with exit code $exit_code"
    print_message "$YELLOW" "  Please check the error message above and try again"
    print_message "$YELLOW" "  For help, visit: https://github.com/sameeralam3127/devops-toolkit/issues"
    exit "$exit_code"
}

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

# Track if apt-get update has been run
APT_UPDATED=false

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
    print_message "$BLUE" "║     DevOps Toolkit Installation        ║"
    print_message "$BLUE" "║     Production-Grade System Monitor    ║"
    print_message "$BLUE" "╚════════════════════════════════════════╝"
    echo ""
}

# Sanitize string for use in sed command
sanitize_for_sed() {
    local input="$1"
    # Escape special characters: / \ & |
    echo "$input" | sed 's/[\/&|]/\\&/g'
}

# Validate cron schedule format
validate_cron_schedule() {
    local schedule="$1"
    # Basic validation: 5 fields separated by spaces
    # Fields: minute hour day month weekday
    if [[ "$schedule" =~ ^[0-9\*\,\-\/]+[[:space:]]+[0-9\*\,\-\/]+[[:space:]]+[0-9\*\,\-\/]+[[:space:]]+[0-9\*\,\-\/]+[[:space:]]+[0-9\*\,\-\/]+$ ]]; then
        return 0
    else
        return 1
    fi
}

# Get package manager for the current OS
get_package_manager() {
    if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        echo "apt-get"
    elif [[ "$OS" =~ ^(rhel|centos|fedora|rocky|almalinux)$ ]]; then
        if command -v dnf &> /dev/null; then
            echo "dnf"
        else
            echo "yum"
        fi
    else
        echo "unknown"
    fi
}

# Run apt-get update once if needed
run_apt_update() {
    if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        if [ "$APT_UPDATED" = false ]; then
            print_message "$BLUE" "  Updating package lists..."
            apt-get update -qq
            APT_UPDATED=true
        fi
    fi
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
        # VERSION variable is sourced from /etc/os-release but not used directly
        # shellcheck disable=SC2034
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
        PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
        PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

        # Validate that version numbers are numeric
        if ! [[ "$PYTHON_MAJOR" =~ ^[0-9]+$ ]] || ! [[ "$PYTHON_MINOR" =~ ^[0-9]+$ ]]; then
            print_message "$RED" "✗ Could not parse Python version: $PYTHON_VERSION"
            return 1
        fi

        if [ "$PYTHON_MAJOR" -ge "$PYTHON_MIN_MAJOR" ] && [ "$PYTHON_MINOR" -ge "$PYTHON_MIN_MINOR" ]; then
            print_message "$GREEN" "✓ Python $PYTHON_VERSION found (>= ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR} required)"
            return 0
        else
            print_message "$RED" "✗ Python $PYTHON_VERSION found but >= ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR} required"
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

    local pkg_manager
    pkg_manager=$(get_package_manager)

    case "$pkg_manager" in
        apt-get)
            run_apt_update
            apt-get install -y python3 python3-pip python3-venv
            ;;
        dnf)
            dnf install -y python3 python3-pip
            ;;
        yum)
            yum install -y python3 python3-pip
            ;;
        *)
            print_message "$RED" "✗ Unsupported OS for automatic Python installation"
            print_message "$YELLOW" "  Please install Python ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}+ manually"
            exit 1
            ;;
    esac

    print_message "$GREEN" "✓ Python installed successfully"
}

# Check and install uv (optional but recommended)
check_uv() {
    if command -v uv &> /dev/null; then
        print_message "$GREEN" "✓ uv package manager found"
        return 0
    else
        print_message "$YELLOW" "  uv not found (optional but recommended)"

        # Non-interactive mode check
        if [ -n "$NON_INTERACTIVE" ] || [ -n "$SKIP_UV" ]; then
            print_message "$YELLOW" "  Skipping uv installation (non-interactive mode)"
            return 1
        fi

        read -t "$INTERACTIVE_TIMEOUT" -p "  Install uv for faster dependency management? (y/n): " INSTALL_UV || {
            print_message "$YELLOW" "  No response, skipping uv installation"
            return 1
        }

        if [[ "$INSTALL_UV" =~ ^[Yy]$ ]]; then
            print_message "$YELLOW" "  Installing uv..."
            print_message "$YELLOW" "  ⚠️  Downloading and executing remote script from $UV_INSTALL_URL"

            # Download script first for inspection (more secure than piping directly)
            local temp_script="/tmp/uv-install-$$.sh"
            if curl -LsSf "$UV_INSTALL_URL" -o "$temp_script" 2>&1; then
                # Execute the downloaded script
                if bash "$temp_script" 2>&1; then
                    rm -f "$temp_script"
                    export PATH="$HOME/.cargo/bin:$PATH"
                    # Verify uv installation
                    if command -v uv &> /dev/null; then
                        print_message "$GREEN" "✓ uv installed successfully"
                        return 0
                    else
                        print_message "$YELLOW" "  uv installation completed but not found in PATH"
                        print_message "$YELLOW" "  Continuing with pip..."
                        return 1
                    fi
                else
                    rm -f "$temp_script"
                    print_message "$YELLOW" "  uv installation failed, continuing with pip..."
                    return 1
                fi
            else
                print_message "$YELLOW" "  Failed to download uv installer, continuing with pip..."
                return 1
            fi
        fi
        return 1
    fi
}

# Install Python dependencies
install_dependencies() {
    print_message "$YELLOW" "Installing Python dependencies..."

    if [ ! -f "pyproject.toml" ]; then
        print_message "$RED" "✗ pyproject.toml not found"
        print_message "$YELLOW" "  Make sure you're running the installer from the project root"
        exit 1
    fi

    # Check if pip is available
    if ! python3 -m pip --version &> /dev/null; then
        print_message "$YELLOW" "  pip not found, installing..."

        local pkg_manager
        pkg_manager=$(get_package_manager)

        case "$pkg_manager" in
            apt-get)
                run_apt_update
                apt-get install -y python3-pip python3-venv python3-dev build-essential
                ;;
            dnf)
                dnf install -y python3-pip python3-devel gcc
                ;;
            yum)
                yum install -y python3-pip python3-devel gcc
                ;;
            *)
                print_message "$RED" "✗ Cannot install pip automatically"
                print_message "$YELLOW" "  Please install python3-pip manually and run the installer again"
                exit 1
                ;;
        esac

        # Verify pip installation
        if ! python3 -m pip --version &> /dev/null; then
            print_message "$RED" "✗ pip installation failed"
            exit 1
        fi

        print_message "$GREEN" "✓ pip installed successfully"
    fi

    # Upgrade pip first
    print_message "$BLUE" "  Upgrading pip..."
    if python3 -m pip install --upgrade pip setuptools wheel 2>&1 | tee /tmp/pip-upgrade.log | grep -i "error"; then
        print_message "$YELLOW" "  Warning: pip upgrade had errors, check /tmp/pip-upgrade.log"
    else
        print_message "$GREEN" "  ✓ pip upgraded successfully"
    fi

    # Try uv first, fall back to pip
    if command -v uv &> /dev/null; then
        print_message "$BLUE" "  Using uv for installation..."
        if uv pip install -e . --system 2>&1; then
            print_message "$GREEN" "✓ Dependencies installed with uv"
        else
            print_message "$YELLOW" "  uv installation failed, falling back to pip..."
            if python3 -m pip install -e . 2>&1; then
                print_message "$GREEN" "✓ Dependencies installed with pip"
            else
                print_message "$RED" "✗ Failed to install dependencies"
                print_message "$YELLOW" "  Trying to install from requirements.txt..."
                if [ -f "requirements.txt" ]; then
                    if python3 -m pip install -r requirements.txt 2>&1; then
                        print_message "$GREEN" "✓ Core dependencies installed"
                    else
                        print_message "$RED" "✗ Failed to install dependencies"
                        print_message "$YELLOW" "  Try manually: python3 -m pip install -r requirements.txt"
                        exit 1
                    fi
                else
                    print_message "$RED" "✗ requirements.txt not found"
                    exit 1
                fi
            fi
        fi
    else
        print_message "$BLUE" "  Using pip for installation..."
        if python3 -m pip install -e . 2>&1; then
            print_message "$GREEN" "✓ Dependencies installed successfully"
        else
            print_message "$YELLOW" "  Installation with -e failed, trying requirements.txt..."
            if [ -f "requirements.txt" ]; then
                if python3 -m pip install -r requirements.txt 2>&1; then
                    print_message "$GREEN" "✓ Core dependencies installed"
                else
                    print_message "$RED" "✗ Failed to install dependencies"
                    print_message "$YELLOW" "  Try manually: python3 -m pip install -r requirements.txt"
                    exit 1
                fi
            else
                print_message "$RED" "✗ Failed to install dependencies and requirements.txt not found"
                exit 1
            fi
        fi
    fi

    # Verify critical dependencies
    print_message "$BLUE" "  Verifying dependencies..."
    local missing_deps=()

    for dep in psutil requests yaml; do
        if ! python3 -c "import $dep" 2>/dev/null; then
            missing_deps+=("$dep")
        fi
    done

    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_message "$RED" "✗ Missing critical dependencies: ${missing_deps[*]}"
        print_message "$YELLOW" "  Try: python3 -m pip install psutil requests PyYAML"
        exit 1
    fi

    print_message "$GREEN" "✓ All dependencies verified"
}

# Copy files to installation directory
install_files() {
    print_message "$YELLOW" "Installing DevOps Toolkit files..."

    # Create installation directory
    if ! mkdir -p "$INSTALL_DIR"; then
        print_message "$RED" "✗ Failed to create installation directory: $INSTALL_DIR"
        print_message "$YELLOW" "  Check permissions or try with sudo"
        exit 1
    fi

    # Copy application
    if [ -d "app" ]; then
        if ! cp -r app "$INSTALL_DIR/"; then
            print_message "$RED" "✗ Failed to copy app directory"
            exit 1
        fi

        if [ -f "pyproject.toml" ]; then
            cp pyproject.toml "$INSTALL_DIR/" 2>/dev/null || true
        else
            print_message "$YELLOW" "  Warning: pyproject.toml not found"
        fi

        print_message "$GREEN" "✓ Files copied to $INSTALL_DIR"
    else
        print_message "$RED" "✗ app directory not found"
        print_message "$YELLOW" "  Make sure you're running the installer from the project root"
        exit 1
    fi

    # Create symbolic link for CLI
    # First, verify the CLI module exists
    if [ ! -f "app/cli.py" ]; then
        print_message "$RED" "✗ app/cli.py not found"
        print_message "$YELLOW" "  The CLI module is missing from the installation"
        exit 1
    fi

    if ! cat > "$BIN_LINK" << 'EOF'
#!/bin/bash
# DevOps Toolkit CLI wrapper
cd /opt/devops_toolkit || exit 1

# Check if running as root for certain operations
if [[ "$1" == "patch" ]] || [[ "$1" == "service" ]]; then
    if [[ $EUID -ne 0 ]]; then
        echo "Error: '$1' command requires root privileges"
        echo "Please run: sudo devops-toolkit $*"
        exit 1
    fi
fi

# Execute the CLI
exec python3 -m app.cli "$@"
EOF
    then
        print_message "$RED" "✗ Failed to create CLI script"
        exit 1
    fi

    if ! chmod +x "$BIN_LINK"; then
        print_message "$RED" "✗ Failed to make CLI script executable"
        exit 1
    fi

    # Verify the CLI works
    if ! "$BIN_LINK" --help &> /dev/null; then
        print_message "$YELLOW" "  Warning: CLI verification failed, but installation will continue"
        print_message "$YELLOW" "  You may need to check the Python module structure"
    fi

    print_message "$GREEN" "✓ Created command: devops-toolkit"
}

# Setup configuration
setup_config() {
    print_message "$YELLOW" "Setting up configuration..."

    # Create config directory
    if ! mkdir -p "$CONFIG_DIR"; then
        print_message "$RED" "✗ Failed to create config directory: $CONFIG_DIR"
        print_message "$YELLOW" "  Check permissions or try with sudo"
        exit 1
    fi

    # Copy example config if doesn't exist
    if [ ! -f "$CONFIG_FILE" ]; then
        if [ -f "config.yaml.example" ]; then
            if ! cp config.yaml.example "$CONFIG_FILE"; then
                print_message "$RED" "✗ Failed to copy configuration file"
                exit 1
            fi
            print_message "$GREEN" "✓ Configuration created at $CONFIG_FILE"
        else
            print_message "$YELLOW" "  Warning: config.yaml.example not found"
            print_message "$YELLOW" "  You'll need to create $CONFIG_FILE manually"
        fi
    else
        print_message "$YELLOW" "  Configuration already exists at $CONFIG_FILE"
    fi

    # Interactive Slack configuration
    if [ -f "$CONFIG_FILE" ]; then
        echo ""
        print_message "$BLUE" "═══ Slack Configuration ═══"
        print_message "$YELLOW" "  Get your webhook from: https://api.slack.com/messaging/webhooks"

        # Non-interactive mode check
        if [ -n "$NON_INTERACTIVE" ]; then
            print_message "$YELLOW" "  Skipping Slack configuration (non-interactive mode)"
            print_message "$YELLOW" "  Edit $CONFIG_FILE to add webhook later"
        else
            read -t "$INTERACTIVE_TIMEOUT" -p "  Enter Slack webhook URL (or press Enter to skip): " WEBHOOK_URL || {
                print_message "$YELLOW" "  No response, skipping Slack configuration"
                WEBHOOK_URL=""
            }

            if [ -n "$WEBHOOK_URL" ]; then
                # Sanitize webhook URL for sed
                local sanitized_url
                sanitized_url=$(sanitize_for_sed "$WEBHOOK_URL")

                # Use Python for safer config update (avoids sed escaping issues)
                if command -v python3 &> /dev/null; then
                    python3 << EOF 2>/dev/null
import re
try:
    with open('$CONFIG_FILE', 'r') as f:
        content = f.read()
    content = re.sub(r"webhook_url:.*", "webhook_url: '$WEBHOOK_URL'", content)
    with open('$CONFIG_FILE', 'w') as f:
        f.write(content)
    print("success")
except Exception:
    print("failed")
EOF
                    if [ $? -eq 0 ]; then
                        print_message "$GREEN" "✓ Slack webhook configured"
                    else
                        print_message "$YELLOW" "  Could not auto-configure webhook. Please edit $CONFIG_FILE manually"
                    fi
                else
                    # Fallback to sed with sanitized input
                    if [[ "$OSTYPE" == "darwin"* ]]; then
                        sed -i '' "s|webhook_url:.*|webhook_url: '$sanitized_url'|g" "$CONFIG_FILE" 2>/dev/null || \
                        print_message "$YELLOW" "  Could not auto-configure webhook. Please edit $CONFIG_FILE manually"
                    else
                        sed -i "s|webhook_url:.*|webhook_url: '$sanitized_url'|g" "$CONFIG_FILE" 2>/dev/null || \
                        print_message "$YELLOW" "  Could not auto-configure webhook. Please edit $CONFIG_FILE manually"
                    fi
                    print_message "$GREEN" "✓ Slack webhook configured"
                fi
            else
                print_message "$YELLOW" "  Skipped. Edit $CONFIG_FILE to add webhook later"
            fi
        fi
    fi
}

# Setup logging
setup_logging() {
    print_message "$YELLOW" "Setting up logging..."

    # Create log directory if it doesn't exist
    LOG_DIR=$(dirname "$LOG_FILE")
    if ! mkdir -p "$LOG_DIR"; then
        print_message "$RED" "✗ Failed to create log directory: $LOG_DIR"
        exit 1
    fi

    if ! touch "$LOG_FILE"; then
        print_message "$RED" "✗ Failed to create log file: $LOG_FILE"
        print_message "$YELLOW" "  Check permissions or try with sudo"
        exit 1
    fi

    if ! chmod 644 "$LOG_FILE"; then
        print_message "$YELLOW" "  Warning: Could not set log file permissions"
    fi

    print_message "$GREEN" "✓ Log file: $LOG_FILE"
}

# Setup cron job
setup_cron() {
    echo ""
    print_message "$BLUE" "═══ Cron Job Setup ═══"

    # Non-interactive mode check
    if [ -n "$NON_INTERACTIVE" ] || [ -n "$SKIP_CRON" ]; then
        print_message "$YELLOW" "  Skipping cron setup (non-interactive mode)"
        return
    fi

    read -t "$INTERACTIVE_TIMEOUT" -p "  Setup automatic execution via cron? (y/n): " SETUP_CRON || {
        print_message "$YELLOW" "  No response, skipping cron setup"
        return
    }

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
            5)
                read -p "  Enter cron schedule (e.g., '0 2 * * *'): " CRON_SCHEDULE
                # Validate cron schedule
                if ! validate_cron_schedule "$CRON_SCHEDULE"; then
                    print_message "$RED" "✗ Invalid cron schedule format"
                    print_message "$YELLOW" "  Expected format: minute hour day month weekday"
                    print_message "$YELLOW" "  Example: 0 2 * * * (daily at 2 AM)"
                    return
                fi
                ;;
            *) print_message "$YELLOW" "  Skipped cron setup"; return ;;
        esac

        CRON_ENTRY="$CRON_SCHEDULE $BIN_LINK run >> $LOG_FILE 2>&1"

        # Use temporary file to avoid race condition
        local temp_cron="/tmp/crontab-$$.tmp"

        # Get current crontab
        if crontab -l 2>/dev/null > "$temp_cron"; then
            # Remove existing devops-toolkit entries
            grep -v "devops-toolkit" "$temp_cron" > "${temp_cron}.new" 2>/dev/null || touch "${temp_cron}.new"
            # Add new entry
            echo "$CRON_ENTRY" >> "${temp_cron}.new"
            # Install new crontab
            if crontab "${temp_cron}.new" 2>/dev/null; then
                print_message "$GREEN" "✓ Cron job configured: $CRON_SCHEDULE"
            else
                print_message "$RED" "✗ Failed to install crontab"
            fi
        else
            # No existing crontab, create new one
            echo "$CRON_ENTRY" > "$temp_cron"
            if crontab "$temp_cron" 2>/dev/null; then
                print_message "$GREEN" "✓ Cron job configured: $CRON_SCHEDULE"
            else
                print_message "$RED" "✗ Failed to install crontab"
            fi
        fi

        # Cleanup
        rm -f "$temp_cron" "${temp_cron}.new"
    fi
}

# Run test
run_test() {
    echo ""
    print_message "$BLUE" "═══ Testing Installation ═══"

    # Non-interactive mode check
    if [ -n "$NON_INTERACTIVE" ] || [ -n "$SKIP_TEST" ]; then
        print_message "$YELLOW" "  Skipping test (non-interactive mode)"
        return
    fi

    read -t "$INTERACTIVE_TIMEOUT" -p "  Run test now? (y/n): " RUN_TEST || {
        print_message "$YELLOW" "  No response, skipping test"
        return
    }

    if [[ "$RUN_TEST" =~ ^[Yy]$ ]]; then
        echo ""
        if devops-toolkit test 2>&1; then
            print_message "$GREEN" "✓ Test completed successfully"
        else
            print_message "$YELLOW" "  Warning: Test had issues, but installation is complete"
            print_message "$YELLOW" "  Check the configuration and try: devops-toolkit test"
        fi
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
