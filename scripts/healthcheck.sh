#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# AI-SupraAgent - Health Check Script
# ═══════════════════════════════════════════════════════════════

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}AI-SupraAgent Health Check${NC}"
echo "═══════════════════════════════════════"

# Check if containers are running
echo -e "\n${YELLOW}Container Status:${NC}"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

# Database health
echo -e "\n${YELLOW}Database:${NC}"
if docker compose exec -T database pg_isready -U ai_user -d vector_store > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is accepting connections${NC}"

    # Check pgvector extension
    PGVECTOR=$(docker compose exec -T database psql -U ai_user -d vector_store -t -c "SELECT extname FROM pg_extension WHERE extname='vector';" 2>/dev/null | tr -d ' ')
    if [ "$PGVECTOR" = "vector" ]; then
        echo -e "${GREEN}✓ pgvector extension is installed${NC}"
    else
        echo -e "${RED}✗ pgvector extension not found${NC}"
    fi

    # Check tables
    TABLES=$(docker compose exec -T database psql -U ai_user -d vector_store -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | tr -d ' ')
    echo -e "  Tables in database: $TABLES"
else
    echo -e "${RED}✗ Database connection failed${NC}"
fi

# Backend health
echo -e "\n${YELLOW}Backend API:${NC}"
BACKEND_RESPONSE=$(docker compose exec -T backend curl -s http://localhost:8000/health 2>/dev/null)
if [ -n "$BACKEND_RESPONSE" ]; then
    echo -e "${GREEN}✓ Backend is responding${NC}"
    echo "  Response: $BACKEND_RESPONSE"
else
    echo -e "${RED}✗ Backend not responding${NC}"
fi

# Frontend health
echo -e "\n${YELLOW}Frontend:${NC}"
if docker compose exec -T frontend wget -q --spider http://localhost:80 2>/dev/null; then
    echo -e "${GREEN}✓ Frontend is serving content${NC}"
else
    echo -e "${RED}✗ Frontend not responding${NC}"
fi

# External endpoints (if Traefik is configured)
echo -e "\n${YELLOW}External Endpoints:${NC}"
API_EXT=$(curl -s -o /dev/null -w "%{http_code}" https://api.ai.scram2k.com/health 2>/dev/null || echo "000")
if [ "$API_EXT" = "200" ]; then
    echo -e "${GREEN}✓ https://api.ai.scram2k.com is accessible${NC}"
else
    echo -e "${YELLOW}○ https://api.ai.scram2k.com returned HTTP $API_EXT${NC}"
fi

FRONT_EXT=$(curl -s -o /dev/null -w "%{http_code}" https://ai.scram2k.com 2>/dev/null || echo "000")
if [ "$FRONT_EXT" = "200" ]; then
    echo -e "${GREEN}✓ https://ai.scram2k.com is accessible${NC}"
else
    echo -e "${YELLOW}○ https://ai.scram2k.com returned HTTP $FRONT_EXT${NC}"
fi

# Resource usage
echo -e "\n${YELLOW}Resource Usage:${NC}"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" $(docker compose ps -q) 2>/dev/null || echo "Unable to fetch stats"

echo -e "\n═══════════════════════════════════════"
