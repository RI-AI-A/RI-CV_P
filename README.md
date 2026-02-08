# Retail Intelligence CV Backend

A production-grade Computer Vision microservice and Backend API for a Retail Intelligence Decision Support System. This system uses YOLOv8 for person detection, ByteTrack for multi-object tracking, and provides a comprehensive REST API for data ingestion, ETL processing, and KPI computation.

## 🏗️ Architecture Overview

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   CV Service    │────────▶│   API Service    │────────▶│   PostgreSQL    │
│  (YOLOv8 +      │  HTTP   │   (FastAPI)      │         │   Database      │
│   ByteTrack)    │         │                  │         │                 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
      │                              │
      │                              │
      ▼                              ▼
 Video Stream              ETL & KPI Computation
 (RTSP/File)               (Aggregation + Analytics)
```

### Components

1. **CV Service**: Real-time person detection and tracking with ROI-based enter/exit detection
2. **API Service**: FastAPI backend for data ingestion, branch management, task management, and KPI retrieval
3. **Database**: PostgreSQL with 9 tables for customers, movements, branches, tasks, events, promotions, and KPIs
4. **ETL Pipeline**: Automated data processing and KPI computation

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.10+ (for local development)
- PostgreSQL 15+ (if running without Docker)

### Installation

1. **Clone and navigate to project**:
```bash
cd retail-intel-cv-backend
```

2. **Copy environment configuration**:
```bash
cp .env.example .env
```

3. **Edit `.env` file** with your configuration:
   - Set `CV_VIDEO_SOURCE` to your video stream URL or file path
   - Configure `CV_ROI_COORDINATES` for enter/exit detection
   - Adjust database credentials if needed

4. **Start services with Docker Compose**:
```bash
docker-compose up -d
```

5. **Run database migrations**:
```bash
docker-compose exec api_service alembic upgrade head
```

6. **Verify services are running**:
```bash
# Check API health
curl http://localhost:8000/health

# Check API docs
open http://localhost:8000/docs
```

## 📋 Database Schema

The system uses 9 tables:

- **customers**: Anonymized customer tracking (UUID-based)
- **customer_branch_movement**: Movement events with enter/exit times
- **branches**: Branch metadata (capacity, peak times, neighbors)
- **employees**: Staff information
- **tasks**: Task management for employees
- **events**: Events with location and repetition support
- **promotions**: Branch-specific and global promotions
- **branch_kpi_timeseries**: Computed KPI metrics over time windows

## 🔌 API Endpoints

### CV Ingestion
```bash
POST /cv/events
```
Receives CV events from the computer vision service.

**Example Request**:
```bash
curl -X POST http://localhost:8000/cv/events \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "550e8400-e29b-41d4-a716-446655440000",
    "branch_id": "branch_001",
    "enter_time": "2026-02-08T10:00:00Z",
    "exit_time": "2026-02-08T10:15:00Z",
    "action_type": "entered"
  }'
```

### Branch Management
```bash
# Create branch
POST /branches

# Get branch
GET /branches/{branch_id}
```

**Example - Create Branch**:
```bash
curl -X POST http://localhost:8000/branches \
  -H "Content-Type: application/json" \
  -d '{
    "id": "branch_001",
    "name": "Downtown Branch",
    "capacity": 150,
    "peak_time": "18:00",
    "neighbors": ["branch_002", "branch_003"],
    "state": "active"
  }'
```

### Task Management
```bash
# Create task
POST /tasks

# Get tasks for branch
GET /tasks/{branch_id}
```

### Event Management
```bash
# Create event
POST /events
```

### ETL & KPIs
```bash
# Trigger ETL pipeline
POST /etl/run

# Get KPIs for branch
GET /kpis/branch/{branch_id}
```

**Example - Run ETL**:
```bash
curl -X POST http://localhost:8000/etl/run \
  -H "Content-Type: application/json" \
  -d '{
    "branch_id": "branch_001",
    "time_window_minutes": 60
  }'
```

**Example - Get KPIs**:
```bash
curl http://localhost:8000/kpis/branch/branch_001
```

### Health Check
```bash
GET /health
```

## 📊 KPI Metrics

The system computes the following KPIs:

1. **Traffic Index**: `visitors / historical_baseline`
2. **Conversion Proxy**: `entered / (entered + passed)`
3. **Congestion Level**: `people_in_branch / capacity`
4. **Growth Momentum**: `slope(visitors over time)`
5. **Utilization Ratio**: `entered / capacity`
6. **Staffing Adequacy Index**: `staff_on_duty / required_staff`
7. **Bottleneck Score**: Combined metric of congestion and staffing issues

## 🎥 Computer Vision Configuration

### Video Source

Set in `.env`:
```bash
# RTSP stream
CV_VIDEO_SOURCE=rtsp://192.168.1.100:554/stream

# Or local file
CV_VIDEO_SOURCE=/data/sample_video.mp4
```

### ROI Configuration

Define Region of Interest for enter/exit detection:
```bash
# Format: x1,y1,x2,y2 (top-left and bottom-right coordinates)
CV_ROI_COORDINATES=100,100,500,400
```

### Action Types

- **passed**: Customer crossed ROI boundary but didn't enter
- **entered**: Customer crossed into ROI and spent time inside

## 🧪 Testing

Run tests with pytest:

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=. --cov-report=html

# Run specific test file
pytest tests/test_cv_ingestion.py -v
pytest tests/test_kpi_pipeline.py -v
```

## 🔧 Development

### Local Development Setup

1. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Start PostgreSQL** (via Docker):
```bash
docker-compose up -d postgres
```

4. **Run migrations**:
```bash
alembic upgrade head
```

5. **Start API service**:
```bash
uvicorn api_service.main:app --reload
```

6. **Start CV service** (in another terminal):
```bash
python -m cv_service.stream_processor
```

### Database Migrations

Create new migration:
```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback migration:
```bash
alembic downgrade -1
```

## 📁 Project Structure

```
retail-intel-cv-backend/
│
├── cv_service/              # Computer Vision Service
│   ├── detector.py          # YOLOv8 person detection
│   ├── tracker.py           # ByteTrack multi-object tracking
│   ├── stream_processor.py  # Main processing loop with ROI logic
│   ├── event_builder.py     # CV event payload construction
│   ├── client.py            # HTTP client for API communication
│   └── config.py            # CV service configuration
│
├── api_service/             # FastAPI Backend Service
│   ├── main.py              # FastAPI application
│   ├── config.py            # API configuration
│   ├── deps.py              # Dependency injection
│   ├── routers/             # API route handlers
│   │   ├── cv_ingestion.py  # CV event ingestion
│   │   ├── branches.py      # Branch management
│   │   ├── tasks.py         # Task management
│   │   ├── events.py        # Event management
│   │   └── kpis.py          # ETL & KPI endpoints
│   └── services/            # Business logic services
│       ├── etl_service.py   # ETL orchestration
│       ├── kpi_service.py   # KPI computation
│       └── aggregation_service.py  # Data aggregation
│
├── db/                      # Database Layer
│   ├── base.py              # SQLAlchemy base
│   ├── session.py           # Database session management
│   ├── models.py            # ORM models
│   └── migrations/          # Alembic migrations
│
├── schemas/                 # Pydantic Schemas
│   ├── cv_event.py          # CV event schemas
│   ├── branch.py            # Branch schemas
│   ├── task.py              # Task schemas
│   ├── event.py             # Event schemas
│   └── kpi.py               # KPI schemas
│
├── pipelines/               # ETL Pipelines
│   ├── etl.py               # ETL pipeline entry point
│   └── feature_engineering.py  # Advanced feature engineering
│
├── tests/                   # Test Suite
│   ├── conftest.py          # Pytest configuration
│   ├── test_cv_ingestion.py # CV ingestion tests
│   └── test_kpi_pipeline.py # KPI computation tests
│
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile               # Docker image definition
├── requirements.txt         # Python dependencies
├── alembic.ini              # Alembic configuration
├── .env.example             # Environment variables template
└── README.md                # This file
```

## 🔗 Integration Points

This system is designed to integrate with future modules:

### For Forecasting Models
- Access movement data via `customer_branch_movement` table
- Retrieve KPI time series from `branch_kpi_timeseries` table
- Use aggregated metrics for predictive modeling

### For Recommendation Engines
- Query branch metadata and capacity from `branches` table
- Analyze traffic patterns and conversion rates
- Leverage neighbor branch data for recommendations

### For Conversational AI
- Expose all endpoints via REST API
- Provide structured JSON responses
- Access real-time KPIs and operational data

## 📝 Example CV Event Payload

```json
{
  "customer_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "branch_001",
  "enter_time": "2026-02-08T10:00:00Z",
  "exit_time": "2026-02-08T10:15:00Z",
  "action_type": "entered"
}
```

## 🎓 Academic Context

This system is designed as a graduation project with:
- **Production-grade architecture**: Microservices, async processing, proper error handling
- **Clean code principles**: Modular design, dependency injection, comprehensive testing
- **Scalability**: Stateless services, database indexing, time-window aggregation
- **Extensibility**: Well-defined APIs, integration contracts, documented schemas

## 📄 License

This project is part of a graduation project for academic purposes.

## 🤝 Contributing

This is an academic project. For questions or suggestions, please contact the project maintainers.

## 🔍 Troubleshooting

### CV Service Not Detecting People
- Verify video source is accessible
- Check YOLO model is downloaded (first run downloads automatically)
- Adjust `YOLO_CONFIDENCE_THRESHOLD` in `.env`

### Database Connection Issues
- Ensure PostgreSQL is running: `docker-compose ps`
- Check database credentials in `.env`
- Verify network connectivity: `docker-compose logs postgres`

### API Service Errors
- Check logs: `docker-compose logs api_service`
- Verify all migrations are applied: `alembic current`
- Ensure database is accessible

### No KPIs Generated
- Verify movement data exists in database
- Check ETL service logs
- Ensure branches are created before running ETL

## 📞 Support

For issues or questions:
1. Check the logs: `docker-compose logs [service_name]`
2. Review API documentation: `http://localhost:8000/docs`
3. Verify environment configuration in `.env`
