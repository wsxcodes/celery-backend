import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict
import shutil
import os

from backend.decorators import log_endpoint

router = APIRouter()

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger.setLevel(logging.INFO)


# XXX incorporate customer_id


@router.post("/upload")
@log_endpoint
async def upload_file(file: UploadFile = File(...)) -> Dict[str, str]:
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    logger.info(f"Uploaded file: {file.filename}")
    return {"status": "success", "filename": file.filename}


@router.put("/update/{filename}")
@log_endpoint
async def update_file(filename: str, file: UploadFile = File(...)) -> Dict[str, str]:
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    logger.info(f"Updated file: {filename}")
    return {"status": "updated", "filename": filename}


@router.delete("/delete/{filename}")
@log_endpoint
async def delete_file(filename: str) -> Dict[str, str]:
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    os.remove(file_path)
    logger.info(f"Deleted file: {filename}")
    return {"status": "deleted", "filename": filename}
