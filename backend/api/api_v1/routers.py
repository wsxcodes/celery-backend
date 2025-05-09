from fastapi import APIRouter

from backend.api.api_v1.endpoints import generic_endpoints, files_endpoints, db_endpoints

api_router = APIRouter()

# Generic Endpoints
api_router.include_router(
    generic_endpoints.router,
    tags=["Generic"]
)

# Files Endpoints
api_router.include_router(
    files_endpoints.router,
    prefix="/files",
    tags=["Files"]
)

# DB Endpoints
api_router.include_router(
    db_endpoints.router,
    prefix="/db",
    tags=["DB"]
)
