#!/bin/bash
# Pre-run hook for Claude Code
# Runs linting and unit tests before execution

set -e

echo "🔧 Running pre-run checks..."

# Check if we're in a Python project
if [ -f "pyproject.toml" ] || [ -f "requirements.txt" ] || [ -f "setup.py" ]; then
    echo "📦 Python project detected"
    
    # Check for virtual environment
    if [ ! -d "venv" ] && [ ! -d ".venv" ] && [ -z "$VIRTUAL_ENV" ]; then
        echo "⚠️  Warning: No virtual environment detected"
    fi
    
    # Run linting if available
    if command -v ruff &> /dev/null; then
        echo "🔍 Running ruff linter..."
        ruff check . || echo "⚠️  Linting issues found"
    elif command -v flake8 &> /dev/null; then
        echo "🔍 Running flake8 linter..."
        flake8 . || echo "⚠️  Linting issues found"
    fi
    
    # Run type checking if mypy is available
    if command -v mypy &> /dev/null; then
        echo "🔍 Running type checking..."
        mypy . || echo "⚠️  Type checking issues found"
    fi
    
    # Run unit tests if pytest is available
    if command -v pytest &> /dev/null && [ -d "tests" ]; then
        echo "🧪 Running unit tests..."
        pytest tests/ -v --tb=short || echo "⚠️  Some tests failed"
    fi

# Check if we're in a Node.js project
elif [ -f "package.json" ]; then
    echo "📦 Node.js project detected"
    
    # Install dependencies if node_modules doesn't exist
    if [ ! -d "node_modules" ]; then
        echo "📦 Installing dependencies..."
        npm install
    fi
    
    # Run linting if available
    if npm list eslint &> /dev/null; then
        echo "🔍 Running ESLint..."
        npm run lint || echo "⚠️  Linting issues found"
    fi
    
    # Run type checking if TypeScript is available
    if npm list typescript &> /dev/null; then
        echo "🔍 Running TypeScript checking..."
        npm run typecheck || echo "⚠️  Type checking issues found"
    fi
    
    # Run unit tests
    if npm list jest &> /dev/null || npm list vitest &> /dev/null; then
        echo "🧪 Running unit tests..."
        npm test || echo "⚠️  Some tests failed"
    fi

# Check if we're in a Rust project
elif [ -f "Cargo.toml" ]; then
    echo "📦 Rust project detected"
    
    # Run cargo check
    echo "🔍 Running cargo check..."
    cargo check || echo "⚠️  Compilation issues found"
    
    # Run clippy if available
    if command -v cargo-clippy &> /dev/null; then
        echo "🔍 Running clippy..."
        cargo clippy -- -D warnings || echo "⚠️  Clippy warnings found"
    fi
    
    # Run tests
    echo "🧪 Running unit tests..."
    cargo test || echo "⚠️  Some tests failed"

# Check if we're in an Elixir project
elif [ -f "mix.exs" ]; then
    echo "📦 Elixir project detected"
    
    # Get dependencies
    echo "📦 Getting dependencies..."
    mix deps.get || echo "⚠️  Dependency issues"
    
    # Compile project
    echo "🔧 Compiling project..."
    mix compile || echo "⚠️  Compilation issues"
    
    # Run formatter check
    echo "🔍 Checking code formatting..."
    mix format --check-formatted || echo "⚠️  Code formatting issues"
    
    # Run credo if available
    if mix deps | grep -q credo; then
        echo "🔍 Running credo..."
        mix credo || echo "⚠️  Credo issues found"
    fi
    
    # Run tests
    echo "🧪 Running tests..."
    mix test || echo "⚠️  Some tests failed"

else
    echo "📂 Generic project - running basic checks"
    
    # Check for common issues
    echo "🔍 Checking for common issues..."
    
    # Check for large files
    find . -type f -size +50M -not -path "./.git/*" -not -path "./node_modules/*" -not -path "./.venv/*" -not -path "./venv/*" | while read -r file; do
        echo "⚠️  Large file detected: $file"
    done
    
    # Check for secrets (basic patterns)
    if command -v grep &> /dev/null; then
        echo "🔐 Checking for potential secrets..."
        grep -r -i "password\|secret\|key\|token" --include="*.py" --include="*.js" --include="*.ts" --include="*.json" --include="*.yaml" --include="*.yml" . | grep -v ".git" | head -10 || true
    fi
fi

echo "✅ Pre-run checks completed"
exit 0