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
    db.execute(
        """
        INSERT INTO files (
            uuid, customer_id, filename, file_hash, uploaded_at,
            analysis_status, analysis_started_at, analysis_completed_at, analysis_cost,
            file_size
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            file_uuid,
            customer_id,
            file.filename,
            file_hash,
            datetime.utcnow().isoformat(),
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

    # XXX TODO assure document ownership
    # if document.customer_id != customer_id:
    #     raise HTTPException(status_code=403, detail="Document does not belong to this customer")

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

    # XXX TODO assure document ownership
    # if document.customer_id != customer_id:
    #     raise HTTPException(status_code=403, detail="Document does not belong to this customer")

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


@router.get("/check_exists/{uuid}", response_model=bool)
@log_endpoint
async def check_that_the_document_exists(
    uuid: str,
    db=Depends(get_db)
) -> bool:
    row = db.execute(
        "SELECT 1 FROM files WHERE uuid = ?",
        (uuid,)
    ).fetchone()

    exists = row is not None
    logger.info(f"Document exists check for UUID {uuid}: {exists}")
    return exists


@router.put("/{customer_id}/versions/{uuid}")
@log_endpoint
async def update_document_version(
    customer_id: str,
    uuid: str,
    comment: str = Form(...),
    file: UploadFile = File(...),
    db=Depends(get_db)
) -> dict:
    # Verify document exists and belongs to the customer
    row = db.execute(
        "SELECT filename, customer_id, file_hash, file_size FROM files WHERE uuid = ?",
        (uuid,)
    ).fetchone()
    if not row:
        logger.info(f"Document not found for UUID: {uuid}")
        raise HTTPException(status_code=404, detail="Document not found")
    if row["customer_id"] != customer_id:
        raise HTTPException(status_code=403, detail="Document does not belong to this customer")

    original_hash = row["file_hash"]
    original_size = row["file_size"]

    original_filename = row["filename"]
    customer_dir = os.path.join(BASE_UPLOAD_DIR, customer_id)
    current_path = os.path.join(customer_dir, original_filename)
    if not os.path.exists(current_path):
        raise HTTPException(status_code=404, detail="Original file not found on disk")

    # Backup existing file
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    name_root, ext = os.path.splitext(original_filename)
    backup_name = f"{name_root}_{timestamp}{ext}"
    backup_path = os.path.join(customer_dir, backup_name)
    os.rename(current_path, backup_path)

    # Record the old version
    db.execute(
        """
        INSERT INTO document_versions
          (document_uuid, customer_id, version_path, file_size, file_hash, comment, uploaded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            uuid,
            customer_id,
            backup_path,
            original_size,
            original_hash,
            comment,
            datetime.utcnow().isoformat()
        )
    )
    db.commit()

    # Save the new file
    contents = await file.read()
    new_filename = file.filename
    new_path = os.path.join(customer_dir, new_filename)
    with open(new_path, "wb") as buffer:
        buffer.write(contents)
    new_hash = hashlib.sha256(contents).hexdigest()

    # XXX Compute new file metadata
    # file_size = len(contents)
    # new_hash = new_hash
    # uploaded_at = datetime.utcnow().isoformat()
    # analysis_status = 'pending'
    # analysis_started_at = None
    # analysis_completed_at = None

    # Update file metadata
    db.execute(
        """
        UPDATE files
        SET filename = ?, file_hash = ?, uploaded_at = ?
        WHERE uuid = ?
        """,
        (new_filename, new_hash, datetime.utcnow().isoformat(), uuid)
    )
    db.commit()

    # XXX TODO Reset document to trigger re-analysis
    # XXX TODO remember to update file path in the document
    logger.info("Resetting document to trigger re-analysis")
    # await update_document_metadata(...)

    logger.info(f"Updated document for customer {customer_id}, UUID {uuid}, new file {file.filename}")
    return {"status": "success", "document_uuid": uuid, "version_path": backup_path}


@router.get("/{customer_id}/versions/{uuid}", response_model=List[DocumentVersion])
@log_endpoint
async def get_document_versions(
    customer_id: str,
    uuid: str,
    db=Depends(get_db)
) -> List[DocumentVersion]:
    rows = db.execute(
        """
        SELECT document_uuid, customer_id, version_path, file_size, file_hash, comment, uploaded_at
        FROM document_versions
        WHERE document_uuid = ? AND customer_id = ?
        ORDER BY uploaded_at DESC
        """,
        (uuid, customer_id)
    ).fetchall()

    if not rows:
        logger.info(f"No versions found for document UUID {uuid}")
        raise HTTPException(status_code=404, detail="No document versions found")

    versions = [DocumentVersion(**dict(row)) for row in rows]
    logger.info(f"Retrieved {len(versions)} versions for document UUID {uuid}")
    return versions


@router.get("/{customer_id}/versions", response_model=List[DocumentVersion])
@log_endpoint
async def list_customer_document_versions(customer_id: str, db=Depends(get_db)) -> List[DocumentVersion]:
    """
    List all document versions for a given customer across all files.
    """
    rows = db.execute(
        """
        SELECT document_uuid, customer_id, version_path, file_size, file_hash, comment, uploaded_at
        FROM document_versions
        WHERE customer_id = ?
        ORDER BY uploaded_at DESC
        """,
        (customer_id,)
    ).fetchall()

    if not rows:
        logger.info(f"No document versions found for customer {customer_id}")
        raise HTTPException(status_code=404, detail="No document versions found for this customer")

    versions = [DocumentVersion(**dict(row)) for row in rows]
    logger.info(f"Retrieved {len(versions)} versions for customer {customer_id}")
    return versions


@router.delete("/delete/{customer_id}/{filename}")
@log_endpoint
async def delete_document(customer_id: str, filename: str, db=Depends(get_db)):
    # XXX TODO assure document ownership
    # if document.customer_id != customer_id:
    #     raise HTTPException(status_code=403, detail="Document does not belong to this customer")

    file_path = os.path.join(BASE_UPLOAD_DIR, customer_id, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    os.remove(file_path)

    # Update file_count for customer
    db.execute(
        "UPDATE customers SET file_count = file_count - 1 WHERE customer_id = ? AND file_count > 0",
        (customer_id,)
    )
    db.commit()

    logger.info(f"Deleted file for customer {customer_id}: {filename}")
    return {"status": "deleted", "customer_id": customer_id, "filename": filename}


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
