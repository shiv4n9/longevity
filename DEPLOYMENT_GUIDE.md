# Deployment Guide - Juniper Server

This guide will help you deploy the Longevity Dashboard to your Juniper server.

## Prerequisites

Before deploying, ensure your Juniper server has:

1. **Docker & Docker Compose** installed
2. **Git** installed
3. **Network access** to ttbg-shell012.juniper.net
4. **Open ports**: 80 (HTTP), 443 (HTTPS - optional), 8000 (Backend API), 5432 (PostgreSQL)
5. **Sufficient resources**: 4GB RAM minimum, 20GB disk space

## Deployment Options

### Option 1: Docker Compose (Recommended)

This is the easiest method - everything runs in containers.

#### Step 1: Connect to Your Server

```bash
ssh your-username@your-juniper-server.juniper.net
```

#### Step 2: Clone the Repository

```bash
cd /opt  # or your preferred directory
git clone https://github.com/shiv4n9/longevity.git
cd longevity
```

#### Step 3: Configure Environment

```bash
# Copy and edit the environment file
cp .env.example .env
nano .env
```

Update these values in `.env`:
```bash
# SSH Credentials for device access
SSH_USERNAME=your_username
SSH_PASSWORD=your_password

# Database Configuration
POSTGRES_DB=longevity
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password_here

# Backend API URL (use your server's IP or hostname)
VITE_API_URL=http://your-server-ip:8000
```

#### Step 4: Update Frontend Configuration

Edit `frontend/.env`:
```bash
echo "VITE_API_URL=http://your-server-ip:8000" > frontend/.env
```

Or if using a domain name:
```bash
echo "VITE_API_URL=http://longevity.juniper.net:8000" > frontend/.env
```

#### Step 5: Build and Start Services

```bash
# Make scripts executable
chmod +x start.sh STOP.sh

# Start all services
./start.sh
```

This will:
- Build Docker images for backend and frontend
- Start PostgreSQL database
- Initialize database schema and partitions
- Start backend API on port 8000
- Start frontend on port 3000

#### Step 6: Verify Deployment

```bash
# Check all containers are running
docker ps

# You should see:
# - longevity-db (PostgreSQL)
# - longevity-backend (FastAPI)
# - longevity-frontend (React)

# Check backend logs
docker logs longevity-backend

# Check frontend logs
docker logs longevity-frontend
```

#### Step 7: Access the Application

Open your browser and navigate to:
- **Frontend**: `http://your-server-ip:3000`
- **Backend API**: `http://your-server-ip:8000`
- **API Docs**: `http://your-server-ip:8000/docs`

---

### Option 2: Production Deployment with Nginx

For a production setup with proper domain and SSL, use Nginx as a reverse proxy.

#### Step 1: Install Nginx

```bash
sudo apt update
sudo apt install nginx -y
```

#### Step 2: Create Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
services:
  postgres:
    image: postgres:15-alpine
    container_name: longevity-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-longevity}
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "127.0.0.1:5432:5432"  # Only accessible from localhost
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    container_name: longevity-backend
    restart: unless-stopped
    ports:
      - "127.0.0.1:8000:8000"  # Only accessible from localhost
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      - POSTGRES_DB=${POSTGRES_DB:-longevity}
      - POSTGRES_USER=${POSTGRES_USER:-postgres}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_HOST=postgres
    volumes:
      - ./backend:/app
      - /app/venv

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    container_name: longevity-frontend
    restart: unless-stopped
    ports:
      - "127.0.0.1:3000:80"  # Nginx serves on port 80 inside container
    depends_on:
      - backend

volumes:
  postgres_data:
```

#### Step 3: Create Production Frontend Dockerfile

Create `frontend/Dockerfile.prod`:

```dockerfile
# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

#### Step 4: Create Nginx Configuration for Frontend

Create `frontend/nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

#### Step 5: Configure Nginx Reverse Proxy

Create `/etc/nginx/sites-available/longevity`:

```nginx
# Redirect HTTP to HTTPS (optional, for SSL)
server {
    listen 80;
    server_name longevity.juniper.net;  # Replace with your domain
    return 301 https://$server_name$request_uri;
}

# Main server block
server {
    listen 443 ssl http2;
    server_name longevity.juniper.net;  # Replace with your domain

    # SSL Configuration (if you have certificates)
    # ssl_certificate /etc/ssl/certs/longevity.crt;
    # ssl_certificate_key /etc/ssl/private/longevity.key;

    # For HTTP only (no SSL), use this instead:
    # listen 80;
    # Comment out the SSL lines above

    # Frontend
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://127.0.0.1:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API docs
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host $host;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/longevity /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl reload nginx
```

#### Step 6: Update Frontend Environment

Edit `frontend/.env`:
```bash
# If using Nginx reverse proxy
VITE_API_URL=https://longevity.juniper.net  # or http:// if no SSL
```

#### Step 7: Start Production Services

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

---

## Post-Deployment Steps

### 1. Set Up Systemd Service (Auto-start on Boot)

Create `/etc/systemd/system/longevity.service`:

```ini
[Unit]
Description=Longevity Dashboard
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/longevity
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable longevity
sudo systemctl start longevity
```

### 2. Set Up Log Rotation

Create `/etc/logrotate.d/longevity`:

```
/opt/longevity/backend.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
}
```

### 3. Configure Firewall

```bash
# Allow HTTP
sudo ufw allow 80/tcp

# Allow HTTPS (if using SSL)
sudo ufw allow 443/tcp

# Or if not using Nginx, allow direct access
sudo ufw allow 3000/tcp  # Frontend
sudo ufw allow 8000/tcp  # Backend
```

### 4. Set Up Database Backups

Create backup script `/opt/longevity/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/opt/longevity/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

docker exec longevity-db pg_dump -U postgres longevity | gzip > $BACKUP_DIR/longevity_$DATE.sql.gz

# Keep only last 7 days of backups
find $BACKUP_DIR -name "longevity_*.sql.gz" -mtime +7 -delete
```

Make executable and add to cron:
```bash
chmod +x /opt/longevity/backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add this line:
0 2 * * * /opt/longevity/backup.sh
```

---

## Monitoring & Maintenance

### Check Service Status

```bash
# Check all containers
docker ps

# Check specific container logs
docker logs longevity-backend -f
docker logs longevity-frontend -f
docker logs longevity-db -f

# Check resource usage
docker stats
```

### Update Application

```bash
cd /opt/longevity
git pull origin main
docker-compose down
docker-compose up -d --build
```

### Database Maintenance

```bash
# Access database
docker exec -it longevity-db psql -U postgres -d longevity

# View database size
docker exec longevity-db psql -U postgres -d longevity -c "SELECT pg_size_pretty(pg_database_size('longevity'));"

# Vacuum database (cleanup)
docker exec longevity-db psql -U postgres -d longevity -c "VACUUM ANALYZE;"
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs longevity-backend
docker logs longevity-frontend

# Rebuild containers
docker-compose down
docker-compose up -d --build --force-recreate
```

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Test database connection
docker exec longevity-db psql -U postgres -d longevity -c "SELECT 1;"

# Check environment variables
docker exec longevity-backend env | grep POSTGRES
```

### Frontend Can't Connect to Backend

1. Check `frontend/.env` has correct `VITE_API_URL`
2. Rebuild frontend: `docker-compose up -d --build frontend`
3. Check CORS settings in `backend/app/main.py`

### SSH Connection Failures

```bash
# Test SSH from server
ssh sshivang@ttbg-shell012.juniper.net

# Check backend logs for SSH errors
docker logs longevity-backend | grep -i ssh
```

---

## Security Recommendations

1. **Change default passwords** in `.env`
2. **Use SSL certificates** for HTTPS (Let's Encrypt)
3. **Restrict database access** to localhost only
4. **Set up firewall rules** properly
5. **Regular backups** of database
6. **Keep Docker images updated**
7. **Use secrets management** for production (Docker secrets or Vault)

---

## Performance Tuning

### PostgreSQL Optimization

Edit `docker-compose.yml` and add to postgres service:

```yaml
command: postgres -c shared_buffers=256MB -c max_connections=200 -c work_mem=4MB
```

### Backend Scaling

For high load, run multiple backend instances:

```yaml
backend:
  deploy:
    replicas: 3
```

Then use Nginx load balancing.

---

## Support

For issues during deployment:
1. Check logs: `docker logs <container-name>`
2. Verify environment variables
3. Test network connectivity
4. Review this guide's troubleshooting section

---

## Quick Reference

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Restart a service
docker-compose restart backend

# Update and rebuild
git pull && docker-compose up -d --build

# Backup database
docker exec longevity-db pg_dump -U postgres longevity > backup.sql

# Restore database
cat backup.sql | docker exec -i longevity-db psql -U postgres -d longevity
```
