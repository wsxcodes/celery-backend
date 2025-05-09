from fastapi import APIRouter

from backend.api.api_v1.endpoints import generic_endpoints

api_router = APIRouter()

# Generic Endpoints
api_router.include_router(
    generic_endpoints.router,
    tags=["Generic"]
)
