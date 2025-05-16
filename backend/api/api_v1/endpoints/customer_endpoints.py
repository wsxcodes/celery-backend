import logging
from datetime import datetime, timezone
from typing import List

import humanize
from fastapi import APIRouter, Body, Depends, HTTPException

from backend.db.schemas.customers_schemas import Customer, UpdateCustomer, AImode
from backend.decorators import log_endpoint
from backend.dependencies import get_db

logger = logging.getLogger(__name__)

# Ensure logging is properly configured
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()


# XXX TODO provide token spending report for each customer

@router.post("/")
@log_endpoint
async def add_new_customer(customer_id: str, output_language: str = "Czech", db=Depends(get_db)) -> dict:
    logger.info(f"Registering new customer: {customer_id}")
    # Check if customer already exists
    existing = db.execute(
        "SELECT 1 FROM customers WHERE customer_id = ?",
        (customer_id,)
    ).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="Customer already registered")

    cursor = db.execute(
        """
        INSERT INTO customers (customer_id, output_language, file_count, ai_mode)
        VALUES (?, ?, ?, ?)
        """,
        (customer_id, output_language, 0, AImode.standard.value)
    )
    db.commit()
    customer_id_int = cursor.lastrowid
    return {
        "status": "registered",
        "id": customer_id_int,
        "customer_id": customer_id,
        "output_language": output_language
    }


@router.get("/{customer_id}", response_model=Customer)
@log_endpoint
async def get_customer(customer_id: str, db=Depends(get_db)):
    cursor = db.execute("""
        SELECT id, customer_id, output_language, ai_mode, file_count
        FROM customers
        WHERE customer_id = ?
    """, (customer_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Customer not found")
    return dict(row)


@router.patch("/{customer_id}", response_model=Customer)
@log_endpoint
async def update_customer(customer_id: str, update: UpdateCustomer = Body(...), db=Depends(get_db)):
    existing = db.execute("""
        SELECT customer_id FROM customers WHERE customer_id = ?
    """, (customer_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Customer not found")

    update_data = update.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    for key, value in update_data.items():
        db.execute(f"UPDATE customers SET {key} = ? WHERE customer_id = ?", (value, customer_id))
    db.commit()

    updated = db.execute("""
        SELECT id, customer_id, output_language, ai_mode, file_count
        FROM customers
        WHERE customer_id = ?
    """, (customer_id,)).fetchone()
    return dict(updated)


@router.get("/documents/{customer_id}", response_model=dict)
@log_endpoint
async def list_customer_documents(customer_id: str, limit: int = None, db=Depends(get_db)):
    logger = logging.getLogger(__name__)

    # Build SQL query with optional LIMIT
    query = """
        SELECT id, customer_id, uuid, filename, file_hash, file_preview, uploaded_at,
               analysis_status, analysis_started_at, analysis_completed_at, analysis_cost,
               ai_alert, ai_expires, ai_category, ai_sub_category, ai_summary_short,
               ai_summary_long, ai_analysis_criteria, ai_features_and_insights,
               ai_alerts_and_actions, ai_enterny_legacy_schema, file_size, raw_text,
               health_score
        FROM files
        WHERE customer_id = ?
        ORDER BY uploaded_at DESC
    """
    params = [customer_id]
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    # Fetch documents from the database
    cursor = db.execute(query, tuple(params))
    rows = cursor.fetchall()

    docs = [dict(row) for row in rows]

    # Categorize documents
    from collections import defaultdict
    category_map = defaultdict(list)
    for doc in docs:
        category_map[doc["ai_category"]].append(doc)

    sorted_categories = sorted(category_map.keys(), key=lambda x: (x is not None and x != "", x or ""))

    categorized_documents = [
        {"category": cat or None, "documents": category_map[cat]}
        for cat in sorted_categories
    ]

    # Enrich categorized_documents with file_size_human and uploaded_at_human
    for cat_index, cat in enumerate(categorized_documents):
        for doc_index, doc in enumerate(cat.get("documents", [])):
            if "file_size" in doc:
                doc["file_size_human"] = humanize.naturalsize(doc["file_size"], binary=False)
            if "uploaded_at" in doc:
                try:
                    uploaded_at_utc = datetime.fromisoformat(doc["uploaded_at"]).replace(tzinfo=timezone.utc)
                    now_utc = datetime.now(timezone.utc)
                    doc["uploaded_at_human"] = humanize.naturaltime(now_utc - uploaded_at_utc)
                except ValueError:
                    logger.warning(
                        "uploaded_at for doc %d in category %d is not in the correct datetime format: %s",
                        doc_index + 1,
                        cat_index + 1,
                        doc["uploaded_at"]
                    )

    return {
        "documents": docs,
        "categorized_documents": categorized_documents
    }


@router.get("/all", response_model=List[Customer])
@log_endpoint
async def list_customers(db=Depends(get_db)):
    cursor = db.execute("""
        SELECT id, customer_id, output_language, ai_mode, file_count
        FROM customers
        ORDER BY customer_id
    """)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]
