.PHONY: help dev prod build clean logs status restart

# Default target
help:
	@echo "PolarVortex Docker Management"
	@echo ""
	@echo "Available commands:"
	@echo "  make dev      - Start development environment"
	@echo "  make prod     - Start production environment"
	@echo "  make build    - Build all containers"
	@echo "  make clean    - Stop and remove containers"
	@echo "  make logs     - Show logs from all services"
	@echo "  make status   - Show container status"
	@echo "  make restart  - Restart all services"
	@echo "  make setup    - Initial setup (copy env files)"

# Development environment
dev:
	@echo "Starting development environment..."
	docker-compose up --build -d
	@echo "Development environment started!"
	@echo "Frontend: http://localhost:5173"
	@echo "Backend:  http://localhost:8000"

# Production environment
prod:
	@echo "Starting production environment..."
	docker-compose -f docker-compose.prod.yml up --build -d
	@echo "Production environment started!"
	@echo "Frontend: http://localhost"
	@echo "Backend:  http://localhost:8000"

# Build containers
build:
	@echo "Building containers..."
	docker-compose build
	docker-compose -f docker-compose.prod.yml build

# Clean up
clean:
	@echo "Stopping and removing containers..."
	docker-compose down
	docker-compose -f docker-compose.prod.yml down
	docker system prune -f

# Show logs
logs:
	docker-compose logs -f

# Show status
status:
	@echo "Container Status:"
	docker-compose ps

# Restart services
restart:
	@echo "Restarting services..."
	docker-compose restart

# Initial setup
setup:
	@echo "Setting up environment files..."
	@if [ ! -f .env ]; then cp env.example .env; echo "Created .env from env.example"; fi
	@if [ ! -f .env.production ]; then cp env.production.example .env.production; echo "Created .env.production from env.production.example"; fi
	@echo "Setup complete! Please edit .env and .env.production files with your settings."

# Health check
health:
	@echo "Checking service health..."
	@curl -f http://localhost:8000/health || echo "Backend health check failed"
	@curl -f http://localhost:5173 || echo "Frontend health check failed"

# Production health check
health-prod:
	@echo "Checking production service health..."
	@curl -f http://localhost:8000/health || echo "Backend health check failed"
	@curl -f http://localhost/health || echo "Frontend health check failed"
