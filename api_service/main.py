"""FastAPI main application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog
from contextlib import asynccontextmanager

from api_service.config import api_config
from api_service.routers import cv_ingestion, branches, tasks, events, kpis, situations, recommendations
from db.session import engine

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer() if api_config.log_format == "json" 
        else structlog.dev.ConsoleRenderer()
    ]
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Retail Intelligence API Service")
    yield
    # Shutdown
    logger.info("Shutting down Retail Intelligence API Service")
    await engine.dispose()


# Create FastAPI application
app = FastAPI(
    title="Retail Intelligence API",
    description="Backend API for Retail Intelligence Decision Support System",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=api_config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(cv_ingestion.router)
app.include_router(branches.router)
app.include_router(tasks.router)
app.include_router(events.router)
app.include_router(kpis.router)
app.include_router(situations.router)
app.include_router(recommendations.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "retail-intelligence-api",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Retail Intelligence API",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_service.main:app",
        host=api_config.api_host,
        port=api_config.api_port,
        reload=True
    )
