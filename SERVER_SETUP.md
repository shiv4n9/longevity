# Quick Server Setup Guide

This is a simplified guide to get the Longevity Dashboard running on your Juniper server quickly.

## Prerequisites Check

Before starting, verify your server has:

```bash
# Check Docker
docker --version

# Check Docker Compose
docker-compose --version

# Check Git
git --version

# Check available disk space (need at least 20GB)
df -h

# Check available memory (need at least 4GB)
free -h
```

If any are missing, install them first.

## Quick Deployment (5 Minutes)

### 1. Clone the Repository

```bash
# SSH to your server
ssh your-username@your-juniper-server.juniper.net

# Navigate to installation directory
cd /opt  # or wherever you want to install

# Clone the repo
git clone https://github.com/shiv4n9/longevity.git
cd longevity
```

### 2. Configure Environment

```bash
# Create environment file
cp .env.example .env

# Edit with your credentials
nano .env
```

Update these critical values:
```bash
SSH_USERNAME=your_ssh_username
SSH_PASSWORD=your_ssh_password
POSTGRES_PASSWORD=choose_a_secure_password
```

### 3. Configure Frontend API URL

```bash
# Get your server's IP address
hostname -I

# Create frontend environment file
echo "VITE_API_URL=http://YOUR_SERVER_IP:8000" > frontend/.env

# Replace YOUR_SERVER_IP with actual IP, for example:
# echo "VITE_API_URL=http://10.49.123.45:8000" > frontend/.env
```

### 4. Deploy

```bash
# Make deployment script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh

# Choose option 1 for development or 2 for production
```

### 5. Verify

```bash
# Check all containers are running
docker ps

# You should see 3 containers:
# - longevity-db
# - longevity-backend
# - longevity-frontend

# Check logs if needed
docker logs longevity-backend
docker logs longevity-frontend
```

### 6. Access

Open your browser:
- **Frontend**: `http://YOUR_SERVER_IP:3000`
- **Backend API**: `http://YOUR_SERVER_IP:8000`
- **API Docs**: `http://YOUR_SERVER_IP:8000/docs`

## Firewall Configuration

If you can't access the application, open the required ports:

```bash
# For Ubuntu/Debian with UFW
sudo ufw allow 3000/tcp  # Frontend
sudo ufw allow 8000/tcp  # Backend
sudo ufw reload

# For RHEL/CentOS with firewalld
sudo firewall-cmd --permanent --add-port=3000/tcp
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

## Common Issues

### Issue: "Cannot connect to Docker daemon"

```bash
# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker
```

### Issue: "Port already in use"

```bash
# Check what's using the port
sudo lsof -i :3000
sudo lsof -i :8000

# Kill the process or change ports in docker-compose.yml
```

### Issue: "Frontend can't connect to backend"

1. Check `frontend/.env` has correct IP
2. Verify backend is running: `curl http://localhost:8000/docs`
3. Check firewall allows port 8000

### Issue: "SSH connection to devices fails"

1. Test SSH manually: `ssh username@ttbg-shell012.juniper.net`
2. Verify credentials in `.env` are correct
3. Check backend logs: `docker logs longevity-backend | grep SSH`

## Stopping the Application

```bash
cd /opt/longevity
docker-compose down
```

## Updating the Application

```bash
cd /opt/longevity
git pull origin main
docker-compose down
docker-compose up -d --build
```

## Auto-Start on Server Reboot

Create systemd service:

```bash
sudo nano /etc/systemd/system/longevity.service
```

Paste this content:
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

Enable it:
```bash
sudo systemctl daemon-reload
sudo systemctl enable longevity
sudo systemctl start longevity
```

## Monitoring

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker logs longevity-backend -f
docker logs longevity-frontend -f
docker logs longevity-db -f

# Check resource usage
docker stats

# Check disk usage
docker system df
```

## Backup Database

```bash
# Create backup
docker exec longevity-db pg_dump -U postgres longevity > backup_$(date +%Y%m%d).sql

# Restore backup
cat backup_20240402.sql | docker exec -i longevity-db psql -U postgres -d longevity
```

## Need Help?

1. Check logs: `docker-compose logs -f`
2. Review DEPLOYMENT_GUIDE.md for detailed instructions
3. Check troubleshooting section in README.md

## Production Deployment with Domain

If you want to use a proper domain (e.g., longevity.juniper.net):

1. Follow the "Option 2: Production Deployment with Nginx" in DEPLOYMENT_GUIDE.md
2. Set up DNS to point to your server
3. Configure SSL certificates (optional but recommended)

## Quick Reference Commands

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart

# View logs
docker-compose logs -f

# Update
git pull && docker-compose up -d --build

# Check status
docker-compose ps

# Access database
docker exec -it longevity-db psql -U postgres -d longevity
```
