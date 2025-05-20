from fastapi import APIRouter

from backend.api.api_v1.endpoints import (documents_endpoints,
                                          generic_endpoints, llm_endpoints,
                                          rag_endpoints, utils_endpoints, artifacts_endpoints)

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

# LLM Endpoints
api_router.include_router(
    llm_endpoints.router,
    prefix="/llm",
    tags=["LLM"]
)

# Documents Endpoints
api_router.include_router(
    documents_endpoints.router,
    prefix="/document",
    tags=["Documents"]
)

# Artifacts Endpoints
api_router.include_router(
    artifacts_endpoints.router,
    prefix="/artifacts",
    tags=["Artifacts"]
)

# Customer Endpoints
api_router.include_router(
    utils_endpoints.router,
    prefix="/utils",
    tags=["Utils"]
)
