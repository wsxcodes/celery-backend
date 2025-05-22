import hashlib
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
from backend.core.celery import celery_app

router = APIRouter()

BASE_UPLOAD_DIR = config.BASE_UPLOAD_DIR
os.makedirs(BASE_UPLOAD_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger.setLevel(logging.INFO)


@router.post("/{customer_id}")
@log_endpoint
async def add_document_for_analysis(
    customer_id: str,
    customer_data: str = Form(
        ...,
        description='Customer data JSON string. Example: {"customer_name": "Jan Filips"}'
    ),
    gcs_bucket: Optional[str] = Form(None),
    gcs_file_path: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    ai_analysis_mode: AImode = Form(...),
    ai_output_language: str = Form('Czech'),
    eterny_api_webhook_url: str = Form(...),
    db=Depends(get_db),
) -> dict:
    try:
        customer_data = json.loads(customer_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="customer_data must be valid JSON")

    # Ensure mutually exclusive inputs: either file or GCS info
    if file and (gcs_bucket or gcs_file_path):
        raise HTTPException(status_code=400, detail="Provide either a file or bucket+document_path, not both")

    # Validate that either a file is uploaded or GCS bucket and document_path are provided
    if file is None:
        if not gcs_bucket or not gcs_file_path:
            raise HTTPException(status_code=400, detail="Either upload a file or provide gcs_bucket and gcs_file_path")
        # Download file from Google Cloud Storage
        gcs_client = storage.Client()
        bucket = gcs_client.bucket(gcs_bucket)
        blob = bucket.blob(gcs_file_path)
        filename = os.path.basename(gcs_file_path)
        customer_dir = os.path.join(BASE_UPLOAD_DIR, customer_id)
        os.makedirs(customer_dir, exist_ok=True)
        file_path = os.path.join(customer_dir, filename)
        blob.download_to_filename(file_path)
        with open(file_path, "rb") as f:
            contents = f.read()
        hash_sha256 = hashlib.sha256(contents).hexdigest()
    else:
        contents = await file.read()
        hash_sha256 = hashlib.sha256(contents).hexdigest()
        filename = file.filename
        customer_dir = os.path.join(BASE_UPLOAD_DIR, customer_id)
        os.makedirs(customer_dir, exist_ok=True)
        file_path = os.path.join(customer_dir, filename)
        with open(file_path, "wb") as buffer:
            buffer.write(contents)

    # Compute metadata
    file_size = len(contents)
    file_uuid = customer_id + "_" + str(filename)

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
            ai_output_language, ai_analysis_mode, analysis_status, analysis_started_at, analysis_completed_at,
            webhook_url,
            file_size,
            hash_sha256
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            file_uuid,
            customer_id,
            filename,
            now_iso,
            ai_output_language,
            ai_analysis_mode,
            'pending',
            None,
            None,
            eterny_api_webhook_url,
            file_size,
            hash_sha256
        )
    )
    db.commit()

    logger.info("Triggering Celery task for document analysis")
    try:
        task = celery_app.send_task(
            "backend.workers.ai_analysis.analyse_document",
            args=[file_uuid],
        )
    except Exception as e:
        logger.error(f"Failed to start Celery worker: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start Celery worker")

    logger.info(f"Uploaded file for customer {customer_id}: {filename} ({file_size} bytes)")
    return {
        "status": "success",
        "customer_id": customer_id,
        "filename": filename,
        "sha256": hash_sha256,
        "file_size": file_size
    }
