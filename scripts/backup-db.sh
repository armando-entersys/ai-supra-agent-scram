#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# AI-SupraAgent - Database Backup Script
# ═══════════════════════════════════════════════════════════════

set -e

# Configuration
BACKUP_DIR="/srv/servicios/ai-supra-agent/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="ai_supra_agent_backup_${TIMESTAMP}.sql.gz"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}AI-SupraAgent Database Backup${NC}"
echo "═══════════════════════════════════════"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Perform backup
echo -e "\n${YELLOW}Creating backup...${NC}"
docker compose exec -T database pg_dump -U ai_user -d vector_store | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

# Check backup size
BACKUP_SIZE=$(ls -lh "${BACKUP_DIR}/${BACKUP_FILE}" | awk '{print $5}')
echo -e "${GREEN}✓ Backup created: ${BACKUP_FILE} (${BACKUP_SIZE})${NC}"

# Keep only last 7 backups
echo -e "\n${YELLOW}Cleaning old backups...${NC}"
cd "$BACKUP_DIR"
ls -t ai_supra_agent_backup_*.sql.gz | tail -n +8 | xargs -r rm -f
BACKUP_COUNT=$(ls -1 ai_supra_agent_backup_*.sql.gz 2>/dev/null | wc -l)
echo -e "${GREEN}✓ Keeping ${BACKUP_COUNT} most recent backups${NC}"

echo -e "\n${GREEN}Backup complete!${NC}"
echo "Location: ${BACKUP_DIR}/${BACKUP_FILE}"
