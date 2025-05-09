import logging
from typing import List

from fastapi import APIRouter, Depends

from fastapi import HTTPException
from backend.db.schemas.files_schemas import FileRecord, Customer
from backend.decorators import log_endpoint
from backend.dependencies import get_db

logger = logging.getLogger(__name__)

# Ensure logging is properly configured
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()


@router.get("/customers", response_model=List[Customer])
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


@router.get("/customers/{customer_id}", response_model=Customer)
@log_endpoint
async def get_customer(customer_id: str, db=Depends(get_db)):
    cursor = db.execute("""
        SELECT customer_id, COUNT(*) AS file_count
        FROM files
        WHERE customer_id = ?
        GROUP BY customer_id
    """, (customer_id,))
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return dict(row)


@router.get("/list/{customer_id}", response_model=List[FileRecord])
@log_endpoint
async def list_files(customer_id: str, db=Depends(get_db)):
    cursor = db.execute(
        "SELECT id, customer_id, filename, uploaded_at FROM files WHERE customer_id = ? ORDER BY uploaded_at DESC",
        (customer_id,)
    )
    rows = cursor.fetchall()
    return [dict(row) for row in rows]
