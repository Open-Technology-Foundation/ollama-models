#!/bin/bash
# install.sh - Ollama Models Toolbox installation script
# Version: 1.0.0
#
# This script sets up the Ollama Models Toolbox environment:
# - Creates canonical model directories if they don't exist
# - Sets up symlinks to the appropriate model directory
# - Installs required Python dependencies
#
set -euo pipefail

# Define color codes for output
declare COLOR_GREEN="\033[0;32m"
declare COLOR_YELLOW="\033[0;33m"
declare COLOR_RED="\033[0;31m"
declare COLOR_RESET="\033[0m"

# Output functions
info() {
  echo -e "${COLOR_GREEN}[INFO]${COLOR_RESET} $1"
}

warn() {
  echo -e "${COLOR_YELLOW}[WARNING]${COLOR_RESET} $1" >&2
}

error() {
  echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $1" >&2
}

# Check for required commands
declare -a REQUIRED_COMMANDS=("pip" "python3" "wget")
for cmd in "${REQUIRED_COMMANDS[@]}"; do
  if ! command -v "$cmd" &> /dev/null; then
    error "Required command '$cmd' not found. Please install it and try again."
    exit 1
  fi
done

# Create canonical model directories
setup_model_dirs() {
  declare -a DIRS=(
    "/usr/local/share/ollama/models"
    "$HOME/.local/share/ollama/models"
  )
  
  for dir in "${DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
      info "Creating directory: $dir"
      mkdir -p "$dir" 2>/dev/null || {
        warn "Could not create $dir (permission denied)"
        continue
      }
    else
      info "Directory already exists: $dir"
    fi
  done
}

# Set up symlink to the appropriate models directory
setup_symlink() {
  # Remove existing models symlink or directory if it exists
  if [ -e "models" ]; then
    info "Removing existing models link or directory"
    rm -rf "models"
  fi
  
  # Try to use system directory first
  if [ -d "/usr/local/share/ollama/models" ] && [ -w "/usr/local/share/ollama/models" ]; then
    info "Creating symlink to system models directory"
    ln -sf "/usr/local/share/ollama/models" "models"
  else
    info "System models directory not writable, using user directory"
    mkdir -p "$HOME/.local/share/ollama/models"
    ln -sf "$HOME/.local/share/ollama/models" "models"
  fi
  
  # Validate the symlink was created
  if [ -L "models" ]; then
    info "Models symlink created successfully pointing to $(readlink -f models)"
  else
    error "Failed to create models symlink"
    exit 1
  fi
}

# Install Python dependencies
install_deps() {
  info "Installing Python dependencies"
  pip install --user beautifulsoup4
  
  # Check html_deltags is available
  if ! command -v html_deltags &> /dev/null; then
    warn "html_deltags command not found. You may need to install it separately."
    warn "The ollama-update-models-library script requires this tool."
  fi
}

# Make scripts executable
make_executable() {
  info "Making scripts executable"
  chmod +x ollama-models.py ollama-update-models.py ollama-update-models-library
}

# Create symbolic links without .py extension
create_shortcuts() {
  info "Creating symbolic links for scripts"
  if [ ! -L "ollama-models" ]; then
    ln -sf "ollama-models.py" "ollama-models"
  fi
  
  if [ ! -L "ollama-update-models" ]; then
    ln -sf "ollama-update-models.py" "ollama-update-models"
  fi
}

# Main execution
# Check for help or version flags
if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
  echo "Usage: ./install.sh [OPTIONS]"
  echo ""
  echo "Installs the Ollama Models Toolbox:"
  echo " - Creates canonical model directories if they don't exist"
  echo " - Sets up symlinks to the appropriate model directory"
  echo " - Installs required Python dependencies"
  echo " - Makes scripts executable and creates symbolic links"
  echo ""
  echo "Options:"
  echo "  -h, --help     Show this help message"
  echo "  -V, --version  Show version information"
  exit 0
fi

if [[ "$1" == "-V" ]] || [[ "$1" == "--version" ]]; then
  echo "Ollama Models Toolbox v1.0.0"
  exit 0
fi

info "Installing Ollama Models Toolbox v1.0.0"
setup_model_dirs
setup_symlink
install_deps
make_executable
create_shortcuts
info "Installation complete!"
info "You can now run the following commands:"
info "  1. ollama-update-models-library    # To download the latest model library"
info "  2. ollama-update-models            # To extract model information"
info "  3. ollama-models [options]         # To filter and search models"

#fin