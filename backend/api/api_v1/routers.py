from fastapi import APIRouter

from backend.api.api_v1.endpoints import (artefacts_endpoints,
                                          documents_endpoints,
                                          generic_endpoints, llm_endpoints,
                                          rag_endpoints, utils_endpoints)

api_router = APIRouter()

# Documents Endpoints
api_router.include_router(
    documents_endpoints.router,
    prefix="/document",
    tags=["Documents"]
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

# Utils Endpoints
api_router.include_router(
    utils_endpoints.router,
    prefix="/utils",
    tags=["Utils"]
)

# Artefacts Endpoints
api_router.include_router(
    artefacts_endpoints.router,
    prefix="/artefact",
    tags=["Artefacts"]
)

# Generic Endpoints
api_router.include_router(
    generic_endpoints.router,
    tags=["Generic"]
)
