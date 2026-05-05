#!/bin/bash
# Local Setup Script - Configure environment for local testing
# Creates virtual environment and installs dependencies

set -e  # Exit on error

echo "🔧 ProcessApp Agent v2.0 - Local Setup"
echo "========================================"

# Get script directory and navigate to agents root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_DIR="$(dirname "$SCRIPT_DIR")"
cd "$AGENTS_DIR"

# Check if we're in the agents directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: requirements.txt not found"
    exit 1
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo "📦 Installing dependencies from requirements.txt..."
pip install -r requirements.txt --quiet

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Set AWS credentials: export AWS_PROFILE=ans-super"
echo "2. Run the agent: ./scripts/run_local.sh"
echo "3. Test with curl: ./scripts/test_local.sh"
echo "4. Interactive chat: ./scripts/chat_local.sh"
echo ""
echo "💡 To activate the virtual environment manually:"
echo "   source venv/bin/activate"
