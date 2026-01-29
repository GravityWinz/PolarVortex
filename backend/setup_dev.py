#!/usr/bin/env python3
"""
Setup script for PolarVortex Backend Development Environment
Automates virtual environment creation and dependency installation
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python version {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def create_directories():
    """Create necessary directories"""
    directories = [
        "processed_images",
        "uploads",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}")

def setup_virtual_environment():
    """Create and activate virtual environment"""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("⚠️  Virtual environment already exists")
        response = input("   Do you want to recreate it? (y/N): ")
        if response.lower() != 'y':
            print("   Using existing virtual environment")
            return True
        else:
            import shutil
            shutil.rmtree(venv_path)
            print("   Removed existing virtual environment")
    
    # Create virtual environment
    if not run_command(f"{sys.executable} -m venv venv", "Creating virtual environment"):
        return False
    
    return True

def get_activate_command():
    """Get the appropriate activation command based on OS"""
    system = platform.system().lower()
    
    if system == "windows":
        return "venv\\Scripts\\activate"
    else:
        return "source venv/bin/activate"

def install_dependencies():
    """Install Python dependencies"""
    # Determine pip path
    if platform.system().lower() == "windows":
        pip_path = "venv\\Scripts\\pip"
    else:
        pip_path = "venv/bin/pip"
    
    # Upgrade pip first
    if not run_command(f"{pip_path} install --upgrade pip", "Upgrading pip"):
        return False
    
    # Install dependencies with Windows-specific handling
    if platform.system().lower() == "windows":
        print("🔄 Installing dependencies for Windows...")
        
        # Try installing with pre-compiled wheels first
        if not run_command(f"{pip_path} install --only-binary=all -r requirements.txt", "Installing dependencies with pre-compiled wheels"):
            print("⚠️  Pre-compiled installation failed, trying alternative approach...")
            
            # Try Windows-specific requirements
            if not run_command(f"{pip_path} install -r requirements-windows.txt", "Installing Windows-specific dependencies"):
                print("⚠️  Windows-specific installation failed, trying individual packages...")
                
                # Install packages individually to identify problematic ones
                packages = [
                    "fastapi==0.104.1",
                    "uvicorn[standard]==0.24.0",
                    "pyserial==3.5",
                    "python-multipart==0.0.6",
                    "Pillow==10.1.0",
                    "opencv-python-headless==4.8.1.78",
                    "numpy==1.24.3",
                    "scipy>=1.11.0",
                    "scikit-image>=0.22.0",
                    "PyYAML==6.0.1",
                    "vpype==1.15.0",
                    "vpype-gcode>=0.10.0",
                    "vpype-occult>=0.4.0",
                    "svgpathtools==1.6.1",
                    "cairosvg>=2.7.0"
                ]
                
                for package in packages:
                    if not run_command(f"{pip_path} install {package}", f"Installing {package}"):
                        print(f"❌ Failed to install {package}")
                        return False
    else:
        # Non-Windows installation
        if not run_command(f"{pip_path} install -r requirements.txt", "Installing dependencies"):
            return False
    
    return True

def create_env_file():
    """Create .env file with default configuration"""
    env_content = """# PolarVortex Backend Configuration

# Arduino Configuration
ARDUINO_PORTS=COM3,COM4,/dev/ttyUSB0,/dev/ttyACM0

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Logging
LOG_LEVEL=INFO

# Development Settings
DEBUG=true
RELOAD=true
"""
    
    env_file = Path(".env")
    if not env_file.exists():
        with open(env_file, "w") as f:
            f.write(env_content)
        print("✅ Created .env file with default configuration")
    else:
        print("⚠️  .env file already exists (skipping creation)")

def create_run_scripts():
    """Create convenient run scripts"""
    
    # Windows batch file
    if platform.system().lower() == "windows":
        batch_content = """@echo off
echo Starting PolarVortex Backend...
call venv\\Scripts\\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
"""
        with open("run_dev.bat", "w") as f:
            f.write(batch_content)
        print("✅ Created run_dev.bat for Windows")
    
    # Unix shell script
    shell_content = """#!/bin/bash
echo "Starting PolarVortex Backend..."
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""
    with open("run_dev.sh", "w") as f:
        f.write(shell_content)
    
    # Make shell script executable on Unix systems
    if platform.system().lower() != "windows":
        os.chmod("run_dev.sh", 0o755)
        print("✅ Created run_dev.sh for Unix systems")

def main():
    """Main setup function"""
    print("🚀 PolarVortex Backend Development Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Setup virtual environment
    if not setup_virtual_environment():
        print("❌ Failed to create virtual environment")
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Create configuration files
    create_env_file()
    create_run_scripts()
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Activate the virtual environment:")
    
    activate_cmd = get_activate_command()
    print(f"   {activate_cmd}")
    
    print("\n2. Start the development server:")
    if platform.system().lower() == "windows":
        print("   run_dev.bat")
    else:
        print("   ./run_dev.sh")
    
    print("\n3. Or manually:")
    print("   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    
    print("\n4. Access the API documentation:")
    print("   http://localhost:8000/docs")
    
    print("\n🔧 Configuration:")
    print("   - Edit .env file to customize settings")
    print("   - Connect Arduino and update ARDUINO_PORTS if needed")
    
    print("\n📚 Documentation:")
    print("   - See README.md for detailed information")
    print("   - API docs available at http://localhost:8000/docs")

if __name__ == "__main__":
    main()

