import hashlib
import logging
import os
import uuid
from datetime import datetime
from enum import Enum
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend import config
from backend.db.schemas.artefacts_schemas import (Artefact, DocumentUpdate,
                                                  DocumentVersion)
from backend.decorators import log_endpoint
from backend.dependencies import get_db

router = APIRouter()

BASE_UPLOAD_DIR = config.BASE_UPLOAD_DIR
os.makedirs(BASE_UPLOAD_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger.setLevel(logging.INFO)


@router.get("/{uuid}", response_model=Artefact, response_model_exclude_none=False)
@log_endpoint
async def get_document(
    uuid: str,
    db=Depends(get_db)
) -> Artefact:
    # Query document metadata from database
    row = db.execute(
        "SELECT * FROM files WHERE uuid = ?",
        (uuid,)
    ).fetchone()

    if hasattr(row, "keys"):
        logger.debug("get_document row keys: %s", row.keys())
        logger.debug("get_document row data: %r", dict(row))

    if not row:
        logger.info(f"Document not found for UUID: {uuid}")
        raise HTTPException(status_code=404, detail="Document not found")

    # Convert database row to Document schema
    document = Artefact(**dict(row))
    logger.info(f"get_document returning data for UUID {uuid}: %s", document.dict())

    logger.info(f"Retrieved document for UUID: {uuid}")
    return document


@router.patch("/metadata/{uuid}", response_model=Artefact, response_model_exclude_none=False)
@log_endpoint
async def update_document_metadata(uuid: str, update: DocumentUpdate, db=Depends(get_db)):
    data = update.dict(exclude_unset=True)
    logger.info(f"update_document_metadata called for UUID {uuid} with data: %s", data)

    if not data:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    fields = []
    values = []

    for key, value in data.items():
        if isinstance(value, Enum):
            value = value.value
        elif isinstance(value, datetime):
            value = value.isoformat()
        fields.append(f"{key} = ?")
        values.append(value)

    values.append(uuid)
    query = f"UPDATE files SET {', '.join(fields)} WHERE uuid = ?"
    logger.debug("update_document_metadata SQL: %s", query)
    logger.debug("update_document_metadata params: %s", values)
    db.execute(query, values)
    db.commit()

    row = db.execute("SELECT * FROM files WHERE uuid = ?", (uuid,)).fetchone()
    logger.info(f"update_document_metadata updated row for UUID {uuid}: %s", dict(row))
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    updated_doc = Artefact(**dict(row))
    logger.info(f"update_document_metadata returning updated document for UUID {uuid}: %s", updated_doc.dict())
    return updated_doc


@router.delete("/delete/{document_uuid}")
@log_endpoint
async def delete_document(customer_id: str, db=Depends(get_db)):
    # XXX TODO delete document from DB and filesystem
    return False


@router.get("/list/pending", response_model=List[Artefact])
@log_endpoint
async def list_pending_documents(limit: int = 10, db=Depends(get_db)):
    rows = db.execute(
        "SELECT * FROM files WHERE analysis_status = 'pending' LIMIT ?",
        (limit,)
    ).fetchall()

    documents = [Artefact(**dict(row)) for row in rows]
    logger.info(f"Retrieved {len(documents)} pending documents (limit: {limit})")
    return documents
