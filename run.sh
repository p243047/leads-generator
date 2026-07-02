#!/bin/bash

# Lead Generation Pro - Run Script
# This script sets up the environment and runs the application

set -e  # Exit on error

echo "🚀 Lead Generation Pro - Starting Setup..."

# Check if Python 3.10+ is installed
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "🐍 Detected Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
echo "🌐 Installing Playwright browsers (Chromium)..."
playwright install chromium

# Optional: Install system dependencies for Playwright (Linux only)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "🔧 Installing system dependencies for Playwright..."
    playwright install-deps chromium 2>/dev/null || true
fi

# Run the application
echo "✨ Starting Lead Generation Pro..."
python main.py

echo "✅ Application closed."
