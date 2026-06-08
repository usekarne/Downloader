#!/usr/bin/env bash
# ==============================================================================
# RS Downloader v10.0.0 - Uninstaller
# Author: RAJSARASWATI JATAV (RS)
# License: MIT
# ==============================================================================

set -euo pipefail

# Paths
INSTALL_DIR="${HOME}/.rs-downloader"
VENV_DIR="${INSTALL_DIR}/venv"
CONFIG_DIR="${INSTALL_DIR}/config"
CACHE_DIR="${INSTALL_DIR}/cache"
DATA_DIR="${INSTALL_DIR}/data"
LOG_DIR="${INSTALL_DIR}/logs"
SYMLINK_PATH="/usr/local/bin/rsdl"
LOCAL_BIN_SYMLINK="${HOME}/.local/bin/rsdl"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Flags
KEEP_DOWNLOADS=0
FORCE=0

info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# ==============================================================================
# Banner
# ==============================================================================

uninstall_banner() {
    echo -e "${RED}"
    echo -e "  ╔══════════════════════════════════════════════════╗"
    echo -e "  ║          RS DOWNLOADER UNINSTALLER               ║"
    echo -e "  ╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# ==============================================================================
# Confirmation
# ==============================================================================

confirm_uninstall() {
    if [[ "${FORCE}" -eq 0 ]]; then
        echo -e "${YELLOW}⚠  This will remove RS Downloader from your system.${NC}"
        echo ""
        echo "  The following will be removed:"
        echo "    • Virtual environment: ${VENV_DIR}"
        echo "    • Cache: ${CACHE_DIR}"
        echo "    • Logs: ${LOG_DIR}"
        echo "    • Command symlink: ${SYMLINK_PATH}"
        echo ""
        read -rp "  Are you sure you want to uninstall? [y/N] " -n 1 reply
        echo
        if [[ "${reply,,}" != "y" ]]; then
            info "Uninstall cancelled."
            exit 0
        fi
    fi
}

# ==============================================================================
# Remove Virtual Environment
# ==============================================================================

remove_venv() {
    info "Removing virtual environment..."
    if [[ -d "${VENV_DIR}" ]]; then
        rm -rf "${VENV_DIR}"
        success "Virtual environment removed"
    else
        info "Virtual environment not found, skipping"
    fi
}

# ==============================================================================
# Remove Symlink
# ==============================================================================

remove_symlink() {
    info "Removing command symlinks..."

    # Remove /usr/local/bin symlink
    if [[ -L "${SYMLINK_PATH}" ]] || [[ -f "${SYMLINK_PATH}" ]]; then
        sudo rm -f "${SYMLINK_PATH}" 2>/dev/null && \
            success "Removed ${SYMLINK_PATH}" || \
            warn "Could not remove ${SYMLINK_PATH}"
    else
        info "Symlink ${SYMLINK_PATH} not found"
    fi

    # Remove ~/.local/bin symlink
    if [[ -L "${LOCAL_BIN_SYMLINK}" ]] || [[ -f "${LOCAL_BIN_SYMLINK}" ]]; then
        rm -f "${LOCAL_BIN_SYMLINK}" 2>/dev/null && \
            success "Removed ${LOCAL_BIN_SYMLINK}" || \
            warn "Could not remove ${LOCAL_BIN_SYMLINK}"
    else
        info "Symlink ${LOCAL_BIN_SYMLINK} not found"
    fi

    # Remove wrapper script
    if [[ -f "${INSTALL_DIR}/bin/rsdl" ]]; then
        rm -f "${INSTALL_DIR}/bin/rsdl"
        success "Removed wrapper script"
    fi
}

# ==============================================================================
# Remove Configuration
# ==============================================================================

remove_config() {
    info "Removing configuration..."

    if [[ -d "${CONFIG_DIR}" ]]; then
        if [[ "${FORCE}" -eq 0 ]]; then
            read -rp "  Delete configuration files? [y/N] " -n 1 reply
            echo
            if [[ "${reply,,}" == "y" ]]; then
                rm -rf "${CONFIG_DIR}"
                success "Configuration removed"
            else
                info "Configuration preserved at ${CONFIG_DIR}"
            fi
        else
            rm -rf "${CONFIG_DIR}"
            success "Configuration removed (forced)"
        fi
    else
        info "Configuration directory not found"
    fi
}

# ==============================================================================
# Remove Cache
# ==============================================================================

remove_cache() {
    info "Removing cache..."
    if [[ -d "${CACHE_DIR}" ]]; then
        rm -rf "${CACHE_DIR}"
        success "Cache removed"
    else
        info "Cache directory not found"
    fi
}

# ==============================================================================
# Remove Logs
# ==============================================================================

remove_logs() {
    info "Removing logs..."
    if [[ -d "${LOG_DIR}" ]]; then
        rm -rf "${LOG_DIR}"
        success "Logs removed"
    else
        info "Log directory not found"
    fi
}

# ==============================================================================
# Remove Data / Keep Downloads Option
# ==============================================================================

remove_data() {
    info "Removing data..."

    if [[ -d "${DATA_DIR}" ]]; then
        if [[ "${KEEP_DOWNLOADS}" -eq 1 ]]; then
            info "Keeping downloads (--keep-downloads flag)"
            # Remove everything except downloads
            find "${DATA_DIR}" -mindepth 1 -maxdepth 1 ! -name "downloads" -exec rm -rf {} +
            success "Data removed (downloads preserved)"
        else
            if [[ "${FORCE}" -eq 0 ]]; then
                read -rp "  Delete downloaded files? [y/N] " -n 1 reply
                echo
                if [[ "${reply,,}" == "y" ]]; then
                    rm -rf "${DATA_DIR}"
                    success "Data removed"
                else
                    info "Data preserved at ${DATA_DIR}"
                fi
            else
                rm -rf "${DATA_DIR}"
                success "Data removed (forced)"
            fi
        fi
    else
        info "Data directory not found"
    fi
}

# ==============================================================================
# Clean Shell Integration
# ==============================================================================

clean_shell_integration() {
    info "Cleaning shell integration..."

    local shell_files=("${HOME}/.bashrc" "${HOME}/.zshrc" "${HOME}/.profile" "${HOME}/.bash_profile")

    for rc_file in "${shell_files[@]}"; do
        if [[ -f "${rc_file}" ]]; then
            if grep -q "rs-downloader" "${rc_file}" 2>/dev/null; then
                # Remove RS Downloader lines from shell config
                sed -i '/# RS Downloader/d' "${rc_file}" 2>/dev/null || true
                sed -i '/rs-downloader\/bin/d' "${rc_file}" 2>/dev/null || true
                success "Cleaned ${rc_file}"
            fi
        fi
    done
}

# ==============================================================================
# Remove Install Directory
# ==============================================================================

remove_install_dir() {
    info "Removing install directory..."
    if [[ -d "${INSTALL_DIR}" ]]; then
        # Check if anything is left
        local remaining
        remaining=$(find "${INSTALL_DIR}" -mindepth 1 | wc -l)
        if [[ "${remaining}" -eq 0 ]]; then
            rmdir "${INSTALL_DIR}"
            success "Install directory removed"
        else
            info "Install directory not empty, keeping: ${INSTALL_DIR}"
            info "To fully remove: rm -rf ${INSTALL_DIR}"
        fi
    else
        info "Install directory not found"
    fi
}

# ==============================================================================
# Usage
# ==============================================================================

usage() {
    echo -e "${BOLD}RS Downloader v10.0.0 Uninstaller${NC}"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help, -h            Show this help message"
    echo "  --force, -f           Force uninstall without confirmation"
    echo "  --keep-downloads      Preserve downloaded files"
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
            --force|-f)
                FORCE=1
                shift
                ;;
            --keep-downloads)
                KEEP_DOWNLOADS=1
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
# Main
# ==============================================================================

main() {
    parse_args "$@"
    uninstall_banner
    confirm_uninstall

    echo ""
    info "Starting uninstallation..."
    echo ""

    remove_symlink
    remove_venv
    remove_cache
    remove_logs
    remove_config
    remove_data
    clean_shell_integration
    remove_install_dir

    echo ""
    success "╔══════════════════════════════════════════════╗"
    success "║  RS Downloader has been uninstalled.         ║"
    success "╚══════════════════════════════════════════════╝"
    echo ""
    info "To reinstall: ./install.sh"
    echo ""
}

main "$@"
