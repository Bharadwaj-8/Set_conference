# src/api/server.py
"""
FastAPI server for the Green AI Orchestrator
"""

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
import time
from datetime import datetime
import uuid

from ..orchestrator.decision_engine import DynamicGreenOrchestrator
from ..utils.logger import setup_logging
from ..utils.platform import get_platform_info
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Green AI Orchestrator API",
    description="REST API for dynamic, carbon-aware workload orchestration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Global orchestrator instance
orchestrator = None
decision_history = []


# Pydantic models
class ContextRequest(BaseModel):
    """Request model for context"""
    battery_percentage: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Battery percentage (0-100)"
    )
    carbon_flag: Optional[int] = Field(
        None,
        ge=0,
        le=1,
        description="Carbon flag (0=dirty, 1=green)"
    )
    network_quality: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Network quality (0-1)"
    )
    network_speed_mbps: Optional[float] = Field(
        None,
        ge=0,
        description="Network speed in Mbps"
    )
    use_real_data: bool = Field(
        True,
        description="Use real system data if available"
    )

    @validator('battery_percentage')
    def validate_battery(cls, v):
        if v is not None and not 0 <= v <= 100:
            raise ValueError('Battery percentage must be between 0 and 100')
        return v

    @validator('network_quality')
    def validate_network_quality(cls, v):
        if v is not None and not 0 <= v <= 1:
            raise ValueError('Network quality must be between 0 and 1')
        return v


class DecisionRequest(BaseModel):
    """Request model for decision"""
    context: Optional[ContextRequest] = Field(
        None,
        description="Optional context data"
    )
    weights: Optional[Dict[str, float]] = Field(
        None,
        description="Custom weights for battery, carbon, network"
    )
    threshold: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Decision threshold"
    )

    @validator('weights')
    def validate_weights(cls, v):
        if v is not None:
            total = sum(v.values())
            if abs(total - 1.0) > 0.01:
                raise ValueError('Weights must sum to approximately 1.0')
        return v

    @validator('threshold')
    def validate_threshold(cls, v):
        if v is not None and not 0 <= v <= 1:
            raise ValueError('Threshold must be between 0 and 1')
        return v


class DecisionResponse(BaseModel):
    """Response model for decision"""
    decision_id: str
    execution_mode: str
    score: float
    confidence: float
    reasoning: str
    timestamp: datetime
    context: Dict[str, Any]
    metadata: Dict[str, Any]
    processing_time_ms: float


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    platform: str
    timestamp: datetime
    monitors_available: Dict[str, bool]
    uptime_seconds: float


class StatisticsResponse(BaseModel):
    """Statistics response"""
    total_decisions: int
    edge_decisions: int
    cloud_decisions: int
    edge_percentage: float
    cloud_percentage: float
    average_score: float
    average_confidence: float
    time_range: Dict[str, Optional[datetime]]


# Dependency for authentication (optional)
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify authentication token"""
    # This is a simple example. In production, use proper authentication.
    token = credentials.credentials
    if token != "secret-token":  # Replace with real authentication
        raise HTTPException(status_code=403, detail="Invalid token")
    return token


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize orchestrator on startup"""
    global orchestrator
    global startup_time

    try:
        logger.info("Initializing Green AI Orchestrator API...")
        orchestrator = DynamicGreenOrchestrator()
        startup_time = time.time()
        logger.info("Orchestrator initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize orchestrator: {e}")
        raise


# Routes
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "service": "Green AI Orchestrator API",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "context": "/context",
            "decision": "/decision",
            "decisions": "/decisions",
            "stats": "/stats"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    # Check monitor availability
    monitors_available = {}
    for name, monitor in orchestrator.monitors.items():
        monitors_available[name] = monitor.is_available()

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        platform=get_platform_info().get("system", "unknown"),
        timestamp=datetime.now(),
        monitors_available=monitors_available,
        uptime_seconds=time.time() - startup_time
    )


@app.get("/context", tags=["Context"])
async def get_context(
        use_real_data: bool = Query(True, description="Use real system data"),
        # token: str = Depends(verify_token)  # Uncomment to enable authentication
):
    """Get current system context"""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        context = orchestrator.collect_context(use_real_data=use_real_data)
        return JSONResponse(content=context.to_dict(), status_code=200)
    except Exception as e:
        logger.error(f"Failed to collect context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/decision", response_model=DecisionResponse, tags=["Decision"])
async def make_decision(
        request: DecisionRequest,
        background_tasks: BackgroundTasks,
        # token: str = Depends(verify_token)  # Uncomment to enable authentication
):
    """Make a routing decision"""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        # Prepare context
        context_dict = None
        if request.context:
            # Use provided context
            context_dict = request.context.dict(exclude_none=True)

        # Make decision
        decision = orchestrator.make_decision(
            context=None,  # Will be collected if not provided
            custom_weights=request.weights,
            custom_threshold=request.threshold
        )

        # Convert to dict for response
        decision_dict = decision.to_dict()

        # Add to history
        decision_history.append(decision_dict)

        # Keep only last 1000 decisions
        if len(decision_history) > 1000:
            decision_history.pop(0)

        # Background task to save decision
        background_tasks.add_task(
            orchestrator._save_decision,
            decision,
            len(decision_history)
        )

        return DecisionResponse(**decision_dict)

    except Exception as e:
        logger.error(f"Failed to make decision: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/decisions", tags=["History"])
async def get_decisions(
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of decisions"),
        offset: int = Query(0, ge=0, description="Offset for pagination"),
        # token: str = Depends(verify_token)
):
    """Get decision history"""
    start = min(offset, len(decision_history))
    end = min(start + limit, len(decision_history))

    return {
        "total": len(decision_history),
        "offset": offset,
        "limit": limit,
        "decisions": decision_history[start:end]
    }


@app.get("/decisions/{decision_id}", tags=["History"])
async def get_decision(
        decision_id: str,
        # token: str = Depends(verify_token)
):
    """Get specific decision by ID"""
    for decision in decision_history:
        if decision.get("decision_id") == decision_id:
            return decision

    raise HTTPException(status_code=404, detail="Decision not found")


@app.get("/stats", response_model=StatisticsResponse, tags=["Statistics"])
async def get_statistics(
        # token: str = Depends(verify_token)
):
    """Get decision statistics"""
    if not decision_history:
        return StatisticsResponse(
            total_decisions=0,
            edge_decisions=0,
            cloud_decisions=0,
            edge_percentage=0,
            cloud_percentage=0,
            average_score=0,
            average_confidence=0,
            time_range={"first": None, "last": None}
        )

    total = len(decision_history)
    edge_decisions = sum(1 for d in decision_history if d["execution_mode"] == "EDGE")
    cloud_decisions = total - edge_decisions

    scores = [d["score"] for d in decision_history]
    confidences = [d["confidence"] for d in decision_history]

    return StatisticsResponse(
        total_decisions=total,
        edge_decisions=edge_decisions,
        cloud_decisions=cloud_decisions,
        edge_percentage=(edge_decisions / total * 100) if total > 0 else 0,
        cloud_percentage=(cloud_decisions / total * 100) if total > 0 else 0,
        average_score=sum(scores) / total if total > 0 else 0,
        average_confidence=sum(confidences) / total if total > 0 else 0,
        time_range={
            "first": decision_history[0]["timestamp"] if decision_history else None,
            "last": decision_history[-1]["timestamp"] if decision_history else None
        }
    )


@app.post("/batch", tags=["Decision"])
async def make_batch_decisions(
        requests: List[DecisionRequest],
        background_tasks: BackgroundTasks,
        # token: str = Depends(verify_token)
):
    """Make multiple decisions in batch"""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    results = []

    for i, request in enumerate(requests):
        try:
            context_dict = None
            if request.context:
                context_dict = request.context.dict(exclude_none=True)

            decision = orchestrator.make_decision(
                context=None,
                custom_weights=request.weights,
                custom_threshold=request.threshold
            )

            decision_dict = decision.to_dict()
            decision_history.append(decision_dict)

            results.append({
                "index": i,
                "success": True,
                "decision_id": decision_dict["decision_id"],
                "execution_mode": decision_dict["execution_mode"],
                "score": decision_dict["score"]
            })

        except Exception as e:
            results.append({
                "index": i,
                "success": False,
                "error": str(e)
            })

    # Keep history manageable
    if len(decision_history) > 1000:
        decision_history[:] = decision_history[-1000:]

    # Background task to save batch
    background_tasks.add_task(
        orchestrator._save_history
    )

    return {
        "total": len(requests),
        "successful": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results
    }


@app.get("/platform", tags=["System"])
async def get_platform_info_endpoint(
        # token: str = Depends(verify_token)
):
    """Get platform information"""
    return get_platform_info()


@app.post("/config", tags=["Configuration"])
async def update_configuration(
        config: Dict[str, Any],
        # token: str = Depends(verify_token)
):
    """Update orchestrator configuration"""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        # This would require reinitializing the orchestrator with new config
        # For simplicity, we'll just return the config for now
        return {
            "message": "Configuration update would require restart",
            "received_config": config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))