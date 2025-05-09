from fastapi import APIRouter

from backend.api.api_v1.endpoints import (db_endpoints, documents_endpoints,
                                          generic_endpoints)

api_router = APIRouter()

# Generic Endpoints
api_router.include_router(
    generic_endpoints.router,
    tags=["Generic"]
)

# Files Endpoints
api_router.include_router(
    documents_endpoints.router,
    prefix="/documents",
    tags=["Documents"]
)

# DB Endpoints
api_router.include_router(
    db_endpoints.router,
    prefix="/db",
    tags=["DB"]
)
