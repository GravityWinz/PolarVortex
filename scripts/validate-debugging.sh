#!/bin/bash

# PolarVortex Debugging Validation Script
# This script validates that the debugging setup is working correctly

echo "🔍 PolarVortex Debugging Validation"
echo "===================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a port is open
check_port() {
    local port=$1
    local service=$2
    
    if command -v nc >/dev/null 2>&1; then
        if nc -z localhost $port 2>/dev/null; then
            echo -e "${GREEN}✅ $service port $port is open${NC}"
            return 0
        else
            echo -e "${RED}❌ $service port $port is not accessible${NC}"
            return 1
        fi
    elif command -v curl >/dev/null 2>&1; then
        if curl -s --connect-timeout 2 http://localhost:$port >/dev/null 2>&1; then
            echo -e "${GREEN}✅ $service port $port is accessible${NC}"
            return 0
        else
            echo -e "${RED}❌ $service port $port is not accessible${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  Cannot check port $port (nc and curl not available)${NC}"
        return 1
    fi
}

# Function to check container status
check_container() {
    local service=$1
    local status=$(docker-compose ps -q $service 2>/dev/null)
    
    if [ -n "$status" ]; then
        local health=$(docker-compose ps $service | grep -o "(healthy\|unhealthy)" | head -1)
        if [ "$health" = "(healthy)" ]; then
            echo -e "${GREEN}✅ $service container is running and healthy${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️  $service container is running but unhealthy${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ $service container is not running${NC}"
        return 1
    fi
}

# Function to test API endpoints
test_api() {
    local endpoint=$1
    local description=$2
    
    if curl -s --connect-timeout 5 $endpoint >/dev/null 2>&1; then
        echo -e "${GREEN}✅ $description is responding${NC}"
        return 0
    else
        echo -e "${RED}❌ $description is not responding${NC}"
        return 1
    fi
}

echo ""
echo "📦 Checking Container Status..."
echo "-------------------------------"

backend_ok=false
frontend_ok=false

if check_container backend; then
    backend_ok=true
fi

if check_container frontend; then
    frontend_ok=true
fi

echo ""
echo "🔌 Checking Debug Ports..."
echo "---------------------------"

debug_backend_ok=false
debug_frontend_ok=false

if check_port 5678 "Backend Debug"; then
    debug_backend_ok=true
fi

if check_port 9229 "Frontend Debug"; then
    debug_frontend_ok=true
fi

echo ""
echo "🌐 Checking API Endpoints..."
echo "----------------------------"

api_ok=false
if test_api "http://localhost:8000/health" "Backend Health API"; then
    api_ok=true
fi

if test_api "http://localhost:5173" "Frontend Development Server"; then
    frontend_ok=true
fi

echo ""
echo "📋 VS Code Configuration Check..."
echo "---------------------------------"

# Check if VS Code configuration files exist
if [ -f ".vscode/launch.json" ]; then
    echo -e "${GREEN}✅ VS Code launch.json found${NC}"
else
    echo -e "${RED}❌ VS Code launch.json missing${NC}"
fi

if [ -f ".vscode/settings.json" ]; then
    echo -e "${GREEN}✅ VS Code settings.json found${NC}"
else
    echo -e "${RED}❌ VS Code settings.json missing${NC}"
fi

if [ -f ".vscode/extensions.json" ]; then
    echo -e "${GREEN}✅ VS Code extensions.json found${NC}"
else
    echo -e "${RED}❌ VS Code extensions.json missing${NC}"
fi

echo ""
echo "📁 Checking Required Files..."
echo "-----------------------------"

# Check if required files exist
if [ -f "backend/Dockerfile.dev" ]; then
    echo -e "${GREEN}✅ Backend development Dockerfile found${NC}"
else
    echo -e "${RED}❌ Backend development Dockerfile missing${NC}"
fi

if [ -f "frontend/Dockerfile.dev" ]; then
    echo -e "${GREEN}✅ Frontend development Dockerfile found${NC}"
else
    echo -e "${RED}❌ Frontend development Dockerfile missing${NC}"
fi

if [ -f "docker-compose.yml" ]; then
    echo -e "${GREEN}✅ Docker Compose file found${NC}"
else
    echo -e "${RED}❌ Docker Compose file missing${NC}"
fi

echo ""
echo "📊 Summary..."
echo "-------------"

if [ "$backend_ok" = true ] && [ "$debug_backend_ok" = true ] && [ "$api_ok" = true ]; then
    echo -e "${GREEN}✅ Backend debugging is ready!${NC}"
else
    echo -e "${RED}❌ Backend debugging has issues${NC}"
fi

if [ "$frontend_ok" = true ] && [ "$debug_frontend_ok" = true ]; then
    echo -e "${GREEN}✅ Frontend debugging is ready!${NC}"
else
    echo -e "${RED}❌ Frontend debugging has issues${NC}"
fi

echo ""
echo "🚀 Next Steps:"
echo "1. Open VS Code in the project root: code ."
echo "2. Install recommended extensions"
echo "3. Set breakpoints in your code"
echo "4. Press F5 and select 'Attach to Backend (Python in Docker)'"
echo "5. Make API requests to trigger breakpoints"
echo ""
echo "📖 For detailed instructions, see DEBUGGING_GUIDE.md"

