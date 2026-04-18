#!/bin/bash

# DevOps Toolkit Uninstallation Script
# This script removes the DevOps Toolkit from the system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Installation paths
INSTALL_DIR="/opt/devops_toolkit"
CONFIG_DIR="/etc/devops_toolkit"
LOG_FILE="/var/log/devops_toolkit.log"
BIN_LINK="/usr/local/bin/devops-toolkit"

# Print colored message
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_message "$RED" "Error: This script must be run as root (use sudo)"
        exit 1
    fi
}

# Confirm uninstallation
confirm_uninstall() {
    echo ""
    print_message "$YELLOW" "======================================"
    print_message "$YELLOW" "  DevOps Toolkit Uninstallation"
    print_message "$YELLOW" "======================================"
    echo ""
    print_message "$RED" "WARNING: This will remove DevOps Toolkit from your system."
    echo ""
    
    read -p "Are you sure you want to continue? (yes/no): " CONFIRM
    
    if [[ "$CONFIRM" != "yes" ]]; then
        print_message "$GREEN" "Uninstallation cancelled."
        exit 0
    fi
}

# Remove cron jobs
remove_cron() {
    print_message "$YELLOW" "Removing cron jobs..."
    
    if crontab -l 2>/dev/null | grep -q "devops-toolkit"; then
        crontab -l 2>/dev/null | grep -v "devops-toolkit" | crontab -
        print_message "$GREEN" "Cron jobs removed"
    else
        print_message "$YELLOW" "No cron jobs found"
    fi
}

# Remove files
remove_files() {
    print_message "$YELLOW" "Removing installation files..."
    
    # Remove installation directory
    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR"
        print_message "$GREEN" "Removed $INSTALL_DIR"
    else
        print_message "$YELLOW" "Installation directory not found"
    fi
    
    # Remove binary link
    if [ -f "$BIN_LINK" ]; then
        rm -f "$BIN_LINK"
        print_message "$GREEN" "Removed $BIN_LINK"
    else
        print_message "$YELLOW" "Binary link not found"
    fi
}

# Remove configuration
remove_config() {
    echo ""
    read -p "Do you want to remove configuration files? (y/n): " REMOVE_CONFIG
    
    if [[ "$REMOVE_CONFIG" =~ ^[Yy]$ ]]; then
        if [ -d "$CONFIG_DIR" ]; then
            rm -rf "$CONFIG_DIR"
            print_message "$GREEN" "Removed $CONFIG_DIR"
        else
            print_message "$YELLOW" "Configuration directory not found"
        fi
    else
        print_message "$YELLOW" "Configuration files preserved at $CONFIG_DIR"
    fi
}

# Remove logs
remove_logs() {
    echo ""
    read -p "Do you want to remove log files? (y/n): " REMOVE_LOGS
    
    if [[ "$REMOVE_LOGS" =~ ^[Yy]$ ]]; then
        if [ -f "$LOG_FILE" ]; then
            rm -f "$LOG_FILE"
            print_message "$GREEN" "Removed $LOG_FILE"
        else
            print_message "$YELLOW" "Log file not found"
        fi
        
        # Remove rotated logs
        if ls /var/log/devops_toolkit.log.* 1> /dev/null 2>&1; then
            rm -f /var/log/devops_toolkit.log.*
            print_message "$GREEN" "Removed rotated log files"
        fi
    else
        print_message "$YELLOW" "Log files preserved at $LOG_FILE"
    fi
}

# Remove Python dependencies
remove_dependencies() {
    echo ""
    read -p "Do you want to remove Python dependencies? (y/n): " REMOVE_DEPS
    
    if [[ "$REMOVE_DEPS" =~ ^[Yy]$ ]]; then
        print_message "$YELLOW" "Removing Python dependencies..."
        python3 -m pip uninstall -y psutil requests PyYAML 2>/dev/null || true
        print_message "$GREEN" "Python dependencies removed"
    else
        print_message "$YELLOW" "Python dependencies preserved"
    fi
}

# Main uninstallation
main() {
    check_root
    confirm_uninstall
    
    echo ""
    print_message "$YELLOW" "Starting uninstallation..."
    echo ""
    
    remove_cron
    remove_files
    remove_config
    remove_logs
    remove_dependencies
    
    echo ""
    print_message "$GREEN" "======================================"
    print_message "$GREEN" "  Uninstallation Complete!"
    print_message "$GREEN" "======================================"
    echo ""
    print_message "$GREEN" "DevOps Toolkit has been removed from your system."
    echo ""
}

# Run main uninstallation
main

# Made with Bob
