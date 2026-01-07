from fastapi import FastAPI
from app.config import settings
from app.routes import router


app = FastAPI(title=settings.SERVICE_NAME)


@app.get("/health")
async def health_root():
    return {"status": "ok"}


app.include_router(router, prefix="/api/v1")
"""API Gateway - Main entry point for all client requests."""

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
from datetime import datetime
import uuid
import logging
import httpx
import os
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service registry
SERVICES = {
    "auth": {
        "url": os.getenv("AUTH_SERVICE_URL", "http://localhost:8001"),
        "name": "Authentication Service",
        "version": "1.0.0",
    },
    "profile": {
        "url": os.getenv("PROFILE_SERVICE_URL", "http://localhost:8002"),
        "name": "Profile Service",
        "version": "1.0.0",
    },
    "loan": {
        "url": os.getenv("LOAN_SERVICE_URL", "http://localhost:8003"),
        "name": "Loan Service",
        "version": "1.0.0",
    },
    "document": {
        "url": os.getenv("DOCUMENT_SERVICE_URL", "http://localhost:8004"),
        "name": "Document Service",
        "version": "1.0.0",
    },
    "notification": {
        "url": os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8005"),
        "name": "Notification Service",
        "version": "1.0.0",
    },
    "audit": {
        "url": os.getenv("AUDIT_SERVICE_URL", "http://localhost:8006"),
        "name": "Audit Service",
        "version": "1.0.0",
    },
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown handlers."""
    # Startup
    logger.info("API Gateway starting...")
    logger.info(f"Connected services: {list(SERVICES.keys())}")
    yield
    # Shutdown
    logger.info("API Gateway shutting down...")


app = FastAPI(
    title="Multi-Finance Platform API Gateway",
    description="API Gateway for multi-finance microservices platform",
    version="1.0.0",
    lifespan=lifespan,
)


# Middleware for request correlation tracing
@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add correlation ID to all requests for tracing."""
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "api-gateway",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/v1/discovery", tags=["Discovery"])
async def discovery():
    """Service discovery endpoint for AI/agents."""
    return {
        "service": {
            "name": "Multi-Finance Platform API Gateway",
            "version": "1.0.0",
            "description": "API Gateway routing requests to microservices",
        },
        "capabilities": {
            "authentication": True,
            "authorization": True,
            "rate_limiting": True,
            "service_composition": True,
            "tracing": True,
        },
        "endpoints": {
            "health": "/health",
            "auth": "/api/v1/auth",
            "users": "/api/v1/users",
            "loans": "/api/v1/loans",
            "documents": "/api/v1/documents",
            "notifications": "/api/v1/notifications",
            "audit": "/api/v1/audit",
        },
        "authentication": {
            "type": "bearer",
            "scheme": "JWT",
            "header": "Authorization",
            "format": "Bearer <token>",
        },
        "services": SERVICES,
    }


# Auth Service Routes
@app.post("/api/v1/auth/login", tags=["Authentication"])
async def login(request: Request):
    """Login endpoint."""
    return await proxy_request(request, "auth", "/api/v1/auth/login")


@app.post("/api/v1/auth/register", tags=["Authentication"])
async def register(request: Request):
    """Registration endpoint."""
    return await proxy_request(request, "auth", "/api/v1/auth/register")


@app.post("/api/v1/auth/refresh", tags=["Authentication"])
async def refresh_token(request: Request):
    """Refresh token endpoint."""
    return await proxy_request(request, "auth", "/api/v1/auth/refresh")


# Profile Service Routes
@app.get("/api/v1/users/{user_id}", tags=["Users"])
async def get_user(user_id: str, request: Request):
    """Get user profile."""
    return await proxy_request(request, "profile", f"/api/v1/users/{user_id}")


@app.patch("/api/v1/users/{user_id}", tags=["Users"])
async def update_user(user_id: str, request: Request):
    """Update user profile."""
    return await proxy_request(request, "profile", f"/api/v1/users/{user_id}")


# Loan Service Routes
@app.get("/api/v1/loans", tags=["Loans"])
async def list_loans(request: Request):
    """List user loans."""
    return await proxy_request(request, "loan", "/api/v1/loans")


@app.post("/api/v1/loans", tags=["Loans"])
async def create_loan(request: Request):
    """Create new loan application."""
    return await proxy_request(request, "loan", "/api/v1/loans")


@app.get("/api/v1/loans/{loan_id}", tags=["Loans"])
async def get_loan(loan_id: str, request: Request):
    """Get loan details."""
    return await proxy_request(request, "loan", f"/api/v1/loans/{loan_id}")


# Document Service Routes
@app.post("/api/v1/documents/upload", tags=["Documents"])
async def upload_document(request: Request):
    """Upload document."""
    return await proxy_request(request, "document", "/api/v1/documents/upload")


@app.get("/api/v1/documents/{doc_id}", tags=["Documents"])
async def get_document(doc_id: str, request: Request):
    """Get document."""
    return await proxy_request(request, "document", f"/api/v1/documents/{doc_id}")


# Notification Routes
@app.post("/api/v1/notifications", tags=["Notifications"])
async def send_notification(request: Request):
    """Send notification."""
    return await proxy_request(request, "notification", "/api/v1/notifications")


# Audit Routes
@app.get("/api/v1/audit", tags=["Audit"])
async def get_audit_logs(request: Request):
    """Get audit logs."""
    return await proxy_request(request, "audit", "/api/v1/audit")


async def proxy_request(request: Request, service: str, path: str):
    """Proxy request to backend service."""
    if service not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Service '{service}' not found")
    
    service_url = SERVICES[service]["url"]
    full_url = f"{service_url}{path}"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Forward request to service
            response = await client.request(
                method=request.method,
                url=full_url,
                headers={
                    "X-Correlation-ID": request.state.correlation_id,
                    **{k: v for k, v in request.headers.items() if k.lower() != "host"},
                },
                content=await request.body(),
                params=dict(request.query_params),
            )
            
            return JSONResponse(
                status_code=response.status_code,
                content=response.json() if response.text else {},
                headers={"X-Correlation-ID": request.state.correlation_id},
            )
    except Exception as e:
        logger.error(f"Service proxy error: {e}", extra={"correlation_id": request.state.correlation_id})
        return JSONResponse(
            status_code=503,
            content={
                "type": "https://api.example.com/errors/service-unavailable",
                "title": "Service Unavailable",
                "status": 503,
                "detail": f"Could not reach {service} service",
                "error_code": "SERVICE_UNAVAILABLE",
                "trace_id": request.state.correlation_id,
            },
        )


def custom_openapi():
    """Custom OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Multi-Finance Platform API",
        version="1.0.0",
        description="API Gateway for microservices-based financial platform",
        routes=app.routes,
    )
    
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
