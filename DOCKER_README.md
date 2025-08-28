# PolarVortex Docker Setup

This document describes how to run the PolarVortex application using Docker containers.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Git (to clone the repository)

### Initial Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd PolarVortex

# Run initial setup
make setup

# Edit environment files with your settings
nano .env
nano .env.production
```

### Development Environment
```bash
# Start development environment
make dev

# Or manually
docker-compose up --build -d
```

### Production Environment
```bash
# Start production environment
make prod

# Or manually
docker-compose -f docker-compose.prod.yml up --build -d
```

## 📁 File Structure

```
PolarVortex/
├── docker-compose.yml              # Development environment
├── docker-compose.prod.yml         # Production environment
├── env.example                     # Development environment variables
├── env.production.example          # Production environment variables
├── Makefile                        # Management commands
├── frontend/
│   ├── Dockerfile                  # Production frontend
│   ├── Dockerfile.dev              # Development frontend
│   └── .dockerignore               # Frontend build exclusions
└── backend/
    ├── Dockerfile                  # Production backend
    ├── Dockerfile.dev              # Development backend
    └── .dockerignore               # Backend build exclusions
```

## 🔧 Available Commands

### Make Commands
```bash
make help      # Show all available commands
make dev       # Start development environment
make prod      # Start production environment
make build     # Build all containers
make clean     # Stop and remove containers
make logs      # Show logs from all services
make status    # Show container status
make restart   # Restart all services
make setup     # Initial setup (copy env files)
make health    # Check service health
```

### Docker Compose Commands
```bash
# Development
docker-compose up --build -d
docker-compose down
docker-compose logs -f

# Production
docker-compose -f docker-compose.prod.yml up --build -d
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml logs -f
```

## 🌐 Access Points

### Development
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **Backend Health**: http://localhost:8000/health
- **Node.js Debug**: localhost:9229
- **Python Debug**: localhost:5678

### Production
- **Frontend**: http://localhost (port 80)
- **Backend API**: http://localhost:8000
- **Backend Health**: http://localhost:8000/health

## 🔒 Security Features

### Production Security
- Non-root user execution
- Read-only filesystem (except necessary volumes)
- No new privileges
- Temporary filesystem for /tmp
- Environment variable isolation

### Environment Variables
- Separate configuration for dev/prod
- Secret key management
- CORS origin control
- File size limits

## 📊 Monitoring & Health Checks

### Health Check Endpoints
- **Backend**: `GET /health` - Returns service status and Arduino connection
- **Frontend**: Health check via HTTP request to dev server

### Logging
- JSON-formatted logs
- Log rotation (10MB max, 3 files)
- Separate log volumes for persistence

### Health Check Configuration
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

## 🔧 Configuration

### Environment Variables

#### Development (.env)
```bash
# Copy from env.example
cp env.example .env

# Key variables to configure:
VITE_API_BASE_URL=http://localhost:8000
ARDUINO_DEVICE=/dev/ttyUSB0
DEBUG=true
LOG_LEVEL=DEBUG
```

#### Production (.env.production)
```bash
# Copy from env.production.example
cp env.production.example .env.production

# Key variables to configure:
SECRET_KEY=your-super-secret-production-key
CORS_ORIGINS=http://your-domain.com
DEBUG=false
LOG_LEVEL=WARNING
```

### Volume Mounts

#### Development
- `./frontend:/app` - Hot reloading for frontend
- `./backend:/app` - Hot reloading for backend
- `./backend/uploads:/app/uploads` - File uploads
- `./backend/processed_images:/app/processed_images` - Processed images
- `./backend/logs:/app/logs` - Application logs

#### Production
- `./backend/uploads:/app/uploads:rw` - File uploads (read-write)
- `./backend/processed_images:/app/processed_images:rw` - Processed images
- `./backend/logs:/app/logs:rw` - Application logs

## 🐛 Troubleshooting

### Common Issues

#### 1. Port Already in Use
```bash
# Check what's using the port
lsof -i :5173
lsof -i :8000

# Stop conflicting services or change ports in docker-compose.yml
```

#### 2. Arduino Device Not Found
```bash
# Check available devices
ls /dev/tty*

# Update ARDUINO_DEVICE in .env file
ARDUINO_DEVICE=/dev/ttyUSB1  # or appropriate device
```

#### 3. Permission Issues
```bash
# Fix volume permissions
sudo chown -R $USER:$USER ./backend/uploads
sudo chown -R $USER:$USER ./backend/processed_images
sudo chown -R $USER:$USER ./backend/logs
```

#### 4. Container Won't Start
```bash
# Check logs
docker-compose logs

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

#### 5. Health Check Failures
```bash
# Check service status
make health

# Check individual containers
docker-compose ps
docker-compose logs frontend
docker-compose logs backend
```

### Debug Mode

#### Frontend Debugging
```bash
# Access Node.js debugger
# Open Chrome DevTools and connect to localhost:9229
```

#### Backend Debugging
```bash
# Access Python debugger
# Use VS Code or PyCharm to connect to localhost:5678
```

## 🔄 Updates and Maintenance

### Updating Dependencies
```bash
# Frontend
docker-compose exec frontend npm update

# Backend
docker-compose exec backend pip install --upgrade -r requirements.txt
```

### Backup and Restore
```bash
# Backup data
tar -czf polarvortex-backup-$(date +%Y%m%d).tar.gz \
  backend/uploads backend/processed_images backend/logs

# Restore data
tar -xzf polarvortex-backup-YYYYMMDD.tar.gz
```

### Cleanup
```bash
# Remove unused containers, networks, and images
make clean

# Or manually
docker system prune -a
```

## 📈 Performance Optimization

### Development
- Hot reloading enabled
- Debug ports exposed
- Verbose logging

### Production
- Multi-worker backend
- Optimized logging
- Security hardening
- Resource limits (can be added to docker-compose.prod.yml)

## 🤝 Contributing

When making changes to the Docker setup:

1. Test both development and production configurations
2. Update this README if needed
3. Ensure environment variables are documented
4. Test health checks and monitoring
5. Verify security settings

## 📞 Support

For issues with the Docker setup:
1. Check the troubleshooting section
2. Review logs: `make logs`
3. Check health status: `make health`
4. Verify environment configuration
5. Check Docker and Docker Compose versions
