#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# AI-SupraAgent - Development Mode Script
# Starts services with hot-reload for development
# ═══════════════════════════════════════════════════════════════

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}AI-SupraAgent - Development Mode${NC}"
echo "═══════════════════════════════════════"

# Check for .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env from .env.example...${NC}"
    cp .env.example .env
    echo "Please edit .env with your values"
fi

# Start only database in Docker
echo -e "\n${YELLOW}Starting database...${NC}"
docker compose up -d database

# Wait for database
echo -e "${YELLOW}Waiting for database to be ready...${NC}"
sleep 5

echo -e "\n${GREEN}Database is running!${NC}"
echo ""
echo "To start backend (in a new terminal):"
echo "  cd backend"
echo "  pip install -r requirements.txt"
echo "  uvicorn src.main:app --reload --port 8000"
echo ""
echo "To start frontend (in another terminal):"
echo "  cd frontend"
echo "  npm install"
echo "  npm run dev"
echo ""
echo "Access points:"
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
