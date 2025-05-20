import hashlib
import logging
import os
import uuid
from datetime import datetime
from enum import Enum
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend import config
from backend.db.schemas.documents_schemas import (Document, DocumentUpdate,
                                                  DocumentVersion)
from backend.decorators import log_endpoint
from backend.dependencies import get_db

router = APIRouter()

BASE_UPLOAD_DIR = config.BASE_UPLOAD_DIR
os.makedirs(BASE_UPLOAD_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger.setLevel(logging.INFO)


@router.post("/{customer_id}")
@log_endpoint
async def add_new_document(
    customer_id: str,
    file: UploadFile = File(...),
    db=Depends(get_db)
) -> dict:
    customer_dir = os.path.join(BASE_UPLOAD_DIR, customer_id)
    os.makedirs(customer_dir, exist_ok=True)
    file_path = os.path.join(customer_dir, file.filename)

    # Check if file already exists for customer
    if os.path.exists(file_path):
        logger.info(f"File already exists for customer {customer_id}: {file.filename}")
        raise HTTPException(status_code=409, detail="File already exists!")

    # Read entire file content into memory
    contents = await file.read()

    # Compute metadata
    file_size = len(contents)
    file_hash = hashlib.sha256(contents).hexdigest()
    file_uuid = str(uuid.uuid4())

    # Write file to disk
    with open(file_path, "wb") as buffer:
        buffer.write(contents)

    # Save metadata to DB
    now_iso = datetime.utcnow().isoformat()
    db.execute(
        """
        INSERT INTO files (
            uuid, customer_id, filename, file_hash, uploaded_at, updated_at,
            analysis_status, analysis_started_at, analysis_completed_at, analysis_cost,
            file_size
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            file_uuid,
            customer_id,
            file.filename,
            file_hash,
            now_iso,
            now_iso,
            'pending',
            None,
            None,
            0,
            file_size
        )
    )
    db.commit()

    # Update file_count for customer
    db.execute(
        "UPDATE customers SET file_count = file_count + 1 WHERE customer_id = ?",
        (customer_id,)
    )
    db.commit()

    # Record document version
    db.execute(
        """
        INSERT INTO document_versions (
            document_uuid,
            customer_id,
            version_path,
            file_size,
            file_hash,
            comment,
            uploaded_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            file_uuid,
            customer_id,
            file_path,
            file_size,
            file_hash,
            "Initial upload",
            datetime.utcnow().isoformat()
        )
    )
    db.commit()

    logger.info(f"Uploaded file for customer {customer_id}: {file.filename} ({file_size} bytes)")
    return {
        "status": "success",
        "customer_id": customer_id,
        "filename": file.filename,
        "uuid": file_uuid,
        "file_hash": file_hash,
        "file_size": file_size
    }


@router.get("/{uuid}", response_model=Document, response_model_exclude_none=False)
@log_endpoint
async def get_document(
    uuid: str,
    db=Depends(get_db)
) -> Document:
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
    document = Document(**dict(row))
    logger.info(f"get_document returning data for UUID {uuid}: %s", document.dict())

    logger.info(f"Retrieved document for UUID: {uuid}")
    return document


@router.patch("/metadata/{uuid}", response_model=Document, response_model_exclude_none=False)
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

    updated_doc = Document(**dict(row))
    logger.info(f"update_document_metadata returning updated document for UUID {uuid}: %s", updated_doc.dict())
    return updated_doc


@router.delete("/delete/{document_uuid}")
@log_endpoint
async def delete_document(customer_id: str, db=Depends(get_db)):
    # XXX TODO
    return False


@router.get("/list/pending", response_model=List[Document])
@log_endpoint
async def list_pending_documents(limit: int = 10, db=Depends(get_db)):
    rows = db.execute(
        "SELECT * FROM files WHERE analysis_status = 'pending' LIMIT ?",
        (limit,)
    ).fetchall()

    documents = [Document(**dict(row)) for row in rows]
    logger.info(f"Retrieved {len(documents)} pending documents (limit: {limit})")
    return documents
