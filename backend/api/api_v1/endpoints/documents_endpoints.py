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
