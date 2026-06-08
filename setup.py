"""
RS Downloader v10.0.0 - Setup Configuration
Author: RAJSARASWATI JATAV (RS)
License: MIT
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = [
        line.strip()
        for line in requirements_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="rs-downloader",
    version="10.0.0",
    author="RAJSARASWATI JATAV",
    author_email="rs@t3rmuxk1ng.dev",
    description="The Ultimate Download Toolkit by RS - Video, Audio, Playlist & Batch Downloading",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/T3rmuxk1ng/rs-downloader",
    license="MIT",
    packages=find_packages(exclude=["tests", "tests.*", "docs", "docs.*"]),
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "rsdl = rs_toolkit:main",
        ],
    },
    extras_require={
        "cloud": [
            "boto3>=1.34.0",
            "google-cloud-storage>=2.14.0",
            "azure-storage-blob>=12.19.0",
        ],
        "torrent": [
            "libtorrent>=2.0.0",
        ],
        "ai": [
            "openai>=1.6.0",
            "langchain>=0.1.0",
        ],
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.23.0",
            "pytest-cov>=4.1.0",
            "black>=23.12.0",
            "isort>=5.13.0",
            "mypy>=1.8.0",
            "flake8>=7.0.0",
            "pylint>=3.0.0",
            "pre-commit>=3.6.0",
        ],
        "all": [
            "boto3>=1.34.0",
            "google-cloud-storage>=2.14.0",
            "azure-storage-blob>=12.19.0",
            "libtorrent>=2.0.0",
            "openai>=1.6.0",
            "langchain>=0.1.0",
            "pytest>=7.4.0",
            "pytest-asyncio>=0.23.0",
            "pytest-cov>=4.1.0",
            "black>=23.12.0",
            "isort>=5.13.0",
            "mypy>=1.8.0",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Multimedia :: Video",
        "Topic :: Utilities",
    ],
    keywords=[
        "downloader", "video", "audio", "youtube", "playlist",
        "batch-download", "yt-dlp", "rs-downloader", "t3rmuxk1ng",
    ],
    project_urls={
        "Bug Tracker": "https://github.com/T3rmuxk1ng/rs-downloader/issues",
        "Documentation": "https://github.com/T3rmuxk1ng/rs-downloader/wiki",
        "Source Code": "https://github.com/T3rmuxk1ng/rs-downloader",
    },
)
