# Docker Installation Guide

## macOS Installation

### Option 1: Docker Desktop (Recommended)
1. Download Docker Desktop from: https://www.docker.com/products/docker-desktop
2. Install the .dmg file
3. Launch Docker Desktop
4. Wait for Docker to start (whale icon in menu bar)

### Option 2: Homebrew
```bash
brew install --cask docker
```

## Verify Installation

```bash
docker --version
docker-compose --version
```

## After Installation

Once Docker is running, return to the project and run:

```bash
./start.sh
```

This will:
1. Start PostgreSQL database
2. Run database migrations
3. Start FastAPI backend
4. Start React frontend

All services will be accessible at:
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:3000
