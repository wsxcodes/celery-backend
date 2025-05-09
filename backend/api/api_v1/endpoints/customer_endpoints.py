import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.db.schemas.documents_schemas import (Customer, Document,
                                                  DocumentUpdate)
from backend.decorators import log_endpoint
from backend.dependencies import get_db

logger = logging.getLogger(__name__)

# Ensure logging is properly configured
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()


@router.get("/", response_model=List[Customer])
@log_endpoint
async def list_customers(db=Depends(get_db)):
    cursor = db.execute("""
        SELECT customer_id, COUNT(*) AS file_count
        FROM files
        GROUP BY customer_id
        ORDER BY customer_id
    """)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


@router.get("/{customer_id}", response_model=List[Document])
@log_endpoint
async def list_customer_documents(customer_id: str, db=Depends(get_db)):
    cursor = db.execute("""
        SELECT id, uuid, customer_id, filename, file_hash, uploaded_at,
            analysis_status, analysis_started_at, analysis_completed_at, analysis_cost, file_size
        FROM files
        WHERE customer_id = ?
        ORDER BY uploaded_at DESC
    """, (customer_id,))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


@router.patch("/document/{document_id}")
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
