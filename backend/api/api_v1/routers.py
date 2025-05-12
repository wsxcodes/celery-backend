from fastapi import APIRouter

from backend.api.api_v1.endpoints import (customer_endpoints,
                                          documents_endpoints,
                                          generic_endpoints, rag_endpoints,
                                          utils_endpoints)

api_router = APIRouter()

# Generic Endpoints
api_router.include_router(
    generic_endpoints.router,
    tags=["Generic"]
)

# RAG Endpoints
api_router.include_router(
    rag_endpoints.router,
    prefix="/rag",
    tags=["RAG"]
)

# Documents Endpoints
api_router.include_router(
    documents_endpoints.router,
    prefix="/document",
    tags=["Documents"]
)

# Customer Endpoints
api_router.include_router(
    customer_endpoints.router,
    prefix="/customer",
    tags=["Customers"]
)

# Customer Endpoints
api_router.include_router(
    utils_endpoints.router,
    prefix="/utils",
    tags=["Utils"]
)
