# PolarVortex Backend Development Guide

This guide covers setting up and working with the PolarVortex backend development environment.

## 🚀 Quick Start

### Automated Setup (Recommended)

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Run the setup script:**
   ```bash
   python setup_dev.py
   ```

3. **Start development server:**
   ```bash
   # Windows
   run_dev.bat
   
   # macOS/Linux
   ./run_dev.sh
   ```

### Manual Setup

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   ```

2. **Activate virtual environment:**
   ```bash
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Create directories:**
   ```bash
   mkdir processed_images uploads logs
   ```

5. **Create .env file:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

## 🛠️ Development Tools

### Using Makefile

The project includes a Makefile with common development tasks:

```bash
# Show all available commands
make help

# Setup development environment
make setup

# Install dependencies
make install-dev

# Start development server
make run

# Run tests
make test

# Format code
make format

# Run linting
make lint
```

### VS Code Configuration

The project includes VS Code settings for optimal development:

- **Python Interpreter**: Automatically uses the virtual environment
- **Linting**: Flake8 and MyPy enabled
- **Formatting**: Black formatter with auto-format on save
- **Testing**: Pytest integration
- **Import Sorting**: isort integration

### Development Dependencies

Additional development tools included:

- **Testing**: pytest, pytest-asyncio, pytest-cov
- **Linting**: flake8, mypy
- **Formatting**: black, isort
- **Debugging**: ipython, ipdb
- **Documentation**: mkdocs, mkdocs-material

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Arduino Configuration
ARDUINO_PORTS=COM3,COM4,/dev/ttyUSB0,/dev/ttyACM0

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Logging
LOG_LEVEL=INFO

# Development Settings
DEBUG=true
RELOAD=true
```

### Arduino Setup

1. **Upload Arduino sketch:**
   - Open `arduino/polargraph.ino` in Arduino IDE
   - Select your Arduino board
   - Upload the sketch

2. **Connect Arduino:**
   - Connect Arduino via USB
   - Note the COM port (Windows) or device path (Linux/macOS)
   - Update `ARDUINO_PORTS` in `.env` if needed

3. **Test connection:**
   ```bash
   curl http://localhost:8000/status
   ```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
make test

# Run tests with coverage
make test-cov

# Run specific test file
pytest tests/test_main.py

# Run tests with verbose output
pytest -v
```

### Writing Tests

Create test files in the `tests/` directory:

```python
# tests/test_main.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "PolarVortex API" in response.json()["message"]

def test_status_endpoint():
    response = client.get("/status")
    assert response.status_code == 200
    assert "connected" in response.json()
```

## 📝 Code Quality

### Formatting

```bash
# Format code with black and isort
make format

# Format specific file
black app/main.py
isort app/main.py
```

### Linting

```bash
# Run all linting checks
make lint

# Run specific linter
flake8 app/
mypy app/
```

### Pre-commit Hooks

Set up pre-commit hooks for automatic code quality checks:

```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

## 🐛 Debugging

### Debug Mode

```bash
# Start server in debug mode
make debug

# Or manually
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
```

### Interactive Debugging

```bash
# Start IPython shell
make shell

# Or with debugger
python -m ipdb app/main.py
```

### Logging

Configure logging levels in `.env`:

```env
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

## 📚 Documentation

### API Documentation

Once the server is running, visit:
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Code Documentation

Generate documentation:

```bash
# Build documentation
make docs

# Serve documentation locally
mkdocs serve
```

## 🐳 Docker Development

### Build and Run

```bash
# Build Docker image
make docker-build

# Run Docker container
make docker-run
```

### Docker Compose (for full stack)

```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f backend
```

## 🔄 Development Workflow

### Typical Development Session

1. **Start development:**
   ```bash
   make run
   ```

2. **Make changes to code**

3. **Test changes:**
   ```bash
   make test
   make lint
   ```

4. **Format code:**
   ```bash
   make format
   ```

5. **Commit changes:**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

### Adding New Features

1. **Create feature branch:**
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Implement feature**

3. **Add tests**

4. **Update documentation**

5. **Create pull request**

## 🚨 Troubleshooting

### Common Issues

#### Virtual Environment Issues

```bash
# Recreate virtual environment
rm -rf venv
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

#### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

#### Arduino Connection Issues

```bash
# Check available ports
python -c "import serial.tools.list_ports; print([p.device for p in serial.tools.list_ports.comports()])"

# Test Arduino connection
python -c "import serial; s = serial.Serial('/dev/ttyUSB0', 9600); print('Connected')"
```

#### Import Errors

```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Install in development mode
pip install -e .
```

### Getting Help

1. **Check logs** for error messages
2. **Review API documentation** at http://localhost:8000/docs
3. **Check configuration** in `.env` file
4. **Verify dependencies** are installed correctly

## 📋 Development Checklist

Before committing code:

- [ ] Code is formatted with black and isort
- [ ] Linting passes (flake8, mypy)
- [ ] Tests pass
- [ ] Documentation is updated
- [ ] Environment variables are configured
- [ ] No sensitive data is committed

## 🔗 Useful Links

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Pytest Documentation**: https://docs.pytest.org/
- **Black Documentation**: https://black.readthedocs.io/
- **MyPy Documentation**: https://mypy.readthedocs.io/
- **OpenCV Documentation**: https://docs.opencv.org/
- **Pillow Documentation**: https://pillow.readthedocs.io/

