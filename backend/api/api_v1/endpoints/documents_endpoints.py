import json
import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from google.cloud import storage

from backend import config
from backend.db.schemas.artefacts_schemas import AImode
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
    customer_data: str = Form(
        ...,
        description='Customer data JSON string. Example: {"customer_name": "Jan Filips"}'
    ),
    bucket: Optional[str] = Form(None),
    document_path: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    ai_analysis_mode: AImode = Form(...),
    output_language: str = Form('Czech'),
    webhook_url: str = Form(...),
    db=Depends(get_db),
) -> dict:
    try:
        customer_data = json.loads(customer_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="customer_data must be valid JSON")

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

    # Compute metadata
    file_size = len(contents)
    file_uuid = customer_id + "_" + str(filename)

    # Write file to disk
    if file is None:
        # Download directly to file_path from Google Cloud Storage
        blob.download_to_filename(file_path)
        # Read contents back if needed
        with open(file_path, "rb") as f:
            contents = f.read()
    else:
        with open(file_path, "wb") as buffer:
            buffer.write(contents)

    # Delete existing document record and file for this UUID
    existing = db.execute(
        "SELECT filename FROM files WHERE uuid = ?",
        (file_uuid,),
    ).fetchone()
    if existing:
        old_file_path = os.path.join(customer_dir, existing[0])
        if os.path.exists(old_file_path):
            os.remove(old_file_path)
        db.execute(
            "DELETE FROM files WHERE uuid = ?",
            (file_uuid,),
        )

    # Save metadata to DB
    now_iso = datetime.utcnow().isoformat()
    db.execute(
        """
        INSERT INTO files (
            uuid, customer_id, filename, uploaded_at,
            analysis_status, analysis_started_at, analysis_completed_at,
            file_size
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            file_uuid,
            customer_id,
            filename,
            now_iso,
            'pending',
            None,
            None,
            file_size,
        )
    )
    db.commit()

    logger.info(f"Uploaded file for customer {customer_id}: {filename} ({file_size} bytes)")
    return {
        "status": "success",
        "customer_id": customer_id,
        "filename": filename,
        "file_size": file_size
    }
