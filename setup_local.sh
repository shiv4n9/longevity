#!/bin/bash

echo "🚀 Setting up Longevity Dashboard v2.0 (Local Development)..."

# Create virtual environment
echo "📦 Creating Python virtual environment..."
cd backend
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📥 Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "⚠️  You need PostgreSQL running. Options:"
echo ""
echo "1. Install PostgreSQL locally:"
echo "   brew install postgresql@15"
echo "   brew services start postgresql@15"
echo "   createdb longevity"
echo ""
echo "2. Use Docker for PostgreSQL only:"
echo "   docker run -d --name longevity-db -p 5432:5432 \\"
echo "     -e POSTGRES_DB=longevity \\"
echo "     -e POSTGRES_USER=postgres \\"
echo "     -e POSTGRES_PASSWORD=postgres \\"
echo "     postgres:15-alpine"
echo ""
echo "3. Use SQLite for quick testing (edit config.py):"
echo "   database_url: str = 'sqlite+aiosqlite:///./longevity.db'"
echo ""
echo "After database is ready:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   uvicorn app.main:app --reload"
