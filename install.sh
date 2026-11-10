#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "  Ollama Desktop Chatbot - Automated Installation (Linux/macOS)"
echo "=========================================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed. Please install Python 3.10 or newer."
    exit 1
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✓ Found Python $PY_VER"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment in .venv..."
    python3 -m venv .venv
else
    echo "✓ Existing virtual environment detected."
fi

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip and install requirements
echo "Installing dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# Check Ollama
echo "Checking Ollama installation..."
if command -v ollama &> /dev/null; then
    echo "✓ Ollama is installed."
    if curl -s http://localhost:11434/api/tags &> /dev/null; then
        echo "✓ Ollama server is running on http://localhost:11434"
    else
        echo "⚠️  Ollama server is not running right now. You can start it with 'ollama serve'."
    fi
else
    echo "⚠️  Ollama command not found in PATH."
    echo "   If you want to use local models, install Ollama from https://ollama.com"
fi

# Make run script executable
chmod +x run.sh || true

echo ""
echo "=========================================================="
echo "  ✅ Installation complete!"
echo "  Launch the application anytime by running: ./run.sh"
echo "=========================================================="
