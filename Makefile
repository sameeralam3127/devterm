.PHONY: help install install-dev test lint format clean check pre-commit run

# Default target
help:
	@echo "DevOps Toolkit - Available Commands:"
	@echo ""
	@echo "  make install        - Install production dependencies"
	@echo "  make install-dev    - Install development dependencies"
	@echo "  make test           - Run tests with coverage"
	@echo "  make lint           - Run all linters (ruff, pylint, bandit)"
	@echo "  make format         - Format code with black and ruff"
	@echo "  make check          - Run all checks (format, lint, test)"
	@echo "  make pre-commit     - Install pre-commit hooks"
	@echo "  make clean          - Clean build artifacts"
	@echo "  make run            - Run the toolkit"
	@echo ""

# Install production dependencies
install:
	@echo "Installing production dependencies..."
	pip install -e .

# Install development dependencies
install-dev:
	@echo "Installing development dependencies..."
	pip install -e ".[dev]"
	@echo "Installing pre-commit hooks..."
	pre-commit install

# Run tests with coverage
test:
	@echo "Running tests with coverage..."
	pytest -v --cov=app --cov-report=term-missing --cov-report=html

# Run quick tests
test-quick:
	@echo "Running quick tests..."
	pytest -v -x

# Run linters
lint:
	@echo "Running ruff..."
	ruff check app tests
	@echo ""
	@echo "Running pylint..."
	pylint app
	@echo ""
	@echo "Running bandit..."
	bandit -r app -c pyproject.toml

# Format code
format:
	@echo "Formatting with black..."
	black app tests
	@echo ""
	@echo "Sorting imports with ruff..."
	ruff check --select I --fix app tests

# Run all checks
check: format lint test
	@echo ""
	@echo "All checks passed!"

# Install pre-commit hooks
pre-commit:
	@echo "Installing pre-commit hooks..."
	pre-commit install
	@echo "Running pre-commit on all files..."
	pre-commit run --all-files

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .ruff_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Clean complete!"

# Run the toolkit
run:
	@echo "Running DevOps Toolkit..."
	python -m app.devops_toolkit.cli run

# Run in test mode
test-run:
	@echo "Running DevOps Toolkit in test mode..."
	python -m app.devops_toolkit.cli test

# Build package
build:
	@echo "Building package..."
	python -m build

# Type checking
typecheck:
	@echo "Running mypy type checker..."
	mypy app

# Security check
security:
	@echo "Running security checks..."
	bandit -r app -c pyproject.toml
	@echo ""
	@echo "Checking for known vulnerabilities..."
	pip-audit || echo "pip-audit not installed, skipping..."

# Generate coverage report
coverage:
	@echo "Generating coverage report..."
	pytest --cov=app --cov-report=html --cov-report=term
	@echo ""
	@echo "Coverage report generated in htmlcov/index.html"

# Watch tests
watch:
	@echo "Watching for changes and running tests..."
	pytest-watch

# Install with uv (if available)
install-uv:
	@echo "Installing with uv..."
	@command -v uv >/dev/null 2>&1 || { echo "uv not found. Install with: pip install uv"; exit 1; }
	uv pip install -e ".[dev]"
