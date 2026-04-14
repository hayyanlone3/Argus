# backend/main.py
"""
ARGUS v2.2 - Provenance Graph Anomaly Detection System
Main FastAPI application with 6-layer detection pipeline
"""

import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.logger import setup_logger
from database.connection import init_db
from config import settings

# Import all layer routers
from layers.layer0_bouncer.routes import router as layer0_router
from layers.layer1_graph_engine.routes import router as layer1_router
from layers.layer2_scoring.routes import router as layer2_router
from layers.layer3_correlator.routes import router as layer3_router
from layers.layer4_response.routes import router as layer4_router
from layers.layer5_learning.routes import router as layer5_router

logger = setup_logger(__name__)

# ═══════════════════════════════════════════════════════════════
# LIFESPAN EVENTS
# ═══════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events"""
    
    # STARTUP
    fs_collector = None
    try:
        logger.info("=" * 80)
        logger.info("🚀 ARGUS v2.2 Backend Initializing...")
        logger.info("=" * 80)
        
        # Initialize database
        init_db()
        
        logger.info("✅ Database initialized successfully")
        logger.info("✅ API running on 0.0.0.0:8000")
        logger.info("✅ Debug mode: True")

        # Start file-system collector (Plan A in-process ingestion)
        if settings.collector_enabled:
            from collectors.fs_watcher import FileSystemCollector
            watched = [p.strip() for p in settings.collector_watched_paths.split(",") if p.strip()]
            fs_collector = FileSystemCollector(
                watched_paths=watched,
                hash_max_bytes=settings.collector_hash_max_bytes,
            )
            fs_collector.start()
            logger.info("✅ FileSystemCollector started")
        else:
            logger.info("ℹ️  FileSystemCollector disabled (set COLLECTOR_ENABLED=true to enable)")

        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        sys.exit(1)
    
    yield
    
    # SHUTDOWN
    logger.info("🛑 ARGUS Backend shutting down...")
    if fs_collector is not None:
        fs_collector.stop()

# ═══════════════════════════════════════════════════════════════
# FASTAPI APP
# ═══════════════════════════════════════════════════════════════

app = FastAPI(
    title="ARGUS v2.2",
    description="Provenance Graph Anomaly Detection System",
    version="2.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ═══════════════════════════════════════════════════════════════
# CORS MIDDLEWARE
# ═══════════════════════════════════════════════════════════════

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════════
# ROOT ENDPOINT
# ═══════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.2.0",
        "environment": "development",
        "database": "connected",
        "api_url": "http://0.0.0.0:8000",
    }

# ═══════════════════════════════════════════════════════════════
# INCLUDE ALL LAYER ROUTERS
# ═══════════════════════════════════════════════════════════════

# Layer 0: Bouncer
app.include_router(layer0_router, prefix="/api/layer0", tags=["Layer 0: Bouncer"])

# Layer 1: Graph Engine
app.include_router(layer1_router, prefix="/api/layer1", tags=["Layer 1: Graph Engine"])

# Layer 2: Scoring
app.include_router(layer2_router, prefix="/api/layer2", tags=["Layer 2: Scoring"])

# Layer 3: Correlator
app.include_router(layer3_router, prefix="/api/layer3", tags=["Layer 3: Correlator"])

# Layer 4: Response
app.include_router(layer4_router, prefix="/api/layer4", tags=["Layer 4: Response"])

# Layer 5: Learning
app.include_router(layer5_router, prefix="/api/layer5", tags=["Layer 5: Learning"])

# ═══════════════════════════════════════════════════════════════
# ERROR HANDLERS
# ═══════════════════════════════════════════════════════════════

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors"""
    return {
        "error": "Not Found",
        "path": str(request.url),
        "message": f"Endpoint {request.url.path} not found",
    }

@app.exception_handler(500)
async def server_error_handler(request, exc):
    """Handle 500 errors"""
    logger.error(f"❌ Server error: {exc}")
    return {
        "error": "Internal Server Error",
        "message": "An unexpected error occurred",
    }

# ═══════════════════════════════════════════════════════════════
# STARTUP LOG
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )