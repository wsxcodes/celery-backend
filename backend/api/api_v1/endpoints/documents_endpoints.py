import hashlib
import logging
import os
import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional
from google.cloud import storage

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend import config
from backend.db.schemas.artefacts_schemas import (AImode, Artefact, ArtefactUpdate)
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
    customer_data: dict,
    bucket: Optional[str] = Form(None),
    document_path: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    output_language: str = Form(...),
    ai_analysis_mode: AImode = Form(...),
    webhook_url: str = Form(...),
    db=Depends(get_db),
) -> dict:
    # Validate that either a file is uploaded or GCS bucket and document_path are provided
    if file is None:
        if not bucket or not document_path:
            raise HTTPException(status_code=400, detail="Either upload a file or provide bucket and document_path")
        # Download file from Google Cloud Storage
        gcs_client = storage.Client()
        gcs_bucket = gcs_client.bucket(bucket)
        blob = gcs_bucket.blob(document_path)
        contents = blob.download_as_bytes()
        filename = os.path.basename(document_path)
    else:
        contents = await file.read()
        filename = file.filename

    customer_dir = os.path.join(BASE_UPLOAD_DIR, customer_id)
    os.makedirs(customer_dir, exist_ok=True)
    file_path = os.path.join(customer_dir, filename)

    # Check if file already exists for customer
    if os.path.exists(file_path):
        logger.info(f"File already exists for customer {customer_id}: {filename}")
        raise HTTPException(status_code=409, detail="File already exists!")

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
            filename,
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

    logger.info(f"Uploaded file for customer {customer_id}: {filename} ({file_size} bytes)")
    return {
        "status": "success",
        "customer_id": customer_id,
        "filename": filename,
        "uuid": file_uuid,
        "file_hash": file_hash,
        "file_size": file_size
    }
