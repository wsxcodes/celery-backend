import hashlib
import logging
import os
import shutil
import uuid
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.db.schemas.documents_schemas import DocumentUpdate
from backend.decorators import log_endpoint
from backend.dependencies import get_db

router = APIRouter()

BASE_UPLOAD_DIR = "data/uploads"
os.makedirs(BASE_UPLOAD_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger.setLevel(logging.INFO)


@router.post("/upload/{customer_id}")
@log_endpoint
async def add_new_document(
    customer_id: str,
    file: UploadFile = File(...),
    db=Depends(get_db)
) -> dict:
    customer_dir = os.path.join(BASE_UPLOAD_DIR, customer_id)
    os.makedirs(customer_dir, exist_ok=True)
    file_path = os.path.join(customer_dir, file.filename)

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

    logger.info(f"Uploaded file for customer {customer_id}: {file.filename} ({file_size} bytes)")
    return {
        "status": "success",
        "customer_id": customer_id,
        "filename": file.filename,
        "uuid": file_uuid,
        "file_hash": file_hash,
        "file_size": file_size
    }


@router.patch("/metadata/{document_id}")
@log_endpoint
async def update_document_metadata(document_id: int, update: DocumentUpdate, db=Depends(get_db)):
    fields = []
    values = []
    file_id = document_id

    if update.analysis_status is not None:
        fields.append("analysis_status = ?")
        values.append(update.analysis_status)

    if update.analysis_started_at is not None:
        fields.append("analysis_started_at = ?")
        values.append(update.analysis_started_at.isoformat())

    if update.analysis_completed_at is not None:
        fields.append("analysis_completed_at = ?")
        values.append(update.analysis_completed_at.isoformat())

    if update.analysis_cost is not None:
        fields.append("analysis_cost = ?")
        values.append(update.analysis_cost)

    if not fields:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    values.append(file_id)

    query = f"UPDATE files SET {', '.join(fields)} WHERE id = ?"
    db.execute(query, values)
    db.commit()

    return {"status": "updated", "file_id": file_id}


@router.put("/version/{customer_id}/{filename}")
@log_endpoint
async def update_document_version(customer_id: str, filename: str, file: UploadFile = File(...)) -> Dict[str, str]:
    customer_dir = os.path.join(BASE_UPLOAD_DIR, customer_id)
    file_path = os.path.join(customer_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    logger.info(f"Updated file for customer {customer_id}: {filename}")
    return {"status": "updated", "customer_id": customer_id, "filename": filename}


@router.delete("/delete/{customer_id}/{filename}")
@log_endpoint
async def delete_document(customer_id: str, filename: str) -> Dict[str, str]:
    file_path = os.path.join(BASE_UPLOAD_DIR, customer_id, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    os.remove(file_path)
    logger.info(f"Deleted file for customer {customer_id}: {filename}")
    return {"status": "deleted", "customer_id": customer_id, "filename": filename}
