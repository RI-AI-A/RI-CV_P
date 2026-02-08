# Testing Guide - Without Docker

This guide helps you test the Retail Intelligence CV Backend locally without Docker.

## Prerequisites

- Python 3.10+
- PostgreSQL (will be installed by setup script)

## Quick Start

### 1. Run Setup Script

```bash
./setup_local.sh
```

This will:
- Create a Python virtual environment
- Install all dependencies
- Set up PostgreSQL database
- Run database migrations

### 2. Start API Service

In one terminal:
```bash
source venv/bin/activate
export DATABASE_URL="postgresql+asyncpg://retail_user:retail_pass@localhost:5432/retail_intel"
uvicorn api_service.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Create Test Branch

In another terminal:
```bash
curl -X POST http://localhost:8000/branches \
  -H "Content-Type: application/json" \
  -d '{
    "id": "branch_001",
    "name": "Test Branch",
    "capacity": 100,
    "peak_time": "18:00",
    "state": "active"
  }'
```

### 4. Test CV Service

```bash
./test_cv.sh
```

This will process the downloaded retail video and detect people.

## Alternative: Docker with Sudo

If you prefer Docker, add your user to the docker group:

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and log back in, then:
docker compose up -d
docker compose exec api_service alembic upgrade head
```

## Verify Everything Works

1. **Check API Health**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **View API Documentation**:
   Open browser: http://localhost:8000/docs

3. **Check CV Events** (after running CV service):
   ```bash
   # Run ETL
   curl -X POST http://localhost:8000/etl/run
   
   # Get KPIs
   curl http://localhost:8000/kpis/branch/branch_001
   ```

## Troubleshooting

### PostgreSQL Issues
```bash
# Check PostgreSQL status
sudo service postgresql status

# Start PostgreSQL
sudo service postgresql start

# Reset database
sudo -u postgres psql -c "DROP DATABASE retail_intel;"
sudo -u postgres psql -c "CREATE DATABASE retail_intel OWNER retail_user;"
alembic upgrade head
```

### Python Dependencies
```bash
# Reinstall dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Video Not Found
Make sure the video was downloaded:
```bash
ls -lh data/retail_sample.mp4
```

If missing, download again:
```bash
wget -O data/retail_sample.mp4 "https://www.pexels.com/download/video/3209828/?fps=25.0&h=1080&w=1920"
```
