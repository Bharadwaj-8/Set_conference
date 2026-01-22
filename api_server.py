# api_server.py
"""
REST API server for the Green AI Orchestrator
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import uvicorn
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import json
from datetime import datetime

from orchestrator.decision_engine import DynamicGreenOrchestrator
from utils.logger import setup_logging
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

# Global orchestrator instance
orchestrator = None
decision_history = []


# Pydantic models
class ContextRequest(BaseModel):
    """Request model for context"""
    battery_percentage: Optional[float] = Field(None, ge=0, le=100, description="Battery percentage (0-100)")
    carbon_flag: Optional[int] = Field(None, ge=0, le=1, description="Carbon flag (0=dirty, 1=green)")
    network_quality: Optional[float] = Field(None, ge=0, le=1, description="Network quality (0-1)")
    use_real_data: bool = Field(True, description="Use real system data if available")


class DecisionRequest(BaseModel):
    """Request model for decision"""
    context: Optional[ContextRequest] = None
    weights: Optional[Dict[str, float]] = Field(
        None,
        description="Custom weights for battery, carbon, network"
    )
    threshold: Optional[float] = Field(None, ge=0, le=1, description="Decision threshold")


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


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    platform: str
    timestamp: datetime
    monitors_available: Dict[str, bool]


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize orchestrator on startup"""
    global orchestrator
    try:
        logger.info("Initializing Green AI Orchestrator...")
        orchestrator = DynamicGreenOrchestrator()
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
        "endpoints": {
            "health": "/health",
            "context": "/context",
            "decision": "/decision",
            "decisions": "/decisions",
            "docs": "/docs"
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
        platform=orchestrator.platform_info.get("system", "unknown"),
        timestamp=datetime.now(),
        monitors_available=monitors_available
    )


@app.get("/context", tags=["Context"])
async def get_context(use_real_data: bool = True):
    """Get current system context"""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        context = orchestrator.collect_context(use_real_data=use_real_data)
        return JSONResponse(content=context, status_code=200)
    except Exception as e:
        logger.error(f"Failed to collect context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/decision", response_model=DecisionResponse, tags=["Decision"])
async def make_decision(request: DecisionRequest):
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
        decision = orchestrator.make_decision(context=context_dict)

        # Convert to dict for response
        decision_dict = decision.to_dict()

        # Add to history
        decision_history.append(decision_dict)

        # Keep only last 1000 decisions
        if len(decision_history) > 1000:
            decision_history.pop(0)

        return DecisionResponse(**decision_dict)

    except Exception as e:
        logger.error(f"Failed to make decision: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/decisions", tags=["History"])
async def get_decisions(
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of decisions to return"),
        offset: int = Query(0, ge=0, description="Offset for pagination")
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
async def get_decision(decision_id: str):
    """Get specific decision by ID"""
    for decision in decision_history:
        if decision.get("decision_id") == decision_id:
            return decision

    raise HTTPException(status_code=404, detail="Decision not found")


@app.post("/decisions/batch", tags=["Decision"])
async def make_batch_decisions(
        requests: List[DecisionRequest],
        background_tasks: BackgroundTasks
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

            decision = orchestrator.make_decision(context=context_dict)
            decision_dict = decision.to_dict()

            # Add to history
            decision_history.append(decision_dict)

            results.append({
                "index": i,
                "success": True,
                "decision": decision_dict
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

    return {
        "total": len(requests),
        "successful": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results
    }


@app.get("/stats", tags=["Statistics"])
async def get_statistics():
    """Get decision statistics"""
    if not decision_history:
        return {"message": "No decisions made yet"}

    total = len(decision_history)
    edge_decisions = sum(1 for d in decision_history if d["execution_mode"] == "EDGE")
    cloud_decisions = total - edge_decisions

    scores = [d["score"] for d in decision_history]
    confidences = [d["confidence"] for d in decision_history]

    return {
        "total_decisions": total,
        "edge_decisions": edge_decisions,
        "cloud_decisions": cloud_decisions,
        "edge_percentage": (edge_decisions / total * 100) if total > 0 else 0,
        "cloud_percentage": (cloud_decisions / total * 100) if total > 0 else 0,
        "average_score": sum(scores) / total if total > 0 else 0,
        "average_confidence": sum(confidences) / total if total > 0 else 0,
        "time_range": {
            "first": decision_history[0]["timestamp"],
            "last": decision_history[-1]["timestamp"]
        }
    }


def main():
    """Main function to run the API server"""
    import argparse

    parser = argparse.ArgumentParser(description="Green AI Orchestrator API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--log-level", default="info", help="Log level")

    args = parser.parse_args()

    # Setup logging
    setup_logging(level=args.log_level.upper())

    print(f"Starting Green AI Orchestrator API server...")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Reload: {args.reload}")
    print(f"Log Level: {args.log_level}")
    print("-" * 40)
    print(f"API Documentation: http://{args.host}:{args.port}/docs")
    print("-" * 40)

    uvicorn.run(
        "api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level
    )


if __name__ == "__main__":
    main()