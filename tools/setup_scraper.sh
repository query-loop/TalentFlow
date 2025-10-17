#!/usr/bin/env bash
"""
Setup script for the job posting scraper.
Installs dependencies and prepares the environment.
"""

set -euo pipefail

echo "🚀 Setting up TalentFlow Job Scraper..."

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✓ Python version: $python_version"

if [[ $(echo "$python_version < 3.8" | bc) -eq 1 ]]; then
    echo "❌ Python 3.8+ required, found $python_version"
    exit 1
fi

# Install system dependencies for Playwright
echo "📦 Installing system dependencies..."
if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y \
        libnss3-dev \
        libatk-bridge2.0-dev \
        libdrm-dev \
        libxkbcommon-dev \
        libgtk-3-dev \
        libxss1 \
        libasound2-dev
elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y \
        nss \
        atk \
        at-spi2-atk \
        libdrm \
        libxkbcommon \
        gtk3 \
        libXScrnSaver \
        alsa-lib
fi

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip3 install --upgrade pip

# Core dependencies
pip3 install \
    playwright>=1.40.0 \
    jsonschema>=4.20.0 \
    python-dateutil>=2.8.0 \
    aiofiles>=23.0.0

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install chromium

# Make CLI script executable
echo "⚙️  Setting up CLI command..."
chmod +x scrape_job.py

# Create symlink for global access (optional)
if [[ ":$PATH:" == *":$HOME/.local/bin:"* ]]; then
    mkdir -p "$HOME/.local/bin"
    ln -sf "$(pwd)/scrape_job.py" "$HOME/.local/bin/scrape-job"
    echo "✓ CLI command 'scrape-job' available globally"
else
    echo "ℹ️  Add $(pwd) to PATH or use ./scrape_job.py directly"
fi

# Run tests to verify installation
echo "🧪 Running tests..."
python3 test_scraper.py

echo "✅ Setup complete!"
echo ""
echo "Usage examples:"
echo "  ./scrape_job.py --url https://example.com/job --out job.json"
echo "  scrape-job --url https://company.com/careers/123 --out results/job.json --verbose"
echo ""
echo "For help: ./scrape_job.py --help"