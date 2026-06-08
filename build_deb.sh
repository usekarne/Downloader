#!/usr/bin/env bash
# ==============================================================================
# RS Downloader v10.0.0 - .deb Package Builder
# Author: RAJSARASWATI JATAV (RS)
# License: MIT
# ==============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; }
step()    { echo -e "${CYAN}[STEP]${NC} ${BOLD}$1${NC}"; }

# ==============================================================================
# Configuration
# ==============================================================================

PACKAGE_NAME="rs-downloader"
PACKAGE_VERSION=""
PACKAGE_ARCH="all"
PACKAGE_MAINTAINER="RAJSARASWATI JATAV <rs@t3rmuxk1ng.dev>"
PACKAGE_DESCRIPTION="The Ultimate Download Toolkit by RS - Video, Audio, Playlist & Batch Downloading"
PACKAGE_HOMEPAGE="https://github.com/T3rmuxk1ng/rs-downloader"
PACKAGE_LICENSE="MIT"
PACKAGE_SECTION="net"
PACKAGE_PRIORITY="optional"

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build"
DEB_DIR="${BUILD_DIR}/${PACKAGE_NAME}"
DEBIAN_DIR="${DEB_DIR}/DEBIAN"

# ==============================================================================
# Version Extraction
# ==============================================================================

extract_version() {
    step "Extracting version..."

    # Try to read from core/__init__.py first
    local init_file="${SCRIPT_DIR}/rs_toolkit/__init__.py"
    if [[ -f "${init_file}" ]]; then
        PACKAGE_VERSION=$(grep -oP '__version__\s*=\s*["\x27]\K[^"\x27]+' "${init_file}" 2>/dev/null || true)
    fi

    # Fallback to pyproject.toml
    if [[ -z "${PACKAGE_VERSION}" ]] && [[ -f "${SCRIPT_DIR}/pyproject.toml" ]]; then
        PACKAGE_VERSION=$(grep -oP '^version\s*=\s*"\K[^"]+' "${SCRIPT_DIR}/pyproject.toml" 2>/dev/null || true)
    fi

    # Fallback to setup.py
    if [[ -z "${PACKAGE_VERSION}" ]] && [[ -f "${SCRIPT_DIR}/setup.py" ]]; then
        PACKAGE_VERSION=$(grep -oP 'version\s*=\s*["\x27]\K[^"\x27]+' "${SCRIPT_DIR}/setup.py" 2>/dev/null | head -1 || true)
    fi

    # Ultimate fallback
    if [[ -z "${PACKAGE_VERSION}" ]]; then
        warn "Could not extract version from source files"
        read -rp "Enter version [10.0.0]: " PACKAGE_VERSION
        PACKAGE_VERSION="${PACKAGE_VERSION:-10.0.0}"
    fi

    success "Version: ${PACKAGE_VERSION}"
}

# ==============================================================================
# Package Directory Structure
# ==============================================================================

create_package_dirs() {
    step "Creating package directory structure..."

    # Clean previous build
    if [[ -d "${BUILD_DIR}" ]]; then
        rm -rf "${BUILD_DIR}"
    fi

    # Create directory tree
    mkdir -p "${DEBIAN_DIR}"
    mkdir -p "${DEB_DIR}/opt/rs-downloader"
    mkdir -p "${DEB_DIR}/usr/bin"
    mkdir -p "${DEB_DIR}/usr/share/doc/rs-downloader"
    mkdir -p "${DEB_DIR}/usr/share/man/man1"
    mkdir -p "${DEB_DIR}/etc/rs-downloader/profiles"
    mkdir -p "${DEB_DIR}/var/lib/rs-downloader"
    mkdir -p "${DEB_DIR}/var/cache/rs-downloader"
    mkdir -p "${DEB_DIR}/var/log/rs-downloader"

    success "Package directory structure created"
}

# ==============================================================================
# Copy Files to Package Directory
# ==============================================================================

copy_files() {
    step "Copying application files..."

    # Copy Python package
    if [[ -d "${SCRIPT_DIR}/rs_toolkit" ]]; then
        cp -r "${SCRIPT_DIR}/rs_toolkit" "${DEB_DIR}/opt/rs-downloader/"
        success "Copied rs_toolkit/"
    else
        warn "rs_toolkit/ not found, skipping"
    fi

    # Copy requirements and setup files
    if [[ -f "${SCRIPT_DIR}/requirements.txt" ]]; then
        cp "${SCRIPT_DIR}/requirements.txt" "${DEB_DIR}/opt/rs-downloader/"
        success "Copied requirements.txt"
    fi

    if [[ -f "${SCRIPT_DIR}/setup.py" ]]; then
        cp "${SCRIPT_DIR}/setup.py" "${DEB_DIR}/opt/rs-downloader/"
        success "Copied setup.py"
    fi

    if [[ -f "${SCRIPT_DIR}/pyproject.toml" ]]; then
        cp "${SCRIPT_DIR}/pyproject.toml" "${DEB_DIR}/opt/rs-downloader/"
        success "Copied pyproject.toml"
    fi

    # Copy config profiles
    if [[ -d "${SCRIPT_DIR}/config/profiles" ]]; then
        cp -r "${SCRIPT_DIR}/config/profiles/"* "${DEB_DIR}/etc/rs-downloader/profiles/"
        success "Copied config profiles"
    fi

    # Copy documentation
    if [[ -f "${SCRIPT_DIR}/README.md" ]]; then
        cp "${SCRIPT_DIR}/README.md" "${DEB_DIR}/usr/share/doc/rs-downloader/"
        success "Copied README.md"
    fi

    if [[ -f "${SCRIPT_DIR}/LICENSE" ]]; then
        cp "${SCRIPT_DIR}/LICENSE" "${DEB_DIR}/usr/share/doc/rs-downloader/"
        success "Copied LICENSE"
    fi

    # Copy changelog
    if [[ -f "${SCRIPT_DIR}/CHANGELOG.md" ]]; then
        cp "${SCRIPT_DIR}/CHANGELOG.md" "${DEB_DIR}/usr/share/doc/rs-downloader/"
    fi

    success "All files copied"
}

# ==============================================================================
# Generate DEBIAN/control
# ==============================================================================

generate_control() {
    step "Generating DEBIAN/control..."

    # Calculate installed size (in KB)
    local installed_size
    installed_size=$(du -sk "${DEB_DIR}" 2>/dev/null | cut -f1 || echo "10240")

    cat > "${DEBIAN_DIR}/control" << EOF
Package: ${PACKAGE_NAME}
Version: ${PACKAGE_VERSION}
Section: ${PACKAGE_SECTION}
Priority: ${PACKAGE_PRIORITY}
Architecture: ${PACKAGE_ARCH}
Essential: no
Installed-Size: ${installed_size}
Maintainer: ${PACKAGE_MAINTAINER}
Homepage: ${PACKAGE_HOMEPAGE}
Depends: python3 (>= 3.10), python3-pip, ffmpeg, python3-venv
Recommends: python3-dev, libssl-dev, libffi-dev, build-essential
Suggests: yt-dlp
Conflicts: rs-downloader-nightly
Replaces: rs-downloader-beta
Provides: rs-downloader
Description: ${PACKAGE_DESCRIPTION}
 RS Downloader is the ultimate download toolkit by RS (RAJSARASWATI JATAV).
 It supports video, audio, playlist, and batch downloading from hundreds
 of websites. Built with Python, it features a rich CLI, async downloads,
 progress tracking, and extensive configuration options.
 .
 Features:
  - Video downloading from 1000+ sites (via yt-dlp)
  - Audio extraction and conversion
  - Playlist and channel downloading
  - Batch downloading from file lists
  - Resume interrupted downloads
  - Format conversion via ffmpeg
  - Proxy and authentication support
  - Rich progress bars and logging
  - Configurable download profiles
  - Prometheus metrics for monitoring
EOF

    success "DEBIAN/control generated"
}

# ==============================================================================
# Generate postinst Script
# ==============================================================================

generate_postinst() {
    step "Generating DEBIAN/postinst..."

    cat > "${DEBIAN_DIR}/postinst" << 'POSTINST'
#!/bin/bash
set -e

# RS Downloader - Post-installation script

VENV_DIR="/opt/rs-downloader/venv"
APP_DIR="/opt/rs-downloader"

echo "Setting up RS Downloader..."

# Create virtual environment
if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv "${VENV_DIR}" || {
        echo "ERROR: Failed to create virtual environment" >&2
        exit 1
    }
fi

# Install dependencies
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip setuptools wheel -q 2>/dev/null || true

if [ -f "${APP_DIR}/requirements.txt" ]; then
    pip install -r "${APP_DIR}/requirements.txt" -q 2>/dev/null || true
fi

if [ -f "${APP_DIR}/setup.py" ] || [ -f "${APP_DIR}/pyproject.toml" ]; then
    pip install -e "${APP_DIR}" -q 2>/dev/null || true
fi

deactivate || true

# Create symlink
if [ -f "${VENV_DIR}/bin/rsdl" ]; then
    ln -sf "${VENV_DIR}/bin/rsdl" /usr/bin/rsdl
else
    # Create wrapper
    cat > /usr/bin/rsdl << 'WRAPPER'
#!/bin/bash
source /opt/rs-downloader/venv/bin/activate 2>/dev/null || true
python3 -m rs_toolkit "$@"
WRAPPER
    chmod +x /usr/bin/rsdl
fi

# Set permissions
chmod -R 755 /opt/rs-downloader
chown -R root:root /opt/rs-downloader

# Create user config directory
mkdir -p /etc/rs-downloader/profiles
chmod 755 /etc/rs-downloader

echo "RS Downloader installed successfully. Run 'rsdl --help' to get started."
POSTINST

    chmod 755 "${DEBIAN_DIR}/postinst"
    success "DEBIAN/postinst generated"
}

# ==============================================================================
# Generate prerm Script
# ==============================================================================

generate_prerm() {
    step "Generating DEBIAN/prerm..."

    cat > "${DEBIAN_DIR}/prerm" << 'PRERM'
#!/bin/bash
set -e

# RS Downloader - Pre-removal script

echo "Stopping RS Downloader services..."

# Kill any running rsdl processes
if pgrep -f "rs_toolkit" >/dev/null 2>&1; then
    echo "Terminating running RS Downloader processes..."
    pkill -f "rs_toolkit" 2>/dev/null || true
    sleep 1
fi

# Remove symlink
rm -f /usr/bin/rsdl 2>/dev/null || true
rm -f /usr/local/bin/rsdl 2>/dev/null || true

echo "RS Downloader pre-removal complete."
PRERM

    chmod 755 "${DEBIAN_DIR}/prerm"
    success "DEBIAN/prerm generated"
}

# ==============================================================================
# Generate postrm Script
# ==============================================================================

generate_postrm() {
    step "Generating DEBIAN/postrm..."

    cat > "${DEBIAN_DIR}/postrm" << 'POSTRM'
#!/bin/bash
set -e

# RS Downloader - Post-removal script

VENV_DIR="/opt/rs-downloader/venv"
APP_DIR="/opt/rs-downloader"

echo "Cleaning up RS Downloader..."

# Remove virtual environment
if [ -d "${VENV_DIR}" ]; then
    rm -rf "${VENV_DIR}"
    echo "Removed virtual environment."
fi

# Remove application directory (only if empty or on purge)
if [ "$1" = "purge" ]; then
    # Remove config
    if [ -d /etc/rs-downloader ]; then
        rm -rf /etc/rs-downloader
        echo "Removed configuration."
    fi

    # Remove cache
    if [ -d /var/cache/rs-downloader ]; then
        rm -rf /var/cache/rs-downloader
        echo "Removed cache."
    fi

    # Remove logs
    if [ -d /var/log/rs-downloader ]; then
        rm -rf /var/log/rs-downloader
        echo "Removed logs."
    fi

    # Remove user config
    if [ -d "${HOME}/.rs-downloader" ]; then
        echo "Note: User config at ~/.rs-downloader was preserved."
        echo "To remove: rm -rf ~/.rs-downloader"
    fi

    # Remove app directory
    rm -rf "${APP_DIR}"
    echo "Removed application directory."
fi

# Remove any remaining symlinks
rm -f /usr/bin/rsdl 2>/dev/null || true
rm -f /usr/local/bin/rsdl 2>/dev/null || true

echo "RS Downloader post-removal complete."
POSTRM

    chmod 755 "${DEBIAN_DIR}/postrm"
    success "DEBIAN/postrm generated"
}

# ==============================================================================
# Generate conffiles
# ==============================================================================

generate_conffiles() {
    step "Generating DEBIAN/conffiles..."

    cat > "${DEBIAN_DIR}/conffiles" << EOF
/etc/rs-downloader/profiles/default.json
/etc/rs-downloader/profiles/production.json
EOF

    success "DEBIAN/conffiles generated"
}

# ==============================================================================
# Generate changelog
# ==============================================================================

generate_changelog() {
    step "Generating DEBIAN changelog..."

    local changelog_dir="${DEB_DIR}/usr/share/doc/rs-downloader"
    local date_str
    date_str=$(date -R 2>/dev/null || date)

    cat > "${changelog_dir}/changelog.Debian" << EOF
rs-downloader (${PACKAGE_VERSION}) unstable; urgency=medium

  * Release v${PACKAGE_VERSION}
  * The Ultimate Download Toolkit by RAJSARASWATI JATAV (RS)
  * Video, Audio, Playlist & Batch Downloading
  * Rich CLI interface with progress tracking
  - Async download engine
  - 1000+ site support via yt-dlp
  - Format conversion via ffmpeg
  - Proxy and authentication support
  - Prometheus metrics integration
  - Configurable download profiles

 -- ${PACKAGE_MAINTAINER}  ${date_str}
EOF

    gzip -f "${changelog_dir}/changelog.Debian" 2>/dev/null || true
    success "DEBIAN changelog generated"
}

# ==============================================================================
# Build Package
# ==============================================================================

build_package() {
    step "Building .deb package..."

    local output_file="${BUILD_DIR}/${PACKAGE_NAME}_${PACKAGE_VERSION}_${PACKAGE_ARCH}.deb"

    # Build with dpkg-deb
    dpkg-deb --build "${DEB_DIR}" "${output_file}" || {
        error "dpkg-deb build failed"
        error "Make sure dpkg-deb is installed (apt install dpkg-dev)"
        exit 1
    }

    # Verify the package
    if [[ -f "${output_file}" ]]; then
        local pkg_size
        pkg_size=$(du -h "${output_file}" | cut -f1)
        success "Package built successfully!"
        echo ""
        echo -e "  ${BOLD}Output:${NC} ${output_file}"
        echo -e "  ${BOLD}Size:${NC}   ${pkg_size}"
        echo ""
        info "Install with: sudo dpkg -i ${output_file}"
        info "Or: sudo apt install ${output_file}"

        # Lint the package if lintian is available
        if command -v lintian &>/dev/null; then
            echo ""
            info "Running lintian..."
            lintian "${output_file}" 2>/dev/null || true
        fi
    else
        error "Package build failed - output file not found"
        exit 1
    fi
}

# ==============================================================================
# Cleanup
# ==============================================================================

cleanup() {
    step "Cleaning up build artifacts..."
    # Keep the .deb file, remove the build directory structure
    # Uncomment the following line to remove build dir after packaging:
    # rm -rf "${DEB_DIR}"
    info "Build directory preserved at: ${BUILD_DIR}"
}

# ==============================================================================
# Usage
# ==============================================================================

usage() {
    echo -e "${BOLD}RS Downloader v10.0.0 .deb Package Builder${NC}"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help, -h       Show this help message"
    echo "  --clean          Clean build directory and exit"
    echo "  --version VER    Override version number"
    echo ""
}

# ==============================================================================
# Main
# ==============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help|-h)
                usage
                exit 0
                ;;
            --clean)
                rm -rf "${BUILD_DIR}"
                echo "Build directory cleaned."
                exit 0
                ;;
            --version)
                PACKAGE_VERSION="$2"
                shift 2
                ;;
            *)
                error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    echo -e "${CYAN}"
    echo "  ╔══════════════════════════════════════════════════╗"
    echo "  ║     RS DOWNLOADER .DEB PACKAGE BUILDER           ║"
    echo "  ╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"

    # Check for dpkg-deb
    if ! command -v dpkg-deb &>/dev/null; then
        error "dpkg-deb is required but not installed"
        error "Install with: sudo apt install dpkg-dev"
        exit 1
    fi

    # Run build steps
    extract_version
    create_package_dirs
    copy_files
    generate_control
    generate_postinst
    generate_prerm
    generate_postrm
    generate_conffiles
    generate_changelog
    build_package
    cleanup

    echo ""
    success "Build complete! 🎉"
}

main "$@"
