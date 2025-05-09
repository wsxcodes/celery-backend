import logging
from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException

from backend.db.schemas.customers_schemas import Customer, UpdateCustomer
from backend.decorators import log_endpoint
from backend.dependencies import get_db

logger = logging.getLogger(__name__)

# Ensure logging is properly configured
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()


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

    db.execute(
        """
        INSERT INTO customers (customer_id, output_language, file_count)
        VALUES (?, ?, ?)
        """,
        (customer_id, output_language, 0)
    )
    db.commit()
    return {"status": "registered", "customer_id": customer_id, "output_language": output_language}


@router.get("/all", response_model=List[Customer])
@log_endpoint
async def list_customers(db=Depends(get_db)):
    cursor = db.execute("""
        SELECT customer_id, output_language, file_count
        FROM customers
        ORDER BY customer_id
    """)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


@router.get("/{customer_id}", response_model=Customer)
@log_endpoint
async def get_customer(customer_id: str, db=Depends(get_db)):
    cursor = db.execute("""
        SELECT customer_id, output_language, file_count
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
        SELECT customer_id, output_language, file_count
        FROM customers
        WHERE customer_id = ?
    """, (customer_id,)).fetchone()
    return dict(updated)


@router.get("/documents/{customer_id}", response_model=dict)
@log_endpoint
async def list_customer_documents(customer_id: str, db=Depends(get_db)):
    cursor = db.execute("""
        SELECT id, customer_id, uuid, filename, file_size, file_hash, uploaded_at,
               analysis_status, analysis_started_at, analysis_completed_at, analysis_cost,
               ai_alert, ai_category, ai_summary_short, ai_summary_text as ai_summary_long
        FROM files
        WHERE customer_id = ?
        ORDER BY uploaded_at DESC
    """, (customer_id,))
    rows = cursor.fetchall()

    docs = [dict(row) for row in rows]

    from collections import defaultdict

    category_map = defaultdict(list)
    for doc in docs:
        category_map[doc["ai_category"]].append(doc)

    sorted_categories = sorted(category_map.keys(), key=lambda x: (x is not None and x != "", x or ""))

    categorized_documents = [
        {"category": cat or None, "documents": category_map[cat]}
        for cat in sorted_categories
    ]

    return {
        "documents": docs,
        "categorized_documents": categorized_documents
    }
