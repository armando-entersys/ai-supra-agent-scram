#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# AI-SupraAgent - Deployment Script
# ═══════════════════════════════════════════════════════════════

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DEPLOY_PATH="/srv/servicios/ai-supra-agent"
COMPOSE_FILE="docker-compose.yml"

echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}       AI-SupraAgent - Deployment Script${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"

# Check if running from correct directory
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}Error: docker-compose.yml not found${NC}"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo "Creating from .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env with your actual values before continuing${NC}"
    exit 1
fi

# Check for secrets
if [ ! -f "secrets/gcp-sa-key.json" ]; then
    echo -e "${RED}Error: GCP Service Account key not found${NC}"
    echo "Please place your service account JSON at: secrets/gcp-sa-key.json"
    exit 1
fi

# Validate docker-compose
echo -e "\n${YELLOW}Validating docker-compose configuration...${NC}"
docker compose config > /dev/null
echo -e "${GREEN}✓ Configuration valid${NC}"

# Pull/build images
echo -e "\n${YELLOW}Building Docker images...${NC}"
docker compose build --no-cache

# Stop existing containers (if any)
echo -e "\n${YELLOW}Stopping existing containers...${NC}"
docker compose down --remove-orphans || true

# Start services
echo -e "\n${YELLOW}Starting services...${NC}"
docker compose up -d

# Wait for services to be healthy
echo -e "\n${YELLOW}Waiting for services to be healthy...${NC}"
sleep 10

# Health check
echo -e "\n${YELLOW}Running health checks...${NC}"

# Check database
if docker compose exec -T database pg_isready -U ai_user -d vector_store > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Database is ready${NC}"
else
    echo -e "${RED}✗ Database check failed${NC}"
fi

# Check backend
BACKEND_HEALTH=$(docker compose exec -T backend curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "000")
if [ "$BACKEND_HEALTH" = "200" ]; then
    echo -e "${GREEN}✓ Backend is healthy${NC}"
else
    echo -e "${RED}✗ Backend health check failed (HTTP $BACKEND_HEALTH)${NC}"
fi

# Check frontend
FRONTEND_HEALTH=$(docker compose exec -T frontend wget -q --spider http://localhost:80 && echo "200" || echo "000")
if [ "$FRONTEND_HEALTH" = "200" ]; then
    echo -e "${GREEN}✓ Frontend is healthy${NC}"
else
    echo -e "${RED}✗ Frontend health check failed${NC}"
fi

# Show container status
echo -e "\n${YELLOW}Container status:${NC}"
docker compose ps

echo -e "\n${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}       Deployment Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "\nAccess points:"
echo -e "  Frontend:  ${GREEN}https://ai.scram2k.com${NC}"
echo -e "  API:       ${GREEN}https://api.ai.scram2k.com${NC}"
echo -e "  API Docs:  ${GREEN}https://api.ai.scram2k.com/docs${NC}"
echo -e "\nUseful commands:"
echo -e "  View logs:     docker compose logs -f"
echo -e "  Restart:       docker compose restart"
echo -e "  Stop:          docker compose down"
