import json
import logging
from typing import List, Literal

import tiktoken
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from backend.api.api_v1.endpoints.customer_endpoints import get_customer
from backend.api.api_v1.endpoints.documents_endpoints import get_document
from backend.db.schemas.rag_schemas import MessagePayload, RAGMessage
from backend.decorators import log_endpoint
from backend.dependencies import ai_client, get_db
from backend.utils.helpers import update_tokens_spent_async
from backend.utils.prompt_generators import load_prompts

logger = logging.getLogger(__name__)

router = APIRouter()


# Ensure logging is properly configured
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@router.get("/ask")
@log_endpoint
async def ask_question_about_document(
    customer_id: str,
    document_uuid: str,
    question: str = Query(...),
    db=Depends(get_db)
) -> EventSourceResponse:
    """RAG ask endpoint with streaming."""
    # Get customer output language
    customer = await get_customer(customer_id, db)
    output_language = customer["output_language"]
    prompts = load_prompts()

    print("customer", customer)
    print("output_language", output_language)

    # XXX TODO add tasks and alerts in the RAG feature
    document = await get_document(document_uuid, db)
    print(document)

    # XXX TODO assure document ownership

    # Get message history
    conversation_history = await get_messages(document_uuid, order="desc", db=db)
    print(conversation_history)
    # XXX TODO rag to init conversation about the finding about the documents (alerts, tasks, insights)

    # XXX TODO utilise init_rag and rag_query prompts

    # Record incoming question on a separate DB connection to avoid closed DB issue
    db_ctx = get_db()
    db_conn = next(db_ctx)
    try:
        await record_messages(
            document_uuid=document_uuid,
            payload=MessagePayload(question=question),
            db=db_conn
        )
    finally:
        db_ctx.close()

    # Build custom system message for RAG
    system_message = "You are a helpful assistant."

    # Streaming event generator
    async def event_generator():
        try:
            stream = ai_client.chat.completions.create(
                model="gpt-4.1",
                temperature=0.5,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": question},
                ],
                stream=True,
            )
        except Exception as e:
            logger.error("AI streaming error: %s", e, exc_info=True)
            raise HTTPException(status_code=502, detail="AI service error")

        try:
            enc = tiktoken.encoding_for_model("gpt-4")
        except Exception:
            enc = tiktoken.get_encoding("cl100k_base")
        prompt_tokens = sum(len(enc.encode(msg)) for msg in [system_message, question])
        completion_chunks: List[str] = []

        for chunk in stream:
            choices = getattr(chunk, "choices", None)
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            content = getattr(delta, "content", None)
            if not content:
                continue
            completion_chunks.append(content)
            yield f"data: {json.dumps({'content': content})}\n\n"

        # Compute and record token usage
        completion_tokens = sum(len(enc.encode(c)) for c in completion_chunks)
        total_tokens = prompt_tokens + completion_tokens

        # Record token usage asynchronously
        await update_tokens_spent_async(
            document_uuid=document_uuid,
            add_tokens_spent=total_tokens,
        )
        logger.info("Tokens spent updated for document %s", document_uuid)

        # Record the full answer on a separate DB connection to avoid closed DB issue
        full_answer = "".join(completion_chunks)
        db_ctx = get_db()
        db_conn = next(db_ctx)
        try:
            await record_messages(
                document_uuid=document_uuid,
                payload=MessagePayload(answer=full_answer),
                db=db_conn
            )
        finally:
            db_ctx.close()

        yield "data: [DONE]\n\n"

    return EventSourceResponse(
        event_generator(),
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        },
        media_type="text/event-stream"
    )


@router.post("/message", response_model=RAGMessage)
@log_endpoint
async def record_messages(
    document_uuid: str,
    payload: MessagePayload = Body(...),
    db=Depends(get_db)
) -> RAGMessage:
    # enforce alternation: no two questions or two answers in a row
    db.execute(
        "SELECT message_type FROM messages WHERE document_uuid = ? ORDER BY id DESC LIMIT 1",
        (document_uuid,)
    )
    context_type = 'question' if payload.question else 'answer'
    content = payload.question or payload.answer
    cursor = db.execute(
        "INSERT INTO messages (document_uuid, message_type, content) VALUES (?, ?, ?)",
        (document_uuid, context_type, content)
    )
    db.commit()
    message_id = cursor.lastrowid
    cursor = db.execute(
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
    sql = (
        "SELECT id, document_uuid, message_type, content, created_at "
        "FROM messages WHERE document_uuid = ? "
        f"ORDER BY id {order.upper()}"
    )
    cursor = db.execute(sql, (document_uuid,))
    rows = cursor.fetchall()
    return [RAGMessage(**row) for row in rows]
