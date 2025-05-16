import hashlib
import logging
import os
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend import config
from backend.db.schemas.documents_schemas import Document, DocumentUpdate
from backend.decorators import log_endpoint
from backend.dependencies import get_db

router = APIRouter()

BASE_UPLOAD_DIR = config.BASE_UPLOAD_DIR
os.makedirs(BASE_UPLOAD_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger.setLevel(logging.INFO)

# XXX TODO Assure document ownership
# if document.customer_id != customer_id:
#     raise HTTPException(status_code=403, detail="Document does not belong to this customer")


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

    logger.info(f"Uploaded file for customer {customer_id}: {file.filename} ({file_size} bytes)")
    return {
        "status": "success",
        "customer_id": customer_id,
        "filename": file.filename,
        "uuid": file_uuid,
        "file_hash": file_hash,
        "file_size": file_size
    }


@router.get("/{uuid}", response_model=Document)
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

    if not row:
        logger.info(f"Document not found for UUID: {uuid}")
        raise HTTPException(status_code=404, detail="Document not found")

    # Convert database row to Document schema
    document = Document(**dict(row))

    logger.info(f"Retrieved document for UUID: {uuid}")
    return document


@router.patch("/metadata/{uuid}", response_model=Document)
@log_endpoint
async def update_document_metadata(uuid: str, update: DocumentUpdate, db=Depends(get_db)):
    data = update.dict(exclude_unset=True)

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
    db.execute(query, values)
    db.commit()

    row = db.execute("SELECT * FROM files WHERE uuid = ?", (uuid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    return Document(**dict(row))


@router.put("/version/{customer_id}/{filename}")
@log_endpoint
async def update_document_version(customer_id: str, filename: str, file: UploadFile = File(...)) -> Dict[str, str]:
    # XXX TODO
    return {"status": "XXX TODO"}


@router.delete("/delete/{customer_id}/{filename}")
@log_endpoint
async def delete_document(customer_id: str, filename: str, db=Depends(get_db)):
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
