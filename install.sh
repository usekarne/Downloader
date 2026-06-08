#!/usr/bin/env bash
# ==============================================================================
# RS Downloader v10.0.0 - Auto Installer
# Author: RAJSARASWATI JATAV (RS)
# License: MIT
# ==============================================================================

set -euo pipefail

# Version
INSTALLER_VERSION="10.0.0"

# Paths
INSTALL_DIR="${HOME}/.rs-downloader"
VENV_DIR="${INSTALL_DIR}/venv"
CONFIG_DIR="${INSTALL_DIR}/config"
CACHE_DIR="${INSTALL_DIR}/cache"
LOG_FILE="${INSTALL_DIR}/install.log"
SYMLINK_PATH="/usr/local/bin/rsdl"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Flags
VERBOSE=0
UPDATE_MODE=0
UNINSTALL_MODE=0
CHECK_MODE=0
SKIP_DEPS=0

# ==============================================================================
# Color Output Functions
# ==============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

banner() {
    echo -e "${MAGENTA}"
    echo -e "  ╔══════════════════════════════════════════════════╗"
    echo -e "  ║                                                  ║"
    echo -e "  ║          RS DOWNLOADER v${INSTALLER_VERSION}                    ║"
    echo -e "  ║          The Ultimate Download Toolkit           ║"
    echo -e "  ║          by RAJSARASWATI JATAV (RS)             ║"
    echo -e "  ║                                                  ║"
    echo -e "  ╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

verbose() {
    if [[ "${VERBOSE}" -eq 1 ]]; then
        echo -e "${DIM}[VERBOSE]${NC} $1"
    fi
}

step() {
    echo -e "${CYAN}[STEP]${NC} ${BOLD}$1${NC}"
}

# ==============================================================================
# Logging
# ==============================================================================

log() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] $1" >> "${LOG_FILE}" 2>/dev/null || true
}

# ==============================================================================
# OS Detection
# ==============================================================================

detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        echo "${ID}"
    elif [[ "$(uname)" == "Darwin" ]]; then
        echo "macos"
    elif command -v termux-info &>/dev/null || [[ -d /data/data/com.termux ]]; then
        echo "termux"
    else
        echo "unknown"
    fi
}

detect_os_name() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        echo "${PRETTY_NAME:-${ID}}"
    elif [[ "$(uname)" == "Darwin" ]]; then
        echo "macOS $(sw_vers -productVersion 2>/dev/null || echo 'Unknown')"
    elif command -v termux-info &>/dev/null || [[ -d /data/data/com.termux ]]; then
        echo "Termux (Android)"
    else
        echo "Unknown OS"
    fi
}

# ==============================================================================
# Dependency Installation Per OS
# ==============================================================================

install_deps_ubuntu() {
    info "Installing dependencies for Ubuntu/Debian..."
    sudo apt-get update -qq || { error "apt-get update failed"; return 1; }
    sudo apt-get install -y -qq \
        python3 python3-pip python3-venv \
        ffmpeg ffprobe \
        libssl-dev libffi-dev \
        build-essential \
        2>/dev/null || { error "Package installation failed"; return 1; }
    success "Ubuntu/Debian dependencies installed"
}

install_deps_debian() {
    install_deps_ubuntu
}

install_deps_kali() {
    info "Installing dependencies for Kali Linux..."
    sudo apt-get update -qq || { error "apt-get update failed"; return 1; }
    sudo apt-get install -y -qq \
        python3 python3-pip python3-venv \
        ffmpeg ffprobe \
        libssl-dev libffi-dev \
        build-essential \
        2>/dev/null || { error "Package installation failed"; return 1; }
    success "Kali Linux dependencies installed"
}

install_deps_fedora() {
    info "Installing dependencies for Fedora..."
    sudo dnf install -y \
        python3 python3-pip \
        ffmpeg ffmpeg-free \
        openssl-devel libffi-devel \
        gcc gcc-c++ make \
        2>/dev/null || { error "Package installation failed"; return 1; }
    success "Fedora dependencies installed"
}

install_deps_arch() {
    info "Installing dependencies for Arch Linux..."
    sudo pacman -Sy --noconfirm \
        python python-pip \
        ffmpeg \
        openssl libffi \
        base-devel \
        2>/dev/null || { error "Package installation failed"; return 1; }
    success "Arch Linux dependencies installed"
}

install_deps_macos() {
    info "Installing dependencies for macOS..."
    if ! command -v brew &>/dev/null; then
        warn "Homebrew not found. Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || {
            error "Homebrew installation failed"; return 1;
        }
    fi
    brew install python3 ffmpeg || { error "brew install failed"; return 1; }
    success "macOS dependencies installed"
}

install_deps_termux() {
    info "Installing dependencies for Termux..."
    pkg update -y || { error "pkg update failed"; return 1; }
    pkg install -y python python-pip ffmpeg libffi openssl || {
        error "pkg install failed"; return 1;
    }
    success "Termux dependencies installed"
}

install_system_deps() {
    local os
    os=$(detect_os)
    verbose "Detected OS: ${os}"

    case "${os}" in
        ubuntu)   install_deps_ubuntu ;;
        debian)   install_deps_debian ;;
        kali)     install_deps_kali ;;
        linuxmint|pop) install_deps_ubuntu ;;
        fedora)   install_deps_fedora ;;
        centos|rhel|rocky|almalinux) install_deps_fedora ;;
        arch|manjaro|endeavouros) install_deps_arch ;;
        macos)    install_deps_macos ;;
        termux)   install_deps_termux ;;
        *)
            warn "Unknown OS: ${os}. Attempting generic installation..."
            if command -v apt-get &>/dev/null; then
                install_deps_ubuntu
            elif command -v dnf &>/dev/null; then
                install_deps_fedora
            elif command -v pacman &>/dev/null; then
                install_deps_arch
            elif command -v brew &>/dev/null; then
                install_deps_macos
            else
                error "Cannot determine package manager. Please install manually:"
                error "  python3 (>=3.10), pip, ffmpeg"
                return 1
            fi
            ;;
    esac
}

# ==============================================================================
# Virtual Environment Setup
# ==============================================================================

create_venv() {
    step "Creating virtual environment..."
    verbose "VENV_DIR: ${VENV_DIR}"

    if [[ -d "${VENV_DIR}" ]] && [[ "${UPDATE_MODE}" -eq 0 ]]; then
        warn "Virtual environment already exists at ${VENV_DIR}"
        read -rp "Remove and recreate? [y/N] " -n 1 reply
        echo
        if [[ "${reply,,}" == "y" ]]; then
            rm -rf "${VENV_DIR}"
        else
            info "Using existing virtual environment"
            return 0
        fi
    fi

    if [[ -d "${VENV_DIR}" ]] && [[ "${UPDATE_MODE}" -eq 1 ]]; then
        info "Updating existing virtual environment..."
        rm -rf "${VENV_DIR}"
    fi

    mkdir -p "${INSTALL_DIR}"

    python3 -m venv "${VENV_DIR}" || {
        error "Failed to create virtual environment"
        error "Make sure python3-venv is installed"
        return 1
    }

    success "Virtual environment created at ${VENV_DIR}"
    log "Virtual environment created: ${VENV_DIR}"
}

# ==============================================================================
# Python Dependencies
# ==============================================================================

install_python_deps() {
    step "Installing Python dependencies..."
    verbose "Activating virtual environment..."

    # Activate venv
    source "${VENV_DIR}/bin/activate" || {
        error "Failed to activate virtual environment"
        return 1
    }

    # Upgrade pip
    info "Upgrading pip..."
    pip install --upgrade pip setuptools wheel 2>/dev/null || {
        warn "pip upgrade had issues, continuing..."
    }

    # Install requirements
    if [[ -f "${PROJECT_DIR}/requirements.txt" ]]; then
        info "Installing from requirements.txt..."
        pip install -r "${PROJECT_DIR}/requirements.txt" 2>/dev/null || {
            error "Failed to install requirements.txt"
            return 1
        }
        success "Requirements installed"
    else
        warn "requirements.txt not found, skipping"
    fi

    # Install package in editable mode
    if [[ -f "${PROJECT_DIR}/setup.py" ]] || [[ -f "${PROJECT_DIR}/pyproject.toml" ]]; then
        info "Installing RS Downloader in editable mode..."
        pip install -e "${PROJECT_DIR}" 2>/dev/null || {
            warn "Editable install had issues, trying standard install..."
            pip install "${PROJECT_DIR}" 2>/dev/null || {
                error "Failed to install RS Downloader package"
                return 1
            }
        }
        success "RS Downloader package installed"
    else
        warn "No setup.py or pyproject.toml found, skipping package install"
    fi

    log "Python dependencies installed successfully"
}

# ==============================================================================
# Symlink Creation
# ==============================================================================

create_symlink() {
    step "Creating rsdl command symlink..."

    local target="${VENV_DIR}/bin/rsdl"

    if [[ ! -f "${target}" ]]; then
        # Create a wrapper script if the entry point doesn't exist yet
        verbose "Entry point not found in venv, creating wrapper script..."
        mkdir -p "${INSTALL_DIR}/bin"
        cat > "${INSTALL_DIR}/bin/rsdl" << 'WRAPPER'
#!/usr/bin/env bash
# RS Downloader wrapper script
source "${HOME}/.rs-downloader/venv/bin/activate" 2>/dev/null || true
python3 -m rs_toolkit "$@"
WRAPPER
        chmod +x "${INSTALL_DIR}/bin/rsdl"
        target="${INSTALL_DIR}/bin/rsdl"
    fi

    # Remove existing symlink
    if [[ -L "${SYMLINK_PATH}" ]]; then
        sudo rm -f "${SYMLINK_PATH}"
    elif [[ -f "${SYMLINK_PATH}" ]]; then
        sudo rm -f "${SYMLINK_PATH}"
    fi

    # Create new symlink
    sudo ln -sf "${target}" "${SYMLINK_PATH}" || {
        warn "Cannot create symlink at ${SYMLINK_PATH} (no sudo access?)"
        info "Adding to PATH via shell profile instead..."
        add_to_path
        return 0
    }

    success "Symlink created: ${SYMLINK_PATH} -> ${target}"
    log "Symlink created: ${SYMLINK_PATH}"
}

add_to_path() {
    local path_line="export PATH=\"\${HOME}/.rs-downloader/bin:\${PATH}\""
    local shell_rc="${HOME}/.bashrc"

    if [[ -n "${ZSH_VERSION:-}" ]]; then
        shell_rc="${HOME}/.zshrc"
    fi

    if ! grep -q "rs-downloader/bin" "${shell_rc}" 2>/dev/null; then
        echo "" >> "${shell_rc}"
        echo "# RS Downloader" >> "${shell_rc}"
        echo "${path_line}" >> "${shell_rc}"
        info "Added RS Downloader to PATH in ${shell_rc}"
        info "Run 'source ${shell_rc}' or restart your shell"
    else
        info "RS Downloader already in PATH"
    fi
}

# ==============================================================================
# Configuration Setup
# ==============================================================================

setup_config() {
    step "Setting up configuration..."
    mkdir -p "${CONFIG_DIR}"
    mkdir -p "${CACHE_DIR}"

    if [[ ! -f "${CONFIG_DIR}/config.json" ]]; then
        if [[ -f "${PROJECT_DIR}/config/profiles/default.json" ]]; then
            cp "${PROJECT_DIR}/config/profiles/default.json" "${CONFIG_DIR}/config.json"
            success "Default configuration copied"
        else
            info "No default config template found, will be created on first run"
        fi
    else
        info "Configuration already exists, preserving"
    fi

    log "Configuration setup complete"
}

# ==============================================================================
# Health Check
# ==============================================================================

health_check() {
    echo ""
    step "RS Downloader Health Check"
    echo "═══════════════════════════════════════"

    local passed=0
    local failed=0

    # Check Python
    if command -v python3 &>/dev/null; then
        local py_ver
        py_ver=$(python3 --version 2>&1)
        success "Python: ${py_ver}"
        ((passed++))
    else
        error "Python3: NOT FOUND"
        ((failed++))
    fi

    # Check pip
    if command -v pip3 &>/dev/null || command -v pip &>/dev/null; then
        success "pip: installed"
        ((passed++))
    else
        error "pip: NOT FOUND"
        ((failed++))
    fi

    # Check ffmpeg
    if command -v ffmpeg &>/dev/null; then
        local ff_ver
        ff_ver=$(ffmpeg -version 2>&1 | head -1)
        success "ffmpeg: ${ff_ver}"
        ((passed++))
    else
        warn "ffmpeg: NOT FOUND (optional, required for video conversion)"
        ((failed++))
    fi

    # Check venv
    if [[ -d "${VENV_DIR}" ]]; then
        success "Virtual environment: ${VENV_DIR}"
        ((passed++))
    else
        error "Virtual environment: NOT FOUND"
        ((failed++))
    fi

    # Check rsdl command
    if command -v rsdl &>/dev/null; then
        success "rsdl command: $(command -v rsdl)"
        ((passed++))
    else
        warn "rsdl command: NOT IN PATH"
        ((failed++))
    fi

    # Check config
    if [[ -f "${CONFIG_DIR}/config.json" ]]; then
        success "Configuration: ${CONFIG_DIR}/config.json"
        ((passed++))
    else
        warn "Configuration: NOT FOUND (will be created on first run)"
        ((failed++))
    fi

    echo "═══════════════════════════════════════"
    echo -e "  ${GREEN}Passed: ${passed}${NC}  ${RED}Failed: ${failed}${NC}"
    echo "═══════════════════════════════════════"

    if [[ "${failed}" -eq 0 ]]; then
        success "All checks passed! RS Downloader is ready."
        return 0
    else
        warn "Some checks failed. Run install.sh to fix issues."
        return 1
    fi
}

# ==============================================================================
# Update
# ==============================================================================

do_update() {
    step "Updating RS Downloader..."
    UPDATE_MODE=1

    if [[ -d "${PROJECT_DIR}/.git" ]]; then
        info "Pulling latest changes..."
        git -C "${PROJECT_DIR}" pull || warn "git pull failed, continuing..."
    fi

    create_venv
    install_python_deps
    create_symlink
    success "RS Downloader updated to v${INSTALLER_VERSION}!"
}

# ==============================================================================
# Usage
# ==============================================================================

usage() {
    echo -e "${BOLD}RS Downloader v${INSTALLER_VERSION} Installer${NC}"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help, -h       Show this help message"
    echo "  --update, -u     Update existing installation"
    echo "  --uninstall      Uninstall RS Downloader"
    echo "  --check, -c      Run health check"
    echo "  --skip-deps      Skip system dependency installation"
    echo "  -v, --verbose    Verbose output"
    echo ""
    echo "Examples:"
    echo "  $0                    # Fresh install"
    echo "  $0 --update           # Update installation"
    echo "  $0 --check            # Health check"
    echo "  $0 -v --skip-deps     # Verbose install, skip deps"
    echo ""
}

# ==============================================================================
# Parse Arguments
# ==============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help|-h)
                usage
                exit 0
                ;;
            --update|-u)
                UPDATE_MODE=1
                shift
                ;;
            --uninstall)
                UNINSTALL_MODE=1
                shift
                ;;
            --check|-c)
                CHECK_MODE=1
                shift
                ;;
            --skip-deps)
                SKIP_DEPS=1
                shift
                ;;
            -v|--verbose)
                VERBOSE=1
                shift
                ;;
            *)
                error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

# ==============================================================================
# Main Installation
# ==============================================================================

main_install() {
    banner
    info "OS: $(detect_os_name)"
    info "Install dir: ${INSTALL_DIR}"
    info "Project dir: ${PROJECT_DIR}"
    echo ""

    # Step 1: System dependencies
    if [[ "${SKIP_DEPS}" -eq 0 ]]; then
        step "1/5 Installing system dependencies..."
        install_system_deps || {
            error "System dependency installation failed"
            error "Try: $0 --skip-deps to skip this step"
            exit 1
        }
    else
        step "1/5 Skipping system dependencies (--skip-deps)"
    fi
    echo ""

    # Step 2: Virtual environment
    step "2/5 Setting up virtual environment..."
    create_venv || {
        error "Virtual environment setup failed"
        exit 1
    }
    echo ""

    # Step 3: Python dependencies
    step "3/5 Installing Python dependencies..."
    install_python_deps || {
        error "Python dependency installation failed"
        exit 1
    }
    echo ""

    # Step 4: Configuration
    step "4/5 Setting up configuration..."
    setup_config || {
        warn "Configuration setup had issues"
    }
    echo ""

    # Step 5: Symlink
    step "5/5 Creating command symlink..."
    create_symlink || {
        warn "Symlink creation had issues"
    }
    echo ""

    # Done
    success "╔══════════════════════════════════════════════╗"
    success "║  RS Downloader v${INSTALLER_VERSION} installed successfully!  ║"
    success "╚══════════════════════════════════════════════╝"
    echo ""
    info "Run 'rsdl --help' to get started"
    info "Config: ${CONFIG_DIR}/config.json"
    info "Cache:  ${CACHE_DIR}"
    echo ""

    log "Installation completed successfully"
}

# ==============================================================================
# Entry Point
# ==============================================================================

main() {
    parse_args "$@"

    # Create log directory
    mkdir -p "${INSTALL_DIR}" 2>/dev/null || true

    # Handle modes
    if [[ "${CHECK_MODE}" -eq 1 ]]; then
        health_check
        exit $?
    fi

    if [[ "${UNINSTALL_MODE}" -eq 1 ]]; then
        bash "${PROJECT_DIR}/uninstall.sh"
        exit $?
    fi

    if [[ "${UPDATE_MODE}" -eq 1 ]]; then
        banner
        do_update
        exit $?
    fi

    # Fresh install
    main_install
}

main "$@"
