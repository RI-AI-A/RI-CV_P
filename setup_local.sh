# Quick setup script for local testing
echo "🚀 Setting up Retail Intelligence CV Backend for local testing..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check if PostgreSQL is running
echo "🔍 Checking PostgreSQL..."
if ! command -v psql &> /dev/null; then
    echo "⚠️  PostgreSQL not found. Installing..."
    sudo apt-get update
    sudo apt-get install -y postgresql postgresql-contrib
fi

# Start PostgreSQL
echo "▶️  Starting PostgreSQL..."
sudo service postgresql start

# Create database and user
echo "🗄️  Setting up database..."
sudo -u postgres psql -c "CREATE USER retail_user WITH PASSWORD 'retail_pass';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE retail_intel OWNER retail_user;" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE retail_intel TO retail_user;" 2>/dev/null || true

# Update DATABASE_URL for local PostgreSQL
export DATABASE_URL="postgresql+asyncpg://retail_user:retail_pass@localhost:5432/retail_intel"

# Run migrations
echo "🔄 Running database migrations..."
alembic upgrade head

echo "✅ Setup complete!"
echo ""
echo "To start the API service:"
echo "  source venv/bin/activate"
echo "  uvicorn api_service.main:app --reload"
echo ""
echo "To start the CV service (in another terminal):"
echo "  source venv/bin/activate"
echo "  python -m cv_service.stream_processor"
