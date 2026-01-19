#!/bin/bash

# 11+ Deep Tutor - Run Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}11+ Deep Tutor - Starting Up${NC}"
echo ""

# Check for uv
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed. Please install it first:${NC}"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check for node
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed. Please install it first.${NC}"
    exit 1
fi

# Navigate to script directory
cd "$(dirname "$0")"

# Backend setup
echo -e "${YELLOW}Setting up backend...${NC}"
cd backend

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi

echo "Installing dependencies..."
uv pip install -e . --quiet

# Initialize database and seed questions
echo "Initializing database..."
uv run python scripts/seed_questions.py

cd ..

# Frontend setup
echo -e "${YELLOW}Setting up frontend...${NC}"
cd frontend

if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install --silent
fi

cd ..

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "To start the application, run these commands in separate terminals:"
echo ""
echo -e "${YELLOW}Backend (terminal 1):${NC}"
echo "  cd backend && uv run uvicorn app.main:app --reload"
echo ""
echo -e "${YELLOW}Frontend (terminal 2):${NC}"
echo "  cd frontend && npm run dev"
echo ""
echo "Then open http://localhost:3000 in your browser."
