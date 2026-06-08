#!/usr/bin/env python3
"""
RS Downloader v10.0.0 - Auto Virtual Environment Setup
Author: RAJSARASWATI JATAV (RS)
License: MIT

Automatically creates a virtual environment, installs dependencies,
and validates the installation.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


# Configuration
INSTALL_DIR = Path.home() / ".rs-downloader"
VENV_DIR = INSTALL_DIR / "venv"
PROJECT_DIR = Path(__file__).parent.resolve()
REQUIREMENTS_FILE = PROJECT_DIR / "requirements.txt"

# Colors for terminal output
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
NC = "\033[0m"


def print_colored(color: str, prefix: str, message: str) -> None:
    """Print a colored message with a prefix."""
    print(f"{color}[{prefix}]{NC} {message}")


def info(msg: str) -> None:
    print_colored(BLUE, "INFO", msg)


def success(msg: str) -> None:
    print_colored(GREEN, "OK", msg)


def warn(msg: str) -> None:
    print_colored(YELLOW, "WARN", msg)


def error(msg: str) -> None:
    print_colored(RED, "ERROR", msg)


def step(msg: str) -> None:
    print(f"\n{CYAN}[STEP]{NC} {BOLD}{msg}{NC}")


def check_python_version() -> bool:
    """Check if Python version meets minimum requirement (3.10)."""
    step("Checking Python version...")
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    if version.major == 3 and version.minor >= 10:
        success(f"Python {version_str} detected (>= 3.10 required)")
        return True
    else:
        error(f"Python {version_str} found, but 3.10+ is required")
        return False


def find_python3() -> str:
    """Find the python3 executable path."""
    # Try current interpreter first
    if sys.executable and "python3" in sys.executable:
        return sys.executable

    # Try common paths
    for path in ["/usr/bin/python3", "/usr/local/bin/python3"]:
        if os.path.isfile(path):
            return path

    # Fallback
    python3 = shutil.which("python3")
    if python3:
        return python3

    return sys.executable


def create_venv(force: bool = False) -> bool:
    """Create a virtual environment."""
    step("Creating virtual environment...")

    if VENV_DIR.exists() and not force:
        warn(f"Virtual environment already exists at {VENV_DIR}")
        try:
            reply = input("Remove and recreate? [y/N]: ").strip().lower()
            if reply != "y":
                info("Using existing virtual environment")
                return True
        except (EOFError, KeyboardInterrupt):
            info("Using existing virtual environment")
            return True

    # Remove existing venv
    if VENV_DIR.exists():
        info("Removing existing virtual environment...")
        shutil.rmtree(VENV_DIR)

    # Create install directory
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)

    # Create venv
    python_exe = find_python3()
    info(f"Creating venv with {python_exe}...")

    try:
        result = subprocess.run(
            [python_exe, "-m", "venv", str(VENV_DIR)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            error(f"Failed to create venv: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        error("Venv creation timed out")
        return False
    except Exception as e:
        error(f"Venv creation error: {e}")
        return False

    success(f"Virtual environment created at {VENV_DIR}")
    return True


def get_venv_python() -> Path:
    """Get the path to the venv Python executable."""
    return VENV_DIR / "bin" / "python"


def get_venv_pip() -> Path:
    """Get the path to the venv pip executable."""
    return VENV_DIR / "bin" / "pip"


def install_dependencies() -> bool:
    """Install Python dependencies in the virtual environment."""
    step("Installing Python dependencies...")

    pip_exe = get_venv_pip()
    if not pip_exe.exists():
        error("pip not found in virtual environment")
        return False

    # Upgrade pip, setuptools, wheel
    info("Upgrading pip, setuptools, wheel...")
    try:
        subprocess.run(
            [str(pip_exe), "install", "--upgrade", "pip", "setuptools", "wheel"],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except Exception as e:
        warn(f"pip upgrade had issues: {e}")

    # Install requirements.txt
    if REQUIREMENTS_FILE.exists():
        info(f"Installing from {REQUIREMENTS_FILE}...")
        try:
            result = subprocess.run(
                [str(pip_exe), "install", "-r", str(REQUIREMENTS_FILE)],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if result.returncode != 0:
                error(f"Failed to install requirements: {result.stderr}")
                return False
            success("Requirements installed")
        except subprocess.TimeoutExpired:
            error("Requirements installation timed out")
            return False
        except Exception as e:
            error(f"Requirements installation error: {e}")
            return False
    else:
        warn(f"requirements.txt not found at {REQUIREMENTS_FILE}")

    # Install package in editable mode
    if (PROJECT_DIR / "setup.py").exists() or (PROJECT_DIR / "pyproject.toml").exists():
        info("Installing RS Downloader in editable mode...")
        try:
            result = subprocess.run(
                [str(pip_exe), "install", "-e", str(PROJECT_DIR)],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                warn(f"Editable install had issues: {result.stderr}")
            else:
                success("RS Downloader installed in editable mode")
        except Exception as e:
            warn(f"Editable install error: {e}")

    return True


def validate_installation() -> bool:
    """Validate the installation by checking key components."""
    step("Validating installation...")

    python_exe = get_venv_python()
    if not python_exe.exists():
        error("Python executable not found in venv")
        return False

    all_ok = True

    # Check key packages
    packages = [
        "requests", "aiohttp", "yt_dlp", "rich", "click",
        "tqdm", "bs4", "PIL", "httpx", "pydantic",
    ]

    for pkg in packages:
        try:
            result = subprocess.run(
                [str(python_exe), "-c", f"import {pkg}; print({pkg}.__version__)"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                success(f"{pkg}: {result.stdout.strip()}")
            else:
                warn(f"{pkg}: import failed")
                all_ok = False
        except Exception:
            warn(f"{pkg}: check failed")
            all_ok = False

    # Check rsdl entry point
    rsdl_path = VENV_DIR / "bin" / "rsdl"
    if rsdl_path.exists():
        success(f"rsdl entry point: {rsdl_path}")
    else:
        warn("rsdl entry point not found in venv")
        all_ok = False

    return all_ok


def print_summary() -> None:
    """Print installation summary."""
    print(f"\n{GREEN}{'=' * 50}")
    print(f"  RS Downloader v10.0.0 - Setup Complete!")
    print(f"{'=' * 50}{NC}")
    print(f"\n  Virtual env:  {VENV_DIR}")
    print(f"  Python:       {get_venv_python()}")
    print(f"  Pip:          {get_venv_pip()}")
    print(f"  Config dir:   {INSTALL_DIR / 'config'}")
    print(f"\n  To activate:  source {VENV_DIR}/bin/activate")
    print(f"  To run:       rsdl --help")
    print()


def main() -> int:
    """Main entry point for auto venv setup."""
    print(f"\n{CYAN}{'=' * 50}")
    print("  RS Downloader v10.0.0 - Auto Venv Setup")
    print(f"{'=' * 50}{NC}\n")

    # Step 1: Check Python version
    if not check_python_version():
        error("Python 3.10+ is required. Please upgrade Python.")
        return 1

    # Step 2: Create virtual environment
    if not create_venv():
        error("Virtual environment creation failed")
        return 1

    # Step 3: Install dependencies
    if not install_dependencies():
        error("Dependency installation failed")
        return 1

    # Step 4: Validate
    if not validate_installation():
        warn("Some validation checks failed, but installation may still work")

    # Summary
    print_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
