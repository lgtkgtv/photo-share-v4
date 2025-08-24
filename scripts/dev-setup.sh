#!/bin/bash
# PhotoShare Development Environment Setup
# =====================================
# Sets up uv-managed Python virtual environment and installs all dependencies

set -e  # Exit on any error

echo "🚀 PhotoShare Development Environment Setup"
echo "=========================================="

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ uv found: $(uv --version)"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "🔧 Creating uv virtual environment..."
    uv venv
else
    echo "✅ Virtual environment already exists"
fi

# Install dependencies
echo "📦 Installing dependencies with uv..."
uv sync

# Install development dependencies
echo "📦 Installing development dependencies..."
uv sync --extra dev --extra test --extra security --extra docs

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "🔧 Next steps:"
echo "   1. Activate the virtual environment: source .venv/bin/activate"
echo "   2. Start the services: docker compose -f docker-compose.separated.yml up -d"
echo "   3. Test the setup: bash api-integration-tests/test-auth-flow.sh"
echo ""
echo "📚 Development commands:"
echo "   • uv run pytest                 # Run tests"
echo "   • uv run black .                # Format code"
echo "   • uv run mypy .                 # Type checking"
echo "   • uv run bandit -r .            # Security analysis"
echo "   • uv add <package>              # Add new dependency"
echo "   • uv sync                       # Update dependencies"
echo ""
echo "⚠️  IMPORTANT: Always use 'uv' commands for Python package management!"