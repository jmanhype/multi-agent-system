# GEPA Multi-Agent Trading System Makefile
# Simplifies common operations and workflows

.PHONY: help install setup clean run optimize analyze backtest monitor

# Default target
help:
	@echo "GEPA Multi-Agent Trading System"
	@echo "================================"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install     - Install dependencies with pip"
	@echo "  make setup-uv    - Set up project with uv package manager"
	@echo "  make fix-numpy   - Fix NumPy/VectorBT compatibility issues"
	@echo ""
	@echo "Core Operations:"
	@echo "  make optimize    - Run GEPA optimization (light budget)"
	@echo "  make optimize-medium - Run GEPA with medium budget"
	@echo "  make optimize-heavy  - Run GEPA with heavy budget"
	@echo "  make three-gulfs - Run Three Gulfs Framework analysis"
	@echo "  make volatility  - Analyze 10% volatility scenario"
	@echo "  make scenarios   - Test all volatility scenarios"
	@echo "  make pipeline    - Run complete trading pipeline"
	@echo ""
	@echo "Monitoring & Analysis:"
	@echo "  make monitor     - Monitor GEPA execution in real-time"
	@echo "  make logs        - Tail recent logs"
	@echo "  make report      - Generate performance report"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean       - Remove logs, cache, and temporary files"
	@echo "  make clean-logs  - Remove only log files"
	@echo "  make backup      - Backup critical configurations"
	@echo ""
	@echo "Development:"
	@echo "  make lint        - Run code linting"
	@echo "  make format      - Format code with black"
	@echo "  make test        - Run actual tests (if any)"

# Installation targets
install:
	pip install -r requirements.txt

setup-uv:
	@echo "Setting up with uv..."
	@command -v uv >/dev/null 2>&1 || (echo "Installing uv..." && curl -LsSf https://astral.sh/uv/install.sh | sh)
	uv venv
	uv pip install -r requirements.txt

fix-numpy:
	@echo "Fixing NumPy/VectorBT compatibility..."
	pip install numpy==1.23.5 numba==0.56.4 --force-reinstall
	@echo "Testing VectorBT import..."
	@python -c "import vectorbtpro as vbt; print(f'✅ VectorBT {vbt.__version__} working!')"

# Core operations
optimize:
	@echo "Running GEPA optimization (light budget)..."
	GEPA_BUDGET=light python gepa_optimizer.py

optimize-medium:
	@echo "Running GEPA optimization (medium budget)..."
	GEPA_BUDGET=medium python gepa_optimizer.py

optimize-heavy:
	@echo "Running GEPA optimization (heavy budget)..."
	GEPA_BUDGET=heavy python gepa_optimizer.py

three-gulfs:
	@echo "Running Three Gulfs Framework analysis..."
	python gepa_three_gulfs.py --test-volatility

volatility:
	@echo "Analyzing 10% volatility scenario..."
	python volatility_analyzer.py

scenarios:
	@echo "Testing all volatility scenarios..."
	python volatility_scenarios.py

pipeline:
	@echo "Running complete trading pipeline..."
	python main.py

# Monitoring
monitor:
	@echo "Monitoring GEPA execution..."
	@tail -f gepa_monitoring.log | grep -E "Score:|Iteration|VectorBT|ERROR"

logs:
	@echo "Recent log entries:"
	@tail -n 50 logs/*.jsonl 2>/dev/null || tail -n 50 *.log

report:
	@echo "Generating performance report..."
	@python -c "import json; import glob; \
		files = glob.glob('data/gepa_logs/**/*.json', recursive=True); \
		print(f'Found {len(files)} result files'); \
		for f in files[-3:]: \
			with open(f) as file: \
				data = json.load(file); \
				if 'score' in str(data): \
					print(f'{f}: Best score found')"

# Maintenance
clean:
	@echo "Cleaning up..."
	rm -rf __pycache__ **/__pycache__
	rm -rf .pytest_cache
	rm -f *.log
	rm -rf data/gepa_logs/enhanced/*.bin
	@echo "✅ Cleaned cache and temporary files"

clean-logs:
	@echo "Cleaning log files..."
	mkdir -p logs/archive
	mv *.log logs/archive/ 2>/dev/null || true
	@echo "✅ Moved logs to logs/archive/"

backup:
	@echo "Backing up critical files..."
	@mkdir -p backups
	@cp .env backups/.env.backup 2>/dev/null || true
	@cp -r config backups/config_$$(date +%Y%m%d) 2>/dev/null || true
	@cp -r artifacts backups/artifacts_$$(date +%Y%m%d) 2>/dev/null || true
	@echo "✅ Backed up to backups/"

# Development
lint:
	@echo "Running linting..."
	@command -v ruff >/dev/null 2>&1 && ruff check . || echo "Install ruff: pip install ruff"

format:
	@echo "Formatting code..."
	@command -v black >/dev/null 2>&1 && black . || echo "Install black: pip install black"

test:
	@echo "No test suite configured yet"
	@echo "Core files are in: test_*.py (these are system components, not tests)"

# File organization utilities
.PHONY: organize
organize:
	@echo "Organizing project files..."
	@mkdir -p logs
	@mv *.log logs/ 2>/dev/null || true
	@echo "✅ Log files moved to logs/"
	@echo "✅ Project organized"

# Quick start commands
.PHONY: quick-start dev-setup

quick-start: fix-numpy
	@echo "Running quick optimization test..."
	@make optimize

dev-setup: setup-uv fix-numpy
	@echo "✅ Development environment ready!"
	@echo "Run 'make help' to see available commands"