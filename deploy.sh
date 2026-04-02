#!/bin/bash

# Longevity Dashboard Deployment Script
# This script helps deploy the application to a production server

set -e  # Exit on error

echo "=========================================="
echo "Longevity Dashboard Deployment"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please create a .env file with your configuration."
    echo "You can copy .env.example and modify it:"
    echo "  cp .env.example .env"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed!${NC}"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed!${NC}"
    echo "Please install Docker Compose first: https://docs.docker.com/compose/install/"
    exit 1
fi

# Ask for deployment type
echo "Select deployment type:"
echo "1) Development (docker-compose.yml)"
echo "2) Production (docker-compose.prod.yml with Nginx)"
echo ""
read -p "Enter choice [1-2]: " choice

case $choice in
    1)
        COMPOSE_FILE="docker-compose.yml"
        MODE="development"
        ;;
    2)
        COMPOSE_FILE="docker-compose.prod.yml"
        MODE="production"
        ;;
    *)
        echo -e "${RED}Invalid choice!${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Deploying in ${MODE} mode...${NC}"
echo ""

# Pull latest code (if in git repo)
if [ -d .git ]; then
    echo "Pulling latest code from git..."
    git pull origin main || echo -e "${YELLOW}Warning: Could not pull from git${NC}"
fi

# Stop existing containers
echo ""
echo "Stopping existing containers..."
docker-compose -f $COMPOSE_FILE down

# Build and start containers
echo ""
echo "Building and starting containers..."
docker-compose -f $COMPOSE_FILE up -d --build

# Wait for services to be healthy
echo ""
echo "Waiting for services to start..."
sleep 10

# Check if containers are running
echo ""
echo "Checking container status..."
docker-compose -f $COMPOSE_FILE ps

# Check backend health
echo ""
echo "Checking backend health..."
if curl -f http://localhost:8000/docs > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is running${NC}"
else
    echo -e "${YELLOW}⚠ Backend may not be ready yet. Check logs with: docker logs longevity-backend${NC}"
fi

# Check frontend health
echo ""
echo "Checking frontend health..."
if [ "$MODE" == "production" ]; then
    if curl -f http://localhost:3000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Frontend is running${NC}"
    else
        echo -e "${YELLOW}⚠ Frontend may not be ready yet. Check logs with: docker logs longevity-frontend${NC}"
    fi
else
    echo -e "${YELLOW}Frontend is starting in dev mode (may take a minute)...${NC}"
fi

# Check database
echo ""
echo "Checking database..."
if docker exec longevity-db psql -U postgres -d longevity -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Database is running${NC}"
else
    echo -e "${RED}✗ Database connection failed${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "Access the application:"
if [ "$MODE" == "production" ]; then
    echo "  Frontend: http://localhost:3000"
    echo "  Backend API: http://localhost:8000"
    echo "  API Docs: http://localhost:8000/docs"
    echo ""
    echo "Note: In production mode, you should set up Nginx reverse proxy"
    echo "      See DEPLOYMENT_GUIDE.md for details"
else
    echo "  Frontend: http://localhost:3000"
    echo "  Backend API: http://localhost:8000"
    echo "  API Docs: http://localhost:8000/docs"
fi
echo ""
echo "Useful commands:"
echo "  View logs: docker-compose -f $COMPOSE_FILE logs -f"
echo "  Stop services: docker-compose -f $COMPOSE_FILE down"
echo "  Restart: docker-compose -f $COMPOSE_FILE restart"
echo ""
