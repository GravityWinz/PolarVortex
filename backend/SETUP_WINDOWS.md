# Windows Setup Guide for PolarVortex Backend

This guide provides step-by-step instructions for setting up the PolarVortex backend on Windows, addressing common compilation issues.

## 🚨 Common Issues on Windows

### Problem: Package Compilation Errors
Some Python packages require C++ compilers on Windows, which can cause installation failures.

### Solution: Use Pre-compiled Wheels

## 🚀 Quick Setup (Recommended)

### Option 1: Automated Setup with Fallback

1. **Run the setup script:**
   ```cmd
   python setup_dev.py
   ```

2. **If it fails, try manual installation:**
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   pip install --upgrade pip
   pip install --only-binary=all -r requirements.txt
   ```

### Option 2: Manual Setup (If Automated Fails)

1. **Create virtual environment:**
   ```cmd
   python -m venv venv
   ```

2. **Activate virtual environment:**
   ```cmd
   venv\Scripts\activate
   ```

3. **Upgrade pip:**
   ```cmd
   python -m pip install --upgrade pip
   ```

4. **Install dependencies with pre-compiled wheels:**
   ```cmd
   pip install --only-binary=all -r requirements.txt
   ```

5. **If that fails, install packages individually:**
   ```cmd
   pip install fastapi==0.104.1
   pip install "uvicorn[standard]==0.24.0"
   pip install pyserial==3.5
   pip install python-multipart==0.0.6
   pip install Pillow==10.1.0
   pip install opencv-python-headless==4.8.1.78
   pip install numpy==1.24.3
   pip install scipy>=1.11.0
   pip install scikit-image>=0.22.0
   pip install PyYAML==6.0.1
   pip install vpype==1.15.0
   pip install vpype-gcode>=0.10.0
   pip install vpype-occult>=0.4.0
   pip install svgpathtools==1.6.1
   pip install cairosvg>=2.7.0
   ```

6. **Create directories:**
   ```cmd
   mkdir processed_images
   mkdir uploads
   mkdir logs
   ```

## 🔧 Alternative Solutions

### If OpenCV Installation Fails

1. **Try opencv-python-headless instead:**
   ```cmd
   pip uninstall opencv-python
   pip install opencv-python-headless==4.8.1.78
   ```

2. **Or use a different version:**
   ```cmd
   pip install opencv-python==4.7.0.72
   ```

### If NumPy Installation Fails

1. **Install NumPy from wheels:**
   ```cmd
   pip install --only-binary=numpy numpy==1.24.3
   ```

2. **Or use a different version:**
   ```cmd
   pip install numpy==1.23.5
   ```

### Install Visual C++ Build Tools (If Needed)

If you still get compilation errors, you may need Visual C++ build tools:

1. **Download Visual Studio Build Tools:**
   - Go to: https://visualstudio.microsoft.com/downloads/
   - Download "Build Tools for Visual Studio 2022"
   - Install with "C++ build tools" workload

2. **Or install Microsoft C++ Build Tools:**
   ```cmd
   pip install microsoft-visual-cpp-build-tools
   ```

## 🧪 Testing the Installation

1. **Test basic imports:**
   ```cmd
   python -c "import fastapi; print('FastAPI OK')"
   python -c "import cv2; print('OpenCV OK')"
   python -c "import numpy; print('NumPy OK')"
   ```

2. **Test the application:**
   ```cmd
   python -c "from app.main import app; print('App imports OK')"
   ```

3. **Start the server:**
   ```cmd
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## 🐛 Troubleshooting

### Error: "Microsoft Visual C++ 14.0 is required"

**Solution:**
1. Install Visual Studio Build Tools
2. Or use pre-compiled wheels: `pip install --only-binary=all package_name`

### Error: "Failed to build wheel"

**Solution:**
1. Try installing with `--only-binary=all` flag
2. Use alternative package versions
3. Install packages individually to identify the problematic one

### Error: "Permission denied"

**Solution:**
1. Run Command Prompt as Administrator
2. Or use `--user` flag: `pip install --user package_name`

### Error: "SSL Certificate Error"

**Solution:**
```cmd
pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org package_name
```

## 📋 Complete Setup Checklist

- [ ] Python 3.8+ installed
- [ ] Virtual environment created
- [ ] Virtual environment activated
- [ ] pip upgraded
- [ ] All dependencies installed
- [ ] Directories created
- [ ] .env file created
- [ ] Application starts without errors
- [ ] API documentation accessible at http://localhost:8000/docs

## 🔗 Useful Commands

```cmd
# Check Python version
python --version

# Check pip version
pip --version

# List installed packages
pip list

# Check virtual environment
where python

# Deactivate virtual environment
deactivate
```

## 📞 Getting Help

If you're still having issues:

1. **Check the error messages** - they often contain specific information about what's failing
2. **Try the manual installation** step by step
3. **Use alternative package versions** if specific versions fail
4. **Check Python and pip versions** - ensure they're compatible
5. **Consider using Anaconda** as an alternative to pip for scientific packages

## 🎯 Success Indicators

You'll know the setup is successful when:

- ✅ All packages install without errors
- ✅ `python -c "from app.main import app"` runs without errors
- ✅ `uvicorn app.main:app --reload` starts the server
- ✅ You can access http://localhost:8000/docs in your browser
