import logging
from typing import List, Literal

from fastapi import APIRouter, Body, Depends, HTTPException

from backend.api.api_v1.endpoints.documents_endpoints import get_document
from backend.decorators import log_endpoint
from backend.dependencies import get_db
from backend.db.schemas.rag_schemas import MessagePayload, RAGMessage

logger = logging.getLogger(__name__)

router = APIRouter()


# Ensure logging is properly configured
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# XXX TODO rag to init conversation about the finding about the documents (alerts, tasks, insights)
# XXX TODO add tasks and alerts in the RAG feature


@router.post("/")
@log_endpoint
async def ask_question_about_document(
    uuid: str,
    question: str = Body(...),
    db=Depends(get_db)
) -> dict[str, str]:
    """RAG ask endpoint."""
    # XXX tokens_spent should be added to the document metadata
    document = await get_document(uuid, db)

    # XXX TODO rag to init conversation about the finding (alerts, tasks, insights)
    # XXX TODO add tasks and alerts in the RAG feature

    logger.info(f"Document found: {document}")
    return {
        "status": "XXX",
        "message": "TODO"
    }


@router.post("/message", response_model=RAGMessage)
@log_endpoint
async def record_messages(
    document_uuid: str,
    payload: MessagePayload = Body(...),
    db=Depends(get_db)
) -> RAGMessage:
    cursor = db.cursor()
    # enforce alternation: no two questions or two answers in a row
    cursor.execute(
        "SELECT message_type FROM messages WHERE document_uuid = ? ORDER BY id DESC LIMIT 1",
        (document_uuid,)
    )
    last = cursor.fetchone()
    new_type = 'question' if payload.question else 'answer'
    if last and last["message_type"] == new_type:
        raise HTTPException(
            status_code=400,
            detail=f"Previous message was {last['message_type']!r}; must alternate."
        )
    content = payload.question or payload.answer
    cursor.execute(
        "INSERT INTO messages (document_uuid, message_type, content) VALUES (?, ?, ?)",
        (document_uuid, new_type, content)
    )
    db.commit()
    message_id = cursor.lastrowid
    cursor.execute(
        "SELECT id, document_uuid, message_type, content, created_at FROM messages WHERE id = ?",
        (message_id,)
    )
    row = cursor.fetchone()
    return RAGMessage(**row)


@router.get("/messages/{document_uuid}", response_model=List[RAGMessage])
@log_endpoint
async def get_messages(
    document_uuid: str,
    order: Literal["asc", "desc"] = "desc",
    db=Depends(get_db)
) -> List[RAGMessage]:
    # validate ordering parameter
    order = order.lower()
    if order not in ("asc", "desc"):
        raise HTTPException(
            status_code=400,
            detail="Query parameter 'order' must be 'asc' or 'desc'"
        )
    cursor = db.cursor()
    sql = (
        "SELECT id, document_uuid, message_type, content, created_at "
        "FROM messages WHERE document_uuid = ? "
        f"ORDER BY id {order.upper()}"
    )
    cursor.execute(sql, (document_uuid,))
    rows = cursor.fetchall()
    return [RAGMessage(**row) for row in rows]
