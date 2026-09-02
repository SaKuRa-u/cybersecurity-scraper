#!/bin/bash

set -e

echo "🚀 Cybersecurity Data Scraper - Complete Setup"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

# Step 1: Configure .env
echo -e "${YELLOW}📝 Step 1/5: Environment configuration${NC}"
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANT: Edit .env with your settings${NC}"
    echo "   nano .env"
    echo ""
    echo "Required changes:"
    echo "  DATABASE_PASSWORD=<secure-password>"
    echo "  SECRET_KEY=<random-32-char-string>"
    echo ""
    echo "Optional (recommended for GitHub scraper):"
    echo "  GITHUB_TOKEN=<your-github-token>"
    echo ""
    echo "Generate secure values:"
    echo "  openssl rand -base64 32   # For DATABASE_PASSWORD"
    echo "  openssl rand -hex 32      # For SECRET_KEY"
    echo ""
    read -p "Press Enter after editing .env to continue..."
fi

# Step 2: Build Docker images
echo ""
echo -e "${YELLOW}🔨 Step 2/5: Building Docker images${NC}"
docker compose build || { echo -e "${RED}❌ Build failed${NC}"; exit 1; }

# Step 3: Start services
echo ""
echo -e "${YELLOW}▶️  Step 3/5: Starting services${NC}"
docker compose up -d || { echo -e "${RED}❌ Start failed${NC}"; exit 1; }

# Step 4: Wait for services
echo ""
echo -e "${YELLOW}⏳ Step 4/5: Waiting for services to be healthy (30s)${NC}"
sleep 30

# Step 5: Initialize database
echo ""
echo -e "${YELLOW}🗄️  Step 5/5: Initializing database${NC}"
echo "Running migrations..."
docker compose exec -T backend alembic upgrade head || { echo -e "${RED}❌ Migration failed${NC}"; exit 1; }

echo "Seeding sources..."
docker compose exec -T backend python -m scripts.seed_sources || { echo -e "${RED}❌ Seed failed${NC}"; exit 1; }

# Verification
echo ""
echo "================================================"
echo -e "${GREEN}✅ Setup complete!${NC}"
echo "================================================"
echo ""
echo "📍 Access Points:"
echo "   Frontend:  http://localhost:3000"
echo "   API Docs:  http://localhost:8000/docs"
echo "   Health:    http://localhost:8000/health"
echo ""
echo "🔍 Verify deployment:"
echo "   ./verify.sh"
echo ""
echo "📊 View logs:"
echo "   docker compose logs -f"
echo ""
echo "🛠️  Useful commands:"
echo "   docker compose ps              # Check status"
echo "   docker compose restart backend # Restart service"
echo "   docker compose down            # Stop all"
echo ""
echo "📖 Next Steps:"
echo "   1. Open http://localhost:3000"
echo "   2. Click 'Scrape Now' on any source"
echo "   3. Watch real-time progress"
echo "   4. Browse data in Data Browser"
echo ""
echo "💡 Implementation Guide:"
echo "   Follow tasks in: docs/superpowers/plans/"
echo "   Each task has step-by-step code to copy-paste"
echo ""
