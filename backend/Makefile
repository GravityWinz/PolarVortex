# PolarVortex Backend Development Makefile

.PHONY: help setup install install-dev run test lint format clean docs

# Default target
help:
	@echo "PolarVortex Backend Development Commands:"
	@echo ""
	@echo "Setup and Installation:"
	@echo "  setup        - Run automated setup script"
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo ""
	@echo "Development:"
	@echo "  run          - Start development server"
	@echo "  run-prod     - Start production server"
	@echo "  test         - Run tests"
	@echo "  test-cov     - Run tests with coverage"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint         - Run linting checks"
	@echo "  format       - Format code with black and isort"
	@echo "  type-check   - Run type checking with mypy"
	@echo ""
	@echo "Utilities:"
	@echo "  clean        - Clean up generated files"
	@echo "  docs         - Generate documentation"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run   - Run Docker container"

# Setup and Installation
setup:
	@echo "🚀 Setting up PolarVortex Backend development environment..."
	python setup_dev.py

install:
	@echo "📦 Installing production dependencies..."
	pip install -r requirements.txt

install-dev:
	@echo "🔧 Installing development dependencies..."
	pip install -r requirements-dev.txt

# Development Server
run:
	@echo "🌐 Starting development server..."
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-prod:
	@echo "🚀 Starting production server..."
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Testing
test:
	@echo "🧪 Running tests..."
	pytest tests/ -v

test-cov:
	@echo "📊 Running tests with coverage..."
	pytest tests/ --cov=app --cov-report=html --cov-report=term

# Code Quality
lint:
	@echo "🔍 Running linting checks..."
	flake8 app/ tests/
	mypy app/

format:
	@echo "🎨 Formatting code..."
	black app/ tests/
	isort app/ tests/

type-check:
	@echo "🔍 Running type checks..."
	mypy app/

# Utilities
clean:
	@echo "🧹 Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf build/
	rm -rf dist/

docs:
	@echo "📚 Generating documentation..."
	mkdocs build

# Docker
docker-build:
	@echo "🐳 Building Docker image..."
	docker build -t polarvortex-backend .

docker-run:
	@echo "🐳 Running Docker container..."
	docker run -p 8000:8000 --device=/dev/ttyUSB0 polarvortex-backend

# Database (if needed in future)
db-migrate:
	@echo "🗄️ Running database migrations..."
	# Add migration commands here when database is added

db-seed:
	@echo "🌱 Seeding database..."
	# Add seed commands here when database is added

# Development helpers
shell:
	@echo "🐍 Starting Python shell..."
	ipython

debug:
	@echo "🐛 Starting debug server..."
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug

# Environment setup
env-create:
	@echo "📝 Creating .env file..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ Created .env file from template"; \
	else \
		echo "⚠️  .env file already exists"; \
	fi

# Quick setup for new developers
quick-setup: env-create install-dev
	@echo "✅ Quick setup completed!"
	@echo "Run 'make run' to start the development server"

