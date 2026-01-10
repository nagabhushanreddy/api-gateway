"""Route handlers for API Gateway."""

from fastapi import APIRouter

from app.routes import admin, discovery, health, proxy

# Create main router
router = APIRouter()

# Include sub-routers (order matters - more specific routes first)
router.include_router(health.router, tags=["Health"])
router.include_router(discovery.router, prefix="/api/v1", tags=["Discovery"])
router.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
router.include_router(
    proxy.router, prefix="/api/v1", tags=["Proxy"]
)  # Catch-all should be last
