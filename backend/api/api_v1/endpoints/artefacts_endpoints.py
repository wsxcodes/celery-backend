import logging
import os
from datetime import datetime
from enum import Enum
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend import config
from backend.db.schemas.artefacts_schemas import Artefact, ArtefactUpdate
from backend.decorators import log_endpoint
from backend.dependencies import get_db

router = APIRouter()

BASE_UPLOAD_DIR = config.BASE_UPLOAD_DIR
os.makedirs(BASE_UPLOAD_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger.setLevel(logging.INFO)


@router.get("/{uuid}", response_model=Artefact, response_model_exclude_none=False)
@log_endpoint
async def get_artefact(
    uuid: str,
    db=Depends(get_db)
) -> Artefact:
    # Query artefact metadata from database
    row = db.execute(
        "SELECT * FROM files WHERE uuid = ?",
        (uuid,)
    ).fetchone()

    if hasattr(row, "keys"):
        logger.debug("get_artefact row keys: %s", row.keys())
        logger.debug("get_artefact row data: %r", dict(row))

    if not row:
        logger.info(f"Artefact not found for UUID: {uuid}")
        raise HTTPException(status_code=404, detail="Artefact not found")

    # Convert database row to Artefact schema
    artefact = Artefact(**dict(row))
    logger.info(f"get_artefact returning data for UUID {uuid}: %s", artefact.dict())

    logger.info(f"Retrieved artefact for UUID: {uuid}")
    return artefact


@router.patch("/metadata/{uuid}", response_model=Artefact, response_model_exclude_none=False)
@log_endpoint
async def update_artefact_metadata(uuid: str, update: ArtefactUpdate, db=Depends(get_db)):
    data = update.dict(exclude_unset=True)
    logger.info(f"update_artefact_metadata called for UUID {uuid} with data: %s", data)

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
    logger.debug("update_artefact_metadata SQL: %s", query)
    logger.debug("update_artefact_metadata params: %s", values)
    db.execute(query, values)
    db.commit()

    row = db.execute("SELECT * FROM files WHERE uuid = ?", (uuid,)).fetchone()
    logger.info(f"update_artefact_metadata updated row for UUID {uuid}: %s", dict(row))
    if not row:
        raise HTTPException(status_code=404, detail="Artefact not found")

    updated_doc = Artefact(**dict(row))
    logger.info(f"update_artefact_metadata returning updated artefact for UUID {uuid}: %s", updated_doc.dict())
    return updated_doc


@router.get("/list/pending", response_model=List[Artefact])
@log_endpoint
async def list_pending_artefacts(limit: int = 10, db=Depends(get_db)):
    rows = db.execute(
        "SELECT * FROM files WHERE analysis_status = 'pending' LIMIT ?",
        (limit,)
    ).fetchall()

    artefacts = [Artefact(**dict(row)) for row in rows]
    logger.info(f"Retrieved {len(artefacts)} pending artefacts (limit: {limit})")
    return artefacts


@router.get("/list/all", response_model=List[Artefact])
@log_endpoint
async def list_all_artefacts(limit: int = 10, offset: int = 0, db=Depends(get_db)):
    rows = db.execute(
        "SELECT * FROM files LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()

    artefacts = [Artefact(**dict(row)) for row in rows]
    logger.info(f"Retrieved {len(artefacts)} artefacts (limit: {limit}, offset: {offset})")
    return artefacts
